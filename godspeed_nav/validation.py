from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from godspeed_nav.config import load_config, runtime_policy
from godspeed_nav.ml import run_predictive_extensions
from godspeed_nav.reports import generate_developmental_report
from godspeed_nav.runtime import NavigationRuntime
from godspeed_nav.schemas import DomainRuleError
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
    lineage = store.query_developmental_memory()
    checks["developmental_memory"] = _check(
        set(lineage) == {
            "paid_paths",
            "failed_settlements",
            "substrate_capabilities",
            "revised_critique_findings",
        },
        {
            "lineage_query_available": True,
            "lineage_keys": sorted(lineage),
        },
    )

    policy_reference = (workspace / "docs" / "references" / "policy-reference.md").read_text(encoding="utf-8")
    evaluator_contract = (workspace / "agents" / "evaluator.md").read_text(encoding="utf-8")
    doctrine_drift_detected = (
        "self-critique" not in policy_reference.lower()
        or "simulation" not in evaluator_contract.lower()
    )
    checks["self_critique"] = _check(
        not doctrine_drift_detected,
        {
            "mandatory_surface_available": True,
            "doctrine_drift_detected": doctrine_drift_detected,
        },
    )

    from mcp.cybernetic_nav_server.server import TOOL_NAMES, call_tool
    from godspeed_nav.cli import build_parser

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
        "cybernetic_nav.search_developmental_memory",
        "cybernetic_nav.start_direction",
        "cybernetic_nav.review_horizon",
        "cybernetic_nav.record_settlement",
        "cybernetic_nav.runtime_snapshot",
        "cybernetic_nav.cognitive_surfaces",
        "cybernetic_nav.developmental_report",
        "cybernetic_nav.predictive_extensions",
        "cybernetic_nav.validate_enterprise_readiness",
    }
    cli_commands = set(build_parser()._subparsers._group_actions[0].choices.keys())
    checks["public_cognitive_surfaces"] = _check(
        "cognitive-surfaces" in cli_commands
        and "cybernetic_nav.cognitive_surfaces" in set(TOOL_NAMES)
        and "search-developmental-memory" in cli_commands
        and "cybernetic_nav.search_developmental_memory" in set(TOOL_NAMES),
        {
            "cli_command_available": "cognitive-surfaces" in cli_commands,
            "mcp_tool_available": "cybernetic_nav.cognitive_surfaces" in set(TOOL_NAMES),
            "developmental_memory_search_cli_available": "search-developmental-memory" in cli_commands,
            "developmental_memory_search_mcp_available": "cybernetic_nav.search_developmental_memory" in set(TOOL_NAMES),
        },
    )

    with tempfile.TemporaryDirectory(prefix="godspeed-validate-") as scratch_dir:
        scratch_workspace = Path(scratch_dir)
        scratch_root = scratch_workspace / ".godspeed-harness"
        runtime = NavigationRuntime(scratch_root, policy=runtime_policy(config))
        direction = runtime.start_direction(
            "Validation", "Run enterprise validation", source="validate"
        )
        runtime.set_representational_state(
            direction_id=direction["id"],
            scope_position="general",
            mode_of_givenness_position="abstract",
            phase="general",
            radius=1.0,
            confidence=0.8,
        )
        runtime.review_representational_transition(
            current_state={
                "scope_position": "general",
                "mode_of_givenness_position": "abstract",
                "phase": "general",
            },
            target_state={
                "scope_position": "general",
                "mode_of_givenness_position": "abstract",
                "phase": "abstract",
            },
            capacity=1.0,
        )
        review = runtime.review_horizon(
            direction_id=direction["id"],
            candidates=[
                {
                    "id": "validation-affordance",
                    "statement": "Validate runtime workflow",
                    "pathway": "local deterministic sample",
                    "required_preconditions": ["tests"],
                    "transition_sequence": ["test", "patch", "verify"],
                    "expected_settlement": {"validated": 1},
                    "lifecycle_status": "ready",
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
            identity_delta={"validation_posture": "explicit"},
            future_affordances_created=["rerun validation under variation"],
        )
        runtime.store.append(
            "capabilities",
            {"id": "sim-cap", "lifecycle_state": "metabolized", "evidence_source": "simulation"},
        )
        critique = runtime.review_self_critique()
        semantic_search = LedgerStore(scratch_root).search_developmental_memory(
            "validation affordable",
            limit=1,
        )
        checks["runtime_workflow"] = _check(
            review["next_affordance"]["id"] == "validation-affordance"
            and settlement["status"] == "success",
            {"direction_id": direction["id"], "settlement_status": settlement["status"]},
        )

        checks["developmental_memory"] = _check(
            set(lineage) == {
                "paid_paths",
                "failed_settlements",
                "substrate_capabilities",
                "revised_critique_findings",
            }
            and semantic_search["provider"] == "ruvector",
            {
                "lineage_query_available": True,
                "lineage_keys": sorted(lineage),
                "semantic_search_available": True,
                "semantic_search_provider": semantic_search["provider"],
                "semantic_search_result_count": semantic_search["result_count"],
            },
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
            {
                "active_direction_count": report["horizon"]["active_direction_count"],
                "developmental_memory_keys": sorted(report["developmental_memory"]),
            },
        )
        checks["cognitive_os_conformance"] = _check(
            all(
                [
                    runtime.snapshot()["latest_representational_state"] is not None,
                    runtime.snapshot()["latest_representational_transition"] is not None,
                    runtime.snapshot()["latest_affordance_path"] is not None,
                    bool(settlement.get("identity_delta")),
                    runtime.snapshot()["latest_repetition_schedule"] is not None,
                    bool(report.get("developmental_memory")),
                    critique["finding_count"] >= 1,
                ]
            ),
            {
                "representational_state": runtime.snapshot()["latest_representational_state"] is not None,
                "representational_transition_policy": runtime.snapshot()["latest_representational_transition"] is not None,
                "affordance_paths": runtime.snapshot()["latest_affordance_path"] is not None,
                "environment_identity_deltas": bool(settlement.get("identity_delta")),
                "repetition_scheduler": runtime.snapshot()["latest_repetition_schedule"] is not None,
                "developmental_memory_lineage": bool(report.get("developmental_memory")),
                "self_critique_findings": critique["finding_count"] >= 1,
            },
        )

        checks["settlement_invariants"] = _probe_settlement_invariants(runtime)
        checks["adapter_authority"] = _probe_adapter_authority(
            runtime, "validation-affordance"
        )
        checks["developmental_truth_storage"] = _probe_developmental_truth_storage(
            scratch_workspace / "truth-probe"
        )

    checks["hooks"] = _check((workspace / "hooks" / "pre_tool_use.py").exists(), {})

    checks["agents"] = _check(
        all(
            section in evaluator_contract
            for section in ["## Inputs", "## Workflow", "## Failure Modes"]
        ),
        {"evaluator_sections": ["## Inputs", "## Workflow", "## Failure Modes"]},
    )

    understanding = (
        workspace / "docs" / "understanding" / "2026-05-29-cognitive-operating-systems.md"
    ).read_text(encoding="utf-8")
    target_spec = workspace / "docs" / "plans" / "specs" / "2026-05-30-cognitive-operating-system-spec.md"
    bridge_plan = workspace / "docs" / "plans" / "2026-05-30-cognitive-operating-system-bridge-plan.md"
    checks["cognitive_runtime_bridge"] = _check(
        target_spec.exists()
        and bridge_plan.exists()
        and "current harness substrate" in understanding.lower()
        and "target-state cognitive operating system spec" in understanding.lower(),
        {
            "target_spec_exists": target_spec.exists(),
            "bridge_plan_exists": bridge_plan.exists(),
            "understanding_mentions_current_substrate": "current harness substrate"
            in understanding.lower(),
            "understanding_mentions_target_bridge": "target-state cognitive operating system spec"
            in understanding.lower(),
        },
    )

    checks["distribution_configuration"] = _compute_distribution_configuration(workspace)

    status = (
        "pass"
        if all(check["status"] == "pass" for check in checks.values())
        else "fail"
    )
    return {"status": status, "checks": checks}


def _check(condition: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"status": "pass" if condition else "fail", "details": details}


_DERIVED_LEDGERS = ("settlements", "trajectories", "capabilities", "repetition_schedules")


def _probe_settlement_invariants(runtime: NavigationRuntime) -> dict[str, Any]:
    """Assert unknown/potential/possibility identifiers cannot settle."""
    before = {name: len(runtime.store.read(name)) for name in _DERIVED_LEDGERS}
    rejected = False
    code = None
    try:
        runtime.record_settlement(
            affordance_id="invariant-unknown-affordance",
            before_state={"x": 0},
            after_state={"x": 1},
            payment_actual={"time": 1},
            evidence=["settlement-invariant probe"],
            horizon_delta=1,
        )
    except DomainRuleError as exc:
        rejected = True
        code = exc.code
    after = {name: len(runtime.store.read(name)) for name in _DERIVED_LEDGERS}
    zero_writes = before == after
    ok = rejected and code == "settlement_requires_executable_affordance" and zero_writes
    return _check(ok, {
        "rejected_unknown_affordance": rejected,
        "rejection_code": code,
        "zero_derived_writes": zero_writes,
    })


def _probe_adapter_authority(runtime: NavigationRuntime, affordance_id: str) -> dict[str, Any]:
    """Assert execution evidence is provisional and writes no settlement state."""
    before = {name: len(runtime.store.read(name)) for name in _DERIVED_LEDGERS}
    complete = {
        "schema_version": "v1",
        "event_id": "invariant-ev-complete",
        "source_agent": "sea-forge",
        "event_type": "EvidenceRecorded",
        "occurred_at": "2026-07-01T00:00:00+00:00",
        "idempotency_key": "invariant-ev-complete",
        "payload": {
            "namespace": "agentic_capability_loop",
            "affordance_id": affordance_id,
            "work_request_id": "wr-invariant",
            "proof_result_id": "pr-invariant",
            "expected_result": "ok",
            "observed_result": "ok",
        },
    }
    provisional = False
    try:
        ingested = runtime.ingest_execution_evidence(complete)
        provisional = ingested.get("classification") == "provisional"
    except DomainRuleError:
        provisional = False
    incomplete_rejected = False
    incomplete_code = None
    try:
        runtime.ingest_execution_evidence(
            {**complete, "event_id": "invariant-ev-incomplete",
             "payload": {**complete["payload"], "observed_result": ""}}
        )
    except DomainRuleError as exc:
        incomplete_rejected = True
        incomplete_code = exc.code
    after = {name: len(runtime.store.read(name)) for name in _DERIVED_LEDGERS}
    zero_writes = before == after
    ok = (
        provisional
        and incomplete_rejected
        and incomplete_code == "incomplete_execution_evidence"
        and zero_writes
    )
    return _check(ok, {
        "complete_evidence_provisional": provisional,
        "incomplete_evidence_rejected": incomplete_rejected,
        "incomplete_rejection_code": incomplete_code,
        "zero_derived_writes": zero_writes,
    })


def _probe_developmental_truth_storage(storage_root: Path) -> dict[str, Any]:
    """Assert learning proposals use canonical LedgerStore storage."""
    from agentic_capability_loop.adapters import detect_coherence_break
    from agentic_capability_loop.learning_proposals import (
        LEDGER_NAME,
        append_learning_proposal,
        query_learning_proposals,
    )

    store = LedgerStore(storage_root)
    _, proposal = detect_coherence_break(
        "truth-storage probe", "wr-truth", domain_area="agentic_capability_loop"
    )
    append_learning_proposal(store, proposal)
    query_ok = len(query_learning_proposals(store, domain_area="agentic_capability_loop")) >= 1
    canonical_path = store.root / "ledgers" / f"{LEDGER_NAME}.jsonl"
    no_root_file = not (Path(store.root) / f"{LEDGER_NAME}.jsonl").exists()
    backup = store.export_backup(storage_root / "backup-probe")
    manifest_ledgers = json.loads(
        (backup / "manifest.json").read_text(encoding="utf-8")
    )["ledgers"]
    backup_ok = f"{LEDGER_NAME}.jsonl" in manifest_ledgers
    ok = query_ok and no_root_file and canonical_path.exists() and backup_ok
    return _check(ok, {
        "canonical_path_exists": canonical_path.exists(),
        "no_root_level_truth_file": no_root_file,
        "query_returns_proposal": query_ok,
        "backup_includes_proposal": backup_ok,
    })


def _compute_distribution_configuration(workspace: Path) -> dict[str, Any]:
    """Report package/test configuration evidence (not built-artifact proof)."""
    import tomllib

    pyproject = tomllib.loads((workspace / "pyproject.toml").read_text(encoding="utf-8"))
    hatch = pyproject.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {})
    wheel_packages = hatch.get("wheel", {}).get("packages", [])
    testpaths = (
        pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths", [])
    )
    both_packages = (
        "agentic_capability_loop" in wheel_packages and "godspeed_nav" in wheel_packages
    )
    adapter_tests = "agentic_capability_loop/tests" in testpaths
    ok = both_packages and adapter_tests
    return _check(ok, {
        "wheel_packages": wheel_packages,
        "testpaths": testpaths,
        "artifact_proof_note": (
            "configuration evidence only; built-artifact proof lives in "
            "tests/test_distribution.py"
        ),
    })
