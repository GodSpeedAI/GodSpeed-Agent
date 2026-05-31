from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from scripts.agenttrove.parsing import (
    count_json_commands,
    detect_structural_errors,
    detect_task_complete,
    parse_assistant_content,
)


COMMAND_PATTERNS = [
    re.compile(r"`([^`]+)`"),
    re.compile(r"\$\s+([a-zA-Z_][\w\-./]*)", re.IGNORECASE),
    re.compile(
        r"(?:^|\n)\s*(?:sudo\s+)?(?:apt|pip|npm|yarn|cargo|go|git|docker|kubectl|python|python3|node|bash|sh|curl|wget|make|cmake|gcc|g\+\+|javac|java|rustc)\s+",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|\n)\s*(?:mkdir|rm|cp|mv|cat|echo|chmod|chown|export|source|grep|find|awk|sed|tar|unzip)\s+",
        re.IGNORECASE,
    ),
    re.compile(r"```(?:bash|sh|shell|zsh)?\s*\n(.*?)```", re.DOTALL),
]

ERROR_PATTERNS = [
    re.compile(r"\berror\b", re.IGNORECASE),
    re.compile(r"\bexception\b", re.IGNORECASE),
    re.compile(r"\btraceback\b", re.IGNORECASE),
    re.compile(r"\bfail(?:ed|ure)?\b", re.IGNORECASE),
    re.compile(r"\bnot found\b", re.IGNORECASE),
    re.compile(r"\bpermission denied\b", re.IGNORECASE),
    re.compile(r"\bno such file\b", re.IGNORECASE),
    re.compile(r"\btimeout\b", re.IGNORECASE),
    re.compile(r"\bconnection refused\b", re.IGNORECASE),
    re.compile(r"\bsegmentation fault\b", re.IGNORECASE),
    re.compile(r"\bstack overflow\b", re.IGNORECASE),
    re.compile(r"\bkeyerror\b", re.IGNORECASE),
    re.compile(r"\bvalueerror\b", re.IGNORECASE),
    re.compile(r"\btypeerror\b", re.IGNORECASE),
    re.compile(r"\bimporterror\b", re.IGNORECASE),
    re.compile(r"\bmodule not found\b", re.IGNORECASE),
]


def is_command_like(content: str) -> bool:
    if not content:
        return False
    for pattern in COMMAND_PATTERNS:
        if pattern.search(content):
            return True
    stripped = content.strip()
    if stripped.startswith("/") or stripped.startswith("./"):
        return True
    if any(
        stripped.startswith(kw)
        for kw in ("sudo ", "apt ", "pip ", "npm ", "git ", "docker ")
    ):
        return True
    return False


def is_error_like(content: str) -> bool:
    if not content:
        return False
    for pattern in ERROR_PATTERNS:
        if pattern.search(content):
            return True
    return False


def count_command_like_actions(messages: list[dict[str, Any]]) -> int:
    return count_regex_command_like_actions(messages) + count_json_commands(messages)


def count_regex_command_like_actions(messages: list[dict[str, Any]]) -> int:
    count = 0
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("assistant", "tool") and is_command_like(content):
            count += 1
    return count


def count_error_like_outputs(messages: list[dict[str, Any]]) -> int:
    structural_errors = detect_structural_errors(messages)
    return len(structural_errors)


def count_regex_error_like_outputs(messages: list[dict[str, Any]]) -> int:
    count = 0
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("tool", "assistant") and is_error_like(content):
            count += 1
    return count


def find_first_error_turn(messages: list[dict[str, Any]]) -> int | None:
    structural_errors = detect_structural_errors(messages)
    if structural_errors:
        return structural_errors[0]["turn_index"]
    return None


def has_final_answer(messages: list[dict[str, Any]]) -> bool:
    if not messages:
        return False

    last = messages[-1]
    content = last.get("content", "").lower()
    role = last.get("role", "")
    if role == "assistant":
        try:
            import json as _json

            parsed = _json.loads(content.strip())
            if isinstance(parsed, dict) and parsed.get("task_complete") is True:
                return True
        except (json.JSONDecodeError, ValueError):
            pass

        answer_markers = [
            "final answer",
            "the answer is",
            "in conclusion",
            "the solution is",
            "result:",
            "answer:",
            "here is the",
            "here's the",
            "i've",
            "i have",
            "successfully",
            "completed",
        ]
        return any(marker in content for marker in answer_markers)
    return False


def profile_trace(trace: dict[str, Any]) -> dict[str, Any]:
    messages = trace.get("messages", [])
    roles = [msg.get("role", "unknown") for msg in messages]

    json_cmd = count_json_commands(messages)
    regex_cmd = count_regex_command_like_actions(messages)
    task_info = detect_task_complete(messages)

    return {
        "trace_id": trace.get("trace_id", ""),
        "source": trace.get("source", ""),
        "teacher": trace.get("teacher", ""),
        "reward": trace.get("reward"),
        "turn_count": len(messages),
        "system_turn_count": roles.count("system"),
        "user_turn_count": roles.count("user"),
        "assistant_turn_count": roles.count("assistant"),
        "tool_turn_count": roles.count("tool"),
        "regex_command_like_action_count": regex_cmd,
        "json_command_count": json_cmd,
        "command_like_action_count": regex_cmd + json_cmd,
        "error_like_output_count": count_error_like_outputs(messages),
        "first_error_turn": find_first_error_turn(messages),
        "final_turn_role": roles[-1] if roles else "",
        "has_final_answer": has_final_answer(messages),
        "has_task_complete_marker": task_info["has_marker"],
        "task_complete_value": task_info["value"],
        "completion_source": task_info["source"],
    }


def profile_traces(
    input_path: str | Path, output_dir: str | Path = "data/agenttrove/profiles"
) -> dict[str, Path]:
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    profiles: list[dict[str, Any]] = []
    source_counts: dict[str, dict[str, int]] = {}

    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            trace = json.loads(line)
            profile = profile_trace(trace)
            profiles.append(profile)

            source = profile.get("source", "unknown")
            if source not in source_counts:
                source_counts[source] = {
                    "count": 0,
                    "total_turns": 0,
                    "total_errors": 0,
                    "total_commands": 0,
                }
            source_counts[source]["count"] += 1
            source_counts[source]["total_turns"] += profile["turn_count"]
            source_counts[source]["total_errors"] += profile["error_like_output_count"]
            source_counts[source]["total_commands"] += profile[
                "command_like_action_count"
            ]

    profile_path = output_dir / "trace_profile.jsonl"
    with profile_path.open("w", encoding="utf-8") as handle:
        for profile in profiles:
            handle.write(json.dumps(profile, sort_keys=True) + "\n")

    summary_path = output_dir / "source_summary.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source", "count", "avg_turns", "avg_errors", "avg_commands"],
        )
        writer.writeheader()
        for source, stats in sorted(source_counts.items()):
            count = stats["count"]
            writer.writerow(
                {
                    "source": source,
                    "count": count,
                    "avg_turns": round(stats["total_turns"] / max(count, 1), 2),
                    "avg_errors": round(stats["total_errors"] / max(count, 1), 2),
                    "avg_commands": round(stats["total_commands"] / max(count, 1), 2),
                }
            )

    return {"profiles": profile_path, "summary": summary_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile AgentTrove traces.")
    parser.add_argument(
        "--input",
        type=str,
        default="data/agenttrove/raw_samples/sample.jsonl",
        help="Input JSONL path.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/agenttrove/profiles",
        help="Output directory.",
    )
    args = parser.parse_args()

    paths = profile_traces(args.input, args.output_dir)
    print(f"Wrote profiles to {paths['profiles']}")
    print(f"Wrote source summary to {paths['summary']}")


if __name__ == "__main__":
    main()
