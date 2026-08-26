"""Convergence T08 — canonical EvidenceRecorded ingestion at the frozen E8
boundary on the GodSpeed-Agent side (realitytrace -> godspeed_agent).

The golden fixture is written by the REAL sxr RealityTrace emitter
(``sxr-core/tests/convergence_t08_evidence_emission.rs``, composed behind the
REAL T07 ingestion gate). Everything here consumes that fixture through the
REAL Python gate and mutates it to prove the negative space.

Frozen contract (sea-rs ``.agents/specs/e2e-preregistration.yml``):
- E8: EvidenceRecorded carries nine required fields; RealityTrace binds
  declared expectation to observed consequence; EvidenceRecorded is
  PROVISIONAL developmental evidence and MUST NOT itself create
  SettlementRecorded, CapabilityUpdated, or metabolized capability.
- I8: EvidenceRecorded remains provisional until independently evaluated by
  GodSpeed-Agent (explicit settlement action only).
- I10: downstream components cannot silently mutate upstream semantic facts.

Plan teeth (named tests):
  TOOTH 1 — missing expected OR observed consequence ⇒ rejected;
  TOOTH 2 — forged parent/proof/settlement refs ⇒ rejected;
  TOOTH 3 — receipt alone creates NO SettlementRecorded/CapabilityUpdated
            anywhere.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from godspeed_nav.evidence_ingest import (
    FALLBACK_PSEUDO_HASH,
    PRODUCER,
    REQUIRED_FIELDS,
    ZERO_HASH,
    EvidenceIngestState,
    ProvisionalEvidence,
    ingest_evidence_recorded,
)
from godspeed_nav.runtime import NavigationRuntime
from godspeed_nav.schemas import DomainRuleError

GOOD_HASH = "a" * 64
WORK_REQUEST_ID = "wr-gsf-001"
AFFORDANCE_ID = "aff-blue-green-001"

_FIXTURE_PATH = Path(
    os.environ.get(
        "SXR_ROOT",
        str(Path(__file__).resolve().parents[2] / "sxr"),
    )
) / "sxr-core" / "tests" / "fixtures" / "t08_evidence_recorded.json"


def _fixture() -> dict[str, Any]:
    if not _FIXTURE_PATH.exists():  # pragma: no cover - guarded by skipif
        pytest.skip(f"sxr emitter golden fixture absent at {_FIXTURE_PATH}")
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def golden() -> dict[str, Any]:
    return _fixture()


#: The locally-resolved model digest THIS deployment binds against — the one
#: the real sxr emitter stamped into the golden fixture.
if _FIXTURE_PATH.exists():  # pragma: no branch - fixture ships with the tree
    MODEL_HASH = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))[
        "domain_model_sha256"
    ]
else:  # pragma: no cover - only when the sxr checkout is absent
    MODEL_HASH = "a" * 64


def _envelope(golden: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(golden["evidence_recorded"])


def _gate(
    envelope: dict[str, Any],
    state: EvidenceIngestState | None = None,
    *,
    expected_work_request_id: str = WORK_REQUEST_ID,
    known_parent_ids: list[str] | None = None,
    model_hash: str | None = None,
):
    return ingest_evidence_recorded(
        envelope,
        local_model_sha256=model_hash or MODEL_HASH,
        expected_work_request_id=expected_work_request_id,
        state=state if state is not None else EvidenceIngestState(),
        known_parent_ids=known_parent_ids,
    )


def _known_parents(golden: dict[str, Any]) -> list[str]:
    return list(golden["known_parent_ids"])


def digest(value: Any) -> str:
    """Bare sha256 over canonical JSON — mirrors sxr's difference digests."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# --- Positive path: REAL emitter output through the REAL gate ---------------------


def test_golden_fixture_from_the_real_sxr_emitter_is_gated_provisional(golden):
    envelope = _envelope(golden)
    assert envelope["source_agent"] == "realitytrace"
    assert envelope["event_type"] == "EvidenceRecorded"
    state = EvidenceIngestState()

    admission = _gate(envelope, state)
    assert admission.status == "first"
    record = admission.record
    assert isinstance(record, ProvisionalEvidence)
    assert record.classification == "provisional"

    # All nine frozen required fields bind to exactly what sxr projected.
    payload = envelope["payload"]
    assert record.event_id == envelope["event_id"]
    assert record.work_request_id == payload["work_request_id"] == WORK_REQUEST_ID
    assert record.affordance_id == payload["affordance_id"] == AFFORDANCE_ID
    # Verbatim projection, no invention: expected/observed ride byte-exactly.
    assert record.expected_outcome == payload["expected_outcome"]
    assert record.observed_outcome == payload["observed_outcome"]
    assert record.difference == payload["difference"]
    assert record.proof_result_ref == payload["proof_result_ref"]
    assert record.operational_settlement_ref == payload["operational_settlement_ref"]
    assert record.domain_model_hash == MODEL_HASH == golden["domain_model_sha256"]
    assert record.verdict in ("equivalent", "divergent")

    # Causality cites the upstream ids sxr bound during E7 ingestion.
    chain = envelope["provenance"]["chain"]
    assert f"caused_by:{golden['expected_settlement_event_id']}" in chain
    assert f"caused_by:{golden['proof_event_id']}" in chain

    # Redelivery under stable identity is consequence-free.
    replay = _gate(envelope, state)
    assert replay.status == "duplicate"
    assert replay.record is None
    assert len(state.claims) == 1


# --- TOOTH 1: missing expected OR observed consequence ⇒ rejected ------------------


@pytest.mark.parametrize("field_name", sorted(REQUIRED_FIELDS[1:]))
def test_tooth1_every_frozen_required_field_is_mandatory(golden, field_name):
    envelope = _envelope(golden)
    del envelope["payload"][field_name]
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code == "incomplete_evidence_recorded"
    assert field_name in str(err.value)


def test_tooth1_missing_expected_outcome_is_rejected(golden):
    envelope = _envelope(golden)
    envelope["payload"]["expected_outcome"] = None
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code == "incomplete_evidence_recorded"


def test_tooth1_missing_observed_outcome_is_rejected(golden):
    envelope = _envelope(golden)
    del envelope["payload"]["observed_outcome"]
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code == "incomplete_evidence_recorded"
    assert "observed_outcome" in str(err.value)


def test_tooth1_blank_observed_value_cannot_bind(golden):
    envelope = _envelope(golden)
    envelope["payload"]["observed_outcome"] = ""
    with pytest.raises(DomainRuleError):
        _gate(envelope)


# --- TOOTH 2: forged parent/proof/settlement refs ⇒ rejected -----------------------


def test_tooth2_parent_citation_outside_pinned_upstream_ids_is_a_forged_reference(
    golden,
):
    envelope = _envelope(golden)
    envelope["provenance"]["chain"].append(
        "caused_by:99999999-9999-4999-8999-999999999999"
    )
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope, known_parent_ids=_known_parents(golden))
    assert err.value.code == "forged_parent_reference"


def test_tooth2_malformed_parent_id_in_chain_is_refused(golden):
    envelope = _envelope(golden)
    envelope["provenance"]["chain"] = [
        f"domain_model_hash:{GOOD_HASH}",
        "caused_by:not-an-event-id",
    ]
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code == "causality_missing"


def test_tooth2_zero_causality_is_refused(golden):
    envelope = _envelope(golden)
    envelope["provenance"]["chain"] = [f"domain_model_hash:{GOOD_HASH}"]
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code == "causality_missing"


def test_tooth2_provenance_origin_contradicting_the_producer_stamp_forges(golden):
    envelope = _envelope(golden)
    envelope["provenance"]["origin"] = "godspeed-agent"
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code == "producer_forge"


@pytest.mark.parametrize(
    ("field_name", "forged"),
    [
        ("proof_result_ref", "not-a-reference"),
        ("proof_result_ref", "sha256:deadbeef"),
        ("operational_settlement_ref", "path/to/settlement.json"),
        ("operational_settlement_ref", "sha256:" + "z" * 64),
    ],
)
def test_tooth2_forged_proof_and_settlement_refs_are_rejected(
    golden, field_name, forged
):
    envelope = _envelope(golden)
    envelope["payload"][field_name] = forged
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code == "invalid_ref"


# --- TOOTH 3: receipt alone creates NO settlement/capability anywhere --------------


def _seed_affordance(runtime: NavigationRuntime, affordance_id: str) -> None:
    runtime.store.append(
        "affordances",
        {
            "id": affordance_id,
            "direction_id": "dir-t08",
            "statement": "seeded executable affordance for T08",
            "pathway": "seeded",
            "current_status": "affordance",
        },
    )


_DERIVED_LEDGERS = (
    "settlements",
    "trajectories",
    "capabilities",
    "repetition_schedules",
)


def test_tooth3_receipt_creates_no_settlement_or_capability_anywhere(golden, tmp_path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, AFFORDANCE_ID)

    before = {name: len(runtime.store.read(name)) for name in _DERIVED_LEDGERS}
    assert before == {name: 0 for name in _DERIVED_LEDGERS}

    result = runtime.ingest_canonical_evidence_recorded(
        _envelope(golden),
        local_model_sha256=MODEL_HASH,
        expected_work_request_id=WORK_REQUEST_ID,
        known_parent_ids=_known_parents(golden),
    )

    # Receipt yields a provisional record ONLY.
    assert result["status"] == "provisional_recorded"
    stored = result["record"]
    assert stored["classification"] == "provisional"
    assert stored["source_event_type"] == "EvidenceRecorded"
    assert stored["source_producer"] == "realitytrace"

    # NOWHERE else did anything move: no settlements, capabilities,
    # trajectories, repetition schedules, and not even the legacy evidence
    # ledger was touched by the canonical path.
    after = {name: len(runtime.store.read(name)) for name in _DERIVED_LEDGERS}
    assert after == before, "receipt must never write derived/settlement state"
    assert len(runtime.store.read("canonical_execution_evidence")) == 1
    assert runtime.store.read_events("execution_evidence") == []

    # And a full redelivery stores nothing further.
    duplicate = runtime.ingest_canonical_evidence_recorded(
        _envelope(golden),
        local_model_sha256=MODEL_HASH,
        expected_work_request_id=WORK_REQUEST_ID,
        known_parent_ids=_known_parents(golden),
    )
    assert duplicate["status"] == "duplicate"
    assert len(runtime.store.read("canonical_execution_evidence")) == 1


def test_provisional_evidence_exposes_no_promotion_surface():
    """Machine-checkable I8: the provisional type has NO promotion method."""
    record = ProvisionalEvidence(
        event_id="0000000b-0000-4000-8000-00000000c002",
        work_request_id=WORK_REQUEST_ID,
        affordance_id=AFFORDANCE_ID,
        expected_outcome={"declared": "green"},
        observed_outcome=["green"],
        difference={
            "verdict": "divergent",
            "expected_sha256": "1" * 64,
            "observed_sha256": "2" * 64,
        },
        proof_result_ref="sha256:" + "3" * 64,
        operational_settlement_ref="sha256:" + "4" * 64,
        domain_model_hash=GOOD_HASH,
        verdict="divergent",
    )
    forbidden_fragments = (
        "promote",
        "settle",
        "capability",
        "metaboliz",
        "record_",
        "emit",
        "update",
        "ingest",
    )
    # The CALLABLE surface must contain no promotion-shaped method at all;
    # frozen data fields (e.g. operational_settlement_ref) are inert data.
    surface = [name for name in dir(record) if not name.startswith("_")]
    for name in surface:
        attribute = getattr(record, name)
        if not callable(attribute):
            continue
        for fragment in forbidden_fragments:
            assert fragment not in name.lower(), (
                f"provisional record exposes promotion-shaped API: {name}"
            )
    allowed_callables = {"to_ledger_record"}
    for name in surface:
        if callable(getattr(record, name)):
            assert name in allowed_callables, (
                f"unexpected public callable on provisional record: {name}"
            )
    for attempt in (
        "record_settlement",
        "promote_capability",
        "emit_settlement_recorded",
        "record_developmental_settlement",
        "update_capability",
    ):
        with pytest.raises(AttributeError):
            getattr(record, attempt)

    # The carried value graph is inert data: no runtime, store, or callable
    # references that could route back into promotion machinery.
    for value in vars(record).values():
        assert not callable(value)
        assert not isinstance(value, NavigationRuntime)


def test_runtime_unknown_affordance_fails_closed_without_any_write(golden, tmp_path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    before = {name: len(runtime.store.read(name)) for name in _DERIVED_LEDGERS}
    with pytest.raises(DomainRuleError) as err:
        runtime.ingest_canonical_evidence_recorded(
            _envelope(golden),
            local_model_sha256=MODEL_HASH,
            expected_work_request_id=WORK_REQUEST_ID,
        )
    assert err.value.code == "settlement_requires_executable_affordance"
    after = {name: len(runtime.store.read(name)) for name in _DERIVED_LEDGERS}
    assert after == before
    assert runtime.store.read("canonical_execution_evidence") == []


# --- Producer authority both directions --------------------------------------------


@pytest.mark.parametrize(
    "impostor",
    [
        "swe-seed",
        "sea-forge",
        "godspeed-agent",
        "execution-environment",
        "external-environment",
        "mystery-component",
        "",
    ],
)
def test_wrong_producers_are_refused_in_both_directions(golden, impostor):
    envelope = _envelope(golden)
    envelope["source_agent"] = impostor
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code == "producer_forge", impostor

    # This gate ingests ONLY EvidenceRecorded: GSA's own outbound event types
    # (and any other type) are refused outright.
    for foreign in ("SettlementRecorded", "CapabilityUpdated", "ProofCompleted"):
        other = _envelope(golden)
        other["event_type"] = foreign
        with pytest.raises(DomainRuleError) as err:
            _gate(other)
        assert err.value.code == "wrong_event_type"


# --- Identity gates -----------------------------------------------------------------


@pytest.mark.parametrize("pseudo", [FALLBACK_PSEUDO_HASH, ZERO_HASH])
def test_placeholder_identity_hashes_are_refused_exactly_as_in_rust(golden, pseudo):
    envelope = _envelope(golden)
    envelope["payload"]["domain_model_hash"] = pseudo
    envelope["payload"]["domain_model_ref"]["model_hash"] = pseudo
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code in (
        "fallback_domain_hash_forbidden",
        "malformed_domain_identity",
    )


def test_drift_against_locally_resolved_model_is_refused(golden):
    # The envelope names a DIFFERENT model than the one this deployment
    # resolves: cross-repo drift, refused (ENV-I1).
    envelope = _envelope(golden)
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope, model_hash="b" * 64)
    assert err.value.code == "hash_drift"


def test_domain_model_ref_rewriting_declared_identity_is_refused(golden):
    envelope = _envelope(golden)
    envelope["payload"]["domain_model_ref"]["model_hash"] = digest({"other": "model"})
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope)
    assert err.value.code == "ref_identity_mismatch"


@pytest.mark.parametrize("placeholder", ["placeholder", "<missing>", "tbd"])
def test_placeholder_correlation_strings_are_refused(golden, placeholder):
    for field_name in ("work_request_id", "affordance_id"):
        envelope = _envelope(golden)
        envelope["payload"][field_name] = placeholder
        with pytest.raises(DomainRuleError) as err:
            _gate(envelope)
        assert err.value.code == "placeholder_field", field_name


# --- Namespace / schema tampering ----------------------------------------------------


def test_namespace_and_schema_tampering_is_refused(golden):
    tampered = _envelope(golden)
    tampered["payload"]["namespace"] = "some_other_namespace"
    with pytest.raises(DomainRuleError) as err:
        _gate(tampered)
    assert err.value.code == "namespace_tampering"

    tampered = _envelope(golden)
    tampered["payload"]["domain_model_ref"]["namespace"] = "other"
    with pytest.raises(DomainRuleError) as err:
        _gate(tampered)
    assert err.value.code == "namespace_tampering"

    tampered = _envelope(golden)
    tampered["schema_version"] = "v2"
    with pytest.raises(DomainRuleError) as err:
        _gate(tampered)
    assert err.value.code == "malformed_envelope"

    with pytest.raises(DomainRuleError) as err:
        _gate([1, 2, 3])
    assert err.value.code == "malformed_envelope"


def test_cross_wired_work_request_is_refused(golden):
    envelope = _envelope(golden)
    envelope["payload"]["work_request_id"] = "wr-not-this-cycle"
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope, expected_work_request_id=WORK_REQUEST_ID)
    assert err.value.code == "cross_wired_work_request"


# --- Duplicate / replay idempotency ---------------------------------------------------


def test_duplicate_delivery_and_identical_rewrap_are_consequence_free(golden):
    envelope = _envelope(golden)
    state = EvidenceIngestState()
    first = _gate(envelope, state)
    assert first.status == "first"
    recorded_before = (len(state.seen_identities), len(state.claims))

    # Exact replay…
    replay = _gate(_envelope(golden), state)
    assert replay.status == "duplicate"

    # …and a re-wrapped envelope (fresh event id) carrying IDENTICAL claims:
    # the settled cycle already stands, so nothing is appended twice.
    rewrapped = _envelope(golden)
    rewrapped["event_id"] = "0000000b-0000-4000-8000-00000000d001"
    rewrapped.pop("idempotency_key", None)
    rewrap = _gate(rewrapped, state)
    assert rewrap.status == "duplicate"
    assert (len(state.seen_identities), len(state.claims)) == recorded_before


def test_duplicate_recognition_survives_a_restart_of_the_gate_state(golden):
    envelope = _envelope(golden)
    state = EvidenceIngestState()
    assert _gate(envelope, state).status == "first"

    serialized = json.dumps(
        {
            "seen_identities": state.seen_identities,
            "claims": state.claims,
        }
    )
    reopened = EvidenceIngestState()
    restored = json.loads(serialized)
    reopened.seen_identities = restored["seen_identities"]
    reopened.claims = restored["claims"]
    replay = _gate(_envelope(golden), reopened)
    assert replay.status == "duplicate"


# --- I10 probes: divergent resubmission must be detected and named --------------------


def test_i10_mutated_observation_with_stale_difference_is_detected_and_named(golden):
    envelope = _envelope(golden)
    state = EvidenceIngestState()
    original = _gate(envelope, state)
    assert original.status == "first"

    probe = _envelope(golden)
    probe["event_id"] = "0000000b-0000-4000-8000-00000000e001"
    probe.pop("idempotency_key", None)
    probe["payload"]["observed_outcome"] = [{"effect": "REWRITTEN AFTER THE FACT"}]
    with pytest.raises(DomainRuleError) as err:
        _gate(probe, state)
    assert err.value.code == "difference_binding_mismatch"
    assert "observed_sha256" in str(err.value)

    # The FIRST record stands untouched.
    assert len(state.claims) == 1
    assert json.loads(state.claims[0]["claim"]["observed_canonical"]) == (
        envelope["payload"]["observed_outcome"]
    )


def test_i10_consistently_restacked_divergent_resubmission_hits_claim_stability(
    golden,
):
    envelope = _envelope(golden)
    state = EvidenceIngestState()
    original = _gate(envelope, state)
    assert original.status == "first"

    probe = _envelope(golden)
    probe["event_id"] = "0000000b-0000-4000-8000-00000000e002"
    probe.pop("idempotency_key", None)
    mutated_expected = dict(probe["payload"]["expected_outcome"])
    mutated_expected["declared_result"] = "REWRITTEN AFTER THE FACT"
    probe["payload"]["expected_outcome"] = mutated_expected
    # The attacker restamps the difference digests consistently — internal
    # binding passes, but claim STABILITY still refuses by name.
    import hashlib

    def digest(value: Any) -> str:
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    probe["payload"]["difference"] = {
        "verdict": "divergent",
        "expected_sha256": digest(mutated_expected),
        "observed_sha256": digest(probe["payload"]["observed_outcome"]),
    }
    with pytest.raises(DomainRuleError) as err:
        _gate(probe, state)
    assert err.value.code == "claim_mismatch"
    assert "expected_canonical" in str(err.value)

    # Nothing moved: one recorded claim, identical to the first admission.
    assert len(state.claims) == 1
    assert json.loads(state.claims[0]["claim"]["expected_canonical"]) == (
        envelope["payload"]["expected_outcome"]
    )
    assert original.record.expected_outcome == envelope["payload"]["expected_outcome"]
