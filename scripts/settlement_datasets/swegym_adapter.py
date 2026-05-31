from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from scripts.settlement_datasets.adapter_base import (
    EMPTY_LABELS,
    EMPTY_OUTCOME,
    SettlementDatasetAdapter,
    make_empty_environment,
    make_empty_payment,
    make_empty_representational_state,
)


class SWEGymAdapter(SettlementDatasetAdapter):
    name = "swegym"
    domain = "code"
    source_uri = "fixture:swegym_style"

    _DEFAULT_FIXTURE_PATH = (
        Path(__file__).resolve().parent.parent.parent
        / "tests"
        / "fixtures"
        / "settlement_datasets"
        / "swegym"
        / "sample.jsonl"
    )

    def stream(
        self, limit: int | None = None, **kwargs: Any
    ) -> Iterator[dict[str, Any]]:
        input_path = kwargs.get("input_path", str(self._DEFAULT_FIXTURE_PATH))
        yielded = 0
        with Path(input_path).open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)
                    yielded += 1
                    if limit is not None and yielded >= limit:
                        break

    def normalize_task(self, raw: dict[str, Any]) -> dict[str, Any]:
        title = raw.get("issue_title", "")
        body = raw.get("issue_body", "")
        description = f"{title}"
        if body:
            description = f"{title}: {body[:200]}"
        return {
            "type": "implementation",
            "description": description,
            "settlement_target": "pass_all_tests",
        }

    def extract_actions(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        trajectory = raw.get("trajectory", [])
        for idx, entry in enumerate(trajectory):
            role = entry.get("role", "")
            action_type = entry.get("action_type", "")
            if role == "assistant" and action_type in ("command", "analysis"):
                actions.append(
                    {
                        "turn_index": idx,
                        "role": role,
                        "action_type": action_type,
                        "content": entry.get("content", ""),
                    }
                )
        return actions

    def extract_observations(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        trajectory = raw.get("trajectory", [])
        for idx, entry in enumerate(trajectory):
            if entry.get("role") == "tool":
                observations.append(
                    {
                        "turn_index": idx,
                        "role": "tool",
                        "content": entry.get("content", ""),
                    }
                )
        return observations

    def extract_outcome(self, raw: dict[str, Any]) -> dict[str, Any]:
        test_result = raw.get("test_result", {})
        resolved = test_result.get("resolved", False)
        failed_tests = test_result.get("failed_tests", [])
        passed_tests = test_result.get("passed_tests", [])

        evidence: list[str] = []
        if resolved:
            evidence.append("test_result.resolved=true")
        else:
            evidence.append("test_result.resolved=false")
        if failed_tests:
            evidence.append(f"failed_tests={json.dumps(failed_tests)}")
        if passed_tests:
            evidence.append(f"passed_count={len(passed_tests)}")

        extracted = self._pre_extract(raw)
        quality = self.infer_settlement_quality(raw, extracted)

        return {
            "success": resolved,
            "reward": 1.0 if resolved else 0.0,
            "score": len(passed_tests) / max(len(passed_tests) + len(failed_tests), 1),
            "settlement_quality": quality["settlement_quality"],
            "confidence": quality["confidence"],
            "evidence": evidence,
        }

    def extract_payment(self, raw: dict[str, Any]) -> dict[str, Any]:
        trajectory = raw.get("trajectory", [])
        commands = 0
        analyses = 0
        tool_responses = 0
        errors = 0

        for entry in trajectory:
            role = entry.get("role", "")
            action_type = entry.get("action_type", "")
            if role == "assistant" and action_type == "command":
                commands += 1
            elif role == "assistant" and action_type == "analysis":
                analyses += 1
            elif role == "tool":
                tool_responses += 1
                content = entry.get("content", "").lower()
                if any(
                    kw in content
                    for kw in ("error", "failed", "traceback", "exception")
                ):
                    errors += 1

        total_turns = len(trajectory)
        if total_turns <= 4:
            complexity = "low"
        elif total_turns <= 10:
            complexity = "medium"
        else:
            complexity = "high"

        return {
            "turns": total_turns,
            "tool_calls": tool_responses,
            "commands": commands,
            "page_actions": 0,
            "api_calls": 0,
            "elapsed_steps": total_turns,
            "error_count": errors,
            "estimated_complexity": complexity,
            "evidence": [
                f"commands={commands}",
                f"analyses={analyses}",
                f"tool_responses={tool_responses}",
                f"errors={errors}",
            ],
        }

    def infer_settlement_quality(
        self, raw: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        test_result = raw.get("test_result", {})
        resolved = test_result.get("resolved", False)
        trajectory = raw.get("trajectory", [])

        error_count = sum(
            1
            for e in trajectory
            if e.get("role") == "tool"
            and any(
                kw in e.get("content", "").lower()
                for kw in ("error", "failed", "traceback", "exception")
            )
        )

        command_indices = [
            i
            for i, e in enumerate(trajectory)
            if e.get("role") == "assistant" and e.get("action_type") == "command"
        ]
        retries = 0
        for ci in command_indices:
            if ci + 1 < len(trajectory):
                obs = trajectory[ci + 1].get("content", "").lower()
                if any(kw in obs for kw in ("failed", "error", "traceback")):
                    retries += 1

        has_test_output = bool(
            test_result.get("passed_tests") or test_result.get("failed_tests")
        )

        if resolved and error_count == 0:
            return {"settlement_quality": "clean_success", "confidence": 0.9}
        elif resolved and error_count > 0 and retries <= 2:
            return {"settlement_quality": "recovered_success", "confidence": 0.8}
        elif resolved and retries > 2:
            return {"settlement_quality": "brittle_success", "confidence": 0.6}
        elif not resolved and has_test_output:
            return {"settlement_quality": "failure_with_signal", "confidence": 0.7}
        elif not resolved and not has_test_output:
            return {"settlement_quality": "failure_without_signal", "confidence": 0.3}
        else:
            return {"settlement_quality": "unknown", "confidence": 0.1}

    def _pre_extract(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "payment": self.extract_payment(raw),
            "outcome_base": {
                "resolved": raw.get("test_result", {}).get("resolved", False),
            },
        }

    def _infer_representational_state(self, raw: dict[str, Any]) -> dict[str, Any]:
        trajectory = raw.get("trajectory", [])
        if not trajectory:
            return make_empty_representational_state()

        first_assistant_idx = None
        first_command_idx = None
        first_analysis_idx = None
        command_sequence: list[int] = []

        for idx, entry in enumerate(trajectory):
            if entry.get("role") == "assistant":
                if first_assistant_idx is None:
                    first_assistant_idx = idx
                action_type = entry.get("action_type", "")
                if action_type == "analysis" and first_analysis_idx is None:
                    first_analysis_idx = idx
                if action_type == "command" and first_command_idx is None:
                    first_command_idx = idx
                if action_type == "command":
                    command_sequence.append(idx)

        edits_repeated = False
        for i in range(len(command_sequence) - 1):
            if command_sequence[i + 1] - command_sequence[i] <= 2:
                edits_repeated = True
                break

        has_loops = False
        if edits_repeated and len(command_sequence) >= 3:
            has_loops = True

        if first_analysis_idx is not None and first_command_idx is not None:
            if first_analysis_idx < first_command_idx:
                return {
                    "start": "general",
                    "desired": "specific_concrete",
                    "path_shape": "GA_to_GC_to_SC",
                    "confidence": 0.7,
                    "evidence": [
                        f"analysis_at={first_analysis_idx}",
                        f"first_command_at={first_command_idx}",
                        "analysis_precedes_command",
                    ],
                }

        if first_analysis_idx is None and first_command_idx is not None:
            return {
                "start": "specific_concrete",
                "desired": "specific_concrete",
                "path_shape": "direct_jump",
                "confidence": 0.6,
                "evidence": [
                    "no_analysis_before_command",
                    f"first_command_at={first_command_idx}",
                ],
            }

        if has_loops:
            return {
                "start": "specific_concrete",
                "desired": "specific_concrete",
                "path_shape": "thrash",
                "confidence": 0.7,
                "evidence": [
                    f"command_count={len(command_sequence)}",
                    "repeated_edit_pattern",
                ],
            }

        return {
            "start": "unknown",
            "desired": "specific_concrete",
            "path_shape": "unknown",
            "confidence": 0.3,
            "evidence": [f"trajectory_length={len(trajectory)}"],
        }

    def _infer_labels(
        self, raw: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        trajectory = raw.get("trajectory", [])
        test_result = raw.get("test_result", {})
        resolved = test_result.get("resolved", False)

        failure_mode = None
        failure_mode_confidence = 0.0
        failure_mode_evidence: list[str] = []

        commands = [
            e
            for e in trajectory
            if e.get("role") == "assistant" and e.get("action_type") == "command"
        ]
        command_contents = [c.get("content", "") for c in commands]
        first_edit_idx = None
        for i, content in enumerate(command_contents):
            if any(kw in content for kw in ("sed", "edit", "patch", "cat")):
                first_edit_idx = i
                break

        if first_edit_idx is not None and first_edit_idx > 0:
            failure_mode = "poor_localization"
            failure_mode_confidence = 0.6
            failure_mode_evidence.append(f"first_file_op_at_command={first_edit_idx}")

        if not resolved:
            failed_tests = test_result.get("failed_tests", [])
            if failed_tests:
                if failure_mode is None:
                    failure_mode = "test_failure"
                    failure_mode_confidence = 0.8
                failure_mode_evidence.append(f"failed_test_count={len(failed_tests)}")

            if not failed_tests and not test_result.get("passed_tests", []):
                if failure_mode is None:
                    failure_mode = "bad_patch"
                    failure_mode_confidence = 0.5
                failure_mode_evidence.append("no_test_results")

        harness_policy_signal = None
        harness_policy_signal_confidence = 0.0
        harness_policy_signal_evidence: list[str] = []

        payment = extracted.get("payment", {})
        if payment.get("error_count", 0) > 3:
            harness_policy_signal = "retry_limit"
            harness_policy_signal_confidence = 0.7
            harness_policy_signal_evidence.append(
                f"error_count={payment['error_count']}"
            )

        if not resolved and len(trajectory) < 4:
            harness_policy_signal = "premature_closure"
            harness_policy_signal_confidence = 0.8
            harness_policy_signal_evidence.append(
                f"trajectory_length={len(trajectory)}"
            )

        metabolization_candidate = None
        metabolization_candidate_confidence = 0.0
        metabolization_candidate_evidence: list[str] = []

        if resolved:
            metabolization_candidate = "yes"
            metabolization_candidate_confidence = 0.8
            metabolization_candidate_evidence.append("resolved=true")
            if payment.get("error_count", 0) == 0:
                metabolization_candidate_confidence = 0.9
                metabolization_candidate_evidence.append("zero_errors")
        elif failure_mode == "poor_localization":
            metabolization_candidate = "partial"
            metabolization_candidate_confidence = 0.4
            metabolization_candidate_evidence.append("localization_needed")

        return {
            "failure_mode": failure_mode,
            "failure_mode_confidence": failure_mode_confidence,
            "failure_mode_evidence": failure_mode_evidence,
            "harness_policy_signal": harness_policy_signal,
            "harness_policy_signal_confidence": harness_policy_signal_confidence,
            "harness_policy_signal_evidence": harness_policy_signal_evidence,
            "metabolization_candidate": metabolization_candidate,
            "metabolization_candidate_confidence": metabolization_candidate_confidence,
            "metabolization_candidate_evidence": metabolization_candidate_evidence,
        }

    def to_settlement_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        payment = self.extract_payment(raw)
        extracted = {"payment": payment}
        outcome = self.extract_outcome(raw)
        quality = self.infer_settlement_quality(raw, extracted)

        task = self.normalize_task(raw)
        actions = self.extract_actions(raw)
        observations = self.extract_observations(raw)
        rep_state = self._infer_representational_state(raw)
        labels = self._infer_labels(raw, extracted)

        metadata = raw.get("metadata", {})
        metadata["repo"] = raw.get("repo", "")
        if "instance_id" not in metadata:
            metadata["instance_id"] = raw.get("task_id", "")
        if "version" not in metadata:
            metadata["version"] = "1.0"

        return {
            "dataset": self.name,
            "domain": self.domain,
            "task_id": raw.get("task_id", ""),
            "source_uri": self.source_uri,
            "desired_direction": task,
            "environment": {
                "type": "code_repository",
                "has_runnable_feedback": True,
                "feedback_type": "tests",
            },
            "representational_state": rep_state,
            "payment": payment,
            "affordance_path": {
                "actions": actions,
                "observations": observations,
                "recovery_events": [],
            },
            "outcome": {
                "success": outcome["success"],
                "reward": outcome["reward"],
                "score": outcome["score"],
                "settlement_quality": quality["settlement_quality"],
                "confidence": quality["confidence"],
                "evidence": outcome["evidence"],
            },
            "labels": labels,
            "metadata": metadata,
        }

    def validate_record(self, record: dict[str, Any]) -> list[str]:
        errors = super().validate_record(record)
        if record.get("domain") != "code":
            errors.append("invalid_domain:expected_code")
        return errors
