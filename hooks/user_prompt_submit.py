#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hooks.common import read_stdin_json, write_stdout_json


def main() -> int:
    event = read_stdin_json()
    prompt = event.get("prompt", "")
    write_stdout_json(
        {
            "hook": "UserPromptSubmit",
            "desired_direction_hypothesis": prompt[:240],
            "outcome_as_terminal": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
