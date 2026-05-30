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
