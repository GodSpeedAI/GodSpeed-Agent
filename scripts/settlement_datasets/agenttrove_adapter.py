from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from scripts.agenttrove.label_settlements import (
    classify_desired_direction,
    classify_path_shape,
    classify_settlement_quality,
    detect_failure_modes,
    detect_harness_policy_signal,
    detect_metabolization_candidate,
    estimate_payment_complexity,
    label_trace,
    load_rules,
)
from scripts.agenttrove.parsing import (
    count_json_commands,
    detect_structural_errors,
    detect_task_complete,
    extract_user_task_content,
    infer_settlement_from_structure,
    is_system_prompt_boilerplate,
    parse_assistant_content,
)
from scripts.agenttrove.profile_traces import profile_trace
from scripts.settlement_datasets.adapter_base import (
    EMPTY_LABELS,
    EMPTY_OUTCOME,
    SettlementDatasetAdapter,
    make_empty_environment,
    make_empty_payment,
    make_empty_representational_state,
)

_DEFAULT_INPUT_PATH = "data/agenttrove/raw_samples/sample.jsonl"
_RULES_PATH = "configs/agenttrove/settlement_label_rules.yaml"


class AgentTroveAdapter(SettlementDatasetAdapter):
    name = "agenttrove"
    domain = "code"
    source_uri = "open-thoughts/AgentTrove"

    def stream(
        self, limit: int | None = None, **kwargs: Any
    ) -> Iterator[dict[str, Any]]:
        input_path = Path(kwargs.get("input_path", _DEFAULT_INPUT_PATH))
        if not input_path.exists():
            return
        count = 0
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                yield json.loads(line)
                count += 1
                if limit is not None and count >= limit:
                    return

    def normalize_task(self, raw: dict[str, Any]) -> dict[str, Any]:
        messages = raw.get("messages", [])
        rules = load_rules(_RULES_PATH)
        return classify_desired_direction(messages, rules)

    def extract_actions(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        messages = raw.get("messages", [])
        actions: list[dict[str, Any]] = []
        for i, msg in enumerate(messages):
            if msg.get("role") != "assistant":
                continue
            parsed = parse_assistant_content(msg.get("content", ""))
            if parsed["parsed"]:
                if parsed.get("actions"):
                    for act in parsed["actions"]:
                        actions.append(
                            {
                                "turn_index": i,
                                "role": "assistant",
                                "action_type": act.get("action_type", "text"),
                                "source": act.get("source", "assistant_json"),
                                "content": act.get("content", ""),
                            }
                        )
                if parsed.get("commands"):
                    for cmd in parsed["commands"]:
                        actions.append(
                            {
                                "turn_index": i,
                                "role": "assistant",
                                "action_type": "command",
                                "source": "assistant_json",
                                "content": cmd.get("content", ""),
                            }
                        )
            else:
                actions.append(
                    {
                        "turn_index": i,
                        "role": "assistant",
                        "action_type": "text",
                        "source": parsed.get("source", "regex_fallback"),
                        "content": msg.get("content", "")[:200],
                    }
                )
        return actions

    def extract_observations(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        messages = raw.get("messages", [])
        observations: list[dict[str, Any]] = []
        for i, msg in enumerate(messages):
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            if (
                "New Terminal Output:" in content
                or "terminal output" in content.lower()
            ):
                observations.append(
                    {
                        "turn_index": i,
                        "role": "user",
                        "content": content,
                    }
                )
        return observations

    def extract_outcome(self, raw: dict[str, Any]) -> dict[str, Any]:
        profile = profile_trace(raw)
        settlement = classify_settlement_quality(raw, profile)
        success = None
        quality = settlement.get("settlement_quality", "unknown")
        if quality in (
            "clean_success",
            "recovered_success",
            "partial_success",
            "brittle_success",
        ):
            success = True
        elif quality in ("failure_with_signal", "failure_without_signal"):
            success = False
        return {
            "success": success,
            "reward": raw.get("reward"),
            "score": None,
            "settlement_quality": quality,
            "confidence": settlement.get("confidence", 0.0),
            "evidence": settlement.get("evidence", []),
        }

    def extract_payment(self, raw: dict[str, Any]) -> dict[str, Any]:
        profile = profile_trace(raw)
        rules = load_rules(_RULES_PATH)
        messages = raw.get("messages", [])
        turn_count = profile.get("turn_count", 0)
        error_count = profile.get("error_like_output_count", 0)
        json_cmd = profile.get("json_command_count", 0)
        total_commands = profile.get("command_like_action_count", 0)
        return {
            "turns": turn_count,
            "tool_calls": profile.get("tool_turn_count", 0),
            "commands": total_commands,
            "page_actions": 0,
            "api_calls": 0,
            "elapsed_steps": turn_count,
            "error_count": error_count,
            "estimated_complexity": estimate_payment_complexity(profile, rules),
            "evidence": [
                f"json_command_count:{json_cmd}",
                f"total_commands:{total_commands}",
                f"error_count:{error_count}",
                f"turn_count:{turn_count}",
            ],
        }

    def infer_settlement_quality(
        self, raw: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        profile = profile_trace(raw)
        messages = raw.get("messages", [])
        return infer_settlement_from_structure(messages, profile)

    def to_settlement_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        messages = raw.get("messages", [])
        profile = profile_trace(raw)
        rules = load_rules(_RULES_PATH)
        settlement_label = label_trace(raw, profile, rules)

        desired_direction = settlement_label.get(
            "desired_direction",
            classify_desired_direction(messages, rules),
        )

        repr_state_raw = classify_path_shape(messages, profile)
        representational_state = {
            "start": repr_state_raw.get("start", "unknown"),
            "desired": repr_state_raw.get("desired", "unknown"),
            "path_shape": repr_state_raw.get("path_shape", "unknown"),
            "confidence": profile.get("turn_count", 0) / 20.0
            if profile.get("turn_count", 0) > 0
            else 0.0,
            "evidence": [
                f"path_shape:{repr_state_raw.get('path_shape', 'unknown')}",
                f"assistant_turns:{profile.get('assistant_turn_count', 0)}",
                f"command_count:{profile.get('command_like_action_count', 0)}",
            ],
        }

        has_terminal_output = any(
            "New Terminal Output:" in m.get("content", "")
            for m in messages
            if m.get("role") == "user"
        )
        if has_terminal_output:
            environment = {
                "type": "simulated_terminal",
                "has_runnable_feedback": True,
                "feedback_type": "tool_output",
            }
        else:
            environment = make_empty_environment()

        at_payment = settlement_label.get("payment", {})
        payment = {
            "turns": at_payment.get("turn_count", 0),
            "tool_calls": at_payment.get("tool_call_count", 0),
            "commands": at_payment.get("command_count", 0),
            "page_actions": 0,
            "api_calls": 0,
            "elapsed_steps": at_payment.get("turn_count", 0),
            "error_count": at_payment.get("error_count", 0),
            "estimated_complexity": at_payment.get("estimated_complexity", "unknown"),
            "evidence": [
                f"json_command_count:{at_payment.get('json_command_count', 0)}",
                f"recovery_attempt_count:{at_payment.get('recovery_attempt_count', 0)}",
            ],
        }

        affordance_path = settlement_label.get("affordance_path", {})

        at_outcome = settlement_label.get("outcome", {})
        settlement_quality = at_outcome.get("settlement_quality", "unknown")
        success = None
        if settlement_quality in (
            "clean_success",
            "recovered_success",
            "partial_success",
            "brittle_success",
        ):
            success = True
        elif settlement_quality in ("failure_with_signal", "failure_without_signal"):
            success = False
        outcome = {
            "success": success,
            "reward": at_outcome.get("reward"),
            "score": None,
            "settlement_quality": settlement_quality,
            "confidence": at_outcome.get("confidence", 0.0),
            "evidence": settlement_label.get("label_evidence", {}).get(
                "settlement_quality", []
            ),
        }

        cognitive_os_labels = settlement_label.get("cognitive_os_labels", {})
        label_evidence = settlement_label.get("label_evidence", {})

        failure_mode = cognitive_os_labels.get("failure_mode")
        if isinstance(failure_mode, list):
            failure_mode = failure_mode[0] if failure_mode else None
        fm_confidence = (
            outcome["confidence"] if failure_mode and failure_mode != "unknown" else 0.0
        )
        fm_evidence = label_evidence.get("failure_mode", [])
        if isinstance(fm_evidence, str):
            fm_evidence = [fm_evidence]

        harness_signal = cognitive_os_labels.get("harness_policy_signal")
        hs_confidence = 0.85 if harness_signal else 0.0
        hs_evidence: list[str] = []
        if harness_signal:
            hs_evidence = [f"policy_signal:{harness_signal}"]

        metabolization = cognitive_os_labels.get("metabolization_candidate")
        meta_confidence = 0.8 if metabolization else 0.0
        meta_evidence: list[str] = []
        if metabolization:
            meta_evidence = [f"metabolization_pattern:{metabolization}"]

        labels = {
            "failure_mode": failure_mode,
            "failure_mode_confidence": fm_confidence,
            "failure_mode_evidence": fm_evidence,
            "harness_policy_signal": harness_signal,
            "harness_policy_signal_confidence": hs_confidence,
            "harness_policy_signal_evidence": hs_evidence,
            "metabolization_candidate": metabolization,
            "metabolization_candidate_confidence": meta_confidence,
            "metabolization_candidate_evidence": meta_evidence,
        }

        metadata = {
            "teacher": raw.get("teacher", ""),
            "source": raw.get("source", ""),
            "reward": raw.get("reward"),
            "trace_id": raw.get("trace_id", ""),
        }

        return {
            "dataset": "agenttrove",
            "domain": "code",
            "task_id": raw.get("task_id") or raw.get("trace_id", ""),
            "source_uri": "open-thoughts/AgentTrove",
            "desired_direction": desired_direction,
            "environment": environment,
            "representational_state": representational_state,
            "payment": payment,
            "affordance_path": affordance_path,
            "outcome": outcome,
            "labels": labels,
            "metadata": metadata,
        }

    def validate_record(self, record: dict[str, Any]) -> list[str]:
        errors = super().validate_record(record)

        task_id = record.get("task_id", "")
        if not task_id:
            errors.append("agenttrove_missing_task_id")

        metadata = record.get("metadata", {})
        if "trace_id" not in metadata:
            errors.append("agenttrove_missing_trace_id_in_metadata")

        env = record.get("environment", {})
        env_type = env.get("type", "")
        if env_type not in ("simulated_terminal", "unknown"):
            errors.append(f"agenttrove_unexpected_environment_type:{env_type}")

        return errors
