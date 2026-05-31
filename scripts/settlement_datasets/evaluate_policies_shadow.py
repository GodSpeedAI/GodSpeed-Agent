from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

import yaml

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)
from scripts.settlement_datasets.registry import available_datasets
from scripts.settlement_datasets.run_scoped_paths import (
    add_run_scope_arguments,
    ensure_run_surface,
)


def _is_error_text(content: str) -> bool:
    lowered = content.lower()
    return any(
        token in lowered
        for token in (
            "error",
            "traceback",
            "exception",
            "failed",
            "failure",
            "permission denied",
            "timeout",
        )
    )


def _is_test_failure_text(content: str) -> bool:
    lowered = content.lower()
    return any(
        token in lowered
        for token in (
            "tests failed",
            "test failed",
            "pytest output",
            "assertionerror",
            "failing test",
            "tests/test_",
            "test_",
        )
    ) and ("failed" in lowered or "assertionerror" in lowered)


def _contains_strategy_revision(content: str) -> bool:
    lowered = content.lower()
    return any(
        token in lowered
        for token in (
            "revised plan",
            "new plan",
            "change strategy",
            "different approach",
            "reflect",
            "reflection",
            "diagnose",
            "inspect",
        )
    )


def _is_low_cost_inspection(content: str) -> bool:
    lowered = content.lower()
    return any(
        token in lowered
        for token in (
            "cat ",
            "ls",
            "pwd",
            "rg ",
            "grep ",
            "find ",
            "head ",
            "tail ",
            "sed -n",
        )
    )


def _closure_likely_text(content: str) -> bool:
    lowered = content.lower()
    return any(
        token in lowered
        for token in (
            "final answer",
            "cannot complete",
            "unable to complete",
            "i failed",
            "task failed",
            "closing",
        )
    )


def _is_feedback_item(item: dict[str, Any]) -> bool:
    role = str(item.get("role", "")).lower()
    action_type = item.get("action_type")
    return role in {"tool", "user"} or action_type in {None, "observation"}


def _sorted_trace_items(record: dict[str, Any]) -> list[dict[str, Any]]:
    items = record.get("affordance_path", {}).get("actions", []) + record.get(
        "affordance_path", {}
    ).get("observations", [])
    return sorted(items, key=lambda item: int(item.get("turn_index", 0)))


def _normalize_error_signature(content: str) -> str:
    return " ".join(content.lower().split())


def _distinct_error_events(record: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()
    for item in _sorted_trace_items(record):
        if not _is_feedback_item(item):
            continue
        content = str(item.get("content", ""))
        if not _is_error_text(content):
            continue
        signature = _normalize_error_signature(content)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        events.append(item)
    return events


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


def _total_error_count(record: dict[str, Any]) -> int:
    return max(
        len(_distinct_error_events(record)),
        int(record.get("payment", {}).get("error_count", 0) or 0),
    )


def _second_unresolved_error_turn(record: dict[str, Any]) -> int | None:
    error_events = _distinct_error_events(record)
    if len(error_events) >= 2:
        return int(error_events[1].get("turn_index", 0))
    if _total_error_count(record) >= 2:
        return _labeled_error_turn(record)
    return None


def _latest_error_turn(record: dict[str, Any]) -> int | None:
    error_events = _distinct_error_events(record)
    if error_events:
        return int(error_events[-1].get("turn_index", 0))
    if _total_error_count(record) > 0:
        return _labeled_error_turn(record)
    return None


def _continued_after_second_error(record: dict[str, Any], second_error_turn: int | None) -> bool:
    if second_error_turn is not None and _later_items(record, second_error_turn):
        return True
    return _total_error_count(record) >= 2 and (_payment_evidence_count(record, "recovery_attempt_count") or 0) > 0


def _later_items(record: dict[str, Any], turn_index: int) -> list[dict[str, Any]]:
    return [
        item
        for item in _sorted_trace_items(record)
        if int(item.get("turn_index", -1)) > turn_index
    ]


def _first_test_failure_turn(record: dict[str, Any]) -> int | None:
    for item in _sorted_trace_items(record):
        if not _is_feedback_item(item):
            continue
        if _is_test_failure_text(str(item.get("content", ""))):
            return int(item.get("turn_index", 0))
    return None


def _test_failure_turns(record: dict[str, Any]) -> list[int]:
    turns: list[int] = []
    for item in _sorted_trace_items(record):
        if not _is_feedback_item(item):
            continue
        if _is_test_failure_text(str(item.get("content", ""))):
            turns.append(int(item.get("turn_index", 0)))
    return turns


def _has_test_pass_after(record: dict[str, Any], turn_index: int) -> bool:
    for item in _later_items(record, turn_index):
        if not _is_feedback_item(item):
            continue
        lowered = str(item.get("content", "")).lower()
        if ("passed" in lowered or "tests pass" in lowered) and not _is_test_failure_text(
            lowered
        ):
            return True
    return False


def _test_failure_trigger(record: dict[str, Any]) -> tuple[int | None, str | None]:
    failure_turns = _test_failure_turns(record)
    if not failure_turns:
        return None, None

    if len(failure_turns) >= 2 and not _has_test_pass_after(record, failure_turns[1]):
        return failure_turns[1], "repeated_test_failure"

    closure_turn = _first_closure_turn_after(record, failure_turns[0])
    if closure_turn is not None:
        return closure_turn, "closure"

    return None, None


def _first_closure_turn_after(record: dict[str, Any], turn_index: int) -> int | None:
    for item in _later_items(record, turn_index):
        content = str(item.get("content", ""))
        if item.get("action_type") in {"final_answer", "submit"}:
            return int(item.get("turn_index", 0))
        if _closure_likely_text(content):
            return int(item.get("turn_index", 0))
    return None


def _contains_explicit_failure_evidence(content: str) -> bool:
    lowered = content.lower()
    return any(
        token in lowered
        for token in (
            "stack trace",
            "traceback",
            "assertionerror",
            "failing test",
            "pytest output",
            "error message",
            "observed failing",
        )
    )


def _failure_evidence_already_present(record: dict[str, Any]) -> bool:
    failure_turn = _first_test_failure_turn(record)
    if failure_turn is None:
        return False

    trigger_turn, _ = _test_failure_trigger(record)
    if trigger_turn is None:
        return False

    for item in _sorted_trace_items(record):
        turn = int(item.get("turn_index", -1))
        if failure_turn < turn < trigger_turn and _contains_explicit_failure_evidence(
            str(item.get("content", ""))
        ):
            return True
    return False


def _total_turns(record: dict[str, Any]) -> int:
    payment = record.get("payment", {})
    turns = int(payment.get("turns", 0) or payment.get("elapsed_steps", 0) or 0)
    if turns > 0:
        return turns

    indexes = [
        int(item.get("turn_index", -1))
        for item in record.get("affordance_path", {}).get("actions", [])
        + record.get("affordance_path", {}).get("observations", [])
        if item.get("turn_index") is not None
    ]
    return (max(indexes) + 1) if indexes else 0


def _estimate_fire_turn_index(
    trigger: dict[str, Any],
    record: dict[str, Any],
    fired: bool,
) -> int | None:
    if not fired:
        return None

    if "settlement_quality" in trigger:
        turns = _total_turns(record)
        return max(turns - 1, 0) if turns else 0

    actions = record.get("affordance_path", {}).get("actions", [])
    observations = record.get("affordance_path", {}).get("observations", [])

    if "early_specific_action" in trigger:
        early_actions = [
            a.get("turn_index")
            for a in actions
            if a.get("action_type") in ("command", "api_call", "buy")
            and a.get("turn_index", 99) < trigger.get("turn_index_lt", 3)
        ]
        if early_actions:
            return min(int(index) for index in early_actions if index is not None)

    if "action_type" in trigger and trigger["action_type"] == "edit_or_api_call":
        edit_indexes = [
            a.get("turn_index")
            for a in actions
            if a.get("action_type") in ("command", "api_call")
        ]
        if edit_indexes:
            return min(int(index) for index in edit_indexes if index is not None)

    if "api_call" in trigger:
        api_indexes = [
            a.get("turn_index")
            for a in actions
            if a.get("action_type") == "api_call"
        ]
        if api_indexes:
            return min(int(index) for index in api_indexes if index is not None)

    if "selection_action" in trigger:
        selection_indexes = [
            a.get("turn_index")
            for a in actions
            if a.get("action_type") in ("buy", "selection")
        ]
        if selection_indexes:
            return min(int(index) for index in selection_indexes if index is not None)

    if "final_answer_action" in trigger or "final_answer_attempted" in trigger:
        final_indexes = [
            a.get("turn_index")
            for a in actions
            if a.get("action_type") in ("buy", "submit", "final_answer")
        ]
        if final_indexes:
            return max(int(index) for index in final_indexes if index is not None)

    if "second_unresolved_error_before_continuing" in trigger:
        second_error_turn = _second_unresolved_error_turn(record)
        if second_error_turn is not None:
            return second_error_turn

    if "closure_without_failure_evidence_after_test_failure" in trigger:
        trigger_turn, _ = _test_failure_trigger(record)
        if trigger_turn is not None:
            return trigger_turn

    if "error_count_gte" in trigger:
        error_indexes = [
            int(item.get("turn_index", -1))
            for item in observations + actions
            if _is_error_text(str(item.get("content", "")))
            and item.get("turn_index") is not None
        ]
        threshold = int(trigger["error_count_gte"])
        if len(error_indexes) >= threshold:
            ordered = sorted(error_indexes)
            return ordered[threshold - 1]
        if error_indexes:
            return max(error_indexes)

    if "step_count_gte" in trigger:
        turns = _total_turns(record)
        threshold = int(trigger["step_count_gte"])
        if turns:
            return min(max(threshold - 1, 0), turns - 1)

    turns = _total_turns(record)
    return max(turns - 1, 0) if turns else None


def _classify_fire_timing(
    trigger: dict[str, Any],
    record: dict[str, Any],
    fire_turn_index: int | None,
    fired: bool,
) -> tuple[str, int]:
    if not fired or fire_turn_index is None:
        return "unknown", 0

    turns = max(_total_turns(record), fire_turn_index + 1)
    remaining_turns = max(turns - fire_turn_index - 1, 0)

    if "settlement_quality" in trigger:
        return "after_failure_already_settled", remaining_turns

    if remaining_turns == 0:
        return "final_turn", 0

    last_index = max(turns - 1, 1)
    progress_ratio = fire_turn_index / last_index
    if progress_ratio < 0.25:
        return "early", remaining_turns
    if progress_ratio <= 0.5:
        return "middle", remaining_turns
    return "late", remaining_turns


def _detect_recovery_opportunity(
    record: dict[str, Any],
    fire_timing: str,
    fire_turn_index: int | None,
    remaining_turns_after_fire: int,
) -> tuple[bool, list[str]]:
    if fire_turn_index is None:
        return False, ["unknown_fire_turn"]

    if fire_timing == "after_failure_already_settled":
        return False, ["failure_already_settled"]
    if fire_timing == "final_turn":
        return False, ["trigger_on_final_turn"]

    labels = record.get("labels", {})
    if labels.get("metabolization_candidate"):
        return False, ["task_already_complete"]

    later_actions = [
        a
        for a in record.get("affordance_path", {}).get("actions", [])
        if int(a.get("turn_index", -1)) > fire_turn_index
    ]
    later_observations = [
        o
        for o in record.get("affordance_path", {}).get("observations", [])
        if int(o.get("turn_index", -1)) > fire_turn_index
    ]
    later_recovery = [
        r
        for r in record.get("affordance_path", {}).get("recovery_events", [])
        if int(r.get("turn_index", fire_turn_index + 1)) > fire_turn_index
    ]

    evidence: list[str] = []
    if later_actions:
        evidence.append(f"later_actions={len(later_actions)}")
    if later_observations:
        evidence.append(f"later_observations={len(later_observations)}")
    if later_recovery:
        evidence.append(f"later_recovery_events={len(later_recovery)}")
    if remaining_turns_after_fire > 0:
        evidence.append(f"remaining_turns={remaining_turns_after_fire}")

    if later_actions or later_observations or later_recovery:
        return True, evidence
    if remaining_turns_after_fire > 0:
        return True, evidence or [f"remaining_turns={remaining_turns_after_fire}"]
    return False, ["no_post_trigger_steps"]


def _classify_uncertainty(
    policy: dict[str, Any],
    record: dict[str, Any],
    trigger_evidence: list[str],
    fire_timing: str,
    recovery_opportunity: bool,
    remaining_turns_after_fire: int,
) -> tuple[str, list[str]]:
    outcome = record.get("outcome", {})
    labels = record.get("labels", {})
    payment = record.get("payment", {})
    sq = outcome.get("settlement_quality", "unknown")
    fm = labels.get("failure_mode")
    conf = float(outcome.get("confidence", 0.0) or 0.0)
    policy_fms = policy.get("evidence", {}).get("observed_failure_patterns", [])
    action = policy.get("action", {})
    require_operator = str(action.get("require_operator", "")).lower()

    if fire_timing == "after_failure_already_settled":
        return "policy_would_fire_too_late", ["trigger_depends_on_settled_failure_label"]

    if not recovery_opportunity and fire_timing == "final_turn":
        return "no_recovery_opportunity", ["no_turns_remain_after_fire"]

    if sq == "unknown" or conf < 0.5:
        return "missing_outcome_signal", [f"settlement_quality={sq}", f"confidence={conf}"]

    if sq == "partial_success":
        return "conflicting_settlement_evidence", [f"settlement_quality={sq}", f"failure_mode={fm}"]

    if fm and fm not in policy_fms:
        return "ambiguous_failure_mode", [f"failure_mode={fm}", f"policy_targets={policy_fms}"]

    if len(trigger_evidence) <= 1 and payment.get("error_count", 0) <= 1:
        return "weak_trigger_evidence", trigger_evidence or ["minimal_trigger_evidence"]

    if _total_turns(record) <= 2:
        return "insufficient_trace_context", [f"turns={_total_turns(record)}"]

    if require_operator in ("reflection", "failure_analysis") and recovery_opportunity:
        return "policy_action_effect_not_observable_offline", [
            f"require_operator={require_operator}",
            f"remaining_turns={remaining_turns_after_fire}",
        ]

    if not recovery_opportunity:
        return "no_recovery_opportunity", ["no_post_trigger_steps"]

    return "unknown", [f"settlement_quality={sq}", f"failure_mode={fm}"]


def _check_trigger(
    trigger: dict[str, Any],
    record: dict[str, Any],
    negative_conditions: list[str] | None = None,
) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    payment = record.get("payment", {})
    labels = record.get("labels", {})
    outcome = record.get("outcome", {})
    actions = record.get("affordance_path", {}).get("actions", [])
    domain = record.get("domain", "")

    if "second_unresolved_error_before_continuing" in trigger:
        total_error_count = _total_error_count(record)
        if total_error_count < 2:
            return False, []

        second_error_turn = _second_unresolved_error_turn(record)
        if not _continued_after_second_error(record, second_error_turn):
            return False, []

        evidence.extend(
            [
                f"distinct_unresolved_error_count={total_error_count}",
                f"second_error_turn={second_error_turn if second_error_turn is not None else 'inferred'}",
                "continued_after_second_error",
            ]
        )

    if "closure_without_failure_evidence_after_test_failure" in trigger:
        failure_turn = _first_test_failure_turn(record)
        if failure_turn is None:
            return False, []

        trigger_turn, trigger_kind = _test_failure_trigger(record)
        if trigger_turn is None:
            return False, []

        evidence.extend(["test_failure_signal_detected", f"test_failure_turn={failure_turn}"])
        if trigger_kind == "repeated_test_failure":
            evidence.extend(
                [
                    "repeated_test_failure_signal_detected",
                    f"repeated_failure_turn={trigger_turn}",
                ]
            )
        else:
            evidence.extend(
                [
                    "closure_attempt_detected",
                    f"closure_turn={trigger_turn}",
                ]
            )

    if "error_count_gte" in trigger:
        threshold = trigger["error_count_gte"]
        actual = payment.get("error_count", 0)
        if actual >= threshold:
            evidence.append(f"error_count={actual}>={threshold}")
        else:
            return False, []

    if "action_type" in trigger:
        at = trigger["action_type"]
        if at == "edit_or_api_call":
            has_edit = any(
                a.get("action_type") in ("command", "api_call") for a in actions
            )
            has_prior_search = any(
                a.get("action_type") in ("analysis", "search")
                for i, a in enumerate(actions)
                if any(
                    a2.get("action_type") in ("command", "api_call")
                    for a2 in actions[i + 1 :]
                )
            )
            if (
                has_edit
                and trigger.get("prior_search") is False
                and not has_prior_search
            ):
                evidence.append(f"has_{at}_without_prior_search")
            elif has_edit:
                return False, []
            else:
                return False, []

    if "selection_action" in trigger:
        has_selection = any(
            a.get("action_type") in ("buy", "selection") for a in actions
        )
        if not has_selection:
            return False, []
        if trigger.get("prior_comparison") is False:
            has_prior_compare = any(
                a.get("action_type") == "analysis"
                for a in actions[: max(1, len(actions) - 1)]
            )
            if not has_prior_compare:
                evidence.append("selection_without_prior_comparison")
            else:
                return False, []
        else:
            evidence.append("selection_action_present")

    if "api_call" in trigger:
        has_api = any(a.get("action_type") == "api_call" for a in actions)
        if has_api and trigger.get("prior_schema_check") is False:
            has_prior_analysis = any(
                a.get("action_type") == "analysis"
                for a in actions[: max(1, len(actions) - 1)]
            )
            if not has_prior_analysis:
                evidence.append("api_call_without_prior_analysis")
            else:
                return False, []
        else:
            return False, []

    if "step_count_gte" in trigger:
        threshold = trigger["step_count_gte"]
        actual = payment.get("elapsed_steps", payment.get("turns", 0))
        if actual >= threshold:
            evidence.append(f"steps={actual}>={threshold}")
            if trigger.get("no_progress"):
                sq = outcome.get("settlement_quality", "")
                if sq in ("failure_with_signal", "failure_without_signal", "unknown"):
                    evidence.append("no_progress_indicated")
                else:
                    return False, []
        else:
            return False, []

    if "final_answer_action" in trigger:
        has_final = any(
            a.get("action_type") in ("buy", "submit", "final_answer")
            for a in actions[-2:]
        )
        if not has_final:
            has_final = outcome.get("settlement_quality") in (
                "clean_success",
                "brittle_success",
                "recovered_success",
            )
        if has_final and trigger.get("prior_verification") is False:
            has_verify = any(
                "test" in str(a.get("content", "")).lower()
                or a.get("action_type") == "verification"
                for a in actions[: max(1, len(actions) - 1)]
            )
            if not has_verify:
                evidence.append("final_answer_without_prior_verification")
            else:
                return False, []
        else:
            return False, []

    if "settlement_quality" in trigger:
        target_sq = trigger["settlement_quality"]
        actual_sq = outcome.get("settlement_quality", "")
        if actual_sq == target_sq:
            evidence.append(f"settlement_quality={actual_sq}")
        else:
            return False, []

    if "early_specific_action" in trigger:
        has_early = any(
            a.get("action_type") in ("command", "api_call", "buy")
            and a.get("turn_index", 99) < trigger.get("turn_index_lt", 3)
            for a in actions
        )
        if has_early:
            evidence.append("early_specific_action_before_analysis")
        else:
            return False, []

    if "domain_is_code" in trigger:
        if domain != "code":
            return False, []
        evidence.append("domain_is_code")

    if "action_history_includes_edit" in trigger:
        has_edit = any(
            a.get("action_type") in ("command", "api_call")
            and any(
                kw in str(a.get("content", "")).lower()
                for kw in (
                    "edit",
                    "patch",
                    "sed",
                    "cat >",
                    "python -c",
                    "bash -c",
                    "implement",
                    "fix",
                    "write",
                )
            )
            for a in actions
        )
        if has_edit:
            evidence.append("action_history_includes_code_edit")
        else:
            return False, []

    if "final_answer_attempted" in trigger:
        has_final = any(
            a.get("action_type") in ("buy", "submit", "final_answer")
            for a in actions[-3:]
        )
        if not has_final:
            sq = outcome.get("settlement_quality", "")
            if sq in (
                "clean_success",
                "brittle_success",
                "recovered_success",
                "partial_success",
            ):
                has_final = True
        if has_final:
            evidence.append("final_answer_attempted")
        else:
            return False, []

    if "no_settlement_evidence" in trigger:
        has_test_output = any(
            "pass" in str(a.get("content", "")).lower()
            or "passed" in str(a.get("content", "")).lower()
            for a in actions
            if a.get("role") == "tool" or a.get("action_type") == "observation"
        )
        has_task_complete = labels.get("metabolization_candidate") is not None
        has_success_signal = (
            outcome.get("confidence", 0) >= 0.8
            and outcome.get("settlement_quality") == "clean_success"
        )
        if has_test_output or has_task_complete or has_success_signal:
            return False, []
        evidence.append("no_settlement_evidence_before_final_answer")

    if "errors_are_unresolved" in trigger:
        error_count = payment.get("error_count", 0)
        recovery_events = record.get("affordance_path", {}).get("recovery_events", [])
        recovered = sum(1 for r in recovery_events if r.get("recovered"))
        if recovered >= error_count:
            return False, []
        evidence.append(f"errors_unresolved={error_count - recovered}_of_{error_count}")

    if "has_failure_condition_evidence" in trigger:
        has_errors = payment.get("error_count", 0) > 0
        has_failure_sq = outcome.get("settlement_quality") in (
            "failure_with_signal",
            "failure_without_signal",
        )
        if not (has_errors or has_failure_sq):
            return False, []
        evidence.append("failure_condition_evidence_present")

    if "constraints_missing_or_ambiguous" in trigger:
        dd = record.get("desired_direction", {})
        desc = str(dd.get("description", "")).lower()
        has_constraints = any(
            kw in desc
            for kw in (
                "must",
                "should",
                "only",
                "required",
                "at least",
                "under",
                "do not",
                "ensure",
            )
        )
        if has_constraints:
            return False, []
        evidence.append("no_explicit_constraints_in_task")

    if "high_payment_or_irreversible_action" in trigger:
        high_cost_actions = [
            a
            for a in actions
            if a.get("action_type") in ("command", "api_call", "buy")
            and any(
                kw in str(a.get("content", "")).lower()
                for kw in (
                    "rm ",
                    "delete",
                    "commit",
                    "submit",
                    "buy",
                    "push",
                    "deploy",
                    "drop",
                    "install",
                )
            )
        ]
        if not high_cost_actions:
            return False, []
        evidence.append(f"high_cost_action_count={len(high_cost_actions)}")

    if "no_intermediate_representation" in trigger:
        has_analysis = any(
            a.get("action_type") == "analysis"
            for a in actions[: max(1, len(actions) - 1)]
        )
        if has_analysis:
            return False, []
        evidence.append("no_intermediate_representation_before_action")

    if "no_user_feedback_resolved_ambiguity" in trigger:
        observations = record.get("affordance_path", {}).get("observations", [])
        if len(observations) >= 2:
            return False, []
        evidence.append("insufficient_feedback_to_resolve_ambiguity")

    if "multiple_viable_options_present" in trigger:
        observations = record.get("affordance_path", {}).get("observations", [])
        has_multi_option_obs = any(
            "result" in str(o.get("content", "")).lower()
            or "found" in str(o.get("content", "")).lower()
            or "." in str(o.get("content", ""))[:50]
            for o in observations
        )
        if not has_multi_option_obs:
            return False, []
        evidence.append("multiple_options_observed")

    if "explicit_constraints_exist" in trigger:
        dd = record.get("desired_direction", {})
        desc = str(dd.get("description", ""))
        has_constraints = any(
            kw in desc.lower() for kw in ("must", "only", "at least", "under", "do not")
        )
        if not has_constraints:
            return False, []
        evidence.append("explicit_constraints_in_instruction")

    if "no_constraint_match_evidence" in trigger:
        last_action_content = ""
        for a in reversed(actions):
            if a.get("action_type") == "buy":
                last_action_content = str(a.get("content", "")).lower()
                break
        obs_contents = " ".join(
            str(o.get("content", "")).lower()
            for o in record.get("affordance_path", {}).get("observations", [])
        )
        if (
            "match" in last_action_content
            or "satisfies" in last_action_content
            or "meets" in last_action_content
            or "all constraints met" in last_action_content
            or "matches all constraints" in last_action_content
        ):
            return False, []
        if (
            "matches" in obs_contents
            or "correct" in obs_contents
            or "all constraints met" in obs_contents
            or "matches all constraints" in obs_contents
        ):
            return False, []
        evidence.append("no_constraint_match_evidence_for_selection")

    if not evidence:
        return False, []

    if negative_conditions:
        blocked = _check_negative_conditions(negative_conditions, record)
        if blocked:
            return False, [f"blocked_by_negative_condition:{blocked}"]

    return True, evidence


def _check_negative_conditions(
    conditions: list[str],
    record: dict[str, Any],
) -> str | None:
    payment = record.get("payment", {})
    outcome = record.get("outcome", {})
    actions = record.get("affordance_path", {}).get("actions", [])
    labels = record.get("labels", {})
    domain = record.get("domain", "")
    dd = record.get("desired_direction", {})
    desc = str(dd.get("description", "")).lower()
    observations = record.get("affordance_path", {}).get("observations", [])

    for cond in conditions:
        if cond == "duplicate_error_signals_only":
            error_events = [
                item
                for item in _sorted_trace_items(record)
                if _is_error_text(str(item.get("content", "")))
            ]
            distinct_errors = _distinct_error_events(record)
            if error_events and len(distinct_errors) < 2 <= len(error_events):
                return cond
        if cond == "strategy_revision_after_latest_error":
            latest_turn = _latest_error_turn(record)
            if latest_turn is not None:
                if any(
                    _contains_strategy_revision(str(item.get("content", "")))
                    for item in _later_items(record, latest_turn)
                ):
                    return cond
        if cond == "low_cost_inspection_after_latest_error":
            latest_turn = _latest_error_turn(record)
            if latest_turn is not None:
                if any(
                    _is_low_cost_inspection(str(item.get("content", "")))
                    for item in _later_items(record, latest_turn)
                ):
                    return cond
        if cond == "closure_or_settlement_after_latest_error":
            latest_turn = _latest_error_turn(record)
            if latest_turn is not None:
                later_items = _later_items(record, latest_turn)
                if not later_items:
                    return cond
                if any(
                    item.get("action_type") in {"final_answer", "submit", "task_complete"}
                    or _closure_likely_text(str(item.get("content", "")))
                    for item in later_items
                ):
                    return cond
        if cond == "domain_is_not_code" and domain != "code":
            return cond
        if cond == "failure_evidence_already_present":
            if _failure_evidence_already_present(record):
                return cond
        if cond == "task_already_settled":
            if labels.get("metabolization_candidate") or outcome.get(
                "settlement_quality"
            ) in {"clean_success", "brittle_success", "recovered_success"}:
                return cond
        if cond == "no_code_edit_in_action_history":
            has_edit = any(
                a.get("action_type") in ("command", "api_call")
                and any(
                    kw in str(a.get("content", "")).lower()
                    for kw in ("edit", "patch", "sed", "fix", "implement")
                )
                for a in actions
            )
            if not has_edit:
                return cond
        if cond == "test_output_already_present":
            has_test = any(
                "pass" in str(a.get("content", "")).lower()
                for a in actions
                if a.get("role") == "tool" or a.get("action_type") == "observation"
            )
            if has_test:
                return cond
        if cond == "task_complete_marker_is_true":
            mc = labels.get("metabolization_candidate")
            if mc:
                return cond
        if cond == "explicit_evaluator_success_exists":
            if (
                outcome.get("confidence", 0) >= 0.8
                and outcome.get("settlement_quality") == "clean_success"
            ):
                return cond
        if cond == "successful_command_output_relevant_to_task":
            for a in reversed(actions):
                if (
                    a.get("action_type") == "observation"
                    and "success" in str(a.get("content", "")).lower()
                ):
                    return cond
        if cond == "only_one_viable_option_exists":
            if len(observations) <= 1:
                return cond
        if cond == "no_explicit_constraints_in_instruction":
            has_constraints = any(
                kw in desc for kw in ("must", "only", "at least", "under", "do not")
            )
            if not has_constraints:
                return cond
        if cond == "selection_is_exploratory_not_final":
            buy_actions = [a for a in actions if a.get("action_type") == "buy"]
            if not buy_actions:
                return cond
        if cond == "selected_option_has_explicit_match_evidence":
            for a in reversed(actions):
                content = str(a.get("content", "")).lower()
                if (
                    "match" in content
                    or "satisfies" in content
                    or "meets all" in content
                    or "all constraints met" in content
                    or "matches all constraints" in content
                ):
                    return cond
        if cond == "errors_are_resolved_in_subsequent_turns":
            recovery_events = record.get("affordance_path", {}).get(
                "recovery_events", []
            )
            if recovery_events and all(r.get("recovered") for r in recovery_events):
                return cond
        if cond == "error_count_is_only_analysis_mentions":
            if payment.get("error_count", 0) == 0:
                return cond
        if cond == "constraints_are_explicit_and_clear":
            has_constraints = any(
                kw in desc
                for kw in ("must", "only", "at least", "under", "do not", "should")
            )
            if has_constraints:
                return cond
        if cond == "action_is_low_cost_exploratory":
            first_actions = actions[:3] if actions else []
            is_exploratory = all(
                a.get("action_type") in ("analysis",)
                or "cat " in str(a.get("content", "")).lower()
                or "ls" in str(a.get("content", "")).lower()
                for a in first_actions
            )
            if is_exploratory:
                return cond
        if cond == "intermediate_representation_exists_in_prior_turns":
            has_analysis = any(
                a.get("action_type") == "analysis"
                for a in actions[: max(1, len(actions) - 1)]
            )
            if has_analysis:
                return cond
        if cond == "user_or_environment_feedback_has_resolved_ambiguity":
            if len(observations) >= 2:
                return cond
        if cond == "settlement_quality_is_not_failure_with_signal":
            if outcome.get("settlement_quality") != "failure_with_signal":
                return cond
        if cond == "no_failure_condition_evidence_available":
            has_errors = payment.get("error_count", 0) > 0
            has_failure_sq = outcome.get("settlement_quality") in (
                "failure_with_signal",
                "failure_without_signal",
            )
            if not (has_errors or has_failure_sq):
                return cond

    return None


def _assess_counterfactual(
    policy: dict[str, Any],
    record: dict[str, Any],
    fired: bool,
) -> tuple[str, str, str, str, str | None, list[str]]:
    if not fired:
        return "no_effect", "Policy trigger not met.", "low", "low", None, []

    fm = record.get("labels", {}).get("failure_mode")
    sq = record.get("outcome", {}).get("settlement_quality", "")
    conf = record.get("outcome", {}).get("confidence", 0.0)
    payment = record.get("payment", {})
    error_count = payment.get("error_count", 0)
    policy_fms = policy.get("evidence", {}).get("observed_failure_patterns", [])

    payment_risk = "low"
    if error_count >= 3 or payment.get("turns", 0) >= 10:
        payment_risk = "medium"
    if error_count >= 5 or payment.get("turns", 0) >= 15:
        payment_risk = "high"

    fp_risk = "low"
    if sq in ("clean_success", "recovered_success") and fm is None:
        fp_risk = "high"
    elif sq in ("clean_success",) and fm is None:
        fp_risk = "medium"

    if sq in ("failure_with_signal", "failure_without_signal") and fm in policy_fms:
        return (
            "likely_helpful",
            f"Policy addresses observed failure mode '{fm}' in {sq} trace.",
            payment_risk,
            fp_risk,
            None,
            [],
        )

    if sq in ("clean_success", "recovered_success") and fm is None:
        return (
            "likely_harmful",
            f"Policy would fire on successful trace (quality={sq}) with no failure mode.",
            payment_risk,
            fp_risk,
            None,
            [],
        )

    if sq in ("partial_success", "unknown"):
        return (
            "uncertain",
            f"Policy fires on ambiguous trace (quality={sq}, fm={fm}).",
            payment_risk,
            fp_risk,
            None,
            [],
        )

    if fm and fm not in policy_fms:
        return (
            "uncertain",
            f"Policy fires but failure mode '{fm}' not in policy's target patterns {policy_fms}.",
            payment_risk,
            fp_risk,
            None,
            [],
        )

    return (
        "uncertain",
        f"Policy fires on trace with quality={sq}, fm={fm}.",
        payment_risk,
        fp_risk,
        None,
        [],
    )


def evaluate_policies_shadow(
    records: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    min_confidence: float = 0.65,
    dataset: str | None = None,
    domain: str | None = None,
    target_policy_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    results = []
    filtered = []
    for rec in records:
        if (
            min_confidence > 0
            and rec.get("outcome", {}).get("confidence", 0.0) < min_confidence
        ):
            continue
        if dataset and rec.get("dataset") != dataset:
            continue
        if domain and rec.get("domain") != domain:
            continue
        filtered.append(rec)

    for policy in policies:
        if policy.get("status") == "superseded":
            continue
        if target_policy_ids and policy.get("id") not in target_policy_ids:
            continue
        for record in filtered:
            trigger = policy.get("trigger", {})
            negative_conditions = policy.get("negative_conditions")
            fired, trigger_evidence = _check_trigger(
                trigger, record, negative_conditions
            )

            fire_turn_index = _estimate_fire_turn_index(trigger, record, fired)
            fire_timing, remaining_turns_after_fire = _classify_fire_timing(
                trigger,
                record,
                fire_turn_index,
                fired,
            )
            recovery_opportunity, recovery_opportunity_evidence = (
                _detect_recovery_opportunity(
                    record,
                    fire_timing,
                    fire_turn_index,
                    remaining_turns_after_fire,
                )
                if fired
                else (False, ["policy_did_not_fire"])
            )

            assessment, rationale, payment_risk, fp_risk, _, _ = _assess_counterfactual(
                policy, record, fired
            )
            uncertainty_reason = None
            uncertainty_evidence: list[str] = []
            if fired and assessment == "uncertain":
                uncertainty_reason, uncertainty_evidence = _classify_uncertainty(
                    policy,
                    record,
                    trigger_evidence,
                    fire_timing,
                    recovery_opportunity,
                    remaining_turns_after_fire,
                )

            results.append(
                {
                    "policy_id": policy.get("id", ""),
                    "trace_id": record.get("task_id", ""),
                    "dataset": record.get("dataset", ""),
                    "domain": record.get("domain", ""),
                    "would_fire": fired,
                    "trigger_evidence": trigger_evidence,
                    "observed_failure_mode": record.get("labels", {}).get(
                        "failure_mode"
                    ),
                    "observed_settlement_quality": record.get("outcome", {}).get(
                        "settlement_quality", ""
                    ),
                    "observed_confidence": record.get("outcome", {}).get(
                        "confidence", 0.0
                    ),
                    "counterfactual_assessment": assessment,
                    "rationale": rationale,
                    "uncertainty_reason": uncertainty_reason,
                    "uncertainty_evidence": uncertainty_evidence,
                    "payment_risk": payment_risk,
                    "false_positive_risk": fp_risk,
                    "fire_turn_index": fire_turn_index,
                    "fire_timing": fire_timing,
                    "remaining_turns_after_fire": remaining_turns_after_fire,
                    "recovery_opportunity": recovery_opportunity,
                    "recovery_opportunity_evidence": recovery_opportunity_evidence,
                }
            )

    return results


def _distribution(items: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = item or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _example_lines(results: list[dict[str, Any]], limit: int = 5) -> list[str]:
    lines = []
    for r in results[:limit]:
        lines.append(
            "- "
            f"`{r.get('trace_id', '')}` "
            f"dataset={r.get('dataset', '')} "
            f"assessment={r.get('counterfactual_assessment', '')} "
            f"timing={r.get('fire_timing', '')} "
            f"recovery={r.get('recovery_opportunity')} "
            f"evidence={r.get('trigger_evidence', [])}"
        )
    return lines or ["- None observed."]


def _representative_trace_excerpt(result: dict[str, Any]) -> str:
    return (
        f"- Trace `{result.get('trace_id', '')}`: "
        f"settlement={result.get('observed_settlement_quality', '')}, "
        f"failure_mode={result.get('observed_failure_mode')}, "
        f"trigger_evidence={result.get('trigger_evidence', [])}, "
        f"uncertainty={result.get('uncertainty_reason') or 'n/a'}."
    )


def _policy_refinement_check(policy_id: str, results: list[dict[str, Any]]) -> list[str]:
    uncertain_reasons = _distribution(
        [
            r.get("uncertainty_reason") or "unknown"
            for r in results
            if r.get("counterfactual_assessment") == "uncertain"
        ]
    )
    late_count = sum(
        1
        for r in results
        if r.get("fire_timing") in ("late", "final_turn", "after_failure_already_settled")
    )
    recovery_count = sum(1 for r in results if r.get("recovery_opportunity"))

    if policy_id == "require_reflection_after_repeated_errors":
        return [
            "Repeated errors should remain constrained to unresolved tool or environment errors.",
            f"Late, final, or already-settled fires: {late_count}.",
            "Reflection remains plausible when recovery opportunity exists; traces that need a revised plan should refine the intervention before activation.",
            f"Offline evaluator limitation signals: {uncertain_reasons.get('policy_action_effect_not_observable_offline', 0)}.",
        ]
    if policy_id == "require_explicit_settlement_for_failure":
        domains = _distribution([r.get("domain", "unknown") for r in results])
        return [
            "The trigger is tied to observed failure_with_signal settlement and explicit failure-condition evidence.",
            f"Recovery opportunity fires: {recovery_count}.",
            f"Domain distribution: {domains}.",
            "No domain-specific variant is justified unless helpful evidence concentrates in one domain after more traces.",
        ]
    return ["No policy-specific refinement check is defined."]


def generate_policy_evidence_packs(
    results: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    output_dir: str | Path,
    target_policy_ids: set[str] | None = None,
) -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    scores_by_policy = {
        score["policy_id"]: score for score in compute_promotion_scores(results, policies)
    }
    results_by_policy: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        if result.get("would_fire"):
            results_by_policy.setdefault(result.get("policy_id", ""), []).append(result)

    written: list[Path] = []
    for policy in policies:
        pid = policy.get("id", "")
        if target_policy_ids and pid not in target_policy_ids:
            continue
        fires = results_by_policy.get(pid, [])
        score = scores_by_policy.get(pid, {})
        helpful = [r for r in fires if r.get("counterfactual_assessment") == "likely_helpful"]
        uncertain = [r for r in fires if r.get("counterfactual_assessment") == "uncertain"]
        harmful = [r for r in fires if r.get("counterfactual_assessment") == "likely_harmful"]
        uncertainty_groups: dict[str, list[dict[str, Any]]] = {}
        for r in uncertain:
            uncertainty_groups.setdefault(r.get("uncertainty_reason") or "unknown", []).append(r)

        fire_timing = score.get(
            "fire_timing_distribution",
            _distribution([r.get("fire_timing", "unknown") for r in fires]),
        )
        recovery_distribution = _distribution(
            ["has_recovery_opportunity" if r.get("recovery_opportunity") else "no_recovery_opportunity" for r in fires]
        )

        lines = [
            f"# {pid}",
            "",
            "## Policy Definition",
            "",
            "```yaml",
            yaml.safe_dump(
                {
                    "trigger": policy.get("trigger", {}),
                    "negative_conditions": policy.get("negative_conditions", []),
                    "required_evidence": policy.get("required_evidence", []),
                    "action": policy.get("action", {}),
                },
                sort_keys=False,
            ).strip(),
            "```",
            "",
            "## Intended Intervention",
            "",
            policy.get("rationale", "No rationale recorded."),
            "",
            "## Current Support Counts",
            "",
            f"- Mined support: {policy.get('evidence', {}).get('supporting_trace_count', 0)}",
            f"- Would-fire events: {score.get('would_fire_count', 0)}",
            f"- Likely helpful: {score.get('likely_helpful_count', 0)}",
            f"- Uncertain: {score.get('uncertain_count', 0)}",
            f"- Harmful: {score.get('likely_harmful_count', 0)}",
            "",
            "## Would-Fire Examples",
            "",
            *_example_lines(fires),
            "",
            "## Likely Helpful Examples",
            "",
            *_example_lines(helpful),
            "",
            "## Uncertain Examples By Reason",
            "",
        ]
        if uncertainty_groups:
            for reason, grouped in sorted(uncertainty_groups.items()):
                lines.extend([f"### {reason}", "", *_example_lines(grouped), ""])
        else:
            lines.extend(["- None observed.", ""])

        lines.extend(
            [
                "## Harmful Examples",
                "",
                *_example_lines(harmful),
                "",
                "## Fire Timing Distribution",
                "",
                f"`{json.dumps(fire_timing, sort_keys=True)}`",
                "",
                "## Recovery Opportunity Distribution",
                "",
                f"`{json.dumps(recovery_distribution, sort_keys=True)}`",
                "",
                "## Representative Trace Excerpts",
                "",
                *([_representative_trace_excerpt(r) for r in fires[:5]] or ["- None observed."]),
                "",
                "## What Evidence Is Still Missing",
                "",
                "- More likely-helpful shadow fires with recovery opportunity.",
                "- Clearer outcome signals after policy trigger points.",
                "- Evidence that the policy action changes settlement, not only that the trigger matches.",
                "",
                "## Policy-Specific Refinement Check",
                "",
                *_policy_refinement_check(pid, fires),
                "",
                "## Recommendation",
                "",
                f"`{score.get('recommendation', 'keep_proposed')}`: {score.get('recommendation_rationale', 'No recommendation rationale recorded.')}",
                "",
            ]
        )

        path = out / f"{pid}.md"
        path.write_text("\n".join(lines))
        written.append(path)

    return written


def compute_promotion_scores(
    results: list[dict[str, Any]],
    policies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    policy_results: dict[str, list[dict]] = {}
    policy_by_id = {policy.get("id"): policy for policy in policies}
    for r in results:
        pid = r["policy_id"]
        policy_results.setdefault(pid, []).append(r)

    scores = []
    for policy in policies:
        pid = policy.get("id", "")
        pr = policy_results.get(pid, [])

        fire_count = sum(1 for r in pr if r["would_fire"])
        helpful = sum(
            1
            for r in pr
            if r["would_fire"] and r["counterfactual_assessment"] == "likely_helpful"
        )
        harmful = sum(
            1
            for r in pr
            if r["would_fire"] and r["counterfactual_assessment"] == "likely_harmful"
        )
        uncertain = sum(
            1
            for r in pr
            if r["would_fire"] and r["counterfactual_assessment"] == "uncertain"
        )

        fire_events = [r for r in pr if r["would_fire"]]
        fp_rate = 0.0
        if fire_events:
            fp_events = sum(
                1 for r in fire_events if r["false_positive_risk"] in ("high", "medium")
            )
            fp_rate = round(fp_events / len(fire_events), 3)

        payment_dist: dict[str, int] = {}
        uncertainty_reason_distribution: dict[str, int] = {}
        fire_timing_distribution: dict[str, int] = {}
        recovery_opportunity_count = 0
        helpful_with_recovery_opportunity_count = 0
        uncertain_with_recovery_opportunity_count = 0
        fires_after_failure_settled_count = 0
        for r in fire_events:
            pr_key = r.get("payment_risk", "low")
            payment_dist[pr_key] = payment_dist.get(pr_key, 0) + 1
            timing = r.get("fire_timing", "unknown")
            fire_timing_distribution[timing] = fire_timing_distribution.get(timing, 0) + 1
            if timing == "after_failure_already_settled":
                fires_after_failure_settled_count += 1
            if r.get("recovery_opportunity"):
                recovery_opportunity_count += 1
                if r.get("counterfactual_assessment") == "likely_helpful":
                    helpful_with_recovery_opportunity_count += 1
                if r.get("counterfactual_assessment") == "uncertain":
                    uncertain_with_recovery_opportunity_count += 1
            if r.get("counterfactual_assessment") == "uncertain":
                reason = r.get("uncertainty_reason") or "unknown"
                uncertainty_reason_distribution[reason] = (
                    uncertainty_reason_distribution.get(reason, 0) + 1
                )

        domains = sorted(set(r["domain"] for r in fire_events)) if fire_events else []
        datasets = sorted(set(r["dataset"] for r in fire_events)) if fire_events else []

        recommendation = "keep_proposed"
        rec_rationale = ""

        if fire_count == 0:
            recommendation = "needs_more_evidence"
            rec_rationale = "Policy never fires on evaluated records."
        elif harmful > 0:
            recommendation = "reject" if harmful >= helpful else "refine"
            rec_rationale = f"Policy harms {harmful} successful traces."
        elif fp_rate > 0.5:
            recommendation = "refine"
            rec_rationale = f"False positive rate {fp_rate:.1%} is too high."
        elif helpful >= 5 and harmful == 0 and fp_rate <= 0.10:
            multi_source = len(datasets) >= 2 or len(domains) >= 2
            if multi_source or policy.get("_domain_specific"):
                recommendation = "candidate_for_activation"
                rec_rationale = f"Helpful on {helpful} traces across {len(datasets)} datasets, no harm, FP rate {fp_rate:.1%}."
            else:
                recommendation = "candidate_for_activation"
                rec_rationale = f"Helpful on {helpful} traces, no harm, FP rate {fp_rate:.1%}. Limited cross-dataset evidence ({len(datasets)} dataset)."
        elif helpful > 0 and harmful == 0:
            recommendation = "keep_proposed"
            rec_rationale = (
                f"Helpful on {helpful} traces but below activation threshold (need 5+)."
            )
        else:
            recommendation = "keep_proposed"
            rec_rationale = "Insufficient evidence for promotion."

        scores.append(
            {
                "policy_id": pid,
                "supporting_trace_count": policy_by_id.get(pid, {})
                .get("evidence", {})
                .get("supporting_trace_count", 0),
                "would_fire_count": fire_count,
                "likely_helpful_count": helpful,
                "likely_harmful_count": harmful,
                "uncertain_count": uncertain,
                "false_positive_rate_estimate": fp_rate,
                "uncertainty_reason_distribution": uncertainty_reason_distribution,
                "fire_timing_distribution": fire_timing_distribution,
                "recovery_opportunity_count": recovery_opportunity_count,
                "helpful_with_recovery_opportunity_count": helpful_with_recovery_opportunity_count,
                "uncertain_with_recovery_opportunity_count": uncertain_with_recovery_opportunity_count,
                "fires_after_failure_settled_count": fires_after_failure_settled_count,
                "payment_risk_distribution": payment_dist,
                "domains_observed": domains,
                "datasets_observed": datasets,
                "recommendation": recommendation,
                "recommendation_rationale": rec_rationale,
            }
        )

    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate policies in shadow mode")
    parser.add_argument("--ledger", default=None, help="SQLite ledger path")
    parser.add_argument("--policies", default="data/settlement_datasets/policies.yaml")
    parser.add_argument(
        "--output", default="data/settlement_datasets/policy_shadow_eval"
    )
    parser.add_argument("--min-confidence", type=float, default=0.0)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--domain", default=None)
    parser.add_argument(
        "--target-policy",
        action="append",
        default=[],
        help="Restrict shadow evaluation and evidence packs to a policy id. May repeat.",
    )
    parser.add_argument(
        "--evidence-pack-output",
        default="docs/policy-evidence-packs",
        help="Directory for generated policy evidence packs.",
    )
    add_run_scope_arguments(parser)

    args = parser.parse_args()
    scope = None
    if any([args.run_id, args.run_dir, args.input_run_dir, args.output_run_dir]):
        scope = ensure_run_surface(
            run_id=args.run_id,
            run_dir=args.run_dir,
            input_run_dir=args.input_run_dir,
            output_run_dir=args.output_run_dir,
        )

    policies_path = (
        str(scope.named_path("policies", "policies.yaml", input_surface=True))
        if scope is not None
        else args.policies
    )
    with open(policies_path) as f:
        policy_data = yaml.safe_load(f)
    policies = policy_data.get("policies", [])

    all_records = []
    datasets = [args.dataset] if args.dataset else available_datasets()
    for ds in datasets:
        path = (
            str(scope.dataset_jsonl_path("normalized", ds, input_surface=True))
            if scope is not None
            else f"data/settlement_datasets/raw_samples/{ds}.jsonl"
        )
        p = Path(path)
        if p.exists():
            all_records.extend(read_records_jsonl(str(p)))

    print(f"Loaded {len(policies)} policies, {len(all_records)} records")

    results = evaluate_policies_shadow(
        all_records,
        policies,
        min_confidence=args.min_confidence,
        dataset=args.dataset,
        domain=args.domain,
        target_policy_ids=set(args.target_policy) if args.target_policy else None,
    )

    output_dir = scope.shadow_dir if scope is not None else Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "policy_shadow_results.jsonl"
    write_records_jsonl(results, str(results_path))
    print(f"Wrote {len(results)} shadow results -> {results_path}")

    scores = compute_promotion_scores(results, policies)
    scores_path = output_dir / "policy_promotion_scores.jsonl"
    write_records_jsonl(scores, str(scores_path))

    summary_path = output_dir / "policy_shadow_summary.csv"
    with summary_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "policy_id",
                "supporting_trace_count",
                "would_fire_count",
                "likely_helpful_count",
                "likely_harmful_count",
                "uncertain_count",
                "false_positive_rate_estimate",
                "uncertainty_reason_distribution",
                "fire_timing_distribution",
                "recovery_opportunity_count",
                "helpful_with_recovery_opportunity_count",
                "uncertain_with_recovery_opportunity_count",
                "fires_after_failure_settled_count",
                "payment_risk_distribution",
                "domains_observed",
                "datasets_observed",
                "recommendation",
                "recommendation_rationale",
            ],
        )
        writer.writeheader()
        for s in scores:
            writer.writerow(s)
    print(f"Wrote promotion scores -> {summary_path}")

    if args.target_policy:
        pack_paths = generate_policy_evidence_packs(
            results,
            policies,
            args.evidence_pack_output,
            target_policy_ids=set(args.target_policy),
        )
        print(f"Wrote {len(pack_paths)} policy evidence packs -> {args.evidence_pack_output}")

    for s in scores:
        print(
            f"  {s['policy_id']}: fires={s['would_fire_count']}, "
            f"helpful={s['likely_helpful_count']}, harmful={s['likely_harmful_count']}, "
            f"FP={s['false_positive_rate_estimate']:.1%}, rec={s['recommendation']}"
        )


if __name__ == "__main__":
    main()
