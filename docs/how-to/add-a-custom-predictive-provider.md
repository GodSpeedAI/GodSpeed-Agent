# How-To: Add a Custom Predictive Provider

This guide explains how to extend GodSpeed-Agent's machine learning layer by implementing a custom `PredictiveModelPort`.

---

## 1. Goal

Implement, register, and verify a custom predictive provider (e.g. an XGBoost model, an LLM scoring proxy, or a domain-specific Bayesian estimator) to predict candidate success probabilities.

---

## 2. The `PredictiveModelPort` Contract

All predictive providers must inherit from `PredictiveModelPort` in `godspeed_nav/ml.py`:

```python
from abc import ABC, abstractmethod
from typing import Any

class PredictiveModelPort(ABC):
    provider_name: str = "abstract"

    @abstractmethod
    def predict_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return candidate predictions sorted by success probability."""
        raise NotImplementedError

    @abstractmethod
    def simulate_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return simulated candidate execution outcomes."""
        raise NotImplementedError
```

---

## 3. Implementation Example: Custom Bayesian Estimator

Create your adapter in `godspeed_nav/ml.py`:

```python
class BayesianPredictiveModelAdapter(PredictiveModelPort):
    provider_name = "bayesian"

    def predict_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        predictions = []
        # Calculate historical success rate
        successes = sum(1 for s in settlement_history if s.get("status") == "success")
        total = max(1, len(settlement_history))
        base_rate = successes / total

        for candidate in candidates:
            c_id = candidate["id"]
            risk = float(candidate.get("risk", 0.0))
            # Adjust probability based on candidate risk
            prob = max(0.0, min(1.0, base_rate * (1.0 - risk)))

            predictions.append({
                "candidate_id": c_id,
                "success_probability": round(prob, 4),
                "predicted_horizon_delta": round(float(candidate.get("expected_horizon_delta", 0)) * prob, 4),
                "rationale": "custom_bayesian_base_rate"
            })

        predictions.sort(key=lambda item: item["success_probability"], reverse=True)
        return predictions

    def simulate_affordances(
        self,
        settlement_history: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        payment_estimates: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "candidate_id": pred["candidate_id"],
                "simulated_status": "success" if pred["success_probability"] >= 0.7 else "partial",
                "confidence": pred["success_probability"],
                "notes": "bayesian_simulation"
            }
            for pred in self.predict_affordances(settlement_history, candidates, payment_estimates)
        ]
```

---

## 4. Provider Registration

Register your provider in `resolve_model_provider` within `godspeed_nav/ml.py`:

```python
PROVIDERS: dict[str, type[PredictiveModelPort]] = {
    "heuristic": HeuristicPredictiveModelAdapter,
    "sklearn": SklearnPredictiveModelAdapter,
    "testing": TestingPredictiveModelAdapter,
    "disabled": DisabledPredictiveModelAdapter,
    "bayesian": BayesianPredictiveModelAdapter,  # Register here
}
```

---

## 5. Verification & Testing

1. Configure `model_provider: bayesian` in `HARNESS.md`.
2. Run the predictive extensions command from the CLI:
   ```bash
   uv run godspeed-nav predictive-extensions \
     --provider bayesian \
     --candidates '[{"id": "test-aff", "expected_horizon_delta": 2, "risk": 0.1}]'
   ```
3. Add a unit test in `tests/test_computation.py` asserting that predictions return valid probabilities.

---

### Source Trail
- Port Definition: `godspeed_nav/ml.py:12-33`
- Heuristic Reference: `godspeed_nav/ml.py:34-97`
- Sklearn Reference: `godspeed_nav/ml.py:123-260`
