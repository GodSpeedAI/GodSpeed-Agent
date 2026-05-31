from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


def load_settlements(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    settlements: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            settlements.append(json.loads(line))
    return settlements


DEFAULT_MIN_CONFIDENCE = 0.65
DEFAULT_MIN_SUPPORTING_TRACES = 3


def mine_policies(
    settlements: list[dict[str, Any]],
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_supporting_traces: int = DEFAULT_MIN_SUPPORTING_TRACES,
) -> list[dict[str, Any]]:
    failure_mode_counts: Counter[str] = Counter()
    failure_mode_traces: dict[str, list[str]] = {}
    failure_mode_confidences: dict[str, list[float]] = {}
    policy_signal_counts: Counter[str] = Counter()
    policy_signal_traces: dict[str, list[str]] = {}
    settlement_quality_counts: Counter[str] = Counter()
    path_shape_counts: Counter[str] = Counter()

    for s in settlements:
        confidence = s.get("outcome", {}).get("confidence", 0.0)
        if confidence < min_confidence:
            continue

        sq = s.get("outcome", {}).get("settlement_quality", "unknown")
        settlement_quality_counts[sq] += 1

        ps = s.get("representational_state", {}).get("path_shape", "unknown")
        path_shape_counts[ps] += 1

        fm = s.get("cognitive_os_labels", {}).get("failure_mode")
        if fm:
            modes = fm if isinstance(fm, list) else [fm]
            for mode in modes:
                failure_mode_counts[mode] += 1
                failure_mode_traces.setdefault(mode, []).append(s.get("trace_id", ""))
                failure_mode_confidences.setdefault(mode, []).append(confidence)

        signal = s.get("cognitive_os_labels", {}).get("harness_policy_signal")
        if signal:
            policy_signal_counts[signal] += 1
            policy_signal_traces.setdefault(signal, []).append(s.get("trace_id", ""))

    total = len(settlements)
    policies: list[dict[str, Any]] = []

    policies.append(
        _build_policy(
            policy_id="require_reflection_after_repeated_tool_errors",
            trigger={"error_count_gte": 2},
            action={
                "require_operator": "reflection",
                "block_next_tool_call_until": "revised_plan_exists",
            },
            rationale="Repeated tool errors indicate settlement feedback is not being metabolized.",
            failure_modes=["tool_thrashing", "failed_recovery"],
            trace_count=sum(
                failure_mode_counts.get(m, 0)
                for m in ["tool_thrashing", "failed_recovery"]
            ),
            example_traces=failure_mode_traces.get("tool_thrashing", [])[:5],
            total_traces=total,
        )
    )

    policies.append(
        _build_policy(
            policy_id="block_premature_final_answer",
            trigger={"failure_mode": "premature_closure"},
            action={"require_settlement_evidence_before_final": True},
            rationale="Final answers without settlement evidence create false closure.",
            failure_modes=["premature_closure"],
            trace_count=failure_mode_counts.get("premature_closure", 0),
            example_traces=failure_mode_traces.get("premature_closure", [])[:5],
            total_traces=total,
        )
    )

    policies.append(
        _build_policy(
            policy_id="payment_spiral_reset",
            trigger={"payment_pattern": "high_payment_failure"},
            action={
                "require_positive_disintegration": True,
                "require_plan_reset": True,
            },
            rationale="High payment with no error reduction indicates path collapse.",
            failure_modes=["payment_spiral"],
            trace_count=failure_mode_counts.get("payment_spiral", 0),
            example_traces=failure_mode_traces.get("payment_spiral", [])[:5],
            total_traces=total,
        )
    )

    policies.append(
        _build_policy(
            policy_id="force_intermediate_representation_for_direct_jump",
            trigger={"failure_mode": "representation_jump"},
            action={
                "require_intermediate_state": {
                    "allowed_paths": [
                        "general_abstract_to_specific_abstract_to_specific_concrete",
                        "general_abstract_to_general_concrete_to_specific_concrete",
                    ]
                }
            },
            rationale="Direct representational opposition jumps are often unaffordable.",
            failure_modes=["representation_jump"],
            trace_count=failure_mode_counts.get("representation_jump", 0),
            example_traces=failure_mode_traces.get("representation_jump", [])[:5],
            total_traces=total,
        )
    )

    policies.append(
        _build_policy(
            policy_id="detect_context_loss",
            trigger={"turn_count_gt": 10, "later_turns_missing_early_keywords": True},
            action={"require_context_check": True, "restate_original_task": True},
            rationale="Later actions that ignore earlier constraints waste payment and produce settlement failure.",
            failure_modes=["context_loss"],
            trace_count=failure_mode_counts.get("context_loss", 0),
            example_traces=failure_mode_traces.get("context_loss", [])[:5],
            total_traces=total,
        )
    )

    policies.append(
        _build_policy(
            policy_id="flag_over_abstraction",
            trigger={
                "assistant_turn_count_gt": 5,
                "command_count_eq": 0,
                "no_final_answer": True,
            },
            action={"require_concrete_action": True, "suggest_tool_use": True},
            rationale="Extended explanation without concrete action suggests the agent is avoiding payment.",
            failure_modes=["over_abstraction"],
            trace_count=failure_mode_counts.get("over_abstraction", 0),
            example_traces=failure_mode_traces.get("over_abstraction", [])[:5],
            total_traces=total,
        )
    )

    policies.append(
        _build_policy(
            policy_id="prevent_premature_concretion",
            trigger={"first_assistant_is_action": True, "error_on_first_action": True},
            action={"require_constraint_gathering_before_action": True},
            rationale="Executing before understanding constraints leads to predictable error.",
            failure_modes=["premature_concretion"],
            trace_count=failure_mode_counts.get("premature_concretion", 0),
            example_traces=failure_mode_traces.get("premature_concretion", [])[:5],
            total_traces=total,
        )
    )

    policies.append(
        _build_policy(
            policy_id="require_recovery_evidence_for_brittle_success",
            trigger={"settlement_quality": "brittle_success"},
            action={
                "require_metabolization_evidence": True,
                "flag_for_repetition": True,
            },
            rationale="Success through excessive or fragile paths is not metabolized capability.",
            failure_modes=["brittle_success"],
            trace_count=failure_mode_counts.get("brittle_success", 0),
            example_traces=failure_mode_traces.get("brittle_success", [])[:5],
            total_traces=total,
        )
    )

    high_error_traces = [
        s.get("trace_id", "")
        for s in settlements
        if s.get("payment", {}).get("error_count", 0) >= 3
    ]
    policies.append(
        _build_policy(
            policy_id="escalate_after_three_errors",
            trigger={"error_count_gte": 3},
            action={
                "require_strategy_change": True,
                "suggest_alternative_approach": True,
            },
            rationale="Three or more errors without strategy change indicate the agent is stuck in a loop.",
            failure_modes=["tool_thrashing", "failed_recovery"],
            trace_count=len(high_error_traces),
            example_traces=high_error_traces[:5],
            total_traces=total,
        )
    )

    no_answer_traces = [
        s.get("trace_id", "")
        for s in settlements
        if s.get("outcome", {}).get("settlement_quality", "")
        in ("failure_with_signal", "failure_without_signal")
    ]
    policies.append(
        _build_policy(
            policy_id="require_explicit_settlement_for_failure",
            trigger={
                "settlement_quality_in": [
                    "failure_with_signal",
                    "failure_without_signal",
                ]
            },
            action={
                "require_failure_analysis": True,
                "record_error_correction_signal": True,
            },
            rationale="Failures without explicit settlement recording lose error-correction data.",
            failure_modes=[],
            trace_count=len(no_answer_traces),
            example_traces=no_answer_traces[:5],
            total_traces=total,
        )
    )

    long_traces_no_reward = [
        s.get("trace_id", "")
        for s in settlements
        if s.get("payment", {}).get("turn_count", 0) > 15
        and s.get("outcome", {}).get("settlement_quality", "unknown")
        not in ("clean_success", "recovered_success")
    ]
    policies.append(
        _build_policy(
            policy_id="payment_cap_for_unproductive_paths",
            trigger={"turn_count_gt": 15, "no_success": True},
            action={
                "require_positive_disintegration": True,
                "suggest_terminating_unproductive_path": True,
            },
            rationale="Long traces without progress drain payment without settlement.",
            failure_modes=["payment_spiral"],
            trace_count=len(long_traces_no_reward),
            example_traces=long_traces_no_reward[:5],
            total_traces=total,
        )
    )

    return policies


def _build_policy(
    policy_id: str,
    trigger: dict[str, Any],
    action: dict[str, Any],
    rationale: str,
    failure_modes: list[str],
    trace_count: int,
    example_traces: list[str],
    total_traces: int,
    confidence_distribution: list[float] | None = None,
) -> dict[str, Any]:
    avg_confidence = 0.0
    if confidence_distribution:
        avg_confidence = round(
            sum(confidence_distribution) / len(confidence_distribution), 2
        )
    return {
        "id": policy_id,
        "trigger": trigger,
        "action": action,
        "rationale": rationale,
        "evidence": {
            "supporting_trace_count": trace_count,
            "total_traces_analyzed": total_traces,
            "example_trace_ids": example_traces,
            "observed_failure_pattern": failure_modes,
            "proportion": round(trace_count / max(total_traces, 1), 4),
            "avg_label_confidence": avg_confidence,
            "meets_min_supporting_count": trace_count >= DEFAULT_MIN_SUPPORTING_TRACES,
        },
        "risk": {
            "false_positive_concern": "Deterministic heuristics may misclassify some traces.",
            "recommended_review": "Human review before activation in production harness.",
        },
        "active_by_default": False,
    }


def write_policies(policies: list[dict[str, Any]], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.dump(
            {"policies": policies},
            handle,
            default_flow_style=False,
            sort_keys=True,
            allow_unicode=True,
        )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mine harness policies from settlement traces."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/agenttrove/settlements/settlement_traces.jsonl",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="policies/generated/agenttrove_harness_policies.yaml",
    )
    args = parser.parse_args()

    settlements = load_settlements(args.input)
    print(f"Loaded {len(settlements)} settlement traces.")
    policies = mine_policies(settlements)
    path = write_policies(policies, args.output)
    print(f"Generated {len(policies)} candidate policies at {path}")
    for p in policies:
        count = p["evidence"]["supporting_trace_count"]
        print(f"  - {p['id']}: {count} supporting traces")


if __name__ == "__main__":
    main()
