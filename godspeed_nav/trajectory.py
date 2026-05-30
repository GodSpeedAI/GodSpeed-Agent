from __future__ import annotations

import math
from typing import Any


def update_trajectory(
    previous_theta: float,
    previous_radius: float,
    settlement_score: float,
    horizon_delta: float,
) -> dict[str, Any]:
    theta_delta = max(0.1, abs(horizon_delta) * 0.1)
    new_theta = previous_theta + theta_delta
    radius_growth = max(0.0, settlement_score - 0.5) * max(0.0, horizon_delta)
    new_radius = previous_radius + radius_growth
    return {
        "new_theta": new_theta,
        "new_radius": new_radius,
        "coordinate": {
            "real": new_radius * math.cos(new_theta),
            "imag": new_radius * math.sin(new_theta),
        },
        "circular_motion_flags": detect_circular_motion(
            [
                {"theta": previous_theta, "radius": previous_radius},
                {"theta": new_theta, "radius": new_radius},
            ]
        ),
    }


def detect_circular_motion(
    trajectory_records: list[dict[str, float]],
    min_rotation: float = math.tau,
    max_radius_growth: float = 0.1,
) -> dict[str, Any]:
    if len(trajectory_records) < 2:
        return {"circular_motion": False, "rotation": 0.0, "radius_growth": 0.0}

    rotation = abs(trajectory_records[-1]["theta"] - trajectory_records[0]["theta"])
    radius_growth = trajectory_records[-1]["radius"] - trajectory_records[0]["radius"]
    return {
        "circular_motion": rotation >= min_rotation and radius_growth <= max_radius_growth,
        "rotation": rotation,
        "radius_growth": radius_growth,
    }
