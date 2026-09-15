# GodSpeed-Agent v006 Dual-Model Settlement Classifier — Final Report

Date: 2026-09-15. Plan: `.agents/plans/godspeed-agent-v006-dual-model.yaml` (v0.3.0, operator amendments 1–12 incorporated).
Branch: `audit-corrections/neatcode-2026-07-29`. All work committed; H artifacts untouched throughout (git-verified).

## Classification

```text
PARTIAL — implementation works but evidence does not justify changing the default
```

The dual-model v006 system was fully implemented, preregistered, executed, and
independently audited. No preregistered gain was earned, so the runtime default
is unchanged and the historical v005 baseline remains operative. Smallest
justified next move is at the end.

## 1. Reconstructed v005 baseline (H — historical reference)

- Run: `hf-calibration-005-features` (2026-09-09), artifacts under
  `data/settlement_datasets/runs/hf-calibration-005-features/` — byte-untouched
  during v006 (`git status` empty at every checkpoint; T08 re-verified).
- Estimator: `LogisticRegression(class_weight="balanced", max_iter=1000,
  solver="lbfgs", random_state=42)`; row-level stratified 80/20 split
  (`random_state=42`); 11 features (payment_predicted_total, payment_actual_total,
  payment_error, horizon_delta, risk_estimate, debt_estimate, tool_diversity_count,
  error_recovery_ratio, action_observation_ratio, avg_actions_per_step, dataset_id).
- Recorded (historical) held-out metrics: ROC-AUC **0.8266**, AP 0.6291,
  balanced accuracy 0.7428, F1 0.5208, Brier 0.1771.
- No persisted model artifact ever existed; the runtime
  (`godspeed_nav/ml.py`) refits a different 4-feature LogisticRegression per
  call from local ledger history. Full reconstruction:
  `.agents/reports/v006-v005-reconstruction.md`.
- Historical ingestion anomalies (diagnosed, preserved as H, corrected going
  forward): agenttrove read a local 100-line file instead of streaming HF
  (`agenttrove_adapter.py` ignored `source_uri`/`split`); nebius logged 441
  per-row crashes from explicit-null HF fields swallowed by the pipeline.

## 2. Datasets, revisions, licensing, counts

| Source | Revision (SHA) | License status | Scanned | Usable parents | S / F | Verdict |
|---|---|---|---|---|---|---|
| SWE-Gym/OpenHands-Sampled-Trajectories (`train.raw`, max 3000) | `baf3a4e4bff514d48ddc08a93a2ade5c126212c7` | **AMBIGUOUS** — HF card declares no license; companion repo Apache-2.0; recorded, not inferred | 3000 | **1574** | 240 / 1334 | ADMITTED (training only; event-level corpus NOT committed) |
| nebius/SWE-agent-trajectories (`train`, max 5000) | `68195a1450865274106246d0d0296a1d6807b88e` | identified: CC-BY-4.0 | 5000 | **225** | 59 / 166 | ADMITTED (4329 exact-duplicate runs dropped; 90 instances, 41 with >1 run) |
| open-thoughts/AgentTrove (`train`, max 5000) | `b395a4307a2bc9950a90dc899438f149e115fc60` | identified: apache-2.0 | 5000 | **0** | — | **REJECTED** — every label column (`task_binary`, `judgment`, `verifier_output`, `result`, `ground_truth`) is null at this revision; README-documented `reward`/`task_id` absent; only label path is agent self-report (confidence 0.6 < 0.65 gate) |
| Agent-Ark/Toucan-1.5M | `0df3cf37f2abefb380370cfb02eabea2a35ae782` | identified: apache-2.0 | — | — | — | **REJECTED** — no verified terminal outcome label in any config; LLM-judge annotations do not gate success (NeoHorse §5.2 uses it as supervision baseline only) |

Streamed → normalized → usable: 13,000 → 13,000 → **1,799 parents**
(299 successes, 16.6%). Adapter errors after correction: **0** (historical H
had 441 on nebius alone). Ingestion corrections: agenttrove adapter now
streams HF when no `input_path`; nebius extraction is null-safe. Dedup: true
content-duplicates only; `parent_id` = trajectory run,
`group_key` = `dataset:instance`; splits key on `group_key`.
Licensing rule enforced (amendment 9): the event-level corpus lives under
`data/settlement_datasets/corpora/` (gitignored); only counts/SHA/manifest
summaries are committed. Dataset-admissibility evidence:
`.agents/reports/v006-data-and-features.md`.

## 3. Feature sets (three named families; amendment 10 distinction preserved)

- **`v005_full_semantics@1`** (11 features) — bit-exact replication of the H
  formulas from the shared corpus, equivalence-tested against
  `external_record_to_model_calibration` + `build_calibration_frame` on all
  six fixture adapters (including the `dataset_id = −1` path).
- **`v005_prefix_compatible@1`** (same 11 features, causal projection) — NOT
  the historical v005 model: prediction point and some semantics differ
  (prefix `elapsed_steps = n_context_events + k` under the verified
  context-first assumption). None of the 11 required omission; the check is
  documented in the module docstring of `v006_features.py`.
- **`v006@1`** (29 features) — deterministic trajectory-state features:
  depth (3), action/observation closure (2), tool dynamics (4: used-family
  diversity, switch rate, repeated-action rate, max repeat run), errors (4),
  recovery (5: attempts, rate, latency ×2, strategy-change-after-failure),
  verification (3: count, rate, after-edit, after-recovery), evidence (3:
  observation novelty, open streak, no-observation rate), stuck-loop (2),
  indicators (`has_failure`, `has_recovery`). Adaptations vs the NeoHorse-
  derived T01 table (tool identity = observable `cmd_family`; verification =
  `cmd_family=="test"`; novelty = hash novelty) are documented in the module
  docstring. Final-length fractions (e.g. `prefix_fraction`) are excluded as
  leakage and their absence is test-proven.
- Structural confound (audited): nebius has **zero** `is_error` events in the
  corpus — error/recovery features are swegym-supported only.
- Audit finding F1 (MAJOR, contained): nebius `counts.error_count` derives
  from terminal `eval_logs` (univariate AUC vs label = 0.918) and is consumed
  **only** by `v005_full_semantics` (A-full/C-full controls) — no prefix arm,
  no frozen endpoint affected; those controls must not be cited as clean
  trajectory-only evidence.

## 4. LightGBM

`lightgbm` **4.7.0** installed via the repo dependency manager (`uv`; `ml`
extra gained `lightgbm>=4.6`; `uv.lock` pins it; no global install).
Configuration as frozen in the preregistration: `LGBMClassifier(random_state=42,
verbose=-1, n_estimators∈{150,400}, num_leaves∈{15,31}, learning_rate∈{0.05,0.1},
min_child_samples∈{20,50}, subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0)`,
selected per (arm, cut) by GroupKFold(5) train-only ROC-AUC. Dependency
contract tests skip cleanly when the extra is absent.

## 5. Experiment results (frozen preregistration honored; test touched once)

Prediction tasks were never mixed (amendment 2). Evidence table (amendment 12):

| ID | Prediction point | Representation | Estimator | Corpus | Purpose | Macro ROC-AUC (with id / without id) |
|---|---|---|---|---|---|---|
| H | completed | historical v005 | Logistic | historical (revisions unrecoverable) | historical reference | 0.8266 (recorded; not comparable) |
| A-full | completed | v005 full | Logistic | current shared | contemporary control | 0.6544 / 0.6539 |
| C-full | completed | v005 full | LightGBM | current shared | estimator ablation | 0.6735 / 0.6800 |
| B-full (diagnostic) | completed | v006 | Logistic | current shared | terminal-point ablation | 0.7407 / 0.7412 |
| P-A | prefix | v005-prefix-compatible | Logistic | current shared | prefix control | **0.6438** / 0.6437 |
| P-B | prefix | v006 | Logistic | current shared | representation test | 0.6317 / 0.6253 |
| P-C | prefix | v005-prefix-compatible | LightGBM | current shared | estimator test | 0.6562 / 0.6576 |
| P-D | prefix | v006 | LightGBM | current shared | combined test | 0.6343 / 0.6376 |

Language discipline (amendment 8): historical v005 recorded ROC-AUC 0.8266 on
a row-level split over a duplicate-heavy corpus; the contemporary control
A-full on the corrected grouped design records 0.6544. These numbers are
**not comparable** and no improvement claim between them is made. H's 0.8266
is very likely inflated by near-duplicate same-instance runs straddling its
random split; the grouped design is the honest one.

Mechanical acceptance verdicts (frozen rule: Δmacro ≥ +0.02 AND ≥ 4/6 cuts,
no identity reversal):

- Representation (P-B vs P-A): **NOT EARNED** (−0.0121, 3/6 cuts).
- Estimator (P-C vs P-A): **NOT EARNED** (+0.0124, 3/6 cuts).
- Combined (P-D vs P-A): **NOT EARNED** (−0.0095, 3/6 cuts).
- Identity robustness: no delta reversed sign without `dataset_id` — nothing
  was gained to be identity-carried. Per-source/macro reporting shows swegym
  dominance handled (87.8% of parents; source-balanced sensitivity arm
  preregistered and reported; P-D flips to +0.0521 there — sensitivity only,
  demonstrating strong source-mixture dependence, not adopted).

Per-cut ROC-AUC (with identity; independently recomputed from raw test
predictions by both the critic and the lead agent):

| Cut | P-A | P-B | P-C | P-D |
|---|---|---|---|---|
| early | 0.6644 | 0.6203 | 0.6473 | 0.6058 |
| 25% | 0.6384 | 0.6599 | 0.6613 | 0.6574 |
| 50% | 0.6432 | 0.6865 | 0.6422 | 0.6534 |
| after first failure | 0.6145 | 0.5176 | 0.6899 | 0.5996 |
| after first recovery | 0.6148 | 0.5587 | 0.6782 | 0.5929 |
| pre-terminal | 0.6875 | **0.7471** | 0.6185 | 0.6968 |

The one real signal: v006 features help **late** (pre-terminal +0.060 over
P-A; B-full 0.7407 at the terminal point) and hurt **early** — the trajectory-
state structure they encode mostly becomes available only near the outcome.
The frozen macro rule correctly rejects adoption; this pattern is recorded as
the basis for the suggested next move, not retro-fitted into the verdict.

## 6. Prefix, cross-dataset, and calibration results

- Prefix cuts: six canonical kinds; per-cut yields, class balance, and
  eligible-parent counts reported (`per_cut_results.csv`); undefined cuts
  absent; no synthetic padding.
- Leave-one-dataset-out: 2 folds only (two admitted sources) — direction
  inconsistent (P-B ahead 4 / tie 1 / behind 3 by the critic's stricter
  tally); reported as weak evidence, as preregistered.
- Calibration: **required, YES for every family** (selected LR models had OOF
  ECE 0.26–0.35). Isotonic fit on out-of-fold train predictions only: test
  Brier 0.183 → **0.127** (v005-prefix family), 0.181 → 0.127 (v006),
  0.187 → 0.128 (full family); ECE → ~0.03–0.04. Never fitted on test.
- Disagreement: mean |p_logit − p_lgbm| ≈ 0.28–0.34 per cut; 71–96% of test
  parents exceed 0.2; disagreement correlates with LR error (r 0.15–0.61).
  Both predictions exposed independently in artifacts; **no fusion or
  averaging anywhere**.
- Threshold discipline: fixed 0.5 for precision/recall/F1; LGBM arms predict
  near-everything as failure at that threshold (recall ≈ 0–0.13) — their
  ranking quality (AUC/AP) is the meaningful comparison.

## 7. Leakage audit and independent verification

- Independent critic (T06, fresh agent, builder narrative withheld until
  after primary checks): **VERDICT: CONFIRM**, zero BLOCKERs
  (`.agents/reports/v006-critique.md`). It independently reimplemented the
  frozen split (identical 134 test groups), ran 120 post-cut mutation checks
  (bit-identical prefix vectors), reproduced all macro-AUCs and verdicts from
  `test_predictions.jsonl`, verified OOF-only calibration (54/54 rows), and
  verified prereg sha256/mtime precedence.
- Lead agent additionally recomputed the leaderboard from raw predictions
  (exact match) and re-ran every gate.
- Findings carried into the record: F1 (MAJOR, contained — eval-logs
  `error_count` in full-semantics controls only), F2 (MINOR — pct cuts keyed
  on final trajectory length; arm comparisons unaffected, absolute
  "how early" readings are conditioned), two builder overstatements corrected
  in this report (LODO tally; C-full leak linkage).
- Target labels trace to source outcome fields only; no invented labels;
  agenttrove/Toucan rejections enforced the admissibility conditions.

## 8. Tests executed

- New: `tests/test_v006_corpus.py` (49), `tests/test_v006_features.py` (43),
  `tests/test_v006_experiments.py` (20, incl. grouping/whitelist/calibration/
  determinism teeth), LightGBM dependency contract tests in
  `tests/test_computation.py`.
- Gates: full suite `uv run pytest -q` → **907 passed, 2 skipped, 0 failed**
  (includes the pre-existing `test_docs_alignment` failure, now repaired —
  see §10); `uv run pytest tests/test_docs_alignment.py -q` → 18 passed;
  runtime surfaces `tests/test_computation.py tests/test_cli_hooks_mcp.py`
  → 55 passed. (Exact final numbers re-verified at T08; see commit.)
- Experiment matrix ran twice end-to-end (165 s) with byte-identical
  results (determinism check).

## 9. Implemented runtime behavior

Unchanged by decision (T07, `.agents/reports/v006-runtime-contract.md`):
the runtime still refits the 4-feature LogisticRegression per call from local
settlement history, advisory-only, behind the existing thresholds; no dual-model
surface, no persisted production artifacts, no lightgbm runtime dependency.
Deployment-model decision recorded explicitly per amendment 7 (static artifact
vs runtime refit vs hybrid → **runtime refit stays; nothing new deployed**).

## 10. Repository repairs carried in this slice

- Pre-existing `test_docs_alignment` failure (README lost its
  implementation-defined / local-first sections in the c8498fa rewrite):
  repaired by restoring the "Using The Harness With A Project", "Project
  Learning And Absorption", and "Self-Critique" sections from AGENTS.md/
  HARNESS.md content. Debt entry removed as resolved.
- New debt recorded in `.agents/OBSERVED_DEBT.md`: nebius eval-logs
  `error_count` label-proxy caveat for any future clean control; AGENTS.md
  references `just context-check` but no justfile exists.

## 11. Unresolved issues

1. AgentTrove's label columns are null at the current upstream revision — a
   data-release question upstream, not a code fix; re-screen on revision change.
2. SWE-Gym dataset-level license remains formally undetermined (card silent;
   companion repo Apache-2.0); corpus content stays uncommitted.
3. nebius `eval_logs`-derived `error_count` remains inside frozen H semantics
   (documented caveat, not silently "fixed").
4. LODO is structurally weak with two admitted sources; a third admissible
   outcome-labeled source would strengthen cross-dataset claims.
5. The pre-terminal v006 signal (+0.060 AUC over P-A) is an observed pattern,
   not an adopted result.

## 12. Smallest justified next move

If trajectory-stage prediction matters operationally, re-preregister a
**late-cut-only endpoint** (pre-terminal / after-first-recovery cuts) on a
fresh corpus revision — the single preregistration-consistent signal this
study produced (P-B pre-terminal 0.7471 vs P-A 0.6875; direction consistent
in both identity variants and both estimators at that cut). Otherwise accept
this negative settlement and keep v005 as the operative baseline; do not
re-run the matrix hoping for a different answer.

## Artifacts index

- Plan: `.agents/plans/godspeed-agent-v006-dual-model.yaml`
- Recon: `.agents/reports/v006-v005-reconstruction.md`
- Research/data: `.agents/reports/v006-data-and-features.md`
- Preregistration: `.agents/reports/v006-experiment-preregistration.yaml`
- Experiment results: `.agents/reports/v006-experiment-results.md` +
  `data/settlement_datasets/runs/hf-calibration-006-experiments/`
- Critique: `.agents/reports/v006-critique.md`
- Runtime contract + decision: `.agents/reports/v006-runtime-contract.md`
- Code: `scripts/settlement_datasets/{build_trajectory_corpus,v006_features,run_v006_experiments}.py`,
  corrected `agenttrove_adapter.py`/`nebius_swe_agent_adapter.py`,
  `configs/settlement_datasets/v006_corpus.yaml`
