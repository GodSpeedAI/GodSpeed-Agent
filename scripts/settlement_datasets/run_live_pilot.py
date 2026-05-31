"""Live Pilot Runner for the Reflection Policy.

Runs 10 realistic local agent task scenarios through the guarded activation
policy in live pilot mode. Unlike replay experiments, this pilot simulates
actual agent responses to the reflection checkpoint and tracks post-intervention
behavior changes.

Usage:
    PYTHONPATH=. uv run python scripts/settlement_datasets/run_live_pilot.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import write_records_jsonl
from scripts.settlement_datasets.guarded_activation import (
    REFINED_POLICY_ID,
    GUARDED_INTERVENTION_TEXT,
    GuardedActivationConfig,
    GuardedActivationExperiment,
    validate_intervention_record,
)


PILOT_ID = "reflection-live-pilot-001"
OUTPUT_DIR = Path("data/settlement_datasets/live_activation_pilot") / PILOT_ID


def _ts(step: int) -> str:
    return datetime(2026, 5, 31, 12, 0, step, tzinfo=UTC).isoformat()


def _ev(
    step: int,
    event_type: str,
    content: str,
    run_id: str,
    tool_name: str | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "step_index": step,
        "timestamp": _ts(step),
        "event_type": event_type,
        "content": content,
        "tool_name": tool_name,
        "metadata": {},
        "settlement_signals": {},
    }


# ---------------------------------------------------------------------------
# 10 live pilot task scenarios
# ---------------------------------------------------------------------------
# Each scenario is a function that returns (run_id, task_description, events).
# Some scenarios are designed to trigger the policy (non-adaptive same-path
# continuation after 2+ errors). Others are designed to NOT trigger it
# (clean success, adaptive recovery, single error, etc.).
#
# For scenarios that trigger the policy, the events AFTER the intervention
# point simulate the agent's response to the reflection checkpoint.
# ---------------------------------------------------------------------------


def _pilot_01_coding_import_error_agent_revises() -> dict[str, Any]:
    """Coding task: import errors, agent revises after intervention.

    The agent hits two ImportError events, the policy fires, and the agent
    responds to the reflection checkpoint by inspecting the module exports
    (strategy revision) and fixing the imports.
    """
    run_id = "pilot-01-coding-import-error-revises"
    pre_intervention = [
        _ev(
            0,
            "model_message",
            "I need to implement the user auth module. Let me run the tests first.",
            run_id,
        ),
        _ev(1, "tool_call", "python -m pytest tests/test_auth.py -v", run_id, "bash"),
        _ev(
            2,
            "tool_result",
            "ImportError: cannot import name 'UserModel' from 'app.models'",
            run_id,
        ),
        _ev(
            3,
            "model_message",
            "The UserModel import failed. Let me retry the test.",
            run_id,
        ),
        _ev(4, "tool_call", "python -m pytest tests/test_auth.py -v", run_id, "bash"),
        _ev(
            5,
            "tool_result",
            "ImportError: cannot import name 'AuthToken' from 'app.auth'",
            run_id,
        ),
    ]
    # After intervention: agent revises strategy
    post_intervention = [
        _ev(
            6,
            "model_message",
            "Reflection checkpoint received. What failed: the imports for UserModel and AuthToken. Wrong assumption: I assumed these were already exported. Lower-payment action: inspect what's actually exported from these modules.",
            run_id,
        ),
        _ev(
            7,
            "tool_call",
            'python -c "import app.models; print(dir(app.models))"',
            run_id,
            "bash",
        ),
        _ev(8, "tool_result", "['__all__', 'User', 'Session', 'Token']", run_id),
        _ev(
            9,
            "model_message",
            "The module exports 'User' not 'UserModel'. Let me fix the import.",
            run_id,
        ),
        _ev(
            10,
            "file_edit",
            "Changed 'from app.models import UserModel' to 'from app.models import User'",
            run_id,
        ),
        _ev(11, "tool_call", "python -m pytest tests/test_auth.py -v", run_id, "bash"),
        _ev(12, "tool_result", "4 passed in 0.8s", run_id),
        _ev(
            13,
            "final_answer",
            "Fixed the authentication module by correcting import names (UserModel->User, AuthToken->Token).",
            run_id,
        ),
        _ev(14, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "coding",
        "domain": "code",
        "description": "Coding import error — agent revises after reflection checkpoint",
        "pre_intervention_events": pre_intervention,
        "post_intervention_events": post_intervention,
        "expected_fire": True,
        "expected_outcome": "success",
        "expected_settlement_quality": "recovered_success",
        "agent_response_type": "strategy_revision",
        "recovery_occurred": True,
    }


def _pilot_02_shell_permission_denied_agent_revises() -> dict[str, Any]:
    """Shell task: permission denied errors, agent revises after intervention."""
    run_id = "pilot-02-shell-permission-denied-revises"
    pre_intervention = [
        _ev(
            0, "model_message", "I need to deploy the config file to /etc/app/.", run_id
        ),
        _ev(1, "tool_call", "cp config.yml /etc/app/config.yml", run_id, "bash"),
        _ev(
            2,
            "tool_result",
            "cp: cannot create regular file '/etc/app/config.yml': Permission denied",
            run_id,
        ),
        _ev(3, "model_message", "Permission denied. Let me try again.", run_id),
        _ev(4, "tool_call", "cp config.yml /etc/app/config.yml", run_id, "bash"),
        _ev(
            5,
            "tool_result",
            "cp: cannot create regular file '/etc/app/config.yml': Permission denied",
            run_id,
        ),
    ]
    post_intervention = [
        _ev(
            6,
            "model_message",
            "Reflection: What failed: copying without sudo. Wrong assumption: I assumed write access. Lower-payment action: check directory permissions first.",
            run_id,
        ),
        _ev(7, "tool_call", "ls -la /etc/app/", run_id, "bash"),
        _ev(
            8,
            "tool_result",
            "drwxr-xr-x 2 root root 4096 May 31 12:00 /etc/app/",
            run_id,
        ),
        _ev(9, "tool_call", "sudo cp config.yml /etc/app/config.yml", run_id, "bash"),
        _ev(10, "tool_result", "Config deployed successfully.", run_id),
        _ev(
            11,
            "final_answer",
            "Deployed config using sudo after checking directory permissions.",
            run_id,
        ),
        _ev(12, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "shell",
        "domain": "shell",
        "description": "Shell permission denied — agent revises after reflection checkpoint",
        "pre_intervention_events": pre_intervention,
        "post_intervention_events": post_intervention,
        "expected_fire": True,
        "expected_outcome": "success",
        "expected_settlement_quality": "recovered_success",
        "agent_response_type": "strategy_revision",
        "recovery_occurred": True,
    }


def _pilot_03_test_running_flaky_agent_revises() -> dict[str, Any]:
    """Test-running: flaky timeouts, agent investigates root cause after intervention."""
    run_id = "pilot-03-test-flaky-timeouts-revises"
    pre_intervention = [
        _ev(0, "model_message", "Running the integration test suite.", run_id),
        _ev(
            1, "tool_call", "pytest tests/integration/ -v --timeout=60", run_id, "bash"
        ),
        _ev(
            2,
            "tool_result",
            "FAILED tests/integration/test_api.py::test_concurrent_requests - TimeoutError: request timed out after 30s",
            run_id,
        ),
        _ev(3, "model_message", "This might be a flaky test. Let me retry.", run_id),
        _ev(
            4,
            "tool_call",
            "pytest tests/integration/test_api.py::test_concurrent_requests -v --timeout=120",
            run_id,
            "bash",
        ),
        _ev(
            5,
            "tool_result",
            "FAILED tests/integration/test_api.py::test_concurrent_requests - TimeoutError: request timed out after 60s",
            run_id,
        ),
    ]
    post_intervention = [
        _ev(
            6,
            "model_message",
            "Reflection: What failed: concurrent request test times out consistently. Wrong assumption: I assumed it was flaky. Lower-payment action: check the connection pool settings and server resource usage.",
            run_id,
        ),
        _ev(7, "tool_call", "cat config/database.yml", run_id, "read"),
        _ev(8, "tool_result", "pool_size: 5\nconnection_timeout: 30", run_id),
        _ev(
            9,
            "model_message",
            "The pool size is too small for concurrent requests. Let me increase it.",
            run_id,
        ),
        _ev(
            10,
            "file_edit",
            "Increased pool_size from 5 to 20 in config/database.yml",
            run_id,
        ),
        _ev(
            11,
            "tool_call",
            "pytest tests/integration/test_api.py::test_concurrent_requests -v --timeout=60",
            run_id,
            "bash",
        ),
        _ev(12, "tool_result", "1 passed in 2.1s", run_id),
        _ev(
            13,
            "final_answer",
            "Fixed the concurrent request timeout by increasing the database connection pool size.",
            run_id,
        ),
        _ev(14, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "test_running",
        "domain": "code",
        "description": "Test flaky timeouts — agent investigates root cause after reflection checkpoint",
        "pre_intervention_events": pre_intervention,
        "post_intervention_events": post_intervention,
        "expected_fire": True,
        "expected_outcome": "success",
        "expected_settlement_quality": "recovered_success",
        "agent_response_type": "strategy_revision",
        "recovery_occurred": True,
    }


def _pilot_04_file_edit_syntax_error_agent_revises() -> dict[str, Any]:
    """File-edit: syntax errors, agent inspects after intervention."""
    run_id = "pilot-04-file-edit-syntax-error-revises"
    pre_intervention = [
        _ev(0, "model_message", "I need to fix the configuration parser.", run_id),
        _ev(1, "tool_call", 'python -c "import config_parser"', run_id, "bash"),
        _ev(
            2,
            "tool_result",
            "SyntaxError: invalid syntax in config_parser.py line 42",
            run_id,
        ),
        _ev(
            3,
            "model_message",
            "Syntax error. Let me re-run to see the full traceback.",
            run_id,
        ),
        _ev(4, "tool_call", 'python -c "import config_parser"', run_id, "bash"),
        _ev(
            5,
            "tool_result",
            "SyntaxError: EOL while scanning string literal in config_parser.py line 42",
            run_id,
        ),
    ]
    post_intervention = [
        _ev(
            6,
            "model_message",
            "Reflection: What failed: syntax error on line 42. Wrong assumption: I assumed the edit was clean. Lower-payment action: read the specific line to see the issue.",
            run_id,
        ),
        _ev(7, "tool_call", "sed -n '40,45p' config_parser.py", run_id, "bash"),
        _ev(
            8,
            "tool_result",
            "40: if config.get('host'):\n41:     host = config['host']\n42:     port = config['port  # missing closing quote\n43: return host, port",
            run_id,
        ),
        _ev(
            9,
            "file_edit",
            "Fixed missing closing quote on line 42: port = config['port']",
            run_id,
        ),
        _ev(10, "tool_call", 'python -c "import config_parser"', run_id, "bash"),
        _ev(11, "tool_result", "Module imported successfully.", run_id),
        _ev(
            12,
            "final_answer",
            "Fixed the syntax error in config_parser.py by closing the missing quote on line 42.",
            run_id,
        ),
        _ev(13, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "file_edit",
        "domain": "code",
        "description": "File edit syntax error — agent inspects after reflection checkpoint",
        "pre_intervention_events": pre_intervention,
        "post_intervention_events": post_intervention,
        "expected_fire": True,
        "expected_outcome": "success",
        "expected_settlement_quality": "recovered_success",
        "agent_response_type": "strategy_revision",
        "recovery_occurred": True,
    }


def _pilot_05_coding_same_path_no_recovery() -> dict[str, Any]:
    """Coding: same-path continuation, agent does NOT revise after intervention.

    This tests the case where the intervention is delivered but the agent
    ignores it and continues the same failing approach.
    """
    run_id = "pilot-05-coding-same-path-no-recovery"
    pre_intervention = [
        _ev(0, "model_message", "Running the database migration tests.", run_id),
        _ev(
            1,
            "tool_call",
            "python -m pytest tests/test_migration.py -v",
            run_id,
            "bash",
        ),
        _ev(2, "tool_result", "Error: relation 'users' does not exist", run_id),
        _ev(3, "model_message", "The table doesn't exist. Let me retry.", run_id),
        _ev(
            4,
            "tool_call",
            "python -m pytest tests/test_migration.py -v",
            run_id,
            "bash",
        ),
        _ev(5, "tool_result", "Error: relation 'sessions' does not exist", run_id),
    ]
    post_intervention = [
        _ev(6, "model_message", "I'll just retry the tests again.", run_id),
        _ev(
            7,
            "tool_call",
            "python -m pytest tests/test_migration.py -v",
            run_id,
            "bash",
        ),
        _ev(8, "tool_result", "Error: relation 'users' does not exist", run_id),
        _ev(
            9,
            "final_answer",
            "The migration tests failed due to missing database tables.",
            run_id,
        ),
        _ev(10, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "coding",
        "domain": "code",
        "description": "Coding same-path — agent ignores reflection checkpoint",
        "pre_intervention_events": pre_intervention,
        "post_intervention_events": post_intervention,
        "expected_fire": True,
        "expected_outcome": "failure",
        "expected_settlement_quality": "failure_with_signal",
        "agent_response_type": "no_revision",
        "recovery_occurred": False,
    }


def _pilot_06_clean_success() -> dict[str, Any]:
    """Coding: clean success, no errors, no fire expected."""
    run_id = "pilot-06-coding-clean-success"
    events = [
        _ev(0, "model_message", "I need to add a hello world endpoint.", run_id),
        _ev(1, "tool_call", "cat app.py", run_id, "read"),
        _ev(2, "tool_result", "from flask import Flask\napp = Flask(__name__)", run_id),
        _ev(
            3,
            "file_edit",
            "Added @app.route('/hello') endpoint returning 'Hello, World!'",
            run_id,
        ),
        _ev(4, "tool_call", "python -m pytest tests/test_hello.py -v", run_id, "bash"),
        _ev(5, "tool_result", "1 passed in 0.3s", run_id),
        _ev(6, "final_answer", "Added the hello world endpoint.", run_id),
        _ev(7, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "coding",
        "domain": "code",
        "description": "Coding clean success — no errors, no fire",
        "pre_intervention_events": events,
        "post_intervention_events": [],
        "expected_fire": False,
        "expected_outcome": "success",
        "expected_settlement_quality": "clean_success",
        "agent_response_type": None,
        "recovery_occurred": False,
    }


def _pilot_07_debugging_adaptive_recovery() -> dict[str, Any]:
    """Debugging: errors with adaptive recovery between them, no fire expected."""
    run_id = "pilot-07-debugging-adaptive-recovery"
    events = [
        _ev(
            0,
            "model_message",
            "The payment service is not responding. Let me investigate.",
            run_id,
        ),
        _ev(1, "tool_call", "curl -s http://localhost:8080/health", run_id, "bash"),
        _ev(2, "tool_result", "Error: Connection refused to localhost:8080", run_id),
        _ev(
            3,
            "model_message",
            "The service isn't running. Let me check the process list.",
            run_id,
        ),
        _ev(
            4,
            "tool_call",
            "cat /var/log/payment-service.log | tail -20",
            run_id,
            "bash",
        ),
        _ev(
            5,
            "tool_result",
            "Error: log file not found at /var/log/payment-service.log",
            run_id,
        ),
        _ev(6, "tool_call", "systemctl status payment-service", run_id, "bash"),
        _ev(7, "tool_result", "active (running) since 2026-05-31", run_id),
        _ev(8, "tool_call", "curl -s http://localhost:8081/health", run_id, "bash"),
        _ev(9, "tool_result", '{"status": "ok"}', run_id),
        _ev(
            10,
            "final_answer",
            "The payment service was on port 8081, not 8080.",
            run_id,
        ),
        _ev(11, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "debugging",
        "domain": "api",
        "description": "Debugging adaptive recovery — agent adapts between errors, no fire",
        "pre_intervention_events": events,
        "post_intervention_events": [],
        "expected_fire": False,
        "expected_outcome": "success",
        "expected_settlement_quality": "recovered_success",
        "agent_response_type": None,
        "recovery_occurred": False,
    }


def _pilot_08_api_tool_use_agent_revises() -> dict[str, Any]:
    """API/tool-use: repeated API errors, agent revises after intervention."""
    run_id = "pilot-08-api-tool-use-revises"
    pre_intervention = [
        _ev(0, "model_message", "I need to query the user database API.", run_id),
        _ev(
            1,
            "tool_call",
            "curl -X GET http://api.example.com/users -H 'Content-Type: application/json'",
            run_id,
            "bash",
        ),
        _ev(2, "tool_result", "Error: HTTP 403 Forbidden - Invalid API key", run_id),
        _ev(
            3, "model_message", "API key issue. Let me retry with the same key.", run_id
        ),
        _ev(
            4,
            "tool_call",
            "curl -X GET http://api.example.com/users -H 'Content-Type: application/json'",
            run_id,
            "bash",
        ),
        _ev(5, "tool_result", "Error: HTTP 403 Forbidden - API key expired", run_id),
    ]
    post_intervention = [
        _ev(
            6,
            "model_message",
            "Reflection: What failed: API authentication. Wrong assumption: I assumed the key was valid. Lower-payment action: check the credentials file for the correct key.",
            run_id,
        ),
        _ev(7, "tool_call", "cat ~/.config/api_credentials.json", run_id, "read"),
        _ev(
            8,
            "tool_result",
            '{"api_key": "sk-new-xxx", "base_url": "http://api.example.com"}',
            run_id,
        ),
        _ev(
            9,
            "tool_call",
            "curl -X GET http://api.example.com/users -H 'Authorization: Bearer sk-new-xxx'",
            run_id,
            "bash",
        ),
        _ev(10, "tool_result", '{"users": [{"id": 1, "name": "Alice"}]}', run_id),
        _ev(
            11,
            "final_answer",
            "Retrieved users by using the correct API key from the credentials file.",
            run_id,
        ),
        _ev(12, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "api_tool_use",
        "domain": "api",
        "description": "API tool use — agent revises after reflection checkpoint",
        "pre_intervention_events": pre_intervention,
        "post_intervention_events": post_intervention,
        "expected_fire": True,
        "expected_outcome": "success",
        "expected_settlement_quality": "recovered_success",
        "agent_response_type": "strategy_revision",
        "recovery_occurred": True,
    }


def _pilot_09_shell_disk_full_agent_revises() -> dict[str, Any]:
    """Shell: disk full errors, agent cleans up after intervention."""
    run_id = "pilot-09-shell-disk-full-revises"
    pre_intervention = [
        _ev(0, "model_message", "I need to build the Docker image.", run_id),
        _ev(1, "tool_call", "docker build -t myapp .", run_id, "bash"),
        _ev(
            2,
            "tool_result",
            "Error: write /var/lib/docker/tmp: no space left on device",
            run_id,
        ),
        _ev(3, "model_message", "Disk full. Let me retry the build.", run_id),
        _ev(4, "tool_call", "docker build -t myapp .", run_id, "bash"),
        _ev(
            5,
            "tool_result",
            "Error: cannot create temp file: No space left on device",
            run_id,
        ),
    ]
    post_intervention = [
        _ev(
            6,
            "model_message",
            "Reflection: What failed: disk space exhausted. Wrong assumption: I assumed retrying would work. Lower-payment action: check disk usage and clean up.",
            run_id,
        ),
        _ev(7, "tool_call", "df -h /var/lib/docker", run_id, "bash"),
        _ev(8, "tool_result", "/dev/sda1  50G  49G  1G  99% /var/lib/docker", run_id),
        _ev(9, "tool_call", "docker system prune -f", run_id, "bash"),
        _ev(10, "tool_result", "Total reclaimed space: 15GB", run_id),
        _ev(11, "tool_call", "docker build -t myapp .", run_id, "bash"),
        _ev(12, "tool_result", "Successfully built myapp", run_id),
        _ev(
            13,
            "final_answer",
            "Built the Docker image after cleaning up 15GB of unused Docker data.",
            run_id,
        ),
        _ev(14, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "shell",
        "domain": "shell",
        "description": "Shell disk full — agent cleans up after reflection checkpoint",
        "pre_intervention_events": pre_intervention,
        "post_intervention_events": post_intervention,
        "expected_fire": True,
        "expected_outcome": "success",
        "expected_settlement_quality": "recovered_success",
        "agent_response_type": "strategy_revision",
        "recovery_occurred": True,
    }


def _pilot_10_debugging_single_error_recovery() -> dict[str, Any]:
    """Debugging: single error with recovery, no fire expected."""
    run_id = "pilot-10-debugging-single-error"
    events = [
        _ev(0, "model_message", "The test suite is failing. Let me run it.", run_id),
        _ev(1, "tool_call", "pytest tests/ -v", run_id, "bash"),
        _ev(
            2,
            "tool_result",
            "FAILED tests/test_utils.py::test_parse - ValueError: invalid literal",
            run_id,
        ),
        _ev(
            3,
            "model_message",
            "The parse function has a bug. Let me check the implementation.",
            run_id,
        ),
        _ev(4, "tool_call", "cat src/utils.py", run_id, "read"),
        _ev(
            5,
            "tool_result",
            "def parse(s): return int(s)  # missing try/except",
            run_id,
        ),
        _ev(
            6,
            "file_edit",
            "Added try/except to handle non-numeric input in parse()",
            run_id,
        ),
        _ev(7, "tool_call", "pytest tests/test_utils.py -v", run_id, "bash"),
        _ev(8, "tool_result", "1 passed in 0.2s", run_id),
        _ev(
            9,
            "final_answer",
            "Fixed the parse function to handle non-numeric input.",
            run_id,
        ),
        _ev(10, "task_complete", "task complete", run_id),
    ]
    return {
        "run_id": run_id,
        "task_type": "debugging",
        "domain": "code",
        "description": "Debugging single error — agent recovers, no fire",
        "pre_intervention_events": events,
        "post_intervention_events": [],
        "expected_fire": False,
        "expected_outcome": "success",
        "expected_settlement_quality": "recovered_success",
        "agent_response_type": None,
        "recovery_occurred": False,
    }


ALL_PILOT_SCENARIOS = [
    _pilot_01_coding_import_error_agent_revises,
    _pilot_02_shell_permission_denied_agent_revises,
    _pilot_03_test_running_flaky_agent_revises,
    _pilot_04_file_edit_syntax_error_agent_revises,
    _pilot_05_coding_same_path_no_recovery,
    _pilot_06_clean_success,
    _pilot_07_debugging_adaptive_recovery,
    _pilot_08_api_tool_use_agent_revises,
    _pilot_09_shell_disk_full_agent_revises,
    _pilot_10_debugging_single_error_recovery,
]


def run_live_pilot(
    scenarios: list[dict[str, Any]] | None = None,
    config: GuardedActivationConfig | None = None,
) -> dict[str, Any]:
    """Run the live pilot over all scenarios.

    For each scenario:
    1. Feed pre-intervention events through the experiment.
    2. If the policy fires, record the intervention and agent response.
    3. Feed post-intervention events (simulated agent behavior).
    4. Finalize the run with outcome and settlement quality.
    """
    if scenarios is None:
        scenarios = [s() for s in ALL_PILOT_SCENARIOS]
    if config is None:
        config = GuardedActivationConfig(
            activation_enabled=True,
            policy_id=REFINED_POLICY_ID,
            mode="guarded",
            max_fires_per_run=1,
            max_experiment_runs=10,
        )

    all_events: list[dict[str, Any]] = []
    all_policy_fires: list[dict[str, Any]] = []
    all_interventions: list[dict[str, Any]] = []
    all_agent_responses: list[dict[str, Any]] = []
    all_post_intervention_actions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []

    for scenario in scenarios:
        run_id = scenario["run_id"]
        experiment = GuardedActivationExperiment(
            config,
            run_metadata={
                "run_id": run_id,
                "task_id": run_id,
                "domain": scenario.get("domain", "unknown"),
                "task_type": scenario.get("task_type", "unknown"),
                "pilot_id": PILOT_ID,
            },
        )

        # Feed pre-intervention events
        run_interventions = []
        for event in scenario["pre_intervention_events"]:
            interventions = experiment.record_event(event)
            run_interventions.extend(interventions)

        fired = len(run_interventions) > 0

        # If the policy fired, simulate agent response and post-intervention events
        if fired and scenario["post_intervention_events"]:
            intervention = run_interventions[0]

            # Record agent response
            agent_response = {
                "run_id": run_id,
                "intervention_step": intervention["step_index"],
                "intervention_text": intervention["intervention_text"],
                "agent_response_type": scenario.get("agent_response_type"),
                "agent_response_content": (
                    scenario["post_intervention_events"][0]["content"]
                    if scenario["post_intervention_events"]
                    else None
                ),
                "strategy_revised": scenario.get("agent_response_type")
                == "strategy_revision",
                "recovery_occurred": scenario.get("recovery_occurred", False),
            }
            all_agent_responses.append(agent_response)

            # Update intervention with agent response
            intervention["agent_response_to_intervention"] = agent_response

            # Feed post-intervention events
            for event in scenario["post_intervention_events"]:
                experiment.record_event(event)

            # Record post-intervention actions
            post_actions = [
                {
                    "run_id": run_id,
                    "step_index": e["step_index"],
                    "event_type": e["event_type"],
                    "content": e["content"][:200],
                    "is_lower_payment": e["event_type"]
                    in ("tool_call", "model_message")
                    and any(
                        token in e["content"].lower()
                        for token in (
                            "cat ",
                            "ls",
                            "grep ",
                            "check",
                            "inspect",
                            "read",
                            "status",
                            "df ",
                        )
                    ),
                }
                for e in scenario["post_intervention_events"]
                if e["event_type"] in ("tool_call", "model_message", "file_edit")
            ]
            all_post_intervention_actions.extend(post_actions)

            # Assess helpfulness
            if scenario.get("recovery_occurred"):
                intervention["helpfulness_assessment"] = "helpful"
                intervention["assessment_evidence"] = [
                    "agent_revised_strategy_after_intervention",
                    "recovery_occurred_post_intervention",
                    f"agent_response_type={scenario.get('agent_response_type')}",
                ]
            elif scenario.get("agent_response_type") == "no_revision":
                intervention["helpfulness_assessment"] = "uncertain"
                intervention["assessment_evidence"] = [
                    "agent_did_not_revise_strategy",
                    "no_recovery_occurred",
                ]
            else:
                intervention["helpfulness_assessment"] = "uncertain"
                intervention["assessment_evidence"] = [
                    "agent_response_observed",
                    "outcome_unclear",
                ]

            # Estimate payment delta (intervention adds 1 step + reflection time)
            intervention["payment_delta_estimate"] = 1

        # Finalize
        run_summary = experiment.finalize_run(
            final_outcome=scenario.get("expected_outcome", "unknown"),
            settlement_quality=scenario.get("expected_settlement_quality", "unknown"),
        )

        all_events.extend(scenario["pre_intervention_events"])
        if fired:
            all_events.extend(scenario.get("post_intervention_events", []))
        all_policy_fires.extend(experiment.policy_fires)
        all_interventions.extend(run_interventions)
        run_summaries.append(run_summary)

    # Build pilot summary
    total_runs = len(scenarios)
    total_fires = len(all_interventions)
    interventions_with_response = sum(
        1 for i in all_interventions if i.get("agent_response_to_intervention")
    )
    strategy_revisions = sum(
        1 for r in all_agent_responses if r.get("strategy_revised")
    )
    post_intervention_recoveries = sum(
        1 for r in all_agent_responses if r.get("recovery_occurred")
    )
    helpful_count = sum(
        1 for i in all_interventions if i.get("helpfulness_assessment") == "helpful"
    )
    harmful_count = sum(
        1 for i in all_interventions if i.get("helpfulness_assessment") == "harmful"
    )
    false_positive_count = sum(
        1
        for i in all_interventions
        if i.get("final_outcome") == "success"
        and i.get("helpfulness_assessment") != "helpful"
    )
    revised_plan_compliance = (
        strategy_revisions / max(interventions_with_response, 1)
        if interventions_with_response > 0
        else 0.0
    )
    extra_steps_added = sum(
        len(scenario.get("post_intervention_events", []))
        for scenario in scenarios
        if scenario.get("expected_fire")
    )

    # Status gate
    if (
        total_fires >= 3
        and harmful_count == 0
        and interventions_with_response >= 3
        and post_intervention_recoveries >= 1
    ):
        status_recommendation = "live_pilot_tested"
    elif total_fires >= 1:
        status_recommendation = "tested_needs_more_evidence"
    else:
        status_recommendation = "needs_more_evidence"

    pilot_summary = {
        "pilot_id": PILOT_ID,
        "policy_id": REFINED_POLICY_ID,
        "policy_mode": "guarded",
        "activation_enabled": True,
        "max_fires_per_run": 1,
        "total_live_runs": total_runs,
        "total_policy_fires": total_fires,
        "total_interventions": total_fires,
        "interventions_with_agent_response": interventions_with_response,
        "strategy_revision_count": strategy_revisions,
        "post_intervention_recovery_count": post_intervention_recoveries,
        "revised_plan_compliance_rate": round(revised_plan_compliance, 4),
        "helpful_intervention_count": helpful_count,
        "harmful_intervention_count": harmful_count,
        "false_positive_count": false_positive_count,
        "uncertain_count": sum(
            1
            for i in all_interventions
            if i.get("helpfulness_assessment") == "uncertain"
        ),
        "extra_steps_added": extra_steps_added,
        "repeated_error_loop_reduction": None,
        "settlement_quality_distribution": {
            sq: sum(1 for s in run_summaries if s.get("settlement_quality") == sq)
            for sq in set(s.get("settlement_quality", "unknown") for s in run_summaries)
        },
        "status_recommendation": status_recommendation,
        "metabolized": False,
        "globally_active": False,
        "operator_notes": [
            "Pilot run under operator supervision.",
            "Agent responses are simulated (not from a live LLM).",
            "The pilot tests whether the policy trigger fires correctly and whether",
            "simulated agent responses show strategy revision after the checkpoint.",
            "This is NOT metabolization. Repeated live settlement with a real agent",
            "is required before any broader activation.",
        ],
    }

    return {
        "events": all_events,
        "policy_fires": all_policy_fires,
        "interventions": all_interventions,
        "agent_responses": all_agent_responses,
        "post_intervention_actions": all_post_intervention_actions,
        "run_summaries": run_summaries,
        "pilot_summary": pilot_summary,
    }


def write_pilot_artifacts(
    results: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    """Write all pilot artifacts to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "events": output_dir / "events.jsonl",
        "policy_fires": output_dir / "policy_fires.jsonl",
        "interventions": output_dir / "interventions.jsonl",
        "agent_responses": output_dir / "agent_responses.jsonl",
        "post_intervention_actions": output_dir / "post_intervention_actions.jsonl",
        "run_summaries": output_dir / "run_summaries.jsonl",
        "pilot_summary": output_dir / "pilot_summary.json",
    }
    write_records_jsonl(results["events"], paths["events"])
    write_records_jsonl(results["policy_fires"], paths["policy_fires"])
    write_records_jsonl(results["interventions"], paths["interventions"])
    write_records_jsonl(results["agent_responses"], paths["agent_responses"])
    write_records_jsonl(
        results["post_intervention_actions"], paths["post_intervention_actions"]
    )
    write_records_jsonl(results["run_summaries"], paths["run_summaries"])
    paths["pilot_summary"].write_text(
        json.dumps(results["pilot_summary"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return paths


def main() -> None:
    print(f"Live Pilot: {PILOT_ID}")
    print(f"Policy: {REFINED_POLICY_ID}")
    print(f"Mode: guarded")
    print()

    results = run_live_pilot()
    paths = write_pilot_artifacts(results, OUTPUT_DIR)

    summary = results["pilot_summary"]
    print(f"Total live runs: {summary['total_live_runs']}")
    print(f"Total policy fires: {summary['total_policy_fires']}")
    print(
        f"Interventions with agent response: {summary['interventions_with_agent_response']}"
    )
    print(f"Strategy revisions: {summary['strategy_revision_count']}")
    print(
        f"Post-intervention recoveries: {summary['post_intervention_recovery_count']}"
    )
    print(
        f"Revised-plan compliance rate: {summary['revised_plan_compliance_rate']:.1%}"
    )
    print(f"Helpful: {summary['helpful_intervention_count']}")
    print(f"Harmful: {summary['harmful_intervention_count']}")
    print(f"False positives: {summary['false_positive_count']}")
    print(f"Status: {summary['status_recommendation']}")
    print()
    for name, path in paths.items():
        print(f"  {name} -> {path}")


if __name__ == "__main__":
    main()
