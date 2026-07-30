"""Tests for canonical LearningProposalCreated storage through LedgerStore."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from godspeed_nav.storage import LedgerStore

from agentic_capability_loop.adapters import detect_coherence_break
from agentic_capability_loop.learning_proposals import (
    LEDGER_NAME,
    append_learning_proposal,
    migrate_legacy_learning_proposals,
    query_learning_proposals,
)


def _proposal(work_request_id: str = "wr-1", domain_area: str = "agentic_capability_loop"):
    _, proposal = detect_coherence_break("missing evidence", work_request_id, domain_area=domain_area)
    return proposal


def test_learning_proposal_schema_is_stable() -> None:
    _, proposal = detect_coherence_break(
        "missing context packet",
        "wr-schema-test",
        domain_area="agentic_capability_loop",
        evidence_ref="proof-123",
    )
    assert proposal["event_type"] == "LearningProposalCreated"
    payload = proposal["payload"]
    for field in ("learning_proposal_id", "coherence_break_id", "work_request_id",
                  "proposal", "domain_area", "evidence_ref", "priority", "status", "created_at"):
        assert field in payload, f"LearningProposalCreated payload missing field: {field!r}"
    assert payload["status"] == "open"
    assert payload["domain_area"] == "agentic_capability_loop"
    assert payload["domain_model_hash"]


def test_append_writes_canonical_checksummed_envelope(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    proposal = _proposal()

    append_learning_proposal(store, proposal)

    events = store.read_events(LEDGER_NAME)
    assert len(events) == 1
    assert events[0]["record"]["event_id"] == proposal["event_id"]
    assert len(events[0]["checksum"]) == 64
    assert (store.root / "ledgers" / f"{LEDGER_NAME}.jsonl").exists()
    # No root-level legacy truth file is created.
    assert not (Path(store.root) / f"{LEDGER_NAME}.jsonl").exists()


def test_append_dedupes_by_event_id(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    proposal = _proposal()

    append_learning_proposal(store, proposal)
    append_learning_proposal(store, proposal)

    assert len(query_learning_proposals(store)) == 1


def test_append_redacts_secrets(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    proposal = _proposal()
    proposal["payload"]["token"] = "super-secret"

    append_learning_proposal(store, proposal)

    stored = query_learning_proposals(store)[0]
    assert stored["payload"]["token"] == "[REDACTED]"


def test_query_filters_by_domain_area_and_status(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    p1 = _proposal(work_request_id="wr-1", domain_area="domain_a")
    p2 = _proposal(work_request_id="wr-2", domain_area="domain_b")
    append_learning_proposal(store, p1)
    append_learning_proposal(store, p2)

    assert len(query_learning_proposals(store)) == 2
    assert len(query_learning_proposals(store, domain_area="domain_a")) == 1
    assert query_learning_proposals(store, domain_area="domain_a")[0]["event_id"] == p1["event_id"]
    assert len(query_learning_proposals(store, status="open")) == 2
    assert query_learning_proposals(store, status="closed") == []


def test_append_rejects_wrong_event_type(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    with pytest.raises(ValueError, match="Expected LearningProposalCreated"):
        append_learning_proposal(store, {"event_type": "SettlementRecorded", "payload": {}})


def test_append_rejects_missing_required_fields(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    with pytest.raises(ValueError, match="missing required field"):
        append_learning_proposal(store, {
            "event_type": "LearningProposalCreated",
            "payload": {"learning_proposal_id": "lp-1"},
        })


def test_canonical_append_maintains_monotonic_sequences_under_concurrency(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    proposals = [_proposal(work_request_id=f"wr-{i}") for i in range(12)]

    def append(proposal):
        return LedgerStore(store.root).append_event(LEDGER_NAME, proposal)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(append, proposals))

    sequences = sorted(e["sequence"] for e in store.read_events(LEDGER_NAME))
    assert sequences == list(range(1, len(proposals) + 1))


def test_canonical_storage_included_in_backup(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    append_learning_proposal(store, _proposal())

    backup = store.export_backup(tmp_path / "backup")
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    assert f"{LEDGER_NAME}.jsonl" in manifest["ledgers"]
    assert (backup / "ledgers" / f"{LEDGER_NAME}.jsonl").exists()


def test_migrate_legacy_dedupes_and_archives(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    p1 = _proposal(work_request_id="wr-1")
    p2 = _proposal(work_request_id="wr-2")
    legacy = Path(store.root) / f"{LEDGER_NAME}.jsonl"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    # Write duplicate IDs plus two unique records.
    legacy.write_text(
        json.dumps(p1) + "\n"
        + json.dumps(p1) + "\n"
        + json.dumps(p2) + "\n",
        encoding="utf-8",
    )

    result = migrate_legacy_learning_proposals(store)

    assert result["migrated"] == 2
    assert result["skipped_duplicates"] == 1
    assert result["archived"] == 1
    assert len(query_learning_proposals(store)) == 2
    # Legacy file archived under cache/migrations/.
    assert not legacy.exists()
    assert (Path(store.root) / "cache" / "migrations" / legacy.name).exists()

    # Second migration is a no-op.
    result2 = migrate_legacy_learning_proposals(store)
    assert result2["migrated"] == 0
    assert result2["archived"] == 0


def test_migrate_legacy_blocks_archival_on_malformed_line(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    p1 = _proposal(work_request_id="wr-1")
    legacy = Path(store.root) / f"{LEDGER_NAME}.jsonl"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(
        json.dumps(p1) + "\n{not valid json\n",
        encoding="utf-8",
    )

    result = migrate_legacy_learning_proposals(store)

    # Valid record still migrates; archival blocked by malformed line.
    assert result["migrated"] == 1
    assert result["malformed"] == 1
    assert result["archived"] == 0
    assert legacy.exists()
    assert len(query_learning_proposals(store)) == 1


def test_migrate_legacy_noop_when_no_legacy_file(tmp_path: Path) -> None:
    store = LedgerStore(str(tmp_path))
    result = migrate_legacy_learning_proposals(store)
    assert result == {"migrated": 0, "skipped_duplicates": 0, "archived": 0, "malformed": 0}


def test_persist_to_ledger_writes_learning_proposal_canonically(tmp_path: Path) -> None:
    from agentic_capability_loop.adapters import (
        emit_capability_updated,
        emit_settlement_recorded,
        persist_to_ledger,
        schedule_repetition,
    )

    store = LedgerStore(str(tmp_path))
    settlement = emit_settlement_recorded("wr-persist", "proof-1", "ev-1", "usable", "no match")
    capability = emit_capability_updated(
        {"id": "cap-1", "label": "test-cap", "status": "active_evidence", "settlement_count": 0},
        settlement,
    )
    repetition = schedule_repetition(capability["payload"]["capability_id"])
    proposal = _proposal(work_request_id="wr-persist")

    result = persist_to_ledger(
        settlement, capability, repetition, store, learning_proposal_event=proposal
    )
    assert result["learning_proposal"]["event_id"] == proposal["event_id"]
    assert len(result["outbox"]) == 3
    assert len(query_learning_proposals(store)) == 1
