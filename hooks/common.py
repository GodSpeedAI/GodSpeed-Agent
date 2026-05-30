from __future__ import annotations

import json
import sys
from typing import Any


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Hook input must be a JSON object")
    return parsed


def write_stdout_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))

