import subprocess
import sys
from pathlib import Path

from godspeed_nav.storage import LedgerStore
from godspeed_nav.validation import validate_enterprise_readiness

ROOT = Path(__file__).resolve().parents[1]


def test_validate_enterprise_readiness_checks_core_surfaces(tmp_path: Path):
    result = validate_enterprise_readiness(ROOT, tmp_path / ".godspeed-harness")

    assert result["status"] == "pass"
    assert {
        "plugin_structure",
        "config",
        "predictive_extensions",
        "storage",
        "developmental_memory",
        "self_critique",
        "public_cognitive_surfaces",
        "cognitive_os_conformance",
        "runtime_workflow",
        "agents",
        "mcp",
        "reports",
        "cognitive_runtime_bridge",
        "settlement_invariants",
        "adapter_authority",
        "developmental_truth_storage",
        "distribution_configuration",
    } <= set(result["checks"])

    for invariant in (
        "settlement_invariants",
        "adapter_authority",
        "developmental_truth_storage",
        "distribution_configuration",
    ):
        assert result["checks"][invariant]["status"] == "pass", invariant

    assert (
        result["checks"]["mcp"]["details"]["snapshot_counts"]["desired_directions"] >= 0
    )
    assert (
        result["checks"]["predictive_extensions"]["details"]["provider"] == "heuristic"
    )
    assert result["checks"]["config"]["details"]["storage_format"] == "jsonl"
    assert result["checks"]["config"]["details"]["storage_evolution_enabled"] is False
    assert result["checks"]["config"]["details"]["preferred_database"] == "sqlite"
    assert result["checks"]["config"]["details"]["vector_index"] == "ruvector"
    assert result["checks"]["developmental_memory"]["details"]["lineage_query_available"] is True
    assert result["checks"]["developmental_memory"]["details"]["semantic_search_available"] is True
    assert result["checks"]["developmental_memory"]["details"]["semantic_search_provider"] == "ruvector"
    assert result["checks"]["self_critique"]["details"]["mandatory_surface_available"] is True
    assert result["checks"]["self_critique"]["details"]["doctrine_drift_detected"] is False
    assert result["checks"]["public_cognitive_surfaces"]["details"]["cli_command_available"] is True
    assert result["checks"]["public_cognitive_surfaces"]["details"]["developmental_memory_search_cli_available"] is True
    assert result["checks"]["public_cognitive_surfaces"]["details"]["developmental_memory_search_mcp_available"] is True
    assert result["checks"]["cognitive_os_conformance"]["details"]["representational_state"] is True
    assert result["checks"]["cognitive_os_conformance"]["details"]["representational_transition_policy"] is True
    assert result["checks"]["cognitive_os_conformance"]["details"]["affordance_paths"] is True
    assert result["checks"]["cognitive_os_conformance"]["details"]["environment_identity_deltas"] is True
    assert result["checks"]["cognitive_os_conformance"]["details"]["repetition_scheduler"] is True
    assert result["checks"]["cognitive_os_conformance"]["details"]["developmental_memory_lineage"] is True
    assert result["checks"]["cognitive_os_conformance"]["details"]["self_critique_findings"] is True
    assert result["checks"]["cognitive_runtime_bridge"]["details"]["target_spec_exists"] is True
    assert result["checks"]["cognitive_runtime_bridge"]["details"]["bridge_plan_exists"] is True
    assert result["checks"]["cognitive_runtime_bridge"]["details"]["understanding_mentions_current_substrate"] is True
    assert result["checks"]["cognitive_runtime_bridge"]["details"]["understanding_mentions_target_bridge"] is True


def test_cli_validate_outputs_pass_status(tmp_path: Path):
    storage_root = f".godspeed-harness/{tmp_path.name}-cli-validate"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "godspeed_nav.cli",
            "validate",
            "--workspace-root",
            str(ROOT),
            "--storage-root",
            storage_root,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert '"status": "pass"' in result.stdout


def test_validate_enterprise_readiness_does_not_mutate_target_storage(tmp_path: Path):
    storage_root = tmp_path / ".godspeed-harness"

    result = validate_enterprise_readiness(ROOT, storage_root)
    store = LedgerStore(storage_root)

    assert result["status"] == "pass"
    assert store.read("desired_directions") == []
    assert store.read("horizon_reviews") == []
    assert store.read("settlements") == []
    assert store.read("trajectories") == []


# ---------------------------------------------------------------------------
# Task 5: invariant-check teeth (each fails under a controlled regression)
# ---------------------------------------------------------------------------


def test_settlement_invariants_fails_when_unknown_can_settle(tmp_path: Path):
    from godspeed_nav.runtime import NavigationRuntime
    from godspeed_nav.validation import _probe_settlement_invariants

    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    # Controlled regression: seed the probe's "unknown" id as executable so the
    # runtime no longer rejects it.
    runtime.store.append(
        "affordances",
        {
            "id": "invariant-unknown-affordance",
            "direction_id": "dir-1",
            "current_status": "affordance",
            "pathway": "seeded",
        },
    )

    result = _probe_settlement_invariants(runtime)

    assert result["status"] == "fail"
    assert result["details"]["rejected_unknown_affordance"] is False


def test_adapter_authority_fails_when_evidence_not_provisional(tmp_path: Path):
    from godspeed_nav.runtime import NavigationRuntime
    from godspeed_nav.validation import _probe_adapter_authority

    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    # No affordance seeded: ingestion rejects instead of classifying provisional.
    result = _probe_adapter_authority(runtime, "missing-affordance")

    assert result["status"] == "fail"
    assert result["details"]["complete_evidence_provisional"] is False


def test_developmental_truth_storage_fails_on_root_level_file(tmp_path: Path):
    from godspeed_nav.validation import _probe_developmental_truth_storage

    probe_root = tmp_path / "truth-probe"
    probe_root.mkdir(parents=True, exist_ok=True)
    # Controlled regression: a root-level truth file exists alongside canonical.
    (probe_root / "agentic_learning_proposals.jsonl").write_text("{}\n", encoding="utf-8")

    result = _probe_developmental_truth_storage(probe_root)

    assert result["status"] == "fail"
    assert result["details"]["no_root_level_truth_file"] is False


def test_distribution_configuration_fails_when_adapter_omitted(tmp_path: Path):
    from godspeed_nav.validation import _compute_distribution_configuration

    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "pyproject.toml").write_text(
        '[tool.hatch.build.targets.wheel]\npackages = ["godspeed_nav"]\n'
        "[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n",
        encoding="utf-8",
    )

    result = _compute_distribution_configuration(workspace)

    assert result["status"] == "fail"
