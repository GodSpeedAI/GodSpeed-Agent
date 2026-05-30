#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from godspeed_nav.schemas import now_iso
from godspeed_nav.storage import LedgerStore
from godspeed_nav.trajectory import update_trajectory
from hooks.common import read_stdin_json, write_stdout_json


def main() -> int:
    event = read_stdin_json()
    storage = LedgerStore(event.get("storage_root", ".godspeed-harness"))
    trajectory = update_trajectory(
        previous_theta=float(event.get("previous_theta", 0)),
        previous_radius=float(event.get("previous_radius", 1)),
        settlement_score=float(event.get("settlement_score", 0)),
        horizon_delta=float(event.get("horizon_delta", 0)),
    )
    record = {"id": event.get("id", f"trajectory-{now_iso()}"), **trajectory, "created_at": now_iso()}
    storage.append("trajectories", record)
    write_stdout_json({"hook": "Stop", "recorded": True, "trajectory": trajectory})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
