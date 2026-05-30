from pathlib import Path

from godspeed_nav.reports import generate_developmental_report
from godspeed_nav.runtime import NavigationRuntime


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
