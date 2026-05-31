from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)
from scripts.settlement_datasets.registry import available_datasets


POLICY_TEMPLATES = [
    {
        "id": "require_reflection_after_repeated_errors",
        "status": "proposed",
        "failure_modes": ["tool_thrashing", "payment_spiral", "failed_recovery"],
        "trigger": {"error_count_gte": 3, "errors_are_unresolved": True},
        "negative_conditions": [
            "errors_are_resolved_in_subsequent_turns",
            "error_count_is_only_analysis_mentions",
        ],
        "required_evidence": [
            "at_least_3_error_outputs_from_environment_or_tool",
            "errors_remain_unresolved_at_trace_end_or_last_3_turns",
        ],
        "action": {
            "require_operator": "reflection",
            "block_next_action_until": "revised_plan_exists",
        },
        "rationale": "Repeated unresolved errors from environment/tool feedback indicate settlement feedback is not being metabolized.",
        "false_positive_risk": "low",
        "payment_risk": "low",
    },
    {
        "id": "search_before_patch",
        "status": "proposed",
        "failure_modes": [
            "poor_localization",
            "bad_patch",
            "wrong_tool",
            "wrong_arguments",
        ],
        "trigger": {"action_type": "edit_or_api_call", "prior_search": False},
        "negative_conditions": [
            "action_is_low_cost_exploratory",
            "intermediate_representation_exists_in_prior_turns",
        ],
        "required_evidence": [
            "edit_or_api_call_attempted",
            "no_prior_search_or_inspection_before_edit_or_call",
        ],
        "action": {
            "require_operator": "search_or_inspect",
            "block": "direct_edit_without_context",
        },
        "rationale": "Direct edits without prior inspection lead to localization failures.",
        "false_positive_risk": "low",
        "payment_risk": "low",
    },
    {
        "id": "require_constraint_match_before_multi_option_selection",
        "status": "proposed",
        "supersedes": "compare_constraints_before_selection",
        "failure_modes": ["constraint_miss", "premature_choice"],
        "trigger": {
            "selection_action": True,
            "multiple_viable_options_present": True,
            "explicit_constraints_exist": True,
            "no_constraint_match_evidence": True,
        },
        "negative_conditions": [
            "only_one_viable_option_exists",
            "no_explicit_constraints_in_instruction",
            "selection_is_exploratory_not_final",
            "selected_option_has_explicit_match_evidence",
        ],
        "required_evidence": [
            "at_least_2_viable_candidates_observed_before_selection",
            "user_instruction_contains_explicit_constraints",
            "no_evidence_that_selected_item_matches_all_constraints",
        ],
        "action": {
            "require_operator": "constraint_verification",
            "block": "selection_without_comparison",
        },
        "rationale": "When multiple options exist and constraints are explicit, selection without constraint comparison leads to constraint misses.",
        "false_positive_risk": "low",
        "payment_risk": "low",
    },
    {
        "id": "compare_constraints_before_selection",
        "status": "superseded",
        "superseded_by": "require_constraint_match_before_multi_option_selection",
        "failure_modes": ["constraint_miss", "premature_choice", "premature_closure"],
        "trigger": {"selection_action": True, "prior_comparison": False},
        "negative_conditions": [],
        "required_evidence": [
            "selection_action_present",
            "no_prior_comparison_step_detected",
        ],
        "action": {
            "require_operator": "constraint_verification",
            "block": "selection_without_comparison",
        },
        "rationale": "Selection without comparing against constraints leads to constraint misses.",
        "false_positive_risk": "high",
        "payment_risk": "low",
    },
    {
        "id": "inspect_api_schema_before_call",
        "status": "proposed",
        "failure_modes": ["wrong_tool", "wrong_arguments", "missing_precondition"],
        "trigger": {"api_call": True, "prior_schema_check": False},
        "negative_conditions": [
            "intermediate_representation_exists_in_prior_turns",
        ],
        "required_evidence": [
            "api_call_attempted",
            "no_prior_schema_or_tool_inspection_detected",
        ],
        "action": {
            "require_operator": "schema_inspection",
            "block": "api_call_without_schema",
        },
        "rationale": "API calls without prior schema inspection lead to argument and tool errors.",
        "false_positive_risk": "low",
        "payment_risk": "low",
    },
    {
        "id": "reset_plan_after_payment_spiral",
        "status": "proposed",
        "failure_modes": ["payment_spiral", "over_search"],
        "trigger": {"step_count_gte": 8, "no_progress": True},
        "negative_conditions": [
            "errors_are_resolved_in_subsequent_turns",
        ],
        "required_evidence": [
            "step_count_exceeds_payment_spiral_threshold",
            "trace_still_shows_no_progress",
        ],
        "action": {
            "require_operator": "positive_disintegration",
            "suggest": "terminate_or_reset",
        },
        "rationale": "Extended unproductive payment should trigger path reset.",
        "false_positive_risk": "low",
        "payment_risk": "medium",
    },
    {
        "id": "require_test_or_settlement_evidence_before_final_for_code_patch",
        "status": "proposed",
        "supersedes": "test_before_final_answer",
        "failure_modes": ["brittle_success", "premature_closure"],
        "trigger": {
            "domain_is_code": True,
            "action_history_includes_edit": True,
            "final_answer_attempted": True,
            "no_settlement_evidence": True,
        },
        "negative_conditions": [
            "domain_is_not_code",
            "no_code_edit_in_action_history",
            "test_output_already_present",
            "task_complete_marker_is_true",
            "explicit_evaluator_success_exists",
            "successful_command_output_relevant_to_task",
        ],
        "required_evidence": [
            "action_history_includes_code_edit_patch_or_implementation",
            "final_answer_or_task_complete_attempted_after_edit",
            "no_passing_test_output_between_last_edit_and_final_answer",
            "no_task_complete_true_marker",
            "no_explicit_success_signal_from_evaluator",
        ],
        "action": {
            "require_operator": "verification_step",
            "block": "answer_without_test_or_settlement_signal",
        },
        "rationale": "Code patches without test output or settlement evidence before final answer risk brittle or premature closure.",
        "false_positive_risk": "low",
        "payment_risk": "low",
    },
    {
        "id": "test_before_final_answer",
        "status": "superseded",
        "superseded_by": "require_test_or_settlement_evidence_before_final_for_code_patch",
        "failure_modes": ["brittle_success", "premature_closure"],
        "trigger": {"final_answer_action": True, "prior_verification": False},
        "negative_conditions": [],
        "required_evidence": [
            "final_answer_or_completion_attempted",
            "no_prior_verification_signal_detected",
        ],
        "action": {
            "require_operator": "verification_step",
            "block": "answer_without_test",
        },
        "rationale": "Final answers without verification produce brittle or premature settlements.",
        "false_positive_risk": "high",
        "payment_risk": "medium",
    },
    {
        "id": "require_explicit_settlement_for_failure",
        "status": "proposed",
        "failure_modes": ["failed_recovery", "test_failure"],
        "trigger": {
            "settlement_quality": "failure_with_signal",
            "has_failure_condition_evidence": True,
        },
        "negative_conditions": [
            "settlement_quality_is_not_failure_with_signal",
            "no_failure_condition_evidence_available",
        ],
        "required_evidence": [
            "settlement_quality_is_failure_with_signal",
            "failure_condition_has_observable_evidence_test_output_error_message_or_tool_feedback",
        ],
        "action": {
            "require_operator": "failure_analysis",
            "record": "error_correction_signal",
        },
        "rationale": "Failures with observable signals should produce explicit error-correction data backed by actual failure condition evidence.",
        "false_positive_risk": "low",
        "payment_risk": "low",
    },
    {
        "id": "prevent_high_payment_action_when_constraints_unknown",
        "status": "proposed",
        "supersedes": "prevent_premature_concretion",
        "failure_modes": [
            "premature_concretion",
            "premature_closure",
            "constraint_miss",
        ],
        "trigger": {
            "constraints_missing_or_ambiguous": True,
            "high_payment_or_irreversible_action": True,
            "no_intermediate_representation": True,
            "no_user_feedback_resolved_ambiguity": True,
        },
        "negative_conditions": [
            "constraints_are_explicit_and_clear",
            "action_is_low_cost_exploratory",
            "intermediate_representation_exists_in_prior_turns",
            "user_or_environment_feedback_has_resolved_ambiguity",
        ],
        "required_evidence": [
            "task_constraints_are_missing_or_ambiguous",
            "action_is_high_payment_edit_delete_commit_submit_purchase_or_irreversible_api",
            "no_analysis_plan_or_intermediate_step_between_task_start_and_action",
            "no_environment_or_user_feedback_between_task_and_action",
        ],
        "action": {
            "require_operator": "intermediate_representation",
            "block": "direct_high_payment_action_with_unknown_constraints",
        },
        "rationale": "High-payment or irreversible actions when constraints are unknown risk premature concretion without affordance for correction.",
        "false_positive_risk": "low",
        "payment_risk": "medium",
    },
    {
        "id": "prevent_premature_concretion",
        "status": "superseded",
        "superseded_by": "prevent_high_payment_action_when_constraints_unknown",
        "failure_modes": ["premature_concretion", "premature_closure"],
        "trigger": {"early_specific_action": True, "turn_index_lt": 3},
        "negative_conditions": [],
        "required_evidence": [
            "early_specific_action_taken",
            "action_occurs_before_intermediate_representation",
        ],
        "action": {
            "require_operator": "intermediate_representation",
            "block": "direct_jump",
        },
        "rationale": "Jumping to specific action without analysis leads to premature concretion.",
        "false_positive_risk": "high",
        "payment_risk": "medium",
    },
]


def mine_policies(
    records: list[dict[str, Any]],
    min_confidence: float = 0.65,
    min_supporting_traces: int = 3,
) -> list[dict[str, Any]]:
    failure_mode_counts = Counter()
    failure_mode_traces: dict[str, list[str]] = {}
    failure_mode_datasets: dict[str, set[str]] = {}

    for rec in records:
        conf = rec.get("outcome", {}).get("confidence", 0.0)
        if conf < min_confidence:
            continue

        fm = rec.get("labels", {}).get("failure_mode")
        if fm:
            failure_mode_counts[fm] += 1
            failure_mode_traces.setdefault(fm, []).append(rec.get("task_id", ""))
            failure_mode_datasets.setdefault(fm, set()).add(rec.get("dataset", ""))

    policies = []
    for template in POLICY_TEMPLATES:
        matching_fms = template["failure_modes"]
        total_support = sum(failure_mode_counts.get(fm, 0) for fm in matching_fms)
        if template.get("status") != "superseded" and total_support < min_supporting_traces:
            continue

        all_trace_ids = []
        all_datasets = set()
        for fm in matching_fms:
            all_trace_ids.extend(failure_mode_traces.get(fm, [])[:10])
            all_datasets.update(failure_mode_datasets.get(fm, set()))

        confidences = []
        for rec in records:
            if rec.get("labels", {}).get("failure_mode") in matching_fms:
                c = rec.get("outcome", {}).get("confidence", 0.0)
                if c >= min_confidence:
                    confidences.append(c)

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        policy = {
            "id": template["id"],
            "status": template.get("status", "proposed"),
            "supersedes": template.get("supersedes"),
            "superseded_by": template.get("superseded_by"),
            "trigger": template["trigger"],
            "negative_conditions": template.get("negative_conditions", []),
            "required_evidence": template.get("required_evidence", []),
            "action": template["action"],
            "rationale": template["rationale"],
            "false_positive_risk": template.get("false_positive_risk", "low"),
            "payment_risk": template.get("payment_risk", "low"),
            "evidence": {
                "supporting_trace_count": total_support,
                "supporting_dataset_count": len(all_datasets),
                "supporting_datasets": sorted(all_datasets),
                "total_traces_analyzed": len(records),
                "example_trace_ids": all_trace_ids[:5],
                "observed_failure_patterns": matching_fms,
                "proportion": round(total_support / len(records), 3)
                if records
                else 0.0,
                "avg_label_confidence": round(avg_conf, 3),
                "confidence_distribution": {
                    "min": round(min(confidences), 3) if confidences else 0.0,
                    "max": round(max(confidences), 3) if confidences else 0.0,
                    "mean": round(avg_conf, 3),
                },
                "meets_min_supporting_count": total_support >= min_supporting_traces,
            },
            "risk": {
                "false_positive_concern": "Deterministic heuristics may misclassify some traces.",
                "recommended_review": "Human review before activation in production harness.",
            },
            "activation_status": "proposed",
            "active_by_default": False,
        }
        policies.append(policy)

    return policies


def write_policies(policies: list[dict], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        yaml.dump({"policies": policies}, f, default_flow_style=False, sort_keys=False)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mine harness policies across datasets"
    )
    parser.add_argument(
        "--dataset",
        default="all",
        choices=["agenttrove", "swegym", "apibank", "webshop", "all"],
    )
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default="data/settlement_datasets/policies.yaml")
    parser.add_argument("--min-confidence", type=float, default=0.65)
    parser.add_argument("--min-supporting-traces", type=int, default=3)

    args = parser.parse_args()

    datasets = available_datasets() if args.dataset == "all" else [args.dataset]
    all_records = []

    for ds in datasets:
        input_path = args.input or f"data/settlement_datasets/settlements/{ds}.jsonl"
        p = Path(input_path)
        if p.exists():
            all_records.extend(read_records_jsonl(str(p)))

    policies = mine_policies(
        all_records,
        min_confidence=args.min_confidence,
        min_supporting_traces=args.min_supporting_traces,
    )
    path = write_policies(policies, args.output)
    print(f"Generated {len(policies)} policies -> {path}")
    for p in policies:
        print(
            f"  {p['id']}: {p['evidence']['supporting_trace_count']} supporting traces across {p['evidence']['supporting_dataset_count']} datasets"
        )


if __name__ == "__main__":
    main()
