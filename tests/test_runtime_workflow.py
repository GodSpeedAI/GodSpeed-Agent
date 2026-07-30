from pathlib import Path
from typing import Any

import pytest

from godspeed_nav.runtime import NavigationRuntime
from godspeed_nav.schemas import DomainRuleError

_DERIVED_LEDGERS = (
    "settlements",
    "trajectories",
    "capabilities",
    "repetition_schedules",
)


def _seed_affordance(runtime: NavigationRuntime, affordance_id: str) -> None:
    runtime.store.append(
        "affordances",
        {
            "id": affordance_id,
            "direction_id": "dir-seed",
            "statement": "seeded executable affordance",
            "pathway": "seeded",
            "current_status": "affordance",
        },
    )


def test_runtime_completes_connected_developmental_cycle(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")

    direction = runtime.start_direction(
        label="Enterprise hardening",
        statement="Make the harness enterprise shippable",
        kind="goal",
        source="test",
    )
    review = runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "thin-docs",
                "statement": "Write more documentation",
                "pathway": "edit README",
                "costs": {"time": 1, "risk": 1},
                "capacities": {"time": 10, "risk": 10},
                "expected_horizon_delta": 1,
                "risk": 1,
            },
            {
                "id": "runtime-loop",
                "statement": "Connect the runtime loop",
                "pathway": "add orchestration service",
                "costs": {"time": 3, "risk": 2},
                "capacities": {"time": 10, "risk": 10},
                "expected_horizon_delta": 7,
                "risk": 1,
            },
            {
                "id": "imaginary-platform",
                "statement": "Launch hosted enterprise platform",
                "pathway": "",
                "costs": {"time": 50, "risk": 50},
                "capacities": {"time": 10, "risk": 10},
                "expected_horizon_delta": 10,
                "risk": 8,
            },
        ],
    )

    assert review["next_affordance"]["id"] == "runtime-loop"
    assert review["rejected_candidates"][0]["id"] == "imaginary-platform"
    assert review["rejected_candidates"][0]["reason"] == "missing_pathway"

    settlement = runtime.record_settlement(
        affordance_id="runtime-loop",
        before_state={"runtime_connected": 0},
        after_state={"runtime_connected": 1},
        payment_actual={"time": 3, "risk": 2},
        evidence=["workflow test passed"],
        horizon_delta=7,
    )

    assert settlement["status"] == "success"
    assert settlement["trajectory"]["new_radius"] > 1

    snapshot = runtime.snapshot()

    assert snapshot["counts"]["desired_directions"] == 1
    assert snapshot["counts"]["affordances"] == 2
    assert snapshot["counts"]["settlements"] == 1
    assert snapshot["counts"]["trajectories"] == 1
    assert snapshot["active_directions"][0]["label"] == "Enterprise hardening"


def test_runtime_marks_unaffordable_candidates_as_possibilities(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    direction = runtime.start_direction(
        label="Reduce payment debt", statement="Avoid unsafe work"
    )

    review = runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "too-expensive",
                "statement": "Rewrite everything",
                "pathway": "large migration",
                "costs": {"time": 100, "risk": 80},
                "capacities": {"time": 10, "risk": 10},
                "expected_horizon_delta": 3,
                "risk": 9,
            }
        ],
    )

    assert review["next_affordance"] is None
    assert review["rejected_candidates"][0]["reason"] == "unaffordable"
    assert runtime.snapshot()["counts"]["possibilities"] == 1


def test_runtime_promotes_repeated_success_into_metabolization_evidence(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "repeatable-loop")

    for before_state, after_state in [
        ({"context_a": 0}, {"context_a": 1}),
        ({"context_b": 0}, {"context_b": 1}),
        ({"context_c": 0}, {"context_c": 1}),
    ]:
        runtime.record_settlement(
            affordance_id="repeatable-loop",
            before_state=before_state,
            after_state=after_state,
            payment_actual={"time": 1},
            evidence=["repeatable workflow passed"],
            horizon_delta=2,
        )

    capability_records = runtime.store.read("capabilities")
    latest = capability_records[-1]

    assert latest["id"] == "repeatable-loop"
    assert latest["settlement_count"] == 3
    assert latest["context_diversity"] >= 2
    assert latest["status"] == "substrate_candidate"
    assert runtime.snapshot()["counts"]["capabilities"] >= 1


def test_runtime_truth_ledgers_use_event_envelopes(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")

    direction = runtime.start_direction(
        label="Durable truth surface",
        statement="Record payment and settlement with integrity metadata",
        source="test",
    )
    runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "durable-loop",
                "statement": "Use event-backed truth ledgers",
                "pathway": "append enveloped records",
                "costs": {"time": 1},
                "capacities": {"time": 5},
                "expected_horizon_delta": 2,
                "risk": 0,
            }
        ],
    )
    runtime.record_settlement(
        affordance_id="durable-loop",
        before_state={"truth": 0},
        after_state={"truth": 1},
        payment_actual={"time": 1},
        evidence=["integrity verified"],
        horizon_delta=2,
    )

    payment_events = runtime.store.read_events("payments")
    settlement_events = runtime.store.read_events("settlements")

    assert payment_events[0]["record"]["affordance_id"] == "durable-loop"
    assert settlement_events[0]["record"]["affordance_id"] == "durable-loop"
    assert runtime.store.read("settlements")[0]["affordance_id"] == "durable-loop"


def test_runtime_persists_representational_state_and_surfaces_it_in_snapshot(
    tmp_path: Path,
):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")

    direction = runtime.start_direction(
        label="Shape the frame",
        statement="Move from broad theory toward situated action",
        kind="goal",
        source="test",
    )
    state = runtime.set_representational_state(
        direction_id=direction["id"],
        scope_position="general",
        mode_of_givenness_position="abstract",
        phase="general",
        radius=1.0,
        confidence=0.9,
    )

    snapshot = runtime.snapshot()

    assert state["direction_id"] == direction["id"]
    assert snapshot["counts"]["representational_states"] == 1
    assert snapshot["latest_representational_state"]["id"] == state["id"]
    assert snapshot["latest_representational_state"]["quadrant"] == "general_abstract"


def test_runtime_reviews_representational_transition_and_persists_result(
    tmp_path: Path,
):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")

    review = runtime.review_representational_transition(
        current_state={
            "scope_position": "general",
            "mode_of_givenness_position": "abstract",
            "phase": "general",
        },
        target_state={
            "scope_position": "specific",
            "mode_of_givenness_position": "abstract",
            "phase": "specific",
        },
        capacity=2.0,
    )

    assert review["status"] == "blocked"
    assert review["code"] == "blocked_opposition_jump"
    assert runtime.store.read("representational_transitions")[-1]["status"] == "blocked"


def test_runtime_persists_explicit_affordance_paths_and_ranks_by_pathway_quality(
    tmp_path: Path,
):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    direction = runtime.start_direction(
        label="Spendable path review",
        statement="Prefer reachable pathways over visible destinations",
        source="test",
    )

    review = runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "vague-destination",
                "statement": "Ship the whole platform",
                "pathway": "start somewhere",
                "required_preconditions": ["platform-design"],
                "transition_sequence": ["general framing"],
                "expected_settlement": {"platform": "unclear"},
                "lifecycle_status": "candidate",
                "pathway_quality": 0.25,
                "costs": {"time": 1},
                "capacities": {"time": 5},
                "expected_horizon_delta": 5,
                "risk": 0,
            },
            {
                "id": "concrete-path",
                "statement": "Add the next local runtime slice",
                "pathway": "edit runtime and tests",
                "required_preconditions": ["failing tests"],
                "transition_sequence": [
                    "write failing tests",
                    "patch runtime",
                    "rerun focused tests",
                ],
                "expected_settlement": {"focused_tests": "pass"},
                "lifecycle_status": "ready",
                "pathway_quality": 0.9,
                "costs": {"time": 1},
                "capacities": {"time": 5},
                "expected_horizon_delta": 4,
                "risk": 0,
            },
        ],
    )

    affordance_paths = runtime.store.read("affordance_paths")

    assert review["next_affordance"]["id"] == "concrete-path"
    assert len(affordance_paths) == 2
    assert affordance_paths[-1]["required_preconditions"] == ["failing tests"]
    assert affordance_paths[-1]["transition_sequence"] == [
        "write failing tests",
        "patch runtime",
        "rerun focused tests",
    ]
    assert affordance_paths[-1]["expected_settlement"] == {"focused_tests": "pass"}
    assert affordance_paths[-1]["lifecycle_status"] == "ready"


def test_runtime_settlement_records_environment_identity_and_future_state_deltas(
    tmp_path: Path,
):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "identity-loop")

    settlement = runtime.record_settlement(
        affordance_id="identity-loop",
        before_state={"docs": 0},
        after_state={"docs": 1},
        payment_actual={"time": 2},
        evidence=["docs updated", "tests passed"],
        horizon_delta=2,
        observed_consequence="operator references now exist",
        unexpected_consequence=["follow-up policy doc needed"],
        payment_variance={"time": 1},
        capability_delta={"docs_loop": "active"},
        identity_delta={"operator_posture": "more_explicit"},
        future_constraints_created=["must keep references current"],
        future_affordances_created=["tighten policy-reference doc"],
    )

    stored = runtime.store.read("settlements")[-1]

    assert settlement["observed_consequence"] == "operator references now exist"
    assert stored["unexpected_consequence"] == ["follow-up policy doc needed"]
    assert stored["payment_variance"] == {"time": 1}
    assert stored["capability_delta"] == {"docs_loop": "active"}
    assert stored["identity_delta"] == {"operator_posture": "more_explicit"}
    assert stored["future_constraints_created"] == ["must keep references current"]
    assert stored["future_affordances_created"] == ["tighten policy-reference doc"]


def test_runtime_schedules_repetition_after_successful_non_metabolized_settlement(
    tmp_path: Path,
):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "repeat-loop")

    runtime.record_settlement(
        affordance_id="repeat-loop",
        before_state={"context_a": 0},
        after_state={"context_a": 1},
        payment_actual={"time": 1},
        evidence=["first success"],
        horizon_delta=2,
    )

    snapshot = runtime.snapshot()
    schedule = runtime.store.read("repetition_schedules")[-1]

    assert snapshot["counts"]["repetition_schedules"] == 1
    assert schedule["status"] == "scheduled"
    assert schedule["variation_coverage"] == 1
    assert schedule["next_condition"] == "changed_conditions"
    assert schedule["critique_escalation"] is None


def test_runtime_escalates_repetition_schedule_when_circular_motion_repeats(
    tmp_path: Path,
):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "repeat-loop")
    runtime.store.append("trajectories", {"new_theta": 0.0, "new_radius": 1.0})
    runtime.store.append("trajectories", {"new_theta": 7.0, "new_radius": 1.01})

    runtime.record_settlement(
        affordance_id="repeat-loop",
        before_state={"context_a": 0},
        after_state={"context_a": 1},
        payment_actual={"time": 1},
        evidence=["repeat without radial growth"],
        horizon_delta=0,
    )

    schedule = runtime.store.read("repetition_schedules")[-1]

    assert schedule["critique_escalation"] == "circular_motion"


def test_runtime_horizon_review_includes_advisory_cognitive_model(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path)
    direction = runtime.start_direction("Core model", "Use advisory cognitive model")

    review = runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "candidate-1",
                "statement": "Run focused model test",
                "pathway": "write failing test then implement",
                "costs": {"time": 1},
                "capacities": {"time": 5},
                "payment_required": {"time": 1},
                "payment_capacity": {"time": 5},
                "expected_horizon_delta": 3,
                "risk": 0.1,
                "debt": 0.1,
            }
        ],
    )

    assert review["next_affordance"]["id"] == "candidate-1"
    assert review["cognitive_model"]["ranked"][0]["candidate_id"] == "candidate-1"
    assert review["cognitive_model"]["mode"] == "advisory"


# ---------------------------------------------------------------------------
# Task 5: Settlement calibration fields
# ---------------------------------------------------------------------------


def test_record_settlement_persists_cognitive_model_calibration_fields(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path)
    direction = runtime.start_direction(
        "Calibrate model", "Record predicted and actual payment"
    )
    runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "aff-1",
                "statement": "Patch model",
                "pathway": "edit code",
                "costs": {"time": 1},
                "capacities": {"time": 5},
                "payment_required": {"time": 1},
                "payment_capacity": {"time": 5},
                "expected_horizon_delta": 2,
                "risk": 0.1,
                "debt": 0.1,
            }
        ],
    )

    settlement = runtime.record_settlement(
        affordance_id="aff-1",
        before_state={"tests": 0},
        after_state={"tests": 1},
        desired_direction={"desired_state": {"tests": 1}},
        payment_actual={"time": 1.5},
        evidence=["pytest passed"],
        horizon_delta=2,
    )

    calibration = settlement["model_calibration"]
    assert calibration["payment_actual"] == {"time": 1.5}
    assert calibration["settlement_success"] is True
    assert "payment_predicted" in calibration
    assert "horizon_delta" in calibration


# ---------------------------------------------------------------------------
# Task 1: Settlement requires an executable affordance
# ---------------------------------------------------------------------------


def _snapshot_derived(runtime: NavigationRuntime) -> dict[str, int]:
    return {ledger: len(runtime.store.read(ledger)) for ledger in _DERIVED_LEDGERS}


def test_record_settlement_rejects_unknown_affordance(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    before = _snapshot_derived(runtime)

    with pytest.raises(DomainRuleError) as exc_info:
        runtime.record_settlement(
            affordance_id="does-not-exist",
            before_state={"x": 0},
            after_state={"x": 1},
            payment_actual={"time": 1},
            evidence=["none"],
            horizon_delta=1,
        )

    assert exc_info.value.code == "settlement_requires_executable_affordance"
    assert _snapshot_derived(runtime) == before


def test_record_settlement_rejects_potential_only_affordance(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    runtime.store.append(
        "potentials",
        {
            "id": "potential-only",
            "direction_id": "dir-1",
            "current_status": "potential",
            "missing_pathway_reason": "no_pathway",
        },
    )
    before = _snapshot_derived(runtime)

    with pytest.raises(DomainRuleError) as exc_info:
        runtime.record_settlement(
            affordance_id="potential-only",
            before_state={"x": 0},
            after_state={"x": 1},
            payment_actual={"time": 1},
            evidence=["none"],
            horizon_delta=1,
        )

    assert exc_info.value.code == "settlement_requires_executable_affordance"
    assert _snapshot_derived(runtime) == before


def test_record_settlement_rejects_possibility_only_affordance(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    runtime.store.append(
        "possibilities",
        {
            "id": "possibility-only",
            "direction_id": "dir-1",
            "current_status": "possibility",
            "candidate_pathway": "big migration",
            "unknowns": ["payment_exceeds_capacity"],
        },
    )
    before = _snapshot_derived(runtime)

    with pytest.raises(DomainRuleError) as exc_info:
        runtime.record_settlement(
            affordance_id="possibility-only",
            before_state={"x": 0},
            after_state={"x": 1},
            payment_actual={"time": 1},
            evidence=["none"],
            horizon_delta=1,
        )

    assert exc_info.value.code == "settlement_requires_executable_affordance"
    assert _snapshot_derived(runtime) == before


def test_record_settlement_rejects_non_executable_status(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    runtime.store.append(
        "affordances",
        {
            "id": "spent-affordance",
            "direction_id": "dir-1",
            "current_status": "settled",
            "pathway": "done",
        },
    )

    with pytest.raises(DomainRuleError) as exc_info:
        runtime.record_settlement(
            affordance_id="spent-affordance",
            before_state={"x": 0},
            after_state={"x": 1},
            payment_actual={"time": 1},
            evidence=["none"],
            horizon_delta=1,
        )

    assert exc_info.value.code == "settlement_requires_executable_affordance"


def test_record_settlement_succeeds_for_seeded_executable_affordance(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "executable-aff")

    settlement = runtime.record_settlement(
        affordance_id="executable-aff",
        before_state={"x": 0},
        after_state={"x": 1},
        payment_actual={"time": 1},
        evidence=["passed"],
        horizon_delta=1,
    )

    assert settlement["status"] == "success"
    assert runtime.snapshot()["counts"]["settlements"] == 1
    assert runtime.snapshot()["counts"]["capabilities"] == 1


# ---------------------------------------------------------------------------
# Task 2: Execution evidence is provisional and capability-neutral
# ---------------------------------------------------------------------------


def _evidence_event(
    event_id: str = "ev-1",
    affordance_id: str = "exec-ev-aff",
    expected: str = "ok",
    observed: str = "ok",
) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "event_id": event_id,
        "source_agent": "sea-forge",
        "event_type": "EvidenceRecorded",
        "occurred_at": "2026-07-01T00:00:00+00:00",
        "idempotency_key": event_id,
        "payload": {
            "namespace": "agentic_capability_loop",
            "affordance_id": affordance_id,
            "work_request_id": "wr-1",
            "proof_result_id": "pr-1",
            "expected_result": expected,
            "observed_result": observed,
        },
    }


def test_ingest_execution_evidence_is_provisional_and_writes_no_settlement_state(
    tmp_path: Path,
):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "exec-ev-aff")
    before = _snapshot_derived(runtime)

    cases = [
        ("ev-match-1", "ok", "ok"),
        ("ev-match-2", "ok", "ok"),
        ("ev-differ-1", "ok", "different"),
    ]
    for event_id, expected, observed in cases:
        result = runtime.ingest_execution_evidence(
            _evidence_event(event_id=event_id, expected=expected, observed=observed)
        )
        assert result["classification"] == "provisional"

    assert _snapshot_derived(runtime) == before
    assert len(runtime.store.read("execution_evidence")) == 3
    by_id = {r["evidence_event_id"]: r["proof_match"] for r in runtime.store.read("execution_evidence")}
    assert by_id == {"ev-match-1": True, "ev-match-2": True, "ev-differ-1": False}


def test_ingest_execution_evidence_rejects_incomplete(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "exec-ev-aff")

    with pytest.raises(DomainRuleError) as exc_info:
        runtime.ingest_execution_evidence(
            _evidence_event(observed="")
        )

    assert exc_info.value.code == "incomplete_execution_evidence"
    assert len(runtime.store.read("execution_evidence")) == 0


def test_ingest_execution_evidence_is_idempotent(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "exec-ev-aff")

    first = runtime.ingest_execution_evidence(_evidence_event())
    second = runtime.ingest_execution_evidence(_evidence_event())

    assert first["id"] == second["id"]
    assert len(runtime.store.read("execution_evidence")) == 1


def test_ingest_execution_evidence_requires_executable_affordance(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")

    with pytest.raises(DomainRuleError) as exc_info:
        runtime.ingest_execution_evidence(
            _evidence_event(affordance_id="not-persisted")
        )

    assert exc_info.value.code == "settlement_requires_executable_affordance"
