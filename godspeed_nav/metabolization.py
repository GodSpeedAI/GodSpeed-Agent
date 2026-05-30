from __future__ import annotations

from typing import Any


def compute_metabolization(
    capability_id: str,
    settlement_events: list[dict[str, Any]],
    reuse_frequency: int,
    context_diversity: int,
    stability: float,
    maintenance_burden: float,
    attention_burden: float,
) -> dict[str, Any]:
    missing: list[str] = []
    if len(settlement_events) < 3:
        missing.append("settlement_events")
    if reuse_frequency < 3:
        missing.append("reuse_frequency")
    if context_diversity < 2:
        missing.append("context_diversity")
    if stability < 0.8:
        missing.append("stability")
    if maintenance_burden > 0.3:
        missing.append("maintenance_burden")
    if attention_burden > 0.3:
        missing.append("attention_burden")

    positive_factors = 6 - len(missing)
    score = max(0.0, min(1.0, positive_factors / 6))
    return {
        "capability_id": capability_id,
        "metabolization_score": score,
        "status_recommendation": "substrate_candidate" if score >= 0.75 and not missing else "not_metabolized",
        "missing_evidence": missing,
    }


def plan_repetition(
    affordance_id: str,
    capability_status: str,
    variation_coverage: int,
    circular_motion: bool = False,
) -> dict[str, Any]:
    return {
        "affordance_id": affordance_id,
        "status": "satisfied" if capability_status == "substrate_candidate" else "scheduled",
        "trigger": "successful_not_metabolized_settlement",
        "variation_coverage": variation_coverage,
        "next_condition": "changed_conditions",
        "recommended_delay": "next_affordable_variation",
        "critique_escalation": "circular_motion" if circular_motion else None,
    }
