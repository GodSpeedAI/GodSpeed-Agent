from __future__ import annotations

from typing import Any


def review_positive_disintegration(
    structures: list[dict[str, Any]],
    require_human_review: bool = True,
) -> dict[str, Any]:
    dissolution = [
        item for item in structures if item.get("settlement_score", 0) < 0.3 and item.get("risk", "high") != "high"
    ]
    metabolization = [
        item
        for item in structures
        if item.get("settlement_score", 0) >= 0.8
        and item.get("attention_burden", 1) <= 0.2
        and item.get("repetitions", 0) >= 3
    ]
    return {
        "dissolution_candidates": dissolution,
        "metabolization_candidates": metabolization,
        "requires_human_review": require_human_review,
        "risk_notes": "Human review required before destructive dissolution." if require_human_review else "",
    }
