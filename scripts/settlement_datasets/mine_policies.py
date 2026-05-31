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
        "failure_modes": ["tool_thrashing", "payment_spiral", "failed_recovery"],
        "trigger": {"error_count_gte": 3},
        "action": {
            "require_operator": "reflection",
            "block_next_action_until": "revised_plan_exists",
        },
        "rationale": "Repeated errors indicate settlement feedback is not being metabolized.",
    },
    {
        "id": "search_before_patch",
        "failure_modes": [
            "poor_localization",
            "bad_patch",
            "wrong_tool",
            "wrong_arguments",
        ],
        "trigger": {"action_type": "edit_or_api_call", "prior_search": False},
        "action": {
            "require_operator": "search_or_inspect",
            "block": "direct_edit_without_context",
        },
        "rationale": "Direct edits without prior inspection lead to localization failures.",
    },
    {
        "id": "compare_constraints_before_selection",
        "failure_modes": ["constraint_miss", "premature_choice", "premature_closure"],
        "trigger": {"selection_action": True, "prior_comparison": False},
        "action": {
            "require_operator": "constraint_verification",
            "block": "selection_without_comparison",
        },
        "rationale": "Selection without comparing against constraints leads to constraint misses.",
    },
    {
        "id": "inspect_api_schema_before_call",
        "failure_modes": ["wrong_tool", "wrong_arguments", "missing_precondition"],
        "trigger": {"api_call": True, "prior_schema_check": False},
        "action": {
            "require_operator": "schema_inspection",
            "block": "api_call_without_schema",
        },
        "rationale": "API calls without prior schema inspection lead to argument and tool errors.",
    },
    {
        "id": "reset_plan_after_payment_spiral",
        "failure_modes": ["payment_spiral", "over_search"],
        "trigger": {"step_count_gte": 8, "no_progress": True},
        "action": {
            "require_operator": "positive_disintegration",
            "suggest": "terminate_or_reset",
        },
        "rationale": "Extended unproductive payment should trigger path reset.",
    },
    {
        "id": "test_before_final_answer",
        "failure_modes": ["brittle_success", "premature_closure"],
        "trigger": {"final_answer_action": True, "prior_verification": False},
        "action": {
            "require_operator": "verification_step",
            "block": "answer_without_test",
        },
        "rationale": "Final answers without verification produce brittle or premature settlements.",
    },
    {
        "id": "require_explicit_settlement_for_failure",
        "failure_modes": ["failed_recovery", "test_failure"],
        "trigger": {"settlement_quality": "failure_with_signal"},
        "action": {
            "require_operator": "failure_analysis",
            "record": "error_correction_signal",
        },
        "rationale": "Failures with signals should produce explicit error-correction data.",
    },
    {
        "id": "prevent_premature_concretion",
        "failure_modes": ["premature_concretion", "premature_closure"],
        "trigger": {"early_specific_action": True, "turn_index_lt": 3},
        "action": {
            "require_operator": "intermediate_representation",
            "block": "direct_jump",
        },
        "rationale": "Jumping to specific action without analysis leads to premature concretion.",
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
        if total_support < min_supporting_traces:
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
            "trigger": template["trigger"],
            "action": template["action"],
            "rationale": template["rationale"],
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
