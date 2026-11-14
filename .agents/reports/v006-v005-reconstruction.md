# v005 Baseline Reconstruction: hf-calibration-005-features

Date: 2026-09-15. RECON report for plan godspeed-agent-v006-dual-model.
Read-only reconstruction of the frozen v005 settlement classifier baseline.
Paths relative to repo root. Adapter error behaviors verified empirically
against local fixtures/sample files only (no network).

## 1. Exact v005 feature schema (11 features)

Features are computed in `scripts/settlement_datasets/run_calibration_pipeline.py:121-236`
(`external_record_to_model_calibration`) from the settlement record's `payment`,
`affordance_path`, and `metadata` blocks, then flattened by
`godspeed_nav/cognitive_model.py:375-439` (`build_calibration_frame`).

Input counters (pipeline:137-141): `elapsed_steps`, `error_count`, `turns`,
`tool_calls`, `commands` all come from `record["payment"]`, which each adapter
derives from the raw trajectory (see §4).

| # | Feature | Formula | Inputs | Kind |
|---|---------|---------|--------|------|
| 1 | `payment_predicted_total` | `sum(payment_predicted.values())` = `elapsed_steps` (only key is `steps`) | pipeline:214; cognitive_model.py:368-372,396 | Derived proxy (total message/step count) |
| 2 | `payment_actual_total` | `turns + tool_calls + commands + errors` (sum of all 4 values) | pipeline:216-220; cognitive_model.py:397 | Derived proxy |
| 3 | `payment_error` | `abs(actual_total - predicted_total)` | cognitive_model.py:398 | Derived proxy |
| 4 | `horizon_delta` | `clamp01(0.6*(1-min(error_rate,1)) + 0.4*min(payment_efficiency,1))`, round 4; `error_rate=error_count/elapsed_steps`; `payment_efficiency=(turns+tool_calls+commands)/max(elapsed_steps,1)` | pipeline:144-151 | Derived proxy (never uses outcome) |
| 5 | `risk_estimate` | `min(1.0, error_rate)` | pipeline:153 | Derived proxy |
| 6 | `debt_estimate` | `min(turns/20, 1)` if `turns>0 and tool_calls==0` else `0.0` | pipeline:156-158 | Derived proxy |
| 7 | `tool_diversity_count` | `len(set(non-empty metadata["tool_names"]))` | pipeline:163-164 | Raw count; **only swegym populates `tool_names`** (swegym_openhands_adapter.py:296) |
| 8 | `error_recovery_ratio` | fraction of error-keyword observations (`error`,`fail`,`traceback`,`exception`,`assertionerror`; pipeline:172) that have any later non-error observation, round 4; 0.0 if no error observations | pipeline:167-188 | Derived proxy over `affordance_path["observations"]` content+`turn_index` |
| 9 | `action_observation_ratio` | `len(actions)/len(observations)`, 0.0 if no observations, round 4 | pipeline:191-197 | Raw counts ratio |
| 10 | `avg_actions_per_step` | `len(actions)/max(elapsed_steps,1)`, round 4 | pipeline:200 | Raw counts ratio |
| 11 | `dataset_id` | map: `swegym_openhands=0`, `agenttrove=1`, `nebius_swe_agent=2`, unknown `-1` | pipeline:204-209 | Categorical encoding |

Frame column order and dtypes: cognitive_model.py:400-439; label columns
`settlement_success` (bool from `outcome.success`, pipeline:221) and
`settlement_score` (1.0/0.0, pipeline:222) are labels only. Record id is
`f"{dataset}:{task_id}"` (pipeline:212).

## 2. Training pipeline end-to-end

Entry: `run_pipeline` (run_calibration_pipeline.py:441-947). Executed per
`.agents/current_status.yml` verification block with `--target-usable-settlements 5000
--min-confidence 0.65 --provider sklearn --sampling-strategy natural --min-datasets 3`.

1. Manifest load: `load_calibration_manifest` (pipeline:55-79); requires
   `target_usable_settlements`, `settlement_classification`, `datasets`; datasets
   sorted by `priority` ascending (pipeline:78). Run surface + manifest write
   (pipeline:460-483). Frozen run manifest:
   `data/settlement_datasets/runs/hf-calibration-005-features/run_manifest.json:2-10`.
2. Per dataset in priority order (pipeline:494-495): stop check
   `should_stop_for_target` (pipeline:87-100) — target 5000 deferred until
   `min_datasets=3` processed. Adapter resolved via registry
   (`registry.py:12-19,35-57`). Stream kwargs: `input_path` if configured, else
   `source_uri` + `split` (pipeline:536-542); `adapter.stream(limit=max_rows, ...)`
   (pipeline:545). Stream-creation exceptions: adapter_errors=1, dataset skipped
   (pipeline:544-551).
3. Per row (pipeline:553-589): `scanned++` (557-558) → `to_settlement_record(raw)`
   wrapped in bare `try/except Exception` that swallows everything and counts
   `adapter_errors` (561-566) → force
   `metadata["settlement_classification"]="external-proxy-settlement"` (568-571) →
   `normalized++` (573-575) → usable filter `_is_usable` (108-113, 577-580) →
   success/failure tallies (582-586) or `rejected++` (588-589). Usable =
   `success is not None AND outcome.confidence >= min_confidence` (108-113);
   per-adapter confidence values in §4.
4. Frame build (pipeline:609-632): read all `settlements/*.jsonl` via glob
   (613-617; glob order is filesystem-dependent — actual frame order is
   agenttrove rows 0-50, swegym rows 51-1942, nebius rows 1943-6496, verified from
   `calibration_frame.csv` dataset_id transitions) → convert each via
   `external_record_to_model_calibration` (619-621) → write
   `model_calibration_records.jsonl` (624-625) → `build_calibration_frame` (630)
   → `calibration_frame.csv` (631-632).
5. sklearn evaluation `_evaluate_sklearn_held_out` (pipeline:244-433), invoked at
   pipeline:694-700 since provider=sklearn and rows>=10. Guards: abort if leakage
   (255-263); skip if <20 rows (305-311) or single class (313-319). Features:
   the 11 columns of §1 minus labels/leaked (282-300).
   - **Exact split**: `train_test_split(X, y, test_size=0.2, random_state=42,
     stratify=y)` (pipeline:321-327) → 5197/1300 (matches model_evaluation.json).
   - Balanced branch (NOT taken in v005; sampling_strategy=natural per
     run_manifest.json:9): downsample majority to minority size
     (`sample(n=minority_size, random_state=42)`), concat, shuffle
     (`.sample(frac=1, random_state=42)`) (pipeline:329-349).
   - **Exact estimator**: `LogisticRegression(class_weight="balanced",
     max_iter=1000, solver="lbfgs", random_state=42)`, `clf.fit(X_train, y_train)`
     (pipeline:351-357). (max_iter=1000 added post-hoc to fix lbfgs
     ConvergenceWarning; converged ~258 iters per `.agents/current_status.yml`.)
   - Metrics (359-433): predict + predict_proba[:,1]; raw/balanced accuracy, f1,
     brier, confusion matrix; roc_auc + average_precision only if both classes in
     test; baselines = majority class and "predict success when prob >= train
     success rate".

## 3. Dataset configs vs actual execution

Configured (`configs/settlement_datasets/calibration_sources.yaml:10-33`):

| name | source_uri | split | max_rows | priority | streaming |
|------|-----------|-------|----------|----------|-----------|
| swegym_openhands | SWE-Gym/OpenHands-Sampled-Trajectories | train.raw | 3000 | 1 | true |
| agenttrove | open-thoughts/AgentTrove | train | 5000 | 2 | true |
| nebius_swe_agent | nebius/SWE-agent-trajectories | train | 5000 | 3 | true |

Executed (`summary.json:5-27`): swegym 3000 scanned / 3000 normalized / 1892
usable / 1108 rejected / 0 errors; agenttrove 100/100/51/49/0; nebius
5000/4559/4554/5/441 errors. Totals: scanned 8100, usable 6497, success 1289
(19.8%), failure 5208 (summary.json:118-127).

### 3a. Why agenttrove scanned only 100 rows despite max_rows 5000

`AgentTroveAdapter.stream()` (agenttrove_adapter.py:46-60) NEVER contacts
Hugging Face. It ignores the `source_uri`/`split` kwargs the pipeline passes and
reads a local file: `kwargs.get("input_path", _DEFAULT_INPUT_PATH)` where
`_DEFAULT_INPUT_PATH = "data/agenttrove/raw_samples/sample.jsonl"`
(agenttrove_adapter.py:37,49). The manifest has no `input_path` for agenttrove
(calibration_sources.yaml:19-25), so the default local file was used. That file
contains exactly 100 lines (`wc -l data/agenttrove/raw_samples/sample.jsonl`),
and the stream ends at EOF (the `count >= limit` check at
agenttrove_adapter.py:59-60 never fires). Verified empirically:
`list(adapter.stream(limit=5000, source_uri="open-thoughts/AgentTrove",
split="train"))` yields exactly 100 rows. No hardcoded cap, no pagination, no
test fixture — the local 100-row sample was exhausted. Additional
silent-failure surface: if the file does not exist, `stream` returns without
yielding (agenttrove_adapter.py:50-51), producing 0 scanned rows with no error.

### 3b. Nature of nebius's 441 adapter_errors

The pipeline's bare `except Exception` around `adapter.to_settlement_record(raw)`
(pipeline:561-566) swallows all exceptions per row, increments
`adapter_errors`, and drops the row. For nebius, `to_settlement_record` calls
`extract_payment` first (nebius_swe_agent_adapter.py:213-214), which raises on
null string fields that HF rows contain: `patch = raw.get("generated_patch", "")`
then `len(patch)` (nebius:158-159) → `TypeError: object of type 'NoneType' has
no len()` if null (verified); `eval_logs = raw.get("eval_logs", "")` then
`eval_logs.lower()` (nebius:161-166) → `AttributeError: 'NoneType' object has no
attribute 'lower'` if null (verified). `extract_outcome` has the same null
hazard (nebius:125,129, `eval_logs[:100]`) but `extract_payment` raises first.
Malformed `trajectory` does NOT error: `_parse_trajectory` tolerates JSON-string
parse failure, non-list, and None, returning `[]` (nebius:21-31; verified with
`"not-json"` and `None`). `raw.get(key, default)` returns None only when the key
exists with a null value — genuine null-valued HF columns. Which field caused
how many of the 441 is UNDETERMINED: the run's `raw/` directory was never
committed (git show c8498fa tracks only calibration/, docs/, run_manifest.json,
summary.json) and no longer exists locally. The error class (null string field →
TypeError/AttributeError) is code-certain; the exact field split is not.

## 4. Preprocessing + label semantics

Usable (pipeline:108-113): `outcome.success is not None` and
`outcome.confidence >= 0.65`. Confidence by adapter:

- swegym (`swegym_openhands_adapter.py:107-144,205-220`): label from `resolved`;
  True → success, `clean_success`, conf 0.9. False → `failure_with_signal` conf
  0.8 if test signal present (`test_result.passed` or nested
  `test_result.report.resolved`), else `failure_without_signal` conf 0.3.
  Rejected 1108 = conf-0.3 rows (dropped from the frame, not labeled 0).
- agenttrove (`agenttrove_adapter.py:129-150,242-263`; rules in
  `scripts/agenttrove/label_settlements.py:140-214` + structural fallback
  `scripts/agenttrove/parsing.py:242-323`): quality→success mapping at
  agenttrove_adapter.py:244-253 (`clean/recovered/partial/brittle_success` →
  True; `failure_with/without_signal` → False). Confidences (label_settlements.py:154-211;
  parsing.py:309-321): reward>=1 clean 0.95 / recovered-brittle 0.85; partial 0.8;
  reward<=0 0.85/0.8; result-string 0.8/0.75; structural fallback 0.3-0.95,
  `unknown` 0.3, tie 0.5. Rejected 49 = sub-0.65 confidence (unknown/tie) rows.
- nebius (`nebius_swe_agent_adapter.py:123-151,193-207`): label from `target`;
  True → success conf 0.9; else `failure_with_signal` conf 0.8 if `eval_logs`
  non-empty, else `failure_without_signal` conf 0.3. Rejected 5.

Terminal label sources: swegym `resolved` (+`test_result`), agenttrove
`reward`/`metadata.result`/structural, nebius `target` (+`eval_logs`). All
records carry `settlement_classification=external-proxy-settlement`, forced by
the pipeline (pipeline:568-571) on top of adapter defaults
(swegym_openhands_adapter.py:293; nebius_swe_agent_adapter.py:264). Frame label
`settlement_success=bool(outcome.success)` (pipeline:221;
cognitive_model.py:406). Usable-class mix per dataset (calibration_frame.csv):
swegym 12.68% success (1892 rows), agenttrove 100.00% (51 rows, all successes),
nebius 21.91% (4554 rows).

## 5. Model artifact format

Artifacts in `data/settlement_datasets/runs/hf-calibration-005-features/calibration/`:

- `calibration_frame.csv` — 6497 rows + header, 14 columns (§1 features +
  `settlement_id`, `settlement_success`, `settlement_score`).
- `model_calibration_records.jsonl` — 6497 records of shape `{id,
  model_calibration, metadata}`; metadata holds only
  `settlement_classification` and `source_dataset` (pipeline:211-236; verified
  from file). Raw actions/observations/tool_names are NOT in this file.
- `model_evaluation.json` — metrics only (§6).

**No serialized model exists**: no joblib/pickle/onnx artifact is written
anywhere in the pipeline (only jsonl/csv/json artifacts; pipeline:592-601,
624-632,729-733,760-764,937-945).

Runtime refit path: `godspeed_nav/ml.py:123-240`
`SklearnPredictiveModelAdapter.predict_affordances` rebuilds a frame from
`settlement_history` via `build_calibration_frame` (ml.py:158-161) and fits a
fresh `LogisticRegression(max_iter=1000, solver="lbfgs")` on every call
(ml.py:207-208), with `fillna(0)` on the frame (ml.py:192) and candidate rows
built from `payment_burden`/`risk`/`debt`/`expected_horizon_delta`
(ml.py:211-227). Two divergences from the v005 evaluation baseline:

- **Different feature list**: runtime uses only
  `[payment_predicted_total, horizon_delta, risk_estimate, debt_estimate]`
  (ml.py:185-190), not the 11 training features.
- **Different estimator args**: no `class_weight="balanced"`, no `random_state`
  (ml.py:207) vs the evaluation's balanced/lbfgs/42 (pipeline:351-356).

So the v005 held-out metrics (roc_auc 0.8266 etc.) describe the 11-feature
evaluation model, which can be re-fit exactly from `calibration_frame.csv` +
the recorded split params (row order preserved in the CSV); the runtime
4-feature adapter is a different, weaker model, exercised only for the
`sklearn_candidate_prediction` block (pipeline:704-722).

## 6. Existing metrics (transcribed from model_evaluation.json)

- calibration_rows: 6497; success_class_count: 1289; failure_class_count: 5208;
  deterministic_baseline_success_rate: 0.1984 (model_evaluation.json:2-4).
- Leakage audit (model_evaluation.json:5-21), `feature_correlations`:
  action_observation_ratio 0.1479 | avg_actions_per_step 0.111 | dataset_id
  0.0977 | debt_estimate 0.156 | error_recovery_ratio 0.1281 | horizon_delta
  0.1855 | payment_actual_total 0.1575 | payment_error 0.1491 |
  payment_predicted_total 0.1621 | risk_estimate 0.1824 | tool_diversity_count
  0.115; `leakage_detected`: false; `leaked_features`: []. (Threshold corr>=0.95,
  pipeline:685-688.)
- Held-out evaluation (model_evaluation.json:31-83): train 5197 (rate 0.1984) /
  test 1300 (rate 0.1985); class_weight balanced; sampling natural; features =
  the 11 of §1. `held_out_metrics`: raw_accuracy 0.7069 | balanced_accuracy
  0.7428 | f1_score 0.5208 | roc_auc 0.8266 | average_precision 0.6291 |
  brier_score 0.1771 | confusion_matrix [[712,330],[51,207]].
  `baseline_metrics`: majority_class raw 0.8015 / balanced 0.5 / f1 0.0;
  success_rate raw 0.3954 / balanced 0.6024 / f1 0.383. Comparisons:
  sklearn_beats_majority_on_balanced_accuracy true, on_f1 true, on_raw_accuracy
  false; beats_success_rate_on_balanced_accuracy true, on_f1 true;
  sklearn_metrics_valid true.
- sklearn_candidate_prediction (model_evaluation.json:23-30): eval_candidate,
  success_probability 0.0301, predicted_horizon_delta 0.0211, rationale
  sklearn_logistic_regression (the 4-feature runtime adapter, not the
  11-feature model).

## 7. v006-relevant observations for prefix prediction

1. **All 11 features are trajectory-global as computed.** Counters
   (`turns/tool_calls/commands/error_count/elapsed_steps`) sum over the whole
   raw record (adapter `extract_payment`s: swegym:146-203, nebius:153-191,
   agenttrove:152-175); `error_recovery_ratio`, `action_observation_ratio` scan
   all observations/actions (pipeline:167-197). None are per-turn snapshots.
2. **But all are prefix-recomputable in principle.** Settlement records preserve
   `affordance_path.actions` and `affordance_path.observations` with
   `turn_index` into the original message/trajectory sequence (swegym:80-105,
   nebius:92-121, agenttrove:67-127). A prefix = filter entries by
   `turn_index <= k`, then recompute payment counters and features with the same
   formulas (§1) using prefix counts. Recomputation is deterministic and
   label-free.
3. **`tool_names` availability is dataset-skewed**: only swegym sets
   `metadata.tool_names` (swegym_openhands_adapter.py:296); agenttrove
   (agenttrove_adapter.py:302-307) and nebius
   (nebius_swe_agent_adapter.py:263-268) do not. Result:
   `tool_diversity_count > 0` for exactly 1892/6497 rows = the swegym usable set
   (verified from calibration_frame.csv) — a de-facto dataset indicator. For
   prefix prediction over local traces, explicitly keep it (populating
   tool_names for all sources) or drop it.
4. **`dataset_id` is a strong confound**: success rate 12.68% / 100.00% / 21.91%
   by dataset (§4), yet its label correlation is lowest (0.0977) — the model can
   exploit per-dataset base rates. agenttrove contributes only 51 rows, 100%
   success; stratification is dominated by swegym/nebius.
5. **Labels exist only at trajectory end.** Prefix prediction requires carrying
   the terminal `settlement_success` back to each prefix row (label=final
   outcome); nothing in v005 stores per-turn outcomes. The frame has no
   turn/prefix dimension — `settlement_id` is dataset:task_id only.
6. **No persisted model means v006 must re-fit**: either refit the 11-feature
   evaluation model from `calibration_frame.csv` (exact split reproducible:
   test_size 0.2, random_state 42, stratify, row order preserved) or extend
   frame building with prefix rows and refit. The runtime adapter refits per
   call on the 4-feature subset with different hyperparameters (§5) — do not
   treat it as the v005 baseline.
7. **Nebius-style null crashes are a live risk for new field access** in prefix
   feature code: `raw.get(k, "")` followed by `len()`/`.lower()` raises on
   explicit nulls (§3b). Use `raw.get(k) or ""` in v006 adapters/extractors.
8. **AgentTrove cannot be re-streamed from HF via this adapter** — it is
   hardwired to the local 100-row sample (§3a); more agenttrove data in v006
   needs a real HF streaming path (fixture
   `tests/fixtures/settlement_datasets/agenttrove/sample.jsonl` has 5 rows).

## Verification methods used (no files modified)

Read-only inspection of run artifacts, pipeline, adapters, config, tests, git
history; `uv run python` snippets: agenttrove stream yield count with limit=5000
(→100); nebius `to_settlement_record` with `generated_patch=None` (TypeError),
`eval_logs=None` (AttributeError), `trajectory="not-json"`/`None` (graceful);
calibration_frame.csv dataset_id distribution/ordering/tool_diversity counts.
