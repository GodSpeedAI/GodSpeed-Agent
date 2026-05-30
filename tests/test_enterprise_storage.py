import json
from concurrent.futures import ThreadPoolExecutor
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


def test_append_event_maintains_index_for_record_id_reads(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")

    store.append_event("settlements", {"id": "set-1", "status": "success"})
    store.append_event("settlements", {"id": "set-2", "status": "failed"})

    index = json.loads((store.root / "indexes" / "settlements.index.json").read_text(encoding="utf-8"))
    assert index["schema_version"] == 1
    assert index["records"]["set-1"]["sequence"] == 1
    assert store.read_event_by_record_id("settlements", "set-2")["record"]["status"] == "failed"


def test_storage_manifest_version_is_initialized_and_validated(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")

    manifest = store.migration_status()

    assert manifest["schema_version"] == 1
    assert manifest["status"] == "current"


def test_storage_manifest_version_mismatch_requires_migration(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")
    manifest_path = store.root / "config" / "storage_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = 999
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(StorageError) as error:
        store.migration_status()

    assert error.value.code == "storage_migration_required"


def test_append_event_maintains_monotonic_sequences_under_concurrency(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")

    def write_event(index: int) -> dict:
        return LedgerStore(store.root).append_event(
            "settlements", {"id": f"set-{index}", "status": "success"}
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(write_event, range(24)))

    sequences = sorted(item["sequence"] for item in results)
    persisted = store.read_events("settlements")

    assert sequences == list(range(1, 25))
    assert [event["sequence"] for event in persisted] == list(range(1, 25))


def test_developmental_memory_query_answers_lineage_questions(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")
    store.append_event("payments", {"id": "pay-1", "affordance_id": "aff-1", "payment_burden": 2})
    store.append_event("settlements", {"id": "set-1", "affordance_id": "aff-1", "status": "failed"})
    store.append("capabilities", {"id": "cap-1", "lifecycle_state": "metabolized"})
    store.append("critique_findings", {"id": "crit-1", "finding": "path too broad", "revised_by": "aff-2"})

    lineage = store.query_developmental_memory()

    assert lineage["paid_paths"] == ["aff-1"]
    assert lineage["failed_settlements"] == ["set-1"]
    assert lineage["substrate_capabilities"] == ["cap-1"]
    assert lineage["revised_critique_findings"] == [{"id": "crit-1", "revised_by": "aff-2"}]
