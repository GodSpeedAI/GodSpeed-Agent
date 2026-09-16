# GodSpeed-Agent v007 Recovery Predictor — Final Report

Date: 2026-09-15. Plan: `.agents/plans/godspeed-agent-v007-recovery-prediction.yaml`.
Builds on settled v006 work (untouched; two post-audit findings against v006
evidence recorded below). Branch: `audit-corrections/neatcode-2026-07-29`.

## Classification

```text
PARTIAL — recovery signal exists but evidence/generalization is insufficient
```

A trustworthy recovery-prediction experiment was constructed, preregistered,
executed twice (Amendment-1 correction round), and independently audited
(VERDICT: CONFIRM, no blockers). The predictor discriminates materially above
chance at both prediction points, but no preregistered acceptance gate was
met, cross-source generalization is weak, and one inherited (verdict-
immaterial) leakage channel was found in the v005-prefix feature family.

## 1. Prediction question and unit of analysis

Question: given that a meaningful execution failure has just occurred, does
the observable state indicate the agent will recover and reach settlement?
Advisory only; no controller policy decisions were implemented.

Unit: the **failure episode** — opening at the first error observation of a
maximal error-observation run preceded by ≥1 non-error observation, with the
failure event `e` excluded if final (0 exclusions realized). Realized corpus:
**37,426 episodes / 74,852 rows** (R0 + R1), mean 4.56 episodes per parent
(max 68) — parent-balanced training weights were load-bearing.

## 2. Recovery definition (preregistered before any training)

`recovery_success = 1` iff the parent trajectory reached verified terminal
settlement AND an escape event (first non-error observation after `e`) is
observable. Escape, tool changes, further actions, or agent claims alone
never count. Audit buckets (frozen + completing cell):
escape_with_settlement 8,028 · escape_no_settlement 26,512 ·
no_escape_with_settlement 414 · no_escape_no_settlement 2,472.
Label-side quantities (escape, terminal outcome) are structurally excluded
from features (mutation-test-proven; whitelist-guarded).

## 3. Datasets (admitted with revisions; rejected with reasons)

| Source | Revision | License | Usable parents | Episodes | % positive |
|---|---|---|---|---|---|
| SWE-Gym/OpenHands-Sampled-Trajectories (`train.raw` ≤3000) | `baf3a4e4…` | ambiguous (card silent; companion repo Apache-2.0) — local training only, content never committed | 1,574 (240 S/1,334 F) | 6,987 | 10.1% |
| nebius/SWE-agent-trajectories (`train` ≤5000) | `68195a14…` | cc-by-4.0 | 4,554 (998 S/3,556 F) | 17,642 | 14.1% |
| SWE-bench/SWE-smith-trajectories (`tool` ≤5000) — **newly admitted** | `08e109b4…` | mit | 3,708 (2,368 S/1,340 F) | 12,797 | 37.8% (gate-selection documented) |

Rejected with evidence: Toucan-1.5M (v006, no verified outcomes), AgentTrove
(v006, label columns null at live revision), SWE-Gym/SWE-Gym (no trajectory
content), R2E-Gym SFT/Verifier sets (no outcome field / judge-derived rewards).

**v006 post-audit finding (recorded, v006 untouched):** v006's "nebius has
zero error events" was an adapter field bug — live events carry `text`, the
adapter read `content`; every v006 nebius event had empty content. The v007
adapter reads text-first (fixtures keep `content`). All v006 nebius per-source
numbers are hereby flagged as computed on degenerate events. v006's corpus-
wide conclusions (swegym-dominated, negative) are unaffected.

**SWE-smith caveat:** the 0.65-confidence gate rejects zero-signal failures
(1,292 rows), so its admitted failures skew error-rich (37.8% episode
positives); per-source reporting carries this.

## 4. Prediction points and schemas

- **R0** — window closes at the failure event: 44 features (`v007_r0@1` =
  v006 family at the cut + v005-prefix family sans dataset_id + 5 episode-
  positional features).
- **R1** — window closes at the first post-failure action plus its immediate
  result observation: 54 features (`v007_r1@1` = R0 + 10 recovery-attempt
  features, e.g. attempt_repeats_prior_action, attempt_family_change,
  attempt_result_is_error, attempt_result_same_hash_as_failure).
- Ablation control: `v005_minimal_recovery@1` (7 features).
- R0 and R1 reported separately throughout; never pooled.

## 5. Results (round 2 = reported run; identical episodes/partitions/weights)

Episode-level test ROC-AUC (primary identity variant; n = 5,769 test rows per
cell; independently recomputed from raw predictions by both the lead agent and
the critic):

| Point | Arm | with identity | without identity |
|---|---|---|---|
| R0 | R_LR (v007_r0) | **0.7578** | 0.7567 |
| R0 | R_LGBM | 0.7557 | 0.7494 |
| R0 | R_LR @ v005_minimal | 0.7520 | 0.7414 |
| R1 | R_LR (v007_r1) | **0.7658** | 0.7643 |
| R1 | R_LGBM | 0.7594 | 0.7549 |
| R1 | R_LR @ v005_minimal | 0.7529 | 0.7409 |

Per-source (with identity): R1 R_LR — nebius 0.6547 / swe_smith 0.7078 /
swegym 0.6616; R1 R_LGBM — 0.6424 / 0.6950 / 0.7271. Macro-source sits well
below pooled (e.g. R1 LR macro ≈ 0.6747 vs pooled 0.7658): pooled numbers
overstate per-source generalization.

### Mechanical acceptance verdicts (frozen criteria)

- **PRIMARY (LightGBM > LogisticRegression by ≥ +0.02): NOT EARNED at both
  points — negative** (LGBM−LR: R0 −0.0021, R1 −0.0064; direction 1/3
  sources). The preregistered falsifier "R_LGBM ≤ R_LR at both points" is
  realized. v006's failure-adjacent LGBM advantage did not transfer to
  episode-level recovery prediction.
- **SECONDARY (v007 representation > v005-minimal at the same estimator):
  NOT EARNED** — R1 delta +0.0129 with direction 3/3 (positive in all three
  sources) but below the +0.02 bar; R0 +0.0058 (direction 1/3).
- Identity removal changes nothing material (±0.002); dataset_id tops LGBM
  gain importance yet its removal is inert.

### Round-1 → Round-2 (Amendment-1) honesty record

Round 1 stratified the holdout on group_label only; the draw put all 11
swegym groups in train, producing a test set with zero swegym rows and a
spuriously optimistic secondary verdict ("EARNED at R1, +0.0227"). Per the
correction protocol: round-1 artifacts preserved at
`runs/v007-recovery/round1-stratum-defect/`; prereg Amendment-1 recorded
(strata = (dataset, group_label); no endpoint/model/metric change); round 2
re-ran everything with source-representative test cells and is the reported
run. The round-1 "earned" did not survive.

## 6. Calibration, generalization, importance, examples

- **Calibration:** 8/12 cells triggered OOF-isotonic (all LR cells, OOF ECE
  0.206–0.229; LGBM 0.021–0.025, never triggered). Isotonic improved test
  Brier in 8/8 triggered cells (LR ≈ 0.21 → 0.145–0.153; ECE → 0.022–0.028),
  fit on train out-of-fold predictions only. Calibration is required for
  deployment-grade probabilities; LGBM is natively calibrated here.
- **LOSO** (train-without-source, no re-tuning): nebius 0.652–0.677,
  swe_smith 0.562–0.579, swegym 0.469–0.589 for v007 schemas vs 0.599/0.601
  for the 7-feature ablation — the v007 representation transfers worst
  exactly where LGBM looked best (swegym). Cross-source generalization is
  the weakest link.
- **Parent-aggregated check:** consistently BELOW episode-level (−0.021 to
  −0.037) — no episode-multiplicity inflation; the conservative headline
  stands.
- **Importance:** LGBM gain — dataset_id, observation_novelty_rate,
  tool_switch_rate, action_observation_ratio, n_events; LR |std-coef| —
  payment_actual_total, fail_event_index, n_events, error_count,
  recovery_attempt_count.
- **Representative examples** (artifacts: `representative_examples.json`):
  e.g. a nebius episode at event 256 of a 257-event trajectory with 7 prior
  errors — p(recovery) ≈ 8×10⁻⁶, correct; correctly-recovered episodes show
  early cut positions with low prior-episode counts and high observation
  novelty.

## 7. Leakage audit (independent critic: VERDICT CONFIRM, zero blockers)

Full report: `.agents/reports/v007-critique.md`. Reproduced exactly by the
critic and the lead agent: all headline and per-source numbers, bucket
partition (sums to 37,426), split composition, Brier/ECE to 6 decimals.

- **MAJOR-1 (verified first-hand; verdict-immaterial):** the v005-prefix
  family computes `elapsed = n_context_events + k` using the FULL-trajectory
  context count. The v006 "context-first" assumption holds for nebius (0/4,554
  parents violate) but fails for swe_smith (1,271/3,708; up to 98 future
  messages) and swegym (918/1,574; up to 20), leaking post-cut information
  into 5 features (payment_predicted_total, payment_error, horizon_delta,
  risk_estimate, avg_actions_per_step). Quantified impact: refitting without
  them moves test AUC by +0.0003 (R0) / +0.0009 (R1) — every frozen verdict
  stays negative, and the primary comparison is same-feature symmetric.
  Inherited from v006's prefix projection (v006 artifacts untouched; flagged).
  A correction slice is required before any future re-freeze.
- Verified clean: no train/test group overlap; 30/30 independent future-event
  mutation checks bit-identical; weights fit-only; calibration never
  test-fit; label-side fields structurally excluded; nebius terminal
  `eval_logs` never reaches R0/R1 features (event-derived error features
  only).
- MINOR: results-report LOSO nebius range transcribed as 0.652–0.680 vs
  actual 0.652–0.677 (corrected here).

## 8. Tests executed

- v007 chain: 115 experiment-chain tests (episodes, features, runner teeth:
  grouping refusal, label whitelist, single-group stratum assignment,
  weights, calibration trigger, determinism, acceptance-rule micro-fixtures)
  + 105 earlier focused tests.
- Full suite: **1,039 passed, 2 skipped, 0 failed**; CLI validate gate: pass;
  docs gate: 18 passed. (Two timestamp-regenerated test fixtures restored
  after suite runs; `just context-check` remains unexecutable — no justfile
  exists, recorded debt.)

## 9. Runtime posture (no deployment)

Nothing was deployed. The existing runtime is unchanged and remains
authoritative over any advisory signal. The intended future control surface —
normal execution → failure observed → recovery predictor → P(recovery) as
advisory evidence to the controller (continue / change strategy / escalate /
stop spending) — is a design sketch only; implementing those policy decisions
is out of scope until a recovery signal earns trust. Deployment-grade use
would additionally require the MAJOR-1 correction, calibration wiring
(LR) or native-calibrated estimator (LGBM), and a local-harness validation
loop, none of which exist today.

## 10. Unresolved issues

1. The v005-prefix context-total leak (MAJOR-1) — correction slice pending
   before any re-freeze; inherited by v006's prefix projection (recorded,
   untouched).
2. Cross-source generalization: macro ≈ 0.67 vs pooled ≈ 0.77; swegym LOSO
   below chance for the full representation. Domain-transfer claims are
   unsupported.
3. SWE-smith gate-selection bias (error-rich failures over-represented).
4. swegym's 11 repositories make its test cells small (2,156 rows, 3 groups);
   source-level conclusions there are correspondingly coarse.
5. LR does not converge within the frozen max_iter=1000 at real scale
   (frozen spec kept; deterministic).
6. `just context-check` referenced by AGENTS.md but no justfile exists
   (pre-existing debt).

## 11. Smallest next move

Execute the **v005-prefix context-total correction slice** (prefix-scoped
context counts in the shared feature family), then re-run this exact frozen
matrix once — cheap, deterministic, and it removes the only known defect
between the current result and a fully clean recovery record. The R1
representation direction (3/3 sources positive) is the only thread worth
re-preregistering afterwards, and only if conditional recovery prediction
matters operationally; otherwise accept this negative settlement and keep
deterministic governance as the sole authority.

## Artifacts index

- Plan: `.agents/plans/godspeed-agent-v007-recovery-prediction.yaml`
- Preregistration (+ Amendment-1): `.agents/reports/v007-experiment-preregistration.yaml`
- Dataset research: `.agents/reports/v007-dataset-research.md`
- Experiment results (round 2 + superseded round 1): `.agents/reports/v007-experiment-results.md`
- Critique: `.agents/reports/v007-critique.md`
- Artifacts: `data/settlement_datasets/runs/v007-recovery/` (+ `round1-stratum-defect/`)
- Code: `scripts/settlement_datasets/{v007_recovery,run_v007_experiments,swe_smith_adapter}.py`,
  nebius adapter text-first fix, `configs/settlement_datasets/v007_{episodes,corpus}.yaml`
- Episode/corpus tables (local-only): `data/settlement_datasets/corpora/v007-*/`
