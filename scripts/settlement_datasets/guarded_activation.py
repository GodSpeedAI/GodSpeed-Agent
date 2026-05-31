from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)
from scripts.settlement_datasets.live_shadow_policy_eval import (
    infer_settlement_signals,
    normalize_live_run_event,
)


POLICY_ID = "require_reflection_after_repeated_errors"
REFINED_POLICY_ID = "require_reflection_before_continuing_after_second_unresolved_error"
VALID_POLICY_IDS = {POLICY_ID, REFINED_POLICY_ID}
GUARDED_INTERVENTION_TEXT = (
    "Repeated unresolved errors detected.\n\n"
    "Before continuing, revise the plan using the latest settlement feedback:\n\n"
    "1. What failed?\n"
    "2. What assumption may be wrong?\n"
    "3. What lower-payment action should happen next?\n"
    "4. What evidence would show the next step worked?"
)

REQUIRED_TRIGGER_EVIDENCE = {
    "error_events",
    "continued_same_path_evidence",
    "missing_revision_evidence",
    "recovery_opportunity_evidence",
}

# Adaptive recovery tokens: indicate the agent is already adjusting behavior
# after an error rather than blindly continuing.
_ADAPTIVE_RECOVERY_TOKENS = (
    "check",
    "inspect",
    "look at",
    "look into",
    "examine",
    "diagnose",
    "debug",
    "investigate",
    "explore",
    "review",
    "analyze",
    "read",
    "cat ",
    "tail ",
    "head ",
    "less ",
    "grep ",
    "rg ",
    "find ",
    "ls ",
    "log",
    "logs",
    "server log",
    "error log",
    "stack trace",
    "traceback",
    "narrow",
    "narrower",
    "specific",
    "targeted",
    "focused",
    "let me see",
    "let me check",
    "let me look",
    "what happened",
    "what went wrong",
    "why did",
    "why is",
    "understand",
    "figure out",
)

# Non-adaptive continuation tokens: indicate the agent is retrying
# the same approach without adjustment.
_NON_ADAPTIVE_TOKENS = (
    "retry",
    "rerun",
    "run again",
    "try again",
    "same command",
    "same test",
    "same approach",
    "re-run",
    "rerunning",
    "let me retry",
    "let me try again",
    "might be a flaky",
    "might be flaky",
    "this might be a flaky",
    "just retry",
)


@dataclass(frozen=True)
class GuardedActivationConfig:
    activation_enabled: bool = False
    policy_id: str = REFINED_POLICY_ID
    mode: str = "shadow"
    max_fires_per_run: int = 1
    max_experiment_runs: int = 20


def _truthy(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def config_from_env(env: dict[str, str] | None = None) -> GuardedActivationConfig:
    source = env if env is not None else os.environ
    return GuardedActivationConfig(
        activation_enabled=_truthy(source.get("HARNESS_POLICY_ACTIVATION_ENABLED")),
        policy_id=source.get("HARNESS_POLICY_EXPERIMENT", REFINED_POLICY_ID),
        mode=source.get("HARNESS_POLICY_MODE", "shadow"),
        max_fires_per_run=int(source.get("HARNESS_POLICY_MAX_FIRES_PER_RUN", "1")),
        max_experiment_runs=int(source.get("HARNESS_POLICY_MAX_EXPERIMENT_RUNS", "20")),
    )


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


def _is_low_cost_inspection(event: dict[str, Any]) -> bool:
    content = str(event.get("content", "")).lower().strip()
    if event.get("event_type") != "tool_call":
        return False
    return content.startswith(("cat ", "ls", "pwd", "grep ", "rg ", "head ", "tail "))


def _fingerprint_error(content: str) -> str:
    lowered = " ".join(content.lower().split())
    for prefix in ("traceback:", "error:", "exception:"):
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix) :].strip()
    return lowered[:160]


def _detect_adaptive_recovery_in_event(event: dict[str, Any]) -> list[str]:
    """Check whether a single event shows adaptive recovery behavior.

    Returns a list of evidence strings describing what was detected.
    """
    content = str(event.get("content", "")).lower().strip()
    event_type = event.get("event_type", "")
    evidence: list[str] = []

    if event_type == "model_message":
        # Only count model messages that show genuine diagnostic intent
        # without non-adaptive qualifiers like "retry" or "rerun"
        has_non_adaptive = any(token in content for token in _NON_ADAPTIVE_TOKENS)
        if not has_non_adaptive:
            for token in _ADAPTIVE_RECOVERY_TOKENS:
                if token in content:
                    evidence.append(f"model_message_contains:{token.strip()}")
                    break
            # Check for explicit diagnostic intent
            if any(
                phrase in content
                for phrase in (
                    "let me check",
                    "let me look",
                    "let me inspect",
                    "let me see",
                    "i need to",
                    "i should",
                    "need to investigate",
                    "need to check",
                    "need to look",
                    "what's available",
                    "what is available",
                )
            ):
                evidence.append("model_message_diagnostic_intent")

    if event_type == "tool_call":
        # Low-cost inspection commands
        if content.startswith(
            ("cat ", "ls", "pwd", "grep ", "rg ", "head ", "tail ", "less ", "find ")
        ):
            evidence.append(f"tool_call_inspection:{content[:60]}")
        # Reading files
        tool_name = str(event.get("tool_name", "")).lower()
        if tool_name in ("read", "cat", "less", "head", "tail"):
            evidence.append(f"tool_call_read:{tool_name}")
        # Diagnostic commands
        if any(
            token in content
            for token in (
                "log",
                "debug",
                "diagnos",
                "inspect",
                "status",
                "info",
                "show",
                "list",
            )
        ):
            evidence.append(f"tool_call_diagnostic:{content[:60]}")
        # Parameter variation: same base command but with changed parameters
        # (e.g., adding --index-url, changing flags)
        if any(
            token in content
            for token in ("--index-url", "--verbose", "-vvv", "--debug", "--dry-run")
        ):
            evidence.append(f"tool_call_parameter_variation:{content[:60]}")

    if event_type == "strategy_revision":
        evidence.append("explicit_strategy_revision_event")

    if event_type == "file_edit":
        evidence.append("file_edit_action")

    return evidence


def detect_adaptive_recovery(
    events_between: list[dict[str, Any]],
    current_event: dict[str, Any],
) -> dict[str, Any]:
    """Detect adaptive recovery behavior between errors and at the current event.

    Looks at events between the first and second error, plus the current
    event being evaluated, to determine whether the agent is already
    adapting rather than blindly continuing.

    The detection prioritizes actual tool-call actions over model messages.
    A model message saying "let me check" followed by the same failing
    command is NOT adaptive recovery. A tool call that inspects logs or
    reads a config file IS adaptive recovery.

    Returns a classification dict with post_error_behavior, confidence,
    and evidence.
    """
    # Separate evidence by strength
    action_evidence: list[str] = []  # tool_call, strategy_revision, file_edit
    message_evidence: list[str] = []  # model_message only

    for event in events_between:
        event_evidence = _detect_adaptive_recovery_in_event(event)
        event_type = event.get("event_type", "")
        for ev in event_evidence:
            if event_type in ("tool_call", "strategy_revision", "file_edit"):
                action_evidence.append(ev)
            else:
                message_evidence.append(ev)

    # Check the current event
    current_evidence = _detect_adaptive_recovery_in_event(current_event)
    current_type = current_event.get("event_type", "")
    for ev in current_evidence:
        if current_type in ("tool_call", "strategy_revision", "file_edit"):
            action_evidence.append(ev)
        else:
            message_evidence.append(ev)

    # Check for non-adaptive signals in the current event
    current_content = str(current_event.get("content", "")).lower().strip()
    non_adaptive_signals = [
        token for token in _NON_ADAPTIVE_TOKENS if token in current_content
    ]

    # Decision logic:
    # 1. If there are adaptive ACTION evidence and no non-adaptive signals -> adaptive
    # 2. If there are only message evidence but actions are non-adaptive -> non-adaptive
    # 3. If current event has non-adaptive signals -> non-adaptive (current action wins)
    # 4. If no evidence at all -> unknown

    has_adaptive_actions = bool(action_evidence)
    has_adaptive_messages = bool(message_evidence)

    if has_adaptive_actions and not non_adaptive_signals:
        # Strong evidence: actual diagnostic/adaptive actions between errors
        confidence = min(1.0, len(action_evidence) * 0.35 + len(message_evidence) * 0.1)
        return {
            "post_error_behavior": "adaptive_recovery",
            "confidence": round(min(confidence, 1.0), 2),
            "evidence": action_evidence + message_evidence,
        }

    if non_adaptive_signals:
        # Current event shows non-adaptive behavior
        confidence = min(1.0, len(non_adaptive_signals) * 0.5)
        evidence = [f"non_adaptive:{t}" for t in non_adaptive_signals]
        if has_adaptive_actions:
            evidence.extend([f"adaptive_ignored:{e}" for e in action_evidence])
        if has_adaptive_messages:
            evidence.extend([f"adaptive_ignored:{e}" for e in message_evidence])
        return {
            "post_error_behavior": "non_adaptive_continuation",
            "confidence": round(confidence, 2),
            "evidence": evidence,
        }

    if has_adaptive_messages and not has_adaptive_actions:
        # Only model messages, no actual adaptive actions.
        # This is weak evidence — the agent may have said "check" but
        # then continued the same failing approach.
        return {
            "post_error_behavior": "unknown",
            "confidence": 0.0,
            "evidence": [f"message_only:{e}" for e in message_evidence],
        }

    return {
        "post_error_behavior": "unknown",
        "confidence": 0.0,
        "evidence": [],
    }


def _settlement_quality_to_outcome(settlement_quality: str) -> str:
    if settlement_quality in {"clean_success", "recovered_success"}:
        return "success"
    if settlement_quality in {"failure_with_signal", "failure_without_signal"}:
        return "failure"
    if settlement_quality == "partial_success":
        return "partial"
    return "unknown"


def validate_intervention_record(intervention: dict[str, Any]) -> list[str]:
    required = {
        "run_id",
        "step_index",
        "policy_id",
        "activation_mode",
        "intervention_text",
        "trigger_evidence",
        "agent_response_to_intervention",
        "post_intervention_actions",
        "final_outcome",
        "settlement_quality",
        "payment_delta_estimate",
        "helpfulness_assessment",
        "assessment_evidence",
    }
    errors = [
        f"missing_required_field:{field}"
        for field in required
        if field not in intervention
    ]
    trigger_evidence = intervention.get("trigger_evidence", {})
    if not isinstance(trigger_evidence, dict):
        errors.append("invalid_trigger_evidence")
        return errors
    for field in REQUIRED_TRIGGER_EVIDENCE:
        if not trigger_evidence.get(field):
            errors.append(f"missing_trigger_evidence:{field}")
    if intervention.get("policy_id") not in VALID_POLICY_IDS:
        errors.append("invalid_policy_id")
    if intervention.get("activation_mode") not in {"guarded", "shadow"}:
        errors.append("invalid_activation_mode")
    if intervention.get("helpfulness_assessment") not in {
        "helpful",
        "harmful",
        "neutral",
        "uncertain",
    }:
        errors.append("invalid_helpfulness_assessment")
    return errors


class GuardedActivationExperiment:
    def __init__(
        self,
        config: GuardedActivationConfig | None = None,
        *,
        run_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.config = config or config_from_env()
        self.run_metadata = run_metadata or {}
        self.events: list[dict[str, Any]] = []
        self.policy_fires: list[dict[str, Any]] = []
        self.interventions: list[dict[str, Any]] = []
        self.suppressions: list[dict[str, Any]] = []
        self._error_events: list[dict[str, Any]] = []
        self._error_fingerprints: set[str] = set()
        self._events_since_first_error: list[dict[str, Any]] = []
        self._first_error_recorded: bool = False
        self._last_strategy_revision_step: int | None = None
        self._task_complete = False
        self._final_answer_emitted = False
        self._errors_resolved = False

    def record_event(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        normalized = normalize_live_run_event(event)
        normalized["settlement_signals"].update(
            infer_settlement_signals(
                normalized.get("content", ""),
                normalized.get("event_type", "model_message"),
            )
        )
        interventions: list[dict[str, Any]] = []
        if self._can_evaluate_before_state(normalized):
            intervention = self._maybe_intervene(normalized)
            if intervention:
                self.interventions.append(intervention)
                self.policy_fires.append(
                    {
                        "run_id": intervention["run_id"],
                        "step_index": intervention["step_index"],
                        "policy_id": self.config.policy_id,
                        "would_fire": True,
                        "activation_mode": intervention["activation_mode"],
                        "activation_status": "guarded_experiment",
                        "trigger_evidence": intervention["trigger_evidence"],
                    }
                )
                interventions.append(intervention)

        self.events.append(normalized)
        self._update_state(normalized)
        return interventions

    def _can_evaluate_before_state(self, event: dict[str, Any]) -> bool:
        if not self.config.activation_enabled:
            return False
        if self.config.mode != "guarded":
            return False
        if self.config.policy_id not in VALID_POLICY_IDS:
            return False
        if len(self.interventions) >= self.config.max_fires_per_run:
            return False
        if self._task_complete or self._final_answer_emitted:
            return False
        if event.get("event_type") in {"task_complete", "final_answer"}:
            return False
        if _is_low_cost_inspection(event):
            return False
        if self._errors_resolved:
            return False
        return True

    def _maybe_intervene(self, event: dict[str, Any]) -> dict[str, Any] | None:
        current_signals = event.get("settlement_signals", {})
        candidate_errors = list(self._error_events)
        if current_signals.get("error_detected") or current_signals.get("test_failed"):
            fingerprint = _fingerprint_error(str(event.get("content", "")))
            if fingerprint in self._error_fingerprints:
                return None
            candidate_errors.append(
                {
                    "step_index": event["step_index"],
                    "content": event.get("content", ""),
                    "fingerprint": fingerprint,
                }
            )

        if len(candidate_errors) < 2:
            return None

        latest_error_step = max(int(item["step_index"]) for item in candidate_errors)
        if (
            self._last_strategy_revision_step is not None
            and self._last_strategy_revision_step > latest_error_step
        ):
            return None

        # Check for adaptive recovery between first error and now
        recovery = detect_adaptive_recovery(self._events_since_first_error, event)
        if recovery["post_error_behavior"] == "adaptive_recovery":
            self.suppressions.append(
                {
                    "run_id": event["run_id"],
                    "step_index": event["step_index"],
                    "policy_id": self.config.policy_id,
                    "suppression_reason": "adaptive_recovery_behavior_detected",
                    "suppression_evidence": recovery["evidence"],
                    "recovery_confidence": recovery["confidence"],
                }
            )
            return None

        trigger_evidence = {
            "error_events": candidate_errors[-3:],
            "continued_same_path_evidence": [
                "multiple_distinct_unresolved_errors_before_revision",
                f"latest_event_type={event.get('event_type')}",
            ],
            "missing_revision_evidence": [
                "no_strategy_revision_after_latest_error",
                f"last_strategy_revision_step={self._last_strategy_revision_step}",
            ],
            "recovery_opportunity_evidence": [
                "run_not_task_complete",
                "final_answer_not_emitted",
            ],
        }
        return {
            "run_id": event["run_id"],
            "step_index": event["step_index"],
            "policy_id": self.config.policy_id,
            "activation_mode": "guarded",
            "intervention_text": GUARDED_INTERVENTION_TEXT,
            "trigger_evidence": trigger_evidence,
            "agent_response_to_intervention": None,
            "post_intervention_actions": [],
            "final_outcome": "unknown",
            "settlement_quality": "unknown",
            "payment_delta_estimate": None,
            "helpfulness_assessment": "uncertain",
            "assessment_evidence": ["replay_mode_no_agent_response_observed"],
        }

    def _update_state(self, event: dict[str, Any]) -> None:
        signals = event.get("settlement_signals", {})
        step = int(event.get("step_index", 0))
        content = str(event.get("content", ""))
        if signals.get("error_detected") or signals.get("test_failed"):
            fingerprint = _fingerprint_error(content)
            if fingerprint not in self._error_fingerprints:
                self._error_fingerprints.add(fingerprint)
                self._error_events.append(
                    {
                        "step_index": step,
                        "content": content,
                        "fingerprint": fingerprint,
                    }
                )
                if not self._first_error_recorded:
                    self._first_error_recorded = True
                    self._events_since_first_error = []
        if signals.get("test_passed") or signals.get("success_signal"):
            self._errors_resolved = True
            self._error_events.clear()
            self._error_fingerprints.clear()
            self._events_since_first_error.clear()
            self._first_error_recorded = False
        if _contains_strategy_revision(content):
            self._last_strategy_revision_step = step
            self._error_events.clear()
            self._error_fingerprints.clear()
            self._events_since_first_error.clear()
            self._first_error_recorded = False
        if event.get("event_type") == "final_answer":
            self._final_answer_emitted = True
        if signals.get("task_complete") or event.get("event_type") == "task_complete":
            self._task_complete = True
        # Track events since first error for adaptive recovery detection
        if self._first_error_recorded:
            self._events_since_first_error.append(event)

    def finalize_run(
        self,
        *,
        final_outcome: str = "unknown",
        settlement_quality: str = "unknown",
    ) -> dict[str, Any]:
        post_intervention_actions = []
        if self.interventions:
            first_step = int(self.interventions[0]["step_index"])
            post_intervention_actions = [
                event
                for event in self.events
                if int(event.get("step_index", 0)) > first_step
                and event.get("event_type") in {"tool_call", "model_message"}
            ]
        for intervention in self.interventions:
            intervention["final_outcome"] = final_outcome
            intervention["settlement_quality"] = settlement_quality
            intervention["post_intervention_actions"] = post_intervention_actions

        return {
            "run_id": self.run_metadata.get("run_id")
            or (self.events[0]["run_id"] if self.events else ""),
            "task_id": self.run_metadata.get("task_id"),
            "domain": self.run_metadata.get("domain", "unknown"),
            "total_steps": len(self.events),
            "final_outcome": final_outcome,
            "settlement_quality": settlement_quality,
            "policy_fires": self.policy_fires,
            "interventions": self.interventions,
            "suppressions": self.suppressions,
            "intervention_count": len(self.interventions),
            "suppression_count": len(self.suppressions),
            "status": "tested_in_replay"
            if self.interventions
            else "needs_more_evidence",
        }


def _group_events_by_run(
    events: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault(str(event.get("run_id", "")), []).append(event)
    for run_events in grouped.values():
        run_events.sort(key=lambda item: int(item.get("step_index", 0)))
    return grouped


def _experiment_summary(
    interventions: list[dict[str, Any]],
    run_summaries: list[dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    policy_id: str = REFINED_POLICY_ID,
) -> dict[str, Any]:
    fires = len(interventions)
    final_steps = {
        (event.get("run_id"), int(event.get("step_index", 0)))
        for event in events
        if event.get("event_type") in {"final_answer", "task_complete"}
    }
    false_positive_count = sum(
        1 for item in interventions if item.get("final_outcome") == "success"
    )
    return {
        "mode": "replay-only",
        "policy_id": policy_id,
        "status": "tested_in_replay" if fires else "needs_more_evidence",
        "runs_evaluated": len(run_summaries),
        "fires": fires,
        "interventions": fires,
        "interventions_completed": sum(
            1 for item in interventions if item.get("agent_response_to_intervention")
        ),
        "post_intervention_recovery_count": sum(
            1
            for item in interventions
            if item.get("agent_response_to_intervention")
            and item.get("final_outcome") == "success"
        ),
        "repeated_error_loop_reduction": None,
        "tool_call_delta": None,
        "error_count_delta": None,
        "settlement_quality_delta": None,
        "false_positive_count": false_positive_count,
        "harmful_intervention_count": 0,
        "uncertain_count": sum(
            1
            for item in interventions
            if item.get("helpfulness_assessment") == "uncertain"
        ),
        "interventions_after_final_settlement": sum(
            1
            for item in interventions
            if (item.get("run_id"), int(item.get("step_index", 0))) in final_steps
        ),
        "payment_cost_observed_or_estimated": None,
        "recommendation": (
            "ready_for_live_guarded_runs"
            if fires
            else "needs_more_replay_or_trace_evidence"
        ),
        "metabolized": False,
        "globally_active": False,
    }


def replay_guarded_activation(
    events: list[dict[str, Any]],
    *,
    output_dir: str | Path,
    config: GuardedActivationConfig | None = None,
    baseline_summaries: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Path]:
    cfg = config or GuardedActivationConfig(
        activation_enabled=True,
        mode="guarded",
    )
    all_policy_fires: list[dict[str, Any]] = []
    all_interventions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []

    grouped = _group_events_by_run(events)
    baseline_summaries = baseline_summaries or {}
    for run_index, (run_id, run_events) in enumerate(grouped.items()):
        if run_index >= cfg.max_experiment_runs:
            break
        experiment = GuardedActivationExperiment(
            cfg,
            run_metadata={"run_id": run_id, "task_id": run_id},
        )
        for event in run_events:
            experiment.record_event(event)
        baseline = baseline_summaries.get(run_id, {})
        summary = experiment.finalize_run(
            final_outcome=baseline.get("final_outcome", "unknown"),
            settlement_quality=baseline.get("settlement_quality", "unknown"),
        )
        all_policy_fires.extend(experiment.policy_fires)
        all_interventions.extend(experiment.interventions)
        run_summaries.append(summary)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "events": output / "events.jsonl",
        "policy_fires": output / "policy_fires.jsonl",
        "interventions": output / "interventions.jsonl",
        "run_summaries": output / "run_summaries.jsonl",
        "experiment_summary": output / "experiment_summary.json",
    }
    write_records_jsonl(events, paths["events"])
    write_records_jsonl(all_policy_fires, paths["policy_fires"])
    write_records_jsonl(all_interventions, paths["interventions"])
    write_records_jsonl(run_summaries, paths["run_summaries"])
    paths["experiment_summary"].write_text(
        json.dumps(
            _experiment_summary(
                all_interventions, run_summaries, events, policy_id=cfg.policy_id
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay guarded activation over live shadow events"
    )
    parser.add_argument(
        "--input",
        default="data/settlement_datasets/live_shadow/events.jsonl",
    )
    parser.add_argument(
        "--output",
        default="data/settlement_datasets/live_activation_experiment",
    )
    parser.add_argument(
        "--run-summaries",
        default="data/settlement_datasets/live_shadow/run_summaries.jsonl",
        help="Optional live shadow run summaries to copy final outcome into interventions.",
    )
    parser.add_argument("--max-runs", type=int, default=None)
    args = parser.parse_args()

    config = GuardedActivationConfig(
        activation_enabled=True,
        mode="guarded",
        max_experiment_runs=args.max_runs
        or GuardedActivationConfig().max_experiment_runs,
    )
    baseline_summaries: dict[str, dict[str, Any]] = {}
    summary_path = Path(args.run_summaries)
    if summary_path.exists():
        baseline_summaries = {
            str(item.get("run_id", "")): item
            for item in read_records_jsonl(summary_path)
        }

    paths = replay_guarded_activation(
        read_records_jsonl(args.input),
        output_dir=args.output,
        config=config,
        baseline_summaries=baseline_summaries,
    )
    print(f"Wrote guarded activation events -> {paths['events']}")
    print(f"Wrote guarded activation fires -> {paths['policy_fires']}")
    print(f"Wrote guarded activation interventions -> {paths['interventions']}")
    print(f"Wrote guarded activation run summaries -> {paths['run_summaries']}")
    print(f"Wrote guarded activation summary -> {paths['experiment_summary']}")


if __name__ == "__main__":
    main()
