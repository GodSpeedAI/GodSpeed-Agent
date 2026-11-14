# v007 Recovery-Prediction Experiment Results (T03, Round 2 — Amendment 1)

Plan: `godspeed-agent-v007-recovery-prediction` · Prereg: `.agents/reports/v007-experiment-preregistration.yaml` (`preregistration_id: v007-recovery`) + uncommitted `amendment_1` block.
Prereg sha256s: frozen blob at HEAD (`033d578`, 2026-09-15T18:47:42-04:00) = `3998241d046ef73fa387fe77a0a747436f9fd397906804e1dbc380f539814b16` (= round-1 manifest record); working file with `amendment_1` (uncommitted, commit left to the coordinator) = `c3e19295a2442f1c686106b6dbf00d61dc7d374c6bfd8e502847322dc537519b` (= round-2 manifest record).
Episode table: `data/settlement_datasets/corpora/v007-episodes/episodes.jsonl` — 74,852 rows (37,426 R0 + 37,426 R1; 37,426 episodes), sha256 `64deaca72a7807cb04ae49de5930a3982dd9ba02fe55898ee3989a2956ea0b92` (identical in both rounds; verified before each run).
Round-2 runtime 2,079 s; manifest `created_at` 2026-09-16T01:15:25Z. Versions: scikit-learn 1.8.0, lightgbm 4.7.0, pandas 3.0.3, numpy 2.4.6, Python 3.14.6. Seeds: random_state 42; LGBM `deterministic=True, force_col_wise=True, n_jobs=1`.

## 0. Amendment 1 (round-2 split) and round-1 supersession

DEFECT (round 1): the holdout stratified on group_label alone; the seed-42 draw put ALL 11 swegym split_groups in train → **zero swegym test rows**, making the three frozen per-source evaluation cells impossible. Round-1 artifacts are preserved verbatim at `data/settlement_datasets/runs/v007-recovery/round1-stratum-defect/` (verified intact: round-1 manifest sha `3998241d…`, swegym test rows 0).

AMENDMENT 1 (2026-09-15, pre-round-2; appended to the prereg, no frozen section altered): holdout strata are **(dataset, group_label)** — each source contributes ~20% of its groups to test. No endpoint, metric, model, or acceptance criterion changed; same seed 42, GroupKFold selection, parent-balanced weights, and calibration rule. A stratum holding a single group (the swegym label-0 stratum has exactly 1 group) is assigned to test deterministically.

Round-2 split composition (per source; groups / rows / test positives, R0+R1 rows pooled):

| Source | train groups | test groups | train rows | test rows | test positives |
|---|---|---|---|---|---|
| nebius_swe_agent | 141 | 35 | 30,888 | 4,396 | 642 |
| swe_smith | 1,561 | 390 | 20,608 | 4,986 | 1,816 |
| swegym_openhands | 8 | 3 | 11,818 | 2,156 | 130 |
| total | 1,710 | 428 | 63,314 | 11,538 | 2,588 |

Per prediction point: 31,657 train / 5,769 test rows (R0: 2,198 nebius + 2,493 swe_smith + 1,078 swegym; test positives 1,294; class balance 22.4%). group_label = 1 iff ANY episode of the split_group has `recovery_success=1`; split stratification only, row labels unchanged. Test touched exactly once.

## 1. Headline: episode-level test ROC-AUC (round 2, raw probabilities)

| Point | Arm (schema) | with identity | without identity |
|---|---|---|---|
| R0 | R_LR (v007_r0@1, 44+1 feats) | **0.7578** | **0.7567** |
| R0 | R_LGBM (v007_r0@1) | 0.7557 | 0.7494 |
| R0 | R_LR ablation (v005_minimal_recovery@1, 7 feats) | 0.7520 | 0.7414 |
| R1 | R_LR (v007_r1@1, 54+1 feats) | **0.7658** | **0.7643** |
| R1 | R_LGBM (v007_r1@1) | 0.7594 | 0.7549 |
| R1 | R_LR ablation | 0.7529 | 0.7409 |

## 2. Mechanical acceptance verdicts (round 2, frozen criteria applied verbatim)

- **PRIMARY: NOT EARNED at both points — and now negative.** LGBM − LR delta: R0 **−0.0021** (without identity −0.0073), R1 **−0.0064** (without identity −0.0094). Direction held in only 1/3 per-source cells at each point (swegym only; LR beats LGBM on nebius and swe_smith). Prereg falsifier #1 ("R_LGBM ≤ R_LR at both points") is realized in round 2.
- **SECONDARY: NOT EARNED at both points.** v007 − ablation delta at R_LR: R0 **+0.0058** (direction 1/3: swe_smith only); R1 **+0.0129** with direction held **3/3** (nebius, swe_smith, swegym all positive) — but the ≥ +0.02 magnitude gate fails. R1 secondary is direction-consistent everywhere and strictly short on magnitude.
- **Classification: PARTIAL** — no hypothesis gate met, but every primary cell sits materially above the 0.5 prior (best with-identity AUC 0.7578 / 0.7658): real signal, unsettled hypotheses.
- All three per-source test cells are now populated, so the ≥ 2-of-3 gates evaluated the full preregistered evidence surface (this was impossible in round 1).

## 3. Secondary metrics per cell (round 2; fixed 0.5 threshold; Brier/ECE raw→calibrated)

| Cell | AP | Brier | ECE | Bal acc | Prec | Rec | F1 | Confusion (tn/fp/fn/tp) |
|---|---|---|---|---|---|---|---|---|
| R0 R_LR with | 0.4611 | 0.2112→0.1473 | 0.2399→0.0223 | 0.679 | 0.368 | 0.712 | 0.485 | 2891/1584/373/921 |
| R0 R_LGBM with | 0.4697 | 0.1496 (uncal) | 0.0357 (uncal) | 0.607 | 0.569 | 0.275 | 0.371 | 4205/270/938/356 |
| R0 R_LR w/o id | 0.4531 | 0.2100→0.1474 | 0.2355→0.0272 | 0.674 | 0.362 | 0.708 | 0.479 | 2860/1615/378/916 |
| R0 R_LGBM w/o id | 0.4697 | 0.1506 (uncal) | 0.0399 (uncal) | 0.607 | 0.563 | 0.275 | 0.370 | 4199/276/938/356 |
| R0 abl R_LR with | 0.4172 | 0.2157→0.1505 | 0.2516→0.0267 | 0.693 | 0.381 | 0.728 | 0.500 | 2946/1529/352/942 |
| R0 abl R_LR w/o id | 0.4043 | 0.2135→0.1523 | 0.2409→0.0259 | 0.668 | 0.340 | 0.766 | 0.471 | 2552/1923/303/991 |
| R1 R_LR with | 0.4805 | 0.2098→0.1453 | 0.2382→0.0270 | 0.684 | 0.363 | 0.747 | 0.489 | 2781/1694/328/966 |
| R1 R_LGBM with | 0.4735 | 0.1487 (uncal) | 0.0312 (uncal) | 0.619 | 0.566 | 0.306 | 0.397 | 4171/304/898/396 |
| R1 R_LR w/o id | 0.4769 | 0.2094→0.1454 | 0.2368→0.0251 | 0.684 | 0.363 | 0.747 | 0.489 | 2778/1697/327/967 |
| R1 R_LGBM w/o id | 0.4748 | 0.1492 (uncal) | 0.0358 (uncal) | 0.619 | 0.573 | 0.303 | 0.396 | 4183/292/902/392 |
| R1 abl R_LR with | 0.4181 | 0.2165→0.1503 | 0.2520→0.0283 | 0.690 | 0.377 | 0.727 | 0.497 | 2920/1555/353/941 |
| R1 abl R_LR w/o id | 0.3966 | 0.2150→0.1533 | 0.2427→0.0223 | 0.666 | 0.335 | 0.781 | 0.469 | 2464/2011/283/1011 |

Calibration verdict: the frozen rule (OOF GroupKFold isotonic iff OOF ECE > 0.05) triggered on **8/12** cells — every LR cell (OOF ECE 0.206–0.229), never LGBM (OOF ECE 0.021–0.025). Isotonic improved test Brier in **8/8** triggered cells (LR 0.209–0.217 → 0.145–0.153) and cut test ECE from ≈ 0.24–0.25 to 0.022–0.028. Selection: LR C=0.1 on both v007 schemas; LGBM 150 trees / 15 leaves / lr 0.05 (min_child_samples 50 at R0, 20 at R1).

## 4. Per-source, macro-source, parent-aggregated, LOSO (round 2)

Per-source test ROC-AUC (with-identity cells; all three sources populated):

| Cell | nebius | swe_smith | swegym | macro (3 sources) | parent-agg AUC (episode AUC) |
|---|---|---|---|---|---|
| R0 R_LR | 0.6395 | 0.6905 | 0.6428 | 0.6576 | 0.7234 (0.7578) |
| R0 R_LGBM | 0.6348 | 0.6871 | **0.7011** | 0.6743 | 0.7351 (0.7557) |
| R0 abl R_LR | 0.6440 | 0.6414 | 0.6488 | 0.6447 | 0.7174 (0.7520) |
| R1 R_LR | 0.6547 | 0.7078 | 0.6616 | 0.6747 | 0.7288 (0.7658) |
| R1 R_LGBM | 0.6424 | 0.6950 | **0.7271** | 0.6882 | 0.7359 (0.7594) |
| R1 abl R_LR | 0.6534 | 0.6460 | 0.6337 | 0.6444 | 0.7216 (0.7529) |

- **Multiplicity-inflation check:** parent-aggregated AUC is now consistently LOWER than episode-level AUC (−0.021 to −0.037): within-parent episode labels disagree enough that averaging probabilities costs ranking power. No multiplicity inflation; the episode-level headline is the conservative number.
- **LOSO** (train-without-source → held-out source, inside the train partition; globally selected hyperparameters, no re-tuning): nebius 0.652–0.680, swe_smith 0.562–0.579, swegym 0.469–0.589 for the v007 schemas vs **0.599 (R0) / 0.601 (R1) for the 7-feature ablation** — the round-1 cross-source finding replicates: the v007 representation transfers poorly to swegym out-of-source while the minimal representation holds ~0.60 there. swegym is the one source where LGBM (with identity) leads in-test (0.7011/0.7271), consistent with it exploiting source-specific (dataset_id-heavy) structure that LOSO shows does not travel.

## 5. Feature importance (top 5 per point, with-identity primary cells)

- R0 R_LGBM (gain): `dataset_id` (4.69e3, dominant), `action_observation_ratio` (1.09e3), `observation_novelty_rate` (1.07e3), `tool_switch_rate` (946), `n_events` (558).
- R1 R_LGBM (gain): `dataset_id` (4.56e3), `observation_novelty_rate` (1.74e3), `avg_actions_per_step` (1.38e3), `tool_switch_rate` (759), `horizon_delta` (519).
- R0 R_LR (|std-coef|): `payment_actual_total` (8.36), `n_events` (3.95), `fail_event_index` (3.79), `n_actions` (2.78), `error_count` (2.29).
- R1 R_LR (|std-coef|): `payment_actual_total` (7.40), `fail_event_index` (4.55), `n_events` (3.02), `recovery_attempt_count` (2.77), `error_count` (2.69).
- Ablation R_LR (R1): `dataset_id` (0.62), `tool_diversity_count` (0.51), `repeated_error_rate` (0.41), `error_count_so_far` (0.40).
- `dataset_id` again dominates LGBM gain, and in round 2 dropping it costs LGBM visibly (R0 −0.006, R1 −0.005 pooled) while LR is ±0.001 — LGBM leans on identity more than LR, yet still loses pooled ROC-AUC to LR. All importance JSON: `feature_importance.json`.

## 6. Representative predictions (best arm per point: R_LR, v007, with identity)

Full JSON with feature snippets: `representative_examples.json`. Highest-confidence correct rows are nebius negatives at p≈0.0000–0.0002 (e.g. `nebius_swe_agent:serge-sans-paille__gast-59:133c90f9c4:ep5`, y=0, p=0.0000 at both points). The confident-wrong tail is now **swe_smith positives** scored near 0 (e.g. R1 `getmoto__moto…:ep*`, y=1, p≈0.034–0.036) — the error-rich, gate-selected source remains the hard cell.

## 7. Round-1 (superseded) — preserved evidence

Round-1 artifacts (verbatim, never overwritten): `data/settlement_datasets/runs/v007-recovery/round1-stratum-defect/` (experiment_manifest.json with frozen prereg sha `3998241d…` and `created_at` 2026-09-16T00:03:10Z, results.json, per_point_results.csv, test_predictions.jsonl, calibration_summary.json, feature_importance.json, representative_examples.json, corpus_summary.json).

Defect: strata on group_label alone → seed-42 draw assigned all 11 swegym split_groups to train; swegym test rows = 0; the three frozen swegym per-source test cells were empty; macro-source and the ≥2-of-3 gates ran on 2 sources only.

Round-1 headline (episode-level test ROC-AUC, with identity): R0 R_LR 0.7164 / R_LGBM 0.7183; R1 R_LR 0.7253 / R_LGBM 0.7336. Round-1 verdicts: PRIMARY NOT EARNED at both points (deltas +0.0019 / +0.0083 — positive but below +0.02; direction 2/2 evaluable sources, not identity-reversed); SECONDARY EARNED at R1 (+0.0227, 2/2) / NOT EARNED at R0 (+0.0169); classification PARTIAL.

Round-2 shifts the picture honestly: on a test partition that represents all three sources, LGBM's round-1 edge disappears (both primary deltas negative, falsifier #1 realized), and the R1 secondary direction holds 3/3 but at half the round-1 magnitude. The reported run is round 2; round 1 stands as evidence that the LGBM edge was an artifact of a source-unrepresentative draw, not a settled capability.

## 8. Determinism, hygiene, validation (round 2)

- The split is deterministic (pinned by `test_single_group_stratum_is_assigned_to_test` and the determinism/holdout tests); the per-cell training/selection/calibration path is unchanged from round 1, where a full re-run of the R0 R_LGBM and R0 R_LR cells reproduced the persisted metric dicts identically. LR caveat unchanged: `lbfgs` hits the frozen `max_iter=1000` without converging on real-scale features (frozen estimator spec kept; results deterministic).
- `uv run pytest tests/test_v007_experiments.py tests/test_v007_episodes.py tests/test_v007_features.py -q` → `115 passed in 2.30s` (one test added: the amendment-1 per-source-coverage tooth).
- Full suite `uv run pytest -q` → `1039 passed, 2 skipped, 4 warnings in 23.58s`. The two timestamp-dirtied fixtures (`tests/fixtures/t03_work_requested.json`, `tests/fixtures/t11_canonical_golden.json`) were restored with `git checkout` afterward.
- Prereg order confirmed: HEAD blob = `3998241d…` (frozen, = round-1 manifest record); amended working file = `c3e19295…` (uncommitted, = round-2 manifest record); commit left to the coordinator. `git show HEAD:` prereg sha == round-1 manifest value; round-2 manifest value == amended file.
- Tracked `data/settlement_datasets/runs/v007-recovery/corpus_summary.json` was briefly displaced by the round-1 directory rename; restored byte-identical at its canonical path (a copy remains in `round1-stratum-defect/`).

## 9. Artifacts (round 2)

`data/settlement_datasets/runs/v007-recovery/`: `experiment_manifest.json` (versions, seeds, amended prereg sha, corpus/episode-table sha256s, per-cell train/test sizes, group_label definition, amendment-1 split strategy + `composition_by_source`), `results.json` (12 cells: selection CV tables, metrics, per-source incl. swegym, parent-aggregated; LOSO; acceptance; classification), `per_point_results.csv`, `test_predictions.jsonl` (69,228 rows: point/arm/schema/variant/episode_id/parent_id/split_group/dataset/y/p_raw/p_calibrated), `calibration_summary.json`, `feature_importance.json`, `representative_examples.json`, plus `round1-stratum-defect/` (preserved round-1 artifacts).

## 10. Reading (not part of the mechanical verdicts)

Round 2 is the harsher and more honest test: with every source represented at test, the LGBM hypothesis fails outright (it beats LR only on swegym, the smallest and most confounded cell), and the representation hypothesis shrinks to a direction-consistent, sub-threshold R1 gain whose LOSO profile shows it travels worst exactly where LGBM looked best. The durable signal across both rounds: episode-level recoverability is predictable at ~0.75–0.77 ROC-AUC from causal prefix features, LR is the stronger ranker under the frozen spec, and swegym transfer is the open hole. Debt worth recording for any future re-freeze: keep the amendment-1 strata, and treat source-level test coverage as a hard precondition.
