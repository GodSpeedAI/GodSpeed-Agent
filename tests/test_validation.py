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
        "runtime_workflow",
        "agents",
        "hooks",
        "mcp",
        "reports",
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
