from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_enterprise_runbooks_cover_required_operations():
    runbook_dir = ROOT / "docs" / "runbooks"
    required = {
        "installation.md": ["uv run pytest -q", "godspeed-nav validate"],
        "configuration.md": ["HARNESS.md", "outcome_as_terminal"],
        "absorption-ingest.md": ["ingest/absorption", "settlement-plan.md", "metabolized"],
        "backup-restore.md": ["export_backup", "manifest.json"],
        "incident-recovery.md": ["quarantine", "storage_migration_required"],
        "release-readiness.md": ["Release gates", "uv run pytest -q", "godspeed-nav validate"],
    }

    for filename, expected_terms in required.items():
        text = (runbook_dir / filename).read_text(encoding="utf-8")
        for term in expected_terms:
            assert term in text


def test_cli_reference_distinguishes_harness_source_from_receiving_project():
    text = (ROOT / "docs" / "references" / "cli-reference.md").read_text(encoding="utf-8")

    assert "--workspace-root` should point at the receiving project" in text
    assert "ingest/absorption/" in text
    assert ".godspeed-harness/" in text
