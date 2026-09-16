# v007 Independent Critique (T04, plan godspeed-agent-v007-recovery-prediction)

Critic: fresh independent agent, no builder role. Method: primary evidence first
(frozen plan/prereg, `v007_recovery.py`, `run_v007_experiments.py`, `v006_features.py`,
adapters, corpus builder, round-2 artifacts, episode table, corpus), independent
recomputation throughout; builder narrative
(`.agents/reports/v007-experiment-results.md`) read only after primary checks (step 9).
Scratch scripts in /tmp; only this file written; `git status` clean after audit;
v005/v006 artifacts untouched (tracked, clean). Focused gates re-run:
`tests/test_v007_{episodes,features,experiments}.py` = 115 passed.

## Findings

### MAJOR-1: v005-prefix `elapsed` estimate embeds post-cut context messages for 2 of 3 sources (real, quantified, immaterial to the recorded verdicts)

- `v005_prefix_compatible_features` sets `elapsed_raw = parent["n_context_events"] + k`
  (scripts/settlement_datasets/v006_features.py:353); the corpus computes
  `n_context_events = max(total_messages - len(actions) - len(observations), 0)`
  (scripts/settlement_datasets/build_trajectory_corpus.py:337) from the FULL raw
  message list. Causality therefore hinges on all context (system/user) messages
  preceding the event stream — an assumption the prereg documents and says was
  "VERIFIED against the adapters on raw fixture rows and local raw samples"
  (prereg lines 123–125). That verification does not generalize.
- Corpus-wide decisive test (events store the raw turn index `i`; turn indices are
  unique per parent): context is head-only iff `min(event i) == n_context_events`.
  Result: nebius 0/4554 violations; **swe_smith 1271/3708 parents violate
  (up to 98 context messages after the first event); swegym 918/1574 violate
  (up to 20)**. For those parents, at a cut k, `payment_predicted_total =
  n_context_events + k` counts context messages not yet seen — future information.
  Affected features (divide by `elapsed`): `payment_predicted_total`,
  `payment_error`, `horizon_delta`, `risk_estimate`, `avg_actions_per_step`
  (5 of 44 R0 / 54 R1 features; the 7-feature ablation schema is unaffected).
- Materiality: these features appear in the top-15 importance of all four primary
  cells (feature_importance.json). Single-feature test AUCs: payment_predicted_total
  0.3960 (= 0.604 reversed — carries terminal-length/label-correlated signal),
  horizon_delta 0.5484/0.5572. BUT an LR refit on the same split/weights without the
  5 features gives R0 0.7577 (full 45-feat refit: 0.7580) and R1 0.7641 (full: 0.7650)
  — deltas +0.0003/+0.0009. All frozen verdicts are negative and can only become
  more negative: the primary delta is same-feature symmetric, and the secondary
  delta (v007 vs clean ablation) shrinks further below the +0.02 bar.
- Classification: MAJOR, not BLOCKER — the leak is proven, violates the strict
  reading of REQ-V007-FEATURES for ~35%/58% of swe_smith/swegym parents, but is
  immaterial to every mechanical verdict recorded. Requires a correction slice
  (causal `elapsed` = witnessed-message count, exact reconstruction possible from
  event `i` indices) or an explicit documented deviation before any re-freeze; the
  same defect is inherited by v006's prefix-family cuts (v006 artifacts stay
  untouched; flag in the final report).

### MINOR-1: LOSO nebius range misquoted in the report

Report §4 claims v007-schema LOSO "nebius 0.652–0.680"; actual folds are 0.6516,
0.6538, 0.6712, 0.6771 → 0.652–0.677. Trivial but it is a number in the narrative
not exactly backed by artifacts. (swe_smith 0.562–0.579 and swegym 0.469–0.589
verify exactly; LR OOF ECE "0.206–0.229" verifies as 0.2063–0.2293.)

### NOTE-1: Pooled-vs-per-source gap is real and disclosed

R1 R_LR pooled 0.7658 vs macro-source 0.6747. Not primarily `dataset_id`:
without-identity pooled is 0.7643 (−0.0015); the gap is cross-source score
geometry. The report handles this honestly (per-source + macro + identity-removed
+ LOSO co-reported per prereg). Readers should quote macro/per-source, not pooled,
as the generalization estimate.

### NOTE-2: R1 window design is post-failure-inclusive by construction

`_r1_cut` (v007_recovery.py:412–426) includes the attempt action plus exactly its
consecutive trailing observations, nothing more; `attempt_result_is_error` reads
only `events[attempt+1]` (in-window). Prereg §3 documents this. Verified by code
read + mutation test.

### NOTE-3: Amendment-1 discipline

Round-1 defect (zero swegym test rows) verified in preserved artifacts
(74232 test rows: 43488 nebius + 30744 swe_smith, swegym absent). Round-2 manifest
prereg sha256 equals the amended working file (recomputed match); no endpoint,
metric, or acceptance text changed by Amendment 1 (diff is strata + provenance
only). The amended prereg was uncommitted at run time (commit left to coordinator
per report §8/line 4) — acceptable under the amendment protocol, but the commit
should land before T05.

### NOTE-4: `prior_escape_count` exception is sound

Maximality argument (each later opening requires an intervening non-error
observation, which is the earlier episode's escape; an escapeless episode is
necessarily last) verified logically, by independent re-derivation, and by
mutation invariance. Every other label-side name is refused by
`assert_no_label_features`; `n_events_total`, `n_parent_episodes` (both
full-trajectory quantities) are identity columns and never enter X (whitelist,
NON_FEATURE_COLUMNS).

## Checklist evidence

1. **Episode opening rule / re-derivation**: frozen rule implemented at
   v007_recovery.py:461–538 (maximal error-observation run preceded by >=1
   non-error observation; intervening actions transparent; final-event exclusion).
   Independent reimplementation over 10 random parents/source (30 parents, 151
   episodes): e, r0_k, r1_k, recovery_success, audit_bucket all match the episode
   table; 0 mismatches.
2. **Recovery labels**: recovery_success = terminal label AND escape (first
   non-error observation at index > e) — hand-computed on the same sample, exact
   match; escape is a genuine downstream observable; actions/claims never count.
   Audit buckets partition: 8028 + 26512 + 414 + 2472 = 37,426 = episode count;
   identical to prereg frozen values; per-source yields 6987/17642/12797 match.
3. **Future-event leakage**: mutation test (15 episodes/point, 5 per source; kinds,
   is_error, hashes randomized on ALL events strictly after the cut): R0 features
   bit-identical after post-R0 mutation, R1 features bit-identical after post-R1
   mutation (30/30 pass). Whitelist refuses label/identity columns
   (`run_v007_experiments.py:358–394`); defeat scenarios on paper:
   `consecutive_error_observations`/`current_streak_prior_nonerror` walk backward
   from the cut only; `prior_escape_count`/`fail_event_index` depend on pre-e
   positions; `prior_episode_count` counts openings < e — none can see post-cut.
   Nebius `counts.error_count` (terminal eval_logs) never reaches features: the
   only counts reader is `v005_full_semantics`, absent from every v007 schema;
   episode-table columns contain no counts-derived fields. EXCEPT MAJOR-1 above
   (`n_context_events` — the checklist's flagged candidate is CONFIRMED as a real
   but immaterial defect).
4. **Parent/group leakage**: split independently recomputed from the frozen rule
   (strata (dataset, group_label), RandomState(42), int(round(0.2*n)), single-group
   stratum to test): train 1710 / test 428 groups; recomputed test set equals the
   split_groups in test_predictions.jsonl exactly; zero overlap; zero parents with
   >1 split_group; zero parents straddling partitions. Per-source test
   groups/rows match the manifest composition block exactly (141/35, 1561/390,
   8/3; rows 4396/4986/2156).
5. **Weights**: `parent_balanced_training_weights` counts distinct episode_ids per
   parent per point (v007_recovery.py:839–851); recomputed 1/n for 10 sampled
   train parents matches; weights passed to every fit (selection, final, OOF) and
   to no metric function (evaluate_probs/per_source_metrics take no weights).
6. **Source dependence**: all three per-source cells populated in round 2
   (swegym n=1078 rows/point); per-source AUCs recomputed from test_predictions
   match the report table exactly (e.g. R1: 0.6547/0.7078/0.6616 LR,
   0.6424/0.6950/0.7271 LGBM); identity-removed variants do not reverse the
   negative primary deltas (R0 −0.0073, R1 −0.0094 without identity);
   round-1 artifacts preserved (8 files, swegym-zero defect verified); round-2
   manifest prereg sha matches the amended file.
7. **Calibration**: OOF GroupKFold isotonic only; trigger ECE>0.05 honored in
   12/12 cells (8 applied — all LR; 4 not — LGBM, OOF ECE 0.0223–0.0247);
   `maybe_calibrate` signature cannot see test labels. Recomputed Brier for R0/R1
   LR with-identity: raw 0.211166/0.209809, calibrated 0.147327/0.145260 — equal
   to calibration_summary.json to 6 decimals; Brier improved in 8/8 applied cells.
8. **Terminal-outcome encoding**: hunt result = MAJOR-1 only. `n_context_events`
   is the sole parent-level field in the feature path beyond the pre-trajectory
   `tool_names_manifest` (raw HF `tools` config — causal). Truncation test is
   trivially satisfied (stored field) and therefore not decisive; the min-i test
   above is decisive. The nebius counts block, `total_messages`, `resolved`, and
   label fields never appear in X.
9. **Honesty cross-check**: every headline, per-source, secondary-metric
   (AP/Brier/ECE/bal-acc/confusion, spot-checked 3 cells + 2 LR Briers),
   importance-top-5, selection-param, LOSO (except MINOR-1), parent-agg
   (0.7234/0.7351/0.7174 recomputed; gaps −0.021..−0.037), representative-example,
   round-1 (0.7164/0.7183/0.7253/0.7336; +0.0019/+0.0083; sec +0.0169 NOT/+0.0227
   EARNED), episode-table sha, and composition claim verifies against artifacts.
   Mechanical verdicts follow from frozen criteria: PRIMARY NOT EARNED at both
   points (deltas −0.0021/−0.0064 < +0.02; direction 1/3; falsifier #1 realized);
   SECONDARY NOT EARNED at both points (R1 +0.0129 with direction 3/3 but below
   the +0.02 bar; R0 +0.0058, 1/3); classification PARTIAL (both points ≥ 0.55,
   no gate met) — exactly the prereg's classification_rule. No overstatement
   found; §10 "Reading" is labeled non-mechanical and stays within the evidence.
10. **Headline reproduction** (test_predictions.jsonl, schema-filtered, raw probs):
    R0/R_LR 0.7578, R0/R_LGBM 0.7557, R1/R_LR 0.7658, R1/R_LGBM 0.7594 — all four
    match to 4 decimals (n=5,769 per cell). Ablation: R0 0.7520, R1 0.7529.
    Without identity: R0 0.7567/0.7494; R1 0.7643/0.7549. All match the report.

## Bottom line

The chain is trustworthy as evidence for its negative verdicts: episodes, labels,
windows, split, weights, calibration, and every reported number reproduce; the one
real defect (MAJOR-1) adds a small amount of label-correlated future information
to 5 of 44/54 features for 2 sources and cannot flip any mechanical conclusion
(all of which are NOT EARNED and would remain so with the leak removed). Fix
MAJOR-1 in a correction slice before any re-freeze or positive claim; record the
LOSO range slip.

VERDICT: CONFIRM
