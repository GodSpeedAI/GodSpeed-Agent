from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)
from scripts.settlement_datasets.evaluate_policies_shadow import (
    _assess_counterfactual,
    _check_trigger,
    compute_promotion_scores,
    evaluate_policies_shadow,
    generate_policy_evidence_packs,
)
from scripts.settlement_datasets.replay_policy_evals import (
    compute_replay_summary,
    replay_evals,
)
from scripts.settlement_datasets.update_policy_status import update_policy_status
from scripts.settlement_datasets.update_metabolization_status import (
    update_metabolization_status,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "settlement_datasets"


def _load_records():
    all_records = []
    for ds in ("agenttrove", "swegym", "apibank", "webshop"):
        path = FIXTURES_DIR / ds / "sample.jsonl"
        if path.exists():
            from scripts.settlement_datasets.registry import get_adapter

            adapter = get_adapter(ds)
            for raw in adapter.stream(input_path=str(path)):
                all_records.append(adapter.to_settlement_record(raw))
    return all_records


def _load_policies():
    path = Path("data/settlement_datasets/policies.yaml")
    if not path.exists():
        pytest.skip("No policies.yaml available")
    with path.open() as f:
        return yaml.safe_load(f).get("policies", [])


def _make_policy(
    policy_id="test_policy", trigger=None, failure_modes=None, evidence=None
):
    return {
        "id": policy_id,
        "trigger": trigger or {"error_count_gte": 3},
        "action": {"require_operator": "reflection"},
        "evidence": {
            "observed_failure_patterns": failure_modes
            or ["tool_thrashing", "failed_recovery"],
            "supporting_trace_count": 5,
        },
    }


def _make_record(
    error_count=0,
    settlement_quality="clean_success",
    failure_mode=None,
    turns=4,
    domain="code",
    dataset="test",
    confidence=0.8,
):
    return {
        "task_id": "test-trace-001",
        "dataset": dataset,
        "domain": domain,
        "outcome": {"settlement_quality": settlement_quality, "confidence": confidence},
        "payment": {
            "turns": turns,
            "error_count": error_count,
            "elapsed_steps": turns,
            "commands": 0,
            "tool_calls": 0,
            "page_actions": 0,
            "api_calls": 0,
            "estimated_complexity": "unknown",
            "evidence": [],
        },
        "labels": {
            "failure_mode": failure_mode,
            "failure_mode_confidence": 0.8 if failure_mode else 0.0,
            "failure_mode_evidence": [],
            "harness_policy_signal": None,
            "harness_policy_signal_confidence": 0.0,
            "harness_policy_signal_evidence": [],
            "metabolization_candidate": None,
            "metabolization_candidate_confidence": 0.0,
            "metabolization_candidate_evidence": [],
        },
        "affordance_path": {"actions": [], "observations": [], "recovery_events": []},
    }


class TestPolicyTriggerMatching:
    def test_error_count_gte_fires(self):
        rec = _make_record(error_count=5)
        fired, evidence = _check_trigger({"error_count_gte": 3}, rec)
        assert fired is True
        assert len(evidence) > 0

    def test_error_count_gte_no_fire(self):
        rec = _make_record(error_count=1)
        fired, evidence = _check_trigger({"error_count_gte": 3}, rec)
        assert fired is False

    def test_settlement_quality_trigger(self):
        rec = _make_record(settlement_quality="failure_with_signal")
        fired, evidence = _check_trigger(
            {"settlement_quality": "failure_with_signal"}, rec
        )
        assert fired is True

    def test_settlement_quality_no_match(self):
        rec = _make_record(settlement_quality="clean_success")
        fired, evidence = _check_trigger(
            {"settlement_quality": "failure_with_signal"}, rec
        )
        assert fired is False

    def test_step_count_gte_with_no_progress(self):
        rec = _make_record(turns=10, settlement_quality="failure_with_signal")
        fired, evidence = _check_trigger(
            {"step_count_gte": 8, "no_progress": True}, rec
        )
        assert fired is True

    def test_step_count_gte_with_progress(self):
        rec = _make_record(turns=10, settlement_quality="clean_success")
        fired, evidence = _check_trigger(
            {"step_count_gte": 8, "no_progress": True}, rec
        )
        assert fired is False

    def test_empty_trigger_no_fire(self):
        rec = _make_record()
        fired, evidence = _check_trigger({}, rec)
        assert fired is False

    def test_early_specific_action_trigger(self):
        rec = _make_record()
        rec["affordance_path"]["actions"] = [
            {"action_type": "command", "turn_index": 0, "content": "edit file"},
        ]
        fired, evidence = _check_trigger(
            {"early_specific_action": True, "turn_index_lt": 3}, rec
        )
        assert fired is True


class TestWouldHaveFiredResultGeneration:
    def test_shadow_evaluation_generates_results(self):
        records = _load_records()
        policies = _load_policies()
        results = evaluate_policies_shadow(records, policies, min_confidence=0.0)
        active_policies = [p for p in policies if p.get("status") != "superseded"]
        assert len(results) > 0
        assert len(results) == len(records) * len(active_policies)

    def test_each_result_has_required_fields(self):
        records = _load_records()
        policies = _load_policies()
        results = evaluate_policies_shadow(records, policies, min_confidence=0.0)
        for r in results:
            assert "policy_id" in r
            assert "trace_id" in r
            assert "would_fire" in r
            assert "counterfactual_assessment" in r
            assert "false_positive_risk" in r
            assert "payment_risk" in r

    def test_would_fire_result_includes_timing_and_recovery_fields(self):
        policy = _make_policy(
            policy_id="late_edit_policy",
            trigger={"early_specific_action": True, "turn_index_lt": 4},
        )
        record = _make_record(turns=4)
        record["affordance_path"]["actions"] = [
            {"action_type": "command", "turn_index": 3, "content": "edit file"},
        ]

        results = evaluate_policies_shadow([record], [policy], min_confidence=0.0)

        assert results[0]["would_fire"] is True
        assert results[0]["fire_turn_index"] == 3
        assert results[0]["fire_timing"] == "final_turn"
        assert results[0]["remaining_turns_after_fire"] == 0
        assert results[0]["recovery_opportunity"] is False
        assert results[0]["recovery_opportunity_evidence"]

    def test_uncertain_result_includes_reason_and_evidence(self):
        policy = _make_policy(
            policy_id="reflection_policy",
            trigger={"error_count_gte": 3},
            failure_modes=["tool_thrashing"],
        )
        record = _make_record(
            error_count=4,
            settlement_quality="partial_success",
            failure_mode="tool_thrashing",
            turns=6,
        )
        record["affordance_path"]["observations"] = [
            {"turn_index": 1, "role": "user", "content": "Traceback: fail 1"},
            {"turn_index": 2, "role": "user", "content": "Error: fail 2"},
            {"turn_index": 3, "role": "user", "content": "Exception: fail 3"},
        ]
        record["affordance_path"]["actions"] = [
            {"action_type": "command", "turn_index": 4, "content": "retry command"},
            {"action_type": "analysis", "turn_index": 5, "content": "inspect failure"},
        ]

        results = evaluate_policies_shadow([record], [policy], min_confidence=0.0)

        assert results[0]["counterfactual_assessment"] == "uncertain"
        assert results[0]["uncertainty_reason"] == "conflicting_settlement_evidence"
        assert results[0]["uncertainty_evidence"]

    def test_settlement_quality_trigger_marks_failure_already_settled(self):
        policy = _make_policy(
            policy_id="failure_policy",
            trigger={
                "settlement_quality": "failure_with_signal",
                "has_failure_condition_evidence": True,
            },
            failure_modes=["failed_recovery"],
        )
        record = _make_record(
            error_count=2,
            settlement_quality="failure_with_signal",
            failure_mode="failed_recovery",
            turns=5,
        )

        results = evaluate_policies_shadow([record], [policy], min_confidence=0.0)

        assert results[0]["would_fire"] is True
        assert results[0]["fire_timing"] == "after_failure_already_settled"
        assert results[0]["recovery_opportunity"] is False

    def test_target_policy_filter_limits_shadow_results(self):
        records = [_make_record(error_count=4), _make_record(error_count=1)]
        policies = [
            _make_policy(policy_id="target_policy", trigger={"error_count_gte": 3}),
            _make_policy(policy_id="other_policy", trigger={"error_count_gte": 1}),
        ]

        results = evaluate_policies_shadow(
            records,
            policies,
            min_confidence=0.0,
            target_policy_ids={"target_policy"},
        )

        assert {r["policy_id"] for r in results} == {"target_policy"}
        assert len(results) == len(records)


class TestCounterfactualAssessment:
    def test_helpful_on_failure_with_matching_mode(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(
            settlement_quality="failure_with_signal", failure_mode="tool_thrashing"
        )
        assessment, *_ = _assess_counterfactual(policy, rec, fired=True)
        assert assessment == "likely_helpful"

    def test_harmful_on_clean_success_no_failure(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(settlement_quality="clean_success", failure_mode=None)
        assessment, _, payment_risk, fp_risk, *_ = _assess_counterfactual(
            policy, rec, fired=True
        )
        assert assessment == "likely_harmful"
        assert fp_risk == "high"

    def test_uncertain_on_partial_success(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(
            settlement_quality="partial_success", failure_mode="tool_thrashing"
        )
        assessment, *_ = _assess_counterfactual(policy, rec, fired=True)
        assert assessment == "uncertain"

    def test_no_effect_when_not_fired(self):
        policy = _make_policy()
        rec = _make_record()
        assessment, rationale, *_ = _assess_counterfactual(policy, rec, fired=False)
        assert assessment == "no_effect"
        assert "not met" in rationale


class TestPromotionScoring:
    def test_promotion_scores_generated(self):
        records = _load_records()
        policies = _load_policies()
        results = evaluate_policies_shadow(records, policies, min_confidence=0.0)
        scores = compute_promotion_scores(results, policies)
        assert len(scores) == len(policies)

    def test_each_score_has_required_fields(self):
        records = _load_records()
        policies = _load_policies()
        results = evaluate_policies_shadow(records, policies, min_confidence=0.0)
        scores = compute_promotion_scores(results, policies)
        for s in scores:
            assert "policy_id" in s
            assert "would_fire_count" in s
            assert "likely_helpful_count" in s
            assert "likely_harmful_count" in s
            assert "uncertainty_reason_distribution" in s
            assert "fire_timing_distribution" in s
            assert "recovery_opportunity_count" in s
            assert "helpful_with_recovery_opportunity_count" in s
            assert "uncertain_with_recovery_opportunity_count" in s
            assert "fires_after_failure_settled_count" in s
            assert "recommendation" in s
            assert s["recommendation"] in (
                "keep_proposed",
                "candidate_for_activation",
                "refine",
                "reject",
                "needs_more_evidence",
            )

    def test_no_fire_means_needs_more_evidence(self):
        policy = _make_policy(policy_id="never_fires")
        policy["trigger"] = {"error_count_gte": 100}
        rec = _make_record(error_count=0)
        results = evaluate_policies_shadow([rec], [policy], min_confidence=0.0)
        scores = compute_promotion_scores(results, [policy])
        assert scores[0]["recommendation"] == "needs_more_evidence"

    def test_harmful_means_reject(self):
        policy = _make_policy(
            policy_id="harmful_test", failure_modes=["tool_thrashing"]
        )
        records = [
            _make_record(
                error_count=5,
                settlement_quality="clean_success",
                failure_mode=None,
                confidence=0.9,
            ),
            _make_record(
                error_count=4,
                settlement_quality="clean_success",
                failure_mode=None,
                confidence=0.9,
            ),
            _make_record(
                error_count=5,
                settlement_quality="failure_with_signal",
                failure_mode="tool_thrashing",
                confidence=0.9,
            ),
        ]
        results = evaluate_policies_shadow(records, [policy], min_confidence=0.0)
        scores = compute_promotion_scores(results, [policy])
        assert scores[0]["recommendation"] in ("reject", "refine")

    def test_summary_rolls_up_uncertainty_timing_and_recovery(self):
        policy = _make_policy(
            policy_id="summary_policy",
            trigger={"error_count_gte": 3},
            failure_modes=["tool_thrashing"],
        )
        uncertain_record = _make_record(
            error_count=3,
            settlement_quality="partial_success",
            failure_mode="tool_thrashing",
            turns=6,
        )
        uncertain_record["affordance_path"]["observations"] = [
            {"turn_index": 1, "role": "user", "content": "Error: fail 1"},
            {"turn_index": 2, "role": "user", "content": "Error: fail 2"},
            {"turn_index": 3, "role": "user", "content": "Error: fail 3"},
        ]
        uncertain_record["affordance_path"]["actions"] = [
            {"action_type": "command", "turn_index": 4, "content": "retry"},
        ]

        settled_failure_policy = _make_policy(
            policy_id="settled_failure_policy",
            trigger={
                "settlement_quality": "failure_with_signal",
                "has_failure_condition_evidence": True,
            },
            failure_modes=["failed_recovery"],
        )
        settled_failure_record = _make_record(
            error_count=2,
            settlement_quality="failure_with_signal",
            failure_mode="failed_recovery",
            turns=5,
        )

        uncertain_results = evaluate_policies_shadow(
            [uncertain_record], [policy], min_confidence=0.0
        )
        settled_failure_results = evaluate_policies_shadow(
            [settled_failure_record], [settled_failure_policy], min_confidence=0.0
        )
        scores = compute_promotion_scores(
            uncertain_results + settled_failure_results,
            [policy, settled_failure_policy],
        )

        summary_policy_score = next(
            score for score in scores if score["policy_id"] == "summary_policy"
        )
        assert summary_policy_score["uncertainty_reason_distribution"] == {
            "conflicting_settlement_evidence": 1
        }
        assert summary_policy_score["fire_timing_distribution"] == {"late": 1}
        assert summary_policy_score["recovery_opportunity_count"] == 1
        assert summary_policy_score["uncertain_with_recovery_opportunity_count"] == 1

        settled_failure_score = next(
            score
            for score in scores
            if score["policy_id"] == "settled_failure_policy"
        )
        assert settled_failure_score["fires_after_failure_settled_count"] == 1


class TestFalsePositiveRiskEstimation:
    def test_fp_risk_high_on_clean_success_firing(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(settlement_quality="clean_success", failure_mode=None)
        _, _, _, fp_risk, *_ = _assess_counterfactual(policy, rec, fired=True)
        assert fp_risk == "high"

    def test_fp_risk_low_on_failure_firing(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(
            settlement_quality="failure_with_signal",
            failure_mode="tool_thrashing",
            error_count=5,
        )
        _, _, _, fp_risk, *_ = _assess_counterfactual(policy, rec, fired=True)
        assert fp_risk == "low"


class TestPolicyEvidencePacks:
    def test_evidence_pack_generation_writes_target_policy_markdown(self):
        policy = _make_policy(
            policy_id="require_reflection_after_repeated_errors",
            trigger={"error_count_gte": 3, "errors_are_unresolved": True},
            failure_modes=["tool_thrashing"],
        )
        record = _make_record(
            error_count=3,
            settlement_quality="partial_success",
            failure_mode="tool_thrashing",
            turns=6,
        )
        record["affordance_path"]["observations"] = [
            {"turn_index": 1, "content": "Error: first failure"},
            {"turn_index": 2, "content": "Error: second failure"},
            {"turn_index": 3, "content": "Error: third failure"},
        ]
        record["affordance_path"]["actions"] = [
            {"action_type": "command", "turn_index": 4, "content": "retry command"},
        ]
        results = evaluate_policies_shadow(
            [record],
            [policy],
            min_confidence=0.0,
            target_policy_ids={policy["id"]},
        )

        with tempfile.TemporaryDirectory() as td:
            written = generate_policy_evidence_packs(
                results,
                [policy],
                td,
                target_policy_ids={policy["id"]},
            )

            assert len(written) == 1
            body = written[0].read_text()
            assert "# require_reflection_after_repeated_errors" in body
            assert "Policy Definition" in body
            assert "Uncertain Examples By Reason" in body
            assert "Fire Timing Distribution" in body
            assert "Recovery Opportunity Distribution" in body
            assert "Recommendation" in body

    def test_evidence_pack_generation_only_writes_target_policies(self):
        target = _make_policy(policy_id="require_explicit_settlement_for_failure")
        other = _make_policy(policy_id="unrelated_policy")
        results = evaluate_policies_shadow(
            [_make_record(error_count=4)],
            [target, other],
            min_confidence=0.0,
            target_policy_ids={target["id"]},
        )

        with tempfile.TemporaryDirectory() as td:
            written = generate_policy_evidence_packs(
                results,
                [target, other],
                td,
                target_policy_ids={target["id"]},
            )

            assert [path.name for path in written] == [
                "require_explicit_settlement_for_failure.md"
            ]


class TestEvalReplayMatching:
    def test_replay_generates_results(self):
        policies = _load_policies()
        results = replay_evals(
            policies, eval_dir="data/settlement_datasets/evals/", min_confidence=0.0
        )
        assert isinstance(results, list)

    def test_replay_results_have_required_fields(self):
        policies = _load_policies()
        results = replay_evals(
            policies, eval_dir="data/settlement_datasets/evals/", min_confidence=0.0
        )
        for r in results:
            assert "policy_id" in r
            assert "match_result" in r
            assert "policy_canonical_action" in r
            assert "eval_canonical_action" in r
            assert "semantic_match" in r
            assert "match_confidence" in r
            assert r["match_result"] in (
                "exact_semantic_match",
                "partial_semantic_match",
                "mismatch",
                "unknown_policy_action",
                "unknown_eval_behavior",
                "insufficient_evidence",
            )

    def test_replay_summary_computation(self):
        policies = _load_policies()
        results = replay_evals(
            policies, eval_dir="data/settlement_datasets/evals/", min_confidence=0.0
        )
        if results:
            summary = compute_replay_summary(results)
            assert len(summary) > 0
            for s in summary:
                assert "raw_match_rate" in s
                assert "semantic_match_rate" in s
                assert "partial_match_rate" in s
                assert "unknown_policy_action_count" in s
                assert "unknown_eval_behavior_count" in s
                assert "excluded_unknown_count" in s


class TestPolicyStatusRecommendation:
    def test_status_update_generates_yaml(self):
        shadow_path = (
            "data/settlement_datasets/policy_shadow_eval/policy_shadow_results.jsonl"
        )
        policies_path = "data/settlement_datasets/policies.yaml"
        if not Path(shadow_path).exists() or not Path(policies_path).exists():
            pytest.skip("Shadow results not available")

        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "status.yaml"
            result = update_policy_status(shadow_path, policies_path, str(output))
            assert result.exists()

            with result.open() as f:
                data = yaml.safe_load(f)
            recs = data.get("policy_status_recommendations", [])
            assert len(recs) > 0
            for rec in recs:
                assert "policy_id" in rec
                assert "recommended_status" in rec
                assert "semantic_replay" in rec["evidence"]
                assert rec["recommended_status"] in (
                    "proposed",
                    "keep_proposed",
                    "candidate_for_activation",
                    "refine",
                    "reject",
                    "needs_more_evidence",
                    "superseded",
                )


class TestMetabolizationStatusUpdate:
    def test_update_produces_output(self):
        cand_path = (
            "data/settlement_datasets/metabolization_candidates/candidates.jsonl"
        )
        if not Path(cand_path).exists():
            pytest.skip("Candidates not available")

        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "updated.jsonl"
            result = update_metabolization_status(cand_path, output_path=str(output))
            assert result.exists()
            updated = read_records_jsonl(str(output))
            assert len(updated) > 0

    def test_no_metabolized_status(self):
        cand_path = (
            "data/settlement_datasets/metabolization_candidates/candidates.jsonl"
        )
        if not Path(cand_path).exists():
            pytest.skip("Candidates not available")

        updated = read_records_jsonl(
            "data/settlement_datasets/metabolization_candidates/candidates_updated.jsonl"
        )
        for c in updated:
            assert c["metabolization_status"] != "metabolized"

    def test_candidate_promotes_to_repeated(self):
        candidates = [
            {
                "candidate_id": "test-1",
                "pattern_name": "test_pattern",
                "supporting_trace_count": 5,
                "metabolization_status": "candidate",
                "dataset_sources": ["test"],
                "description": "test",
                "supporting_trace_ids": [],
                "settlement_quality_distribution": {},
                "payment_profile": {},
                "failure_modes_recovered_from": [],
                "proposed_skill": {
                    "name": "test",
                    "trigger": "",
                    "procedure": [],
                    "settlement_criteria": "",
                    "retirement_criteria": "",
                },
                "risks": [],
                "evidence_summary": "",
                "domain": "code",
            }
        ]
        with tempfile.TemporaryDirectory() as td:
            cand_path = Path(td) / "candidates.jsonl"
            write_records_jsonl(candidates, str(cand_path))
            output_path = Path(td) / "updated.jsonl"
            update_metabolization_status(str(cand_path), output_path=str(output_path))
            updated = read_records_jsonl(str(output_path))
            assert updated[0]["metabolization_status"] == "repeated"


class TestRefinedPolicyTriggers:
    def test_pre_settlement_reflection_trigger_fires_on_second_distinct_error(self):
        policy = {
            "id": "require_reflection_before_continuing_after_second_unresolved_error",
            "trigger": {"second_unresolved_error_before_continuing": True},
            "negative_conditions": [
                "duplicate_error_signals_only",
                "strategy_revision_after_latest_error",
                "low_cost_inspection_after_latest_error",
                "closure_or_settlement_after_latest_error",
            ],
            "evidence": {"observed_failure_patterns": ["tool_thrashing"]},
            "action": {"require_operator": "reflection"},
        }
        rec = _make_record(
            error_count=2,
            settlement_quality="failure_with_signal",
            failure_mode="tool_thrashing",
            turns=5,
        )
        rec["affordance_path"]["observations"] = [
            {"turn_index": 1, "content": "Traceback: missing import in app.py"},
            {"turn_index": 2, "content": "Error: NameError still raised in app.py"},
        ]
        rec["affordance_path"]["actions"] = [
            {"action_type": "command", "turn_index": 3, "content": "python app.py"},
            {"action_type": "command", "turn_index": 4, "content": "retry implementation"},
        ]

        results = evaluate_policies_shadow([rec], [policy], min_confidence=0.0)

        assert results[0]["would_fire"] is True
        assert results[0]["fire_turn_index"] == 2
        assert results[0]["fire_timing"] == "middle"
        assert results[0]["recovery_opportunity"] is True
        assert "distinct_unresolved_error_count=2" in results[0]["trigger_evidence"]

    def test_pre_settlement_reflection_trigger_ignores_duplicate_errors(self):
        policy = {
            "id": "require_reflection_before_continuing_after_second_unresolved_error",
            "trigger": {"second_unresolved_error_before_continuing": True},
            "negative_conditions": ["duplicate_error_signals_only"],
        }
        rec = _make_record(error_count=2, settlement_quality="failure_with_signal", turns=4)
        rec["affordance_path"]["observations"] = [
            {"turn_index": 1, "content": "Traceback: module missing"},
            {"turn_index": 2, "content": "Traceback: module missing"},
        ]
        rec["affordance_path"]["actions"] = [
            {"action_type": "command", "turn_index": 3, "content": "python app.py"},
        ]

        fired, _ = _check_trigger(
            policy["trigger"], rec, policy["negative_conditions"]
        )

        assert fired is False

    def test_pre_settlement_reflection_trigger_blocks_on_strategy_revision(self):
        policy = {
            "id": "require_reflection_before_continuing_after_second_unresolved_error",
            "trigger": {"second_unresolved_error_before_continuing": True},
            "negative_conditions": ["strategy_revision_after_latest_error"],
        }
        rec = _make_record(error_count=2, settlement_quality="failure_with_signal", turns=5)
        rec["affordance_path"]["observations"] = [
            {"turn_index": 1, "content": "Error: first failure"},
            {"turn_index": 2, "content": "Error: second failure"},
        ]
        rec["affordance_path"]["actions"] = [
            {"action_type": "analysis", "turn_index": 3, "content": "new plan: inspect the failing path"},
            {"action_type": "command", "turn_index": 4, "content": "python app.py"},
        ]

        fired, _ = _check_trigger(
            policy["trigger"], rec, policy["negative_conditions"]
        )

        assert fired is False

    def test_pre_settlement_reflection_trigger_blocks_on_low_cost_inspection(self):
        policy = {
            "id": "require_reflection_before_continuing_after_second_unresolved_error",
            "trigger": {"second_unresolved_error_before_continuing": True},
            "negative_conditions": ["low_cost_inspection_after_latest_error"],
        }
        rec = _make_record(error_count=2, settlement_quality="failure_with_signal", turns=5)
        rec["affordance_path"]["observations"] = [
            {"turn_index": 1, "content": "Error: first failure"},
            {"turn_index": 2, "content": "Error: second failure"},
        ]
        rec["affordance_path"]["actions"] = [
            {"action_type": "command", "turn_index": 3, "content": "cat failing_test.py"},
            {"action_type": "command", "turn_index": 4, "content": "ls tests"},
        ]

        fired, _ = _check_trigger(
            policy["trigger"], rec, policy["negative_conditions"]
        )

        assert fired is False

    def test_pre_settlement_reflection_trigger_blocks_on_final_turn(self):
        policy = {
            "id": "require_reflection_before_continuing_after_second_unresolved_error",
            "trigger": {"second_unresolved_error_before_continuing": True},
            "negative_conditions": ["closure_or_settlement_after_latest_error"],
        }
        rec = _make_record(error_count=2, settlement_quality="failure_with_signal", turns=2)
        rec["affordance_path"]["observations"] = [
            {"turn_index": 0, "content": "Error: first failure"},
            {"turn_index": 1, "content": "Error: second failure"},
        ]

        fired, _ = _check_trigger(
            policy["trigger"], rec, policy["negative_conditions"]
        )

        assert fired is False

    def test_pre_settlement_reflection_trigger_ignores_analysis_mentions(self):
        policy = {
            "id": "require_reflection_before_continuing_after_second_unresolved_error",
            "trigger": {"second_unresolved_error_before_continuing": True},
        }
        rec = _make_record(error_count=0, settlement_quality="clean_success", turns=5)
        rec["affordance_path"]["actions"] = [
            {
                "action_type": "analysis",
                "turn_index": 0,
                "content": "The issue mentions a TypeError on empty input.",
            },
            {
                "action_type": "analysis",
                "turn_index": 1,
                "content": "The failure likely comes from the parser raising an exception.",
            },
            {"action_type": "command", "turn_index": 2, "content": "cat parser.py"},
            {"action_type": "command", "turn_index": 3, "content": "sed -i 's/x/y/' parser.py"},
        ]

        fired, _ = _check_trigger(policy["trigger"], rec)

        assert fired is False

    def test_pre_settlement_failure_evidence_trigger_fires_for_code_test_failure(self):
        policy = {
            "id": "require_failure_evidence_before_stopping_on_test_failure",
            "trigger": {"closure_without_failure_evidence_after_test_failure": True},
            "negative_conditions": [
                "domain_is_not_code",
                "failure_evidence_already_present",
                "task_already_settled",
            ],
            "evidence": {"observed_failure_patterns": ["test_failure", "failed_recovery"]},
            "action": {"require_operator": "failure_analysis"},
        }
        rec = _make_record(
            error_count=1,
            settlement_quality="failure_with_signal",
            failure_mode="test_failure",
            turns=5,
        )
        rec["affordance_path"]["observations"] = [
            {"turn_index": 1, "content": "pytest output: 2 failed, 5 passed"},
        ]
        rec["affordance_path"]["actions"] = [
            {"action_type": "analysis", "turn_index": 2, "content": "I cannot complete this because tests failed"},
            {"action_type": "command", "turn_index": 3, "content": "collect failure details"},
            {"action_type": "command", "turn_index": 4, "content": "write summary"},
        ]

        results = evaluate_policies_shadow([rec], [policy], min_confidence=0.0)

        assert results[0]["would_fire"] is True
        assert results[0]["fire_turn_index"] == 2
        assert results[0]["recovery_opportunity"] is True
        assert "test_failure_signal_detected" in results[0]["trigger_evidence"]
        assert "closure_attempt_detected" in results[0]["trigger_evidence"]

    def test_pre_settlement_failure_evidence_trigger_fires_on_repeated_failed_tests(self):
        policy = {
            "id": "require_failure_evidence_before_stopping_on_test_failure",
            "trigger": {"closure_without_failure_evidence_after_test_failure": True},
            "negative_conditions": [
                "domain_is_not_code",
                "failure_evidence_already_present",
                "task_already_settled",
            ],
            "evidence": {"observed_failure_patterns": ["test_failure"]},
            "action": {"require_operator": "failure_analysis"},
        }
        rec = _make_record(
            error_count=2,
            settlement_quality="failure_with_signal",
            failure_mode="test_failure",
            turns=6,
        )
        rec["affordance_path"]["observations"] = [
            {"turn_index": 1, "content": "pytest output: test_parser FAILED"},
            {"turn_index": 3, "content": "pytest output: test_parser FAILED again"},
        ]
        rec["affordance_path"]["actions"] = [
            {"action_type": "command", "turn_index": 2, "content": "apply patch"},
            {"action_type": "command", "turn_index": 4, "content": "retry parser patch"},
            {"action_type": "analysis", "turn_index": 5, "content": "still failing"},
        ]

        results = evaluate_policies_shadow([rec], [policy], min_confidence=0.0)

        assert results[0]["would_fire"] is True
        assert results[0]["fire_turn_index"] == 3
        assert results[0]["recovery_opportunity"] is True
        assert "repeated_test_failure_signal_detected" in results[0]["trigger_evidence"]

    def test_pre_settlement_failure_evidence_trigger_blocks_when_evidence_exists(self):
        policy = {
            "id": "require_failure_evidence_before_stopping_on_test_failure",
            "trigger": {"closure_without_failure_evidence_after_test_failure": True},
            "negative_conditions": ["failure_evidence_already_present"],
        }
        rec = _make_record(
            error_count=1,
            settlement_quality="failure_with_signal",
            failure_mode="test_failure",
            turns=4,
        )
        rec["affordance_path"]["observations"] = [
            {"turn_index": 1, "content": "pytest output: AssertionError in test_login"},
        ]
        rec["affordance_path"]["actions"] = [
            {
                "action_type": "analysis",
                "turn_index": 2,
                "content": "Observed failing test_login assertion with stack trace in pytest output",
            },
            {
                "action_type": "analysis",
                "turn_index": 3,
                "content": "I cannot complete this because tests failed",
            },
        ]

        fired, _ = _check_trigger(
            policy["trigger"], rec, policy["negative_conditions"]
        )

        assert fired is False

    def test_pre_settlement_failure_evidence_trigger_is_code_specific(self):
        policy = {
            "id": "require_failure_evidence_before_stopping_on_test_failure",
            "trigger": {"closure_without_failure_evidence_after_test_failure": True},
            "negative_conditions": ["domain_is_not_code"],
        }
        rec = _make_record(
            error_count=1,
            settlement_quality="failure_with_signal",
            failure_mode="test_failure",
            turns=4,
            domain="api",
        )
        rec["affordance_path"]["observations"] = [
            {"turn_index": 1, "content": "tests failed for request payload"},
        ]
        rec["affordance_path"]["actions"] = [
            {
                "action_type": "analysis",
                "turn_index": 2,
                "content": "I cannot complete this because tests failed",
            },
        ]

        fired, _ = _check_trigger(
            policy["trigger"], rec, policy["negative_conditions"]
        )

        assert fired is False

    def test_code_patch_trigger_fires_on_code_edit_without_test(self):
        policy = {
            "id": "require_test_or_settlement_evidence_before_final_for_code_patch",
            "trigger": {
                "domain_is_code": True,
                "action_history_includes_edit": True,
                "final_answer_attempted": True,
                "no_settlement_evidence": True,
            },
        }
        rec = _make_record(
            domain="code", settlement_quality="brittle_success", confidence=0.6
        )
        rec["affordance_path"]["actions"] = [
            {
                "action_type": "command",
                "content": "sed -i 's/old/new/' file.py",
                "turn_index": 1,
            },
            {"action_type": "command", "content": "submit answer", "turn_index": 2},
        ]
        fired, evidence = _check_trigger(policy["trigger"], rec)
        assert fired is True
        assert any("domain_is_code" in e for e in evidence)

    def test_code_patch_trigger_does_not_fire_on_api_domain(self):
        policy = {
            "id": "require_test_or_settlement_evidence_before_final_for_code_patch",
            "trigger": {
                "domain_is_code": True,
                "action_history_includes_edit": True,
                "final_answer_attempted": True,
                "no_settlement_evidence": True,
            },
        }
        rec = _make_record(domain="api", settlement_quality="clean_success")
        rec["affordance_path"]["actions"] = [
            {
                "action_type": "api_call",
                "content": "get_weather(city='Paris')",
                "turn_index": 1,
            },
        ]
        fired, _ = _check_trigger(policy["trigger"], rec)
        assert fired is False

    def test_code_patch_trigger_does_not_fire_with_test_output(self):
        policy = {
            "id": "require_test_or_settlement_evidence_before_final_for_code_patch",
            "trigger": {
                "domain_is_code": True,
                "action_history_includes_edit": True,
                "final_answer_attempted": True,
                "no_settlement_evidence": True,
            },
        }
        rec = _make_record(
            domain="code", settlement_quality="clean_success", confidence=0.9
        )
        rec["affordance_path"]["actions"] = [
            {
                "action_type": "command",
                "content": "sed -i 's/old/new/' file.py",
                "turn_index": 1,
            },
            {
                "action_type": "observation",
                "content": "2 passed in 0.1s",
                "turn_index": 2,
                "role": "tool",
            },
        ]
        fired, _ = _check_trigger(policy["trigger"], rec)
        assert fired is False

    def test_high_payment_trigger_fires_on_unknown_constraints(self):
        policy = {
            "id": "prevent_high_payment_action_when_constraints_unknown",
            "trigger": {
                "constraints_missing_or_ambiguous": True,
                "high_payment_or_irreversible_action": True,
                "no_intermediate_representation": True,
                "no_user_feedback_resolved_ambiguity": True,
            },
        }
        rec = _make_record(domain="code", settlement_quality="failure_with_signal")
        rec["desired_direction"] = {"type": "action", "description": "fix the bug"}
        rec["affordance_path"]["actions"] = [
            {"action_type": "command", "content": "rm -rf /tmp/test", "turn_index": 0},
        ]
        rec["affordance_path"]["observations"] = []
        fired, evidence = _check_trigger(policy["trigger"], rec)
        assert fired is True

    def test_high_payment_trigger_does_not_fire_with_analysis(self):
        policy = {
            "id": "prevent_high_payment_action_when_constraints_unknown",
            "trigger": {
                "constraints_missing_or_ambiguous": True,
                "high_payment_or_irreversible_action": True,
                "no_intermediate_representation": True,
                "no_user_feedback_resolved_ambiguity": True,
            },
        }
        rec = _make_record(domain="code")
        rec["desired_direction"] = {"type": "action", "description": "fix the bug"}
        rec["affordance_path"]["actions"] = [
            {
                "action_type": "analysis",
                "content": "Let me inspect the issue",
                "turn_index": 0,
            },
            {"action_type": "command", "content": "rm -rf /tmp/test", "turn_index": 1},
        ]
        fired, _ = _check_trigger(policy["trigger"], rec)
        assert fired is False

    def test_constraint_match_trigger_requires_explicit_constraints(self):
        policy = {
            "id": "require_constraint_match_before_multi_option_selection",
            "trigger": {
                "selection_action": True,
                "multiple_viable_options_present": True,
                "explicit_constraints_exist": True,
                "no_constraint_match_evidence": True,
            },
        }
        rec = _make_record(domain="shopping")
        rec["desired_direction"] = {
            "type": "action",
            "description": "Find a red laptop under $800",
        }
        rec["affordance_path"]["actions"] = [
            {"action_type": "search", "content": "laptop", "turn_index": 0},
            {
                "action_type": "observation",
                "content": "Found 5 results",
                "turn_index": 1,
            },
            {"action_type": "buy", "content": "buy item 1", "turn_index": 2},
        ]
        rec["affordance_path"]["observations"] = [
            {
                "content": "Found 5 results: laptop1, laptop2, laptop3, laptop4, laptop5",
                "turn_index": 1,
            },
        ]
        fired, evidence = _check_trigger(policy["trigger"], rec)
        assert fired is True

    def test_constraint_match_trigger_does_not_fire_without_constraints(self):
        policy = {
            "id": "require_constraint_match_before_multi_option_selection",
            "trigger": {
                "selection_action": True,
                "multiple_viable_options_present": True,
                "explicit_constraints_exist": True,
                "no_constraint_match_evidence": True,
            },
        }
        rec = _make_record(domain="shopping")
        rec["desired_direction"] = {"type": "action", "description": "Buy a laptop"}
        rec["affordance_path"]["actions"] = [
            {"action_type": "search", "content": "laptop", "turn_index": 0},
            {
                "action_type": "observation",
                "content": "Found 5 results",
                "turn_index": 1,
            },
            {"action_type": "buy", "content": "buy item 1", "turn_index": 2},
        ]
        rec["affordance_path"]["observations"] = [
            {"content": "Found 5 results", "turn_index": 1},
        ]
        fired, _ = _check_trigger(policy["trigger"], rec)
        assert fired is False


class TestNegativeConditions:
    def test_negative_condition_blocks_firing(self):
        policy = {
            "id": "test_neg",
            "trigger": {"error_count_gte": 3},
            "negative_conditions": ["errors_are_resolved_in_subsequent_turns"],
        }
        rec = _make_record(error_count=3, settlement_quality="recovered_success")
        rec["affordance_path"]["recovery_events"] = [
            {"error_turn": 2, "recovery_turn": 4, "recovered": True},
            {"error_turn": 3, "recovery_turn": 5, "recovered": True},
            {"error_turn": 4, "recovery_turn": 6, "recovered": True},
        ]
        fired, evidence = _check_trigger(
            policy["trigger"], rec, policy.get("negative_conditions")
        )
        assert fired is False

    def test_no_negative_conditions_allows_firing(self):
        policy = {
            "id": "test_none",
            "trigger": {"error_count_gte": 3},
        }
        rec = _make_record(error_count=5, settlement_quality="failure_with_signal")
        fired, evidence = _check_trigger(policy["trigger"], rec)
        assert fired is True


class TestSupersededPolicyHandling:
    def test_superseded_policies_excluded_from_shadow(self):
        records = _load_records()
        policies = _load_policies()
        results = evaluate_policies_shadow(records, policies, min_confidence=0.0)
        superseded_ids = {
            "compare_constraints_before_selection",
            "test_before_final_answer",
            "prevent_premature_concretion",
        }
        for r in results:
            if r["policy_id"] in superseded_ids:
                pytest.fail(
                    f"Superseded policy {r['policy_id']} should not appear in shadow results"
                )

    def test_refined_policies_appear_in_results(self):
        records = _load_records()
        policies = _load_policies()
        results = evaluate_policies_shadow(records, policies, min_confidence=0.0)
        refined_ids = {
            "require_test_or_settlement_evidence_before_final_for_code_patch",
            "prevent_high_payment_action_when_constraints_unknown",
            "require_constraint_match_before_multi_option_selection",
        }
        found_ids = {r["policy_id"] for r in results}
        for rid in refined_ids:
            assert rid in found_ids, f"Refined policy {rid} not found in results"


class TestFalsePositivePrevention:
    def test_refined_policies_have_zero_harmful_on_successful_traces(self):
        records = _load_records()
        policies = _load_policies()
        results = evaluate_policies_shadow(records, policies, min_confidence=0.0)
        refined_ids = {
            "require_test_or_settlement_evidence_before_final_for_code_patch",
            "prevent_high_payment_action_when_constraints_unknown",
            "require_constraint_match_before_multi_option_selection",
        }
        for r in results:
            if r["policy_id"] in refined_ids and r["would_fire"]:
                if (
                    r["observed_settlement_quality"]
                    in ("clean_success", "recovered_success")
                    and r["observed_failure_mode"] is None
                ):
                    assert r["counterfactual_assessment"] != "likely_harmful", (
                        f"Refined policy {r['policy_id']} harms successful trace {r['trace_id']}"
                    )

    def test_refined_fire_count_less_than_original(self):
        records = _load_records()
        policies = _load_policies()
        results = evaluate_policies_shadow(records, policies, min_confidence=0.0)
        fire_counts = {}
        for r in results:
            if r["would_fire"]:
                fire_counts[r["policy_id"]] = fire_counts.get(r["policy_id"], 0) + 1

        original_policies = []
        for policy in policies:
            if policy["id"] in {
                "test_before_final_answer",
                "prevent_premature_concretion",
                "compare_constraints_before_selection",
            }:
                original_policies.append({**policy, "status": "proposed"})
        original_results = evaluate_policies_shadow(
            records, original_policies, min_confidence=0.0
        )
        original_fire_counts = {}
        for r in original_results:
            if r["would_fire"]:
                original_fire_counts[r["policy_id"]] = (
                    original_fire_counts.get(r["policy_id"], 0) + 1
                )

        assert fire_counts.get(
            "require_test_or_settlement_evidence_before_final_for_code_patch", 0
        ) <= original_fire_counts.get("test_before_final_answer", 0)
        assert fire_counts.get(
            "prevent_high_payment_action_when_constraints_unknown", 0
        ) <= original_fire_counts.get("prevent_premature_concretion", 0)
        assert fire_counts.get(
            "require_constraint_match_before_multi_option_selection", 0
        ) <= original_fire_counts.get("compare_constraints_before_selection", 0)
