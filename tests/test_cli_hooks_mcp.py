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


def test_pre_tool_hook_warns_on_unaffordable_action(tmp_path: Path):
    output = run_python(
        ["hooks/pre_tool_use.py"],
        {
            "storage_root": str(tmp_path / ".godspeed-harness"),
            "tool_name": "Edit",
            "costs": {"time": 9, "risk": 9},
            "capacities": {"time": 1, "risk": 1},
            "block_unaffordable_actions": False,
        },
    )

    assert output["decision"] == "warn"
    assert output["payment"]["spendability"] == "unaffordable"


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


def test_mcp_wrapper_registers_required_tools():
    from mcp.cybernetic_nav_server.server import TOOL_NAMES

    assert {
        "cybernetic_nav.compute_error",
        "cybernetic_nav.estimate_payment",
        "cybernetic_nav.score_settlement",
        "cybernetic_nav.update_trajectory",
        "cybernetic_nav.compute_metabolization",
        "cybernetic_nav.rank_affordances",
    } <= set(TOOL_NAMES)


def test_monitor_configuration_contains_recommended_monitors():
    monitors = json.loads((ROOT / "monitors" / "monitors.json").read_text(encoding="utf-8"))

    assert {
        "settlement-log-monitor",
        "horizon-drift-monitor",
        "circular-motion-monitor",
        "unaffordable-action-monitor",
    } <= {monitor["name"] for monitor in monitors["monitors"]}
