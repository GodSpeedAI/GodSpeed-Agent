"""SWE-Gym OpenHands settlement dataset adapter.

Normalises rows from ``SWE-Gym/OpenHands-Sampled-Trajectories`` into
canonical settlement records classified as ``external-proxy-settlement``.

Action content (v008 normalization N1): assistant messages carry the
actual command in ``tool_calls[].function.{name,arguments}`` (OpenAI
format) with ``content`` usually empty; each action's content appends
the rendered tool-call signatures (same rendering as the swe_smith
adapter).  Without this the corpus builder's ``cmd_family``/
``mentions_bash`` derivation and the action-hash identity features
would be degenerate for the ~48% of swegym actions whose ``content``
is empty.  Assistant messages without ``tool_calls`` are unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from scripts.settlement_datasets.adapter_base import (
    EMPTY_LABELS,
    SettlementDatasetAdapter,
    make_empty_environment,
    make_empty_payment,
    make_empty_representational_state,
)


def _render_tool_calls(msg: dict[str, Any]) -> str:
    """Render ``tool_calls[].function.{name,arguments}`` signatures.

    Same rendering as the swe_smith adapter; null-safe for absent or
    malformed ``tool_calls`` fields.
    """
    lines: list[str] = []
    for call in msg.get("tool_calls") or []:
        if not isinstance(call, dict):
            continue
        function = call.get("function")
        if not isinstance(function, dict):
            continue
        lines.append(
            f"{function.get('name') or ''} {function.get('arguments') or ''}".strip()
        )
    return "\n".join(lines)


class SWEGymOpenHandsAdapter(SettlementDatasetAdapter):
    name = "swegym_openhands"
    domain = "code"
    source_uri = "SWE-Gym/OpenHands-Sampled-Trajectories"

    _DEFAULT_FIXTURE_PATH = (
        Path(__file__).resolve().parent.parent.parent
        / "tests"
        / "fixtures"
        / "settlement_datasets"
        / "swegym_openhands"
        / "sample.jsonl"
    )

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def stream(
        self, limit: int | None = None, **kwargs: Any
    ) -> Iterator[dict[str, Any]]:
        input_path = kwargs.get("input_path")
        if input_path:
            yield from self._stream_local(input_path, limit)
        else:
            yield from self._stream_hf(limit, **kwargs)

    def _stream_local(
        self, input_path: str, limit: int | None
    ) -> Iterator[dict[str, Any]]:
        yielded = 0
        with Path(input_path).open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)
                    yielded += 1
                    if limit is not None and yielded >= limit:
                        break

    def _stream_hf(self, limit: int | None, **kwargs: Any) -> Iterator[dict[str, Any]]:
        from scripts.settlement_datasets.hf_stream import iter_limited, load_hf_stream

        source_uri = kwargs.get("source_uri", self.source_uri)
        split = kwargs.get("split", "train.raw")
        stream = load_hf_stream(source_uri, split=split)
        yield from iter_limited(stream, limit)

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def normalize_task(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "implementation",
            "description": raw.get("instance_id", ""),
            "settlement_target": "pass_all_tests",
        }

    def extract_actions(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        for idx, msg in enumerate(raw.get("messages", [])):
            if msg.get("role") == "assistant":
                # N1: render non-empty tool_calls into the content (the
                # command lives there; ``content`` is usually empty).
                # Null-safe: prose and tool-call signature are individually
                # optional in the live rows.
                text = msg.get("content", "")
                calls = _render_tool_calls(msg)
                content = "\n".join(part for part in (text, calls) if part)
                actions.append(
                    {
                        "turn_index": idx,
                        "role": "assistant",
                        "action_type": "message",
                        "content": content,
                    }
                )
        return actions

    def extract_observations(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        for idx, msg in enumerate(raw.get("messages", [])):
            if msg.get("role") == "tool":
                observations.append(
                    {
                        "turn_index": idx,
                        "role": "tool",
                        "content": msg.get("content", ""),
                    }
                )
        return observations

    def context_positions(self, raw: dict[str, Any]) -> list[int]:
        """Indices of context (non-event) messages in the raw message
        sequence; enables prefix-scoped elapsed counts.

        Actions are ``assistant`` messages and observations are ``tool``
        messages (matching ``extract_actions``/``extract_observations``),
        so every other role (system/user context, interleaved or leading)
        is a context position.
        """
        return [
            idx
            for idx, msg in enumerate(raw.get("messages", []))
            if msg.get("role") not in ("assistant", "tool")
        ]

    def extract_outcome(self, raw: dict[str, Any]) -> dict[str, Any]:
        resolved = raw.get("resolved", False)
        test_result = raw.get("test_result", {})

        # Handle both flat schema (test_result.passed) and nested HF schema
        # (test_result.report.resolved).
        test_passed: bool | None = None
        if isinstance(test_result, dict):
            if "passed" in test_result:
                test_passed = test_result["passed"]
            elif isinstance(test_result.get("report"), dict):
                test_passed = test_result["report"].get("resolved")

        evidence: list[str] = [f"resolved={resolved}"]
        if test_passed is not None:
            evidence.append(f"test_passed={test_passed}")

        if resolved:
            return {
                "success": True,
                "reward": 1.0,
                "score": 1.0,
                "settlement_quality": "clean_success",
                "confidence": 0.9,
                "evidence": evidence,
            }

        has_signal = test_result is not None and test_passed is not None
        return {
            "success": False,
            "reward": 0.0,
            "score": 0.0,
            "settlement_quality": "failure_with_signal"
            if has_signal
            else "failure_without_signal",
            "confidence": 0.8 if has_signal else 0.3,
            "evidence": evidence,
        }

    def extract_payment(self, raw: dict[str, Any]) -> dict[str, Any]:
        messages = raw.get("messages", [])
        tools = raw.get("tools", [])

        assistant_turns = sum(1 for m in messages if m.get("role") == "assistant")
        tool_turns = sum(1 for m in messages if m.get("role") == "tool")
        tool_count = len(tools)

        bash_mentions = sum(
            1
            for m in messages
            if m.get("role") == "assistant"
            and m.get("content") is not None
            and "bash" in (m.get("content") or "").lower()
        )

        error_count = sum(
            1
            for m in messages
            if m.get("role") == "tool"
            and m.get("content") is not None
            and any(
                kw in (m.get("content") or "").lower()
                for kw in (
                    "error",
                    "failed",
                    "traceback",
                    "exception",
                    "assertionerror",
                )
            )
        )

        total_steps = len(messages)
        if total_steps <= 4:
            complexity = "low"
        elif total_steps <= 10:
            complexity = "medium"
        else:
            complexity = "high"

        return {
            "turns": assistant_turns,
            "tool_calls": tool_turns,
            "commands": bash_mentions,
            "page_actions": 0,
            "api_calls": 0,
            "elapsed_steps": total_steps,
            "error_count": error_count,
            "estimated_complexity": complexity,
            "evidence": [
                f"assistant_turns={assistant_turns}",
                f"tool_turns={tool_turns}",
                f"tool_count={tool_count}",
                f"bash_mentions={bash_mentions}",
                f"errors={error_count}",
            ],
        }

    def infer_settlement_quality(
        self, raw: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        outcome = extracted.get("outcome_base", {})
        resolved = outcome.get("resolved", raw.get("resolved", False))
        payment = extracted.get("payment", {})
        error_count = payment.get("error_count", 0)

        if resolved and error_count == 0:
            return {"settlement_quality": "clean_success", "confidence": 0.9}
        elif resolved and error_count > 0:
            return {"settlement_quality": "recovered_success", "confidence": 0.8}
        elif not resolved and error_count > 0:
            return {"settlement_quality": "failure_with_signal", "confidence": 0.8}
        else:
            return {"settlement_quality": "failure_without_signal", "confidence": 0.3}

    # ------------------------------------------------------------------
    # Record assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_tool_names(tools: list[Any]) -> list[str]:
        """Extract tool names from both flat and nested HF tool schemas.

        Flat:  ``[{"name": "bash"}, ...]``
        Nested: ``[{"function": {"name": "execute_bash"}, "type": "function"}, ...]``
        """
        names: list[str] = []
        for t in tools:
            if isinstance(t, dict):
                if "name" in t:
                    names.append(t["name"])
                elif isinstance(t.get("function"), dict) and "name" in t["function"]:
                    names.append(t["function"]["name"])
        return names

    def to_settlement_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        payment = self.extract_payment(raw)
        extracted = {
            "payment": payment,
            "outcome_base": {"resolved": raw.get("resolved", False)},
        }
        outcome = self.extract_outcome(raw)
        quality = self.infer_settlement_quality(raw, extracted)

        task = self.normalize_task(raw)
        actions = self.extract_actions(raw)
        observations = self.extract_observations(raw)

        return {
            "dataset": self.name,
            "domain": self.domain,
            "task_id": raw.get("instance_id", ""),
            "source_uri": self.source_uri,
            "desired_direction": task,
            "environment": {
                "type": "code_repository",
                "has_runnable_feedback": True,
                "feedback_type": "tests",
            },
            "representational_state": make_empty_representational_state(),
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
                "settlement_classification": "external-proxy-settlement",
                "source_run_id": raw.get("run_id", ""),
                "raw_source_uri": self.source_uri,
                "tool_names": self._extract_tool_names(raw.get("tools", [])),
            },
        }
