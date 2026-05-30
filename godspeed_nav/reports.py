from __future__ import annotations

from pathlib import Path
from typing import Any

from godspeed_nav.storage import LedgerStore
from godspeed_nav.trajectory import detect_circular_motion


def generate_developmental_report(storage_root: str | Path) -> dict[str, Any]:
    store = LedgerStore(storage_root)
    desired_directions = store.read("desired_directions")
    payments = store.read("payments")
    settlements = store.read("settlements")
    trajectories = store.read("trajectories")
    capabilities = store.read("capabilities")

    settlement_quality: dict[str, int] = {}
    for settlement in settlements:
        status = settlement.get("status", "unknown")
        settlement_quality[status] = settlement_quality.get(status, 0) + 1

    total_burden = sum(float(payment.get("payment_burden", 0)) for payment in payments)
    trajectory_points = [
        {
            "theta": float(item.get("new_theta", item.get("theta", 0))),
            "radius": float(item.get("new_radius", item.get("radius", 1))),
        }
        for item in trajectories
    ]
    circular = detect_circular_motion(trajectory_points) if trajectory_points else {"circular_motion": False}
    latest = trajectory_points[-1] if trajectory_points else {"theta": 0, "radius": 1}

    latest_capabilities: dict[str, dict[str, Any]] = {}
    for capability in capabilities:
        capability_id = capability.get("id")
        if capability_id:
            latest_capabilities[capability_id] = capability

    metabolization_candidates = [
        capability
        for capability in latest_capabilities.values()
        if capability.get("status") in {"capability", "substrate_candidate"}
    ]

    return {
        "settlement_quality": settlement_quality,
        "payment_debt": {
            "total_burden": total_burden,
            "payment_count": len(payments),
        },
        "trajectory": {
            "latest_theta": latest["theta"],
            "latest_radius": latest["radius"],
            "circular_motion": circular["circular_motion"],
            "radius_growth": circular.get("radius_growth", 0),
        },
        "horizon": {
            "active_direction_count": len(
                [item for item in desired_directions if item.get("status") == "active"]
            )
        },
        "metabolization": {
            "candidate_count": len(metabolization_candidates),
            "candidate_ids": [item.get("id") for item in metabolization_candidates],
        },
    }
