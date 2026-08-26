"""Convergence T03 — canonical event projection (E0/E1) from GodSpeed-Agent.

The frozen contract lives in sea-rs `.agents/specs/e2e-preregistration.yml`.
GodSpeed-Agent is the EXCLUSIVE authoritative producer of WorkRequested; the
external environment owns DesiredDirection. Destination-only inputs and
fallback pseudo-identities must never project into canonical events.

The happy-path WorkRequested fixture written here is consumed by SWE_SEED's
Rust ingress test (`convergence_t03_work_ingress.rs`) as cross-language
production evidence.
"""

import json
import os

import pytest

from godspeed_nav.canonical_events import (
    FALLBACK_PSEUDO_HASH,
    GODSPEED_AGENT,
    idempotency_key,
    project_desired_direction,
    project_work_requested,
    verify_domain_model_hash,
)
from godspeed_nav.schemas import DomainRuleError

GOOD_HASH = "a" * 64


def executable_affordance() -> dict:
    return {
        "id": "aff-blue-green-001",
        "statement": "deploy service via blue-green rotation",
        "pathway": "build -> canary 10% -> promote",
        "payment_estimate": {"dimensions": {"compute": 1.5}, "burden": 1.5},
        "expected_horizon_delta": 0.4,
        "current_status": "affordance",
    }


def direction() -> dict:
    return {
        "id": "dir-123",
        "kind": "goal",
        "statement": "ship the deployment capability",
        "success_criteria": ["health check green", "zero-downtime observed"],
    }


# --- identity gate -------------------------------------------------------------

def test_fallback_pseudo_hash_is_refused():
    with pytest.raises(DomainRuleError) as err:
        verify_domain_model_hash(FALLBACK_PSEUDO_HASH)
    assert err.value.code == "fallback_domain_hash_forbidden"


def test_all_zero_and_malformed_hashes_are_refused():
    for bad in ["0" * 64, "", "deadbeef", "A" * 64, GOOD_HASH[:-1] + "g"]:
        with pytest.raises(DomainRuleError):
            verify_domain_model_hash(bad)


# --- E0: desired direction ------------------------------------------------------

def test_desired_direction_projects_with_external_producer():
    event = project_desired_direction(direction(), GOOD_HASH)
    assert event["schema_version"] == "v1"
    assert event["event_type"] == "DesiredDirection"
    # E0 production authority is the external environment.
    assert event["source_agent"] == "external-environment"
    payload = event["payload"]
    assert payload["direction_id"] == "dir-123"
    assert payload["direction_type"] == "goal"
    assert payload["desired_state"] == "ship the deployment capability"
    assert event["provenance"]["origin"] == "external-environment"


def test_incomplete_direction_is_rejected():
    with pytest.raises(DomainRuleError):
        project_desired_direction({"id": "dir-1"}, GOOD_HASH)


# --- E1: work requested ----------------------------------------------------------

def test_executable_affordance_projects_full_contract():
    event = project_work_requested(
        executable_affordance(),
        work_request_id="wr-t03",
        domain_model_hash=GOOD_HASH,
        direction=direction(),
        parent_direction_event_id="e0-event-id-1",
    )
    assert event["schema_version"] == "v1"
    assert event["event_type"] == "WorkRequested"
    # Exclusive producer authority: godspeed_agent, never swe_seed.
    assert event["source_agent"] == GODSPEED_AGENT
    payload = event["payload"]
    assert payload["work_request_id"] == "wr-t03"
    assert payload["affordance_id"] == "aff-blue-green-001"
    assert payload["desired_outcome"] == "deploy service via blue-green rotation"
    assert payload["settlement_criteria"] == [
        "health check green",
        "zero-downtime observed",
    ]
    chain = event["provenance"]["chain"]
    assert f"caused_by:e0-event-id-1" in chain
    assert chain[0].startswith("domain_model_hash:")
    assert len(event["idempotency_key"]) == 64


def test_destination_only_affordance_cannot_become_work_requested():
    bare = {"id": "dest-1", "statement": "be deployed"}
    with pytest.raises(DomainRuleError) as err:
        project_work_requested(
            bare,
            work_request_id="wr-x",
            domain_model_hash=GOOD_HASH,
            direction=direction(),
        )
    assert err.value.code == "destination_only_not_spendable"


def test_pathway_without_payment_is_still_destination_only():
    no_payment = executable_affordance() | {"payment_estimate": None}
    with pytest.raises(DomainRuleError) as err:
        project_work_requested(
            no_payment,
            work_request_id="wr-x",
            domain_model_hash=GOOD_HASH,
            direction=direction(),
        )
    assert err.value.code == "destination_only_not_spendable"


def test_missing_settlement_criteria_is_rejected():
    criteria_free = direction() | {"success_criteria": []}
    with pytest.raises(DomainRuleError) as err:
        project_work_requested(
            executable_affordance(),
            work_request_id="wr-y",
            domain_model_hash=GOOD_HASH,
            direction=criteria_free,
        )
    assert err.value.code == "settlement_criteria_required"


def test_pseudo_hash_cannot_project_work_requested():
    with pytest.raises(DomainRuleError):
        project_work_requested(
            executable_affordance(),
            work_request_id="wr-z",
            domain_model_hash=FALLBACK_PSEUDO_HASH,
            direction=direction(),
        )


def test_idempotency_key_matches_canonical_formula():
    payload = {"b": 2, "a": 1}
    expected = __import__("hashlib").sha256(
        b'wr-1|WorkRequested|{"a":1,"b":2}'
    ).hexdigest()
    assert idempotency_key("WorkRequested", payload, "wr-1") == expected


# --- cross-language golden fixture ----------------------------------------------

def test_writes_golden_fixture_for_swe_seed_ingress():
    """Regenerate tests/fixtures/t03_work_requested.json.

    SWE_SEED's `convergence_t03_work_ingress.rs` consumes this file as
    cross-language production-path evidence that GodSpeed-Agent's real
    projector output passes SWE_SEED's canonical ingress gate.
    """
    event = project_work_requested(
        executable_affordance(),
        work_request_id="wr-gsa-001",
        domain_model_hash=GOOD_HASH,
        direction=direction(),
        parent_direction_event_id="33333333-3333-3333-4444-555555555555",
    )
    fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    os.makedirs(fixture_dir, exist_ok=True)
    path = os.path.join(fixture_dir, "t03_work_requested.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(event, fh, indent=2, sort_keys=True)
        fh.write("\n")
    assert os.path.exists(path)
