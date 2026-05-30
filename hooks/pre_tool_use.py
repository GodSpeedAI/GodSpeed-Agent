#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from godspeed_nav.metrics import estimate_payment
from godspeed_nav.policies import enforce_payment_policy
from godspeed_nav.schemas import now_iso
from hooks.common import read_stdin_json, write_stdout_json
from hooks.common import get_session_context, get_storage


def _candidate_status(event: dict, payment: dict, decision: str) -> str:
    if event.get("require_pathway") and not event.get("pathway"):
        return "potential"
    if payment.get("spendability") == "unaffordable" or decision == "block":
        return "possibility"
    return "affordance"


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
    candidate_status = _candidate_status(event, payment, policy_decision.decision)
    session_context = get_session_context(event)
    storage = get_storage(event)
    storage.append_event(
        "tool_payments",
        {
            "id": event.get("id", f"tool-payment-{now_iso()}"),
            "tool_name": event.get("tool_name"),
            "desired_direction": event.get("desired_direction"),
            "session_context": session_context,
            "payment": payment,
            "candidate_status": candidate_status,
            "policy_decision": policy_decision.to_dict(),
        },
    )
    write_stdout_json(
        {
            "hook": "PreToolUse",
            "tool_name": event.get("tool_name"),
            "decision": policy_decision.decision,
            "payment": payment,
            "candidate_status": candidate_status,
            "session_context": session_context,
            "policy_decision": policy_decision.to_dict(),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
