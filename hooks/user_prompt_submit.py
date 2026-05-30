#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from godspeed_nav.schemas import now_iso
from hooks.common import read_stdin_json, write_stdout_json
from hooks.common import get_session_context, get_storage


def _prompt_label(prompt: str) -> str:
    text = prompt.strip()
    if not text:
        return "empty-direction"
    return text[:80]


def main() -> int:
    event = read_stdin_json()
    prompt = str(event.get("prompt", "")).strip()
    desired_direction_hypothesis = {
        "id": event.get("direction_id", f"dir-hypothesis-{now_iso()}"),
        "label": _prompt_label(prompt),
        "statement": prompt,
        "kind": event.get("kind", "goal"),
        "source": "hook:user_prompt_submit",
        "status": "hypothesis",
        "created_at": now_iso(),
    }
    session_context = get_session_context(event, desired_direction_hypothesis["id"])
    storage = get_storage(event)
    storage.append_event(
        "prompt_submissions",
        {
            "id": event.get("id", f"prompt-{now_iso()}"),
            "prompt": prompt,
            "desired_direction_hypothesis": desired_direction_hypothesis,
            "session_context": session_context,
            "needs_horizon_review": bool(prompt),
            "outcome_as_terminal": False,
        },
    )
    write_stdout_json(
        {
            "hook": "UserPromptSubmit",
            "desired_direction_hypothesis": desired_direction_hypothesis,
            "session_context": session_context,
            "needs_horizon_review": bool(prompt),
            "outcome_as_terminal": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
