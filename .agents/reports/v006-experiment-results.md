# v006 Experiment Results (plan task T05)

Preregistration: `.agents/reports/v006-experiment-preregistration.yaml`
(sha256 `2cce2a537fb1c8a4bce4ff8f31d2c8401aebfc5dd061430307eb8b341e0b6cd9`,
mtime 2026-09-15T20:21:10Z) — frozen before any results artifact (all
artifacts mtime 2026-09-15T20:42:50Z; sha + mtimes embedded in
`experiment_manifest.json`). The final test partition evaluated the
preregistered system and made no design choices.

Corpus: swegym_openhands rev `baf3a4e4…` (1574 parents, 240 S/1334 F,
license ambiguous-recorded) + nebius_swe_agent rev `68195a14…` (225 parents,
59 S/166 F, cc-by-4.0); agenttrove rejected at freeze. Split: stratified
group-level holdout, seed 42 → 533 train / 134 test groups; 1444 train / 355
test parents (56 test positives, 15.8%). GroupKFold(5) selection and OOF
calibration used the train partition only. Runtime 165.4 s; sklearn 1.8.0,
lightgbm 4.7.0, pandas 3.0.3, numpy 2.4.6, Python 3.14.6.

All cuts are well-powered (test n ≥ 234, both classes present; 6/6 reliable
in every variant). Per preregistered confound: `after_first_failure` and
`after_first_recovery` contain swegym parents only (nebius has zero
is_error events).

## 1. Leaderboard — macro ROC-AUC (mean of per-cut AUCs, reliable cuts only)

| Arm | with dataset_id | without dataset_id | early | pct25 | pct50 | aff | afr | pre-term |
|---|---|---|---|---|---|---|---|---|
| P-A (v005-prefix + LR) | **0.6438** | 0.6437 | .6644 | .6384 | .6432 | .6145 | .6148 | .6875 |
| P-B (v006 + LR) | 0.6317 | 0.6253 | .6203 | .6599 | .6865 | .5176 | .5587 | .7471 |
| P-C (v005-prefix + LGBM) | **0.6562** | 0.6576 | .6473 | .6613 | .6422 | .6899 | .6782 | .6185 |
| P-D (v006 + LGBM) | 0.6343 | 0.6376 | .6058 | .6574 | .6534 | .5996 | .5929 | .6968 |

(Per-cut columns are the with-dataset_id variant; the without-dataset_id
per-cut values are in `per_cut_results.csv`; all six cuts reliable in both
variants, so every macro averages six cuts.)

Full-trajectory family (terminal point; secondary; one row per parent,
n=355, 56 positives):

| Arm | AUC (with id / without) | AP | Brier | bal-acc | F1@0.5 |
|---|---|---|---|---|---|
| A-full (v005_full_semantics + LR) | 0.6544 / 0.6539 | 0.2544 | 0.2344 | 0.6140 | 0.3350 |
| C-full (v005_full_semantics + LGBM) | 0.6735 / 0.6800 | 0.3555 | 0.1388 | 0.5910 | 0.3095 |
| B-full (v006 + LR, DIAGNOSTIC) | 0.7407 / 0.7412 | 0.3065 | 0.2133 | 0.6749 | 0.3902 |

Historical H (context only, never a comparison target): ROC-AUC 0.8266,
AP 0.6291 on a row-level split over the historical corpus and ingestion.
No H-vs-v006 delta is meaningful and none is claimed (amendment 8).
Diagnostic observation (not part of the frozen acceptance rule): at the
terminal prediction point, B-full outscores A-full by +0.0863 AUC on the
same holdout, while the prefix cuts show no such representation gain —
the v006 signal the prefix arms can spend causally is much smaller than
what full-trajectory state encodes.

## 2. Per-cut metrics, prefix arms (PRIMARY variant, fixed 0.5 threshold)

P-A — v005_prefix_compatible + LogisticRegression

| cut | n | pos | AUC | AP | Brier | bal-acc | F1 | P | R |
|---|---|---|---|---|---|---|---|---|---|
| early | 355 | 56 | .6644 | .2440 | .2335 | .6097 | .3270 | .2077 | .7679 |
| pct25 | 344 | 56 | .6384 | .2461 | .2286 | .5965 | .3249 | .2270 | .5714 |
| pct50 | 355 | 56 | .6432 | .2368 | .2260 | .5968 | .3184 | .2207 | .5714 |
| after_first_failure | 244 | 32 | .6145 | .1823 | .2418 | .6238 | .3030 | .2000 | .6250 |
| after_first_recovery | 234 | 34 | .6148 | .2031 | .2391 | .5485 | .2651 | .1667 | .6471 |
| pre_terminal | 355 | 56 | .6875 | .2917 | .2265 | .6386 | .3551 | .2405 | .6786 |

P-B — v006 + LogisticRegression

| cut | n | pos | AUC | AP | Brier | bal-acc | F1 | P | R |
|---|---|---|---|---|---|---|---|---|---|
| early | 355 | 56 | .6203 | .2139 | .2339 | .6040 | .3243 | .2169 | .6429 |
| pct25 | 344 | 56 | .6599 | .2564 | .2289 | .6141 | .3420 | .2409 | .5893 |
| pct50 | 355 | 56 | .6865 | .2857 | .2188 | .6525 | .3793 | .2797 | .5893 |
| after_first_failure | 244 | 32 | .5176 | .1565 | .2410 | .5153 | .2051 | .1412 | .3750 |
| after_first_recovery | 234 | 34 | .5587 | .1770 | .2416 | .5709 | .2745 | .2059 | .4118 |
| pre_terminal | 355 | 56 | .7471 | .3112 | .2112 | .6760 | .3939 | .2746 | .6964 |

P-C — v005_prefix_compatible + LGBM

| cut | n | pos | AUC | AP | Brier | bal-acc | F1 | P | R |
|---|---|---|---|---|---|---|---|---|---|
| early | 355 | 56 | .6473 | .2295 | .1370 | .5229 | .1351 | .2778 | .0893 |
| pct25 | 344 | 56 | .6613 | .2328 | .1455 | .5062 | .1039 | .1905 | .0714 |
| pct50 | 355 | 56 | .6422 | .2267 | .1398 | .5145 | .1266 | .2174 | .0893 |
| after_first_failure | 244 | 32 | .6899 | .2268 | .1087 | .5109 | .0571 | .3333 | .0312 |
| after_first_recovery | 234 | 34 | .6782 | .2940 | .1182 | .5000 | .0000 | .0000 | .0000 |
| pre_terminal | 355 | 56 | .6185 | .2081 | .1492 | .5324 | .1728 | .2800 | .1250 |

P-D — v006 + LGBM

| cut | n | pos | AUC | AP | Brier | bal-acc | F1 | P | R |
|---|---|---|---|---|---|---|---|---|---|
| early | 355 | 56 | .6058 | .2128 | .1368 | .5196 | .1316 | .2500 | .0893 |
| pct25 | 344 | 56 | .6574 | .2345 | .1418 | .5042 | .0833 | .1875 | .0536 |
| pct50 | 355 | 56 | .6534 | .2265 | .1450 | .5129 | .1250 | .2083 | .0893 |
| after_first_failure | 244 | 32 | .5996 | .1806 | .1134 | .5000 | .0000 | .0000 | .0000 |
| after_first_recovery | 234 | 34 | .5929 | .1812 | .1260 | .5000 | .0000 | .0000 | .0000 |
| pre_terminal | 355 | 56 | .6968 | .2725 | .1350 | .5291 | .1687 | .2593 | .1250 |

LGBM arms predict almost everything as failure at the fixed 0.5 threshold
(near-zero recall); LR arms trade precision (~0.2) for recall (~0.6–0.77).

## 3. Calibration (frozen OOF procedure; isotonic never touches test)

| family | models | triggered (OOF ECE > 0.05) | mean OOF ECE | test Brier before → after | test ECE before → after | verdict |
|---|---|---|---|---|---|---|
| v005_full_semantics (A/C-full) | 2 | 2/2 | 0.1769 | 0.1866 → 0.1281 | 0.2045 → 0.0371 | required: YES |
| v005_prefix_compatible (P-A/P-C) | 12 | 8/12 | 0.1796 | 0.1828 → 0.1274 | 0.1903 → 0.0392 | required: YES |
| v006 (P-B/P-D) | 12 | 9/12 | 0.1690 | 0.1811 → 0.1271 | 0.1828 → 0.0350 | required: YES |
| v006-full diagnostic (B-full) | 1 | 1/1 | 0.2578 | 0.2133 → 0.1214 | 0.2805 → 0.0316 | required: YES |

Every LR-selected model triggered (OOF ECE 0.26–0.35); most LGBM models did
not (OOF ECE 0.02–0.09). Isotonic on OOF train predictions improved test
Brier/ECE wherever applied. Calibration is mandatory for any LR deployment
of these features; LGBM arms are near-calibrated raw.

## 4. Disagreement — |p_logit − p_lgbm| on the v006 feature set (P-B vs P-D, test)

| cut | mean | median | P90 | frac > 0.2 | Pearson(d, err_LR) | Pearson(d, err_LGBM) |
|---|---|---|---|---|---|---|
| early | 0.285 | 0.292 | 0.366 | 0.834 | 0.611 | 0.226 |
| pct25 | 0.285 | 0.284 | 0.418 | 0.797 | 0.478 | 0.087 |
| pct50 | 0.285 | 0.290 | 0.448 | 0.732 | 0.312 | −0.059 |
| after_first_failure | 0.342 | 0.355 | 0.377 | 0.922 | 0.493 | −0.128 |
| after_first_recovery | 0.319 | 0.323 | 0.363 | 0.962 | 0.146 | −0.192 |
| pre_terminal | 0.277 | 0.281 | 0.461 | 0.707 | 0.534 | 0.188 |

Headline: the two estimators disagree by ≥ 0.2 probability on 71–96% of
test parents per cut; disagreement tracks LogisticRegression's error
(Pearson 0.15–0.61) and is weakly or negatively correlated with LightGBM's
error. Both predictions are exposed independently in
`test_predictions.jsonl`; no fusion or averaging exists anywhere.

## 5. LODO — P-A vs P-B (WEAK evidence: two folds, unequal sizes; dataset_id omitted)

| train → eval | cut | P-A AUC | P-B AUC |
|---|---|---|---|
| swegym → nebius | early | .6935 | .6935 |
| swegym → nebius | pct25 | .7829 | .7847 |
| swegym → nebius | pct50 | .7899 | .7907 |
| swegym → nebius | pre_terminal | .7891 | .7861 |
| nebius → swegym | early | .5926 | .6206 |
| nebius → swegym | pct25 | .6308 | .5744 |
| nebius → swegym | pct50 | .5951 | .5988 |
| nebius → swegym | pre_terminal | .5968 | .5314 |

Direction is inconsistent across folds and cuts (P-B ahead 5 of 8 defined
cells, behind 3). Failure/recovery cuts are not defined for nebius (zero
error events). Marked WEAK per the frozen preregistration; no claim either
way.

## 6. Source-balanced sensitivity arm (w_s = 0.5 / n_train_parents_of_source)

| comparison (with dataset_id) | macro delta | cuts won | reading |
|---|---|---|---|
| P-B vs P-A | −0.0006 | 4/6 | still far below +0.02; NOT EARNED under weights |
| P-D vs P-A | +0.0521 | 6/6 | would pass the frozen gain rule under source balancing |

Sensitivity only, per the preregistration: the natural-mixture PRIMARY
verdict for P-D vs P-A stands (NOT EARNED). The sensitivity arm shows the
v006+LGBM combination is highly source-mixture-dependent: equalizing total
parent weight per source lifts it from below P-A to well above. Any future
adoption case must treat source mixture as a first-class condition, not a
hidden default.

## 7. Per-source test AUC (PRIMARY variant; neb = absent on failure/recovery cuts)

| arm | cut | swegym | nebius | macro |
|---|---|---|---|---|
| P-A | early | .675 | .565 | .620 |
| P-A | pct25 | .595 | .675 | .635 |
| P-A | pct50 | .598 | .643 | .621 |
| P-A | pre_terminal | .666 | .658 | .662 |
| P-B | early | .627 | .523 | .575 |
| P-B | pct25 | .630 | .677 | .653 |
| P-B | pct50 | .666 | .645 | .655 |
| P-B | pre_terminal | .754 | .647 | .700 |
| P-C | early | .649 | .534 | .592 |
| P-C | pct25 | .647 | .600 | .624 |
| P-C | pct50 | .628 | .590 | .609 |
| P-C | pre_terminal | .586 | .628 | .607 |
| P-D | early | .604 | .534 | .569 |
| P-D | pct25 | .633 | .604 | .619 |
| P-D | pct50 | .640 | .600 | .620 |
| P-D | pre_terminal | .696 | .590 | .643 |

P-B's pre-terminal edge over P-A (.7471 vs .6875) is swegym-driven
(.754 vs .666); on nebius it is a slight deficit (.647 vs .658).

## 8. Mechanical reading of the frozen acceptance criteria

Rule: macro-AUC delta ≥ +0.02 AND per-cut direction in ≥ 4 of 6 reliable
cuts; the same comparison without dataset_id must not reverse sign.

| comparison | delta (primary) | cuts won | delta (robustness) | verdict |
|---|---|---|---|---|
| representation: P-B vs P-A | −0.0121 | 3/6 | −0.0184 | NOT EARNED |
| estimator: P-C vs P-A | +0.0124 | 3/6 | +0.0140 | NOT EARNED |
| combined: P-D vs P-A | −0.0095 | 3/6 | −0.0061 | NOT EARNED |

- No comparison reached the +0.02 macro bar; none reached 4/6 cuts. Under
  the frozen rule nothing is earned for adoption.
- Identity-robustness: no delta reversed sign when dataset_id was removed
  (all three robustness deltas share the primary sign; two of them get
  worse, one slightly better). There is no identity-dependent gain because
  there is no gain; the arms are not carrying the classifier via dataset
  identity, but they are not beating the control either.
- P-B is cut-inconsistent: stronger than P-A at pct25/pct50/pre_terminal,
  clearly weaker at the failure/recovery cuts (swegym-only, error-bearing
  population). P-C is the strongest arm overall but fails the direction
  gate (wins only the two swegym-only cuts and pct25).

Settlement-relevant summary: on this corpus, at these prediction points,
the preregistered matrix did NOT earn the v006 representation, the LGBM
estimator, or their combination over the v005-prefix-compatible +
LogisticRegression control. The frozen falsifier condition "P-B ≤ P-A on
the primary endpoint" is realized (−0.0121). Signal does develop along the
trajectory (every arm peaks at pre_terminal), and calibration is a real,
fixable deficiency for LR arms.

## 9. Caveats recorded at execution

- Some LogisticRegression fits hit the frozen max_iter=1000 without full
  lbfgs convergence (largest C, unscaled payment features). The frozen
  estimator contract was kept; this is part of the evaluated system.
- The failure/recovery cuts are swegym-only (nebius zero-error confound,
  preregistered); their per-cut readings describe swegym only.
- Two frozen decisions required documented mechanical realizations
  (embedded in the preregistration, none altered a frozen quantity):
  (a) sklearn GroupShuffleSplit has no stratification support — the
  stratified group holdout is realized per group_label stratum with
  RandomState(42) and int(round(0.20·n)) test groups; (b) LODO omits
  dataset_id because it is constant within a LODO train partition
  (structurally inert). Sensitivity weights are computed per cut's train
  partition; hyperparameter ties beyond mean AP resolve to grid order.
- LGBM carries determinism flags (deterministic=True, force_col_wise=True,
  n_jobs=1) per the global determinism rule; they do not change the frozen
  hyperparameter space.

## 10. Artifacts

- `data/settlement_datasets/runs/hf-calibration-006-experiments/experiment_manifest.json`
- `data/settlement_datasets/runs/hf-calibration-006-experiments/results.json`
- `data/settlement_datasets/runs/hf-calibration-006-experiments/per_cut_results.csv`
- `data/settlement_datasets/runs/hf-calibration-006-experiments/test_predictions.jsonl`
  (17,226 records: 8 arm-variant × cut populations + 6 full-family arms)
- `data/settlement_datasets/runs/hf-calibration-006-experiments/calibration_summary.json`
- `data/settlement_datasets/runs/hf-calibration-006-experiments/disagreement_summary.json`

Validation: `uv run pytest tests/test_v006_experiments.py
tests/test_v006_features.py -q` → `63 passed, 4 warnings in 4.76s`.
Determinism: the matrix was executed twice end-to-end after fixes; the
leaderboard and all acceptance verdicts were byte-identical across runs.
