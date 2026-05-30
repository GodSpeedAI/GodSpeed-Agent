from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_enterprise_runbooks_cover_required_operations():
    runbook_dir = ROOT / "docs" / "runbooks"
    required = {
        "installation.md": ["uv run pytest -q", "godspeed-nav validate"],
        "configuration.md": ["HARNESS.md", "outcome_as_terminal"],
        "backup-restore.md": ["export_backup", "manifest.json"],
        "incident-recovery.md": ["quarantine", "storage_migration_required"],
        "release-readiness.md": ["Release gates", "uv run pytest -q", "godspeed-nav validate"],
    }

    for filename, expected_terms in required.items():
        text = (runbook_dir / filename).read_text(encoding="utf-8")
        for term in expected_terms:
            assert term in text
