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

_DEFAULT_FIXTURE_PATH = Path("tests/fixtures/settlement_datasets/apibank/sample.jsonl")


class APIBankAdapter(SettlementDatasetAdapter):
    name = "apibank"
    domain = "api"
    source_uri = "fixture:apibank_style"

    def stream(
        self, limit: int | None = None, **kwargs: Any
    ) -> Iterator[dict[str, Any]]:
        input_path = Path(kwargs.get("input_path", _DEFAULT_FIXTURE_PATH))
        with input_path.open("r", encoding="utf-8") as f:
            count = 0
            for line in f:
                if line.strip():
                    yield json.loads(line)
                    count += 1
                    if limit is not None and count >= limit:
                        return

    def normalize_task(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "action",
            "description": raw.get("instruction", ""),
            "settlement_target": "complete_all_api_calls_correctly",
        }

    def extract_actions(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        for idx, entry in enumerate(raw.get("trajectory", [])):
            at = entry.get("action_type", "")
            if at in ("api_call", "analysis"):
                action: dict[str, Any] = {
                    "turn_index": idx,
                    "role": entry.get("role", ""),
                    "action_type": at,
                    "content": entry.get("content", ""),
                }
                if at == "api_call":
                    action["tool_name"] = entry.get("tool_name", "")
                    action["arguments"] = entry.get("arguments", {})
                actions.append(action)
        return actions

    def extract_observations(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        for idx, entry in enumerate(raw.get("trajectory", [])):
            if entry.get("action_type") == "api_response":
                observations.append(
                    {
                        "turn_index": idx,
                        "role": entry.get("role", ""),
                        "content": entry.get("content", ""),
                    }
                )
        return observations

    def extract_outcome(self, raw: dict[str, Any]) -> dict[str, Any]:
        reward = raw.get("reward", 0.0)
        expected_calls = raw.get("expected_calls", [])
        trajectory = raw.get("trajectory", [])

        actual_calls: list[str] = []
        for entry in trajectory:
            if entry.get("action_type") == "api_call":
                tool = entry.get("tool_name", "")
                if tool:
                    actual_calls.append(tool)

        calls_matched = 0
        remaining_expected = list(expected_calls)
        for call in actual_calls:
            if call in remaining_expected:
                calls_matched += 1
                remaining_expected.remove(call)

        all_expected_made = len(remaining_expected) == 0
        success = reward == 1.0 and all_expected_made

        if reward == 1.0 and all_expected_made:
            score = 1.0
        elif reward == 1.0 and not all_expected_made:
            score = 0.7
        elif calls_matched > 0:
            score = calls_matched / max(len(expected_calls), 1) * 0.6
        else:
            score = 0.0

        evidence: list[str] = []
        if actual_calls:
            evidence.append(f"actual_calls:{','.join(actual_calls)}")
        if expected_calls:
            evidence.append(f"expected_calls:{','.join(expected_calls)}")
        if remaining_expected:
            evidence.append(f"missing_calls:{','.join(remaining_expected)}")

        return {
            "success": success,
            "reward": reward,
            "score": round(score, 3),
            "settlement_quality": "clean_success" if success else "failure",
            "confidence": 1.0 if reward in (0.0, 1.0) else 0.5,
            "evidence": evidence,
        }

    def extract_payment(self, raw: dict[str, Any]) -> dict[str, Any]:
        trajectory = raw.get("trajectory", [])
        api_call_count = 0
        analysis_count = 0
        error_count = 0

        for entry in trajectory:
            at = entry.get("action_type", "")
            if at == "api_call":
                api_call_count += 1
            elif at == "analysis":
                analysis_count += 1
            elif at == "api_response":
                content = entry.get("content", "")
                try:
                    resp = json.loads(content)
                    if isinstance(resp, dict) and resp.get("status") == "error":
                        error_count += 1
                except (json.JSONDecodeError, TypeError):
                    pass

        total_steps = len(trajectory)

        if api_call_count <= 1 and total_steps <= 3:
            complexity = "simple"
        elif api_call_count <= 3 and total_steps <= 10:
            complexity = "moderate"
        else:
            complexity = "complex"

        return {
            "turns": total_steps,
            "tool_calls": api_call_count,
            "commands": 0,
            "page_actions": 0,
            "api_calls": api_call_count,
            "elapsed_steps": total_steps,
            "error_count": error_count,
            "estimated_complexity": complexity,
            "evidence": [
                f"api_calls:{api_call_count}",
                f"analysis_steps:{analysis_count}",
                f"total_steps:{total_steps}",
            ],
        }

    def infer_settlement_quality(
        self, raw: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        reward = raw.get("reward", 0.0)
        trajectory = raw.get("trajectory", [])
        expected_calls = raw.get("expected_calls", [])

        actual_calls: list[str] = [
            e.get("tool_name", "")
            for e in trajectory
            if e.get("action_type") == "api_call"
        ]

        has_errors = False
        retry_count = 0
        seen_tools: list[str] = []
        for entry in trajectory:
            if entry.get("action_type") == "api_response":
                content = entry.get("content", "")
                try:
                    resp = json.loads(content)
                    if isinstance(resp, dict) and resp.get("status") == "error":
                        has_errors = True
                except (json.JSONDecodeError, TypeError):
                    pass
            elif entry.get("action_type") == "api_call":
                tool = entry.get("tool_name", "")
                if tool in seen_tools:
                    retry_count += 1
                seen_tools.append(tool)

        calls_matched = sum(1 for c in actual_calls if c in expected_calls)
        all_matched = set(expected_calls).issubset(set(actual_calls))

        if reward == 1.0 and not has_errors and retry_count == 0:
            quality, confidence = "clean_success", 0.9
        elif reward == 1.0 and (has_errors or retry_count > 0):
            quality, confidence = "recovered_success", 0.8
        elif calls_matched > 0 and not all_matched:
            quality, confidence = "partial_success", 0.6
        elif reward == 0.0 and actual_calls and not all_matched:
            quality, confidence = "failure_with_signal", 0.7
        elif reward == 0.0 and not actual_calls:
            quality, confidence = "failure_without_signal", 0.3
        else:
            quality, confidence = "unknown", 0.1

        return {
            "settlement_quality": quality,
            "confidence": confidence,
        }

    def to_settlement_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        task = self.normalize_task(raw)
        payment = self.extract_payment(raw)
        outcome = self.extract_outcome(raw)
        actions = self.extract_actions(raw)
        observations = self.extract_observations(raw)

        extracted = {
            "actions": actions,
            "observations": observations,
            "outcome": outcome,
        }
        quality_info = self.infer_settlement_quality(raw, extracted)
        outcome["settlement_quality"] = quality_info["settlement_quality"]
        outcome["confidence"] = quality_info["confidence"]

        trajectory = raw.get("trajectory", [])
        available_apis = [a["name"] for a in raw.get("available_apis", [])]
        expected_calls = raw.get("expected_calls", [])

        api_call_entries = [e for e in trajectory if e.get("action_type") == "api_call"]

        rep_state = make_empty_representational_state()
        if len(api_call_entries) <= 1:
            rep_state["start"] = "direct_action_with_feedback"
            rep_state["desired"] = "single_api_call_completion"
            rep_state["path_shape"] = "direct"
        else:
            analysis_entries = [
                e for e in trajectory if e.get("action_type") == "analysis"
            ]
            if analysis_entries:
                rep_state["start"] = "GA_to_SA_to_SC"
                rep_state["desired"] = "multi_step_api_completion"
                rep_state["path_shape"] = "sequential_with_analysis"
            else:
                rep_state["start"] = "sequential_api_calls"
                rep_state["desired"] = "multi_step_api_completion"
                rep_state["path_shape"] = "sequential"
        rep_state["confidence"] = 0.8
        rep_state["evidence"] = [
            f"api_call_count:{len(api_call_entries)}",
            f"expected_call_count:{len(expected_calls)}",
        ]

        labels: dict[str, Any] = {
            "failure_mode": None,
            "failure_mode_confidence": 0.0,
            "failure_mode_evidence": [],
            "harness_policy_signal": None,
            "harness_policy_signal_confidence": 0.0,
            "harness_policy_signal_evidence": [],
            "metabolization_candidate": None,
            "metabolization_candidate_confidence": 0.0,
            "metabolization_candidate_evidence": [],
        }

        if not outcome.get("success", False):
            fm, fm_conf, fm_ev = self._infer_failure_mode(
                raw, api_call_entries, available_apis, expected_calls
            )
            labels["failure_mode"] = fm
            labels["failure_mode_confidence"] = fm_conf
            labels["failure_mode_evidence"] = fm_ev
        else:
            meta_candidates = self._infer_metabolization_candidates(raw)
            labels["metabolization_candidate"] = (
                meta_candidates[0] if meta_candidates else None
            )
            labels["metabolization_candidate_confidence"] = (
                0.7 if meta_candidates else 0.0
            )
            labels["metabolization_candidate_evidence"] = [
                f"candidate_count:{len(meta_candidates)}"
            ]

        environment = make_empty_environment()
        environment["type"] = "api_sandbox"
        environment["has_runnable_feedback"] = True
        environment["feedback_type"] = "tool_output"

        metadata = {
            "difficulty": raw.get("metadata", {}).get("difficulty", "unknown"),
            "available_api_count": len(available_apis),
            "expected_call_count": len(expected_calls),
        }

        record = {
            "dataset": "apibank",
            "domain": "api",
            "task_id": raw.get("task_id", ""),
            "source_uri": self.source_uri,
            "desired_direction": task,
            "environment": environment,
            "representational_state": rep_state,
            "payment": payment,
            "affordance_path": {
                "type": "api_call_sequence",
                "tools_available": available_apis,
                "tools_used": [e.get("tool_name", "") for e in api_call_entries],
                "tools_expected": expected_calls,
            },
            "outcome": outcome,
            "labels": labels,
            "metadata": metadata,
        }
        return record

    def validate_record(self, record: dict[str, Any]) -> list[str]:
        errors = super().validate_record(record)
        if record.get("domain") != "api":
            errors.append("domain_mismatch:expected_api")
        return errors

    def _infer_failure_mode(
        self,
        raw: dict[str, Any],
        api_call_entries: list[dict[str, Any]],
        available_apis: list[str],
        expected_calls: list[str],
    ) -> tuple[str | None, float, list[str]]:
        if not api_call_entries:
            return "failure_without_signal", 0.5, ["no_api_calls_made"]

        tools_used = [e.get("tool_name", "") for e in api_call_entries]
        evidence: list[str] = []
        failure_mode = None
        confidence = 0.0

        expected_set = set(expected_calls)
        actual_set = set(tools_used)

        for tool in tools_used:
            if available_apis and tool not in available_apis:
                evidence.append(f"tool_not_in_available:{tool}")
                failure_mode = "wrong_tool"
                confidence = 0.85

        if (
            failure_mode is None
            and expected_set
            and not actual_set.intersection(expected_set)
        ):
            wrong_tools = actual_set - expected_set
            evidence.append(f"tools_not_in_expected:{','.join(wrong_tools)}")
            failure_mode = "wrong_tool"
            confidence = 0.75

        if expected_calls and failure_mode is None:
            expected_order_matches = True
            actual_idx = 0
            for expected in expected_calls:
                found = False
                while actual_idx < len(tools_used):
                    if tools_used[actual_idx] == expected:
                        found = True
                        actual_idx += 1
                        break
                    actual_idx += 1
                if not found:
                    expected_order_matches = False
                    break

            if not expected_order_matches and expected_set.issubset(actual_set):
                evidence.append("call_order_differs_from_expected")
                failure_mode = "missing_precondition"
                confidence = 0.7

        if failure_mode is None:
            for entry in api_call_entries:
                args = entry.get("arguments", {})
                tool = entry.get("tool_name", "")
                for api_def in raw.get("available_apis", []):
                    if api_def.get("name") == tool:
                        expected_params = api_def.get("parameters", {})
                        for param_name in expected_params:
                            if param_name not in args:
                                evidence.append(f"missing_param:{tool}.{param_name}")
                                failure_mode = "wrong_arguments"
                                confidence = 0.8

        if failure_mode is None:
            has_response_errors = False
            trajectory = raw.get("trajectory", [])
            for entry in trajectory:
                if entry.get("action_type") == "api_response":
                    content = entry.get("content", "")
                    try:
                        resp = json.loads(content)
                        if isinstance(resp, dict) and resp.get("status") == "error":
                            has_response_errors = True
                    except (json.JSONDecodeError, TypeError):
                        pass

            if has_response_errors:
                failure_mode = "wrong_arguments"
                confidence = 0.75
                evidence.append("api_response_indicated_error")

        if failure_mode is None:
            final_answer = raw.get("final_answer", "")
            if final_answer and not expected_set.issubset(actual_set):
                missing = expected_set - actual_set
                failure_mode = "premature_closure"
                confidence = 0.7
                evidence.append(
                    f"final_answer_before_all_calls:missing_{','.join(missing)}"
                )

        if failure_mode is None:
            retry_count = 0
            seen: list[str] = []
            for tool in tools_used:
                if tool in seen:
                    retry_count += 1
                seen.append(tool)
            if retry_count > 5:
                failure_mode = "payment_spiral"
                confidence = 0.8
                evidence.append(f"retry_count:{retry_count}")

        return failure_mode, confidence, evidence

    def _infer_metabolization_candidates(self, raw: dict[str, Any]) -> list[str]:
        candidates: list[str] = []
        trajectory = raw.get("trajectory", [])

        has_analysis_before_call = False
        has_multiple_tools = False
        tools_seen: set[str] = set()

        last_was_analysis = False
        for entry in trajectory:
            at = entry.get("action_type", "")
            if at == "analysis":
                last_was_analysis = True
            elif at == "api_call":
                if last_was_analysis:
                    has_analysis_before_call = True
                tool = entry.get("tool_name", "")
                if tool in tools_seen:
                    has_multiple_tools = True
                tools_seen.add(tool)
                last_was_analysis = False

        if has_analysis_before_call:
            candidates.append("inspect_api_schema_before_call")
        if has_multiple_tools or len(tools_seen) > 1:
            candidates.append("compare_constraints_before_selection")

        if not candidates:
            candidates.append("inspect_api_schema_before_call")

        return candidates
