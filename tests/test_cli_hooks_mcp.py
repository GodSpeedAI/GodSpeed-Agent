import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def make_workspace(tmp_path: Path) -> Path:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    return workspace_root


def run_python(args: list[str], stdin: dict | None = None) -> dict:
    result = subprocess.run(
        [sys.executable, *args],
        input=json.dumps(stdin) if stdin is not None else None,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_cli_compute_error_outputs_json():
    output = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "compute-error",
            "--desired",
            '{"tests": 3}',
            "--observed",
            '{"tests": 1}',
        ]
    )

    assert output["error_vector"] == {"tests": 2}
    assert output["error_magnitude"] == 2


def test_cli_estimate_payment_outputs_json():
    output = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "estimate-payment",
            "--costs",
            '{"time": 3, "risk": 4}',
            "--capacities",
            '{"time": 5, "risk": 5}',
        ]
    )

    assert output["payment_burden"] == 5
    assert output["spendability"] == "affordable"


def test_cli_rank_affordances_outputs_next_recommendation():
    output = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "rank-affordances",
            "--candidates",
            '[{"id": "a", "expected_horizon_delta": 2, "risk": 2}, {"id": "b", "expected_horizon_delta": 3, "risk": 0}]',
            "--payments",
            '{"a": {"payment_burden": 4}, "b": {"payment_burden": 1}}',
        ]
    )

    assert output["next_recommended_affordance"]["id"] == "b"


def test_cli_score_settlement_outputs_failed_and_successful_cases():
    failed = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "score-settlement",
            "--before",
            '{"tests": 0}',
            "--after",
            '{"tests": 0}',
            "--desired",
            '{"statement": "add tests"}',
            "--payment",
            '{"time": 1}',
            "--evidence",
            '["intent: add tests"]',
        ]
    )
    success = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "score-settlement",
            "--before",
            '{"tests": 0}',
            "--after",
            '{"tests": 3}',
            "--desired",
            '{"statement": "add tests"}',
            "--payment",
            '{"time": 1}',
            "--evidence",
            '["pytest passed"]',
        ]
    )

    assert failed["status"] == "failed"
    assert success["status"] == "success"


def test_cli_metabolization_rejection_outputs_missing_evidence():
    output = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "metabolization",
            "--capability-id",
            "cap-1",
            "--settlements",
            '[{"id": "s1"}]',
            "--reuse-frequency",
            "1",
            "--context-diversity",
            "1",
            "--stability",
            "0.9",
            "--maintenance-burden",
            "0.1",
            "--attention-burden",
            "0.1",
        ]
    )

    assert output["status_recommendation"] == "not_metabolized"


def test_cli_absorption_rejection_outputs_potential_status():
    output = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "absorbability",
            "--root-state",
            '{"capabilities": ["python"]}',
            "--external-state",
            '{"capabilities": ["mcp"]}',
            "--desired",
            '{"statement": "absorb mcp"}',
            "--capability-delta",
            '["mcp"]',
            "--license",
            '{"compatible": true}',
        ]
    )

    assert output["absorbability_status"] == "potential"


def test_cli_runtime_snapshot_outputs_connected_counts(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"

    output = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "runtime-snapshot",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
        ]
    )

    assert output["counts"]["desired_directions"] == 0
    assert output["latest_trajectory"] is None


def test_cli_runtime_workflow_commands_write_connected_ledgers(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"

    direction = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "start-direction",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
            "--label",
            "Enterprise runtime",
            "--statement",
            "Connect workflow commands",
        ]
    )
    review = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "review-horizon",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
            "--direction-id",
            direction["id"],
            "--candidates",
            '[{"id":"cli-loop","statement":"Use runtime CLI","pathway":"call CLI","costs":{"time":1},"capacities":{"time":5},"expected_horizon_delta":4,"risk":0}]',
        ]
    )
    settlement = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "record-settlement",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
            "--affordance-id",
            "cli-loop",
            "--before",
            '{"cli": 0}',
            "--after",
            '{"cli": 1}',
            "--payment",
            '{"time": 1}',
            "--evidence",
            '["cli workflow test passed"]',
            "--horizon-delta",
            "4",
        ]
    )
    snapshot = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "runtime-snapshot",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
        ]
    )

    assert review["next_affordance"]["id"] == "cli-loop"
    assert settlement["status"] == "success"
    assert snapshot["counts"]["desired_directions"] == 1
    assert snapshot["counts"]["affordances"] == 1
    assert snapshot["counts"]["settlements"] == 1


def test_cli_developmental_report_outputs_observability_summary(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"
    run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "start-direction",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
            "--label",
            "Report",
            "--statement",
            "Summarize ledgers",
        ]
    )

    output = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "developmental-report",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
        ]
    )

    assert output["horizon"]["active_direction_count"] == 1
    assert "settlement_quality" in output


def test_cli_predictive_extensions_respects_configured_provider_and_thresholds(
    tmp_path: Path,
):
    workspace_root = make_workspace(tmp_path)
    (workspace_root / "HARNESS.md").write_text(
        "---\n"
        "computation:\n"
        "  model_provider: testing\n"
        "  ml_event_threshold: 2\n"
        "  simulation_threshold: 3\n"
        "---\n",
        encoding="utf-8",
    )
    storage_root = workspace_root / ".godspeed-harness"

    from godspeed_nav.storage import LedgerStore

    store = LedgerStore(storage_root)
    for index in range(3):
        store.append_event("settlements", {"id": f"set-{index}", "status": "success"})

    output = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "predictive-extensions",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
            "--candidates",
            '[{"id":"aff-1","expected_horizon_delta":4,"risk":1,"costs":{"time":1},"capacities":{"time":5}}]',
        ]
    )

    assert output["provider"] == "testing"
    assert output["stage"] == "simulation_assisted"
    assert output["active_extensions"] == ["ml_prediction", "simulation"]


def test_cli_runtime_commands_apply_workspace_safety_policy(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    (workspace_root / "HARNESS.md").write_text(
        "---\n"
        "safety:\n"
        "  block_unaffordable_actions: true\n"
        "  warn_unaffordable_actions: true\n"
        "---\n",
        encoding="utf-8",
    )
    storage_root = workspace_root / ".godspeed-harness"

    direction = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "start-direction",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
            "--label",
            "Policy",
            "--statement",
            "Honor workspace safety policy",
        ]
    )
    review = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "review-horizon",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(storage_root),
            "--direction-id",
            direction["id"],
            "--candidates",
            '[{"id":"too-expensive","statement":"Rewrite everything","pathway":"big migration","costs":{"time":99},"capacities":{"time":1},"expected_horizon_delta":9,"risk":9}]',
        ]
    )

    assert review["policy_decisions"][0]["decision"] == "block"
    assert review["next_affordance"] is None


def test_cli_rejects_storage_root_outside_workspace(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    (workspace_root / "HARNESS.md").write_text("---\n---\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "godspeed_nav.cli",
            "runtime-snapshot",
            "--workspace-root",
            str(workspace_root),
            "--storage-root",
            str(tmp_path / "outside-root"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "invalid_storage_root" in result.stderr


def test_mcp_wrapper_dispatches_predictive_extensions(tmp_path: Path):
    from godspeed_nav.storage import LedgerStore
    from mcp.cybernetic_nav_server.server import call_tool

    workspace_root = make_workspace(tmp_path)
    (workspace_root / "HARNESS.md").write_text(
        "---\n"
        "computation:\n"
        "  model_provider: testing\n"
        "  ml_event_threshold: 1\n"
        "  simulation_threshold: 5\n"
        "---\n",
        encoding="utf-8",
    )
    storage_root = workspace_root / ".godspeed-harness"
    LedgerStore(storage_root).append_event(
        "settlements", {"id": "set-1", "status": "success"}
    )

    result = call_tool(
        "cybernetic_nav.predictive_extensions",
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "candidates": [
                {
                    "id": "mcp-aff",
                    "expected_horizon_delta": 2,
                    "risk": 0,
                    "costs": {"time": 1},
                    "capacities": {"time": 5},
                }
            ],
        },
    )

    assert result["provider"] == "testing"
    assert result["stage"] == "ml_assisted"
    assert result["active_extensions"] == ["ml_prediction"]


def test_mcp_wrapper_rejects_storage_root_outside_workspace(tmp_path: Path):
    from mcp.cybernetic_nav_server.server import call_tool

    workspace_root = make_workspace(tmp_path)
    (workspace_root / "HARNESS.md").write_text("---\n---\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid_storage_root"):
        call_tool(
            "cybernetic_nav.runtime_snapshot",
            {
                "workspace_root": str(workspace_root),
                "storage_root": str(tmp_path / "outside-root"),
            },
        )


def test_pre_tool_hook_warns_on_unaffordable_action(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"
    output = run_python(
        ["hooks/pre_tool_use.py"],
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "tool_name": "Edit",
            "costs": {"time": 9, "risk": 9},
            "capacities": {"time": 1, "risk": 1},
            "block_unaffordable_actions": False,
        },
    )

    assert output["decision"] == "warn"
    assert output["payment"]["spendability"] == "unaffordable"
    assert output["policy_decision"]["code"] == "unaffordable_action"
    assert '"tool_name": "Edit"' in (
        storage_root / "ledgers" / "tool_payments.jsonl"
    ).read_text(encoding="utf-8")


def test_pre_tool_hook_rejects_storage_root_outside_workspace(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    (workspace_root / "HARNESS.md").write_text("---\n---\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "hooks/pre_tool_use.py"],
        input=json.dumps(
            {
                "workspace_root": str(workspace_root),
                "storage_root": str(tmp_path / "outside-root"),
                "tool_name": "Edit",
            }
        ),
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "invalid_storage_root" in result.stderr


def test_user_prompt_hook_records_direction_hypothesis(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"

    output = run_python(
        ["hooks/user_prompt_submit.py"],
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "prompt": "Build the next affordable path to enterprise readiness.",
        },
    )

    assert output["outcome_as_terminal"] is False
    assert output["needs_horizon_review"] is True
    assert output["desired_direction_hypothesis"]["statement"] == (
        "Build the next affordable path to enterprise readiness."
    )
    assert (storage_root / "ledgers" / "prompt_submissions.jsonl").exists()


def test_post_tool_hook_records_settlement_event(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"

    output = run_python(
        ["hooks/post_tool_use.py"],
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "affordance_id": "aff-1",
            "before_state": {"tests": 0},
            "after_state": {"tests": 1},
            "payment_actual": {"time": 1},
            "evidence": ["pytest passed"],
            "horizon_delta": 2,
        },
    )

    assert output["recorded"] is True
    ledger = storage_root / "ledgers" / "settlements.jsonl"
    assert '"affordance_id": "aff-1"' in ledger.read_text(encoding="utf-8")
    assert output["snapshot"]["counts"]["settlements"] == 1
    assert output["snapshot"]["counts"]["trajectories"] == 1
    assert output["report"]["settlement_quality"]["success"] == 1


def test_post_tool_hook_surfaces_metabolization_candidate_after_repeated_success(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"

    final_output = None
    for index, key in enumerate(["hook_a", "hook_b", "hook_c"], start=1):
        final_output = run_python(
            ["hooks/post_tool_use.py"],
            {
                "workspace_root": str(workspace_root),
                "storage_root": str(storage_root),
                "affordance_id": "aff-repeat",
                "before_state": {key: 0},
                "after_state": {key: 1},
                "payment_actual": {"time": 1},
                "evidence": [f"hook pass {index}"],
                "horizon_delta": 2,
            },
        )

    assert final_output is not None
    assert final_output["report"]["metabolization"]["candidate_count"] == 1
    assert final_output["report"]["metabolization"]["candidate_ids"] == ["aff-repeat"]


def test_stop_hook_consolidates_developmental_memory(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"

    output = run_python(
        ["hooks/stop.py"],
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "previous_theta": 0,
            "previous_radius": 1,
            "settlement_score": 0.8,
            "horizon_delta": 2,
        },
    )

    assert output["recorded"] is True
    assert (storage_root / "ledgers" / "trajectories.jsonl").exists()
    assert "report" in output


def test_hooks_trace_one_session_through_prompt_payment_settlement_and_stop(tmp_path: Path):
    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"
    session_id = "sess-123"

    prompt_output = run_python(
        ["hooks/user_prompt_submit.py"],
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "prompt": "Build the next affordable documentation loop.",
            "session_id": session_id,
        },
    )
    desired_direction_id = prompt_output["desired_direction_hypothesis"]["id"]

    pre_output = run_python(
        ["hooks/pre_tool_use.py"],
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "tool_name": "Edit",
            "session_id": session_id,
            "desired_direction_id": desired_direction_id,
            "costs": {"time": 1},
            "capacities": {"time": 5},
        },
    )
    post_output = run_python(
        ["hooks/post_tool_use.py"],
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "tool_name": "Edit",
            "affordance_id": "edit-docs",
            "session_id": session_id,
            "desired_direction_id": desired_direction_id,
            "before_state": {"docs": 0},
            "after_state": {"docs": 1},
            "payment_actual": {"time": 1},
            "evidence": ["docs changed"],
            "horizon_delta": 1,
        },
    )
    stop_output = run_python(
        ["hooks/stop.py"],
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "session_id": session_id,
            "desired_direction_id": desired_direction_id,
            "previous_theta": 0,
            "previous_radius": 1,
            "settlement_score": 0.9,
            "horizon_delta": 1,
        },
    )

    assert prompt_output["session_context"]["session_id"] == session_id
    assert pre_output["session_context"]["desired_direction_id"] == desired_direction_id
    assert post_output["session_context"]["session_id"] == session_id
    assert stop_output["session_context"]["desired_direction_id"] == desired_direction_id

    tool_payments = (storage_root / "ledgers" / "tool_payments.jsonl").read_text(encoding="utf-8")
    post_events = (storage_root / "ledgers" / "post_tool_use_events.jsonl").read_text(encoding="utf-8")
    stop_events = (storage_root / "ledgers" / "stop_events.jsonl").read_text(encoding="utf-8")

    assert f'"session_id": "{session_id}"' in tool_payments
    assert f'"desired_direction_id": "{desired_direction_id}"' in post_events
    assert f'"session_id": "{session_id}"' in stop_events


def test_mcp_wrapper_registers_required_tools():
    from mcp.cybernetic_nav_server.server import TOOL_NAMES

    assert {
        "cybernetic_nav.compute_error",
        "cybernetic_nav.estimate_payment",
        "cybernetic_nav.score_settlement",
        "cybernetic_nav.update_trajectory",
        "cybernetic_nav.compute_metabolization",
        "cybernetic_nav.rank_affordances",
        "cybernetic_nav.start_direction",
        "cybernetic_nav.review_horizon",
        "cybernetic_nav.record_settlement",
        "cybernetic_nav.runtime_snapshot",
        "cybernetic_nav.developmental_report",
        "cybernetic_nav.predictive_extensions",
        "cybernetic_nav.validate_enterprise_readiness",
    } <= set(TOOL_NAMES)


def test_mcp_wrapper_dispatches_runtime_snapshot_and_report(tmp_path: Path):
    from mcp.cybernetic_nav_server.server import call_tool

    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"

    snapshot = call_tool(
        "cybernetic_nav.runtime_snapshot",
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
        },
    )
    report = call_tool(
        "cybernetic_nav.developmental_report",
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
        },
    )

    assert snapshot["counts"]["desired_directions"] == 0
    assert report["horizon"]["active_direction_count"] == 0


def test_mcp_wrapper_dispatches_connected_runtime_workflow(tmp_path: Path):
    from mcp.cybernetic_nav_server.server import call_tool

    workspace_root = make_workspace(tmp_path)
    storage_root = workspace_root / ".godspeed-harness"

    direction = call_tool(
        "cybernetic_nav.start_direction",
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "label": "MCP runtime",
            "statement": "Drive the developmental loop through MCP",
            "kind": "goal",
            "source": "test",
        },
    )
    review = call_tool(
        "cybernetic_nav.review_horizon",
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "direction_id": direction["id"],
            "candidates": [
                {
                    "id": "mcp-loop",
                    "statement": "Run runtime loop through MCP",
                    "pathway": "dispatch runtime tools",
                    "costs": {"time": 1},
                    "capacities": {"time": 5},
                    "expected_horizon_delta": 3,
                    "risk": 0,
                }
            ],
        },
    )
    settlement = call_tool(
        "cybernetic_nav.record_settlement",
        {
            "workspace_root": str(workspace_root),
            "storage_root": str(storage_root),
            "affordance_id": "mcp-loop",
            "before_state": {"mcp": 0},
            "after_state": {"mcp": 1},
            "payment_actual": {"time": 1},
            "evidence": ["mcp workflow passed"],
            "horizon_delta": 3,
        },
    )

    assert review["next_affordance"]["id"] == "mcp-loop"
    assert settlement["status"] == "success"
    assert settlement["trajectory"]["new_radius"] > 1


def test_mcp_wrapper_dispatches_enterprise_validation(tmp_path: Path):
    from mcp.cybernetic_nav_server.server import call_tool

    storage_root = f".godspeed-harness/{tmp_path.name}-validation"

    result = call_tool(
        "cybernetic_nav.validate_enterprise_readiness",
        {
            "workspace_root": str(ROOT),
            "storage_root": storage_root,
        },
    )

    assert result["status"] == "pass"
    assert "mcp" in result["checks"]


def test_monitor_configuration_contains_recommended_monitors():
    monitors = json.loads(
        (ROOT / "monitors" / "monitors.json").read_text(encoding="utf-8")
    )

    assert {
        "settlement-log-monitor",
        "horizon-drift-monitor",
        "circular-motion-monitor",
        "unaffordable-action-monitor",
    } <= {monitor["name"] for monitor in monitors["monitors"]}
