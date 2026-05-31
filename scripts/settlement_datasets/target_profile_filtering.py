from __future__ import annotations

import re
from collections import Counter
from typing import Any

from scripts.settlement_datasets.evaluate_policies_shadow import (
    _classify_fire_timing,
    _closure_likely_text,
    _contains_strategy_revision,
    _detect_recovery_opportunity,
    _distinct_error_events,
    _is_low_cost_inspection,
    _later_items,
)


def _task_complete_marker(record: dict[str, Any]) -> bool:
    outcome_evidence = [str(item).lower() for item in record.get("outcome", {}).get("evidence", [])]
    return any("task_complete:true" in item for item in outcome_evidence)


def _payment_evidence_count(record: dict[str, Any], prefix: str) -> int | None:
    for item in record.get("payment", {}).get("evidence", []):
        text = str(item)
        if text.startswith(f"{prefix}:"):
            try:
                return int(text.split(":", 1)[1])
            except ValueError:
                return None
    return None


def _labeled_error_turn(record: dict[str, Any]) -> int | None:
    for item in record.get("labels", {}).get("failure_mode_evidence", []):
        match = re.search(r"error_at_turn:(\d+)", str(item))
        if match:
            return int(match.group(1))
    return None


def _action_items(record: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        record.get("affordance_path", {}).get("actions", []),
        key=lambda item: int(item.get("turn_index", 0)),
    )


def _substantive_action_items(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in _action_items(record)
        if item.get("action_type") in {"command", "api_call", "selection", "buy"}
    ]


def _later_actions(record: dict[str, Any], turn_index: int) -> list[dict[str, Any]]:
    return [
        item
        for item in _substantive_action_items(record)
        if int(item.get("turn_index", -1)) > turn_index
    ]


def _command_or_action_trace(record: dict[str, Any]) -> bool:
    return any(
        action.get("action_type") in {"command", "api_call", "selection", "buy", "text"}
        for action in _action_items(record)
    )


def _same_path_continuation_after_second_error(record: dict[str, Any], second_error_turn: int | None) -> bool:
    if second_error_turn is None:
        return False

    later_actions = _later_actions(record, second_error_turn)
    return bool(later_actions)


def _analyze_reflection_record(record: dict[str, Any]) -> dict[str, Any]:
    error_events = _distinct_error_events(record)
    payment_error_count = int(record.get("payment", {}).get("error_count", 0) or 0)
    recovery_attempt_count = _payment_evidence_count(record, "recovery_attempt_count") or 0
    total_error_count = max(len(error_events), payment_error_count)
    labeled_error_turn = _labeled_error_turn(record)

    second_error_turn = int(error_events[1].get("turn_index", 0)) if len(error_events) >= 2 else labeled_error_turn
    latest_error_turn = int(error_events[-1].get("turn_index", 0)) if error_events else labeled_error_turn
    later_items_after_latest_error = _later_items(record, latest_error_turn) if latest_error_turn is not None else []
    later_actions_after_second_error = _later_actions(record, second_error_turn) if second_error_turn is not None else []

    fire_timing = "unknown"
    remaining_turns_after_fire = 0
    recovery_opportunity = False
    recovery_opportunity_evidence = ["no_second_error"]
    if second_error_turn is not None:
        fire_timing, remaining_turns_after_fire = _classify_fire_timing(
            {"second_unresolved_error_before_continuing": True},
            record,
            second_error_turn,
            True,
        )
        recovery_opportunity, recovery_opportunity_evidence = _detect_recovery_opportunity(
            record,
            fire_timing,
            second_error_turn,
            remaining_turns_after_fire,
        )
    elif total_error_count >= 2 and recovery_attempt_count > 0:
        fire_timing = "middle"
        remaining_turns_after_fire = recovery_attempt_count
        recovery_opportunity = True
        recovery_opportunity_evidence = [f"recovery_attempt_count={recovery_attempt_count}"]

    strategy_revision_after_latest_error = any(
        _contains_strategy_revision(str(item.get("content", "")))
        for item in later_items_after_latest_error
    )
    low_cost_inspection_after_error = any(
        _is_low_cost_inspection(str(item.get("content", "")))
        for item in later_items_after_latest_error
    )
    closure_after_error = any(
        item.get("action_type") in {"final_answer", "submit", "task_complete"}
        or _closure_likely_text(str(item.get("content", "")))
        for item in later_items_after_latest_error
    )
    total_error_feedback = sum(
        1
        for item in record.get("affordance_path", {}).get("observations", [])
        if any(token in str(item.get("content", "")).lower() for token in ("error", "traceback", "failed", "failure", "exception", "timeout"))
    )
    duplicate_error_only = total_error_feedback >= 2 and len(error_events) < 2
    same_path_continuation = _same_path_continuation_after_second_error(record, second_error_turn) or (
        total_error_count >= 2 and recovery_attempt_count > 0
    )
    recovery_actions_after_error = bool(later_actions_after_second_error) or recovery_attempt_count > 0
    no_action_after_error = total_error_count >= 2 and not same_path_continuation

    return {
        "trace_id": record.get("task_id") or record.get("metadata", {}).get("trace_id") or "unknown-trace",
        "confidence": float(record.get("outcome", {}).get("confidence", 0.0) or 0.0),
        "has_tool_or_environment_error": total_error_count > 0,
        "command_or_action_trace": _command_or_action_trace(record),
        "multiple_error_events": total_error_count >= 2,
        "two_or_more_unresolved_errors": total_error_count >= 2,
        "second_error_turn": second_error_turn,
        "latest_error_turn": latest_error_turn,
        "same_path_continuation_after_second_error": same_path_continuation,
        "no_strategy_revision_after_latest_error": not strategy_revision_after_latest_error,
        "recovery_actions_after_error": recovery_actions_after_error,
        "recovery_opportunity_remaining": recovery_opportunity,
        "recovery_opportunity_evidence": recovery_opportunity_evidence,
        "task_complete_marker": _task_complete_marker(record),
        "final_turn_only_error": fire_timing == "final_turn",
        "duplicate_error_only": duplicate_error_only,
        "no_action_after_error": no_action_after_error,
        "low_cost_inspection_after_error": low_cost_inspection_after_error,
        "closure_after_error": closure_after_error,
        "fire_timing": fire_timing,
        "remaining_turns_after_fire": remaining_turns_after_fire,
    }


def _reflection_match(
    record: dict[str, Any],
    analysis: dict[str, Any],
    *,
    min_confidence: float,
) -> tuple[bool, list[str]]:
    exclude_reasons: list[str] = []

    if analysis["confidence"] < min_confidence:
        exclude_reasons.append("below_min_confidence")
    if not analysis["has_tool_or_environment_error"]:
        exclude_reasons.append("no_tool_or_environment_error")
    if not analysis["command_or_action_trace"]:
        exclude_reasons.append("no_command_or_action_trace")
    if not analysis["two_or_more_unresolved_errors"]:
        exclude_reasons.append("fewer_than_two_unresolved_errors")
    if analysis["duplicate_error_only"]:
        exclude_reasons.append("duplicate_error_only")
    if analysis["final_turn_only_error"]:
        exclude_reasons.append("final_turn_only_error")
    if analysis["no_action_after_error"]:
        exclude_reasons.append("no_action_after_error")
    if not analysis["same_path_continuation_after_second_error"]:
        exclude_reasons.append("no_same_path_continuation_after_second_error")
    if not analysis["no_strategy_revision_after_latest_error"]:
        exclude_reasons.append("strategy_revision_after_latest_error")
    if analysis["low_cost_inspection_after_error"]:
        exclude_reasons.append("low_cost_inspection_after_error")
    if analysis["closure_after_error"] and not analysis["recovery_opportunity_remaining"]:
        exclude_reasons.append("closure_after_error")
    if not analysis["recovery_opportunity_remaining"]:
        exclude_reasons.append("recovery_window_not_open")

    return (len(exclude_reasons) == 0, exclude_reasons)


def apply_target_profile(
    records: list[dict[str, Any]],
    *,
    profile_name: str,
    profile: dict[str, Any],
    min_confidence: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if profile_name != "reflection_second_unresolved_error":
        raise ValueError(f"Operational target filtering is not implemented for profile: {profile_name}")

    matched: list[dict[str, Any]] = []
    analyses: list[dict[str, Any]] = []
    exclude_reason_counts: Counter[str] = Counter()
    rejected_examples: list[dict[str, Any]] = []
    qualifying_examples: list[dict[str, Any]] = []

    for record in records:
        analysis = _analyze_reflection_record(record)
        matched_record, exclude_reasons = _reflection_match(
            record,
            analysis,
            min_confidence=min_confidence,
        )
        analysis["matched"] = matched_record
        analysis["exclude_reasons"] = exclude_reasons
        analyses.append(analysis)

        if matched_record:
            matched.append(record)
            if len(qualifying_examples) < 5:
                qualifying_examples.append(
                    {
                        "trace_id": analysis["trace_id"],
                        "fire_timing": analysis["fire_timing"],
                        "remaining_turns_after_fire": analysis["remaining_turns_after_fire"],
                        "recovery_opportunity_evidence": analysis["recovery_opportunity_evidence"],
                    }
                )
        else:
            for reason in exclude_reasons:
                exclude_reason_counts[reason] += 1
            if len(rejected_examples) < 5:
                rejected_examples.append(
                    {
                        "trace_id": analysis["trace_id"],
                        "exclude_reasons": exclude_reasons,
                        "fire_timing": analysis["fire_timing"],
                    }
                )

    signal_counts = {
        "command_or_action_trace": sum(1 for analysis in analyses if analysis["command_or_action_trace"]),
        "two_or_more_unresolved_errors": sum(1 for analysis in analyses if analysis["two_or_more_unresolved_errors"]),
        "same_path_continuation_after_second_error": sum(1 for analysis in analyses if analysis["same_path_continuation_after_second_error"]),
        "no_strategy_revision_after_latest_error": sum(1 for analysis in analyses if analysis["no_strategy_revision_after_latest_error"]),
        "recovery_opportunity_remaining": sum(1 for analysis in analyses if analysis["recovery_opportunity_remaining"]),
        "recovery_actions_after_error": sum(1 for analysis in analyses if analysis["recovery_actions_after_error"]),
        "task_complete_marker": sum(1 for analysis in analyses if analysis["task_complete_marker"]),
    }

    diagnostics = {
        "profile_name": profile_name,
        "profile_description": profile.get("description"),
        "profile_query": profile.get("query"),
        "targeting_mode": "operational_filtering_on_normalized_records",
        "sampled_count": len(records),
        "matched_count": len(matched),
        "high_confidence_count": sum(1 for analysis in analyses if analysis["confidence"] >= min_confidence),
        "signal_counts": signal_counts,
        "exclude_reason_counts": dict(exclude_reason_counts),
        "qualifying_examples": qualifying_examples,
        "rejected_examples": rejected_examples,
        "analysis_by_trace": analyses,
        "notes": [
            "This profile is operational only for reflection_second_unresolved_error.",
            "Matching requires the early reflection path to remain spendable: distinct second error, same-path continuation, no strategy revision after the latest error, and recovery opportunity still open.",
            "When explicit copied terminal-output observations are absent, the filter falls back to normalized payment evidence such as error_count and recovery_attempt_count.",
            "Raw sampling remains unfiltered; the targeted slice is applied to normalized records before labeling and shadow evaluation.",
        ],
    }
    return matched, diagnostics
