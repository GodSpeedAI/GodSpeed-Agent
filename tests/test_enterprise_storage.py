import json
from pathlib import Path

import pytest

from godspeed_nav.storage import LedgerStore, StorageError


def test_unsafe_ledger_names_are_rejected(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")

    with pytest.raises(StorageError) as error:
        store.ledger_path("../settlements")

    assert error.value.code == "unsafe_ledger_name"


def test_append_event_wraps_record_with_sequence_timestamp_and_checksum(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")

    first = store.append_event("settlements", {"id": "set-1", "status": "success"})
    second = store.append_event("settlements", {"id": "set-2", "status": "failed"})
    events = store.read_events("settlements")

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert events[0]["record"] == {"id": "set-1", "status": "success"}
    assert len(events[0]["checksum"]) == 64
    assert events[0]["schema_version"] == 1


def test_read_events_quarantines_checksum_mismatch(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")
    store.append_event("payments", {"id": "pay-1", "status": "ok"})
    ledger = store.ledger_path("payments")
    tampered = ledger.read_text(encoding="utf-8").replace('"ok"', '"tampered"')
    ledger.write_text(tampered, encoding="utf-8")

    assert store.read_events("payments") == []
    quarantine = store.root / "cache" / "quarantine" / "payments.corrupt.jsonl"
    assert "checksum_mismatch" in quarantine.read_text(encoding="utf-8")


def test_export_backup_contains_ledgers_and_manifest(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")
    store.append_event("settlements", {"id": "set-1"})

    backup = store.export_backup(tmp_path / "backup")

    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["ledger_count"] == 1
    assert (backup / "ledgers" / "settlements.jsonl").exists()
