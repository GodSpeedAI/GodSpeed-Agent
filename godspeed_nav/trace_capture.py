"""Live harness trace capture for policy evidence generation.

Records step-level events from real or local agent runs with settlement
signal detection. Disabled by default; enabled via environment variable
HARNESS_TRACE_CAPTURE_ENABLED=true or explicit constructor argument.

This module is instrumentation only. It does not activate policies,
enforce interventions, or promote metabolization candidates.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


VALID_TRACE_EVENT_TYPES = {
    "model_message",
    "tool_call",
    "tool_result",
    "error",
    "file_edit",
    "command",
    "test_run",
    "final_answer",
    "task_complete",
    "evaluator_result",
    "strategy_revision",
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

REQUIRED_SIGNAL_FIELDS = {
    "error_detected",
    "task_complete",
    "success_signal",
    "failure_signal",
    "test_passed",
    "test_failed",
    "strategy_revision_detected",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _empty_signals() -> dict[str, bool]:
    return {
        "error_detected": False,
        "task_complete": False,
        "success_signal": False,
        "failure_signal": False,
        "test_passed": False,
        "test_failed": False,
        "strategy_revision_detected": False,
    }


def is_trace_capture_enabled(env: dict[str, str] | None = None) -> bool:
    """Check whether trace capture is enabled via environment."""
    source = env if env is not None else os.environ
    return str(source.get("HARNESS_TRACE_CAPTURE_ENABLED", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def default_trace_dir(env: dict[str, str] | None = None) -> str:
    """Return the configured trace output directory."""
    source = env if env is not None else os.environ
    return source.get(
        "HARNESS_TRACE_CAPTURE_DIR",
        "data/settlement_datasets/live_harness_traces",
    )


def infer_settlement_signals(content: str, event_type: str) -> dict[str, bool]:
    """Infer settlement signals from event content and type."""
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
    signals["task_complete"] = (
        event_type == "task_complete" or "task complete" in lowered
    )
    signals["failure_signal"] = any(
        token in lowered for token in ("cannot complete", "failed", "failure", "unable")
    )
    signals["success_signal"] = not signals["failure_signal"] and any(
        token in lowered for token in ("success", "succeeded", "complete", "done")
    )
    signals["test_passed"] = "passed" in lowered or "tests pass" in lowered
    signals["test_failed"] = "test failed" in lowered or "tests failed" in lowered
    if "failed" in lowered and "passed" in lowered:
        signals["test_failed"] = True
    signals["strategy_revision_detected"] = event_type == "strategy_revision" or any(
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
    return signals


def validate_trace_event(event: dict[str, Any]) -> list[str]:
    """Validate a trace event against the required schema."""
    errors: list[str] = []
    for field in REQUIRED_EVENT_FIELDS:
        if field not in event:
            errors.append(f"missing_required_field:{field}")

    if "event_type" in event and event.get("event_type") not in VALID_TRACE_EVENT_TYPES:
        errors.append(f"invalid_event_type:{event.get('event_type')}")
    if "step_index" in event and not isinstance(event.get("step_index"), int):
        errors.append("invalid_step_index")
    if "settlement_signals" in event:
        if not isinstance(event.get("settlement_signals"), dict):
            errors.append("invalid_settlement_signals")
        else:
            for sf in REQUIRED_SIGNAL_FIELDS:
                if sf not in event["settlement_signals"]:
                    errors.append(f"missing_signal_field:{sf}")
    return errors


def normalize_trace_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize a trace event, inferring missing settlement signals."""
    normalized = {
        "run_id": event.get("run_id", ""),
        "step_index": int(event.get("step_index", 0)),
        "timestamp": event.get("timestamp", "") or _now_iso(),
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
    # Explicit caller-provided signals override inferred ones
    normalized["settlement_signals"].update(
        {
            k: v
            for k, v in (event.get("settlement_signals") or {}).items()
            if v is not None
        }
    )
    return normalized


class HarnessTraceCapture:
    """Records step-level live traces from harness execution.

    Disabled by default. Enable via environment variable
    HARNESS_TRACE_CAPTURE_ENABLED=true or pass enabled=True.

    Writes traces under:
        <trace_dir>/<run_id>/
            events.jsonl
            run_summary.json
            settlement_record.json
            shadow_policy_results.jsonl
    """

    def __init__(
        self,
        run_id: str,
        *,
        enabled: bool | None = None,
        trace_dir: str | None = None,
        run_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.run_id = run_id
        self.enabled = is_trace_capture_enabled() if enabled is None else enabled
        self.trace_dir = trace_dir or default_trace_dir()
        self.run_metadata = run_metadata or {}
        self._events: list[dict[str, Any]] = []
        self._step_counter: int = 0
        self._started_at: str = _now_iso()
        self._finalized: bool = False

    @property
    def run_dir(self) -> Path:
        return Path(self.trace_dir) / self.run_id

    def record_event(
        self,
        event_type: str,
        content: str,
        *,
        tool_name: str | None = None,
        metadata: dict[str, Any] | None = None,
        settlement_signals: dict[str, bool] | None = None,
        step_index: int | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Record a single step-level event.

        Returns the normalized event dict regardless of whether
        capture is enabled, so callers can inspect it.
        """
        if step_index is not None:
            idx = step_index
        else:
            idx = self._step_counter
            self._step_counter += 1

        raw = {
            "run_id": self.run_id,
            "step_index": idx,
            "timestamp": timestamp or _now_iso(),
            "event_type": event_type,
            "content": content,
            "tool_name": tool_name,
            "metadata": metadata or {},
            "settlement_signals": settlement_signals or {},
        }
        normalized = normalize_trace_event(raw)
        errors = validate_trace_event(normalized)
        if errors:
            raise ValueError(f"invalid trace event: {errors}")

        if self.enabled:
            self._events.append(normalized)
            self._append_event_to_file(normalized)

        return normalized

    def record_model_message(self, content: str, **kwargs: Any) -> dict[str, Any]:
        return self.record_event("model_message", content, **kwargs)

    def record_tool_call(
        self, content: str, *, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event("tool_call", content, tool_name=tool_name, **kwargs)

    def record_tool_result(
        self, content: str, *, tool_name: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event("tool_result", content, tool_name=tool_name, **kwargs)

    def record_error(self, content: str, **kwargs: Any) -> dict[str, Any]:
        return self.record_event("error", content, **kwargs)

    def record_file_edit(self, content: str, **kwargs: Any) -> dict[str, Any]:
        return self.record_event("file_edit", content, **kwargs)

    def record_command(self, content: str, **kwargs: Any) -> dict[str, Any]:
        return self.record_event("command", content, **kwargs)

    def record_test_run(self, content: str, **kwargs: Any) -> dict[str, Any]:
        return self.record_event("test_run", content, **kwargs)

    def record_final_answer(self, content: str, **kwargs: Any) -> dict[str, Any]:
        return self.record_event("final_answer", content, **kwargs)

    def record_task_complete(self, content: str = "", **kwargs: Any) -> dict[str, Any]:
        return self.record_event("task_complete", content or "task complete", **kwargs)

    def record_evaluator_result(self, content: str, **kwargs: Any) -> dict[str, Any]:
        return self.record_event("evaluator_result", content, **kwargs)

    def record_strategy_revision(self, content: str, **kwargs: Any) -> dict[str, Any]:
        return self.record_event("strategy_revision", content, **kwargs)

    def finalize_run(
        self,
        *,
        final_outcome: str = "unknown",
        settlement_quality: str = "unknown",
    ) -> dict[str, Any]:
        """Finalize the run and write summary files."""
        self._finalized = True
        ended_at = _now_iso()

        error_events = [
            e for e in self._events if e["settlement_signals"].get("error_detected")
        ]
        test_events = [
            e
            for e in self._events
            if e["settlement_signals"].get("test_passed")
            or e["settlement_signals"].get("test_failed")
        ]
        strategy_events = [
            e
            for e in self._events
            if e["settlement_signals"].get("strategy_revision_detected")
        ]
        task_complete_events = [
            e for e in self._events if e["settlement_signals"].get("task_complete")
        ]

        summary = {
            "run_id": self.run_id,
            "started_at": self._started_at,
            "ended_at": ended_at,
            "total_steps": len(self._events),
            "final_outcome": final_outcome,
            "settlement_quality": settlement_quality,
            "error_count": len(error_events),
            "test_event_count": len(test_events),
            "strategy_revision_count": len(strategy_events),
            "task_complete_count": len(task_complete_events),
            "run_metadata": self.run_metadata,
            "trace_capture_enabled": self.enabled,
        }

        settlement_record = self._build_settlement_record(summary)

        if self.enabled:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            (self.run_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            (self.run_dir / "settlement_record.json").write_text(
                json.dumps(settlement_record, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            # Ensure shadow_policy_results.jsonl exists even if empty
            shadow_path = self.run_dir / "shadow_policy_results.jsonl"
            if not shadow_path.exists():
                shadow_path.write_text("", encoding="utf-8")

        return summary

    def _build_settlement_record(self, summary: dict[str, Any]) -> dict[str, Any]:
        """Build a preliminary settlement record from captured events."""
        events = self._events
        error_steps = [
            e["step_index"]
            for e in events
            if e["settlement_signals"].get("error_detected")
        ]
        strategy_steps = [
            e["step_index"]
            for e in events
            if e["settlement_signals"].get("strategy_revision_detected")
        ]
        test_passed_steps = [
            e["step_index"]
            for e in events
            if e["settlement_signals"].get("test_passed")
        ]
        test_failed_steps = [
            e["step_index"]
            for e in events
            if e["settlement_signals"].get("test_failed")
        ]
        task_complete_steps = [
            e["step_index"]
            for e in events
            if e["settlement_signals"].get("task_complete")
        ]

        # Detect same-path continuation after second error
        same_path_continuation = False
        if len(error_steps) >= 2:
            second_error_step = sorted(error_steps)[1]
            post_error_events = [
                e for e in events if e["step_index"] > second_error_step
            ]
            for pe in post_error_events:
                if pe["event_type"] in {"tool_call", "command", "file_edit"}:
                    same_path_continuation = True
                    break

        # Detect duplicate errors (same content)
        error_contents = [
            e["content"]
            for e in events
            if e["settlement_signals"].get("error_detected")
        ]
        duplicate_errors = len(error_contents) != len(set(error_contents))

        # Detect low-cost inspection after error
        low_cost_inspection = False
        if error_steps:
            last_error = max(error_steps)
            post_error = [
                e
                for e in events
                if e["step_index"] > last_error and e["step_index"] <= last_error + 2
            ]
            for pe in post_error:
                if pe["event_type"] in {"model_message", "tool_call"} and any(
                    token in pe["content"].lower()
                    for token in (
                        "inspect",
                        "read",
                        "check",
                        "diagnose",
                        "look",
                        "examine",
                    )
                ):
                    low_cost_inspection = True
                    break

        return {
            "run_id": self.run_id,
            "dataset": "live_harness_trace",
            "domain": self.run_metadata.get("domain", "harness"),
            "task_id": self.run_metadata.get("task_id", self.run_id),
            "source_uri": f"live_harness_trace://{self.run_id}",
            "desired_direction": {
                "statement": self.run_metadata.get("desired_direction", ""),
                "source": "live_capture",
            },
            "environment": {
                "type": "harness",
                "has_runnable_feedback": True,
                "feedback_type": "tool_output",
            },
            "representational_state": {
                "start": "unknown",
                "desired": "unknown",
                "path_shape": "unknown",
                "confidence": 0.0,
                "evidence": [],
            },
            "payment": {
                "turns": len(events),
                "tool_calls": sum(1 for e in events if e["event_type"] == "tool_call"),
                "commands": sum(1 for e in events if e["event_type"] == "command"),
                "page_actions": 0,
                "api_calls": 0,
                "elapsed_steps": len(events),
                "error_count": len(error_steps),
                "estimated_complexity": "unknown",
                "evidence": [],
            },
            "affordance_path": {
                "actions": [
                    {
                        "action_type": e["event_type"],
                        "content": e["content"],
                        "turn_index": e["step_index"],
                        "tool_name": e.get("tool_name"),
                    }
                    for e in events
                    if e["event_type"]
                    in {
                        "tool_call",
                        "command",
                        "file_edit",
                        "model_message",
                        "strategy_revision",
                    }
                ],
                "observations": [
                    {
                        "content": e["content"],
                        "turn_index": e["step_index"],
                        "tool_name": e.get("tool_name"),
                    }
                    for e in events
                    if e["event_type"]
                    in {"tool_result", "error", "test_run", "evaluator_result"}
                ],
            },
            "outcome": {
                "success": summary.get("final_outcome") == "success",
                "reward": None,
                "score": None,
                "settlement_quality": summary.get("settlement_quality", "unknown"),
                "confidence": 0.0,
                "evidence": [],
            },
            "labels": {
                "failure_mode": None,
                "failure_mode_confidence": 0.0,
                "failure_mode_evidence": [],
                "harness_policy_signal": None,
                "harness_policy_signal_confidence": 0.0,
                "harness_policy_signal_evidence": [],
                "metabolization_candidate": None,
                "metabolization_candidate_confidence": 0.0,
                "metabolization_candidate_evidence": [],
            },
            "metadata": {
                "trace_source": "live_harness_capture",
                "error_steps": sorted(error_steps),
                "strategy_revision_steps": sorted(strategy_steps),
                "test_passed_steps": sorted(test_passed_steps),
                "test_failed_steps": sorted(test_failed_steps),
                "task_complete_steps": sorted(task_complete_steps),
                "same_path_continuation_after_second_error": same_path_continuation,
                "duplicate_errors": duplicate_errors,
                "low_cost_inspection_after_error": low_cost_inspection,
            },
        }

    def _append_event_to_file(self, event: dict[str, Any]) -> None:
        """Append a single event to the events.jsonl file."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        events_path = self.run_dir / "events.jsonl"
        with events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

    @property
    def events(self) -> list[dict[str, Any]]:
        """Return all recorded events."""
        return list(self._events)

    @property
    def event_count(self) -> int:
        return len(self._events)


def read_trace_events(run_dir: str | Path) -> list[dict[str, Any]]:
    """Read all events from a captured trace directory."""
    events_path = Path(run_dir) / "events.jsonl"
    if not events_path.exists():
        return []
    events: list[dict[str, Any]] = []
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


def read_run_summary(run_dir: str | Path) -> dict[str, Any] | None:
    """Read the run summary from a captured trace directory."""
    summary_path = Path(run_dir) / "run_summary.json"
    if not summary_path.exists():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def read_settlement_record(run_dir: str | Path) -> dict[str, Any] | None:
    """Read the settlement record from a captured trace directory."""
    record_path = Path(run_dir) / "settlement_record.json"
    if not record_path.exists():
        return None
    return json.loads(record_path.read_text(encoding="utf-8"))


def read_shadow_policy_results(run_dir: str | Path) -> list[dict[str, Any]]:
    """Read shadow policy results from a captured trace directory."""
    shadow_path = Path(run_dir) / "shadow_policy_results.jsonl"
    if not shadow_path.exists():
        return []
    results: list[dict[str, Any]] = []
    with shadow_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def detect_duplicate_errors(events: list[dict[str, Any]]) -> bool:
    """Check whether any two error events have identical content."""
    error_contents = [
        e["content"] for e in events if e["settlement_signals"].get("error_detected")
    ]
    return len(error_contents) != len(set(error_contents))


def detect_same_path_continuation(events: list[dict[str, Any]]) -> bool:
    """Check whether the agent continued on the same path after a second error."""
    error_steps = sorted(
        e["step_index"] for e in events if e["settlement_signals"].get("error_detected")
    )
    if len(error_steps) < 2:
        return False
    second_error = error_steps[1]
    post_error = [e for e in events if e["step_index"] > second_error]
    for e in post_error:
        if e["event_type"] in {"tool_call", "command", "file_edit"}:
            # Check if it's a high-payment continuation (not just inspection)
            if not any(
                token in e["content"].lower()
                for token in ("inspect", "read", "check", "diagnose", "look", "examine")
            ):
                return True
    return False


def detect_strategy_revision_after_error(events: list[dict[str, Any]]) -> bool:
    """Check whether a strategy revision occurred after the latest error."""
    error_steps = [
        e["step_index"] for e in events if e["settlement_signals"].get("error_detected")
    ]
    revision_steps = [
        e["step_index"]
        for e in events
        if e["settlement_signals"].get("strategy_revision_detected")
    ]
    if not error_steps or not revision_steps:
        return False
    return max(revision_steps) > max(error_steps)


def detect_low_cost_inspection_after_error(events: list[dict[str, Any]]) -> bool:
    """Check whether a low-cost inspection action occurred after the latest error."""
    error_steps = [
        e["step_index"] for e in events if e["settlement_signals"].get("error_detected")
    ]
    if not error_steps:
        return False
    last_error = max(error_steps)
    post_error = [
        e
        for e in events
        if e["step_index"] > last_error and e["step_index"] <= last_error + 2
    ]
    for e in post_error:
        if e["event_type"] in {"model_message", "tool_call"} and any(
            token in e["content"].lower()
            for token in ("inspect", "read", "check", "diagnose", "look", "examine")
        ):
            return True
    return False
