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


CANDIDATE_TEMPLATES = [
    {
        "pattern_name": "reflect_after_repeated_tool_error",
        "description": "After 3+ tool/API errors in sequence, agent reflects and changes approach before retrying.",
        "trigger": "error_count >= 3",
        "procedure": [
            "detect_error_pattern",
            "pause_action",
            "analyze_root_cause",
            "revise_approach",
            "retry_with_new_strategy",
        ],
        "settlement_criteria": "Agent breaks error loop and makes progress with revised approach.",
        "retirement_criteria": "Agent no longer enters error loops of this type.",
    },
    {
        "pattern_name": "test_before_final_answer",
        "description": "Before submitting final answer or patch, agent runs verification step.",
        "trigger": "final_answer_action about to execute",
        "procedure": [
            "detect_final_answer_intent",
            "run_verification",
            "check_verification_result",
            "proceed_or_revise",
        ],
        "settlement_criteria": "Final answer is verified correct before submission.",
        "retirement_criteria": "Verification is habitual and catches all known failure modes.",
    },
    {
        "pattern_name": "search_before_patch",
        "description": "Before editing code or making changes, agent searches/inspects relevant context.",
        "trigger": "edit_or_patch_action about to execute",
        "procedure": [
            "detect_edit_intent",
            "search_relevant_files",
            "analyze_context",
            "plan_edit",
            "execute_edit",
        ],
        "settlement_criteria": "Edit is well-localized and addresses the root cause.",
        "retirement_criteria": "Agent consistently localizes correctly before editing.",
    },
    {
        "pattern_name": "inspect_api_schema_before_call",
        "description": "Before making API calls, agent inspects available schemas and parameters.",
        "trigger": "api_call_action about to execute",
        "procedure": [
            "detect_api_call_intent",
            "inspect_available_apis",
            "verify_parameters",
            "execute_call",
        ],
        "settlement_criteria": "API call uses correct tool with correct arguments.",
        "retirement_criteria": "Agent no longer makes wrong-tool or wrong-argument errors.",
    },
    {
        "pattern_name": "compare_constraints_before_selection",
        "description": "Before selecting/purchasing, agent compares options against all stated constraints.",
        "trigger": "selection_or_buy_action about to execute",
        "procedure": [
            "detect_selection_intent",
            "enumerate_constraints",
            "compare_options",
            "verify_best_match",
            "select",
        ],
        "settlement_criteria": "Selected item satisfies all stated constraints.",
        "retirement_criteria": "Agent consistently makes constraint-satisfying selections.",
    },
    {
        "pattern_name": "reset_plan_after_payment_spiral",
        "description": "When payment exceeds threshold without progress, agent resets approach.",
        "trigger": "step_count >= 8 AND no_progress_signal",
        "procedure": [
            "detect_payment_spiral",
            "pause_current_plan",
            "analyze_what_failed",
            "generate_alternative_plan",
            "execute_new_plan",
        ],
        "settlement_criteria": "Agent abandons unproductive path and makes progress on new path.",
        "retirement_criteria": "Agent recognizes unproductive paths before spiraling.",
    },
    {
        "pattern_name": "route_through_intermediate_representation",
        "description": "For complex tasks, agent creates intermediate plan/analysis before acting.",
        "trigger": "task_complexity >= medium AND no_prior_analysis",
        "procedure": [
            "assess_task_complexity",
            "create_intermediate_plan",
            "validate_plan",
            "execute_plan_steps",
        ],
        "settlement_criteria": "Task is completed with fewer errors due to upfront planning.",
        "retirement_criteria": "Agent consistently plans before acting on complex tasks.",
    },
]


def _compute_payment_profile(records: list[dict]) -> dict[str, Any]:
    if not records:
        return {"median_steps": 0, "median_tool_calls": 0, "median_error_count": 0}

    steps = sorted([r.get("payment", {}).get("elapsed_steps", 0) for r in records])
    tools = sorted(
        [
            r.get("payment", {}).get("tool_calls", 0)
            + r.get("payment", {}).get("api_calls", 0)
            for r in records
        ]
    )
    errors = sorted([r.get("payment", {}).get("error_count", 0) for r in records])

    def median(vals):
        n = len(vals)
        if n == 0:
            return 0
        return vals[n // 2]

    return {
        "median_steps": median(steps),
        "median_tool_calls": median(tools),
        "median_error_count": median(errors),
    }


def mine_metabolization_candidates(
    records: list[dict[str, Any]],
    min_confidence: float = 0.65,
) -> list[dict[str, Any]]:
    candidates = []

    for template in CANDIDATE_TEMPLATES:
        matching_records = []
        for rec in records:
            conf = rec.get("outcome", {}).get("confidence", 0.0)
            if conf < min_confidence:
                continue

            sq = rec.get("outcome", {}).get("settlement_quality", "")
            fm = rec.get("labels", {}).get("failure_mode")
            metab = rec.get("labels", {}).get("metabolization_candidate")

            is_success = sq in ("clean_success", "recovered_success")
            has_recovery = sq == "recovered_success" or fm in ("failed_recovery",)
            is_candidate_pattern = False

            if (
                "error" in template["pattern_name"]
                and rec.get("payment", {}).get("error_count", 0) >= 2
                and is_success
            ):
                is_candidate_pattern = True
            elif (
                "test" in template["pattern_name"]
                and sq in ("clean_success",)
                and rec.get("environment", {}).get("feedback_type") == "tests"
            ):
                is_candidate_pattern = True
            elif (
                "search" in template["pattern_name"]
                and fm in ("poor_localization", "bad_patch")
                and is_success
            ):
                is_candidate_pattern = True
            elif (
                "schema" in template["pattern_name"]
                and fm in ("wrong_tool", "wrong_arguments")
                and is_success
            ):
                is_candidate_pattern = True
            elif (
                "constraint" in template["pattern_name"]
                and fm in ("constraint_miss", "premature_choice")
                and is_success
            ):
                is_candidate_pattern = True
            elif (
                "reset" in template["pattern_name"]
                and fm in ("payment_spiral", "over_search")
                and has_recovery
            ):
                is_candidate_pattern = True
            elif (
                "intermediate" in template["pattern_name"]
                and is_success
                and rec.get("representational_state", {}).get("path_shape")
                in ("GA_to_SA_to_SC", "GA_to_GC_to_SC")
            ):
                is_candidate_pattern = True

            if is_candidate_pattern or metab:
                matching_records.append(rec)

        if not matching_records:
            continue

        sq_dist = Counter(
            r.get("outcome", {}).get("settlement_quality", "unknown")
            for r in matching_records
        )
        fms_recovered = list(
            set(
                r.get("labels", {}).get("failure_mode", "")
                for r in matching_records
                if r.get("labels", {}).get("failure_mode")
            )
        )
        datasets = list(set(r.get("dataset", "") for r in matching_records))

        candidate = {
            "candidate_id": f"metab-{template['pattern_name'][:20]}-{len(matching_records)}",
            "domain": ", ".join(
                sorted(set(r.get("domain", "") for r in matching_records))
            ),
            "dataset_sources": datasets,
            "pattern_name": template["pattern_name"],
            "description": template["description"],
            "supporting_trace_count": len(matching_records),
            "supporting_trace_ids": [
                r.get("task_id", "") for r in matching_records[:10]
            ],
            "settlement_quality_distribution": dict(sq_dist),
            "payment_profile": _compute_payment_profile(matching_records),
            "failure_modes_recovered_from": fms_recovered,
            "proposed_skill": {
                "name": template["pattern_name"],
                "trigger": template["trigger"],
                "procedure": template["procedure"],
                "settlement_criteria": template["settlement_criteria"],
                "retirement_criteria": template["retirement_criteria"],
            },
            "metabolization_status": "repeated"
            if len(matching_records) >= 3
            else "candidate",
            "risks": [
                "Pattern extracted from deterministic heuristics, not validated in live harness.",
                "Supporting traces may share confounding factors.",
            ],
            "evidence_summary": f"{len(matching_records)} traces from {len(datasets)} datasets support this pattern. Quality distribution: {dict(sq_dist)}.",
        }
        candidates.append(candidate)

    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mine metabolization candidates across datasets"
    )
    parser.add_argument(
        "--dataset",
        default="all",
        choices=["agenttrove", "swegym", "apibank", "webshop", "all"],
    )
    parser.add_argument("--input", default=None)
    parser.add_argument(
        "--output",
        default="data/settlement_datasets/metabolization_candidates/candidates.jsonl",
    )
    parser.add_argument("--min-confidence", type=float, default=0.65)

    args = parser.parse_args()
    datasets = available_datasets() if args.dataset == "all" else [args.dataset]

    all_records = []
    for ds in datasets:
        input_path = args.input or f"data/settlement_datasets/settlements/{ds}.jsonl"
        p = Path(input_path)
        if p.exists():
            all_records.extend(read_records_jsonl(str(p)))

    candidates = mine_metabolization_candidates(
        all_records, min_confidence=args.min_confidence
    )
    path = write_records_jsonl(candidates, args.output)

    print(
        f"Mined {len(candidates)} metabolization candidates from {len(all_records)} records -> {path}"
    )
    for c in candidates:
        print(
            f"  {c['pattern_name']}: {c['supporting_trace_count']} traces, status={c['metabolization_status']}"
        )


if __name__ == "__main__":
    main()
