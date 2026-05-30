from __future__ import annotations

import math
from typing import Any


def compute_error(
    desired_state: dict[str, float],
    observed_state: dict[str, float],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    weights = weights or {}
    error_vector: dict[str, float] = {}
    for key, desired in desired_state.items():
        observed = observed_state.get(key, 0)
        error_vector[key] = (desired - observed) * weights.get(key, 1)
    magnitude = math.sqrt(sum(value**2 for value in error_vector.values()))
    dominant = max(error_vector, key=lambda key: abs(error_vector[key])) if error_vector else None
    return {
        "error_vector": error_vector,
        "error_magnitude": magnitude,
        "dominant_error": dominant,
    }


def estimate_payment(
    costs: dict[str, float],
    weights: dict[str, float] | None = None,
    capacities: dict[str, float] | None = None,
) -> dict[str, Any]:
    weights = weights or {}
    capacities = capacities or {}
    weighted_costs = {key: value * weights.get(key, 1) for key, value in costs.items()}
    payment_burden = math.sqrt(sum(value**2 for value in weighted_costs.values()))
    capacity_norm = math.sqrt(sum(value**2 for value in capacities.values()))
    dominant_cost = max(weighted_costs, key=lambda key: abs(weighted_costs[key])) if weighted_costs else None
    spendability = "affordable" if capacity_norm == 0 or payment_burden <= capacity_norm else "unaffordable"
    return {
        "payment_burden": payment_burden,
        "capacity_norm": capacity_norm,
        "spendability": spendability,
        "dominant_cost": dominant_cost,
    }


def score_settlement(
    before_state: dict[str, Any],
    after_state: dict[str, Any],
    desired_direction: dict[str, Any],
    payment_actual: dict[str, float],
    evaluator_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del desired_direction, payment_actual
    evaluator_config = evaluator_config or {}
    evidence = evaluator_config.get("evidence", [])
    if not evidence or all(str(item).lower().startswith("intent:") for item in evidence):
        return {"settlement_score": 0, "status": "failed", "evidence_summary": "intent_only"}

    changed_keys = [key for key, value in after_state.items() if before_state.get(key) != value]
    score = min(1.0, len(changed_keys) / max(1, len(after_state)))
    status = "success" if score >= 0.7 else "partial" if score > 0 else "failed"
    return {
        "settlement_score": score,
        "status": status,
        "evidence_summary": "; ".join(map(str, evidence)),
    }


def rank_affordances(
    candidates: list[dict[str, Any]],
    payment_estimates: dict[str, dict[str, float]],
) -> dict[str, Any]:
    ranked: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = candidate["id"]
        payment = payment_estimates.get(candidate_id)
        if not payment:
            rejected.append({"id": candidate_id, "reason": "missing_payment_estimate"})
            continue
        burden = max(payment.get("payment_burden", 0), 0.000001)
        risk = max(candidate.get("risk", 0), 0)
        score = candidate.get("expected_horizon_delta", 0) / (burden * (1 + risk))
        ranked.append({**candidate, "rank_score": score})

    ranked.sort(key=lambda item: item["rank_score"], reverse=True)
    return {
        "ranked_affordances": ranked,
        "next_recommended_affordance": ranked[0] if ranked else None,
        "rejected_candidates": rejected,
    }
