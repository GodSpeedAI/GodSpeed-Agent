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
        assert len(results) > 0
        assert len(results) == len(records) * len(policies)

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


class TestCounterfactualAssessment:
    def test_helpful_on_failure_with_matching_mode(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(
            settlement_quality="failure_with_signal", failure_mode="tool_thrashing"
        )
        assessment, _, _, _ = _assess_counterfactual(policy, rec, fired=True)
        assert assessment == "likely_helpful"

    def test_harmful_on_clean_success_no_failure(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(settlement_quality="clean_success", failure_mode=None)
        assessment, _, payment_risk, fp_risk = _assess_counterfactual(
            policy, rec, fired=True
        )
        assert assessment == "likely_harmful"
        assert fp_risk == "high"

    def test_uncertain_on_partial_success(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(
            settlement_quality="partial_success", failure_mode="tool_thrashing"
        )
        assessment, _, _, _ = _assess_counterfactual(policy, rec, fired=True)
        assert assessment == "uncertain"

    def test_no_effect_when_not_fired(self):
        policy = _make_policy()
        rec = _make_record()
        assessment, rationale, _, _ = _assess_counterfactual(policy, rec, fired=False)
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


class TestFalsePositiveRiskEstimation:
    def test_fp_risk_high_on_clean_success_firing(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(settlement_quality="clean_success", failure_mode=None)
        _, _, _, fp_risk = _assess_counterfactual(policy, rec, fired=True)
        assert fp_risk == "high"

    def test_fp_risk_low_on_failure_firing(self):
        policy = _make_policy(failure_modes=["tool_thrashing"])
        rec = _make_record(
            settlement_quality="failure_with_signal",
            failure_mode="tool_thrashing",
            error_count=5,
        )
        _, _, _, fp_risk = _assess_counterfactual(policy, rec, fired=True)
        assert fp_risk == "low"


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
            assert r["match_result"] in (
                "match",
                "mismatch",
                "uncertain",
                "no_expected_behavior",
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
                assert "match_rate" in s


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
                assert rec["recommended_status"] in (
                    "proposed",
                    "keep_proposed",
                    "candidate_for_activation",
                    "refine",
                    "reject",
                    "needs_more_evidence",
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
