# C4 INDEPENDENT CRITIQUE — godspeed-agent-v007-prefix-correction

Critic: independent adversarial verifier (did not build or run the correction).
Date: 2026-09-16. Method: code read + numeric attack on raw artifacts
(`v007c-trajectories`, `v007c-episodes`, `runs/v007-recovery/` round-3 files) +
a fully independent rerun of the frozen matrix to `/tmp/v007c-critic-rerun`.

## Findings (classified)

- No BLOCKERS. No MAJORS.
- MINOR-1 (housekeeping): round-3 artifacts and the runner `--corpus-root`
  provenance flag are uncommitted at critique time (git: 7 modified files under
  `data/settlement_datasets/runs/v007-recovery/`, 1 untracked
  `round2-pre-correction/`, modified `run_v007_experiments.py`). The runner
  diff is provenance-only (records corpus sha256s; no frozen logic touched —
  diff reviewed). Commit with C4.
- NOTE-1: the builder's "results.json byte-identical across two round-3 runs"
  claim had only one surviving copy on disk. CLOSED by critic: my independent
  rerun (same episode table, seed 42, committed runner) reproduced
  `results.json` md5 `b06ee86b41b88aa2bccdc1c5c1285f97` and
  `test_predictions.jsonl` md5 `e59ca1005a41d561f54f50b92004a49e` exactly.
- NOTE-2: nebius has 0 interleaved-context parents (all context leading), so
  the old-vs-new formula is a no-op there; leak power comes from swe_smith and
  swegym. Consistent with the prereg ("nebius 0/4554 — clean") and with
  near-zero round-2-to-3 nebius movement.
- NOTE-3: swegym test-group fraction is 3/11 = 27.3% (single-group strata go to
  test deterministically). Amendment-1-conformant; not a defect.
- NOTE-4: frozen prereg section 4 `splits` still reads "per group_label
  stratum"; the operative rule is the Amendment-1 strata (dataset, group_label),
  which the amendment block, the manifest, and the code all implement. Frozen
  text is rightly left untouched; no action.
- NOTE-5: `v007_r0@1`/`v007_r1@1` tags are unchanged even though the embedded
  prefix family moved to `v005_prefix_compatible@2` (names/counts unchanged, so
  this is per Amendment-2; the @2 bump is test-pinned in
  `tests/test_v006_features.py::test_schema_versions_are_the_three_normative_tags`).
- Checklist 11: `.agents/reports/godspeed-agent-v007-corrected-final.md` does
  NOT exist yet — skipped per instructions.

## 1. Leak removed — CONFIRMED (code + numeric, with power)

Code: `scripts/settlement_datasets/v006_features.py`
`v005_prefix_compatible_features`: `ctx_through_cut = events[-1].get("ctx", 0)`;
`elapsed_raw = ctx_through_cut + k` (lines ~372-373). No `n_context_events`
reference remains in any executable prefix path (only docstrings). Pre-C1 code
(`git show aabf707~1`) had `elapsed_raw = parent["n_context_events"] + k` and
tag `@1`; now `@2`. Corpus builder
`scripts/settlement_datasets/build_trajectory_corpus.py` sets
`event["ctx"] = bisect_left(sorted(context_positions), event["i"])`
(context strictly below turn index) from the new adapter `context_positions()`
methods (base default `[]`; nebius/swegym/swe_smith overrides match their
extract role sets). All three sources `context_scoped: true` in the corpus
manifest.

Numeric attack (real corpus parents, repo code imported, cuts chosen strictly
BEFORE future context so the leak would manifest, all 5 affected features
checked):

- swe_smith: 10/10 interleaved parents — code == recomputation from
  `ctx_k + k`; OLD formula (`n_context_events + k`) differs in 10/10.
- swegym_openhands: 10/10, OLD differs in 10/10.
- Example: `swe_smith:django__channels.a144b4b8...` k=9, ctx_k=10, n_ctx=16:
  predicted 19 (new) vs 25 (old).
- 20 parents with power >> the 6 required.

## 2. Mutation invariance — CONFIRMED

6 parents per dataset (18 total): deepcopied, 3 synthetic events appended above
max index, 5 extra context positions appended, `ctx` recomputed per the builder
rule; prefix features at the original cut bit-identical (values AND types),
18/18.

## 3. Full semantics untouched — CONFIRMED

`v005_full_semantics_features` still reads only `parent["counts"]` verbatim.
Numeric check on an interleaved swe_smith parent (n_ctx=16): predicted_total =
31.0 = `counts.elapsed_steps` = `total_messages` (not ctx-derived);
payment_error and avg_actions_per_step match counts-block arithmetic.

## 4. Input provenance — CONFIRMED

Round-3 manifest records `v007c-episodes` (episodes.jsonl sha256 789895c3...,
manifest 39f9c42a... — both match on-disk files) and `v007c-trajectories`
(file sha256s match the corpus manifest). Revisions unchanged: swegym
baf3a4e4 / nebius 68195a14 / swe_smith 08e109b4. Prereg sha256 e661b3f7...
matches the file; Amendment-2 committed (fc3f984, 17:28Z) before the round-3
run completed (manifest created_at 19:32:34Z). Episode parity v007-episodes vs
v007c-episodes: 74,852 rows each, keys identical, exactly 6,580 rows differ,
differing fields are exactly the 5 affected features (0 rows differ outside
them), `payment_predicted_total` strictly decreased in all 6,580. Aggregate
audit buckets equal the frozen numbers (8028/26512/414/2472; sum 37,426).

## 5. Split integrity — CONFIRMED

Recomputed with the runner's own `group_labels_from_frame` +
`stratified_group_holdout` on the v007c table, seed 42: 1,710 train / 428 test
groups; test set EXACTLY equals the split_groups in `test_predictions.jsonl`;
disjoint; `assert_partitions_grouped` guard passes; all three per-source test
cells non-empty (swegym 12,936 / nebius 26,376 / swe_smith 29,916 rows across
12 cells). Round-1 defect (zero swegym test rows) is gone.

## 6. Calibration isolation — CONFIRMED

`maybe_calibrate(oof, y_train, test_probs)`: signature cannot receive test
labels; isotonic fit on OOF train predictions only; trigger 0.05 on OOF ECE.
Behavior: LR cells (OOF ECE ~0.21) calibrated; LGBM cells (~0.025) not.
Recomputed from `test_predictions.jsonl` to <1e-12: R0 LR Brier 0.211964 raw →
0.147431 calibrated; R1 LR 0.210157 → 0.145432 (matches results.json, which
reports headline metrics on raw probabilities; isotonic is monotone so AUC is
invariant).

## 7. Weights — CONFIRMED

`parent_balanced_training_weights`: 1/(distinct train episode_ids per parent).
Recomputed on the R0 train partition: 31,657 rows (matches manifest), 6,875
parents, per-parent weight sums exactly 1.0; example parent with 7 episodes →
1/7 per row. Passed to `est.fit` and CV selection only; `evaluate_probs` has no
weight parameter (metrics unweighted). No test rows in train frames.

## 8. Headline reproduction — EXACT (independent rank-based AUC)

From `test_predictions.jsonl` (schema-filtered, raw probabilities):

| cell (with_identity)      | reproduced | claimed |
|---------------------------|-----------|---------|
| R0 R_LR v007_r0           | 0.756590  | 0.7566  |
| R0 R_LGBM v007_r0         | 0.752501  | 0.7525  |
| R0 R_LR minimal           | 0.751998  | 0.7520  |
| R1 R_LR v007_r1           | 0.764949  | 0.7649  |
| R1 R_LGBM v007_r1         | 0.758051  | 0.7581  |
| R1 R_LR minimal           | 0.752929  | 0.7529  |

Attention cell R1 v007_LR minus minimal_LR, per source: nebius 0.6545 vs 0.6534
(+0.0010), swe_smith 0.7079 vs 0.6460 (+0.0619), swegym 0.6481 vs 0.6337
(+0.0144) — 3/3 positive, as claimed. Round-2 deltas: R1 rep-minus-minimal
+0.0120 (round 2: +0.0129, recomputed from the preserved round-2 file).

## 9. Verdict fidelity — CONFIRMED (mechanical)

Frozen criteria (+0.02; per-source >= 2/3; no identity reversal):
- PRIMARY: LGBM − LR = −0.0041 (R0) and −0.0069 (R1); per-source direction 1/3
  at both points; falsifier "R_LGBM <= R_LR at both points" fires →
  PRIMARY NOT EARNED (negative). `results.json` acceptance records exactly
  this (earned=false, sources_held 1/3, identity_reversed=false).
- SECONDARY: R1 delta +0.0120 < +0.02 (R0 +0.0046, 1/3) → NOT EARNED even with
  3/3 direction at R1. PARTIAL classification (both points materially above
  0.5 prior, margin 0.05) follows the frozen classification_rule.

## 10. Determinism + preservation — CONFIRMED

Critic's independent rerun (runner from HEAD + corrected v007c inputs, seed 42,
output to /tmp) produced `results.json` BYTE-IDENTICAL to the reported round-3
file (md5 `b06ee86b...`), including cells, split, acceptance, classification;
`test_predictions.jsonl` also identical. Round-1 dir is tracked and unmodified;
`round2-pre-correction/` present and genuine (its headline 0.7578/0.7557/
0.7658/0.7594 matches the round-2 report). Internal control: all four minimal
cells metric-identical between rounds 2 and 3 (+0.000000) — the correction
touched only prefix-family inputs. Pre-correction corpus preserved at
`corpora/v007-trajectories` (distinct hashes); git status shows no changes
outside `runs/v007-recovery/` and the runner flag; v006 artifacts untouched.
Regression suites green: `tests/test_v007_features.py` + `tests/test_v006_features.py`
= 93 passed.

## Bottom line

The leak is removed with demonstrated power, the frozen experiment was rerun
unchanged except the corrected feature inputs, every headline and the
attention-cell direction reproduce exactly, and the verdicts follow
mechanically from the frozen criteria. The corrected conclusions are: recovery
signal is real at both points (~0.75 AUC) but neither preregistered hypothesis
is earned; the leak was verdict-immaterial (all four headline cells moved
down by <= 0.0032).

VERDICT: CONFIRM
