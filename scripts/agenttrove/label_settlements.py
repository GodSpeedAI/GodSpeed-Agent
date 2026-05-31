from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.agenttrove.parsing import (
    count_json_commands,
    detect_structural_errors,
    detect_task_complete,
    extract_user_task_content,
    infer_settlement_from_structure,
    is_system_prompt_boilerplate,
    parse_assistant_content,
)
from scripts.agenttrove.profile_traces import (
    count_error_like_outputs,
    find_first_error_turn,
    has_final_answer,
    is_command_like,
    is_error_like,
)


def load_rules(
    rules_path: str | Path = "configs/agenttrove/settlement_label_rules.yaml",
) -> dict[str, Any]:
    return yaml.safe_load(Path(rules_path).read_text(encoding="utf-8"))


def classify_desired_direction(
    messages: list[dict[str, Any]], rules: dict[str, Any]
) -> dict[str, str]:
    task_content = extract_user_task_content(messages)
    if not task_content:
        user_messages = [m for m in messages if m.get("role") == "user"]
        if user_messages:
            task_content = user_messages[0].get("content", "")
    if not task_content:
        return {"type": "unknown", "description": "", "settlement_target": ""}

    lower_content = task_content.lower()
    direction_keywords = rules.get("desired_direction_keywords", {})

    best_type = "unknown"
    best_count = 0
    for direction_type, keywords in direction_keywords.items():
        count = sum(1 for kw in keywords if kw in lower_content)
        if count > best_count:
            best_count = count
            best_type = direction_type

    snippet = lower_content[:200]
    return {
        "type": best_type,
        "description": snippet,
        "settlement_target": snippet[:100],
    }


def classify_path_shape(
    messages: list[dict[str, Any]], profile: dict[str, Any]
) -> dict[str, str]:
    if not messages:
        return {"start": "unknown", "desired": "unknown", "path_shape": "unknown"}

    turn_count = profile.get("turn_count", 0)
    error_count = profile.get("error_like_output_count", 0)
    total_command_count = profile.get("command_like_action_count", 0)
    assistant_count = profile.get("assistant_turn_count", 0)
    user_count = profile.get("user_turn_count", 0)

    task_content = extract_user_task_content(messages)
    is_broad_start = len(task_content) > 50 or "?" in task_content

    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    first_has_commands = False
    if assistant_messages:
        parsed = parse_assistant_content(assistant_messages[0].get("content", ""))
        first_has_commands = bool(parsed["commands"]) or is_command_like(
            assistant_messages[0].get("content", "")
        )

    if is_broad_start and turn_count < 5 and first_has_commands:
        return {
            "start": "general_abstract",
            "desired": "specific_concrete",
            "path_shape": "direct_jump",
        }
    if error_count >= 3 and total_command_count >= 3 and turn_count > 10:
        return {
            "start": "general_abstract",
            "desired": "specific_concrete",
            "path_shape": "thrash",
        }
    if is_broad_start and assistant_count > 2 and total_command_count > 0:
        return {
            "start": "general_abstract",
            "desired": "specific_concrete",
            "path_shape": "GA_to_SA_to_SC",
        }
    if first_has_commands and error_count > 0:
        return {
            "start": "specific_concrete",
            "desired": "specific_concrete",
            "path_shape": "direct_action_with_feedback",
        }
    if assistant_count > 3 and user_count > 1 and turn_count > 10:
        return {
            "start": "general_abstract",
            "desired": "specific_concrete",
            "path_shape": "GA_to_GC_to_SC",
        }
    return {"start": "unknown", "desired": "unknown", "path_shape": "unknown"}


def estimate_payment_complexity(profile: dict[str, Any], rules: dict[str, Any]) -> str:
    turn_count = profile.get("turn_count", 0)
    command_count = profile.get("command_like_action_count", 0)
    error_count = profile.get("error_like_output_count", 0)

    if turn_count < 5 and command_count < 2 and error_count < 1:
        return "low"
    if turn_count >= 15 or command_count >= 5 or error_count >= 3:
        return "high"
    return "medium"


def classify_settlement_quality(
    trace: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    messages = trace.get("messages", [])
    reward = trace.get("reward")
    error_count = profile.get("error_like_output_count", 0)
    turn_count = profile.get("turn_count", 0)

    try:
        reward_val = float(reward) if reward is not None else None
    except (TypeError, ValueError):
        reward_val = None

    evidence: list[str] = []

    if reward_val is not None:
        evidence.append(f"reward:{reward_val}")

    if reward_val is not None and reward_val >= 1.0:
        if error_count == 0:
            return {
                "settlement_quality": "clean_success",
                "confidence": 0.95,
                "evidence": evidence + ["reward>=1.0", "error_count:0"],
            }
        if error_count >= 1:
            if turn_count > 15 and error_count >= 3:
                return {
                    "settlement_quality": "brittle_success",
                    "confidence": 0.85,
                    "evidence": evidence
                    + [
                        "reward>=1.0",
                        f"turn_count:{turn_count}",
                        f"error_count:{error_count}",
                    ],
                }
            return {
                "settlement_quality": "recovered_success",
                "confidence": 0.85,
                "evidence": evidence + ["reward>=1.0", f"error_count:{error_count}"],
            }
        return {
            "settlement_quality": "clean_success",
            "confidence": 0.9,
            "evidence": evidence + ["reward>=1.0"],
        }

    if reward_val is not None and reward_val > 0 and reward_val < 1.0:
        return {
            "settlement_quality": "partial_success",
            "confidence": 0.8,
            "evidence": evidence + [f"reward:{reward_val}"],
        }

    if reward_val is not None and reward_val <= 0.0:
        if error_count >= 1:
            return {
                "settlement_quality": "failure_with_signal",
                "confidence": 0.85,
                "evidence": evidence + ["reward<=0.0", f"error_count:{error_count}"],
            }
        return {
            "settlement_quality": "failure_without_signal",
            "confidence": 0.8,
            "evidence": evidence + ["reward<=0.0"],
        }

    result_str = str(trace.get("metadata", {}).get("result", "")).lower()
    if result_str in ("resolved", "success", "pass", "passed", "correct"):
        evidence.append(f"result:{result_str}")
        if error_count == 0:
            return {
                "settlement_quality": "clean_success",
                "confidence": 0.8,
                "evidence": evidence,
            }
        return {
            "settlement_quality": "recovered_success",
            "confidence": 0.75,
            "evidence": evidence + [f"error_count:{error_count}"],
        }

    structural = infer_settlement_from_structure(messages, profile)
    return structural


def detect_failure_modes(
    messages: list[dict[str, Any]],
    profile: dict[str, Any],
    settlement_result: dict[str, Any],
) -> tuple[list[str], list[str]]:
    modes: list[str] = []
    evidence_list: list[str] = []
    settlement_quality = settlement_result.get("settlement_quality", "unknown")

    turn_count = profile.get("turn_count", 0)
    error_count = profile.get("error_like_output_count", 0)
    total_command_count = profile.get("command_like_action_count", 0)
    json_cmd_count = profile.get("json_command_count", 0)
    assistant_count = profile.get("assistant_turn_count", 0)

    task_complete_info = detect_task_complete(messages)

    has_answer = has_final_answer(messages) or (
        task_complete_info["has_marker"] and task_complete_info["value"] is True
    )

    if turn_count < 3 and has_answer and error_count == 0:
        modes.append("premature_closure")
        evidence_list.append(
            f"turn_count:{turn_count}, has_answer:{has_answer}, error_count:0"
        )

    if total_command_count >= 5 and error_count >= 3:
        modes.append("tool_thrashing")
        evidence_list.append(
            f"command_count:{total_command_count}, error_count:{error_count}"
        )

    if error_count >= 2:
        structural_errors = detect_structural_errors(messages)
        assistant_msgs = [
            (i, m) for i, m in enumerate(messages) if m.get("role") == "assistant"
        ]
        for err in structural_errors:
            err_idx = err["turn_index"]
            for j in range(err_idx + 1, min(err_idx + 5, len(messages))):
                if messages[j].get("role") == "assistant":
                    parsed = parse_assistant_content(messages[j].get("content", ""))
                    if not parsed["commands"]:
                        modes.append("failed_recovery")
                        evidence_list.append(
                            f"error_at_turn:{err_idx}, no_command_recovery_at_turn:{j}"
                        )
                        break
            if "failed_recovery" in modes:
                break

    task_content = extract_user_task_content(messages)
    is_broad = len(task_content) > 50 or "?" in task_content
    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    first_has_commands = False
    if assistant_messages:
        parsed = parse_assistant_content(assistant_messages[0].get("content", ""))
        first_has_commands = bool(parsed["commands"])
    if is_broad and first_has_commands and turn_count < 5:
        modes.append("representation_jump")
        evidence_list.append(
            f"broad_task:{is_broad}, first_action_concrete:true, turns:{turn_count}"
        )

    if turn_count > 15 and total_command_count >= 5:
        if settlement_quality in ("failure_with_signal", "failure_without_signal"):
            modes.append("payment_spiral")
            evidence_list.append(
                f"turn_count:{turn_count}, commands:{total_command_count}, quality:{settlement_quality}"
            )

    context_loss_result = _detect_context_loss(messages, profile)
    if context_loss_result["detected"]:
        modes.append("context_loss")
        evidence_list.append(context_loss_result["evidence"])

    if (
        assistant_count > 5
        and total_command_count == 0
        and json_cmd_count == 0
        and not has_answer
    ):
        modes.append("over_abstraction")
        evidence_list.append(
            f"assistant_count:{assistant_count}, total_commands:0, json_commands:0, has_answer:{has_answer}"
        )

    if assistant_messages:
        first_asst = assistant_messages[0].get("content", "")
        parsed = parse_assistant_content(first_asst)
        if parsed["commands"]:
            structural_errors = detect_structural_errors(messages)
            for err in structural_errors:
                if err["turn_index"] < 3 and err["role"] in ("user", "tool"):
                    modes.append("premature_concretion")
                    evidence_list.append(
                        f"first_assistant_has_commands:true, error_at_turn:{err['turn_index']}"
                    )
                    break

    if settlement_quality == "brittle_success":
        modes.append("brittle_success")
        evidence_list.append("settlement_quality:brittle_success")

    return (
        modes if modes else ["unknown"],
        evidence_list if evidence_list else ["no_specific_failure_evidence"],
    )


def _detect_context_loss(
    messages: list[dict[str, Any]], profile: dict[str, Any]
) -> dict[str, Any]:
    turn_count = profile.get("turn_count", 0)
    if turn_count < 4:
        return {"detected": False, "evidence": ""}

    task_content = extract_user_task_content(messages)
    if not task_content or is_system_prompt_boilerplate(task_content):
        return {"detected": False, "evidence": "no_extractable_user_constraints"}

    task_words = set(task_content.lower().split())
    if len(task_words) < 5:
        return {"detected": False, "evidence": "insufficient_task_words_for_comparison"}

    specific_constraints = []
    task_lower = task_content.lower()
    constraint_patterns = [
        "must",
        "should",
        "required",
        "needs to",
        "only use",
        "do not",
        "without",
        "ensure",
        "make sure",
        "has to",
        "specifically",
        "exactly",
        "at least",
        "at most",
    ]
    for pattern in constraint_patterns:
        if pattern in task_lower:
            idx = task_lower.index(pattern)
            snippet = task_content[max(0, idx - 20) : idx + 60]
            specific_constraints.append(snippet)

    if not specific_constraints:
        return {"detected": False, "evidence": "no_explicit_constraints_found"}

    last_assistant = ""
    for m in reversed(messages):
        if m.get("role") == "assistant":
            last_assistant = m.get("content", "").lower()
            break

    if not last_assistant:
        return {"detected": False, "evidence": ""}

    constraint_words = set()
    for constraint in specific_constraints:
        constraint_words.update(constraint.lower().split())

    overlap = constraint_words & set(last_assistant.split())
    if len(overlap) < 2:
        return {
            "detected": True,
            "evidence": f"constraints:{specific_constraints[:2]}, overlap_with_final:{len(overlap)}/{len(constraint_words)}",
        }

    return {"detected": False, "evidence": f"sufficient_overlap:{len(overlap)}"}


def detect_metabolization_candidate(
    profile: dict[str, Any], settlement_result: dict[str, Any]
) -> str | None:
    quality = settlement_result.get("settlement_quality", "unknown")
    confidence = settlement_result.get("confidence", 0.0)
    if confidence < 0.65:
        return None
    if quality in ("clean_success", "recovered_success"):
        turn_count = profile.get("turn_count", 0)
        error_count = profile.get("error_like_output_count", 0)
        if turn_count < 10 and error_count == 0:
            return "repeated_success_pattern"
        if error_count > 0 and quality == "recovered_success":
            return "clean_recovery_pattern"
    return None


def detect_harness_policy_signal(
    failure_modes: list[str], settlement_result: dict[str, Any], profile: dict[str, Any]
) -> str | None:
    if "premature_closure" in failure_modes:
        return "block_premature_final_answer"
    if "tool_thrashing" in failure_modes:
        return "require_reflection_after_repeated_tool_errors"
    if profile.get("error_like_output_count", 0) >= 3:
        return "require_reflection_after_repeated_tool_errors"
    if "payment_spiral" in failure_modes:
        return "payment_spiral_reset"
    if "representation_jump" in failure_modes:
        return "force_intermediate_representation_for_direct_jump"
    return None


def label_trace(
    trace: dict[str, Any], profile: dict[str, Any], rules: dict[str, Any]
) -> dict[str, Any]:
    messages = trace.get("messages", [])

    desired_direction = classify_desired_direction(messages, rules)
    representational_state = classify_path_shape(messages, profile)
    settlement_result = classify_settlement_quality(trace, profile)
    payment_complexity = estimate_payment_complexity(profile, rules)
    failure_modes, failure_evidence = detect_failure_modes(
        messages, profile, settlement_result
    )
    metabolization = detect_metabolization_candidate(profile, settlement_result)
    policy_signal = detect_harness_policy_signal(
        failure_modes, settlement_result, profile
    )

    total_command_count = profile.get("command_like_action_count", 0)
    error_count = profile.get("error_like_output_count", 0)

    recovery_events: list[dict[str, Any]] = []
    structural_errors = detect_structural_errors(messages)
    for err in structural_errors:
        err_idx = err["turn_index"]
        for j in range(err_idx + 1, min(err_idx + 5, len(messages))):
            if messages[j].get("role") == "assistant":
                parsed = parse_assistant_content(messages[j].get("content", ""))
                if parsed["commands"]:
                    recovery_events.append(
                        {
                            "error_turn": err_idx,
                            "recovery_turn": j,
                            "recovered": True,
                        }
                    )
                break

    actions: list[dict[str, Any]] = []
    for i, m in enumerate(messages):
        if m.get("role") == "assistant":
            parsed = parse_assistant_content(m.get("content", ""))
            if parsed["commands"]:
                for cmd in parsed["commands"]:
                    actions.append(
                        {
                            "turn_index": i,
                            "role": "assistant",
                            "action_type": "command",
                            "source": "assistant_json",
                            "content": cmd.get("content", "")[:200],
                        }
                    )
            else:
                actions.append(
                    {
                        "turn_index": i,
                        "role": "assistant",
                        "action_type": "text",
                        "is_command": False,
                    }
                )
        elif m.get("role") == "tool":
            actions.append(
                {
                    "turn_index": i,
                    "role": "tool",
                    "action_type": "tool_output",
                    "is_command": is_command_like(m.get("content", "")),
                }
            )

    label_evidence: dict[str, list[str]] = {
        "failure_mode": failure_evidence,
        "settlement_quality": settlement_result.get("evidence", []),
        "path_shape": [],
        "payment_pattern": [],
    }

    return {
        "trace_id": trace.get("trace_id", ""),
        "source": trace.get("source", ""),
        "teacher_model": trace.get("teacher", ""),
        "task_id": trace.get("task_id", ""),
        "desired_direction": desired_direction,
        "representational_state": representational_state,
        "payment": {
            "turn_count": profile.get("turn_count", 0),
            "tool_call_count": profile.get("tool_turn_count", 0),
            "command_count": total_command_count,
            "json_command_count": profile.get("json_command_count", 0),
            "error_count": error_count,
            "recovery_attempt_count": len(recovery_events),
            "estimated_complexity": payment_complexity,
        },
        "affordance_path": {
            "actions": actions[:20],
            "recovery_events": recovery_events,
        },
        "outcome": {
            "reward": trace.get("reward"),
            "settlement_quality": settlement_result.get(
                "settlement_quality", "unknown"
            ),
            "confidence": settlement_result.get("confidence", 0.0),
        },
        "cognitive_os_labels": {
            "failure_mode": failure_modes[0]
            if len(failure_modes) == 1
            else failure_modes,
            "metabolization_candidate": metabolization,
            "harness_policy_signal": policy_signal,
        },
        "label_evidence": label_evidence,
    }


def label_traces(
    input_path: str | Path,
    profile_path: str | Path = "data/agenttrove/profiles/trace_profile.jsonl",
    rules_path: str = "configs/agenttrove/settlement_label_rules.yaml",
    output_path: str | Path = "data/agenttrove/settlements/settlement_traces.jsonl",
) -> Path:
    input_path = Path(input_path)
    profile_path = Path(profile_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rules = load_rules(rules_path)

    profiles_by_id: dict[str, dict[str, Any]] = {}
    if profile_path.exists():
        with profile_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                prof = json.loads(line)
                profiles_by_id[prof["trace_id"]] = prof

    settlements: list[dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            trace = json.loads(line)
            trace_id = trace.get("trace_id", "")
            profile = profiles_by_id.get(trace_id, {})
            if not profile:
                profile = _derive_profile_from_trace(trace)
            settlement = label_trace(trace, profile, rules)
            settlements.append(settlement)

    with output_path.open("w", encoding="utf-8") as handle:
        for s in settlements:
            handle.write(json.dumps(s, sort_keys=True) + "\n")

    return output_path


def _derive_profile_from_trace(trace: dict[str, Any]) -> dict[str, Any]:
    from scripts.agenttrove.profile_traces import profile_trace

    return profile_trace(trace)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Label AgentTrove traces with Cognitive OS settlement records."
    )
    parser.add_argument(
        "--input", type=str, default="data/agenttrove/raw_samples/sample.jsonl"
    )
    parser.add_argument(
        "--profile", type=str, default="data/agenttrove/profiles/trace_profile.jsonl"
    )
    parser.add_argument(
        "--rules", type=str, default="configs/agenttrove/settlement_label_rules.yaml"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/agenttrove/settlements/settlement_traces.jsonl",
    )
    args = parser.parse_args()

    path = label_traces(args.input, args.profile, args.rules, args.output)
    print(f"Wrote settlement labels to {path}")


if __name__ == "__main__":
    main()
