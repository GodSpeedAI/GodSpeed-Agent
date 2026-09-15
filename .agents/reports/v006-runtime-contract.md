# v006 Runtime Operational Contract (T07)

Date: 2026-09-15. Task T07 of plan godspeed-agent-v006-dual-model
(amendments 6 and 7: document the existing contract before any integration;
decide the deployment model explicitly).

## 1. The existing runtime predictor (unchanged by v006)

| Question | Answer (repository evidence) |
|---|---|
| What is trained offline? | **Nothing is persisted.** No serialized model artifact exists anywhere in the repo. The "hf-calibration-005" training runs (`scripts/settlement_datasets/run_calibration_pipeline.py`) produce evaluation metrics and a calibration frame (`data/settlement_datasets/runs/hf-calibration-005-features/`), not a deployed model. |
| What is fit at runtime? | `SklearnPredictiveModelAdapter.predict_affordances` (`godspeed_nav/ml.py:150-240`) refits a `LogisticRegression(max_iter=1000)` **on every call**, over a 4-feature subset (`payment_predicted_total`, `horizon_delta`, `risk_estimate`, `debt_estimate`) of rows drawn from settlement history. This is a *different estimator contract* from the 11-feature training-time evaluation in the calibration pipeline. |
| What data feeds it? | The local settlement ledger (`LedgerStore(...).read("settlements")`, `godspeed_nav/ml.py:347-349`) — i.e. local settlement events, not the external trajectory corpus. |
| What prediction is made? | Success probability for **candidate affordances** (next-step options), given settlement history — a candidate-scoped, history-conditioned prediction. |
| What consumes it? | `build_predictive_extension_plan` / `run_predictive_extensions` (`godspeed_nav/ml.py:295-366`): advisory `ml_predictions` inside the predictive-extension plan, gated by `ml_event_threshold` (200) and the `model_provider` config. Deterministic ranking (`rank_affordances`) is always computed and remains the authority; predictions are suggestions only. |

## 2. The new v006 trajectory-prefix predictor (evaluated, NOT deployed)

| Question | Answer |
|---|---|
| What was trained? | Per (arm, prefix-cut) LogisticRegression / LightGBM models inside the experiment runner (`scripts/settlement_datasets/run_v006_experiments.py`), fit on the external proxy corpus, persisted only as experiment artifacts (metrics + test predictions) under `data/settlement_datasets/runs/hf-calibration-006-experiments/`. |
| What data feeds it? | The materialized external trajectory corpus (swegym_openhands + nebius_swe_agent parents; event-level corpus is local-only). |
| What prediction is made? | Probability that a **trajectory in progress** will eventually settle successfully — a trajectory-scoped, prefix-conditioned prediction. |
| What would consume it? | Nothing today. No runtime surface, CLI command, or report consumes trajectory-prefix predictions. |

**Contract distinction (amendment 6):** the existing predictor answers
"which affordance candidate looks most settleable given settlement history";
the v006 predictor answers "will this in-flight trajectory settle". These are
different prediction points over different data. They are NOT the same
prediction problem, and v006 does not replace or rewire the existing one.

## 3. Deployment-model decision (amendment 7) — DECIDED: no v006 runtime integration

The preregistered acceptance rule was not met for any gain (representation,
estimator, or combined; see `.agents/reports/v006-experiment-results.md` and
`.agents/reports/v006-critique.md`):

- P-B vs P-A (representation): macro-AUC −0.0121, direction consistent in 3/6 cuts → not earned.
- P-C vs P-A (estimator): +0.0124, 3/6 cuts → not earned.
- P-D vs P-A (combined): −0.0095, 3/6 cuts → not earned.
- No identity-dependence reversal; LODO direction-inconsistent (weak, 2 folds).

Consequences, decided explicitly:

1. **No dual-model runtime surface is added.** `godspeed_nav/ml.py` registry,
   defaults, and consumer semantics are unchanged. The dual-model diagram is
   not forced into the runtime.
2. **No persisted production model artifacts are introduced.** The existing
   architecture fits at runtime from local ledger state; introducing static
   pretrained artifacts would be a new architecture serving a predictor that
   did not earn deployment. Experiment artifacts remain under the run
   directory for reproducibility only.
3. **`lightgbm` remains an `ml` extra** for experiment reproduction; nothing
   at runtime depends on it, so the degradation question is moot in the
   default path (and the T02 contract test keeps the dependency optional).
4. **Calibration finding recorded, not silently bundled:** OOF-isotonic
   calibration halved Brier (≈0.18 → ≈0.13) for every family and is required
   if any of these models is ever deployed. Retro-fitting calibration into the
   existing sklearn predictor is a *separate* candidate change with its own
   settlement criteria; it is recorded as the smallest justified next move,
   not implemented here.
5. **v005/H remains the operative baseline.** Rollback = git revert of the
   v006 commits; nothing in the runtime path changed, so runtime rollback is
   vacuous.

## 4. Verification

- `uv run pytest tests/test_computation.py tests/test_cli_hooks_mcp.py -q` —
  existing runtime surfaces pass unchanged (run in T08 gates).
- `git diff godspeed_nav/` is empty for the v006 branch work: no runtime code
  was modified after T02's dependency addition.
