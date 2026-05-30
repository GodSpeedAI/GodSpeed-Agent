from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.agenttrove.profile_traces import (
    count_command_like_actions,
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
    user_messages = [m for m in messages if m.get("role") == "user"]
    if not user_messages:
        return {"type": "unknown", "description": "", "settlement_target": ""}

    first_user = user_messages[0].get("content", "").lower()
    direction_keywords = rules.get("desired_direction_keywords", {})

    best_type = "unknown"
    best_count = 0
    for direction_type, keywords in direction_keywords.items():
        count = sum(1 for kw in keywords if kw in first_user)
        if count > best_count:
            best_count = count
            best_type = direction_type

    snippet = first_user[:200] if first_user else ""
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
    command_count = profile.get("command_like_action_count", 0)
    assistant_count = profile.get("assistant_turn_count", 0)
    user_count = profile.get("user_turn_count", 0)

    user_messages = [m for m in messages if m.get("role") == "user"]
    first_user_content = user_messages[0].get("content", "") if user_messages else ""
    is_broad_start = len(first_user_content) > 50 or "?" in first_user_content

    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    first_assistant_is_action = bool(assistant_messages) and is_command_like(
        assistant_messages[0].get("content", "")
    )

    if is_broad_start and turn_count < 5 and first_assistant_is_action:
        path_shape = "direct_jump"
        start = "general_abstract"
        desired = "specific_concrete"
    elif error_count >= 3 and command_count >= 3 and turn_count > 10:
        path_shape = "thrash"
        start = "general_abstract"
        desired = "specific_concrete"
    elif is_broad_start and assistant_count > 2 and command_count > 0:
        path_shape = "GA_to_SA_to_SC"
        start = "general_abstract"
        desired = "specific_concrete"
    elif first_assistant_is_action and error_count > 0:
        path_shape = "direct_action_with_feedback"
        start = "specific_concrete"
        desired = "specific_concrete"
    elif assistant_count > 3 and user_count > 1 and turn_count > 10:
        path_shape = "GA_to_GC_to_SC"
        start = "general_abstract"
        desired = "specific_concrete"
    else:
        path_shape = "unknown"
        start = "unknown"
        desired = "unknown"

    return {"start": start, "desired": desired, "path_shape": path_shape}


def estimate_payment_complexity(profile: dict[str, Any], rules: dict[str, Any]) -> str:
    turn_count = profile.get("turn_count", 0)
    command_count = profile.get("command_like_action_count", 0)
    error_count = profile.get("error_like_output_count", 0)

    if turn_count < 5 and command_count < 2 and error_count < 1:
        return "low"
    if turn_count >= 15 or command_count >= 5 or error_count >= 3:
        return "high"
    return "medium"


def classify_settlement_quality(trace: dict[str, Any], profile: dict[str, Any]) -> str:
    reward = trace.get("reward")
    error_count = profile.get("error_like_output_count", 0)
    turn_count = profile.get("turn_count", 0)
    has_answer = has_final_answer(trace.get("messages", []))

    try:
        reward_val = float(reward) if reward is not None else None
    except (TypeError, ValueError):
        reward_val = None

    if reward_val is not None and reward_val >= 1.0:
        if error_count == 0 and has_answer:
            return "clean_success"
        if error_count >= 1 and has_answer:
            if turn_count > 15 and error_count >= 3:
                return "brittle_success"
            return "recovered_success"
        if turn_count > 15 and error_count >= 3:
            return "brittle_success"
        return "clean_success"

    if reward_val is not None and reward_val > 0 and reward_val < 1.0:
        return "partial_success"

    if reward_val is not None and reward_val <= 0.0:
        if error_count >= 1:
            return "failure_with_signal"
        return "failure_without_signal"

    result_str = str(trace.get("metadata", {}).get("result", "")).lower()
    if result_str in ("resolved", "success", "pass", "passed", "correct"):
        if error_count == 0:
            return "clean_success"
        return "recovered_success"

    if has_answer and error_count == 0:
        return "clean_success"
    if error_count >= 1 and not has_answer:
        return "failure_with_signal"
    if not has_answer:
        return "failure_without_signal"

    return "unknown"


def detect_failure_modes(
    messages: list[dict[str, Any]], profile: dict[str, Any], settlement_quality: str
) -> list[str]:
    modes: list[str] = []
    turn_count = profile.get("turn_count", 0)
    error_count = profile.get("error_like_output_count", 0)
    command_count = profile.get("command_like_action_count", 0)
    assistant_count = profile.get("assistant_turn_count", 0)
    has_answer = has_final_answer(messages)

    if turn_count < 3 and has_answer and error_count == 0:
        modes.append("premature_closure")

    if command_count >= 5 and error_count >= 3:
        modes.append("tool_thrashing")

    if error_count >= 2:
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        for i in range(len(tool_msgs)):
            if is_error_like(tool_msgs[i].get("content", "")):
                for j in range(i, min(i + 3, len(assistant_msgs))):
                    if is_command_like(assistant_msgs[j].get("content", "")):
                        same_cmd = _similar_action(
                            assistant_msgs[j].get("content", ""),
                            assistant_msgs[max(0, j - 1)].get("content", "")
                            if j > 0
                            else "",
                        )
                        if same_cmd:
                            modes.append("failed_recovery")
                            break
                if "failed_recovery" in modes:
                    break

    user_messages = [m for m in messages if m.get("role") == "user"]
    if user_messages:
        first_user = user_messages[0].get("content", "")
        is_broad = len(first_user) > 50 or "?" in first_user
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        first_is_concrete = bool(assistant_messages) and is_command_like(
            assistant_messages[0].get("content", "")
        )
        if is_broad and first_is_concrete and turn_count < 5:
            modes.append("representation_jump")

    if turn_count > 15 and command_count >= 5:
        reward = None
        if settlement_quality in ("failure_with_signal", "failure_without_signal"):
            modes.append("payment_spiral")

    if turn_count > 10 and len(user_messages) > 1:
        first_user_text = user_messages[0].get("content", "").lower()
        last_assistant = ""
        for m in reversed(messages):
            if m.get("role") == "assistant":
                last_assistant = m.get("content", "").lower()
                break
        if first_user_text and last_assistant:
            early_words = set(first_user_text.split()[:10])
            late_words = set(last_assistant.split())
            overlap = early_words & late_words
            if len(overlap) < 2 and turn_count > 10:
                modes.append("context_loss")

    if assistant_count > 5 and command_count == 0 and not has_answer:
        modes.append("over_abstraction")

    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    if assistant_messages:
        first_asst = assistant_messages[0].get("content", "")
        if is_command_like(first_asst):
            tool_msgs_after = [m for m in messages if m.get("role") == "tool"]
            if tool_msgs_after and is_error_like(tool_msgs_after[0].get("content", "")):
                modes.append("premature_concretion")

    if settlement_quality == "brittle_success":
        modes.append("brittle_success")

    return modes if modes else ["unknown"]


def detect_metabolization_candidate(
    profile: dict[str, Any], settlement_quality: str
) -> str | None:
    if settlement_quality in ("clean_success", "recovered_success"):
        turn_count = profile.get("turn_count", 0)
        error_count = profile.get("error_like_output_count", 0)
        if turn_count < 10 and error_count == 0:
            return "repeated_success_pattern"
        if error_count > 0 and settlement_quality == "recovered_success":
            return "clean_recovery_pattern"
    return None


def detect_harness_policy_signal(
    failure_modes: list[str], settlement_quality: str, profile: dict[str, Any]
) -> str | None:
    if "premature_closure" in failure_modes:
        return "block_premature_final_answer"
    if (
        "tool_thrashing" in failure_modes
        or profile.get("error_like_output_count", 0) >= 2
    ):
        return "require_reflection_after_repeated_tool_errors"
    if "payment_spiral" in failure_modes:
        return "payment_spiral_reset"
    if "representation_jump" in failure_modes:
        return "force_intermediate_representation_for_direct_jump"
    return None


def _similar_action(content_a: str, content_b: str) -> bool:
    if not content_a or not content_b:
        return False
    words_a = set(content_a.lower().split()[:10])
    words_b = set(content_b.lower().split()[:10])
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
    return overlap > 0.7


def label_trace(
    trace: dict[str, Any], profile: dict[str, Any], rules: dict[str, Any]
) -> dict[str, Any]:
    messages = trace.get("messages", [])

    desired_direction = classify_desired_direction(messages, rules)
    representational_state = classify_path_shape(messages, profile)
    settlement_quality = classify_settlement_quality(trace, profile)
    payment_complexity = estimate_payment_complexity(profile, rules)
    failure_modes = detect_failure_modes(messages, profile, settlement_quality)
    metabolization = detect_metabolization_candidate(profile, settlement_quality)
    policy_signal = detect_harness_policy_signal(
        failure_modes, settlement_quality, profile
    )

    command_count = profile.get("command_like_action_count", 0)
    error_count = profile.get("error_like_output_count", 0)

    recovery_events: list[dict[str, Any]] = []
    tool_msgs = [(i, m) for i, m in enumerate(messages) if m.get("role") == "tool"]
    for idx, tm in tool_msgs:
        if is_error_like(tm.get("content", "")):
            for j in range(idx + 1, min(idx + 4, len(messages))):
                if messages[j].get("role") == "assistant":
                    asst_content = messages[j].get("content", "")
                    has_new_command = is_command_like(asst_content)
                    has_error_keyword_only = (
                        is_error_like(asst_content) and not has_new_command
                    )
                    if has_new_command or not has_error_keyword_only:
                        recovery_events.append(
                            {
                                "error_turn": idx,
                                "recovery_turn": j,
                                "recovered": True,
                            }
                        )
                    break

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
            "command_count": command_count,
            "error_count": error_count,
            "recovery_attempt_count": len(recovery_events),
            "estimated_complexity": payment_complexity,
        },
        "affordance_path": {
            "actions": [
                {
                    "turn_index": i,
                    "role": m.get("role", ""),
                    "is_command": is_command_like(m.get("content", "")),
                }
                for i, m in enumerate(messages)
                if m.get("role") in ("assistant", "tool")
            ],
            "recovery_events": recovery_events,
        },
        "outcome": {
            "reward": trace.get("reward"),
            "settlement_quality": settlement_quality,
        },
        "cognitive_os_labels": {
            "failure_mode": failure_modes[0]
            if len(failure_modes) == 1
            else failure_modes,
            "metabolization_candidate": metabolization,
            "harness_policy_signal": policy_signal,
        },
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
    messages = trace.get("messages", [])
    roles = [m.get("role", "unknown") for m in messages]
    return {
        "trace_id": trace.get("trace_id", ""),
        "turn_count": len(messages),
        "system_turn_count": roles.count("system"),
        "user_turn_count": roles.count("user"),
        "assistant_turn_count": roles.count("assistant"),
        "tool_turn_count": roles.count("tool"),
        "command_like_action_count": count_command_like_actions(messages),
        "error_like_output_count": count_error_like_outputs(messages),
        "first_error_turn": find_first_error_turn(messages),
        "final_turn_role": roles[-1] if roles else "",
        "has_final_answer": has_final_answer(messages),
    }


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
