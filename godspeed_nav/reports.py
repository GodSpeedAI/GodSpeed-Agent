from __future__ import annotations

from pathlib import Path
from typing import Any

from godspeed_nav.schemas import infer_capability_lifecycle
from godspeed_nav.storage import LedgerStore
from godspeed_nav.trajectory import detect_circular_motion


def generate_developmental_report(storage_root: str | Path) -> dict[str, Any]:
    store = LedgerStore(storage_root)
    desired_directions = store.read("desired_directions")
    representational_states = store.read("representational_states")
    affordance_paths = store.read("affordance_paths")
    payments = store.read("payments")
    settlements = store.read("settlements")
    trajectories = store.read("trajectories")
    repetition_schedules = store.read("repetition_schedules")
    capabilities = store.read("capabilities")
    developmental_memory = store.query_developmental_memory()
    critique_findings = store.read("critique_findings")

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
    latest_settlement = settlements[-1] if settlements else None

    latest_capabilities: dict[str, dict[str, Any]] = {}
    for capability in capabilities:
        capability_id = capability.get("id")
        if capability_id:
            latest_capabilities[capability_id] = capability

    lifecycle_counts = {
        "latent": 0,
        "active": 0,
        "repeated": 0,
        "metabolized": 0,
        "brittle": 0,
        "retired": 0,
    }
    for capability in latest_capabilities.values():
        lifecycle_state = capability.get("lifecycle_state") or infer_capability_lifecycle(
            settlement_count=int(capability.get("settlement_count", 0)),
            stability=float(capability.get("stability", 0.0)),
            metabolization_score=float(capability.get("metabolization_score", 0.0)),
            retired=bool(capability.get("retired", False)),
        )
        lifecycle_counts[lifecycle_state] = lifecycle_counts.get(lifecycle_state, 0) + 1

    metabolization_candidates = [
        capability
        for capability in latest_capabilities.values()
        if capability.get("status") in {"capability", "substrate_candidate"}
    ]
    active_direction_ids = [item.get("id") for item in desired_directions if item.get("status") == "active"]
    capability_ids = sorted(latest_capabilities)
    substrate_ids = [
        capability_id
        for capability_id, capability in latest_capabilities.items()
        if capability.get("lifecycle_state") == "metabolized"
    ]
    lock_in_risks = ["circular_motion" if circular.get("circular_motion") else None]
    lock_in_risks = [risk for risk in lock_in_risks if risk]

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
        "representational_state": {
            "count": len(representational_states),
            "latest": representational_states[-1] if representational_states else None,
        },
        "affordance_paths": {
            "count": len(affordance_paths),
            "latest": affordance_paths[-1] if affordance_paths else None,
        },
        "metabolization": {
            "candidate_count": len(metabolization_candidates),
            "candidate_ids": [item.get("id") for item in metabolization_candidates],
        },
        "capabilities": {
            "count": len(latest_capabilities),
            "lifecycle_counts": lifecycle_counts,
            "latest": list(latest_capabilities.values())[-1] if latest_capabilities else None,
        },
        "identity_state": {
            "active_direction_ids": active_direction_ids,
            "capability_ids": capability_ids,
            "substrate_ids": substrate_ids,
            "lock_in_risks": lock_in_risks,
        },
        "latest_settlement": latest_settlement,
        "repetition": {
            "schedule_count": len(repetition_schedules),
            "latest": repetition_schedules[-1] if repetition_schedules else None,
        },
        "self_critique": {
            "finding_count": len(critique_findings),
            "finding_codes": [item.get("code") for item in critique_findings if item.get("code")],
            "latest": critique_findings[-1] if critique_findings else None,
        },
        "developmental_memory": developmental_memory,
    }
