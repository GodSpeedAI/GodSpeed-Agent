#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from godspeed_nav.metrics import score_settlement
from godspeed_nav.runtime import NavigationRuntime
from godspeed_nav.schemas import now_iso
from godspeed_nav.storage import LedgerStore
from hooks.common import read_stdin_json, write_stdout_json


def main() -> int:
    event = read_stdin_json()
    storage = LedgerStore(event.get("storage_root", ".godspeed-harness"))
    settlement = score_settlement(
        event.get("before_state", {}),
        event.get("after_state", {}),
        event.get("desired_direction", {}),
        event.get("payment_actual", {}),
        {"evidence": event.get("evidence", [])},
    )
    record = {
        "id": event.get("id", f"settlement-{now_iso()}"),
        "affordance_id": event.get("affordance_id"),
        "before_state": event.get("before_state", {}),
        "after_state": event.get("after_state", {}),
        "payment_actual": event.get("payment_actual", {}),
        "score": settlement["settlement_score"],
        "status": settlement["status"],
        "evidence": event.get("evidence", []),
        "created_at": now_iso(),
    }
    storage.append("settlements", record)
    snapshot = NavigationRuntime(event.get("storage_root", ".godspeed-harness")).snapshot()
    write_stdout_json(
        {"hook": "PostToolUse", "recorded": True, "settlement": settlement, "snapshot": snapshot}
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
