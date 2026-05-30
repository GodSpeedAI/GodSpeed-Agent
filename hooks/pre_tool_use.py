#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from godspeed_nav.metrics import estimate_payment
from hooks.common import read_stdin_json, write_stdout_json


def main() -> int:
    event = read_stdin_json()
    payment = estimate_payment(
        event.get("costs", {}),
        event.get("weights", {}),
        event.get("capacities", {}),
    )
    unaffordable = payment["spendability"] == "unaffordable"
    decision = "allow"
    if unaffordable:
        decision = "block" if event.get("block_unaffordable_actions", False) else "warn"
    write_stdout_json(
        {
            "hook": "PreToolUse",
            "tool_name": event.get("tool_name"),
            "decision": decision,
            "payment": payment,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
