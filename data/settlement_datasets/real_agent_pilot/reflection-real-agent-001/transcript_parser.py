"""Parse a raw VS Code agent conversation transcript into structured events.

Takes a pasted conversation transcript and produces events.jsonl entries,
policy fire records, and run summaries for the real agent pilot.

Usage:
    from transcript_parser import parse_transcript
    events = parse_transcript(transcript_text, run_id="run-01")
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PILOT_DIR = Path("data/settlement_datasets/real_agent_pilot/reflection-real-agent-001")


def _classify_line(line: str) -> dict[str, Any] | None:
    """Classify a single line of transcript text into an event type."""
    stripped = line.strip()
    if not stripped:
        return None

    # Tool calls — bash, read, write, edit
    if re.match(r"^\$\s+", stripped):
        cmd = re.sub(r"^\$\s+", "", stripped)
        return {"event_type": "tool_call", "content": cmd, "tool_name": "bash"}

    if re.match(r"^(Running|Executing|Reading|Editing|Writing)\s", stripped, re.I):
        return {"event_type": "tool_call", "content": stripped, "tool_name": "inferred"}

    # Tool results — error patterns
    error_patterns = [
        r"^(Traceback|Error|Exception|FAILED|AssertionError|ModuleNotFoundError|"
        r"ImportError|FileNotFoundError|KeyError|TypeError|ValueError|"
        r"OperationalError|PermissionError)",
    ]
    for pattern in error_patterns:
        if re.match(pattern, stripped, re.I):
            return {"event_type": "tool_result", "content": stripped, "is_error": True}

    # Test results
    if re.match(r"^\d+ (passed|failed)", stripped):
        return {
            "event_type": "tool_result",
            "content": stripped,
            "is_error": "failed" in stripped,
        }

    # File edits
    if re.match(r"^(Editing|Modified|Created|Wrote|Updated)\s", stripped, re.I):
        return {"event_type": "file_edit", "content": stripped}

    # Task completion markers
    if "TASK COMPLETE" in stripped or "task complete" in stripped.lower():
        return {"event_type": "task_complete", "content": stripped}
    if "TASK FAILED" in stripped or "task failed" in stripped.lower():
        return {"event_type": "task_complete", "content": stripped}

    # Default: model message (agent thinking/talking)
    return {"event_type": "model_message", "content": stripped}


def parse_transcript(
    transcript: str,
    run_id: str,
    condition: str = "baseline",
    task_dir: str = "",
    task_description: str = "",
) -> dict[str, Any]:
    """Parse a raw conversation transcript into structured pilot artifacts.

    Returns a dict with:
        events: list of event dicts
        error_count: number of error events
        total_steps: total event count
        outcome: "success" or "failure"
        settlement_quality: inferred settlement quality
        policy_fire_step: step where policy would have fired (or None)
        agent_revised_strategy: whether agent changed approach after errors
    """
    lines = transcript.split("\n")
    events: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    policy_fire_step: int | None = None
    agent_revised_strategy = False
    step = 0

    # Track errors for policy fire detection
    error_fingerprints: list[str] = []
    same_path_after_error = False

    for line in lines:
        classified = _classify_line(line)
        if classified is None:
            continue

        event = {
            "run_id": run_id,
            "step_index": step,
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": classified["event_type"],
            "content": classified["content"][:500],
            "tool_name": classified.get("tool_name"),
            "is_error": classified.get("is_error", False),
            "metadata": {},
        }
        events.append(event)

        # Track errors
        if classified.get("is_error"):
            errors.append(event)
            fp = classified["content"][:100].lower()
            error_fingerprints.append(fp)

        # Detect same-path continuation after errors
        if (
            len(errors) >= 2
            and classified["event_type"] == "tool_call"
            and policy_fire_step is None
        ):
            # Check if this is a retry of a previous command
            prev_calls = [e for e in events[:-1] if e["event_type"] == "tool_call"]
            if prev_calls:
                current_cmd = classified["content"].lower().strip()
                for prev in prev_calls:
                    prev_cmd = prev["content"].lower().strip()
                    if (
                        current_cmd == prev_cmd
                        or current_cmd in prev_cmd
                        or prev_cmd in current_cmd
                    ):
                        same_path_after_error = True
                        policy_fire_step = step
                        break

        # Detect strategy revision
        if len(errors) >= 1 and classified["event_type"] in (
            "tool_call",
            "model_message",
        ):
            content_lower = classified["content"].lower()
            revision_tokens = (
                "check",
                "inspect",
                "look at",
                "examine",
                "diagnose",
                "investigate",
                "explore",
                "review",
                "analyze",
                "read",
                "cat ",
                "ls",
                "grep ",
                "let me check",
                "let me look",
                "what's in",
                "what is in",
                "i need to understand",
                "different approach",
                "new plan",
                "revised",
            )
            if any(t in content_lower for t in revision_tokens):
                # Only count if it's a tool_call (action, not just words)
                if classified["event_type"] == "tool_call":
                    agent_revised_strategy = True

        step += 1

    # Determine outcome
    has_task_complete = any(e["event_type"] == "task_complete" for e in events)
    has_success_marker = any(
        "passed" in e["content"].lower() and "failed" not in e["content"].lower()
        for e in events
        if e["event_type"] == "tool_result"
    )
    has_failure_marker = any("TASK FAILED" in e["content"] for e in events)

    if has_failure_marker:
        outcome = "failure"
    elif has_success_marker or has_task_complete:
        outcome = "success"
    else:
        outcome = "unknown"

    # Infer settlement quality
    if outcome == "success" and len(errors) == 0:
        settlement_quality = "clean_success"
    elif outcome == "success" and len(errors) > 0:
        settlement_quality = "recovered_success"
    elif outcome == "failure":
        settlement_quality = "failure_with_signal"
    else:
        settlement_quality = "unknown"

    return {
        "run_id": run_id,
        "condition": condition,
        "task_dir": task_dir,
        "task_description": task_description,
        "events": events,
        "error_count": len(errors),
        "total_steps": len(events),
        "outcome": outcome,
        "settlement_quality": settlement_quality,
        "policy_fire_step": policy_fire_step,
        "policy_would_have_fired": policy_fire_step is not None,
        "agent_revised_strategy": agent_revised_strategy,
        "same_path_after_error": same_path_after_error,
        "parsed_at": datetime.now(UTC).isoformat(),
    }


def write_parsed_run(
    result: dict[str, Any], pilot_dir: Path = PILOT_DIR
) -> dict[str, Path]:
    """Write parsed run results to JSONL artifacts."""
    pilot_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    # Events
    events_path = pilot_dir / "events.jsonl"
    for event in result["events"]:
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    paths["events"] = events_path

    # Policy fires
    if result["policy_would_have_fired"]:
        fire_record = {
            "run_id": result["run_id"],
            "step_index": result["policy_fire_step"],
            "policy_id": "require_reflection_before_continuing_after_second_unresolved_error",
            "fire_reason": "second_unresolved_error_with_same_path_continuation",
            "error_count": result["error_count"],
        }
        fires_path = pilot_dir / "policy_fires.jsonl"
        with open(fires_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(fire_record, ensure_ascii=False) + "\n")
        paths["policy_fires"] = fires_path

    # Run summary
    summary = {
        "run_id": result["run_id"],
        "total_steps": result["total_steps"],
        "error_count": result["error_count"],
        "outcome": result["outcome"],
        "settlement_quality": result["settlement_quality"],
        "policy_would_have_fired": result["policy_would_have_fired"],
        "policy_fire_step": result["policy_fire_step"],
        "agent_revised_strategy": result["agent_revised_strategy"],
        "same_path_after_error": result["same_path_after_error"],
    }
    summaries_path = pilot_dir / "run_summaries.jsonl"
    with open(summaries_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    paths["run_summaries"] = summaries_path

    return paths
