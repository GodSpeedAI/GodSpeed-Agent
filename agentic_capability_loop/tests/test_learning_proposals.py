"""Tests for LearningProposalLedger and stabilized LearningProposalCreated schema."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the godspeed_agent repo root is importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentic_capability_loop.adapters import detect_coherence_break
from agentic_capability_loop.learning_proposals import LearningProposalLedger, LEDGER_NAME


def test_learning_proposal_schema_is_stable() -> None:
    """LearningProposalCreated must carry all required schema fields."""
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
    assert payload["domain_model_hash"]  # must be non-empty


def test_learning_proposal_ledger_appends_and_reads(tmp_path: Path) -> None:
    ledger = LearningProposalLedger(tmp_path)
    _, proposal = detect_coherence_break(
        "missing evidence",
        "wr-ledger-test",
        domain_area="agentic_capability_loop",
    )
    ledger.append(proposal)
    records = ledger.read_all()
    assert len(records) == 1
    assert records[0]["event_id"] == proposal["event_id"]
    assert (tmp_path / f"{LEDGER_NAME}.jsonl").exists()


def test_learning_proposal_ledger_is_queryable_by_domain_area(tmp_path: Path) -> None:
    ledger = LearningProposalLedger(tmp_path)
    _, p1 = detect_coherence_break("reason-1", "wr-1", domain_area="agentic_capability_loop")
    _, p2 = detect_coherence_break("reason-2", "wr-2", domain_area="other_domain")
    ledger.append(p1)
    ledger.append(p2)

    results = ledger.query_by_domain_area("agentic_capability_loop")
    assert len(results) == 1
    assert results[0]["event_id"] == p1["event_id"]

    empty = ledger.query_by_domain_area("nonexistent_domain")
    assert empty == []


def test_learning_proposal_ledger_rejects_wrong_event_type(tmp_path: Path) -> None:
    ledger = LearningProposalLedger(tmp_path)
    with pytest.raises(ValueError, match="Expected LearningProposalCreated"):
        ledger.append({"event_type": "SettlementRecorded", "payload": {}})


def test_learning_proposal_ledger_rejects_missing_required_fields(tmp_path: Path) -> None:
    ledger = LearningProposalLedger(tmp_path)
    with pytest.raises(ValueError, match="missing required field"):
        ledger.append({
            "event_type": "LearningProposalCreated",
            "payload": {"learning_proposal_id": "lp-1"},  # missing work_request_id, domain_area, status
        })


def test_persist_to_ledger_includes_learning_proposal(tmp_path: Path) -> None:
    """persist_to_ledger writes the learning proposal to the JSONL ledger."""
    from godspeed_nav.storage import LedgerStore
    from agentic_capability_loop.adapters import (
        emit_settlement_recorded, update_capability_ledger,
        schedule_repetition, persist_to_ledger,
    )

    store = LedgerStore(str(tmp_path))
    settlement = emit_settlement_recorded("wr-persist", "proof-1", "ev-1", "unusable", "no match")
    capability = update_capability_ledger(settlement, "test-cap", settlement_count=0)
    repetition = schedule_repetition(capability["payload"]["capability_id"])
    _, proposal = detect_coherence_break("evidence mismatch", "wr-persist", domain_area="agentic_capability_loop")

    result = persist_to_ledger(settlement, capability, repetition, store, learning_proposal_event=proposal)
    assert result["learning_proposal"]["event_id"] == proposal["event_id"]

    ledger = LearningProposalLedger(tmp_path)
    assert len(ledger.read_all()) == 1
    assert ledger.read_all()[0]["event_id"] == proposal["event_id"]
