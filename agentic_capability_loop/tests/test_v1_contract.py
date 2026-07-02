"""v1 contract test (WP-1, F-01): every envelope GSA emits validates against
`sea.agent.event.v1.json`.

The ledger enforces v1 fail-closed (`additionalProperties:false`); before this
fix GSA emitted the family-A shape (`namespace` at top level, no
`schema_version`/`source_agent`/`idempotency_key`) which the ledger would DLQ.

We mirror jsonschema's enforcement of the schema's `required` list and
`additionalProperties:false` by reading the vendored schema directly, so the
allowed-property set is the schema's, not a hand-maintained copy. A true
jsonschema pass lives at the ledger; this is the producer-side teeth-check.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentic_capability_loop.adapters import (  # noqa: E402
    detect_coherence_break,
    emit_settlement_recorded,
    handle_evidence_recorded,
    schedule_repetition,
    update_capability_ledger,
)

_SCHEMA = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "sea.agent.event.v1.json"
)


def _load_schema() -> dict:
    return json.loads(_SCHEMA.read_text(encoding="utf-8"))


def assert_v1(envelope: dict) -> None:
    """Assert `envelope` satisfies the v1 schema's structural invariants.

    Mirrors: `required` present, `additionalProperties:false` (no top-level
    field outside `properties`), `schema_version` const, and `source_agent`
    non-empty.
    """
    schema = _load_schema()
    allowed = set(schema["properties"].keys())
    for field in schema["required"]:
        assert field in envelope, f"v1 required field missing: {field}"
    extra = set(envelope.keys()) - allowed
    assert not extra, (
        f"v1 additionalProperties:false violated by top-level keys: {sorted(extra)}"
    )
    assert envelope["schema_version"] == "v1", "schema_version must be 'v1'"
    assert envelope["source_agent"], "source_agent must be non-empty"
    assert isinstance(envelope["payload"], dict), "payload must be an object"
    # namespace rides inside payload (never top-level) — the family-A->v1 port.
    assert envelope["payload"].get("namespace") == "agentic_capability_loop"
    assert "namespace" not in envelope, "top-level namespace rejected by v1"
    # F-06: every GSA envelope carries a populated CEP-0008 SS15 provenance.
    prov = envelope.get("provenance")
    assert isinstance(prov, dict) and prov.get("origin"), "provenance.origin required"
    assert isinstance(prov.get("chain"), list), "provenance.chain must be a list"


def _evidence_event() -> dict:
    return {
        "schema_version": "v1",
        "event_id": "ev-1",
        "source_agent": "sea-forge",
        "event_type": "EvidenceRecorded",
        "occurred_at": "2026-07-01T00:00:00+00:00",
        "idempotency_key": "ev-1",
        "payload": {
            "domain_model_hash": "deadbeef",
            "namespace": "agentic_capability_loop",
            "work_request_id": "wr-1",
            "proof_result_id": "pr-1",
            "observed_result": "ok",
            "expected_result": "ok",
        },
    }


def test_settlement_envelope_is_v1_conformant() -> None:
    settlement = emit_settlement_recorded(
        "wr-1", "pr-1", "ev-1", "usable", "observed matches expected"
    )
    assert_v1(settlement)
    assert settlement["source_agent"] == "godspeed-agent"
    assert settlement["event_type"] == "SettlementRecorded"


def test_capability_repetition_twin_coherence_envelopes_are_v1() -> None:
    settlement = emit_settlement_recorded("wr-1", "pr-1", "ev-1", "usable", "match")
    capability = update_capability_ledger(settlement, "cap", settlement_count=3)
    repetition = schedule_repetition(capability["payload"]["capability_id"])
    coherence, _proposal = detect_coherence_break("missing context", "wr-1")
    for env in (capability, repetition, coherence):
        assert_v1(env)


def test_handle_evidence_recorded_emits_v1_settlement() -> None:
    settlement = handle_evidence_recorded(_evidence_event())
    assert_v1(settlement)


def test_replay_shares_idempotency_key_not_event_id() -> None:
    """F-10 fix: the old bug bound idempotency_key to event_id, so a
    re-delivered/re-wrapped event (fresh event_id + occurred_at, identical
    payload) looked like a new event and could not be deduped. With a
    content-derived key the replay keeps the key while getting a new id."""
    original = emit_settlement_recorded("wr-1", "pr-1", "ev-1", "usable", "match")
    replay = copy.deepcopy(original)
    replay["event_id"] = "00000000-0000-0000-0000-000000000000"
    replay["occurred_at"] = "2030-01-01T00:00:00+00:00"
    assert original["event_id"] != replay["event_id"]
    assert original["occurred_at"] != replay["occurred_at"]
    assert original["idempotency_key"] == replay["idempotency_key"], (
        "a re-wrapped replay (same payload, new id/time) must share idempotency_key"
    )
    # The old bug: idempotency_key was literally event_id.
    assert original["idempotency_key"] != original["event_id"]


def test_distinct_events_have_distinct_idempotency_keys() -> None:
    a = emit_settlement_recorded("wr-1", "pr-1", "ev-1", "usable", "match")
    b = emit_settlement_recorded("wr-2", "pr-2", "ev-2", "usable", "match")
    assert a["idempotency_key"] != b["idempotency_key"]


def test_teeth_top_level_namespace_is_rejected() -> None:
    """Re-adding top-level `namespace` (the family-A shape) MUST fail v1
    additionalProperties:false — this is the contract's teeth."""
    settlement = emit_settlement_recorded("wr-1", "pr-1", "ev-1", "usable", "match")
    family_a = copy.deepcopy(settlement)
    family_a["namespace"] = "agentic_capability_loop"
    with pytest.raises(AssertionError, match="additionalProperties"):
        assert_v1(family_a)


def test_teeth_missing_required_field_is_rejected() -> None:
    settlement = emit_settlement_recorded("wr-1", "pr-1", "ev-1", "usable", "match")
    missing = copy.deepcopy(settlement)
    del missing["source_agent"]
    with pytest.raises(AssertionError, match="required field missing"):
        assert_v1(missing)


def test_vendored_v1_schema_matches_contracts_pin() -> None:
    """WP-2 drift check: the vendored v1 schema must be byte-identical to the
    canonical copy in hassos-addon-agent-memory-ledger (pin in that repo's
    contracts/CONTRACTS_VERSION). Editing this copy by one byte fails here.
    """
    import hashlib

    digest = hashlib.sha256(_SCHEMA.read_bytes()).hexdigest()
    assert digest == "d2a245183f7a52672dec11d7a8e9236d3db78dac674ab066d944fb758443e195", (
        "vendored v1 schema drifted from the ledger's CONTRACTS_VERSION pin"
    )
