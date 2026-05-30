#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from godspeed_nav.schemas import now_iso
from godspeed_nav.reports import generate_developmental_report
from godspeed_nav.trajectory import update_trajectory
from hooks.common import read_stdin_json, write_stdout_json
from hooks.common import get_runtime, get_session_context, get_storage


def main() -> int:
    event = read_stdin_json()
    session_context = get_session_context(event)
    runtime = get_runtime(event)
    snapshot = runtime.snapshot()
    latest_trajectory = snapshot.get("latest_trajectory") or {}
    storage = get_storage(event)
    settlements = storage.read("settlements")
    latest_settlement = settlements[-1] if settlements else {}
    trajectory = update_trajectory(
        previous_theta=float(
            event.get("previous_theta", latest_trajectory.get("new_theta", latest_trajectory.get("theta", 0)))
        ),
        previous_radius=float(
            event.get("previous_radius", latest_trajectory.get("new_radius", latest_trajectory.get("radius", 1)))
        ),
        settlement_score=float(event.get("settlement_score", latest_settlement.get("score", 0))),
        horizon_delta=float(event.get("horizon_delta", 0)),
    )
    record = {"id": event.get("id", f"trajectory-{now_iso()}"), **trajectory, "created_at": now_iso()}
    storage.append("trajectories", record)
    storage.append_event(
        "stop_events",
        {
            "id": f"stop-{now_iso()}",
            "session_context": session_context,
            "trajectory_id": record["id"],
            "latest_settlement_id": latest_settlement.get("id"),
            "active_direction_count": len(snapshot.get("active_directions", [])),
        },
    )
    report = generate_developmental_report(str(runtime.store.root))
    write_stdout_json(
        {
            "hook": "Stop",
            "recorded": True,
            "session_context": session_context,
            "trajectory": trajectory,
            "report": report,
            "snapshot": runtime.snapshot(),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
