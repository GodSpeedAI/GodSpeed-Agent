"""Cognitive model computational core.

Implements the deterministic mathematical layer from ``tmp/math.md``:
representational coordinates, burden kernel, hard gates, spendability
scoring, and advisory controller ranking.

All formulas use measurable inputs, justified functional forms,
bootstrappable defaults, calibration paths, and failure criteria
as required by the math specification design contract (Section 0).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp *value* to ``[low, high]``."""
    return max(low, min(high, value))


# ---------------------------------------------------------------------------
# Section 4–5: Representational coordinates and burden
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RepresentationalCoordinates:
    """Position in the default two-axis projection (scope, givenness).

    ``scope``: 0 = maximally general, 1 = maximally specific.
    ``givenness``: 0 = maximally abstract, 1 = maximally concrete.
    """

    scope: float
    givenness: float

    def vector(self) -> np.ndarray:
        return np.array([clamp(self.scope), clamp(self.givenness)], dtype=float)


@dataclass(frozen=True)
class BurdenParameters:
    """Weights for the representational burden quadratic form.

    The burden matrix ``M`` is built as::

        M = [[w_scope,      w_interaction],
             [w_interaction, w_givenness  ]]

    Strict positive-definiteness is guaranteed by the ``matrix_floor``
    parameter (δ in the spec).  The default matrix is approximately
    Euclidean with a small positive floor.
    """

    w_scope: float = 1.0
    w_givenness: float = 1.0
    w_interaction: float = 0.0
    matrix_floor: float = 0.05
    overflow_weight: float = 0.25

    def matrix(self) -> np.ndarray:
        """Return the 2×2 burden matrix (not yet floored).

        Callers that need strict positive-definiteness should add
        ``matrix_floor * I`` separately or use the burden function
        which handles this internally.
        """
        return np.array(
            [
                [self.w_scope, self.w_interaction],
                [self.w_interaction, self.w_givenness],
            ],
            dtype=float,
        )


def compute_representational_burden(
    current: RepresentationalCoordinates,
    target: RepresentationalCoordinates,
    distinctions_current: int,
    distinctions_max: int = 20,
    parameters: BurdenParameters | None = None,
) -> dict[str, Any]:
    """Compute representational burden (Section 5 of the math spec).

    Returns a dict with:
    - ``delta``: scope and givenness deltas
    - ``burden_raw``: ``sqrt(ΔRᵀ M ΔR)`` before overflow
    - ``burden``: total burden including scope overflow
    - ``burden_max``: maximum in-bounds burden under current weights
    - ``scope_overflow``: over-specification penalty
    - ``matrix_floor``: the δ parameter used
    """
    parameters = parameters or BurdenParameters()
    delta = target.vector() - current.vector()

    # Build strictly positive-definite matrix: M + δI
    matrix = parameters.matrix() + parameters.matrix_floor * np.eye(2)

    burden_raw = float(np.sqrt(max(delta.T @ matrix @ delta, 0.0)))
    scope_overflow = max(0.0, distinctions_current / max(distinctions_max, 1) - 1.0)
    burden = burden_raw + parameters.overflow_weight * scope_overflow
    burden_max = float(np.sqrt(parameters.w_scope + parameters.w_givenness))

    return {
        "delta": {
            "scope": round(float(delta[0]), 10),
            "givenness": round(float(delta[1]), 10),
        },
        "burden": burden,
        "burden_raw": burden_raw,
        "burden_max": burden_max,
        "scope_overflow": scope_overflow,
        "matrix_floor": parameters.matrix_floor,
    }


# ---------------------------------------------------------------------------
# Section 7: Hard gates and continuous spendability
# ---------------------------------------------------------------------------

# Section 13.1: Risk ceilings by context
RISK_CEILINGS: dict[str, float] = {
    "exploration": 0.50,
    "production": 0.30,
    "recovery": 0.20,
    "safety_critical": 0.05,
}

# Section 13.1: Debt ceilings by context
DEBT_CEILINGS: dict[str, float] = {
    "exploration": 0.50,
    "production": 0.30,
    "recovery": 0.15,
    "safety_critical": 0.05,
}

# Section 7.3: Spendability factor weights
SPENDABILITY_WEIGHTS: dict[str, float] = {
    "visibility": 0.20,
    "reachability": 0.25,
    "payment_fit": 0.35,
    "capability_support": 0.20,
}


def _payment_exceeds_capacity(candidate: dict[str, Any]) -> bool:
    """Return True if any payment currency exceeds capacity (Section 7.2)."""
    required = candidate.get("payment_required", {})
    capacity = candidate.get("payment_capacity", {})
    for currency, amount in required.items():
        if float(amount) > float(capacity.get(currency, 0)):
            return True
    return False


def _spendability_factors(candidate: dict[str, Any]) -> dict[str, float]:
    """Compute the four spendability factors (Section 7.4).

    V — Visibility: 1.0 if pathway and expected settlement are described.
    R — Reachability: fraction of preconditions met.
    F — Payment fit: min over currencies of ``1 - required/capacity``.
    C — Capability support: fraction of required capabilities active.
    """
    # Visibility
    has_pathway = bool(candidate.get("pathway"))
    has_settlement = bool(candidate.get("expected_settlement"))
    visibility = (
        1.0 if has_pathway and has_settlement else (0.5 if has_pathway else 0.0)
    )

    # Reachability
    required_pre = candidate.get("required_preconditions", [])
    met_pre = candidate.get("met_preconditions", [])
    if required_pre:
        reachability = len(set(met_pre) & set(required_pre)) / len(required_pre)
    else:
        reachability = 1.0

    # Payment fit (min rule — most constrained currency is binding)
    payment_required = candidate.get("payment_required", {})
    payment_capacity = candidate.get("payment_capacity", {})
    if payment_required:
        fits = []
        for currency, amount in payment_required.items():
            cap = float(payment_capacity.get(currency, 0))
            fits.append(clamp(1.0 - float(amount) / max(cap, 1e-9), 0.0, 1.0))
        payment_fit = min(fits)
    else:
        payment_fit = 1.0

    # Capability support
    required_caps = candidate.get("required_capabilities", [])
    active_caps = candidate.get("active_capabilities", [])
    if required_caps:
        capability_support = len(set(active_caps) & set(required_caps)) / len(
            required_caps
        )
    else:
        capability_support = 1.0

    return {
        "visibility": visibility,
        "reachability": reachability,
        "payment_fit": payment_fit,
        "capability_support": capability_support,
    }


def evaluate_candidate_model(
    candidate: dict[str, Any],
    context: str = "production",
) -> dict[str, Any]:
    """Evaluate a candidate through hard gates then continuous spendability.

    Implements Sections 7.1–7.4 of the math spec.  Hard gates are
    evaluated first; if any gate fails the candidate is blocked and
    ``spendability_score`` is ``None``.  Otherwise the continuous
    spendability score is computed as a weighted sum of visibility,
    reachability, payment fit, and capability support.
    """
    blocking_reasons: list[str] = []
    risk_ceiling = RISK_CEILINGS.get(context, RISK_CEILINGS["production"])
    debt_ceiling = DEBT_CEILINGS.get(context, DEBT_CEILINGS["production"])
    risk = float(candidate.get("risk", 0.0))
    debt = float(candidate.get("debt", 0.0))

    if not candidate.get("governance_allowed", True):
        blocking_reasons.append("governance_blocked")
    if not candidate.get("settlement_accessible", True):
        blocking_reasons.append("settlement_inaccessible")
    if _payment_exceeds_capacity(candidate):
        blocking_reasons.append("payment_capacity_exceeded")
    if risk > risk_ceiling:
        blocking_reasons.append("risk_ceiling_exceeded")
    if debt > debt_ceiling:
        blocking_reasons.append("debt_ceiling_exceeded")

    if blocking_reasons:
        return {
            "candidate_id": candidate.get("id"),
            "allowed": False,
            "blocking_reasons": blocking_reasons,
            "spendability_score": None,
            "factors": {},
            "risk_ceiling": risk_ceiling,
            "debt_ceiling": debt_ceiling,
        }

    factors = _spendability_factors(candidate)
    score = sum(
        SPENDABILITY_WEIGHTS[key] * factors[key] for key in SPENDABILITY_WEIGHTS
    )
    return {
        "candidate_id": candidate.get("id"),
        "allowed": True,
        "blocking_reasons": [],
        "spendability_score": score,
        "factors": factors,
        "risk_ceiling": risk_ceiling,
        "debt_ceiling": debt_ceiling,
    }


# ---------------------------------------------------------------------------
# Section 13: Cybernetic controller – advisory ranking
# ---------------------------------------------------------------------------

# Section 13.6: Default controller weights
CONTROLLER_WEIGHTS: dict[str, float] = {
    "burden": 0.5,
    "risk": 1.5,
    "debt": 0.8,
    "horizon_gain": 0.3,
    "direction": 0.5,
}


def rank_candidates_by_controller(
    candidates: list[dict[str, Any]],
    context: str = "production",
) -> dict[str, Any]:
    """Rank candidates using the controller objective (Section 13.2).

    For each allowed candidate the objective is::

        objective = error_cost
                  + λ·burden
                  + μ·risk
                  + ν·debt
                  - η·horizon_gain
                  - κ·direction_score

    Lower objective ranks first.  Rejected candidates remain rejected
    regardless of expected horizon delta.

    Expected candidate dict fields (missing keys default to 0.0):

    - ``error_cost``: expected remaining error magnitude after action.
      Populate via ``compute_error(desired_state, expected_post_action_state)["error_magnitude"]``
      when available; defaults to 0.0 (dormant).
    - ``burden``: representational burden (from ``compute_representational_burden``).
    - ``risk``: compensable risk estimate.
    - ``debt``: expected future payment burden.
    - ``expected_horizon_delta``: expected horizon expansion.
    - ``direction_score``: alignment with active non-gated directions.
    """
    ranked: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for candidate in candidates:
        evaluation = evaluate_candidate_model(candidate, context=context)

        if not evaluation["allowed"]:
            rejected.append(
                {
                    "candidate_id": candidate.get("id"),
                    "blocking_reasons": evaluation["blocking_reasons"],
                }
            )
            continue

        risk = float(candidate.get("risk", 0.0))
        debt = float(candidate.get("debt", 0.0))
        horizon_gain = float(candidate.get("expected_horizon_delta", 0))
        direction_score = float(candidate.get("direction_score", 0.0))
        burden = float(candidate.get("burden", 0.0))
        error_cost = float(candidate.get("error_cost", 0.0))

        objective = (
            error_cost
            + CONTROLLER_WEIGHTS["burden"] * burden
            + CONTROLLER_WEIGHTS["risk"] * risk
            + CONTROLLER_WEIGHTS["debt"] * debt
            - CONTROLLER_WEIGHTS["horizon_gain"] * horizon_gain
            - CONTROLLER_WEIGHTS["direction"] * direction_score
        )

        ranked.append(
            {
                "candidate_id": candidate.get("id"),
                "objective": objective,
                "spendability_score": evaluation["spendability_score"],
                "factors": evaluation["factors"],
            }
        )

    ranked.sort(key=lambda item: item["objective"])
    return {"ranked": ranked, "rejected": rejected}


# ---------------------------------------------------------------------------
# Section 5.5 / 17: Calibration dataset builder
# ---------------------------------------------------------------------------

import pandas as pd


def _total_payment(payment: dict[str, Any] | None) -> float:
    """Sum payment currency values into a scalar total."""
    if not payment:
        return 0.0
    return sum(float(v) for v in payment.values())


def build_calibration_frame(
    settlements: list[dict[str, Any]],
) -> pd.DataFrame:
    """Extract calibration fields from settlement records into a DataFrame.

    Only settlements that contain a ``model_calibration`` object are
    included.  Settlements missing calibration data are silently skipped.

    The resulting DataFrame has columns:
    ``settlement_id``, ``payment_predicted_total``, ``payment_actual_total``,
    ``payment_error``, ``settlement_success``, ``settlement_score``,
    ``horizon_delta``, ``risk_estimate``, ``debt_estimate``.
    """
    rows: list[dict[str, Any]] = []
    for settlement in settlements:
        cal = settlement.get("model_calibration")
        if not cal:
            continue

        predicted_total = _total_payment(cal.get("payment_predicted"))
        actual_total = _total_payment(cal.get("payment_actual"))
        payment_error = abs(actual_total - predicted_total)

        rows.append(
            {
                "settlement_id": settlement.get("id"),
                "payment_predicted_total": predicted_total,
                "payment_actual_total": actual_total,
                "payment_error": payment_error,
                "settlement_success": bool(cal.get("settlement_success", False)),
                "settlement_score": float(cal.get("settlement_score", 0.0)),
                "horizon_delta": float(cal.get("horizon_delta", 0)),
                "risk_estimate": cal.get("risk_estimate"),
                "debt_estimate": cal.get("debt_estimate"),
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "settlement_id",
            "payment_predicted_total",
            "payment_actual_total",
            "payment_error",
            "settlement_success",
            "settlement_score",
            "horizon_delta",
            "risk_estimate",
            "debt_estimate",
        ],
    )
