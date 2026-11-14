from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from godspeed_nav.config import load_config
from godspeed_nav.metrics import estimate_payment, rank_affordances
from godspeed_nav.storage import LedgerStore


class PredictiveModelPort(ABC):
    provider_name = "abstract"

    @abstractmethod
    def predict_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def simulate_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class HeuristicPredictiveModelAdapter(PredictiveModelPort):
    provider_name = "heuristic"

    def predict_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        predictions: list[dict[str, Any]] = []
        settlement_factor = min(0.95, 0.5 + (len(settlement_history) / 2000))

        for candidate in candidates:
            candidate_id = candidate["id"]
            payment_burden = max(
                payment_estimates.get(candidate_id, {}).get("payment_burden", 1.0), 1.0
            )
            expected_delta = float(candidate.get("expected_horizon_delta", 0))
            risk = max(float(candidate.get("risk", 0)), 0.0)
            raw_score = expected_delta / max(
                expected_delta + payment_burden + risk + 1.0, 1.0
            )
            success_probability = max(0.0, min(1.0, raw_score * settlement_factor))
            predictions.append(
                {
                    "candidate_id": candidate_id,
                    "success_probability": round(success_probability, 4),
                    "predicted_horizon_delta": round(
                        expected_delta * success_probability, 4
                    ),
                    "rationale": "local_heuristic_prediction",
                }
            )

        predictions.sort(key=lambda item: item["success_probability"], reverse=True)
        return predictions

    def simulate_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        simulations: list[dict[str, Any]] = []
        for prediction in self.predict_affordances(
            settlement_history, candidates, payment_estimates
        ):
            probability = prediction["success_probability"]
            if probability >= 0.7:
                status = "success"
            elif probability >= 0.35:
                status = "partial"
            else:
                status = "failed"
            simulations.append(
                {
                    "candidate_id": prediction["candidate_id"],
                    "simulated_status": status,
                    "confidence": round(min(0.99, probability + 0.1), 4),
                    "notes": "simulation_suggestion_not_settlement",
                }
            )
        return simulations


class TestingPredictiveModelAdapter(HeuristicPredictiveModelAdapter):
    provider_name = "testing"


class DisabledPredictiveModelAdapter(PredictiveModelPort):
    provider_name = "disabled"

    def predict_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return []

    def simulate_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return []


class SklearnPredictiveModelAdapter(PredictiveModelPort):
    """Built-in scikit-learn predictive provider.

    Registered through ``resolve_model_provider("sklearn")`` but kept
    dormant behind dependency checks, configuration, the existing
    predictive model port, and settlement-history thresholds.

    - Below ``ml_event_threshold``, ``build_predictive_extension_plan``
      returns ``stage: deterministic_only`` and never calls this provider.
    - If scikit-learn is not installed, ``_require_sklearn`` raises a
      clear ``RuntimeError`` directing the operator to install the
      ``ml`` extra.
    - Predictions are advisory only; deterministic ranking and hard gates
      remain required.
    """

    provider_name = "sklearn"

    def _require_sklearn(self) -> None:
        """Lazily import scikit-learn; raise if unavailable."""
        try:
            import sklearn  # noqa: F401 – import check only
        except ImportError as exc:
            raise RuntimeError(
                "sklearn_extra_required: install with uv sync --extra ml"
            ) from exc

    def predict_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self._require_sklearn()

        from godspeed_nav.cognitive_model import build_calibration_frame

        # Extract calibration rows from settlement history.
        frame = build_calibration_frame(settlement_history)

        # If calibration rows are insufficient even though the event-count
        # threshold passed, return empty predictions with an explanatory note.
        if len(frame) < 10:
            return [
                {
                    "candidate_id": c.get("id"),
                    "success_probability": None,
                    "predicted_horizon_delta": None,
                    "rationale": "insufficient_calibration_data",
                    "note": (
                        f"Calibration frame has {len(frame)} rows; "
                        "need at least 10 for sklearn fitting. "
                        "Continuing with deterministic ranking."
                    ),
                }
                for c in candidates
            ]

        # Use simple, inspectable models: logistic regression for
        # settlement success prediction.
        from sklearn.linear_model import LogisticRegression

        feature_cols = [
            "payment_predicted_total",
            "horizon_delta",
            "risk_estimate",
            "debt_estimate",
        ]
        available_cols = [c for c in feature_cols if c in frame.columns]
        X = frame[available_cols].fillna(0).values
        y = frame["settlement_success"].astype(int).values

        # Need both classes for logistic regression.
        if len(set(y)) < 2:
            return [
                {
                    "candidate_id": c.get("id"),
                    "success_probability": None,
                    "predicted_horizon_delta": None,
                    "rationale": "single_class_calibration_data",
                }
                for c in candidates
            ]

        model = LogisticRegression(max_iter=1000, solver="lbfgs")
        model.fit(X, y)

        predictions: list[dict[str, Any]] = []
        for candidate in candidates:
            cid = candidate["id"]
            payment_burden = max(
                payment_estimates.get(cid, {}).get("payment_burden", 1.0), 1.0
            )
            risk = float(candidate.get("risk", 0))
            debt = float(candidate.get("debt", 0))
            horizon_delta = float(candidate.get("expected_horizon_delta", 0))

            # Build feature vector matching training columns.
            feature_values = {
                "payment_predicted_total": payment_burden,
                "horizon_delta": horizon_delta,
                "risk_estimate": risk,
                "debt_estimate": debt,
            }
            x_row = [[feature_values.get(c, 0) for c in available_cols]]
            prob = float(model.predict_proba(x_row)[0][1])

            predictions.append(
                {
                    "candidate_id": cid,
                    "success_probability": round(prob, 4),
                    "predicted_horizon_delta": round(horizon_delta * prob, 4),
                    "rationale": "sklearn_logistic_regression",
                }
            )

        predictions.sort(key=lambda p: p["success_probability"] or 0, reverse=True)
        return predictions

    def simulate_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self._require_sklearn()
        simulations: list[dict[str, Any]] = []
        for prediction in self.predict_affordances(
            settlement_history, candidates, payment_estimates
        ):
            probability = prediction.get("success_probability")
            if probability is None:
                status = "unknown"
            elif probability >= 0.7:
                status = "success"
            elif probability >= 0.35:
                status = "partial"
            else:
                status = "failed"
            simulations.append(
                {
                    "candidate_id": prediction["candidate_id"],
                    "simulated_status": status,
                    "confidence": round(min(0.99, (probability or 0) + 0.1), 4),
                    "notes": "simulation_suggestion_not_settlement",
                }
            )
        return simulations


def resolve_model_provider(provider_name: str) -> PredictiveModelPort:
    registry = {
        "disabled": DisabledPredictiveModelAdapter,
        "heuristic": HeuristicPredictiveModelAdapter,
        "sklearn": SklearnPredictiveModelAdapter,
        "testing": TestingPredictiveModelAdapter,
    }
    normalized = provider_name.strip().lower()
    try:
        return registry[normalized]()
    except KeyError as exc:
        raise ValueError(f"unknown_model_provider: {provider_name}") from exc


def ensure_ml_allowed(settlement_event_count: int, threshold: int = 200) -> bool:
    if settlement_event_count < threshold:
        raise RuntimeError(
            f"insufficient_settlement_history: {settlement_event_count} events available, {threshold} required"
        )
    return True


def build_predictive_extension_plan(
    settlement_history: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    ml_event_threshold: int = 200,
    simulation_threshold: int = 1000,
    model_port: PredictiveModelPort | None = None,
) -> dict[str, Any]:
    settlement_event_count = len(settlement_history)
    active_extensions: list[str] = []
    stage = "deterministic_only"

    if settlement_event_count >= simulation_threshold:
        stage = "simulation_assisted"
        active_extensions = ["ml_prediction", "simulation"]
    elif settlement_event_count >= ml_event_threshold:
        stage = "ml_assisted"
        active_extensions = ["ml_prediction"]

    payment_estimates = _build_candidate_payment_estimates(candidates)
    deterministic_ranking = rank_affordances(candidates, payment_estimates)
    ml_predictions: list[dict[str, Any]] = []
    simulation_results: list[dict[str, Any]] = []

    if model_port and "ml_prediction" in active_extensions:
        ml_predictions = model_port.predict_affordances(
            settlement_history, candidates, payment_estimates
        )
    if model_port and "simulation" in active_extensions:
        simulation_results = model_port.simulate_affordances(
            settlement_history, candidates, payment_estimates
        )

    return {
        "stage": stage,
        "settlement_event_count": settlement_event_count,
        "thresholds": {
            "ml_event_threshold": ml_event_threshold,
            "simulation_threshold": simulation_threshold,
        },
        "active_extensions": active_extensions,
        "deterministic_ranking": deterministic_ranking,
        "ml_predictions": ml_predictions,
        "simulation_results": simulation_results,
    }


def run_predictive_extensions(
    workspace_root: str | Path = ".",
    storage_root: str | Path = ".godspeed-harness",
    candidates: list[dict[str, Any]] | None = None,
    provider_name: str | None = None,
) -> dict[str, Any]:
    config = load_config(workspace_root)
    settlements = LedgerStore(storage_root).read("settlements")
    chosen_provider = provider_name or config.computation.model_provider
    model_port = resolve_model_provider(chosen_provider)
    result = build_predictive_extension_plan(
        settlement_history=settlements,
        candidates=candidates or [],
        ml_event_threshold=config.computation.ml_event_threshold,
        simulation_threshold=config.computation.simulation_threshold,
        model_port=model_port,
    )
    return {
        **result,
        "provider": model_port.provider_name,
        "deterministic_required": True,
        "notes": [
            "predictive_extensions_are_suggestions_only",
            "simulation_does_not_replace_settlement",
        ],
    }


def _build_candidate_payment_estimates(
    candidates: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    payment_estimates: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        payment_estimates[candidate["id"]] = estimate_payment(
            candidate.get("costs", {}),
            candidate.get("weights", {}),
            candidate.get("capacities", {}),
        )
    return payment_estimates


__all__ = [
    "DisabledPredictiveModelAdapter",
    "HeuristicPredictiveModelAdapter",
    "PredictiveModelPort",
    "SklearnPredictiveModelAdapter",
    "TestingPredictiveModelAdapter",
    "build_predictive_extension_plan",
    "ensure_ml_allowed",
    "resolve_model_provider",
    "run_predictive_extensions",
]
