import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    output = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "runtime-snapshot",
            "--storage-root",
            str(tmp_path / ".godspeed-harness"),
        ]
    )

    assert output["counts"]["desired_directions"] == 0
    assert output["latest_trajectory"] is None


def test_cli_runtime_workflow_commands_write_connected_ledgers(tmp_path: Path):
    storage_root = tmp_path / ".godspeed-harness"

    direction = run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "start-direction",
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
    storage_root = tmp_path / ".godspeed-harness"
    run_python(
        [
            "-m",
            "godspeed_nav.cli",
            "start-direction",
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
            "--storage-root",
            str(storage_root),
        ]
    )

    assert output["horizon"]["active_direction_count"] == 1
    assert "settlement_quality" in output


def test_pre_tool_hook_warns_on_unaffordable_action(tmp_path: Path):
    storage_root = tmp_path / ".godspeed-harness"
    output = run_python(
        ["hooks/pre_tool_use.py"],
        {
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
    assert '"tool_name": "Edit"' in (storage_root / "ledgers" / "tool_payments.jsonl").read_text(
        encoding="utf-8"
    )


def test_post_tool_hook_records_settlement_event(tmp_path: Path):
    storage_root = tmp_path / ".godspeed-harness"

    output = run_python(
        ["hooks/post_tool_use.py"],
        {
            "storage_root": str(storage_root),
            "affordance_id": "aff-1",
            "before_state": {"tests": 0},
            "after_state": {"tests": 1},
            "evidence": ["pytest passed"],
        },
    )

    assert output["recorded"] is True
    ledger = storage_root / "ledgers" / "settlements.jsonl"
    assert '"affordance_id": "aff-1"' in ledger.read_text(encoding="utf-8")
    assert output["snapshot"]["counts"]["settlements"] == 1


def test_stop_hook_consolidates_developmental_memory(tmp_path: Path):
    storage_root = tmp_path / ".godspeed-harness"

    output = run_python(
        ["hooks/stop.py"],
        {
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


def test_mcp_wrapper_registers_required_tools():
    from mcp.cybernetic_nav_server.server import TOOL_NAMES

    assert {
        "cybernetic_nav.compute_error",
        "cybernetic_nav.estimate_payment",
        "cybernetic_nav.score_settlement",
        "cybernetic_nav.update_trajectory",
        "cybernetic_nav.compute_metabolization",
        "cybernetic_nav.rank_affordances",
        "cybernetic_nav.runtime_snapshot",
        "cybernetic_nav.developmental_report",
    } <= set(TOOL_NAMES)


def test_mcp_wrapper_dispatches_runtime_snapshot_and_report(tmp_path: Path):
    from mcp.cybernetic_nav_server.server import call_tool

    storage_root = tmp_path / ".godspeed-harness"

    snapshot = call_tool("cybernetic_nav.runtime_snapshot", {"storage_root": str(storage_root)})
    report = call_tool("cybernetic_nav.developmental_report", {"storage_root": str(storage_root)})

    assert snapshot["counts"]["desired_directions"] == 0
    assert report["horizon"]["active_direction_count"] == 0


def test_monitor_configuration_contains_recommended_monitors():
    monitors = json.loads((ROOT / "monitors" / "monitors.json").read_text(encoding="utf-8"))

    assert {
        "settlement-log-monitor",
        "horizon-drift-monitor",
        "circular-motion-monitor",
        "unaffordable-action-monitor",
    } <= {monitor["name"] for monitor in monitors["monitors"]}
