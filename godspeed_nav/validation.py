from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from godspeed_nav.config import load_config, runtime_policy
from godspeed_nav.ml import run_predictive_extensions
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
        and config.harness.outcome_as_terminal is False
        and bool(config.computation.model_provider),
        {
            "primary_metric": config.harness.primary_metric,
            "outcome_as_terminal": config.harness.outcome_as_terminal,
            "storage_format": config.storage.format,
            "storage_evolution_enabled": config.storage.evolution_enabled,
            "preferred_database": config.storage.preferred_database,
            "vector_index": config.storage.vector_index,
            "min_settlements_for_upgrade": config.storage.min_settlements_for_upgrade,
            "model_provider": config.computation.model_provider,
            "ml_event_threshold": config.computation.ml_event_threshold,
            "simulation_threshold": config.computation.simulation_threshold,
        },
    )

    predictive = run_predictive_extensions(
        workspace_root=workspace,
        storage_root=storage_root,
        candidates=[
            {
                "id": "predictive-affordance",
                "expected_horizon_delta": 1,
                "risk": 0,
                "costs": {"time": 1},
                "capacities": {"time": 5},
            }
        ],
    )
    checks["predictive_extensions"] = _check(
        predictive["provider"] == config.computation.model_provider
        and predictive["thresholds"]["ml_event_threshold"]
        == config.computation.ml_event_threshold
        and predictive["thresholds"]["simulation_threshold"]
        == config.computation.simulation_threshold,
        {
            "provider": predictive["provider"],
            "stage": predictive["stage"],
            "thresholds": predictive["thresholds"],
        },
    )

    store = LedgerStore(storage_root)
    checks["storage"] = _check(
        store.migration_status()["status"] == "current", store.migration_status()
    )

    from mcp.cybernetic_nav_server.server import TOOL_NAMES, call_tool

    expected_mcp_tools = {
        "cybernetic_nav.compute_error",
        "cybernetic_nav.estimate_payment",
        "cybernetic_nav.score_settlement",
        "cybernetic_nav.update_trajectory",
        "cybernetic_nav.compute_metabolization",
        "cybernetic_nav.rank_affordances",
        "cybernetic_nav.detect_circular_motion",
        "cybernetic_nav.review_absorbability",
        "cybernetic_nav.review_positive_disintegration",
        "cybernetic_nav.write_ledger_event",
        "cybernetic_nav.read_developmental_memory",
        "cybernetic_nav.start_direction",
        "cybernetic_nav.review_horizon",
        "cybernetic_nav.record_settlement",
        "cybernetic_nav.runtime_snapshot",
        "cybernetic_nav.developmental_report",
        "cybernetic_nav.predictive_extensions",
        "cybernetic_nav.validate_enterprise_readiness",
    }

    with tempfile.TemporaryDirectory(prefix="godspeed-validate-") as scratch_dir:
        scratch_workspace = Path(scratch_dir)
        scratch_root = scratch_workspace / ".godspeed-harness"
        runtime = NavigationRuntime(scratch_root, policy=runtime_policy(config))
        direction = runtime.start_direction(
            "Validation", "Run enterprise validation", source="validate"
        )
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
            review["next_affordance"]["id"] == "validation-affordance"
            and settlement["status"] == "success",
            {"direction_id": direction["id"], "settlement_status": settlement["status"]},
        )

        snapshot = call_tool(
            "cybernetic_nav.runtime_snapshot",
            {
                "workspace_root": str(scratch_workspace),
                "storage_root": str(scratch_root),
            },
        )
        checks["mcp"] = _check(
            expected_mcp_tools <= set(TOOL_NAMES) and "counts" in snapshot,
            {
                "registered_tools": sorted(TOOL_NAMES),
                "snapshot_counts": snapshot.get("counts", {}),
            },
        )

        report = generate_developmental_report(scratch_root)
        checks["reports"] = _check(
            report["horizon"]["active_direction_count"] >= 1,
            {"active_direction_count": report["horizon"]["active_direction_count"]},
        )

    checks["hooks"] = _check((workspace / "hooks" / "pre_tool_use.py").exists(), {})

    evaluator_contract = (workspace / "agents" / "evaluator.md").read_text(
        encoding="utf-8"
    )
    checks["agents"] = _check(
        all(
            section in evaluator_contract
            for section in ["## Inputs", "## Workflow", "## Failure Modes"]
        ),
        {"evaluator_sections": ["## Inputs", "## Workflow", "## Failure Modes"]},
    )

    status = (
        "pass"
        if all(check["status"] == "pass" for check in checks.values())
        else "fail"
    )
    return {"status": status, "checks": checks}


def _check(condition: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"status": "pass" if condition else "fail", "details": details}
