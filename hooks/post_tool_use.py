#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from godspeed_nav.reports import generate_developmental_report
from godspeed_nav.schemas import now_iso
from hooks.common import read_stdin_json, write_stdout_json
from hooks.common import get_runtime, get_session_context, get_storage


def _affordance_id(event: dict) -> str:
    return event.get("affordance_id") or event.get("tool_name") or "unspecified-affordance"


def main() -> int:
    event = read_stdin_json()
    session_context = get_session_context(event)
    runtime = get_runtime(event)
    settlement = runtime.record_settlement(
        affordance_id=_affordance_id(event),
        before_state=event.get("before_state", {}),
        after_state=event.get("after_state", {}),
        payment_actual=event.get("payment_actual", {}),
        evidence=event.get("evidence", []),
        horizon_delta=float(event.get("horizon_delta", 0)),
    )
    storage = get_storage(event)
    storage.append_event(
        "post_tool_use_events",
        {
            "id": event.get("id", f"post-tool-{now_iso()}"),
            "tool_name": event.get("tool_name"),
            "affordance_id": _affordance_id(event),
            "desired_direction": event.get("desired_direction"),
            "session_context": session_context,
            "settlement_id": settlement["id"],
            "status": settlement["status"],
            "horizon_delta": float(event.get("horizon_delta", 0)),
        },
    )
    snapshot = runtime.snapshot()
    report = generate_developmental_report(str(runtime.store.root))
    write_stdout_json(
        {
            "hook": "PostToolUse",
            "recorded": True,
            "session_context": session_context,
            "settlement": settlement,
            "snapshot": snapshot,
            "report": report,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
