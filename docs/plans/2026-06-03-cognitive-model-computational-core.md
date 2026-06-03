# Cognitive Model Computational Core Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn `tmp/math.md` into a deterministic, inspectable computational core for `godspeed_agent`, then promote proven pieces into runtime decisions and leave learned estimators behind settlement-history gates.

**Architecture:** Build a new advisory model module first, keeping the current runtime behavior stable while exposing math-model gates, burden, spendability, risk, debt, reliability, and controller scores. Promote deterministic gates into `NavigationRuntime.review_horizon` only after focused tests prove the advisory output is coherent. Register scikit-learn as a built-in predictive provider during the main implementation, but keep it dormant behind dependency checks, configuration, the existing predictive model port, and settlement-history thresholds; do not use ML to override governance, payment, settlement-access, risk, or debt gates.

**Tech Stack:** Python 3.11, dataclasses, NumPy for vector and matrix math, pandas for calibration/reporting, scikit-learn registered through `godspeed_nav.ml.PredictiveModelPort` and installed through the existing `ml` extra, pytest, local JSONL ledgers.

## Context

The controlling specification is `tmp/math.md`. The most important rules are:

- Live formulas require measurable inputs, defaults, calibration paths, and failure criteria.
- The implementation posture is continuous state with discrete settlement.
- Low-data operation must prefer deterministic gates over learned estimates.
- Hard gates are separate from continuous scores.
- Learned estimates may inform ranking only after enough settlement history exists.

Current relevant code:

- `godspeed_nav/metrics.py` contains existing deterministic helpers: error, payment, settlement, affordance ranking, and representational transition review.
- `godspeed_nav/runtime.py` owns the local navigation loop and `review_horizon`.
- `godspeed_nav/ml.py` already defines `PredictiveModelPort`, heuristic providers, thresholds, and advisory predictive extensions.
- `godspeed_nav/config.py` already exposes computation settings and ML thresholds.
- `tests/test_computation.py` is the right first home for focused deterministic model tests.
- `tests/test_runtime_workflow.py` is the right home for runtime advisory-output and promotion tests.

## Non-Goals

- Do not replace the current runtime ranking in the first implementation slice.
- Do not introduce Polars.
- Do not make scikit-learn an always-active authority; it must remain dependency-checked, threshold-gated, and advisory.
- Do not treat simulation, heuristic prediction, or fitted estimates as settlement.
- Do not migrate storage formats.

## Task 1: Add Deterministic Model Types And Defaults

**Files:**
- Create: `godspeed_nav/cognitive_model.py`
- Modify: `tests/test_computation.py`

**Step 1: Write the failing tests**

Append tests that prove default representational coordinates, burden, and strict positive-definite defaults are available:

```python
from godspeed_nav.cognitive_model import (
    BurdenParameters,
    RepresentationalCoordinates,
    compute_representational_burden,
)


def test_cognitive_model_computes_default_representational_burden():
    result = compute_representational_burden(
        current=RepresentationalCoordinates(scope=0.2, givenness=0.2),
        target=RepresentationalCoordinates(scope=0.7, givenness=0.6),
        distinctions_current=14,
        distinctions_max=20,
        parameters=BurdenParameters(),
    )

    assert result["delta"] == {"scope": 0.5, "givenness": 0.4}
    assert result["scope_overflow"] == 0.0
    assert result["burden"] > 0
    assert result["burden_max"] == pytest.approx(2 ** 0.5)
    assert result["matrix_floor"] == pytest.approx(0.05)
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_computation.py::test_cognitive_model_computes_default_representational_burden -q
```

Expected: fail because `godspeed_nav.cognitive_model` does not exist.

**Step 3: Implement the minimal model types and burden function**

Create `godspeed_nav/cognitive_model.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class RepresentationalCoordinates:
    scope: float
    givenness: float

    def vector(self) -> np.ndarray:
        return np.array([clamp(self.scope), clamp(self.givenness)], dtype=float)


@dataclass(frozen=True)
class BurdenParameters:
    w_scope: float = 1.0
    w_givenness: float = 1.0
    w_interaction: float = 0.0
    matrix_floor: float = 0.05
    overflow_weight: float = 0.25

    def matrix(self) -> np.ndarray:
        base = np.array(
            [
                [self.w_scope, self.w_interaction],
                [self.w_interaction, self.w_givenness],
            ],
            dtype=float,
        )
        return base


def compute_representational_burden(
    current: RepresentationalCoordinates,
    target: RepresentationalCoordinates,
    distinctions_current: int,
    distinctions_max: int = 20,
    parameters: BurdenParameters | None = None,
) -> dict[str, Any]:
    parameters = parameters or BurdenParameters()
    delta = target.vector() - current.vector()
    matrix = parameters.matrix()
    burden_raw = float(np.sqrt(max(delta.T @ matrix @ delta, 0.0)))
    scope_overflow = max(0.0, distinctions_current / max(distinctions_max, 1) - 1.0)
    burden = burden_raw + parameters.overflow_weight * scope_overflow
    burden_max = float(np.sqrt(parameters.w_scope + parameters.w_givenness))
    return {
        "delta": {"scope": round(float(delta[0]), 10), "givenness": round(float(delta[1]), 10)},
        "burden": burden,
        "burden_raw": burden_raw,
        "burden_max": burden_max,
        "scope_overflow": scope_overflow,
        "matrix_floor": parameters.matrix_floor,
    }
```

**Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_computation.py::test_cognitive_model_computes_default_representational_burden -q
```

Expected: pass.

**Step 5: Commit**

```bash
git add godspeed_nav/cognitive_model.py tests/test_computation.py
git commit -m "feat: add cognitive model burden kernel"
```

## Task 2: Add Hard Gate And Spendability Scoring

**Files:**
- Modify: `godspeed_nav/cognitive_model.py`
- Modify: `tests/test_computation.py`

**Step 1: Write the failing tests**

Add tests for gate separation and continuous spendability:

```python
from godspeed_nav.cognitive_model import evaluate_candidate_model


def test_cognitive_model_blocks_failed_hard_gate_before_scoring():
    result = evaluate_candidate_model(
        candidate={
            "id": "unsafe",
            "governance_allowed": False,
            "settlement_accessible": True,
            "payment_required": {"time": 1},
            "payment_capacity": {"time": 5},
            "risk": 0.1,
            "debt": 0.1,
        },
        context="production",
    )

    assert result["allowed"] is False
    assert result["blocking_reasons"] == ["governance_blocked"]
    assert result["spendability_score"] is None


def test_cognitive_model_scores_allowed_candidate_spendability():
    result = evaluate_candidate_model(
        candidate={
            "id": "path",
            "governance_allowed": True,
            "settlement_accessible": True,
            "payment_required": {"time": 1},
            "payment_capacity": {"time": 5},
            "required_preconditions": ["tests", "docs"],
            "met_preconditions": ["tests"],
            "required_capabilities": ["python", "pytest"],
            "active_capabilities": ["python"],
            "pathway": "run focused test and patch code",
            "expected_settlement": {"tests": "pass"},
            "risk": 0.1,
            "debt": 0.1,
        },
        context="production",
    )

    assert result["allowed"] is True
    assert result["blocking_reasons"] == []
    assert result["spendability_score"] >= 0.5
    assert result["factors"]["visibility"] == 1.0
```

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_computation.py -q -k "cognitive_model"
```

Expected: fail because `evaluate_candidate_model` does not exist.

**Step 3: Implement candidate gate and scoring**

Add:

```python
RISK_CEILINGS = {
    "exploration": 0.50,
    "production": 0.30,
    "recovery": 0.20,
    "safety_critical": 0.05,
}

DEBT_CEILINGS = {
    "exploration": 0.50,
    "production": 0.30,
    "recovery": 0.15,
    "safety_critical": 0.05,
}

SPENDABILITY_WEIGHTS = {
    "visibility": 0.20,
    "reachability": 0.25,
    "payment_fit": 0.35,
    "capability_support": 0.20,
}


def evaluate_candidate_model(candidate: dict[str, Any], context: str = "production") -> dict[str, Any]:
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
    score = sum(SPENDABILITY_WEIGHTS[key] * factors[key] for key in SPENDABILITY_WEIGHTS)
    return {
        "candidate_id": candidate.get("id"),
        "allowed": True,
        "blocking_reasons": [],
        "spendability_score": score,
        "factors": factors,
        "risk_ceiling": risk_ceiling,
        "debt_ceiling": debt_ceiling,
    }
```

Also implement private helpers `_payment_exceeds_capacity` and `_spendability_factors`.

**Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_computation.py -q -k "cognitive_model"
```

Expected: pass.

**Step 5: Commit**

```bash
git add godspeed_nav/cognitive_model.py tests/test_computation.py
git commit -m "feat: add cognitive model gates and spendability"
```

## Task 3: Add Controller Objective As Advisory Ranking

**Files:**
- Modify: `godspeed_nav/cognitive_model.py`
- Modify: `tests/test_computation.py`

**Step 1: Write the failing test**

```python
from godspeed_nav.cognitive_model import rank_candidates_by_controller


def test_cognitive_model_controller_ranks_allowed_paths_without_overriding_gates():
    result = rank_candidates_by_controller(
        candidates=[
            {
                "id": "blocked",
                "governance_allowed": False,
                "settlement_accessible": True,
                "payment_required": {"time": 1},
                "payment_capacity": {"time": 10},
                "risk": 0.0,
                "debt": 0.0,
                "expected_horizon_delta": 100,
            },
            {
                "id": "steady",
                "governance_allowed": True,
                "settlement_accessible": True,
                "payment_required": {"time": 1},
                "payment_capacity": {"time": 10},
                "risk": 0.1,
                "debt": 0.1,
                "expected_horizon_delta": 3,
                "direction_score": 0.8,
            },
        ],
        context="production",
    )

    assert result["ranked"][0]["candidate_id"] == "steady"
    assert result["rejected"][0]["candidate_id"] == "blocked"
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_computation.py::test_cognitive_model_controller_ranks_allowed_paths_without_overriding_gates -q
```

Expected: fail because `rank_candidates_by_controller` does not exist.

**Step 3: Implement controller ranking**

Use the defaults from `tmp/math.md`:

```python
CONTROLLER_WEIGHTS = {
    "burden": 0.5,
    "risk": 1.5,
    "debt": 0.8,
    "horizon_gain": 0.3,
    "direction": 0.5,
}
```

For each allowed candidate:

```text
objective = error_cost + 0.5 * burden + 1.5 * risk + 0.8 * debt - 0.3 * horizon_gain - 0.5 * direction_score
```

`error_cost` is read from `candidate.get("error_cost", 0.0)`. It represents the expected remaining error magnitude after the candidate action completes (Section 13.2 of `tmp/math.md`: "expected remaining error after action"). Callers should populate it using `compute_error(desired_state, expected_post_action_state)["error_magnitude"]` when a desired state and an expected post-action state are available. When neither is available, the default of `0.0` means the term is dormant and the controller ranks on burden, risk, debt, horizon gain, and direction score alone.

Lower objective ranks first. Rejected candidates remain rejected regardless of expected horizon delta.

**Step 4: Run test**

Run:

```bash
uv run pytest tests/test_computation.py -q -k "cognitive_model"
```

Expected: pass.

**Step 5: Commit**

```bash
git add godspeed_nav/cognitive_model.py tests/test_computation.py
git commit -m "feat: add advisory cognitive controller ranking"
```

## Task 4: Wire Advisory Model Output Into Runtime Horizon Review

**Files:**
- Modify: `godspeed_nav/runtime.py`
- Modify: `tests/test_runtime_workflow.py`

**Step 1: Write the failing test**

Add a runtime test that verifies `review_horizon` includes advisory math output while preserving existing `next_affordance` behavior:

```python
def test_runtime_horizon_review_includes_advisory_cognitive_model(tmp_path):
    runtime = NavigationRuntime(tmp_path)
    direction = runtime.start_direction("Core model", "Use advisory cognitive model")

    review = runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "candidate-1",
                "statement": "Run focused model test",
                "pathway": "write failing test then implement",
                "costs": {"time": 1},
                "capacities": {"time": 5},
                "payment_required": {"time": 1},
                "payment_capacity": {"time": 5},
                "expected_horizon_delta": 3,
                "risk": 0.1,
                "debt": 0.1,
            }
        ],
    )

    assert review["next_affordance"]["id"] == "candidate-1"
    assert review["cognitive_model"]["ranked"][0]["candidate_id"] == "candidate-1"
    assert review["cognitive_model"]["mode"] == "advisory"
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_runtime_workflow.py::test_runtime_horizon_review_includes_advisory_cognitive_model -q
```

Expected: fail because `review_horizon` does not include `cognitive_model`.

**Step 3: Add advisory model output**

In `NavigationRuntime.review_horizon`, after existing `rank_affordances`, call:

```python
from godspeed_nav.cognitive_model import rank_candidates_by_controller
```

Use the accepted affordances list first. Preserve existing `ranked_affordances` and `next_affordance`. Add:

```python
"cognitive_model": {
    **rank_candidates_by_controller(affordances, context=self.policy.get("context", "production")),
    "mode": "advisory",
}
```

Do not block or reorder runtime choices in this task.

**Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_runtime_workflow.py tests/test_computation.py -q
```

Expected: pass.

**Step 5: Commit**

```bash
git add godspeed_nav/runtime.py godspeed_nav/cognitive_model.py tests/test_runtime_workflow.py tests/test_computation.py
git commit -m "feat: expose advisory cognitive model in horizon review"
```

## Task 5: Record Calibration Fields On Settlement

**Files:**
- Modify: `godspeed_nav/runtime.py`
- Modify: `tests/test_runtime_workflow.py`
- Modify: `docs/references/ledger-reference.md`

**Step 1: Write the failing test**

Add a test proving settlement records include fields needed by `tmp/math.md` calibration:

```python
def test_record_settlement_persists_cognitive_model_calibration_fields(tmp_path):
    runtime = NavigationRuntime(tmp_path)
    direction = runtime.start_direction("Calibrate model", "Record predicted and actual payment")
    runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "aff-1",
                "statement": "Patch model",
                "pathway": "edit code",
                "costs": {"time": 1},
                "capacities": {"time": 5},
                "expected_horizon_delta": 2,
                "risk": 0.1,
                "debt": 0.1,
            }
        ],
    )

    settlement = runtime.record_settlement(
        affordance_id="aff-1",
        before_state={"tests": 0},
        after_state={"tests": 1},
        desired_direction={"desired_state": {"tests": 1}},
        payment_actual={"time": 1.5},
        evidence=["pytest passed"],
        horizon_delta=2,
    )

    calibration = settlement["model_calibration"]
    assert calibration["payment_actual"] == {"time": 1.5}
    assert calibration["settlement_success"] is True
    assert "payment_predicted" in calibration
    assert "horizon_delta" in calibration
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_runtime_workflow.py::test_record_settlement_persists_cognitive_model_calibration_fields -q
```

Expected: fail because calibration fields are absent.

**Step 3: Add calibration fields**

In `NavigationRuntime.record_settlement`, include a `model_calibration` object in the settlement record:

```python
"model_calibration": {
    "payment_predicted": predicted_payment_from_payment_ledger_or_empty,
    "payment_actual": payment_actual,
    "settlement_success": settlement_review["status"] == "success",
    "settlement_score": settlement_review["settlement_score"],
    "horizon_delta": horizon_delta,
    "risk_estimate": matched_affordance.get("risk"),
    "debt_estimate": matched_affordance.get("debt"),
}
```

Keep missing historical values explicit as `None` or `{}`. Do not fabricate predictions.

**Step 4: Update ledger reference**

Add a short section to `docs/references/ledger-reference.md` explaining `model_calibration` and that it supports later calibration but is not proof of capability.

**Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/test_runtime_workflow.py tests/test_docs_alignment.py -q
```

Expected: pass.

**Step 6: Commit**

```bash
git add godspeed_nav/runtime.py tests/test_runtime_workflow.py docs/references/ledger-reference.md
git commit -m "feat: record cognitive model calibration fields"
```

## Task 6: Add Calibration Dataset Builder

**Files:**
- Modify: `godspeed_nav/cognitive_model.py`
- Modify: `tests/test_computation.py`

**Step 1: Write the failing test**

```python
from godspeed_nav.cognitive_model import build_calibration_frame


def test_build_calibration_frame_extracts_settlement_model_fields():
    frame = build_calibration_frame(
        settlements=[
            {
                "id": "set-1",
                "model_calibration": {
                    "payment_predicted": {"time": 1},
                    "payment_actual": {"time": 1.5},
                    "settlement_success": True,
                    "settlement_score": 0.8,
                    "horizon_delta": 2,
                    "risk_estimate": 0.1,
                    "debt_estimate": 0.2,
                },
            }
        ]
    )

    assert list(frame.columns) == [
        "settlement_id",
        "payment_predicted_total",
        "payment_actual_total",
        "payment_error",
        "settlement_success",
        "settlement_score",
        "horizon_delta",
        "risk_estimate",
        "debt_estimate",
    ]
    assert frame.iloc[0]["payment_error"] == pytest.approx(0.5)
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_computation.py::test_build_calibration_frame_extracts_settlement_model_fields -q
```

Expected: fail because `build_calibration_frame` does not exist.

**Step 3: Implement pandas calibration extraction**

Use pandas locally in the function. Flatten only the stable calibration fields. Skip settlements with missing `model_calibration`.

**Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_computation.py -q -k "cognitive_model or calibration"
```

Expected: pass.

**Step 5: Commit**

```bash
git add godspeed_nav/cognitive_model.py tests/test_computation.py
git commit -m "feat: build cognitive model calibration dataset"
```

## Task 7: Add Built-In Scikit-Learn Provider Behind Evidence Gate

**Files:**
- Modify: `godspeed_nav/ml.py`
- Modify: `tests/test_computation.py`
- Modify: `docs/runbooks/configuration.md`

**Step 1: Write the failing tests**

Add two tests:

```python
def test_sklearn_provider_is_registered_but_threshold_gated():
    result = build_predictive_extension_plan(
        settlement_history=[{"id": f"set-{index}"} for index in range(199)],
        candidates=[],
        ml_event_threshold=200,
        simulation_threshold=1000,
        model_port=resolve_model_provider("sklearn"),
    )

    assert result["stage"] == "deterministic_only"
    assert result["ml_predictions"] == []


def test_sklearn_provider_is_builtin_and_reports_provider_name():
    provider = resolve_model_provider("sklearn")
    assert provider.provider_name == "sklearn"
```

Add a missing-dependency behavior test if the local test environment does not install the `ml` extra:

```python
def test_sklearn_provider_reports_clear_missing_dependency(monkeypatch):
    provider = resolve_model_provider("sklearn")

    def missing_import():
        raise RuntimeError("sklearn_extra_required: install with uv sync --extra ml")

    monkeypatch.setattr(provider, "_require_sklearn", missing_import)

    with pytest.raises(RuntimeError, match="sklearn_extra_required"):
        provider.predict_affordances(
            settlement_history=[{"id": f"set-{index}"} for index in range(200)],
            candidates=[
                {
                    "id": "candidate-1",
                    "expected_horizon_delta": 2,
                    "risk": 0.1,
                }
            ],
            payment_estimates={"candidate-1": {"payment_burden": 1}},
        )
```

**Step 2: Run tests**

Run:

```bash
uv run pytest tests/test_computation.py -q -k "sklearn_provider"
```

Expected: fail because the provider is not registered.

**Step 3: Implement provider**

Add `SklearnPredictiveModelAdapter(PredictiveModelPort)`.

Rules:

- Register `"sklearn"` in `resolve_model_provider`.
- Import scikit-learn lazily inside a `_require_sklearn()` helper.
- If scikit-learn is unavailable, raise a clear `RuntimeError("sklearn_extra_required: install with uv sync --extra ml")`.
- Below `ml_event_threshold`, `build_predictive_extension_plan` must continue returning `stage: deterministic_only` and must not call the provider.
- Above `ml_event_threshold`, train only from extracted calibration rows with enough usable data.
- Use simple, inspectable models first, such as logistic regression for settlement success.
- If calibration rows are insufficient even though the event-count threshold passed, return an empty prediction list with an explanatory note instead of fabricating confidence.
- Return suggestions only in the existing `ml_predictions` shape.
- Keep predictions advisory; deterministic ranking and hard gates remain required.

**Step 4: Update configuration docs**

Document:

- `model_provider: sklearn` is a built-in provider option.
- Install with `uv sync --extra ml` when sklearn predictions are desired.
- Existing `ml_event_threshold` still controls activation.
- Below the threshold, sklearn is registered but dormant.
- ML predictions are advisory and never override hard gates.

**Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/test_computation.py tests/test_config.py tests/test_docs_alignment.py -q
```

Expected: pass.

**Step 6: Commit**

```bash
git add godspeed_nav/ml.py tests/test_computation.py docs/runbooks/configuration.md
git commit -m "feat: add gated sklearn predictive provider"
```

## Task 8: Validation And Release Evidence

**Files:**
- Modify if needed: `godspeed_nav/validation.py`
- Modify if needed: `tests/test_validation.py`
- Create if appropriate: `docs/cognitive-model-computational-core-report.md`

**Step 1: Add validation checks**

If the implementation changes public runtime behavior, add validation details that confirm:

- cognitive model module exists;
- advisory model output is present in horizon review;
- calibration fields are recorded;
- predictive model remains threshold gated.

**Step 2: Run focused suite**

Run:

```bash
uv run pytest tests/test_computation.py tests/test_runtime_workflow.py tests/test_config.py tests/test_validation.py tests/test_docs_alignment.py -q
```

Expected: pass.

**Step 3: Run full suite**

Run:

```bash
uv run pytest -q
```

Expected: pass.

**Step 4: Run enterprise validation**

Run:

```bash
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/cognitive-model-validation
```

Expected: JSON status is `pass`.

**Step 5: Write evidence report if behavior changed materially**

Create `docs/cognitive-model-computational-core-report.md` with:

- scope implemented;
- proof classification;
- validation commands and results;
- known limits;
- next settlement-data threshold.

**Step 6: Commit**

```bash
git add godspeed_nav tests docs
git commit -m "docs: record cognitive model validation evidence"
```

## Implementation Order

Execute in this order:

1. Deterministic model types and burden.
2. Hard gates and spendability.
3. Controller advisory ranking.
4. Runtime advisory output.
5. Calibration fields.
6. Calibration dataset builder.
7. Built-in scikit-learn provider behind evidence gate.
8. Validation and evidence.

Stop after Task 4 if the goal is only an advisory computational model. Continue through Task 6 if the goal is calibration readiness. Continue through Task 7 to make sklearn available as a dormant built-in provider that automatically remains inactive until the configured settlement-history threshold is met.

## Proof Classification

Expected classification after Task 4: `focused-slice`.

Expected classification after Task 7 with full tests and validation: `local-confidence`.

Do not call the result `enterprise-shippable` unless it has live dependency evidence, an evidence artifact, and a reproducible acceptance command over a real receiving project with settlement ledgers.
