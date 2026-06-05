import math

import pytest

from godspeed_nav.absorption import review_absorbability
from godspeed_nav.disintegration import review_positive_disintegration
from godspeed_nav.metabolization import compute_metabolization
from godspeed_nav.metrics import (
    compute_error,
    estimate_payment,
    rank_affordances,
    review_representational_transition,
    score_settlement,
)
from godspeed_nav.ml import (
    TestingPredictiveModelAdapter,
    build_predictive_extension_plan,
    ensure_ml_allowed,
    resolve_model_provider,
)
from godspeed_nav.trajectory import detect_circular_motion, update_trajectory


def test_compute_error_produces_vector_magnitude_and_dominant_error():
    result = compute_error(
        desired_state={"tests": 10, "docs": 4},
        observed_state={"tests": 6, "docs": 1},
        weights={"tests": 2, "docs": 1},
    )

    assert result["error_vector"] == {"tests": 8, "docs": 3}
    assert result["error_magnitude"] == pytest.approx(math.sqrt(73))
    assert result["dominant_error"] == "tests"


def test_estimate_payment_computes_weighted_norm_and_spendability():
    result = estimate_payment(
        costs={"time": 3, "risk": 4},
        weights={"time": 1, "risk": 2},
        capacities={"time": 6, "risk": 8},
    )

    assert result["payment_burden"] == pytest.approx(math.sqrt(73))
    assert result["capacity_norm"] == pytest.approx(10)
    assert result["spendability"] == "affordable"
    assert result["dominant_cost"] == "risk"


def test_representational_transition_prices_distance_and_blocks_unearned_opposition_jumps():
    adjacent = review_representational_transition(
        current_state={
            "scope_position": "general",
            "mode_of_givenness_position": "abstract",
            "phase": "general",
        },
        target_state={
            "scope_position": "general",
            "mode_of_givenness_position": "abstract",
            "phase": "abstract",
        },
        capacity=1.5,
    )
    blocked = review_representational_transition(
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
    metabolized = review_representational_transition(
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
        metabolized_shortcuts=["general->specific"],
    )

    assert adjacent["is_adjacent"] is True
    assert adjacent["status"] == "affordable"
    assert adjacent["distance_cost"] == pytest.approx(0.0)
    assert blocked["is_opposition_jump"] is True
    assert blocked["status"] == "blocked"
    assert blocked["code"] == "blocked_opposition_jump"
    assert blocked["recommended_next_phases"] == ["abstract", "concrete"]
    assert metabolized["status"] == "metabolized"


def test_score_settlement_rejects_intent_only_evidence():
    result = score_settlement(
        before_state={"tests": 0},
        after_state={"tests": 0},
        desired_direction={"statement": "Add tests"},
        payment_actual={"time": 1},
        evaluator_config={"evidence": ["intent: I planned to add tests"]},
    )

    assert result["status"] == "failed"
    assert result["settlement_score"] == 0
    assert result["evidence_summary"] == "intent_only"


def test_score_settlement_flags_regressions_as_partial():
    result = score_settlement(
        before_state={"tests": 1, "bugs": 0},
        after_state={"tests": 2, "bugs": 2},
        desired_direction={"statement": "Improve quality"},
        payment_actual={"time": 2},
        evaluator_config={
            "evidence": ["pytest passed", "bug count increased in smoke test"]
        },
    )

    assert result["status"] == "partial"
    assert "bugs" in result["regression_keys"]
    assert "tests" in result["improved_keys"]


def test_score_settlement_uses_desired_state_when_available():
    result = score_settlement(
        before_state={"tests": 1, "docs": 0},
        after_state={"tests": 3, "docs": 1},
        desired_direction={"desired_state": {"tests": 3, "docs": 1}},
        payment_actual={"time": 1},
        evaluator_config={"evidence": ["pytest passed", "docs updated"]},
    )

    assert result["status"] == "success"
    assert result["settlement_score"] == pytest.approx(1.0)


def test_score_settlement_reports_missing_observable_change():
    result = score_settlement(
        before_state={"runtime": 1},
        after_state={"runtime": 1},
        desired_direction={"statement": "Improve runtime"},
        payment_actual={"time": 1},
        evaluator_config={"evidence": ["command ran successfully"]},
    )

    assert result["status"] == "failed"
    assert result["missing_evidence"] == ["observable_change"]


def test_update_trajectory_increases_radius_only_on_positive_settlement():
    positive = update_trajectory(
        previous_theta=0,
        previous_radius=1,
        settlement_score=0.8,
        horizon_delta=2,
    )
    failed = update_trajectory(
        previous_theta=0,
        previous_radius=1,
        settlement_score=0.1,
        horizon_delta=2,
    )

    assert positive["new_radius"] > 1
    assert failed["new_radius"] == 1
    assert {"real", "imag"} <= set(positive["coordinate"])


def test_detect_circular_motion_flags_activity_without_radius_growth():
    result = detect_circular_motion(
        trajectory_records=[
            {"theta": 0.0, "radius": 1.0},
            {"theta": 1.2, "radius": 1.01},
            {"theta": 2.5, "radius": 1.0},
            {"theta": 3.8, "radius": 1.01},
        ],
        min_rotation=3.0,
        max_radius_growth=0.05,
    )

    assert result["circular_motion"] is True


def test_compute_metabolization_rejects_low_diversity_repetition():
    result = compute_metabolization(
        capability_id="cap-1",
        settlement_events=[{"id": "s1"}, {"id": "s2"}, {"id": "s3"}],
        reuse_frequency=10,
        context_diversity=1,
        stability=0.9,
        maintenance_burden=0.1,
        attention_burden=0.1,
    )

    assert result["status_recommendation"] == "not_metabolized"
    assert "context_diversity" in result["missing_evidence"]


def test_rank_affordances_recommends_best_horizon_delta_per_payment_and_risk():
    result = rank_affordances(
        candidates=[
            {"id": "a", "expected_horizon_delta": 5, "risk": 4},
            {"id": "b", "expected_horizon_delta": 3, "risk": 1},
        ],
        payment_estimates={"a": {"payment_burden": 5}, "b": {"payment_burden": 1}},
    )

    assert result["next_recommended_affordance"]["id"] == "b"
    assert [item["id"] for item in result["ranked_affordances"]] == ["b", "a"]


def test_absorbability_without_pathway_remains_potential():
    result = review_absorbability(
        root_project_state={"capabilities": ["python"]},
        external_project_state={"capabilities": ["mcp"]},
        desired_direction={"statement": "Absorb external MCP tool"},
        capability_delta=["mcp"],
        license_summary={"compatible": True},
        pathway=None,
    )

    assert result["absorbability_status"] == "potential"
    assert result["missing_pathway"]


def test_absorbability_returns_policy_rich_blocking_reasons():
    result = review_absorbability(
        root_project_state={"capabilities": ["python"]},
        external_project_state={"capabilities": ["mcp", "evals"]},
        desired_direction={"statement": "Absorb external MCP tool"},
        capability_delta=["mcp", "evals"],
        license_summary={"compatible": False, "spdx": "GPL-3.0"},
        pathway="port the tool locally",
    )

    assert result["absorbability_status"] == "blocked"
    assert "incompatible_license" in result["blocking_reasons"]
    assert result["policy_gate"]["code"] == "human_review_required"
    assert result["required_human_review"] is True
    assert result["settlement_plan"]


def test_positive_disintegration_reports_dissolution_and_body_candidates():
    result = review_positive_disintegration(
        structures=[
            {"id": "old-hook", "settlement_score": 0.1, "risk": "low"},
            {
                "id": "review-loop",
                "settlement_score": 0.9,
                "attention_burden": 0.1,
                "repetitions": 5,
            },
        ],
        require_human_review=True,
    )

    assert result["dissolution_candidates"][0]["id"] == "old-hook"
    assert result["metabolization_candidates"][0]["id"] == "review-loop"
    assert result["requires_human_review"] is True


def test_positive_disintegration_separates_blocked_high_risk_items_from_salvageable_ones():
    result = review_positive_disintegration(
        structures=[
            {
                "id": "dangerous-cut",
                "settlement_score": 0.1,
                "risk": "high",
                "salvageable_elements": ["logging"],
            },
            {
                "id": "stale-loop",
                "settlement_score": 0.2,
                "risk": "low",
                "salvageable_elements": ["tests", "docs"],
            },
        ],
        require_human_review=True,
    )

    assert result["blocked_candidates"][0]["id"] == "dangerous-cut"
    assert result["dissolution_candidates"][0]["id"] == "stale-loop"
    assert result["salvage_plan"]["stale-loop"] == ["tests", "docs"]


def test_ml_training_refuses_below_configured_threshold():
    with pytest.raises(RuntimeError, match="insufficient_settlement_history"):
        ensure_ml_allowed(settlement_event_count=25, threshold=200)


def test_predictive_extensions_remain_deterministic_before_ml_threshold():
    result = build_predictive_extension_plan(
        settlement_history=[{"id": f"set-{index}"} for index in range(199)],
        candidates=[
            {
                "id": "aff-1",
                "expected_horizon_delta": 4,
                "risk": 1,
                "costs": {"time": 1},
                "capacities": {"time": 5},
            }
        ],
        ml_event_threshold=200,
        simulation_threshold=1000,
        model_port=TestingPredictiveModelAdapter(),
    )

    assert result["stage"] == "deterministic_only"
    assert result["active_extensions"] == []
    assert result["ml_predictions"] == []
    assert result["simulation_results"] == []


def test_predictive_extensions_auto_activate_ml_and_simulation_at_thresholds():
    candidates = [
        {
            "id": "aff-1",
            "expected_horizon_delta": 5,
            "risk": 1,
            "costs": {"time": 1},
            "capacities": {"time": 5},
        }
    ]

    ml_ready = build_predictive_extension_plan(
        settlement_history=[{"id": f"set-{index}"} for index in range(200)],
        candidates=candidates,
        ml_event_threshold=200,
        simulation_threshold=1000,
        model_port=TestingPredictiveModelAdapter(),
    )
    simulation_ready = build_predictive_extension_plan(
        settlement_history=[{"id": f"set-{index}"} for index in range(1000)],
        candidates=candidates,
        ml_event_threshold=200,
        simulation_threshold=1000,
        model_port=TestingPredictiveModelAdapter(),
    )

    assert ml_ready["stage"] == "ml_assisted"
    assert ml_ready["active_extensions"] == ["ml_prediction"]
    assert ml_ready["ml_predictions"][0]["candidate_id"] == "aff-1"
    assert ml_ready["simulation_results"] == []

    assert simulation_ready["stage"] == "simulation_assisted"
    assert simulation_ready["active_extensions"] == ["ml_prediction", "simulation"]
    assert simulation_ready["simulation_results"][0]["candidate_id"] == "aff-1"


# ---------------------------------------------------------------------------
# Task 1: Cognitive model – deterministic burden kernel
# ---------------------------------------------------------------------------

from godspeed_nav.cognitive_model import (
    BurdenParameters,
    RepresentationalCoordinates,
    build_calibration_frame,
    compute_representational_burden,
    evaluate_candidate_model,
    rank_candidates_by_controller,
)


def test_cognitive_model_computes_default_representational_burden():
    result = compute_representational_burden(
        current=RepresentationalCoordinates(scope=0.2, givenness=0.2),
        target=RepresentationalCoordinates(scope=0.7, givenness=0.6),
        distinctions_current=14,
        distinctions_max=20,
        parameters=BurdenParameters(),
    )

    assert result["delta"] == {
        "scope": pytest.approx(0.5),
        "givenness": pytest.approx(0.4),
    }
    assert result["scope_overflow"] == 0.0
    assert result["burden"] > 0
    assert result["burden_max"] == pytest.approx(2**0.5)
    assert result["matrix_floor"] == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Task 2: Cognitive model – hard gates and spendability scoring
# ---------------------------------------------------------------------------


def test_cognitive_model_blocks_failed_hard_gate_before_scoring():
    result = evaluate_candidate_model(
        candidate={
            "id": "unsafe",
            "governance_allowed": False,
            "settlement_accessible": True,
            "payment_required": {"time": 1},
            "payment_capacity": {"time": 5},
            "risk": 0.1,
            "debt": 0.1,
        },
        context="production",
    )

    assert result["allowed"] is False
    assert result["blocking_reasons"] == ["governance_blocked"]
    assert result["spendability_score"] is None


def test_cognitive_model_scores_allowed_candidate_spendability():
    result = evaluate_candidate_model(
        candidate={
            "id": "path",
            "governance_allowed": True,
            "settlement_accessible": True,
            "payment_required": {"time": 1},
            "payment_capacity": {"time": 5},
            "required_preconditions": ["tests", "docs"],
            "met_preconditions": ["tests"],
            "required_capabilities": ["python", "pytest"],
            "active_capabilities": ["python"],
            "pathway": "run focused test and patch code",
            "expected_settlement": {"tests": "pass"},
            "risk": 0.1,
            "debt": 0.1,
        },
        context="production",
    )

    assert result["allowed"] is True
    assert result["blocking_reasons"] == []
    assert result["spendability_score"] >= 0.5
    assert result["factors"]["visibility"] == 1.0


# ---------------------------------------------------------------------------
# Task 3: Cognitive model – advisory controller ranking
# ---------------------------------------------------------------------------


def test_cognitive_model_controller_ranks_allowed_paths_without_overriding_gates():
    result = rank_candidates_by_controller(
        candidates=[
            {
                "id": "blocked",
                "governance_allowed": False,
                "settlement_accessible": True,
                "payment_required": {"time": 1},
                "payment_capacity": {"time": 10},
                "risk": 0.0,
                "debt": 0.0,
                "expected_horizon_delta": 100,
            },
            {
                "id": "steady",
                "governance_allowed": True,
                "settlement_accessible": True,
                "payment_required": {"time": 1},
                "payment_capacity": {"time": 10},
                "risk": 0.1,
                "debt": 0.1,
                "expected_horizon_delta": 3,
                "direction_score": 0.8,
            },
        ],
        context="production",
    )

    assert result["ranked"][0]["candidate_id"] == "steady"
    assert result["rejected"][0]["candidate_id"] == "blocked"


# ---------------------------------------------------------------------------
# Task 6: Calibration dataset builder
# ---------------------------------------------------------------------------


def test_build_calibration_frame_extracts_settlement_model_fields():
    frame = build_calibration_frame(
        settlements=[
            {
                "id": "set-1",
                "model_calibration": {
                    "payment_predicted": {"time": 1},
                    "payment_actual": {"time": 1.5},
                    "settlement_success": True,
                    "settlement_score": 0.8,
                    "horizon_delta": 2,
                    "risk_estimate": 0.1,
                    "debt_estimate": 0.2,
                },
            }
        ]
    )

    assert list(frame.columns) == [
        "settlement_id",
        "payment_predicted_total",
        "payment_actual_total",
        "payment_error",
        "settlement_success",
        "settlement_score",
        "horizon_delta",
        "risk_estimate",
        "debt_estimate",
        "tool_diversity_count",
        "error_recovery_ratio",
        "action_observation_ratio",
        "avg_actions_per_step",
        "dataset_id",
    ]
    assert frame.iloc[0]["payment_error"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Task 7: Built-in sklearn provider behind evidence gate
# ---------------------------------------------------------------------------


def test_sklearn_provider_is_registered_but_threshold_gated():
    result = build_predictive_extension_plan(
        settlement_history=[{"id": f"set-{index}"} for index in range(199)],
        candidates=[],
        ml_event_threshold=200,
        simulation_threshold=1000,
        model_port=resolve_model_provider("sklearn"),
    )

    assert result["stage"] == "deterministic_only"
    assert result["ml_predictions"] == []


def test_sklearn_provider_is_builtin_and_reports_provider_name():
    provider = resolve_model_provider("sklearn")
    assert provider.provider_name == "sklearn"


def test_sklearn_provider_reports_clear_missing_dependency(monkeypatch):
    provider = resolve_model_provider("sklearn")

    def missing_import():
        raise RuntimeError("sklearn_extra_required: install with uv sync --extra ml")

    monkeypatch.setattr(provider, "_require_sklearn", missing_import)

    with pytest.raises(RuntimeError, match="sklearn_extra_required"):
        provider.predict_affordances(
            settlement_history=[{"id": f"set-{index}"} for index in range(200)],
            candidates=[
                {
                    "id": "candidate-1",
                    "expected_horizon_delta": 2,
                    "risk": 0.1,
                }
            ],
            payment_estimates={"candidate-1": {"payment_burden": 1}},
        )
