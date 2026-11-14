from pathlib import Path

from godspeed_nav.reports import generate_developmental_report
from godspeed_nav.runtime import NavigationRuntime


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


def test_developmental_report_summarizes_settlement_payment_and_trajectory(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    direction = runtime.start_direction(label="Reports", statement="Make state inspectable")
    runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "report-loop",
                "statement": "Generate report",
                "pathway": "call report module",
                "costs": {"time": 2, "risk": 1},
                "capacities": {"time": 5, "risk": 5},
                "expected_horizon_delta": 3,
                "risk": 1,
            }
        ],
    )
    runtime.record_settlement(
        affordance_id="report-loop",
        before_state={"reports": 0},
        after_state={"reports": 1},
        payment_actual={"time": 2, "risk": 1},
        evidence=["report test passed"],
        horizon_delta=3,
    )

    report = generate_developmental_report(tmp_path / ".godspeed-harness")

    assert report["settlement_quality"]["success"] == 1
    assert report["payment_debt"]["total_burden"] > 0
    assert report["trajectory"]["latest_radius"] > 1
    assert report["horizon"]["active_direction_count"] == 1
    assert report["metabolization"]["candidate_count"] == 0


def test_developmental_report_detects_circular_motion_from_trajectory_records(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    runtime.store.append(
        "trajectories",
        {"new_theta": 0.0, "new_radius": 1.0},
    )
    runtime.store.append(
        "trajectories",
        {"new_theta": 7.0, "new_radius": 1.01},
    )

    report = generate_developmental_report(tmp_path / ".godspeed-harness")

    assert report["trajectory"]["circular_motion"] is True


def test_developmental_report_surfaces_runtime_owned_metabolization_candidates(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "report-loop")

    for before_state, after_state in [
        ({"report_a": 0}, {"report_a": 1}),
        ({"report_b": 0}, {"report_b": 1}),
        ({"report_c": 0}, {"report_c": 1}),
    ]:
        runtime.record_settlement(
            affordance_id="report-loop",
            before_state=before_state,
            after_state=after_state,
            payment_actual={"time": 1},
            evidence=["report loop passed"],
            horizon_delta=2,
        )

    report = generate_developmental_report(tmp_path / ".godspeed-harness")

    assert report["metabolization"]["candidate_count"] == 1
    assert report["metabolization"]["candidate_ids"] == ["report-loop"]


def test_developmental_report_summarizes_affordance_paths(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    direction = runtime.start_direction(label="Path report", statement="Report spendable paths")
    runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "path-report-loop",
                "statement": "Persist explicit path metadata",
                "pathway": "update runtime and report",
                "required_preconditions": ["failing tests"],
                "transition_sequence": ["test", "patch", "verify"],
                "expected_settlement": {"report": "expanded"},
                "lifecycle_status": "ready",
                "pathway_quality": 0.8,
                "costs": {"time": 1},
                "capacities": {"time": 5},
                "expected_horizon_delta": 2,
                "risk": 0,
            }
        ],
    )

    report = generate_developmental_report(tmp_path / ".godspeed-harness")

    assert report["affordance_paths"]["count"] == 1
    assert report["affordance_paths"]["latest"]["lifecycle_status"] == "ready"
    assert report["affordance_paths"]["latest"]["required_preconditions"] == ["failing tests"]


def test_developmental_report_surfaces_latest_settlement_consequences(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "report-consequence-loop")
    runtime.record_settlement(
        affordance_id="report-consequence-loop",
        before_state={"reports": 0},
        after_state={"reports": 1},
        payment_actual={"time": 1},
        evidence=["report updated"],
        horizon_delta=1,
        observed_consequence="report surface is richer",
        unexpected_consequence=["new doc obligations"],
        payment_variance={"time": 0},
        capability_delta={"reporting": "active"},
        identity_delta={"runtime_identity": "more_observable"},
        future_constraints_created=["keep report interpretation aligned"],
        future_affordances_created=["add critique section"],
    )

    report = generate_developmental_report(tmp_path / ".godspeed-harness")

    assert report["latest_settlement"]["observed_consequence"] == "report surface is richer"
    assert report["latest_settlement"]["identity_delta"] == {"runtime_identity": "more_observable"}
    assert report["latest_settlement"]["future_affordances_created"] == ["add critique section"]


def test_developmental_report_surfaces_repetition_schedule_summary(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    _seed_affordance(runtime, "repeat-report-loop")
    runtime.record_settlement(
        affordance_id="repeat-report-loop",
        before_state={"report_a": 0},
        after_state={"report_a": 1},
        payment_actual={"time": 1},
        evidence=["first report success"],
        horizon_delta=2,
    )

    report = generate_developmental_report(tmp_path / ".godspeed-harness")

    assert report["repetition"]["schedule_count"] == 1
    assert report["repetition"]["latest"]["affordance_id"] == "repeat-report-loop"
    assert report["repetition"]["latest"]["next_condition"] == "changed_conditions"


def test_developmental_report_surfaces_capability_lifecycle_and_identity_state(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    direction = runtime.start_direction(label="Identity", statement="Track capability posture")
    _seed_affordance(runtime, "identity-capability")

    for before_state, after_state in [
        ({"ctx_a": 0}, {"ctx_a": 1}),
        ({"ctx_b": 0}, {"ctx_b": 1}),
        ({"ctx_c": 0}, {"ctx_c": 1}),
    ]:
        runtime.record_settlement(
            affordance_id="identity-capability",
            before_state=before_state,
            after_state=after_state,
            payment_actual={"time": 1},
            evidence=["capability repeated successfully"],
            horizon_delta=2,
        )

    report = generate_developmental_report(tmp_path / ".godspeed-harness")

    assert report["capabilities"]["lifecycle_counts"]["metabolized"] == 1
    assert report["capabilities"]["latest"]["lifecycle_state"] == "metabolized"
    assert report["identity_state"]["active_direction_ids"] == [direction["id"]]
    assert report["identity_state"]["capability_ids"] == ["identity-capability"]


def test_developmental_report_surfaces_self_critique_findings(tmp_path: Path):
    runtime = NavigationRuntime(tmp_path / ".godspeed-harness")
    runtime.start_direction(label="Dead end", statement="Keep moving")
    _seed_affordance(runtime, "dead-end-loop")
    runtime.record_settlement(
        affordance_id="dead-end-loop",
        before_state={"docs": 0},
        after_state={"docs": 1},
        payment_actual={"time": 1},
        evidence=["docs changed"],
        horizon_delta=0,
    )
    runtime.store.append("trajectories", {"new_theta": 0.0, "new_radius": 1.0})
    runtime.store.append("trajectories", {"new_theta": 7.0, "new_radius": 1.01})
    runtime.store.append(
        "capabilities",
        {"id": "simulated-capability", "lifecycle_state": "metabolized", "evidence_source": "simulation"},
    )
    runtime.review_self_critique()

    report = generate_developmental_report(tmp_path / ".godspeed-harness")

    assert report["self_critique"]["finding_count"] >= 3
    assert "dead_end_direction" in report["self_critique"]["finding_codes"]
    assert "circular_motion" in report["self_critique"]["finding_codes"]
    assert "simulation_is_not_capability" in report["self_critique"]["finding_codes"]
