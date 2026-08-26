"""Convergence T09 — canonical E9 developmental settlement and durable memory
at the frozen E9/I9 boundary (godspeed_agent -> memory_ledger).

Everything flows through the REAL GodSpeed-Agent emitter
(:mod:`godspeed_nav.developmental_events`) and the REAL durable memory gate
(:mod:`godspeed_nav.developmental_memory`, persisted over the REAL
``LedgerStore`` flock-guarded JSONL write seam), including the committed
golden fixture produced by the real emitter.

Frozen contract (sea-rs ``.agents/specs/e2e-preregistration.yml``):
- E9: godspeed_agent is the EXCLUSIVE producer of SettlementRecorded,
  CapabilityUpdated, RepetitionPlanned, LearningProposalCreated, and
  CoherenceBreakDetected; every envelope carries work_request_id,
  source_evidence_refs, developmental_decision, domain_model_ref; GSA
  independently evaluates whether evidence suffices for developmental
  settlement; CapabilityUpdated requires its own declared capability
  evidence; ONE successful proof/execution can never establish metabolized
  capability; developmental records retain provenance to their justifying
  evidence.
- I9: capability promotion requires repeated settlement under DECLARED
  relevant variation — never tool access, explanation, imitation, one proof,
  or one successful execution. Statuses below metabolized keep explicitly
  declared lower thresholds (frozen known confound, preserved not collapsed).
- I14: redelivering the same canonical event cannot duplicate developmental
  history.

Plan teeth (named tests):
  TOOTH 1 — pristine single successful cycle + metabolized promotion request
            ⇒ refused / not earned;
  TOOTH 2 — identical E9 envelope redelivery ⇒ zero duplicate history;
  TOOTH 3 — stripped source_evidence_refs ⇒ quarantine, never persisted as
            authoritative developmental truth.
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest

from agentic_capability_loop.publisher import SettlementPublisher
from godspeed_nav.developmental_events import (
    COMMON_REQUIRED_FIELDS,
    DEVELOPMENTAL_EVENT_TYPES,
    FALLBACK_PSEUDO_HASH,
    PROMOTION_TARGETS,
    ZERO_HASH,
    project_developmental_event,
)
from godspeed_nav.developmental_memory import (
    DEVELOPMENTAL_LEDGER,
    DevelopmentalMemoryState,
    ingest_developmental_event,
    load_developmental_memory_state,
    persist_developmental_event,
    read_developmental_history,
)
from godspeed_nav.runtime import NavigationRuntime
from godspeed_nav.schemas import DomainRuleError
from godspeed_nav.storage import LedgerStore

GOOD_HASH = "b" * 64
OTHER_HASH = "c" * 64
WORK_REQUEST_ID = "wr-gsf-t09"
EVIDENCE_ID = "e8ee0000-0000-4000-8000-00000000e801"
EVIDENCE_ID_2 = "e8ee0000-0000-4000-8000-00000000e802"
CAPABILITY = "aff-cap-x"

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "t09_developmental_events.json"
FIXED_NOW = "2026-08-26T00:00:00+00:00"


def _fixed_id(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"t09-golden/{name}"))


GOLDEN_PARENTS = [_fixed_id("parent-e8-1"), _fixed_id("parent-e8-2")]


def _type_payload(event_type: str, **overrides: Any) -> dict[str, Any]:
    payloads: dict[str, dict[str, Any]] = {
        "SettlementRecorded": {
            "affordance_id": CAPABILITY,
            "settlement_ref": "set-001",
            "settlement_status": "success",
            "settlement_score": 0.9,
        },
        "CapabilityUpdated": {
            "capability_id": CAPABILITY,
            "target_lifecycle": "active",
            "variation_evidence": ["set-001"],
        },
        "RepetitionPlanned": {"affordance_id": CAPABILITY, "repetition_count": 3},
        "LearningProposalCreated": {
            "learning_proposal_id": "lp-001",
            "domain_area": "navigation",
            "status": "proposed",
        },
        "CoherenceBreakDetected": {"break_reason": "circular trajectory detected"},
    }
    base = payloads[event_type]
    if overrides.get("variation_context") is not None:
        base["variation_context"] = overrides["variation_context"]
    return base


def _decision(**overrides: Any) -> dict[str, Any]:
    decision = {
        "action": "record_developmental_consequence",
        "evaluation": "independent_gsa_evaluation",
        "basis": "evidence-weighted",
    }
    return {**decision, **overrides}


def _emit(
    event_type: str,
    *,
    payload: dict[str, Any] | None = None,
    refs: list[str] | None = None,
    wr: str | None = WORK_REQUEST_ID,
    parents: list[str] | None = None,
    decision: dict[str, Any] | None = None,
    model_hash: str | None = GOOD_HASH,
    event_id: str | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    return project_developmental_event(
        event_type,
        work_request_id=wr or WORK_REQUEST_ID,
        source_evidence_refs=[EVIDENCE_ID] if refs is None else refs,
        developmental_decision=_decision() if decision is None else decision,
        domain_model_hash=model_hash or GOOD_HASH,
        parent_evidence_ids=[EVIDENCE_ID] if parents is None else parents,
        payload=payload,
        event_id=event_id,
        occurred_at=occurred_at,
    )


def _settlement(
    ref: str = "set-001",
    *,
    status: str = "success",
    score: float | None = 0.9,
    variation: str | None = "ctx-alpha",
    capability: str = CAPABILITY,
    **kw: Any,
) -> dict[str, Any]:
    payload = {
        "affordance_id": capability,
        "settlement_ref": ref,
        "settlement_status": status,
    }
    if score is not None:
        payload["settlement_score"] = score
    if variation is not None:
        payload["variation_context"] = variation
    return _emit("SettlementRecorded", payload={**_type_payload("SettlementRecorded"), **payload}, **kw)


def _promotion(
    target: str = "metabolized",
    *,
    capability: str = CAPABILITY,
    evidence_refs: list[str] | None = None,
    decision: dict[str, Any] | None = None,
    extra_payload: dict[str, Any] | None = None,
    **kw: Any,
) -> dict[str, Any]:
    payload = {
        "capability_id": capability,
        "target_lifecycle": target,
        "variation_evidence": ["set-001"] if evidence_refs is None else evidence_refs,
    }
    if extra_payload:
        payload.update(extra_payload)
    return _emit(
        "CapabilityUpdated",
        payload={**_type_payload("CapabilityUpdated"), **payload},
        decision=decision,
        **kw,
    )


@pytest.fixture()
def store(tmp_path: Path) -> LedgerStore:
    return LedgerStore(tmp_path / "memory-ledger")


def _persist(
    store: LedgerStore,
    envelope: dict[str, Any],
    *,
    state: DevelopmentalMemoryState | None = None,
    local_model_sha256: str | None = GOOD_HASH,
    known_parent_ids: list[str] | None = None,
) -> dict[str, Any]:
    return persist_developmental_event(
        store,
        envelope,
        state=state,
        local_model_sha256=local_model_sha256,
        known_parent_ids=known_parent_ids,
    )


def _rows(store: LedgerStore) -> list[dict[str, Any]]:
    return [event["record"]["envelope"] for event in store.read_events(DEVELOPMENTAL_LEDGER)]


def _admit_settlements(
    store: LedgerStore,
    specs: list[tuple[str, float | None, str | None]],
) -> list[dict[str, Any]]:
    admitted = []
    for ref, score, variation in specs:
        result = _persist(store, _settlement(ref, score=score, variation=variation))
        assert result["status"] == "first"
        admitted.append(result["record"])
    return admitted


# --- Golden fixture: REAL emitter output consumed by the REAL durable gate ----


def _regenerate_fixture() -> dict[str, Any]:
    sequence = [
        (
            "SettlementRecorded",
            {
                "affordance_id": "aff-t09-golden",
                "settlement_ref": "set-golden-001",
                "settlement_status": "success",
                "settlement_score": 0.9,
                "variation_context": "ctx-alpha",
            },
        ),
        (
            "RepetitionPlanned",
            {
                "affordance_id": "aff-t09-golden",
                "repetition_count": 3,
                "planned_variations": ["ctx-alpha", "ctx-beta"],
            },
        ),
        (
            "LearningProposalCreated",
            {
                "learning_proposal_id": "lp-golden-001",
                "domain_area": "navigation",
                "status": "proposed",
            },
        ),
        ("CoherenceBreakDetected", {"break_reason": "trajectory circular motion"}),
        (
            "CapabilityUpdated",
            {
                "capability_id": "aff-t09-golden",
                "target_lifecycle": "active",
                "variation_evidence": ["set-golden-001"],
            },
        ),
    ]
    events = [
        project_developmental_event(
            event_type,
            work_request_id="wr-gsf-t09",
            source_evidence_refs=[GOLDEN_PARENTS[0]],
            developmental_decision=_decision(),
            domain_model_hash=GOOD_HASH,
            parent_evidence_ids=GOLDEN_PARENTS,
            payload=payload,
            event_id=_fixed_id(event_type),
            occurred_at=FIXED_NOW,
        )
        for event_type, payload in sequence
    ]
    return {
        "domain_model_sha256": GOOD_HASH,
        "work_request_id": "wr-gsf-t09",
        "known_parent_ids": GOLDEN_PARENTS,
        "events": events,
    }


def test_golden_fixture_is_committed_and_matches_real_emitter_output():
    regenerated = _regenerate_fixture()
    assert len(regenerated["events"]) == 5
    if os.environ.get("GSA_T09_REGEN_FIXTURE") == "1":
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(
            json.dumps(regenerated, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    assert FIXTURE_PATH.exists(), (
        "committed golden fixture missing; regenerate with "
        "GSA_T09_REGEN_FIXTURE=1 pytest tests/test_convergence_t09_developmental_memory.py"
    )
    committed = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert committed == regenerated


@pytest.fixture(scope="module")
def golden() -> dict[str, Any]:
    if not FIXTURE_PATH.exists():  # pragma: no cover - guarded by skip
        pytest.skip(f"T09 golden fixture absent at {FIXTURE_PATH}")
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_golden_all_five_types_flow_through_real_durable_gate(tmp_path, golden):
    ledger = LedgerStore(tmp_path / "memory-ledger")
    for envelope in golden["events"]:
        result = persist_developmental_event(
            ledger,
            envelope,
            local_model_sha256=golden["domain_model_sha256"],
            known_parent_ids=golden["known_parent_ids"],
        )
        assert result["status"] == "first"
        assert result["record"]["classification"] == "developmental"

    history = read_developmental_history(ledger)
    assert history["counts_by_type"] == {
        "SettlementRecorded": 1,
        "RepetitionPlanned": 1,
        "LearningProposalCreated": 1,
        "CoherenceBreakDetected": 1,
        "CapabilityUpdated": 1,
    }
    assert history["settlement_count"] == 1
    assert history["promotion_count"] == 1
    assert history["promotions"][0]["payload"]["target_lifecycle"] == "active"

    stored = _rows(ledger)
    assert [row["event_type"] for row in stored] == [
        envelope["event_type"] for envelope in golden["events"]
    ]
    first = stored[0]
    assert first["payload"]["source_evidence_refs"] == [GOLDEN_PARENTS[0]]
    assert first["provenance"]["chain"][1:] == [
        f"caused_by:{parent}" for parent in GOLDEN_PARENTS
    ]


# --- TOOTH 1: one pristine successful cycle can never promote metabolized -----


def test_tooth_1_pristine_single_success_cannot_promote_metabolized(store):
    _admit_settlements(store, [("set-001", 0.9, "ctx-alpha")])
    with pytest.raises(DomainRuleError) as err:
        _persist(store, _promotion(target="metabolized"))
    assert err.value.code == "capability_requires_repeated_settlement"
    assert len(_rows(store)) == 1
    history = read_developmental_history(store)
    assert history["promotion_count"] == 0


def test_two_identical_condition_successes_cannot_promote_metabolized(store):
    _admit_settlements(
        store, [("set-a", 0.95, "ctx-alpha"), ("set-b", 0.95, "ctx-alpha")]
    )
    with pytest.raises(DomainRuleError) as err:
        _persist(
            store,
            _promotion(target="metabolized", evidence_refs=["set-a", "set-b"]),
        )
    assert err.value.code == "variation_not_demonstrated"


def test_three_successes_without_declared_variation_are_refused(store):
    _admit_settlements(
        store,
        [("set-a", 0.9, None), ("set-b", 0.9, None), ("set-c", 0.9, None)],
    )
    with pytest.raises(DomainRuleError) as err:
        _persist(
            store,
            _promotion(
                target="metabolized", evidence_refs=["set-a", "set-b", "set-c"]
            ),
        )
    assert err.value.code == "undeclared_variation"
    assert len(_rows(store)) == 3


def test_promotion_citing_unrecorded_settlement_refs_is_refused(store):
    with pytest.raises(DomainRuleError) as err:
        _persist(store, _promotion(evidence_refs=["set-fabricated"]))
    assert err.value.code == "unresolved_capability_evidence"


def test_promotion_cannot_cite_another_capabilitys_settlements(store):
    _admit_settlements(
        store, [("set-cap-a", 0.9, "ctx-alpha"), ("set-cap-a-2", 0.95, "ctx-beta")]
    )
    with pytest.raises(DomainRuleError) as err:
        _persist(
            store,
            _promotion(
                capability="aff-other-capability",
                target="metabolized",
                evidence_refs=["set-cap-a", "set-cap-a-2"],
            ),
        )
    assert err.value.code == "unresolved_capability_evidence"
    assert read_developmental_history(store)["promotion_count"] == 0


def test_mixed_real_and_fabricated_variation_evidence_is_refused(store):
    _admit_settlements(store, [("set-real", 0.9, "ctx-alpha")])
    with pytest.raises(DomainRuleError) as err:
        _persist(
            store,
            _promotion(target="repeated", evidence_refs=["set-real", "set-fake"]),
        )
    assert err.value.code == "unresolved_capability_evidence"


def test_low_scoring_successes_fail_the_capability_bar(store):
    _admit_settlements(
        store,
        [("set-a", 0.4, "ctx-alpha"), ("set-b", 0.5, "ctx-beta")],
    )
    with pytest.raises(DomainRuleError) as err:
        _persist(
            store,
            _promotion(target="metabolized", evidence_refs=["set-a", "set-b"]),
        )
    assert err.value.code == "capability_requires_repeated_settlement"


def test_inline_post_hoc_variation_declaration_is_ignored(store):
    _admit_settlements(
        store, [("set-a", 0.9, None), ("set-b", 0.9, None)]
    )
    gamed_decision = _decision(
        variations_performed=["ctx-x", "ctx-y"],
        declared_variations=["ctx-x", "ctx-y"],
    )
    with pytest.raises(DomainRuleError) as err:
        _persist(
            store,
            _promotion(
                target="metabolized",
                evidence_refs=["set-a", "set-b"],
                decision=gamed_decision,
            ),
        )
    assert err.value.code == "undeclared_variation"


def test_borderline_three_varied_high_scoring_settlements_earn_metabolized(store):
    """Composition pin: exactly the bar infer_capability_lifecycle +
    compute_metabolization impose — three successes, two distinct declared
    variations, mean score high enough for stability."""
    _admit_settlements(
        store,
        [
            ("set-a", 0.95, "ctx-alpha"),
            ("set-b", 0.95, "ctx-alpha"),
            ("set-c", 0.95, "ctx-beta"),
        ],
    )
    result = _persist(
        store,
        _promotion(target="metabolized", evidence_refs=["set-a", "set-b", "set-c"]),
    )
    assert result["status"] == "first"
    history = read_developmental_history(store)
    assert history["promotions"][-1]["payload"]["target_lifecycle"] == "metabolized"


def test_lower_status_thresholds_stay_explicitly_distinct(tmp_path):
    """Frozen known confound: statuses BELOW metabolized may have lower valid
    thresholds — preserved here rather than collapsed into one bar."""
    active_store = LedgerStore(tmp_path / "active-scenario")
    _admit_settlements(active_store, [("set-1", 0.9, "ctx-alpha")])
    active_result = _persist(
        active_store, _promotion(target="active", evidence_refs=["set-1"])
    )
    assert active_result["status"] == "first"

    repeated_store = LedgerStore(tmp_path / "repeated-scenario")
    _admit_settlements(
        repeated_store, [("set-1", 0.9, "ctx-alpha"), ("set-2", 0.9, "ctx-alpha")]
    )
    repeated_result = _persist(
        repeated_store, _promotion(target="repeated", evidence_refs=["set-1", "set-2"])
    )
    assert repeated_result["status"] == "first"
    with pytest.raises(DomainRuleError):
        _persist(
            repeated_store,
            _promotion(target="metabolized", evidence_refs=["set-1", "set-2"]),
        )


@pytest.mark.parametrize("target", ["latent", "brittle", "retired"])
def test_non_promotion_targets_are_refused_at_projection(store, target):
    with pytest.raises(DomainRuleError) as err:
        _promotion(target=target)
    assert err.value.code == "invalid_promotion_target"


def test_empty_variation_evidence_is_a_degenerate_claim(store):
    with pytest.raises(DomainRuleError) as err:
        _persist(store, _promotion(target="active", evidence_refs=[]))
    assert err.value.code == "provenance_stripped"


# --- TOOTH 2: identical redelivery creates zero duplicate history -------------


def test_tooth_2_identical_envelope_redelivery_creates_no_duplicate_history(store):
    envelope = _settlement()
    first = _persist(store, envelope)
    second = _persist(store, copy.deepcopy(envelope))
    third = _persist(store, copy.deepcopy(envelope))
    assert first["status"] == "first"
    assert second["status"] == "duplicate"
    assert third["status"] == "duplicate"
    assert second["record"] is None
    assert len(_rows(store)) == 1
    assert read_developmental_history(store)["settlement_count"] == 1


def test_redelivery_survives_process_restart_via_durable_replay(tmp_path, store):
    envelope = _settlement()
    assert _persist(store, envelope)["status"] == "first"

    reopened_store = LedgerStore(Path(store.root))
    fresh_state = load_developmental_memory_state(reopened_store)
    again = _persist(reopened_store, copy.deepcopy(envelope), state=fresh_state)
    assert again["status"] == "duplicate"
    assert len(_rows(reopened_store)) == 1

    cold = persist_developmental_event(
        reopened_store, copy.deepcopy(envelope), local_model_sha256=GOOD_HASH
    )
    assert cold["status"] == "duplicate"
    assert len(_rows(reopened_store)) == 1
    assert read_developmental_history(reopened_store)["settlement_count"] == 1


def test_same_content_under_new_event_id_duplicates_by_idempotency_key(store):
    original = _settlement(event_id=_fixed_id("dup-original"))
    redelivered = _settlement(event_id=_fixed_id("dup-redelivery"))
    assert original["idempotency_key"] == redelivered["idempotency_key"]
    assert original["event_id"] != redelivered["event_id"]
    assert _persist(store, original)["status"] == "first"
    assert _persist(store, redelivered)["status"] == "duplicate"
    assert len(_rows(store)) == 1


def test_replay_with_mutation_under_stable_identity_is_refused_by_name(store):
    envelope = _settlement()
    assert _persist(store, envelope)["status"] == "first"
    mutated = copy.deepcopy(envelope)
    mutated["payload"]["settlement_score"] = 0.4
    with pytest.raises(DomainRuleError) as err:
        _persist(store, mutated)
    assert err.value.code == "envelope_identity_conflict"
    rows = _rows(store)
    assert len(rows) == 1
    assert rows[0]["payload"]["settlement_score"] == 0.9


def test_duplicate_capability_promotion_leaves_single_history_row(store):
    _admit_settlements(store, [("set-1", 0.9, "ctx-alpha")])
    envelope = _promotion(target="active", evidence_refs=["set-1"])
    assert _persist(store, envelope)["status"] == "first"
    assert _persist(store, copy.deepcopy(envelope))["status"] == "duplicate"
    history = read_developmental_history(store)
    assert history["promotion_count"] == 1
    assert len(_rows(store)) == 2


# --- TOOTH 3: stripped provenance is quarantined, never authoritative ---------

_STRIP_MUTATIONS = {
    "absent": lambda payload: payload.pop("source_evidence_refs"),
    "none": lambda payload: payload.__setitem__("source_evidence_refs", None),
    "empty_list": lambda payload: payload.__setitem__("source_evidence_refs", []),
    "blank_string_entry": lambda payload: payload.__setitem__(
        "source_evidence_refs", [""]
    ),
    "whitespace_entry": lambda payload: payload.__setitem__(
        "source_evidence_refs", ["   "]
    ),
    "placeholder_token": lambda payload: payload.__setitem__(
        "source_evidence_refs", ["placeholder"]
    ),
    "not_a_list": lambda payload: payload.__setitem__("source_evidence_refs", "set-001"),
    "null_entry": lambda payload: payload.__setitem__("source_evidence_refs", [None]),
}


@pytest.mark.parametrize("case", sorted(_STRIP_MUTATIONS))
def test_tooth_3_stripped_source_evidence_refs_are_quarantined(tmp_path, case):
    ledger = LedgerStore(tmp_path / f"memory-ledger-{case}")
    envelope = _settlement()
    _STRIP_MUTATIONS[case](envelope["payload"])
    with pytest.raises(DomainRuleError) as err:
        _persist(ledger, envelope)
    if case in ("absent", "none"):
        assert err.value.code == "incomplete_developmental_event"
    else:
        assert err.value.code == "provenance_stripped"
    assert _rows(ledger) == []
    assert not (Path(ledger.root) / "ledgers" / f"{DEVELOPMENTAL_LEDGER}.jsonl").exists()


def test_caused_by_chain_stripped_after_emission_is_refused(store):
    envelope = _settlement()
    envelope["provenance"]["chain"] = [
        entry
        for entry in envelope["provenance"]["chain"]
        if not entry.startswith("caused_by:")
    ]
    with pytest.raises(DomainRuleError) as err:
        _persist(store, envelope)
    assert err.value.code == "causality_missing"
    assert _rows(store) == []


def test_malformed_parent_reference_refused_at_emission():
    with pytest.raises(DomainRuleError) as err:
        _settlement(parents=["not-a-well-formed-id"])
    assert err.value.code == "malformed_parent_reference"
    with pytest.raises(DomainRuleError) as err:
        _settlement(parents=[])
    assert err.value.code == "causality_missing"


def test_forged_parent_against_pinned_upstream_ids_is_refused(store):
    envelope = _settlement(parents=[EVIDENCE_ID_2])
    with pytest.raises(DomainRuleError) as err:
        _persist(store, envelope, known_parent_ids=[EVIDENCE_ID])
    assert err.value.code == "forged_parent_reference"
    assert _rows(store) == []


def test_admitted_records_retain_provenance_verbatim(store):
    refs = [EVIDENCE_ID, EVIDENCE_ID_2]
    envelope = _settlement(refs=refs, parents=[EVIDENCE_ID, EVIDENCE_ID_2])
    assert _persist(store, envelope)["status"] == "first"
    stored = _rows(store)[0]
    assert stored["payload"]["source_evidence_refs"] == refs
    assert stored["provenance"]["chain"][-2:] == [
        f"caused_by:{EVIDENCE_ID}",
        f"caused_by:{EVIDENCE_ID_2}",
    ]
    assert stored["payload"]["developmental_decision"] == _decision()


# --- Exclusive producer authority over ALL FIVE types -------------------------


_FORGING_PRODUCERS = [
    "realitytrace",
    "swe-seed",
    "sea-forge",
    "context-kernel",
    "memory-ledger",
]


@pytest.mark.parametrize("event_type", DEVELOPMENTAL_EVENT_TYPES)
@pytest.mark.parametrize("forger", _FORGING_PRODUCERS)
def test_wrong_producer_refused_for_every_developmental_type(store, event_type, forger):
    envelope = _emit(event_type, payload=_type_payload(event_type))
    envelope["source_agent"] = forger
    with pytest.raises(DomainRuleError) as err:
        ingest_developmental_event(envelope, state=DevelopmentalMemoryState())
    assert err.value.code == "producer_forge"


def test_provenance_origin_contradicting_the_stamp_is_refused():
    envelope = _settlement()
    envelope["provenance"]["origin"] = "realitytrace"
    with pytest.raises(DomainRuleError) as err:
        ingest_developmental_event(envelope, state=DevelopmentalMemoryState())
    assert err.value.code == "producer_forge"


def test_non_developmental_event_types_are_not_ingestable_here():
    envelope = _settlement()
    envelope["event_type"] = "DevelopmentalMemory"
    with pytest.raises(DomainRuleError) as err:
        ingest_developmental_event(envelope, state=DevelopmentalMemoryState())
    assert err.value.code == "wrong_event_type"


# --- Identity gates: placeholders, drift, namespace ---------------------------


@pytest.mark.parametrize(
    "bad_hash",
    [FALLBACK_PSEUDO_HASH, ZERO_HASH, "abc123", "A" * 64],
)
def test_placeholder_and_malformed_domain_identity_never_project(bad_hash):
    with pytest.raises(DomainRuleError):
        _settlement(model_hash=bad_hash)


def test_hash_drift_against_locally_resolved_model_is_refused(store):
    envelope = _settlement(model_hash=OTHER_HASH)
    with pytest.raises(DomainRuleError) as err:
        _persist(store, envelope, local_model_sha256=GOOD_HASH)
    assert err.value.code == "hash_drift"
    assert _rows(store) == []


def test_namespace_tampering_is_refused(store):
    envelope = _settlement()
    envelope["payload"]["namespace"] = "someone_else_loop"
    with pytest.raises(DomainRuleError) as err:
        _persist(store, envelope)
    assert err.value.code == "namespace_tampering"

    tampered_ref = _settlement()
    tampered_ref["payload"]["domain_model_ref"]["namespace"] = "someone_else_loop"
    with pytest.raises(DomainRuleError) as err:
        _persist(store, tampered_ref)
    assert err.value.code == "namespace_tampering"

    swapped_ref = _settlement()
    swapped_ref["payload"]["domain_model_ref"]["model_hash"] = OTHER_HASH
    with pytest.raises(DomainRuleError) as err:
        _persist(store, swapped_ref)
    assert err.value.code == "ref_identity_mismatch"


# --- Missing-field battery over the four common requirements ------------------


@pytest.mark.parametrize("field_name", COMMON_REQUIRED_FIELDS)
def test_each_missing_common_field_is_reported(store, field_name):
    envelope = _settlement()
    del envelope["payload"][field_name]
    with pytest.raises(DomainRuleError) as err:
        _persist(store, envelope)
    assert err.value.code == "incomplete_developmental_event"
    assert field_name in str(err.value)


def test_all_four_common_fields_missing_reported_together(store):
    envelope = _settlement()
    for field_name in COMMON_REQUIRED_FIELDS:
        del envelope["payload"][field_name]
    with pytest.raises(DomainRuleError) as err:
        _persist(store, envelope)
    message = str(err.value)
    for field_name in sorted(COMMON_REQUIRED_FIELDS):
        assert field_name in message


# --- Degenerate value battery -------------------------------------------------


@pytest.mark.parametrize("bad_decision", [{}, [], "promote_capability"])
def test_degenerate_developmental_decision_is_refused(store, bad_decision):
    with pytest.raises(DomainRuleError) as err:
        _settlement(decision=bad_decision)
    assert err.value.code == "degenerate_developmental_decision"


@pytest.mark.parametrize("bad_count", [0, -1, "3", True, 1.5, None])
def test_degenerate_repetition_count_is_refused(bad_count):
    with pytest.raises(DomainRuleError) as err:
        _emit(
            "RepetitionPlanned",
            payload={"affordance_id": CAPABILITY, "repetition_count": bad_count},
        )
    assert err.value.code == "degenerate_field_value"


@pytest.mark.parametrize("bad_score", [1.5, -0.1, "high", True])
def test_out_of_range_settlement_score_is_refused(bad_score):
    with pytest.raises(DomainRuleError) as err:
        _settlement(score=bad_score)
    assert err.value.code == "degenerate_field_value"


def test_blank_work_request_id_is_a_degenerate_identity(store):
    with pytest.raises(DomainRuleError) as err:
        _settlement(wr="   ")
    assert err.value.code == "degenerate_field_value"


def test_failed_settlements_remain_recorded_but_never_count_as_capability(
    store,
):
    result = _persist(
        store, _settlement("set-fail", status="failed", score=0.2, variation=None)
    )
    assert result["status"] == "first"
    with pytest.raises(DomainRuleError):
        _persist(store, _promotion(target="active", evidence_refs=["set-fail"]))
    history = read_developmental_history(store)
    assert history["settlement_count"] == 1
    assert history["promotion_count"] == 0


# --- Every reachable promotion surface hits the SAME gate ---------------------


def test_runtime_request_capability_promotion_surface_refuses_unearned(tmp_path):
    runtime = NavigationRuntime(tmp_path / "harness")
    with pytest.raises(DomainRuleError) as err:
        runtime.request_capability_promotion(
            CAPABILITY,
            "metabolized",
            variation_evidence=["set-none"],
            work_request_id=WORK_REQUEST_ID,
            source_evidence_refs=[EVIDENCE_ID],
            domain_model_sha256=GOOD_HASH,
            parent_evidence_ids=[EVIDENCE_ID],
        )
    assert err.value.code == "unresolved_capability_evidence"
    assert runtime.store.read_events(DEVELOPMENTAL_LEDGER) == []
    assert runtime.snapshot()["counts"]["capabilities"] == 0


def test_runtime_full_earned_path_promotes_through_runtime_surfaces(tmp_path):
    runtime = NavigationRuntime(tmp_path / "harness")
    specs = [
        ("set-r1", 0.95, "ctx-alpha"),
        ("set-r2", 0.95, "ctx-alpha"),
        ("set-r3", 0.95, "ctx-beta"),
    ]
    for ref, score, variation in specs:
        outcome = runtime.emit_developmental_event(
            "SettlementRecorded",
            work_request_id=WORK_REQUEST_ID,
            source_evidence_refs=[EVIDENCE_ID],
            developmental_decision=_decision(),
            domain_model_sha256=GOOD_HASH,
            parent_evidence_ids=[EVIDENCE_ID],
            payload={
                "affordance_id": CAPABILITY,
                "settlement_ref": ref,
                "settlement_status": "success",
                "settlement_score": score,
                "variation_context": variation,
            },
        )
        assert outcome["status"] == "first"

    promoted = runtime.request_capability_promotion(
        CAPABILITY,
        "metabolized",
        variation_evidence=["set-r1", "set-r2", "set-r3"],
        work_request_id=WORK_REQUEST_ID,
        source_evidence_refs=[EVIDENCE_ID],
        domain_model_sha256=GOOD_HASH,
        parent_evidence_ids=[EVIDENCE_ID],
        rationale="three varied settled repetitions survived",
    )
    assert promoted["status"] == "first"
    history = read_developmental_history(runtime.store)
    assert history["promotions"][-1]["payload"]["target_lifecycle"] == "metabolized"


def test_direct_bridge_route_gate_call_refuses_unearned_promotion(store):
    _admit_settlements(store, [("set-only", 0.9, "ctx-alpha")])
    with pytest.raises(DomainRuleError) as err:
        ingest_developmental_event(
            _promotion(evidence_refs=["set-only"]), state=load_developmental_memory_state(store)
        )
    assert err.value.code == "capability_requires_repeated_settlement"


def test_raw_ledger_row_bypassing_the_gate_is_quarantined_on_replay(store):
    _admit_settlements(store, [("set-ok", 0.9, "ctx-alpha")])
    forged = _promotion(target="metabolized", evidence_refs=["set-forged"])
    store.append_event(
        DEVELOPMENTAL_LEDGER,
        {
            "event_id": forged["event_id"],
            "stored_at": FIXED_NOW,
            "envelope": forged,
        },
    )
    history = read_developmental_history(store)
    assert history["promotion_count"] == 0
    assert any(
        q["code"] == "unresolved_capability_evidence"
        and q["event_id"] == forged["event_id"]
        for q in history["quarantined"]
    )


def test_publisher_offline_drain_forwards_nothing_unreviewed(store):
    _admit_settlements(store, [("set-p", 0.9, "ctx-alpha")])
    publisher = SettlementPublisher(enabled=False)
    assert publisher.enabled is False

    async def _drain() -> dict[str, int]:
        return await publisher.drain(store, DEVELOPMENTAL_LEDGER)

    counts = asyncio.run(_drain())
    assert counts["forwarded"] == 0

    with pytest.raises(DomainRuleError):
        ingest_developmental_event(
            _promotion(target="metabolized", evidence_refs=["set-p"]),
            state=load_developmental_memory_state(store),
        )


# --- Runtime coexistence with the existing settlement machinery ---------------


def test_canonical_layer_coexists_with_record_settlement_machinery(tmp_path):
    runtime = NavigationRuntime(tmp_path / "harness")
    runtime.store.append(
        "affordances",
        {
            "id": CAPABILITY,
            "direction_id": "dir-seed",
            "statement": "seeded executable affordance",
            "pathway": "seeded",
            "current_status": "affordance",
        },
    )
    internal = runtime.record_settlement(
        affordance_id=CAPABILITY,
        before_state={"connected": 0},
        after_state={"connected": 1},
        payment_actual={"time": 2},
        evidence=["internal workflow ran"],
        horizon_delta=3,
    )
    assert internal["status"] == "success"

    emitted = runtime.emit_developmental_event(
        "SettlementRecorded",
        work_request_id=WORK_REQUEST_ID,
        source_evidence_refs=[internal["id"]],
        developmental_decision=_decision(),
        domain_model_sha256=GOOD_HASH,
        parent_evidence_ids=[EVIDENCE_ID],
        payload={
            "affordance_id": CAPABILITY,
            "settlement_ref": internal["id"],
            "settlement_status": internal["status"],
            "settlement_score": internal["score"],
            "variation_context": "runtime-loop",
        },
    )
    assert emitted["status"] == "first"
    snapshot = runtime.snapshot()
    assert snapshot["counts"]["settlements"] == 1
    assert read_developmental_history(runtime.store)["settlement_count"] == 1


# --- Emitter/gate agreement ---------------------------------------------------


def test_emitter_stamps_exclusive_producer_and_four_common_fields_on_every_type():
    for event_type in DEVELOPMENTAL_EVENT_TYPES:
        envelope = _emit(event_type, payload=_type_payload(event_type))
        assert envelope["source_agent"] == "godspeed-agent"
        assert envelope["provenance"]["origin"] == "godspeed-agent"
        payload = envelope["payload"]
        for field_name in COMMON_REQUIRED_FIELDS:
            assert field_name in payload, (event_type, field_name)
        assert payload["domain_model_ref"] == {
            "namespace": "agentic_capability_loop",
            "model_hash": GOOD_HASH,
        }
        assert payload["namespace"] == "agentic_capability_loop"
        assert any(
            entry.startswith("caused_by:") for entry in envelope["provenance"]["chain"]
        )


def test_promotion_targets_table_keeps_declared_distinctions():
    assert PROMOTION_TARGETS == ("active", "repeated", "metabolized")
