"""Nebius SWE-Agent settlement dataset adapter.

Normalises rows from ``nebius/SWE-agent-trajectories`` into canonical
settlement records classified as ``external-proxy-settlement``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from scripts.settlement_datasets.adapter_base import (
    SettlementDatasetAdapter,
    make_empty_environment,
    make_empty_payment,
    make_empty_representational_state,
)


def _parse_trajectory(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the trajectory field, tolerating JSON-string or list forms."""
    trajectory = raw.get("trajectory", [])
    if isinstance(trajectory, str):
        try:
            trajectory = json.loads(trajectory)
        except (json.JSONDecodeError, TypeError):
            trajectory = []
    if not isinstance(trajectory, list):
        trajectory = []
    return trajectory


class NebiusSWEAgentAdapter(SettlementDatasetAdapter):
    name = "nebius_swe_agent"
    domain = "code"
    source_uri = "nebius/SWE-agent-trajectories"

    _DEFAULT_FIXTURE_PATH = (
        Path(__file__).resolve().parent.parent.parent
        / "tests"
        / "fixtures"
        / "settlement_datasets"
        / "nebius_swe_agent"
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
        split = kwargs.get("split", "train")
        stream = load_hf_stream(source_uri, split=split)
        yield from iter_limited(stream, limit)

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def normalize_task(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "implementation",
            "description": raw.get("instance_id") or "",
            "settlement_target": "pass_all_tests",
        }

    def extract_actions(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        trajectory = _parse_trajectory(raw)
        actions: list[dict[str, Any]] = []
        for idx, entry in enumerate(trajectory):
            role = entry.get("role", "")
            if role in ("ai", "assistant"):
                actions.append(
                    {
                        "turn_index": idx,
                        "role": role,
                        "action_type": "message",
                        # Live HF rows (v006 finding) carry the message in
                        # ``text``; fixtures carry legacy ``content``.
                        "content": entry.get("text") or entry.get("content") or "",
                    }
                )
        return actions

    def extract_observations(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        trajectory = _parse_trajectory(raw)
        observations: list[dict[str, Any]] = []
        for idx, entry in enumerate(trajectory):
            role = entry.get("role", "")
            if role in ("user", "tool"):
                observations.append(
                    {
                        "turn_index": idx,
                        "role": role,
                        # Live HF rows (v006 finding) carry the message in
                        # ``text``; fixtures carry legacy ``content``.
                        "content": entry.get("text") or entry.get("content") or "",
                    }
                )
        return observations

    def extract_outcome(self, raw: dict[str, Any]) -> dict[str, Any]:
        target = raw.get("target", False)
        eval_logs = raw.get("eval_logs", "")

        evidence: list[str] = [f"target={target}"]
        if eval_logs:
            evidence.append(f"eval_logs={eval_logs[:100]}")

        if target:
            return {
                "success": True,
                "reward": 1.0,
                "score": 1.0,
                "settlement_quality": "clean_success",
                "confidence": 0.9,
                "evidence": evidence,
            }

        has_signal = bool(eval_logs)
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
        trajectory = _parse_trajectory(raw)
        ai_turns = sum(1 for e in trajectory if e.get("role") in ("ai", "assistant"))
        user_turns = sum(1 for e in trajectory if e.get("role") in ("user", "tool"))

        # Null-safe: HF rows can carry explicit nulls for these string
        # fields (v005 observed 441 adapter errors from len(None)/.lower()).
        patch = raw.get("generated_patch") or ""
        patch_size = len(patch)

        eval_logs = raw.get("eval_logs") or ""
        error_like_count = sum(
            1
            for kw in ("error", "fail", "assertion", "traceback", "exception")
            if kw in eval_logs.lower()
        )

        total_steps = len(trajectory)
        if total_steps <= 4:
            complexity = "low"
        elif total_steps <= 10:
            complexity = "medium"
        else:
            complexity = "high"

        return {
            "turns": ai_turns,
            "tool_calls": user_turns,
            "commands": ai_turns,
            "page_actions": 0,
            "api_calls": 0,
            "elapsed_steps": total_steps,
            "error_count": error_like_count,
            "estimated_complexity": complexity,
            "evidence": [
                f"ai_turns={ai_turns}",
                f"user_turns={user_turns}",
                f"patch_size={patch_size}",
                f"error_like_in_logs={error_like_count}",
            ],
        }

    def infer_settlement_quality(
        self, raw: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        target = raw.get("target", False)
        payment = extracted.get("payment", {})
        error_count = payment.get("error_count", 0)

        if target and error_count == 0:
            return {"settlement_quality": "clean_success", "confidence": 0.9}
        elif target and error_count > 0:
            return {"settlement_quality": "recovered_success", "confidence": 0.8}
        elif not target and error_count > 0:
            return {"settlement_quality": "failure_with_signal", "confidence": 0.8}
        else:
            return {"settlement_quality": "failure_without_signal", "confidence": 0.3}

    # ------------------------------------------------------------------
    # Record assembly
    # ------------------------------------------------------------------

    def to_settlement_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        payment = self.extract_payment(raw)
        extracted = {
            "payment": payment,
            "outcome_base": {"target": raw.get("target", False)},
        }
        outcome = self.extract_outcome(raw)
        quality = self.infer_settlement_quality(raw, extracted)

        task = self.normalize_task(raw)
        actions = self.extract_actions(raw)
        observations = self.extract_observations(raw)

        return {
            "dataset": self.name,
            "domain": self.domain,
            "task_id": raw.get("instance_id") or "",
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
                "model_name": raw.get("model_name") or "",
                "exit_status": raw.get("exit_status") or "",
                "raw_source_uri": self.source_uri,
            },
        }
