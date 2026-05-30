from __future__ import annotations

from pathlib import Path
from typing import Any

from godspeed_nav.config import load_config
from godspeed_nav.reports import generate_developmental_report
from godspeed_nav.runtime import NavigationRuntime
from godspeed_nav.storage import LedgerStore


REQUIRED_PATHS = [
    ".claude-plugin/plugin.json",
    "HARNESS.md",
    "README.md",
    "hooks/hooks.json",
    ".mcp.json",
    "monitors/monitors.json",
    "evals/evals.json",
]


def validate_enterprise_readiness(
    workspace_root: str | Path = ".",
    storage_root: str | Path = ".godspeed-harness",
) -> dict[str, Any]:
    workspace = Path(workspace_root)
    checks: dict[str, dict[str, Any]] = {}

    missing = [path for path in REQUIRED_PATHS if not (workspace / path).exists()]
    checks["plugin_structure"] = _check(not missing, {"missing": missing})

    config = load_config(workspace)
    checks["config"] = _check(
        config.harness.primary_metric == "horizon_expansion"
        and config.harness.outcome_as_terminal is False,
        {
            "primary_metric": config.harness.primary_metric,
            "outcome_as_terminal": config.harness.outcome_as_terminal,
        },
    )

    store = LedgerStore(storage_root)
    checks["storage"] = _check(store.migration_status()["status"] == "current", store.migration_status())

    runtime = NavigationRuntime(storage_root)
    direction = runtime.start_direction("Validation", "Run enterprise validation", source="validate")
    review = runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "validation-affordance",
                "statement": "Validate runtime workflow",
                "pathway": "local deterministic sample",
                "costs": {"time": 1},
                "capacities": {"time": 5},
                "expected_horizon_delta": 1,
                "risk": 0,
            }
        ],
    )
    settlement = runtime.record_settlement(
        affordance_id="validation-affordance",
        before_state={"validated": 0},
        after_state={"validated": 1},
        payment_actual={"time": 1},
        evidence=["validation sample completed"],
        horizon_delta=1,
    )
    checks["runtime_workflow"] = _check(
        review["next_affordance"]["id"] == "validation-affordance" and settlement["status"] == "success",
        {"direction_id": direction["id"], "settlement_status": settlement["status"]},
    )

    checks["hooks"] = _check((workspace / "hooks" / "pre_tool_use.py").exists(), {})
    checks["mcp"] = _check((workspace / "mcp" / "cybernetic_nav_server" / "server.py").exists(), {})

    report = generate_developmental_report(storage_root)
    checks["reports"] = _check(
        report["horizon"]["active_direction_count"] >= 1,
        {"active_direction_count": report["horizon"]["active_direction_count"]},
    )

    status = "pass" if all(check["status"] == "pass" for check in checks.values()) else "fail"
    return {"status": status, "checks": checks}


def _check(condition: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"status": "pass" if condition else "fail", "details": details}
