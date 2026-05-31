from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)


TARGET_POLICY_IDS = {
    "require_reflection_after_repeated_errors",
    "require_explicit_settlement_for_failure",
}

VALID_EVENT_TYPES = {
    "model_message",
    "tool_call",
    "tool_result",
    "error",
    "final_answer",
    "task_complete",
    "evaluator_result",
}

REQUIRED_EVENT_FIELDS = {
    "run_id",
    "step_index",
    "timestamp",
    "event_type",
    "content",
    "tool_name",
    "metadata",
    "settlement_signals",
}


def is_live_shadow_enabled(env: dict[str, str] | None = None) -> bool:
    source = env if env is not None else os.environ
    return str(source.get("SHADOW_POLICY_EVAL_ENABLED", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _empty_signals() -> dict[str, bool]:
    return {
        "error_detected": False,
        "task_complete": False,
        "success_signal": False,
        "failure_signal": False,
        "test_passed": False,
        "test_failed": False,
    }


def infer_settlement_signals(content: str, event_type: str = "model_message") -> dict[str, bool]:
    lowered = content.lower()
    signals = _empty_signals()
    signals["error_detected"] = event_type == "error" or any(
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
    signals["task_complete"] = event_type == "task_complete" or "task complete" in lowered
    signals["failure_signal"] = any(
        token in lowered for token in ("cannot complete", "failed", "failure", "unable")
    )
    signals["success_signal"] = (
        not signals["failure_signal"]
        and any(token in lowered for token in ("success", "succeeded", "complete", "done"))
    )
    signals["test_passed"] = "passed" in lowered or "tests pass" in lowered
    signals["test_failed"] = "test failed" in lowered or "tests failed" in lowered
    if "failed" in lowered and "passed" in lowered:
        signals["test_failed"] = True
    return signals


def validate_live_run_event(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_EVENT_FIELDS:
        if field not in event:
            errors.append(f"missing_required_field:{field}")

    if "event_type" in event and event.get("event_type") not in VALID_EVENT_TYPES:
        errors.append(f"invalid_event_type:{event.get('event_type')}")
    if "step_index" in event and not isinstance(event.get("step_index"), int):
        errors.append("invalid_step_index")
    if "settlement_signals" in event and not isinstance(
        event.get("settlement_signals"), dict
    ):
        errors.append("invalid_settlement_signals")
    return errors


def normalize_live_run_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "run_id": event.get("run_id", ""),
        "step_index": int(event.get("step_index", 0)),
        "timestamp": event.get("timestamp", ""),
        "event_type": event.get("event_type", "model_message"),
        "content": str(event.get("content", "")),
        "tool_name": event.get("tool_name"),
        "metadata": event.get("metadata", {}),
        "settlement_signals": _empty_signals(),
    }
    inferred = infer_settlement_signals(
        normalized["content"],
        normalized["event_type"],
    )
    normalized["settlement_signals"].update(inferred)
    normalized["settlement_signals"].update(event.get("settlement_signals", {}) or {})
    return normalized


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


def _closure_likely(event: dict[str, Any]) -> bool:
    content = str(event.get("content", "")).lower()
    return event.get("event_type") in {"final_answer", "task_complete"} or any(
        token in content
        for token in (
            "final answer",
            "cannot complete",
            "unable to complete",
            "i failed",
            "task failed",
            "closing",
        )
    )


def _fire_timing(step_index: int, event_type: str) -> str:
    if event_type in {"final_answer", "task_complete"}:
        return "final_turn"
    if step_index < 3:
        return "early"
    if step_index < 8:
        return "middle"
    return "late"


class LiveShadowPolicyEvaluator:
    def __init__(
        self,
        *,
        enabled: bool | None = None,
        target_policy_ids: set[str] | None = None,
        run_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.enabled = is_live_shadow_enabled() if enabled is None else enabled
        self.target_policy_ids = target_policy_ids or set(TARGET_POLICY_IDS)
        self.run_metadata = run_metadata or {}
        self.events: list[dict[str, Any]] = []
        self.policy_fires: list[dict[str, Any]] = []
        self._fired_policy_ids: set[str] = set()
        self._unresolved_error_steps: list[int] = []
        self._last_strategy_revision_step: int | None = None
        self._task_settled = False
        self._settlement_evidence_recorded = False

    def record_event(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        normalized = normalize_live_run_event(event)
        errors = validate_live_run_event(normalized)
        if errors:
            raise ValueError(f"invalid live shadow event: {errors}")

        self.events.append(normalized)
        self._update_state(normalized)

        if not self.enabled:
            return []

        fires: list[dict[str, Any]] = []
        for policy_id in sorted(self.target_policy_ids):
            if policy_id in self._fired_policy_ids:
                continue
            fire = self._evaluate_policy(policy_id, normalized)
            if fire:
                self._fired_policy_ids.add(policy_id)
                self.policy_fires.append(fire)
                fires.append(fire)
        return fires

    def _update_state(self, event: dict[str, Any]) -> None:
        signals = event["settlement_signals"]
        step = int(event["step_index"])
        content = str(event.get("content", ""))

        if signals.get("error_detected") or signals.get("test_failed"):
            self._unresolved_error_steps.append(step)
        if signals.get("test_passed") or signals.get("success_signal"):
            self._settlement_evidence_recorded = True
            self._unresolved_error_steps.clear()
        if _contains_strategy_revision(content):
            self._last_strategy_revision_step = step
            self._unresolved_error_steps.clear()
        if signals.get("task_complete") or event.get("event_type") == "task_complete":
            self._task_settled = True

    def _evaluate_policy(
        self,
        policy_id: str,
        event: dict[str, Any],
    ) -> dict[str, Any] | None:
        if policy_id == "require_reflection_after_repeated_errors":
            return self._evaluate_reflection_policy(event)
        if policy_id == "require_explicit_settlement_for_failure":
            return self._evaluate_explicit_settlement_policy(event)
        return None

    def _base_fire(
        self,
        event: dict[str, Any],
        policy_id: str,
        trigger_evidence: list[str],
        shadow_action: str,
    ) -> dict[str, Any]:
        return {
            "run_id": event["run_id"],
            "step_index": event["step_index"],
            "policy_id": policy_id,
            "would_fire": True,
            "trigger_evidence": trigger_evidence,
            "shadow_action": shadow_action,
            "fire_timing": _fire_timing(event["step_index"], event["event_type"]),
            "recovery_opportunity": not self._task_settled,
            "activation_status": "shadow_only",
            "enforced": False,
        }

    def _evaluate_reflection_policy(self, event: dict[str, Any]) -> dict[str, Any] | None:
        if self._task_settled:
            return None
        if _closure_likely(event):
            return None
        if len(self._unresolved_error_steps) < 2:
            return None
        latest_error_step = max(self._unresolved_error_steps)
        if (
            self._last_strategy_revision_step is not None
            and self._last_strategy_revision_step >= latest_error_step
        ):
            return None
        return self._base_fire(
            event,
            "require_reflection_after_repeated_errors",
            [
                f"unresolved_error_count={len(self._unresolved_error_steps)}",
                f"latest_error_step={latest_error_step}",
                "no_strategy_revision_after_latest_error",
                "run_not_settled",
            ],
            "would_require_reflection_or_revised_plan",
        )

    def _evaluate_explicit_settlement_policy(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any] | None:
        signals = event["settlement_signals"]
        failure_condition = signals.get("failure_signal") or bool(self._unresolved_error_steps)
        if self._task_settled or self._settlement_evidence_recorded:
            return None
        if not failure_condition or not _closure_likely(event):
            return None
        return self._base_fire(
            event,
            "require_explicit_settlement_for_failure",
            [
                "failure_condition_detected",
                "closure_likely",
                "no_explicit_settlement_evidence_recorded",
                "task_not_settled",
            ],
            "would_require_explicit_settlement_evidence",
        )

    def finalize_run(
        self,
        *,
        final_outcome: str = "unknown",
        settlement_quality: str = "unknown",
    ) -> dict[str, Any]:
        run_id = self.events[0]["run_id"] if self.events else self.run_metadata.get("run_id", "")
        first_fire = min(
            (int(f["step_index"]) for f in self.policy_fires),
            default=None,
        )
        final_steps = {
            int(e["step_index"])
            for e in self.events
            if e.get("event_type") in {"final_answer", "task_complete"}
        }
        first_final = min(final_steps) if final_steps else None
        fires_before_final = sum(
            1
            for fire in self.policy_fires
            if first_final is None or int(fire["step_index"]) < first_final
        )
        post_fire_outcome = "unknown"
        if self.policy_fires:
            post_fire_outcome = {
                "success": "improved",
                "failure": "failed",
                "partial": "unknown",
            }.get(final_outcome, "unknown")
            if final_outcome == "success":
                post_fire_outcome = "succeeded_without_intervention"

        return {
            "run_id": run_id,
            "task_id": self.run_metadata.get("task_id", run_id),
            "domain": self.run_metadata.get("domain", "unknown"),
            "total_steps": len(self.events),
            "final_outcome": final_outcome,
            "settlement_quality": settlement_quality,
            "shadow_fires": self.policy_fires,
            "first_shadow_fire_step": first_fire,
            "fires_before_final": fires_before_final,
            "fires_with_recovery_opportunity": sum(
                1 for fire in self.policy_fires if fire.get("recovery_opportunity")
            ),
            "post_fire_outcome": post_fire_outcome,
            "policy_activation_recommendations": [],
        }


def event_from_trace_item(
    item: dict[str, Any],
    *,
    run_id: str,
    item_kind: str = "action",
) -> dict[str, Any]:
    action_type = item.get("action_type", "")
    content = str(item.get("content", ""))
    if item_kind == "observation":
        event_type = "tool_result"
    elif action_type in {"command", "api_call", "search", "buy", "selection"}:
        event_type = "tool_call"
    elif action_type in {"final_answer", "submit"}:
        event_type = "final_answer"
    else:
        event_type = "model_message"
    return normalize_live_run_event(
        {
            "run_id": run_id,
            "step_index": int(item.get("turn_index", 0)),
            "timestamp": str(item.get("timestamp", "")),
            "event_type": event_type,
            "content": content,
            "tool_name": item.get("tool_name") or action_type or None,
            "metadata": {"source_item": item_kind, "action_type": action_type},
            "settlement_signals": item.get("settlement_signals", {}),
        }
    )


def _events_from_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    run_id = str(record.get("task_id") or record.get("trace_id") or "unknown-run")
    items: list[dict[str, Any]] = []
    for action in record.get("affordance_path", {}).get("actions", []):
        items.append(event_from_trace_item(action, run_id=run_id, item_kind="action"))
    for observation in record.get("affordance_path", {}).get("observations", []):
        items.append(
            event_from_trace_item(
                observation,
                run_id=run_id,
                item_kind="observation",
            )
        )
    return sorted(items, key=lambda event: int(event.get("step_index", 0)))


def _final_outcome_from_record(record: dict[str, Any]) -> str:
    quality = record.get("outcome", {}).get("settlement_quality", "unknown")
    if quality in {"clean_success", "recovered_success"}:
        return "success"
    if quality in {"failure_with_signal", "failure_without_signal"}:
        return "failure"
    if quality == "partial_success":
        return "partial"
    return "unknown"


def replay_records_to_live_shadow(
    records: list[dict[str, Any]],
    *,
    output_dir: str | Path,
    enabled: bool = True,
    target_policy_ids: set[str] | None = None,
) -> dict[str, Path]:
    all_events: list[dict[str, Any]] = []
    all_fires: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for record in records:
        run_id = str(record.get("task_id") or record.get("trace_id") or "unknown-run")
        evaluator = LiveShadowPolicyEvaluator(
            enabled=enabled,
            target_policy_ids=target_policy_ids,
            run_metadata={
                "run_id": run_id,
                "task_id": run_id,
                "domain": record.get("domain", "unknown"),
            },
        )
        for event in _events_from_record(record):
            all_events.append(event)
            evaluator.record_event(event)
        summary = evaluator.finalize_run(
            final_outcome=_final_outcome_from_record(record),
            settlement_quality=record.get("outcome", {}).get(
                "settlement_quality",
                "unknown",
            ),
        )
        all_fires.extend(evaluator.policy_fires)
        summaries.append(summary)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "events": output / "events.jsonl",
        "policy_fires": output / "policy_fires.jsonl",
        "run_summaries": output / "run_summaries.jsonl",
    }
    write_records_jsonl(all_events, paths["events"])
    write_records_jsonl(all_fires, paths["policy_fires"])
    write_records_jsonl(summaries, paths["run_summaries"])
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay live shadow policy evaluation from settlement traces")
    parser.add_argument(
        "--input",
        default="data/settlement_datasets/evidence_accumulation_run/settlements/agenttrove.jsonl",
    )
    parser.add_argument("--output", default="data/settlement_datasets/live_shadow")
    parser.add_argument("--disabled", action="store_true")
    args = parser.parse_args()

    records = read_records_jsonl(args.input)
    paths = replay_records_to_live_shadow(
        records,
        output_dir=args.output,
        enabled=not args.disabled,
    )
    print(f"Wrote live shadow events -> {paths['events']}")
    print(f"Wrote live shadow policy fires -> {paths['policy_fires']}")
    print(f"Wrote live shadow run summaries -> {paths['run_summaries']}")


if __name__ == "__main__":
    main()
