from __future__ import annotations

import math
from typing import Any


NEGATIVE_POLARITY_TOKENS = {
    "bug",
    "bugs",
    "defect",
    "defects",
    "error",
    "errors",
    "failure",
    "failures",
    "risk",
    "debt",
    "latency",
}


def _classify_evidence(evidence: list[Any]) -> tuple[list[str], list[str]]:
    accepted: list[str] = []
    rejected: list[str] = []
    for item in evidence:
        text = str(item).strip()
        if not text:
            continue
        if text.lower().startswith("intent:"):
            rejected.append(text)
        else:
            accepted.append(text)
    return accepted, rejected


def _delta_classification(key: str, before: Any, after: Any) -> int:
    negative_polarity = any(token in key.lower() for token in NEGATIVE_POLARITY_TOKENS)
    if isinstance(before, bool) or isinstance(after, bool):
        raw_delta = int(bool(after)) - int(bool(before))
        return -raw_delta if negative_polarity else raw_delta
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        if after > before:
            return -1 if negative_polarity else 1
        if after < before:
            return 1 if negative_polarity else -1
        return 0
    if before == after:
        return 0
    raw_delta = 1 if after else -1
    return -raw_delta if negative_polarity else raw_delta


def _score_against_desired_state(
    before_state: dict[str, Any],
    after_state: dict[str, Any],
    desired_state: dict[str, Any],
) -> tuple[float, list[str], list[str]]:
    improved: list[str] = []
    regressed: list[str] = []
    total = 0
    progress = 0.0

    for key, desired_value in desired_state.items():
        total += 1
        before_distance = abs(float(desired_value) - float(before_state.get(key, 0)))
        after_distance = abs(float(desired_value) - float(after_state.get(key, 0)))
        if after_distance < before_distance:
            improved.append(key)
            progress += 1.0
        elif after_distance > before_distance:
            regressed.append(key)
            progress -= 1.0
        elif after_state.get(key) == desired_value:
            improved.append(key)
            progress += 1.0

    score = max(0.0, progress / max(1, total))
    return score, improved, regressed


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
    evaluator_config = evaluator_config or {}
    evidence = evaluator_config.get("evidence", [])
    accepted_evidence, rejected_evidence = _classify_evidence(evidence)
    if not accepted_evidence:
        return {
            "settlement_score": 0,
            "status": "failed",
            "evidence_summary": "intent_only",
            "accepted_evidence": [],
            "rejected_evidence": rejected_evidence,
            "missing_evidence": ["observable_consequence"],
            "improved_keys": [],
            "regression_keys": [],
            "payment_summary": payment_actual,
        }

    desired_state = desired_direction.get("desired_state")
    if isinstance(desired_state, dict) and desired_state:
        score, improved_keys, regression_keys = _score_against_desired_state(
            before_state,
            after_state,
            desired_state,
        )
    else:
        all_keys = set(before_state) | set(after_state)
        improved_keys = [
            key for key in all_keys if _delta_classification(key, before_state.get(key), after_state.get(key)) > 0
        ]
        regression_keys = [
            key for key in all_keys if _delta_classification(key, before_state.get(key), after_state.get(key)) < 0
        ]
        score = max(0.0, (len(improved_keys) - len(regression_keys)) / max(1, len(all_keys)))
        if improved_keys and regression_keys and score == 0.0:
            score = 0.5

    missing_evidence: list[str] = []
    if not improved_keys and not regression_keys:
        missing_evidence.append("observable_change")
        score = 0.0

    if regression_keys and score >= 0.7:
        score = min(score, 0.69)

    status = "success" if score >= 0.7 and not regression_keys else "partial" if score > 0 else "failed"
    return {
        "settlement_score": score,
        "status": status,
        "evidence_summary": "; ".join(accepted_evidence),
        "accepted_evidence": accepted_evidence,
        "rejected_evidence": rejected_evidence,
        "missing_evidence": missing_evidence,
        "improved_keys": improved_keys,
        "regression_keys": regression_keys,
        "payment_summary": payment_actual,
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
