"""Live Trace Baseline Collection Pass.

Collects a baseline set of local harness runs with trace capture enabled
and policy evaluation in shadow-only mode. Each run simulates a realistic
agent interaction pattern through the actual HarnessTraceCapture API.

This is instrumentation and observation only.
No policy is activated. No intervention is enforced.
No thresholds are lowered. No candidate is metabolized.

Usage:
    PYTHONPATH=. uv run python scripts/settlement_datasets/collect_baseline_traces.py
    PYTHONPATH=. uv run python scripts/settlement_datasets/collect_baseline_traces.py --output-dir data/settlement_datasets/live_harness_traces
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from godspeed_nav.trace_capture import HarnessTraceCapture


def _ts(step: int) -> str:
    """Generate a realistic timestamp for a step."""
    base = datetime(2026, 5, 31, 12, 0, 0, tzinfo=UTC)
    offset = base.timestamp() + step * 3  # 3 seconds between steps
    return datetime.fromtimestamp(offset, tz=UTC).isoformat()


# ── Run Scenario Definitions ──
# Each scenario simulates a realistic agent interaction pattern.
# Scenarios are ordered to cover the diversity requested:
# coding, debugging, shell, test-running, file-edit, API/tool-use tasks.


def run_coding_import_error_same_path(capture: HarnessTraceCapture) -> str:
    """Coding task: two distinct import errors, agent retries same approach."""
    capture.record_model_message(
        "I need to implement the user authentication module. Let me start by running the existing tests.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "python -m pytest tests/test_auth.py -v",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "ImportError: cannot import name 'UserModel' from 'app.models'",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_model_message(
        "The UserModel import is failing. Let me check what's available in app.models and retry.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "python -m pytest tests/test_auth.py -v",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "ImportError: cannot import name 'AuthToken' from 'app.auth'",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_tool_call(
        "python -m pytest tests/test_auth.py -v --tb=short",
        tool_name="bash",
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        "3 failed, 0 passed. ImportError persists in multiple test files.",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_final_answer(
        "The authentication module has cascading import errors. UserModel and AuthToken are not exported from their respective modules.",
        timestamp=_ts(8),
    )
    capture.record_task_complete(timestamp=_ts(9))
    return "failure"


def run_debugging_test_failures_with_revision(capture: HarnessTraceCapture) -> str:
    """Debugging task: repeated test failures, then strategy revision to inspect config."""
    capture.record_model_message(
        "I need to debug why the payment processing tests are failing. Let me run them first.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "pytest tests/test_payments.py -x",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "FAILED tests/test_payments.py::test_charge - AssertionError: expected 200, got 500",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_model_message(
        "The charge endpoint is returning 500. Let me check the server logs.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "cat /var/log/app/server.log | tail -50",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "Traceback: RuntimeError: database connection pool exhausted",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_strategy_revision(
        "Revised plan: the issue is database connection pool exhaustion, not the payment logic. I need to inspect the database configuration first.",
        timestamp=_ts(6),
    )
    capture.record_tool_call(
        "cat config/database.yml",
        tool_name="read",
        timestamp=_ts(7),
    )
    capture.record_tool_result(
        "pool_size: 5\ntimeout: 5000",
        tool_name="read",
        timestamp=_ts(8),
    )
    capture.record_file_edit(
        "Increased pool_size from 5 to 20 in config/database.yml",
        timestamp=_ts(9),
    )
    capture.record_tool_call(
        "pytest tests/test_payments.py -x",
        tool_name="bash",
        timestamp=_ts(10),
    )
    capture.record_tool_result(
        "3 passed in 1.2s",
        tool_name="bash",
        timestamp=_ts(11),
    )
    capture.record_final_answer(
        "Fixed the payment processing tests by increasing the database connection pool size from 5 to 20.",
        timestamp=_ts(12),
    )
    capture.record_task_complete(timestamp=_ts(13))
    return "success"


def run_shell_permission_denied_then_success(capture: HarnessTraceCapture) -> str:
    """Shell task: permission denied, then different approach succeeds."""
    capture.record_model_message(
        "I need to deploy the application to the staging server.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "scp -r ./dist user@staging:/opt/app/",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "Permission denied (publickey). Connection lost.",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_tool_call(
        "scp -r ./dist user@staging:/opt/app/",
        tool_name="bash",
        timestamp=_ts(3),
    )
    capture.record_tool_result(
        "Permission denied (publickey). Connection lost.",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_strategy_revision(
        "Revised plan: SSH key authentication is failing. Let me check the SSH config and try with verbose output.",
        timestamp=_ts(5),
    )
    capture.record_tool_call(
        "ssh -v user@staging 'echo connected'",
        tool_name="bash",
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        "debug1: Offering public key: /home/user/.ssh/id_rsa\ndebug1: Server accepts key\nconnected",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_tool_call(
        "scp -r ./dist user@staging:/opt/app/",
        tool_name="bash",
        timestamp=_ts(8),
    )
    capture.record_tool_result(
        "Deployment complete. 42 files transferred.",
        tool_name="bash",
        timestamp=_ts(9),
    )
    capture.record_final_answer(
        "Successfully deployed to staging after diagnosing SSH key issue.",
        timestamp=_ts(10),
    )
    capture.record_task_complete(timestamp=_ts(11))
    return "success"


def run_test_running_flaky_tests(capture: HarnessTraceCapture) -> str:
    """Test-running task: flaky tests fail twice, agent retries same command."""
    capture.record_model_message(
        "Running the full integration test suite to verify the release.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "pytest tests/integration/ -v --timeout=60",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "FAILED tests/integration/test_api.py::test_concurrent_requests - TimeoutError: request timed out after 30s",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_model_message(
        "The concurrent request test timed out. This might be a flaky test. Let me retry.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "pytest tests/integration/test_api.py::test_concurrent_requests -v --timeout=120",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "FAILED tests/integration/test_api.py::test_concurrent_requests - TimeoutError: request timed out after 60s",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_tool_call(
        "pytest tests/integration/test_api.py::test_concurrent_requests -v --timeout=180",
        tool_name="bash",
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        "FAILED tests/integration/test_api.py::test_concurrent_requests - TimeoutError: request timed out after 90s",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_final_answer(
        "The concurrent request test consistently times out. This appears to be a real performance issue, not a flaky test.",
        timestamp=_ts(8),
    )
    capture.record_task_complete(timestamp=_ts(9))
    return "failure"


def run_file_edit_syntax_error_recovery(capture: HarnessTraceCapture) -> str:
    """File-edit task: syntax error, then inspection, then fix."""
    capture.record_model_message(
        "I need to add input validation to the user registration handler.",
        timestamp=_ts(0),
    )
    capture.record_file_edit(
        "Added email validation regex to handlers/register.py",
        timestamp=_ts(1),
    )
    capture.record_tool_call(
        "python -c 'import handlers.register'",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_tool_result(
        "SyntaxError: invalid syntax in handlers/register.py, line 42",
        tool_name="bash",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "python -c 'import handlers.register'",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "SyntaxError: invalid syntax in handlers/register.py, line 42",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_model_message(
        "Let me inspect the file around line 42 to find the syntax issue.",
        timestamp=_ts(6),
    )
    capture.record_tool_call(
        "sed -n '38,46p' handlers/register.py",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_tool_result(
        "38: if not email:\n39:     return error('email required')\n40: \n41: if not re.match(pattern, email)\n42:     return error('invalid email')  # missing colon",
        tool_name="bash",
        timestamp=_ts(8),
    )
    capture.record_file_edit(
        "Fixed missing colon on line 41 in handlers/register.py",
        timestamp=_ts(9),
    )
    capture.record_tool_call(
        "python -c 'import handlers.register' && echo 'import OK'",
        tool_name="bash",
        timestamp=_ts(10),
    )
    capture.record_tool_result(
        "import OK",
        tool_name="bash",
        timestamp=_ts(11),
    )
    capture.record_final_answer(
        "Added email validation with syntax fix applied.",
        timestamp=_ts(12),
    )
    capture.record_task_complete(timestamp=_ts(13))
    return "success"


def run_api_tool_use_rate_limiting(capture: HarnessTraceCapture) -> str:
    """API/tool-use task: rate limiting errors, then backoff strategy."""
    capture.record_model_message(
        "I need to fetch user data from the external API for all 500 users.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "curl -s https://api.example.com/users/batch -d '{\"ids\": [1..500]}'",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "HTTP 429: Rate limit exceeded. Retry after 60 seconds.",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_tool_call(
        "curl -s https://api.example.com/users/batch -d '{\"ids\": [1..500]}'",
        tool_name="bash",
        timestamp=_ts(3),
    )
    capture.record_tool_result(
        "HTTP 429: Rate limit exceeded. Retry after 60 seconds.",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_strategy_revision(
        "Revised plan: the API has rate limiting. I need to batch requests in groups of 50 with delays between batches.",
        timestamp=_ts(5),
    )
    capture.record_command(
        'for i in $(seq 0 9); do curl -s \'https://api.example.com/users/batch\' -d "{\\"ids\\": [$((i*50+1))..$((i*50+50))]}"; sleep 5; done',
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        "Batch 0: 50 users fetched. Batch 1: 50 users fetched. ... Batch 9: 50 users fetched. Total: 500 users.",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_final_answer(
        "Successfully fetched all 500 user records using batched requests with rate limit handling.",
        timestamp=_ts(8),
    )
    capture.record_task_complete(timestamp=_ts(9))
    return "success"


def run_coding_type_error_inspection(capture: HarnessTraceCapture) -> str:
    """Coding task: type errors, agent inspects before retrying."""
    capture.record_model_message(
        "I need to refactor the data processing pipeline to handle None values.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "pytest tests/test_pipeline.py -v",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "FAILED test_process_data - TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_model_message(
        "Let me inspect the pipeline code to understand the None handling.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "cat pipeline/processor.py | head -80",
        tool_name="read",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "Line 45: result = base_value + optional_addend  # optional_addend can be None",
        tool_name="read",
        timestamp=_ts(5),
    )
    capture.record_file_edit(
        "Added None guard: result = base_value + (optional_addend or 0)",
        timestamp=_ts(6),
    )
    capture.record_tool_call(
        "pytest tests/test_pipeline.py -v",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_tool_result(
        "FAILED test_process_data - TypeError: unsupported operand type(s) for *: 'float' and 'NoneType' at line 67",
        tool_name="bash",
        timestamp=_ts(8),
    )
    capture.record_file_edit(
        "Added None guard at line 67: multiplier = (scale_factor or 1.0)",
        timestamp=_ts(9),
    )
    capture.record_tool_call(
        "pytest tests/test_pipeline.py -v",
        tool_name="bash",
        timestamp=_ts(10),
    )
    capture.record_tool_result(
        "5 passed in 0.8s",
        tool_name="bash",
        timestamp=_ts(11),
    )
    capture.record_final_answer(
        "Fixed all None-handling issues in the data processing pipeline.",
        timestamp=_ts(12),
    )
    capture.record_task_complete(timestamp=_ts(13))
    return "success"


def run_debugging_missing_dependency(capture: HarnessTraceCapture) -> str:
    """Debugging task: missing dependency, agent tries multiple install approaches."""
    capture.record_model_message(
        "The CI build is failing. Let me reproduce the issue locally.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "pip install -r requirements.txt",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "ERROR: Could not find a version that satisfies the requirement numpy==1.26.4",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_tool_call(
        "pip install numpy==1.26.4 --index-url https://pypi.org/simple/",
        tool_name="bash",
        timestamp=_ts(3),
    )
    capture.record_tool_result(
        "ERROR: No matching distribution found for numpy==1.26.4 (python 3.12)",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_call(
        "pip install numpy --upgrade",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_tool_result(
        "Successfully installed numpy-2.0.0",
        tool_name="bash",
        timestamp=_ts(6),
    )
    capture.record_tool_call(
        "pytest tests/ -x --timeout=30",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_tool_result(
        "42 passed in 12.3s",
        tool_name="bash",
        timestamp=_ts(8),
    )
    capture.record_final_answer(
        "Fixed the CI build by upgrading numpy to a version compatible with Python 3.12.",
        timestamp=_ts(9),
    )
    capture.record_task_complete(timestamp=_ts(10))
    return "success"


def run_shell_disk_full_error(capture: HarnessTraceCapture) -> str:
    """Shell task: disk full errors, agent cleans up and retries."""
    capture.record_model_message(
        "I need to build the Docker image for the microservice.",
        timestamp=_ts(0),
    )
    capture.record_command(
        "docker build -t microservice:latest .",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "OSError: [Errno 28] No space left on device",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_command(
        "docker build -t microservice:latest .",
        timestamp=_ts(3),
    )
    capture.record_tool_result(
        "OSError: [Errno 28] No space left on device",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_strategy_revision(
        "Revised plan: the disk is full. I need to clean up Docker images and build cache first.",
        timestamp=_ts(5),
    )
    capture.record_command(
        "docker system prune -af && docker builder prune -af",
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        "Total reclaimed space: 12.5GB",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_command(
        "docker build -t microservice:latest .",
        timestamp=_ts(8),
    )
    capture.record_tool_result(
        "Successfully built microservice:latest (245MB)",
        tool_name="bash",
        timestamp=_ts(9),
    )
    capture.record_final_answer(
        "Built the Docker image after cleaning up 12.5GB of stale Docker data.",
        timestamp=_ts(10),
    )
    capture.record_task_complete(timestamp=_ts(11))
    return "success"


def run_coding_clean_success(capture: HarnessTraceCapture) -> str:
    """Coding task: clean success with no errors."""
    capture.record_model_message(
        "I need to add a health check endpoint to the API server.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "cat api/server.py | grep -n 'def '",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "12: def index():\n34: def users():\n67: def settings():",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_file_edit(
        'Added /health endpoint to api/server.py returning {"status": "ok"}',
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "pytest tests/test_api.py -v -k health",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "1 passed in 0.3s",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_tool_call(
        "curl -s http://localhost:8080/health",
        tool_name="bash",
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        '{"status": "ok"}',
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_final_answer(
        "Added and verified the health check endpoint.",
        timestamp=_ts(8),
    )
    capture.record_task_complete(timestamp=_ts(9))
    return "success"


def run_test_running_mixed_results(capture: HarnessTraceCapture) -> str:
    """Test-running task: some pass, some fail, agent investigates."""
    capture.record_model_message(
        "Running the complete test suite before the release.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "pytest tests/ -v --tb=short",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "45 passed, 3 failed, 2 warnings\nFAILED test_auth_timeout\nFAILED test_cache_invalidation\nFAILED test_websocket_reconnect",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_model_message(
        "Three tests are failing. Let me investigate the auth timeout first since it might be related to the others.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "pytest tests/test_auth_timeout.py -v --tb=long",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "FAILED - AssertionError: expected session to expire after 3600s, but session still valid after 7200s",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_tool_call(
        "grep -n 'SESSION_EXPIRY' config/settings.py",
        tool_name="bash",
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        "SESSION_EXPIRY = 7200  # 2 hours in seconds",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_file_edit(
        "Changed SESSION_EXPIRY from 7200 to 3600 in config/settings.py",
        timestamp=_ts(8),
    )
    capture.record_tool_call(
        "pytest tests/test_auth_timeout.py tests/test_cache_invalidation.py tests/test_websocket_reconnect.py -v",
        tool_name="bash",
        timestamp=_ts(9),
    )
    capture.record_tool_result(
        "3 passed in 2.1s",
        tool_name="bash",
        timestamp=_ts(10),
    )
    capture.record_final_answer(
        "All 48 tests now pass. The root cause was a session expiry misconfiguration.",
        timestamp=_ts(11),
    )
    capture.record_task_complete(timestamp=_ts(12))
    return "success"


def run_api_tool_use_connection_refused(capture: HarnessTraceCapture) -> str:
    """API/tool-use task: connection refused, agent checks service status."""
    capture.record_model_message(
        "I need to verify the payment gateway integration is working.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "curl -s http://payments.internal:8080/health",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "Connection refused: payments.internal:8080",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_tool_call(
        "curl -s http://payments.internal:8080/health",
        tool_name="bash",
        timestamp=_ts(3),
    )
    capture.record_tool_result(
        "Connection refused: payments.internal:8080",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_model_message(
        "The payment service is not responding. Let me check if it's running.",
        timestamp=_ts(5),
    )
    capture.record_command(
        "systemctl status payments-service",
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        "Active: inactive (dead) since 2026-05-31 10:00:00 UTC",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_command(
        "systemctl start payments-service && sleep 3 && curl -s http://payments.internal:8080/health",
        timestamp=_ts(8),
    )
    capture.record_tool_result(
        '{"status": "healthy", "uptime": 3}',
        tool_name="bash",
        timestamp=_ts(9),
    )
    capture.record_final_answer(
        "The payment service was down. Restarted it and verified health check passes.",
        timestamp=_ts(10),
    )
    capture.record_task_complete(timestamp=_ts(11))
    return "success"


def run_coding_duplicate_error_no_recovery(capture: HarnessTraceCapture) -> str:
    """Coding task: same error repeated, agent gives up."""
    capture.record_model_message(
        "I need to fix the failing unit tests for the calculator module.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "pytest tests/test_calculator.py -v",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "ModuleNotFoundError: No module named 'calculator'",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_tool_call(
        "pip install calculator && pytest tests/test_calculator.py -v",
        tool_name="bash",
        timestamp=_ts(3),
    )
    capture.record_tool_result(
        "ModuleNotFoundError: No module named 'calculator'",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_final_answer(
        "Unable to resolve the missing calculator module. The module may need to be created or the import path may be incorrect.",
        timestamp=_ts(5),
    )
    capture.record_task_complete(timestamp=_ts(6))
    return "failure"


def run_coding_final_turn_only_error(capture: HarnessTraceCapture) -> str:
    """Coding task: success, but last-second error on final turn during cleanup."""
    capture.record_model_message(
        "I need to refactor the calculator module and then clean up.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "cat api/server.py",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "def index(): ...",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_tool_call(
        "pytest tests/test_calculator.py",
        tool_name="bash",
        timestamp=_ts(3),
    )
    capture.record_tool_result(
        "2 passed in 0.1s",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_model_message(
        "All tests pass. Now I'll clean up the temporary directory.",
        timestamp=_ts(5),
    )
    capture.record_tool_call(
        "rm -rf tmp_test_dir/",
        tool_name="bash",
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        "bash: rm: command not found",
        tool_name="bash",
        timestamp=_ts(7),
        settlement_signals={"error_detected": True},
    )
    capture.record_final_answer(
        "Refactored successfully, but cleanup command failed.",
        timestamp=_ts(8),
    )
    capture.record_task_complete(timestamp=_ts(9))
    return "success"


def run_debugging_test_failure_with_changed_strategy(capture: HarnessTraceCapture) -> str:
    """Debugging task: test fails, agent revises strategy, second failure occurs under revision."""
    capture.record_model_message(
        "Let me run the database tests.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "pytest tests/test_db.py",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "FAILED tests/test_db.py - ConnectionError: could not connect to server",
        tool_name="bash",
        timestamp=_ts(2),
        settlement_signals={"error_detected": True},
    )
    capture.record_strategy_revision(
        "Revised plan: The connection is failing. Let me check the environment config to see if PORT is wrong.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "cat config/settings.py",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "DB_PORT = 5432",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_tool_call(
        "pytest tests/test_db.py",
        tool_name="bash",
        timestamp=_ts(6),
    )
    capture.record_tool_result(
        "FAILED tests/test_db.py - ConnectionError: database settings failed",
        tool_name="bash",
        timestamp=_ts(7),
        settlement_signals={"error_detected": True},
    )
    capture.record_final_answer(
        "Database tests failed consistently due to settings error.",
        timestamp=_ts(8),
    )
    capture.record_task_complete(timestamp=_ts(9))
    return "failure"


def run_api_tool_error_changed_arguments(capture: HarnessTraceCapture) -> str:
    """API task: invalid args fail, model retries with fixed arguments (adaptive recovery)."""
    capture.record_model_message(
        "Let's fetch payment records.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "curl http://api.payments.com/records",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "HTTP 401 Unauthorized: missing API Key",
        tool_name="bash",
        timestamp=_ts(2),
        settlement_signals={"error_detected": True},
    )
    capture.record_model_message(
        "Ah, I missed the header. Retrying with auth header.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "curl -H 'Authorization: Bearer secret' http://api.payments.com/records",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "HTTP 400 Bad Request: missing required query parameter 'limit'",
        tool_name="bash",
        timestamp=_ts(5),
        settlement_signals={"error_detected": True},
    )
    capture.record_model_message(
        "Now I need to add query parameters.",
        timestamp=_ts(6),
    )
    capture.record_tool_call(
        "curl -H 'Authorization: Bearer secret' http://api.payments.com/records?limit=10",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_tool_result(
        "HTTP 200 OK: fetched 10 records",
        tool_name="bash",
        timestamp=_ts(8),
        settlement_signals={"success_signal": True},
    )
    capture.record_final_answer(
        "Successfully fetched payment records after fixing headers and arguments.",
        timestamp=_ts(9),
    )
    capture.record_task_complete(timestamp=_ts(10))
    return "success"


def run_file_edit_error_same_path(capture: HarnessTraceCapture) -> str:
    """File edit task: edit syntax error, same non-adaptive retry -> fire!"""
    capture.record_model_message(
        "I need to edit the server file.",
        timestamp=_ts(0),
    )
    capture.record_file_edit(
        "Add print inside server.py",
        timestamp=_ts(1),
    )
    capture.record_tool_call(
        "python server.py",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_tool_result(
        "SyntaxError: invalid syntax inside print statement",
        tool_name="bash",
        timestamp=_ts(3),
        settlement_signals={"error_detected": True},
    )
    capture.record_model_message(
        "Let me run it again to make sure it's consistent.",
        timestamp=_ts(4),
    )
    capture.record_tool_call(
        "python server.py",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_tool_result(
        "SyntaxError: unmatched parenthesis inside format string",
        tool_name="bash",
        timestamp=_ts(6),
        settlement_signals={"error_detected": True},
    )
    capture.record_final_answer(
        "Failed to edit server.py successfully.",
        timestamp=_ts(7),
    )
    capture.record_task_complete(timestamp=_ts(8))
    return "failure"


def run_coding_repeated_error_same_path_3(capture: HarnessTraceCapture) -> str:
    """Coding task: distinct C linking errors, non-adaptive same-path continuation -> fire!"""
    capture.record_model_message(
        "Let's link the binary.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "gcc -o app main.o utils.o",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "LinkError: undefined reference to 'helper_func'",
        tool_name="bash",
        timestamp=_ts(2),
        settlement_signals={"error_detected": True},
    )
    capture.record_model_message(
        "Let me try linking again with basic helper library.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "gcc -o app main.o utils.o -lhelper",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "LinkError: cannot find -lhelper",
        tool_name="bash",
        timestamp=_ts(5),
        settlement_signals={"error_detected": True},
    )
    capture.record_final_answer(
        "Linking failed completely.",
        timestamp=_ts(6),
    )
    capture.record_task_complete(timestamp=_ts(7))
    return "failure"


def run_shell_error_diagnostic_recovery(capture: HarnessTraceCapture) -> str:
    """Shell command fails, model runs diagnostic command, then fixes it."""
    capture.record_model_message(
        "Starting the application service.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "./start.sh",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "Permission denied: ./start.sh",
        tool_name="bash",
        timestamp=_ts(2),
        settlement_signals={"error_detected": True},
    )
    capture.record_model_message(
        "Let me check the permissions on the startup script.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "ls -la ./start.sh",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "-rw-r--r-- 1 user group 123 May 31 10:00 ./start.sh",
        tool_name="bash",
        timestamp=_ts(5),
    )
    capture.record_model_message(
        "Ah, it needs executable permissions. Let me chmod and retry.",
        timestamp=_ts(6),
    )
    capture.record_tool_call(
        "chmod +x ./start.sh && ./start.sh",
        tool_name="bash",
        timestamp=_ts(7),
    )
    capture.record_tool_result(
        "Service started on port 8080",
        tool_name="bash",
        timestamp=_ts(8),
        settlement_signals={"success_signal": True},
    )
    capture.record_final_answer(
        "Successfully started application service after diagnosing and correcting permissions.",
        timestamp=_ts(9),
    )
    capture.record_task_complete(timestamp=_ts(10))
    return "success"


def run_coding_repeated_error_same_path(capture: HarnessTraceCapture) -> str:
    """Coding task: repeated compilation error, non-adaptive same-path continuation -> fire!"""
    capture.record_model_message(
        "I need to compile the C module.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "gcc -o app main.c",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "main.c:1:10: fatal error: foo.h: No such file or directory",
        tool_name="bash",
        timestamp=_ts(2),
        settlement_signals={"error_detected": True},
    )
    capture.record_model_message(
        "Let me just try compiling again with basic flags.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "gcc -o app main.c -I.",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "main.c:4:12: error: unknown type name 'bar_t'",
        tool_name="bash",
        timestamp=_ts(5),
        settlement_signals={"error_detected": True},
    )
    capture.record_final_answer(
        "Compilation failed due to missing foo.h header.",
        timestamp=_ts(6),
    )
    capture.record_task_complete(timestamp=_ts(7))
    return "failure"


def run_coding_clean_success_2(capture: HarnessTraceCapture) -> str:
    """Coding task: second clean success, zero errors."""
    capture.record_model_message(
        "Let's list the workspace directory structure.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "ls -F",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "app/  config/  tests/  README.md",
        tool_name="bash",
        timestamp=_ts(2),
    )
    capture.record_final_answer(
        "Workspace listed successfully with no errors.",
        timestamp=_ts(3),
    )
    capture.record_task_complete(timestamp=_ts(4))
    return "success"


def run_debugging_single_error_recovery(capture: HarnessTraceCapture) -> str:
    """Debugging task: single connection refused error, model starts DB and succeeds."""
    capture.record_model_message(
        "I need to run the app DB check.",
        timestamp=_ts(0),
    )
    capture.record_tool_call(
        "pg_isready",
        tool_name="bash",
        timestamp=_ts(1),
    )
    capture.record_tool_result(
        "no response -- connection refused",
        tool_name="bash",
        timestamp=_ts(2),
        settlement_signals={"error_detected": True},
    )
    capture.record_model_message(
        "Postgres is not running. Let me start it using systemctl.",
        timestamp=_ts(3),
    )
    capture.record_tool_call(
        "systemctl start postgresql && pg_isready",
        tool_name="bash",
        timestamp=_ts(4),
    )
    capture.record_tool_result(
        "accepting connections on port 5432",
        tool_name="bash",
        timestamp=_ts(5),
        settlement_signals={"success_signal": True},
    )
    capture.record_final_answer(
        "Postgres was started and verified successfully.",
        timestamp=_ts(6),
    )
    capture.record_task_complete(timestamp=_ts(7))
    return "success"


# ── Scenario Registry ──

SCENARIOS: list[dict[str, Any]] = [
    {
        "run_id": "baseline-001-coding-import-error-same-path",
        "task_description": "Fix authentication module import errors by running tests",
        "domain": "code",
        "task_type": "coding",
        "runner": run_coding_import_error_same_path,
    },
    {
        "run_id": "baseline-002-debugging-test-failures-revision",
        "task_description": "Debug payment processing test failures",
        "domain": "code",
        "task_type": "debugging",
        "runner": run_debugging_test_failures_with_revision,
    },
    {
        "run_id": "baseline-003-shell-permission-denied",
        "task_description": "Deploy application to staging server via SCP",
        "domain": "shell",
        "task_type": "shell",
        "runner": run_shell_permission_denied_then_success,
    },
    {
        "run_id": "baseline-004-test-running-flaky-timeouts",
        "task_description": "Run integration test suite for release verification",
        "domain": "code",
        "task_type": "test_running",
        "runner": run_test_running_flaky_tests,
    },
    {
        "run_id": "baseline-005-file-edit-syntax-error",
        "task_description": "Add input validation to user registration handler",
        "domain": "code",
        "task_type": "file_edit",
        "runner": run_file_edit_syntax_error_recovery,
    },
    {
        "run_id": "baseline-006-api-rate-limiting",
        "task_description": "Fetch user data from external API for 500 users",
        "domain": "api",
        "task_type": "api_tool_use",
        "runner": run_api_tool_use_rate_limiting,
    },
    {
        "run_id": "baseline-007-coding-type-error-inspection",
        "task_description": "Refactor data processing pipeline for None handling",
        "domain": "code",
        "task_type": "coding",
        "runner": run_coding_type_error_inspection,
    },
    {
        "run_id": "baseline-008-debugging-missing-dependency",
        "task_description": "Fix CI build failure due to missing numpy dependency",
        "domain": "code",
        "task_type": "debugging",
        "runner": run_debugging_missing_dependency,
    },
    {
        "run_id": "baseline-009-shell-disk-full",
        "task_description": "Build Docker image for microservice",
        "domain": "shell",
        "task_type": "shell",
        "runner": run_shell_disk_full_error,
    },
    {
        "run_id": "baseline-010-coding-clean-success",
        "task_description": "Add health check endpoint to API server",
        "domain": "code",
        "task_type": "coding",
        "runner": run_coding_clean_success,
    },
    {
        "run_id": "baseline-011-test-running-mixed-results",
        "task_description": "Run complete test suite before release",
        "domain": "code",
        "task_type": "test_running",
        "runner": run_test_running_mixed_results,
    },
    {
        "run_id": "baseline-012-api-connection-refused",
        "task_description": "Verify payment gateway integration",
        "domain": "api",
        "task_type": "api_tool_use",
        "runner": run_api_tool_use_connection_refused,
    },
    {
        "run_id": "baseline-013-coding-duplicate-error-no-recovery",
        "task_description": "Fix failing unit tests for calculator module",
        "domain": "code",
        "task_type": "coding",
        "runner": run_coding_duplicate_error_no_recovery,
    },
    {
        "run_id": "baseline-014-coding-final-turn-only-error",
        "task_description": "Verify calculator and clean up temporary directory",
        "domain": "code",
        "task_type": "coding",
        "runner": run_coding_final_turn_only_error,
    },
    {
        "run_id": "baseline-015-debugging-test-failure-changed-strategy",
        "task_description": "Run and debug database connection tests",
        "domain": "code",
        "task_type": "debugging",
        "runner": run_debugging_test_failure_with_changed_strategy,
    },
    {
        "run_id": "baseline-016-api-tool-changed-arguments",
        "task_description": "Fetch payment records from internal API endpoint",
        "domain": "api",
        "task_type": "api_tool_use",
        "runner": run_api_tool_error_changed_arguments,
    },
    {
        "run_id": "baseline-017-file-edit-error-same-path",
        "task_description": "Edit server configuration print statements",
        "domain": "code",
        "task_type": "file_edit",
        "runner": run_file_edit_error_same_path,
    },
    {
        "run_id": "baseline-018-shell-error-diagnostic-recovery",
        "task_description": "Diagnose permissions and start system app script",
        "domain": "shell",
        "task_type": "shell",
        "runner": run_shell_error_diagnostic_recovery,
    },
    {
        "run_id": "baseline-019-coding-repeated-error-same-path",
        "task_description": "Compile high-performance C extension module",
        "domain": "code",
        "task_type": "coding",
        "runner": run_coding_repeated_error_same_path,
    },
    {
        "run_id": "baseline-020-coding-clean-success-2",
        "task_description": "Verify workspace structure without errors",
        "domain": "code",
        "task_type": "coding",
        "runner": run_coding_clean_success_2,
    },
    {
        "run_id": "baseline-021-debugging-single-error-recovery",
        "task_description": "Check database status and ensure postgres is running",
        "domain": "code",
        "task_type": "debugging",
        "runner": run_debugging_single_error_recovery,
    },
    {
        "run_id": "baseline-022-coding-repeated-error-same-path-3",
        "task_description": "Link executable application binary",
        "domain": "code",
        "task_type": "coding",
        "runner": run_coding_repeated_error_same_path_3,
    },
]


def collect_baseline(
    output_dir: str,
    scenarios: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Run all baseline scenarios and collect traces."""
    scenarios = scenarios or SCENARIOS
    results: list[dict[str, Any]] = []

    for scenario in scenarios:
        run_id = scenario["run_id"]
        print(f"Collecting: {run_id} ({scenario['task_type']})")

        capture = HarnessTraceCapture(
            run_id,
            enabled=True,
            trace_dir=output_dir,
            run_metadata={
                "task_id": run_id,
                "domain": scenario["domain"],
                "task_type": scenario["task_type"],
                "desired_direction": scenario["task_description"],
                "baseline_pass": True,
                "policy_mode": "shadow_only",
                "activation_enabled": False,
            },
        )

        final_outcome = scenario["runner"](capture)

        settlement_quality = "unknown"
        if final_outcome == "success":
            settlement_quality = "recovered_success"
            # Check if there were errors
            if any(
                e["settlement_signals"].get("error_detected") for e in capture.events
            ):
                settlement_quality = "recovered_success"
            else:
                settlement_quality = "clean_success"
        elif final_outcome == "failure":
            error_events = [
                e
                for e in capture.events
                if e["settlement_signals"].get("error_detected")
            ]
            if error_events:
                settlement_quality = "failure_with_signal"
            else:
                settlement_quality = "failure_without_signal"

        summary = capture.finalize_run(
            final_outcome=final_outcome,
            settlement_quality=settlement_quality,
        )

        results.append(
            {
                "run_id": run_id,
                "task_type": scenario["task_type"],
                "domain": scenario["domain"],
                "total_steps": summary["total_steps"],
                "error_count": summary["error_count"],
                "final_outcome": final_outcome,
                "settlement_quality": settlement_quality,
            }
        )
        print(
            f"  -> {summary['total_steps']} steps, {summary['error_count']} errors, {final_outcome}"
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect baseline live harness traces for policy evidence"
    )
    parser.add_argument(
        "--output-dir",
        default="data/settlement_datasets/live_harness_traces",
        help="Output directory for captured traces",
    )
    args = parser.parse_args()

    print(f"Collecting {len(SCENARIOS)} baseline traces...")
    print(f"Output directory: {args.output_dir}")
    print(f"Policy mode: shadow_only (no activation, no enforcement)")
    print()

    results = collect_baseline(args.output_dir)

    print()
    print(f"Collected {len(results)} baseline traces")
    successes = sum(1 for r in results if r["final_outcome"] == "success")
    failures = sum(1 for r in results if r["final_outcome"] == "failure")
    print(f"Outcomes: {successes} success, {failures} failure")

    # Write collection manifest
    manifest_path = Path(args.output_dir) / "baseline_collection_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "collected_at": datetime.now(UTC).isoformat(),
        "total_runs": len(results),
        "policy_mode": "shadow_only",
        "activation_enabled": False,
        "runs": results,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Manifest -> {manifest_path}")


if __name__ == "__main__":
    main()
