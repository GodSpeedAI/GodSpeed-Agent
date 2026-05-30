import subprocess
import sys
from pathlib import Path

from godspeed_nav.validation import validate_enterprise_readiness


ROOT = Path(__file__).resolve().parents[1]


def test_validate_enterprise_readiness_checks_core_surfaces(tmp_path: Path):
    result = validate_enterprise_readiness(ROOT, tmp_path / ".godspeed-harness")

    assert result["status"] == "pass"
    assert {
        "plugin_structure",
        "config",
        "storage",
        "runtime_workflow",
        "agents",
        "hooks",
        "mcp",
        "reports",
    } <= set(result["checks"])

    assert result["checks"]["mcp"]["details"]["snapshot_counts"]["desired_directions"] >= 0


def test_cli_validate_outputs_pass_status(tmp_path: Path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "godspeed_nav.cli",
            "validate",
            "--workspace-root",
            str(ROOT),
            "--storage-root",
            str(tmp_path / ".godspeed-harness"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert '"status": "pass"' in result.stdout
