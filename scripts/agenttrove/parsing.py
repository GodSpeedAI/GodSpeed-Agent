from __future__ import annotations

import json
import re
from typing import Any


SYSTEM_PROMPT_BOILERPLATE_PATTERNS = [
    re.compile(r"you are an ai assistant tasked with", re.IGNORECASE),
    re.compile(r"you are a helpful assistant", re.IGNORECASE),
    re.compile(r"you are an expert", re.IGNORECASE),
]


def parse_assistant_content(content: str) -> dict[str, Any]:
    if not content or not content.strip():
        return {"parsed": False, "commands": [], "task_complete": None, "actions": []}

    parsed_json = _try_parse_json(content)

    if parsed_json is not None:
        commands = _extract_json_commands(parsed_json)
        task_complete = parsed_json.get("task_complete")
        actions = _extract_json_actions(parsed_json)
        return {
            "parsed": True,
            "source": "assistant_json",
            "commands": commands,
            "task_complete": task_complete,
            "actions": actions,
            "raw_keys": list(parsed_json.keys())
            if isinstance(parsed_json, dict)
            else [],
        }

    commands = _extract_regex_commands(content)
    return {
        "parsed": False,
        "source": "regex_fallback",
        "commands": commands,
        "task_complete": None,
        "actions": [
            {"action_type": "text", "source": "regex", "content": content[:200]}
        ],
    }


def _try_parse_json(content: str) -> dict[str, Any] | list[Any] | None:
    stripped = content.strip()
    if not stripped.startswith("{") and not stripped.startswith("["):
        return None
    try:
        result = json.loads(stripped)
        if isinstance(result, (dict, list)):
            return result
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _extract_json_commands(parsed: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []

    if isinstance(parsed, dict):
        for key in ("commands", "command", "actions", "action"):
            value = parsed.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                for item in value:
                    commands.extend(_normalize_command_item(item))
            elif isinstance(value, str):
                commands.append(
                    {
                        "action_type": "command",
                        "source": "assistant_json",
                        "content": value,
                    }
                )
            elif isinstance(value, dict):
                commands.extend(_normalize_command_item(value))

    return commands


def _normalize_command_item(item: Any) -> list[dict[str, Any]]:
    if isinstance(item, str):
        return [{"action_type": "command", "source": "assistant_json", "content": item}]
    if isinstance(item, dict):
        for field in ("keystrokes", "command", "cmd", "content", "script"):
            val = item.get(field)
            if isinstance(val, str) and val.strip():
                return [
                    {
                        "action_type": "command",
                        "source": "assistant_json",
                        "content": val,
                        "raw": item,
                    }
                ]
        if "action" in item and isinstance(item["action"], str):
            return [
                {
                    "action_type": "command",
                    "source": "assistant_json",
                    "content": item["action"],
                    "raw": item,
                }
            ]
    return []


def _extract_json_actions(parsed: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    if isinstance(parsed, dict):
        if "analysis" in parsed:
            actions.append(
                {
                    "action_type": "analysis",
                    "source": "assistant_json",
                    "content": str(parsed["analysis"])[:200],
                }
            )
        if "plan" in parsed:
            actions.append(
                {
                    "action_type": "plan",
                    "source": "assistant_json",
                    "content": str(parsed["plan"])[:200],
                }
            )

    return actions


def _extract_regex_commands(content: str) -> list[dict[str, Any]]:
    from scripts.agenttrove.profile_traces import is_command_like

    if is_command_like(content):
        return [{"action_type": "command", "source": "regex", "content": content[:200]}]
    return []


def count_json_commands(messages: list[dict[str, Any]]) -> int:
    count = 0
    for msg in messages:
        if msg.get("role") == "assistant":
            parsed = parse_assistant_content(msg.get("content", ""))
            count += len(parsed["commands"])
    return count


def detect_task_complete(messages: list[dict[str, Any]]) -> dict[str, Any]:
    if not messages:
        return {"has_marker": False, "value": None, "source": "none"}

    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        parsed = parse_assistant_content(msg.get("content", ""))
        if parsed["parsed"] and parsed["task_complete"] is not None:
            return {
                "has_marker": True,
                "value": parsed["task_complete"],
                "source": "assistant_json",
            }

    from scripts.agenttrove.profile_traces import has_final_answer

    if has_final_answer(messages):
        return {"has_marker": True, "value": True, "source": "prose"}

    return {"has_marker": False, "value": None, "source": "none"}


def is_system_prompt_boilerplate(content: str) -> bool:
    if not content:
        return False
    for pattern in SYSTEM_PROMPT_BOILERPLATE_PATTERNS:
        if pattern.search(content):
            return True
    return False


def extract_user_task_content(messages: list[dict[str, Any]]) -> str:
    user_messages = [m for m in messages if m.get("role") == "user"]
    if not user_messages:
        return ""

    first = user_messages[0].get("content", "")
    if is_system_prompt_boilerplate(first):
        for msg in user_messages[1:]:
            content = msg.get("content", "")
            if (
                not is_system_prompt_boilerplate(content)
                and "terminal output" not in content.lower()
            ):
                return content
        return ""

    return first


def detect_structural_errors(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    from scripts.agenttrove.profile_traces import is_error_like

    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user" and is_error_like(content):
            lower = content.lower()
            if "new terminal output" in lower:
                after_marker = lower.split("new terminal output", 1)[-1]
                if is_error_like(after_marker):
                    errors.append(
                        {"turn_index": i, "role": "user", "source": "terminal_output"}
                    )
            elif not is_system_prompt_boilerplate(content):
                errors.append(
                    {"turn_index": i, "role": "user", "source": "user_message"}
                )

        if role == "assistant":
            parsed = parse_assistant_content(content)
            if parsed["parsed"]:
                analysis = str(parsed.get("raw_keys", ""))
                pass
            elif is_error_like(content):
                errors.append(
                    {"turn_index": i, "role": "assistant", "source": "assistant_text"}
                )

        if role == "tool" and is_error_like(content):
            errors.append({"turn_index": i, "role": "tool", "source": "tool_output"})

    return errors


def infer_settlement_from_structure(
    messages: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    evidence: list[str] = []
    positive_signals = 0
    negative_signals = 0

    task_complete = detect_task_complete(messages)
    if task_complete["has_marker"] and task_complete["value"] is True:
        positive_signals += 2
        evidence.append(
            f"task_complete:{task_complete['value']}:{task_complete['source']}"
        )
    elif task_complete["has_marker"] and task_complete["value"] is False:
        negative_signals += 2
        evidence.append(
            f"task_complete:{task_complete['value']}:{task_complete['source']}"
        )

    json_cmd_count = profile.get("json_command_count", 0)
    if json_cmd_count > 0:
        positive_signals += 1
        evidence.append(f"json_command_count:{json_cmd_count}")

    error_count = profile.get("error_like_output_count", 0)
    if error_count == 0:
        positive_signals += 1
        evidence.append("error_count:0")
    elif error_count >= 3:
        negative_signals += 2
        evidence.append(f"error_count:{error_count}")
    elif error_count >= 1:
        negative_signals += 1
        evidence.append(f"error_count:{error_count}")

    from scripts.agenttrove.profile_traces import has_final_answer

    if has_final_answer(messages):
        positive_signals += 1
        evidence.append("has_final_answer:true")

    structural_errors = detect_structural_errors(messages)
    terminal_errors = [e for e in structural_errors if e["source"] == "terminal_output"]
    unresolved_terminal_errors = 0
    for err in terminal_errors:
        err_idx = err["turn_index"]
        has_recovery = False
        for j in range(err_idx + 1, min(err_idx + 5, len(messages))):
            if messages[j].get("role") == "assistant":
                parsed = parse_assistant_content(messages[j].get("content", ""))
                if parsed["commands"]:
                    has_recovery = True
                    break
        if not has_recovery:
            unresolved_terminal_errors += 1

    if unresolved_terminal_errors > 0:
        negative_signals += unresolved_terminal_errors
        evidence.append(f"unresolved_terminal_errors:{unresolved_terminal_errors}")

    if positive_signals > 0 and negative_signals == 0:
        quality = "clean_success"
        confidence = min(0.5 + positive_signals * 0.1, 0.95)
    elif positive_signals > negative_signals:
        quality = "recovered_success" if error_count > 0 else "clean_success"
        confidence = min(0.4 + positive_signals * 0.1, 0.85)
    elif negative_signals > 0 and positive_signals == 0:
        quality = "failure_with_signal" if error_count > 0 else "failure_without_signal"
        confidence = min(0.4 + negative_signals * 0.1, 0.9)
    elif positive_signals == 0 and negative_signals == 0:
        quality = "unknown"
        confidence = 0.3
    else:
        if positive_signals >= negative_signals:
            quality = "partial_success"
            confidence = 0.5
        else:
            quality = "failure_with_signal"
            confidence = 0.5

    return {
        "settlement_quality": quality,
        "confidence": round(confidence, 2),
        "evidence": evidence,
    }
