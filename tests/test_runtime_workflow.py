from pathlib import Path

from godspeed_nav.runtime import NavigationRuntime


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
    direction = runtime.start_direction(label="Reduce payment debt", statement="Avoid unsafe work")

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
