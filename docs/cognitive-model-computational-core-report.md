# Cognitive Model Computational Core — Evidence Report

**Date:** 2026-06-03
**Scope:** Implement `tmp/math.md` as a deterministic, inspectable computational core
**Proof Classification:** `local-confidence`

## Scope Implemented

| Task | Description | Status |
|---:|---|---|
| 1 | Deterministic model types and burden kernel | Complete |
| 2 | Hard gates and spendability scoring | Complete |
| 3 | Controller advisory ranking | Complete |
| 4 | Runtime advisory output in horizon review | Complete |
| 5 | Calibration fields on settlement | Complete |
| 6 | Calibration dataset builder | Complete |
| 7 | Built-in sklearn provider behind evidence gate | Complete |
| 8 | Validation and release evidence | Complete |

### Files Created

- `godspeed_nav/cognitive_model.py` — Representational coordinates, burden kernel, hard gates, spendability scoring, controller ranking, calibration frame builder.

### Files Modified

- `godspeed_nav/runtime.py` — Added `desired_direction` parameter and `model_calibration` object to `record_settlement`; added advisory `cognitive_model` output to `review_horizon`.
- `godspeed_nav/ml.py` — Added `SklearnPredictiveModelAdapter` with lazy sklearn import, threshold gating, and logistic regression prediction; registered `"sklearn"` in provider registry.
- `tests/test_computation.py` — Added 8 new tests covering burden, gates, spendability, controller ranking, calibration frame, and sklearn provider.
- `tests/test_runtime_workflow.py` — Added 2 new tests covering advisory model output in horizon review and calibration fields in settlement.
- `docs/references/ledger-reference.md` — Added `model_calibration` field documentation.
- `docs/runbooks/configuration.md` — Added sklearn provider documentation.

## Proof Classification

**`local-confidence`** — All tasks through Task 7 are complete with focused tests and full suite validation. The implementation has:

- Deterministic gates that separate hard blocks from continuous scoring
- Advisory controller ranking that does not override existing runtime decisions
- Calibration fields recorded on every settlement for future weight fitting
- Pandas calibration frame builder for dataset extraction
- sklearn provider registered but dormant behind dependency checks, configuration, and settlement-history thresholds
- Full test suite passing (516 tests)
- Enterprise validation passing (`"status": "pass"`)

## Validation Commands and Results

```bash
# Focused deterministic model tests
uv run pytest tests/test_computation.py -q -k "cognitive_model or calibration"
# Result: 5 passed

# Runtime workflow tests
uv run pytest tests/test_runtime_workflow.py -q
# Result: 12 passed

# Full test suite
uv run pytest -q
# Result: 516 passed in 26.72s

# Enterprise validation
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/cognitive-model-validation
# Result: {"status": "pass"}
```

## Known Limits

1. **Advisory only** — The cognitive model output in `review_horizon` is advisory. It does not replace or reorder the existing `rank_affordances` result. Promotion of deterministic gates into runtime decisions requires a separate settlement-tested promotion step.
2. **Default weights** — All controller weights, risk ceilings, debt ceilings, and spendability weights use spec defaults. Calibration requires 500+ usable settlements.
3. **sklearn dormant** — The sklearn provider is registered but requires `uv sync --extra ml` and 200+ settlement events before it activates. It remains advisory even when active.
4. **No ML override** — ML predictions never override governance, payment, settlement-access, risk, or debt gates.

## Next Settlement-Data Threshold

- **30 varied transitions**: Fit burden matrix `M` from actual payment data.
- **50 usable settlements**: Recalibrate `D_max` and givenness marker weights.
- **200 settlements**: sklearn provider becomes eligible for activation.
- **500 settlements**: Fit controller weights against outcome quality.
