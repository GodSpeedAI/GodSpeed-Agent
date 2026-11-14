"""SWE-bench SWE-smith settlement dataset adapter.

Normalises rows from ``SWE-bench/SWE-smith-trajectories`` into canonical
settlement records classified as ``external-proxy-settlement``.

Live schema (verified against datasets-server first-rows at revision
``08e109b4a59eaeebf80e4675cd125d42e7ac99a4``, config ``default``, split
``tool``): features are ``messages`` (a JSON-encoded OpenAI-format list),
``instance_id``, ``resolved`` (bool), ``model``, ``traj_id``, ``patch``.

Schema notes that differ from the T01a research sketch (live schema wins):

- Message ``content`` is heterogeneous: plain strings on system/assistant
  messages, but a list of typed parts (``[{"type": "text", "text": ...}]``)
  on user/tool messages.  ``_content_text`` flattens both to a string.
- Tool responses pair to calls through ``tool_call_ids`` (plural list),
  not ``tool_call_id``.  Extraction is role-based (assistant -> actions,
  tool -> observations, mirroring swegym_openhands), so no pairing is
  required; the field is documented here for future consumers.
- Assistant messages additionally carry ``thought``/``action``/``agent``/
  ``message_type`` fields; they are ignored.

Identity model: ``task_id`` carries ``instance_id``; ``traj_id`` is
carried as ``metadata.source_run_id``.  The corpus builder then derives
``group_key = swe_smith:<instance_id>`` (all attempts of one task
instance group together, per the v006 identity contract) and
``parent_id = swe_smith:<instance_id>:<traj_id>-<sha1[:10]>`` (rows are
unique per attempt).  Concatenating ``instance_id:traj_id`` directly
into ``task_id`` was rejected: it would degenerate ``group_key`` (and
therefore the v007 ``split_group`` partition key) to per-trajectory
granularity, breaking the "group_key names the shared task instance"
invariant.

Action content: the assistant's text is often pure prose (the actual
command lives in ``tool_calls[].function.arguments``), so each action's
content appends the rendered tool-call signatures.  Without this the
corpus builder's ``cmd_family``/``mentions_bash`` derivation would be
degenerate for this source.  Observation content is the flattened tool
message text (typically prefixed ``OBSERVATION:`` in the live rows).

``metadata.tool_names`` is omitted: the live schema provides no tools
column (v006 corpus semantics tolerate its absence).

Outcome: ``resolved`` is execution-derived (SWE-bench F2P/P2P test run).
``resolved=True`` -> clean success at confidence 0.9; ``resolved=False``
is an explicit terminal label -> failure with signal at confidence 0.8;
a missing/null ``resolved`` yields an undefined label (confidence 0.0),
which the corpus usability rule rejects rather than silently counting
as failure.  ``patch`` is label/leakage-side and is never copied into
the record.
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


def _parse_messages(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the messages field, tolerating JSON-string or list forms."""
    messages = raw.get("messages", [])
    if isinstance(messages, str):
        try:
            messages = json.loads(messages)
        except (json.JSONDecodeError, TypeError):
            messages = []
    if not isinstance(messages, list):
        messages = []
    return messages


def _content_text(content: Any) -> str:
    """Flatten OpenAI-style content (string or typed-part list) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text") is not None:
                parts.append(str(item["text"]))
        return "\n".join(parts)
    return ""


def _render_tool_calls(msg: dict[str, Any]) -> str:
    """Render ``tool_calls[].function.{name,arguments}`` signatures."""
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


class SWESmithAdapter(SettlementDatasetAdapter):
    name = "swe_smith"
    domain = "code"
    source_uri = "SWE-bench/SWE-smith-trajectories"

    _DEFAULT_FIXTURE_PATH = (
        Path(__file__).resolve().parent.parent.parent
        / "tests"
        / "fixtures"
        / "settlement_datasets"
        / "swe_smith"
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
        split = kwargs.get("split", "tool")
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
        actions: list[dict[str, Any]] = []
        for idx, msg in enumerate(_parse_messages(raw)):
            if msg.get("role") != "assistant":
                continue
            text = _content_text(msg.get("content"))
            calls = _render_tool_calls(msg)
            # Null-safe: prose and tool-call signature are individually
            # optional in the live rows.
            content = "\n".join(part for part in (text, calls) if part)
            actions.append(
                {
                    "turn_index": idx,
                    "role": "assistant",
                    "action_type": "tool_call" if calls else "message",
                    "content": content,
                }
            )
        return actions

    def extract_observations(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        for idx, msg in enumerate(_parse_messages(raw)):
            if msg.get("role") != "tool":
                continue
            observations.append(
                {
                    "turn_index": idx,
                    "role": "tool",
                    "content": _content_text(msg.get("content")),
                }
            )
        return observations

    def context_positions(self, raw: dict[str, Any]) -> list[int]:
        """Indices of context (non-event) messages in the raw message
        sequence; enables prefix-scoped elapsed counts.

        Actions are ``assistant`` messages and observations are ``tool``
        messages of the parsed message list (matching
        ``extract_actions``/``extract_observations``), so every other
        role (system/user context, interleaved or leading) is a context
        position.
        """
        return [
            idx
            for idx, msg in enumerate(_parse_messages(raw))
            if msg.get("role") not in ("assistant", "tool")
        ]

    def extract_outcome(self, raw: dict[str, Any]) -> dict[str, Any]:
        resolved = raw.get("resolved")
        evidence: list[str] = [f"resolved={resolved}"]

        if resolved is True:
            return {
                "success": True,
                "reward": 1.0,
                "score": 1.0,
                "settlement_quality": "clean_success",
                "confidence": 0.9,
                "evidence": evidence,
            }
        if resolved is False:
            # ``resolved`` is an explicit execution-derived bool in the
            # live schema, so the failure label carries full signal.
            return {
                "success": False,
                "reward": 0.0,
                "score": 0.0,
                "settlement_quality": "failure_with_signal",
                "confidence": 0.8,
                "evidence": evidence,
            }
        # Null/absent resolution: undefined label, rejected downstream.
        return {
            "success": None,
            "reward": None,
            "score": None,
            "settlement_quality": "unknown",
            "confidence": 0.0,
            "evidence": evidence,
        }

    def extract_payment(self, raw: dict[str, Any]) -> dict[str, Any]:
        messages = _parse_messages(raw)

        assistant_turns = sum(1 for m in messages if m.get("role") == "assistant")
        tool_turns = sum(1 for m in messages if m.get("role") == "tool")

        bash_mentions = sum(
            1
            for msg in self.extract_actions(raw)
            if "bash" in (msg.get("content") or "").lower()
        )

        error_count = sum(
            1
            for msg in self.extract_observations(raw)
            if any(
                kw in (msg.get("content") or "").lower()
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
                f"bash_mentions={bash_mentions}",
                f"errors={error_count}",
            ],
        }

    def infer_settlement_quality(
        self, raw: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        resolved = raw.get("resolved")
        payment = extracted.get("payment", {})
        error_count = payment.get("error_count", 0)

        if resolved is None:
            return {"settlement_quality": "unknown", "confidence": 0.0}
        elif resolved and error_count == 0:
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

    def to_settlement_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        payment = self.extract_payment(raw)
        extracted = {
            "payment": payment,
            "outcome_base": {"resolved": raw.get("resolved")},
        }
        outcome = self.extract_outcome(raw)
        quality = self.infer_settlement_quality(raw, extracted)

        task = self.normalize_task(raw)
        actions = self.extract_actions(raw)
        observations = self.extract_observations(raw)

        return {
            "dataset": self.name,
            "domain": self.domain,
            # instance_id names the task instance; traj_id (the unique
            # per-attempt key) rides as source_run_id -- see the module
            # docstring for the identity-model rationale.
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
                "source_run_id": raw.get("traj_id") or "",
                "model": raw.get("model") or "",
                "raw_source_uri": self.source_uri,
            },
        }
