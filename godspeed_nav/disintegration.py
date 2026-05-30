from __future__ import annotations

from typing import Any

from godspeed_nav.policies import enforce_disintegration_review


def review_positive_disintegration(
    structures: list[dict[str, Any]],
    require_human_review: bool = True,
) -> dict[str, Any]:
    blocked = [
        item
        for item in structures
        if item.get("risk", "low") == "high" and require_human_review
    ]
    dissolution = [
        item
        for item in structures
        if item.get("settlement_score", 0) < 0.3 and item.get("risk", "high") != "high"
    ]
    metabolization = [
        item
        for item in structures
        if item.get("settlement_score", 0) >= 0.8
        and item.get("attention_burden", 1) <= 0.2
        and item.get("repetitions", 0) >= 3
    ]
    salvage_plan = {
        item["id"]: item.get("salvageable_elements", [])
        for item in dissolution + blocked
        if item.get("id")
    }
    policy_gate = enforce_disintegration_review(
        candidate={"risk": "high" if blocked else "low"},
        policy={"require_human_review_for_disintegration": require_human_review},
    )
    return {
        "blocked_candidates": blocked,
        "dissolution_candidates": dissolution,
        "metabolization_candidates": metabolization,
        "salvage_plan": salvage_plan,
        "requires_human_review": require_human_review,
        "policy_gate": policy_gate.to_dict(),
        "risk_notes": "Human review required before destructive dissolution." if require_human_review else "",
    }
