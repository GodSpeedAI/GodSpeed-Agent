# V4 INDEPENDENT CRITIQUE — godspeed-agent-v008-r1-transfer (LOSO, V3 run)

Critic: independent adversarial audit; did not build or run V3. All numbers below are
reproduced from raw artifacts or re-derived with throwaway scripts, not copied from
claims. Checked for a v008 final report: none exists (only prereg + V1 reports); no
contamination.

## VERDICT-RELEVANT FINDINGS (first)

- **MINOR-1 (prereg fidelity gap, documented):** prereg section 6 promises a 6-way
  error-cause classification; `error_analysis.json` delivers 4 mechanically separable
  causes (adapter-semantics and environment-policy dropped), with the reduction stated
  explicitly in `error_analysis.json:note` and the runner docstring
  (`run_v008_transfer.py:1057-1062`). Honest, but the final report must record this as
  an implementation-defined narrowing of the frozen text.
- **MINOR-2 (frozen calibration rule is weak under source shift):** the OOF-ECE>0.05
  trigger fired in 21/21 arm-cells (OOF ECE 0.177–0.358; `calibration_summary.json`),
  i.e. it selects nothing — and isotonic **worsens test Brier in every swe_smith
  arm-cell** (T: 0.2336→0.2952; F_id: +0.0835; `calibration_summary.json`), while
  improving nebius/swegym. Headline AUCs are unaffected (raw probabilities; isotonic is
  monotone). Artifacts report this faithfully; the final report must not headline
  calibrated Brier/ECE for swe_smith.
- **NOTE-1 (implementation-defined, documented in manifest not prereg):** prereg says
  "StandardScaler fit on the training pool's rows" without weighted/unweighted; the
  runner fits weighted scalers (pool scaler, T-rule fold scaler) and an unweighted pool
  scaler for identifiability standardization. Recorded in
  `experiment_manifest.json:scaler_provenance/operationalizations`. Small influence;
  should be repeated in HARNESS/docs at V5.
- **NOTE-2 (interpretation guard):** F beats T in **all three** cells (macro 0.6602 vs
  0.6370; per-cell F>T 3/3). `primary_T_earned=TRUE` is mechanically faithful, but the
  honest reading is "the full representation transfers best; T beats only the minimal M,
  and the frozen secondary rejects T-over-F (0/3 cells)". The macro T−M margin
  (+0.0357) is dominated by swegym (+0.0618); the other two deltas are +0.0223/+0.0231.
  No significance testing is required by the frozen acceptance; the report should not
  imply more than the thresholds bought.
- **NOTE-3:** sensitivity arms cover M and T only (not F) — sufficient for acceptance
  condition (iv), which is defined on T−M; documented in the runner docstring
  (`run_v008_transfer.py:20-21`).
- No BLOCKER or MAJOR findings. Every adversarial attack I attempted failed.

## 1. SOURCE ISOLATION — PASS

- Code: `derive_t_selection`, `fit_scaler`, `select_C_and_oof`, `fit_arm` take only the
  pool (`run_v008_transfer.py:438,577,585,666`); `fit_calibrator(oof_probs, y_pool)`
  has no parameter that could receive held-out labels (:642). `run_arm` calls
  `fit_arm(pool, …)` before the held-out frame is first touched in `predict_arm`
  (:788-790). Held-out source's labels are not readable anywhere in the selection path:
  `run_cell` partitions by `dataset` (:1130-1131) before anything is fitted.
- Tested teeth: pool-only signature tests + behavioral invariance
  (`tests/test_v008_transfer.py:174-217`); 26/26 pass (`uv run pytest
  tests/test_v008_transfer.py -q`).
- Strongest evidence: my from-scratch re-run of the full matrix
  (`--results-root /tmp/v008-critic-repro`) reproduced **all six data artifacts
  byte-identically** (md5 match per file).

## 2. T-RULE FIDELITY — PASS (exact match)

Independent re-implementation of the frozen rule for the swegym cell (pool =
nebius+swe_smith): GroupKFold(5) over `split_group`, per-fold weighted LR(C=1.0,
balanced, lbfgs, rs=42) coefficient signs, per-source univariate AUC signs on fold-train
rows, per-pool identifiability (max over folds of max(AUC, 1−AUC)), per-source constancy,
gates ≥4/5, trim to 20 by min(dir, coef) folds. Result: **n_passing=37, trimmed 20/20
features identical to `t_selection.json`**, identical direction/coefficient fold counts
and identifiability AUCs on spot-checked features (error_count 5/5 ident 0.606;
tool_diversity_count 0/5 ident 0.500 constant-in-source; n_actions 5/-5 ident 0.574).

## 3. IDENTIFIABILITY GATE POWER — PASS

- `tool_diversity_count` excluded: ident AUC 1.000 in the nebius and swe_smith pools;
  constant in both sources in the swegym pool (`t_selection.json` gate tables). 8
  constant-in-a-source features excluded per pool (same 8 in each cell).
- Synthetic check (my script): planted perfect source-separator (noise 0.01σ) with
  source-correlated label → worst ident AUC **1.0000 → excluded**; a genuine
  label-tracking feature (ident 0.726) → retained. The 0.85 gate has real power.

## 4. LEAKAGE SCAN — PASS

- `dataset_id` absent from M/F/T feature lists in all cells (`results.json`
  representations + arms). All primary feature lists contain zero of the 17
  episode/bookkeeping columns (`NON_FEATURE_COLUMNS`, runner :194-196; guard
  `assert_no_identity` :264-273 refuses them; refusal tested at
  `tests/test_v008_transfer.py:225-239`).
- Label-side names structurally excluded (`assert_no_label_features`; FORBIDDEN
  substrings escape/recovery_success/label/settlement, `v007_recovery.py:235-238,334`).
  The single exception `prior_escape_count` is the documented frozen causal feature
  (prior episodes only). `has_recovery` (selected in 2 T sets) is prefix-causal
  ("error observation followed by a non-error observation within the prefix",
  `v006_features.py:523-525`) — computable at the R1 point, not label-side.

## 5. WEIGHTS — PASS

Recomputed on the real nebius+swe_smith pool: per-source total weight exactly 0.5 each
(swe_smith 2,413 parents, swegym 1,575); per-parent totals equal within source
(2.072e-4 / 3.175e-4); matches the direct formula 1/(2·n_parents). Weights are fit-only:
`evaluate_probs(y, p)` has no weight parameter (runner :737-768).

## 6. CALIBRATION ISOLATION + BEHAVIOR — PASS (see MINOR-2)

Isotonic fit on OOF training-pool predictions of the selected C only; applied iff OOF
ECE > 0.05; applied to held-out raw probs afterwards (`run_arm` :791-794). Structural:
calibrator signature cannot accept held-out labels (tested :188-190). All 21 arm-cells
triggered; swe_smith degradation confirmed from both `calibration_summary.json` and raw
predictions.

## 7. SPLIT INTEGRITY — PASS

- split_group straddle between pool and held-out: **0** for all three cells (parent_id
  straddle also 0) — checked on the episode table directly.
- `test_predictions.jsonl`: 262,332 rows = 37,476 × 7 arms. Per (cell, primary arm):
  episode-id sets **exactly equal** the held-out source's R1 episode set, labels match
  the table, zero duplicates; `dataset == cell` in 100% of rows; exactly one test
  evaluation per arm.

## 8. HEADLINE REPRODUCTION — PASS (exact)

Recomputed from `test_predictions.jsonl` (raw probs):

| held-out cell | M | F | T | T−M |
|---|---|---|---|---|
| nebius_swe_agent | 0.6512 | 0.7137 | 0.6735 | +0.0223 |
| swe_smith | 0.5777 | 0.6218 | 0.6008 | +0.0231 |
| swegym_openhands | 0.5749 | 0.6450 | 0.6367 | +0.0618 |
| **macro** | **0.6013** | **0.6602** | **0.6370** | **+0.0357** |

Brier spot-checks (swe_smith|T 0.233567; swegym|M 0.249030) and AUCs match
`results.json`/`per_cell_results.csv` to full precision. Secondary T−F: macro −0.0231,
T≥F 0/3 → not earned, as claimed.

## 9. PREREG FIDELITY — PASS

- Manifest `preregistration.sha256` = b2b7ba2a8aae… == disk file == `git show
  b61edc3:…` (prereg untouched since freeze); manifest `git_head_commit` = b61edc3.
- Frozen T thresholds (≥4/5, ident <0.85, non-constant, fill-5/trim-20), weighting
  (parent×source primary; parent-only sensitivity), preprocessing (pool-fit scaler),
  estimator (LR balanced/lbfgs/max_iter=1000/rs=42; C∈{0.01,0.1,1.0} — all 21 best_C in
  grid, chosen by GroupKFold mean ROC-AUC; swe_smith|T cv_table confirms C=1.0 wins),
  calibration trigger, metric block, macro definition, mechanical acceptance, and
  classification mapping all match the frozen sections. Trim engaged in all cells
  (34–37 passing > 20); fill never needed. `prior_escape_count` substring exception is
  prereg-lineage v007, not a v008 deviation.

## 10. DETERMINISM / PRESERVATION — PASS

- Manifest-recorded md5s match disk for all six artifacts; `runs:2, byte_identical:
  true`; no wall-clock fields in the six data artifacts. My independent re-run
  reproduced all six byte-identically (190.6s).
- Episode parity: table = 74,952 rows, **37,476 R1** (nebius 17,642 / swe_smith 12,797
  / swegym 7,037), 8,028 positives — matches prereg totals and
  `corpus_summary_v1c.json`; per-source positives 2,485/4,837/706 match
  `results.json`.
- `git status`: zero tracked modifications (only untracked v008 outputs + runner +
  tests). v006/v007 corpora and run dirs have mtimes predating the V3 run (17:35+);
  v007-recovery artifacts last written 15:32 (prior slice). Runner writes only under
  `runs/v008-transfer/` and imports (never forks) `v007_recovery`.

## ACCEPTANCE MECHANICS (verdict fidelity)

Recomputed mechanically from reproduced deltas: (i) macro T−M +0.0357 ≥ +0.02 ✓;
(ii) T≥M 3/3 ≥ 2 ✓; (iii) worst cell +0.0223 ≥ −0.03 ✓; (iv) sensitivity macro +0.0142
> 0 ✓ (recomputed: 0.630286 − 0.616134); (v) no identity/bookkeeping column in any
primary arm ✓. → `primary_T_earned=TRUE` follows mechanically; `classification =
SETTLED_earned` per the frozen mapping; `secondary_T_vs_F=FALSE` correct. Nothing
overstated numerically; the only overstatement risk is interpretive (see NOTE-2).

VERDICT: CONFIRM
