"""Stage 9 — GodSpeed-Agent world_ref boundary (CEP-0008).

GodSpeed-Agent pins ``world_ref`` on the requests it emits and checks it on the
evidence it receives. It checks syntax and equality only; the digest is
verified by SEA-Forge. Nothing here grants authority, and agent-local
settlement is never presented as SEA-Forge settlement.
"""

from __future__ import annotations

import pytest

from agentic_capability_loop.adapters import (
    detect_coherence_break,
    emit_capability_updated,
    emit_settlement_recorded,
    emit_twin_update,
    handle_evidence_recorded,
    schedule_repetition,
)
from godspeed_nav.canonical_events import (
    project_desired_direction,
    project_work_requested,
)
from godspeed_nav.evidence_ingest import EvidenceIngestState, ingest_evidence_recorded
from godspeed_nav.schemas import DomainRuleError
from godspeed_nav.world_ref import pinned_world_ref, verify_world_ref
from tests.test_convergence_t08_evidence_recorded import (
    MODEL_HASH,
    WORK_REQUEST_ID,
    _envelope,
    golden,  # noqa: F401  (fixture)
)

D = "b" * 64
WORLD = f"world:acme@sha256:{D}"
OTHER = f"world:acme@sha256:{'c' * 64}"
GOOD_HASH = "a" * 64


@pytest.fixture(autouse=True)
def _pin_world(monkeypatch):
    monkeypatch.setenv("GSA_WORLD_REF", WORLD)


# --- syntax gate (vectors shared with Context Kernel / SWE_SEED) -------------------


@pytest.mark.parametrize(
    "ok",
    [
        f"world:a@sha256:{D}",
        f"world:acme.core-v2_x@sha256:{D}",
        f"world:{'a' * 64}@sha256:{D}",
    ],
)
def test_well_formed_world_refs_pass(ok):
    assert verify_world_ref(ok) == ok


@pytest.mark.parametrize(
    "bad",
    [
        "",
        None,
        "world:acme",  # mutable alias
        "acme@sha256:" + D,
        f"world:Acme@sha256:{D}",
        f"world:acme@sha256:{D.upper()}",
        f"world:acme@sha256:{D}0",
        f"world:{'a' * 65}@sha256:{D}",
        f"world:a-@sha256:{D}",
        f"world:a..b@sha256:{D}",
        f"world:1a@sha256:{D}",
    ],
)
def test_alias_label_and_malformed_refs_are_refused(bad):
    with pytest.raises(DomainRuleError) as err:
        verify_world_ref(bad)
    assert err.value.code == "malformed_world_ref"


def test_pin_is_never_invented(monkeypatch):
    monkeypatch.delenv("GSA_WORLD_REF", raising=False)
    assert pinned_world_ref() is None


# --- work request (E0/E1) -----------------------------------------------------------


def _aff():
    return {
        "id": "aff-1",
        "statement": "deploy",
        "pathway": "build -> promote",
        "payment_estimate": {"burden": 1.0},
    }


def test_work_requested_pins_world_ref_and_grants_no_authority():
    event = project_work_requested(
        _aff(),
        work_request_id="wr-1",
        domain_model_hash=GOOD_HASH,
        settlement_criteria=["green"],
        world_ref=WORLD,
    )
    payload = event["payload"]
    assert payload["world_ref"] == WORLD
    assert f"world_ref:{WORLD}" in event["provenance"]["chain"]
    # A request is not a grant: no authority fields, no decision.
    assert not {k for k in payload if "authority" in k or "decision" in k}


def test_world_ref_is_not_derived_from_the_legacy_hash():
    event = project_work_requested(
        _aff(),
        work_request_id="wr-1",
        domain_model_hash=GOOD_HASH,
        settlement_criteria=["green"],
        world_ref=WORLD,
    )
    assert GOOD_HASH not in event["payload"]["world_ref"]


def test_work_requested_cannot_be_emitted_without_a_world():
    with pytest.raises(TypeError):
        project_work_requested(  # type: ignore[call-arg]
            _aff(),
            work_request_id="wr-1",
            domain_model_hash=GOOD_HASH,
            settlement_criteria=["green"],
        )
    with pytest.raises(DomainRuleError) as err:
        project_work_requested(
            _aff(),
            work_request_id="wr-1",
            domain_model_hash=GOOD_HASH,
            settlement_criteria=["green"],
            world_ref="world:acme",
        )
    assert err.value.code == "malformed_world_ref"


def test_desired_direction_pins_world_ref():
    event = project_desired_direction(
        {"id": "d", "kind": "goal", "statement": "s"}, GOOD_HASH, world_ref=WORLD
    )
    assert event["payload"]["world_ref"] == WORLD


# --- outbound loop events -----------------------------------------------------------


def test_settlement_is_pinned_and_labelled_agent_local():
    event = emit_settlement_recorded("wr-1", "pr-1", "ev-1", "usable", "ok")
    assert event["payload"]["world_ref"] == WORLD  # conftest pin
    assert event["payload"]["settlement_scope"] == "agent_local"
    assert f"world_ref:{WORLD}" in event["provenance"]["chain"]


def test_consequential_events_refuse_an_unpinned_deployment(monkeypatch):
    monkeypatch.delenv("GSA_WORLD_REF", raising=False)
    with pytest.raises(DomainRuleError) as err:
        emit_settlement_recorded("wr-1", "pr-1", "ev-1", "usable", "ok")
    assert err.value.code == "world_ref_required"


def test_diagnostics_stay_reportable_without_a_world(monkeypatch):
    monkeypatch.delenv("GSA_WORLD_REF", raising=False)
    brk, proposal = detect_coherence_break("world not pinned", "wr-1")
    assert brk["payload"]["world_ref"] is None
    assert proposal["payload"]["world_ref"] is None
    assert schedule_repetition("cap-1")["payload"]["world_ref"] is None


def test_explicit_world_must_match_the_deployment_pin():
    with pytest.raises(DomainRuleError) as err:
        emit_settlement_recorded(
            "wr-1", "pr-1", "ev-1", "usable", "ok", world_ref=OTHER
        )
    assert err.value.code == "world_ref_drift"


def test_capability_and_twin_inherit_the_settlements_world():
    settlement = emit_settlement_recorded("wr-1", "pr-1", "ev-1", "usable", "ok")
    capability = emit_capability_updated({"id": "cap-1", "status": "x"}, settlement)
    twin = emit_twin_update(settlement, capability)
    assert capability["payload"]["world_ref"] == WORLD
    assert twin["payload"]["world_ref"] == WORLD


def test_a_settlement_from_another_world_cannot_update_capability():
    settlement = emit_settlement_recorded("wr-1", "pr-1", "ev-1", "usable", "ok")
    settlement["payload"]["world_ref"] = OTHER
    with pytest.raises(DomainRuleError) as err:
        emit_capability_updated({"id": "cap-1"}, settlement)
    assert err.value.code == "world_ref_drift"


# --- inbound evidence (E8) ----------------------------------------------------------


def _gate(envelope, *, local_world_ref):
    return ingest_evidence_recorded(
        envelope,
        local_model_sha256=MODEL_HASH,
        expected_work_request_id=WORK_REQUEST_ID,
        state=EvidenceIngestState(),
        known_parent_ids=None,
        local_world_ref=local_world_ref,
    )


def test_evidence_without_a_world_is_refused_when_a_world_is_pinned(golden):  # noqa: F811
    envelope = _envelope(golden)
    envelope["payload"].pop("world_ref", None)
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope, local_world_ref=WORLD)
    assert err.value.code == "world_ref_missing"


def test_evidence_without_a_world_is_provisional_and_unbound_when_none_pinned(golden):  # noqa: F811
    envelope = _envelope(golden)
    envelope["payload"].pop("world_ref", None)
    record = _gate(envelope, local_world_ref=None).record
    assert record.classification == "provisional"
    assert record.world_binding == "unbound"
    assert record.world_ref is None
    ledger = record.to_ledger_record("2026-10-05T00:00:00Z")
    assert ledger["world_binding"] == "unbound"


def test_evidence_naming_the_pinned_world_is_bound(golden):  # noqa: F811
    envelope = _envelope(golden)
    envelope["payload"]["world_ref"] = WORLD
    record = _gate(envelope, local_world_ref=WORLD).record
    assert record.world_binding == "bound"
    assert record.world_ref == WORLD
    assert record.classification == "provisional"


def test_evidence_from_another_world_is_refused(golden):  # noqa: F811
    envelope = _envelope(golden)
    envelope["payload"]["world_ref"] = OTHER
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope, local_world_ref=WORLD)
    assert err.value.code == "world_ref_drift"


def test_evidence_declaring_a_world_to_an_unpinned_deployment_is_refused(golden):  # noqa: F811
    envelope = _envelope(golden)
    envelope["payload"]["world_ref"] = WORLD
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope, local_world_ref=None)
    assert err.value.code == "world_ref_unpinned"


def test_evidence_with_an_alias_world_is_refused(golden):  # noqa: F811
    envelope = _envelope(golden)
    envelope["payload"]["world_ref"] = "world:acme"
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope, local_world_ref=WORLD)
    assert err.value.code == "malformed_world_ref"


def test_refused_evidence_leaves_no_state(golden):  # noqa: F811
    envelope = _envelope(golden)
    envelope["payload"]["world_ref"] = OTHER
    state = EvidenceIngestState()
    with pytest.raises(DomainRuleError):
        ingest_evidence_recorded(
            envelope,
            local_model_sha256=MODEL_HASH,
            expected_work_request_id=WORK_REQUEST_ID,
            state=state,
            local_world_ref=WORLD,
        )
    assert state.seen_identities == [] and state.claims == []


def test_handle_evidence_recorded_checks_the_world_before_ingest():
    class Boom:
        def ingest_execution_evidence(self, event):  # pragma: no cover
            raise AssertionError("must not reach ingest")

    event = {
        "event_type": "EvidenceRecorded",
        "payload": {"world_ref": OTHER},
    }
    with pytest.raises(DomainRuleError) as err:
        handle_evidence_recorded(event, Boom())
    assert err.value.code == "world_ref_drift"
