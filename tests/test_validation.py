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
        "hooks",
        "mcp",
        "reports",
        "cognitive_runtime_bridge",
    } <= set(result["checks"])

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
    assert result["checks"]["self_critique"]["details"]["mandatory_surface_available"] is True
    assert result["checks"]["self_critique"]["details"]["doctrine_drift_detected"] is False
    assert result["checks"]["public_cognitive_surfaces"]["details"]["cli_command_available"] is True
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
