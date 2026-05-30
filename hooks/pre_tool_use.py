#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from godspeed_nav.metrics import estimate_payment
from godspeed_nav.policies import enforce_payment_policy
from godspeed_nav.storage import LedgerStore
from hooks.common import read_stdin_json, write_stdout_json


def main() -> int:
    event = read_stdin_json()
    payment = estimate_payment(
        event.get("costs", {}),
        event.get("weights", {}),
        event.get("capacities", {}),
    )
    policy_decision = enforce_payment_policy(
        payment,
        {
            "block_unaffordable_actions": event.get("block_unaffordable_actions", False),
            "warn_unaffordable_actions": event.get("warn_unaffordable_actions", True),
        },
    )
    storage = LedgerStore(event.get("storage_root", ".godspeed-harness"))
    storage.append(
        "tool_payments",
        {
            "tool_name": event.get("tool_name"),
            "payment": payment,
            "policy_decision": policy_decision.to_dict(),
        },
    )
    write_stdout_json(
        {
            "hook": "PreToolUse",
            "tool_name": event.get("tool_name"),
            "decision": policy_decision.decision,
            "payment": payment,
            "policy_decision": policy_decision.to_dict(),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
