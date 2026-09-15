# v006 Experiment Chain — Independent Critic Audit (T06)

Auditor: independent critic (did not build). Method: primary-artifact recomputation,
independent reimplementation of the frozen split, adversarial mutation tests, line-by-line
prereg comparison. Builder's narrative (`v006-experiment-results.md`) read only after
checks 1–8 were complete. All scripts were throwaways under `/tmp/v006-audit/`; the only
file written in-repo is this report.

## Verdict-relevant findings first

### F1 [MAJOR] Terminal-eval leakage exists, but only in the secondary FULL arms (A-full, C-full)

- Provenance: nebius `counts.error_count` = keyword count over terminal `eval_logs`
  (`scripts/settlement_datasets/nebius_swe_agent_adapter.py:163-168`). Those logs are the
  outcome evidence itself (`extract_outcome`, lines 123-151). Empirically it is a label
  proxy: univariate ROC-AUC(label ~ −error_count) = 0.918 on the 225 nebius parents; all
  31 parents with error_count==0 are successes (my corpus recompute).
- Consumption scope (exact): only `v005_full_semantics_features` reads the `counts` block
  (`scripts/settlement_datasets/v006_features.py:264-268,273-277`), and only arms A-full
  and C-full use that family (`run_v006_experiments.py:120-124`). Both are
  secondary/diagnostic and appear in no frozen acceptance rule.
- Prefix arms are clean: P-A (`v005_prefix_compatible`) and P-B/P-D (`v006`) derive error
  features from prefix `is_error` events only; nebius has 0 is_error events in the corpus
  (verified: 17,592 for swegym, 0 for nebius). B-full (v006 at k=n) is also clean of the
  counter (nebius error features are constant 0).
- Consequence: C-full's nebius per-source AUC 0.8690 (vs overall 0.6735, `results.json`
  full_family) is partially outcome-tainted; A-full/C-full numbers must not be cited as
  clean "trajectory-only" evidence. No primary endpoint, no acceptance verdict, and no
  P-arm number is affected. Direction check: the leak inflates the v005-family FULL arms,
  so the reported diagnostic B-full > A-full gap (+0.0863) is, if anything, understated.
- Disclosure: the prereg disclosed the confound generically before the run (lines 50-57);
  the results narrative does not connect it to C-full's nebius number. That omission is
  the MAJOR part, not the leak reaching the frozen rule.

### F2 [MINOR] pct25/pct50/pre_terminal cut placement keys on final trajectory length

`_cut_k` (`v006_features.py:671-692`): k = ceil(0.25·n), ceil(0.50·n), n−1 — the observer
at the cut cannot know n mid-run, and n correlates with outcome. Absolute "how early can
we predict" readings on these three cuts are conditioned on future length (the strongest
cut, pre_terminal, is the most affected). Arm-vs-arm comparisons are unaffected (all arms
share identical populations and k per cut). The leakage guard
(`assert_no_leaky_features`, `v006_features.py:858-873`) covers feature values, not cut
placement; the module principle ("prefix position is only legal against an exogenous
budget", docstring lines 87-89) is applied to values but not to cut anchors. Cuts are
prereg-frozen, so this is an interpretation caveat, not a deviation.

### F3 [MINOR] Prereg's "Historical H metrics are co-reported" is not honored in artifacts

Prereg `arms` block: "Historical H metrics are co-reported as context". Grep of
results.json / experiment_manifest.json / calibration_summary.json /
disagreement_summary.json: zero H metrics, zero "historical" mentions. H appears only in
the narrative (section 1), quoted correctly (ROC-AUC 0.8266 verified in
`data/settlement_datasets/runs/hf-calibration-005-features/summary.json`), explicitly
context-only, row-level split, no comparison claimed. Under-report is the conservative
direction; still a prereg deviation.

### F4 [MINOR] Narrative LODO miscount

`v006-experiment-results.md:147`: "P-B ahead 5 of 8 defined cells, behind 3". Recount
from `results.json` lodo block: ahead 4, behind 3, tie 1 (swegym→nebius early is an exact
tie .6935/.6935). Conclusion unchanged (direction inconsistent).

### F5 [NOTE] Prereg freeze has no external anchor

Prereg is git-untracked; `frozen_at: 2026-09-15T20:05:00Z` but file mtime 20:21:10Z (16
min later, presumably mechanical-realization additions). The manifest pins sha256
`2cce2a53…` which matches the file on disk now, so the run used the audited content.
Recommend: commit preregs before running.

### F6 [NOTE] Secondary selection/quality effects, disclosed

- nebius rows without eval_logs get confidence 0.3 and are rejected (446 rows,
  corpus_manifest top_rejection_reasons) — the nebius subset is conditioned on eval-log
  presence. Disclosed in corpus_manifest.json.
- Some LR fits did not converge at the frozen max_iter=1000 (narrative §9; part of the
  evaluated system, honestly disclosed).
- swegym license ambiguous — recorded per prereg; corpus local-only (gitignored).
- "Executed twice, byte-identical" determinism claim is unverifiable from artifacts, but
  my independent split + metric reproduction matched everything, consistent with it.

## Checklist results (evidence)

1. TARGET LEAKAGE — CLEAN for all preregistered endpoints. X columns come only from
   `FAMILY_FEATURES[family]` + sanctioned `dataset_id` (`run_v006_experiments.py:260-292`);
   `assert_no_label_columns` refuses label/identity columns (lines 245-257);
   `assert_no_leaky_features` refuses final-length-derived names. On-paper defeat
   attempts fail: no family feature name collides with LABEL_COLUMNS; extractors read
   only events/counts/manifest/n_context_events; `label` never enters X. The one impurity
   is F1 (counts block → A-full/C-full only). dataset_id as PRIMARY identity feature is
   preregistered and its removal is the robustness variant.
2. FUTURE-PREFIX LEAKAGE — CLEAN. Own test (not the builder's): 5 random parents per
   dataset (seed 20260915), every defined cut, mutate ALL events at positions >= k
   (content/hash/is_error/cmd_family/role/has_terminal_output) and re-extract: 120/120
   feature dicts bit-identical for both prefix families; flipping `label` changes nothing
   (extractors label-independent).
3. PARTITION INTEGRITY — CLEAN. (a) Split groups by group_key:
   `stratified_group_holdout` (`run_v006_experiments.py:192-221`) permutes sorted group
   keys per group_label stratum; `assert_partitions_grouped` (224-237) refuses straddling.
   (b) I reimplemented the split independently from the prereg text: identical 533/134
   groups; the 134 group_keys in test_predictions.jsonl are exactly my test groups; 355
   test parents, 56 positives = manifest; 0 train parents in predictions; 0 group overlap.
   (c) Test populations per cut are identical across all 8 (arm, identity_variant)
   combos (355/344/355/244/234/355); 0 duplicate (arm,variant,cut,parent) rows;
   0 (y,dataset,group_key) inconsistencies across 17,226 records; y equals corpus label
   for all records. No cut's test set is drawn from a different split.
4. LABEL DEFENSIBILITY — CLEAN. Labels trace to source outcome fields only: swegym
   `resolved` (+test_result), nebius `target` (adapters `extract_outcome`);
   `build_parent` rejects undefined success / confidence < 0.65 and records
   `label_source` (`build_trajectory_corpus.py:289-368`). No invented labels. Nebius
   duplicates handled: 4,329 exact content-hash duplicates dropped (label included in
   hash); one row per parent per cut structurally (`plan_prefix_cuts` dedup by k;
   verified 0 duplicates in the 9,512-row prefix frame; manifest train_rows ==
   train_parents at every cut).
5. PREREGISTRATION FIDELITY — HONORED. Arms (P-A..P-D, A-full, C-full, B-full
   diagnostic), estimator specs and frozen grids, selection metric (mean GroupKFold(5)
   ROC-AUC, AP tiebreak), split quantities (0.20/42/stratified-by-group_label with the
   prereg-embedded mechanical realization — which I reproduced exactly), calibration
   rule, disagreement spec, LODO spec, sensitivity trigger (1574/225 > 3) and w_s,
   acceptance rule (Δ≥+0.02, ≥4/6 reliable cuts, sign-reversal block) — all executed as
   frozen; no added or missing arm; no threshold changed. Timestamps: prereg mtime
   2026-09-15T20:21:10Z < artifacts 20:42:50Z; prereg sha256 in manifest matches disk.
   Only deviation: F3 (missing H co-report in artifacts).
6. CALIBRATION — CORRECT. `maybe_calibrate` signature takes (oof_probs, y_train,
   test_probs) — no path fits on test (`run_v006_experiments.py:499-527`); isotonic fit
   on OOF GroupKFold train predictions, trigger oof_ece > 0.05. CSV consistency:
   calibration_applied == (oof_ece > 0.05) in 54/54 rows. Recomputed P-B@pct50 from
   test_predictions.jsonl: Brier raw 0.218817 → calibrated 0.129541, matching
   per_cut_results.csv to full precision (0.21881747 / 0.12954074). Narrative OOF-ECE
   ranges verified (LR 0.2576–0.3518; LGBM 0.0206–0.0895).
7. HEADLINE REPRODUCED — from test_predictions.jsonl alone (uncalibrated p, mean over
   the six reliable cuts, with_dataset_id):
   - P-A 0.6438, P-B 0.6317, P-C 0.6562, P-D 0.6343 — identical to leaderboard.
   - Acceptance: P-B vs P-A Δ=−0.0121 (3/6 cuts, robust Δ=−0.0184) NOT EARNED;
     P-C vs P-A Δ=+0.0124 (3/6, robust +0.0140) NOT EARNED; P-D vs P-A Δ=−0.0095
     (3/6, robust −0.0061) NOT EARNED. All three preregistered NOT-EARNED verdicts
     hold; no sign reversal anywhere (no identity-dependent gain because no gain).
8. H/A/P SEPARATION + H INTACT — PASS. `git status --short
   data/settlement_datasets/runs/hf-calibration-005-features/` → empty. H kept
   historical everywhere: prereg ("explicitly NOT compared as improvement evidence"),
   narrative ("context only, never a comparison target"; numbers correctly quoted from
   the 005 run). No H-vs-v006 delta is computed or implied in any artifact.
9. HONESTY CROSS-CHECK — narrative numbers all match my recomputation (leaderboard,
   per-cut tables, calibration table, disagreement table, LODO table, sensitivity
   deltas −0.0006/+0.0521, per-source spot checks P-B pre_terminal .7536/.6465).
   Negative results are foregrounded, not hidden (all three NOT EARNED; the falsifier
   realized). The sensitivity P-D +0.0521 6/6 "would pass" is correctly kept
   sensitivity-only with the source-mixture dependence named. Two overstatements found,
   both minor: F4 (LODO count) and the F1 omission (C-full's nebius strength not
   connected to the eval-log counter).
10. WEIGHTS — VERIFIED. One row per parent per cut (frame + artifacts). Sensitivity
    weights w_s = 0.5/n_train_parents_of_source recomputed on the real frame per cut's
    train partition: each source's weights sum to exactly 0.5000 at every cut
    (failure/recovery cuts: swegym-only 0.5, as preregistered). PRIMARY arms use
    uniform ones (code path `weights=None` → ones), matching the prereg's
    mechanical realization; `weight_base` = 1/n_prefixes per parent, carried but unused.

Tests: `uv run pytest tests/test_v006_experiments.py tests/test_v006_features.py
tests/test_v006_corpus.py -q` → 112 passed.

## Bottom line

The frozen preregistration was honored; the split, labels, prefix causality, calibration,
and weights are clean under adversarial re-derivation; all headline numbers reproduce
exactly from the primary artifact; the negative verdicts (all three NOT EARNED) are
correct and honestly reported. The only material defect (F1) is confined to the
secondary full-trajectory arms and cannot have inflated any preregistered conclusion;
it must be cited whenever A-full/C-full per-source numbers are used.

VERDICT: CONFIRM
