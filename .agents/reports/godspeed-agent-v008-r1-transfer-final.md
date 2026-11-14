# GodSpeed-Agent v008 R1 Transfer — Final Report

Date: 2026-09-15. Plan: `.agents/plans/godspeed-agent-v008-r1-transfer.yaml`.
Preregistration frozen at commit `b61edc3` before any held-out-source result was
examined. No runtime deployment.

## Classification

```text
SETTLED — transferable R1 recovery representation earned
```

Mechanically, from the frozen acceptance rule: macro held-out T−M = **+0.0357**
(≥ +0.02), T ≥ M in **3/3** held-out environments, worst cell +0.0223 (no
degradation), parent-only sensitivity preserves direction (+0.0142), primary
arms identity-free. Scope statements below are part of the honest result: the
**full** corrected representation F transfers best of all (+0.0589 over M), and
the frozen secondary hypothesis (T > F) is **refuted**.

## 1. Corrected-v007 evidence carried forward

R1 pooled LR 0.7649 (F) vs 0.7529 (M), delta +0.0120, direction 3/3; leak
corrected (Amendment-2 ctx accounting); audit clean; open weakness =
cross-source generalization. All carried into v008 unchanged: same R1
definition, same target, same corrected prefix/context accounting.

## 2. Exact R1 definition (unchanged)

meaningful failure → first recovery attempt → its immediate observable result
→ prediction point. Target: `recovery_success = 1` iff meaningful failure +
observed escape + verified terminal settlement (v007 definition, untouched).

## 3. Admitted sources and revisions (normalized corpus)

| Source | Revision | License | R1 episodes |
|---|---|---|---|
| SWE-Gym/OpenHands-Sampled-Trajectories (`train.raw` ≤3000) | `baf3a4e4…` | ambiguous (card silent; companion Apache-2.0) — local-only | 7,037 |
| nebius/SWE-agent-trajectories (`train` ≤5000) | `68195a14…` | cc-by-4.0 | 17,642 |
| SWE-bench/SWE-smith-trajectories (`tool` ≤5000) | `08e109b4…` | mit | 12,797 |

Total 37,476 R1 rows / 8,028 positives. Semantic normalizations applied before
the experiment (recorded as V1c, corpus `v008-*`): **N2** marker gating by
event kind, not role string (nebius actions use role `ai`; its cmd_family/
mentions_bash were 100% degenerate before); **N1** swegym tool_calls rendering
(empty-content actions 48% → 0%); **N3** nebius pre-first-action user entries
reclassified as context (leading error runs 4,554 → 183 genuine;
`has_failure ≡ 1` artifact removed).

## 4. Semantic adapter audit (V1b; `.agents/reports/v008-adapter-semantics.md`)

54 features audited: 19 SHARED / 21 NORMALIZABLE / 14 SOURCE-SPECIFIC
as-encoded. After N1–N3, the formerly degenerate families behave comparably
(3 of 4 cmd_family features direction-consistent across all three sources;
hash-identity "signals" shown to be empty-content artifacts). Every
T-selected feature's per-source fields, transformation, meaning, and
missing/default behavior are documented in the audit report; semantically
divergent features were excluded from T by the preregistered gates.

## 5. Representations

- **M** (minimal): `v005_minimal_recovery` sans dataset_id — 6 features.
- **F** (full): corrected `v007_r1@1` — 54 features (identity-free).
- **T** (transfer): derived per held-out cell from that cell's two training
  sources ONLY by the frozen mechanical rule. Selected sets: 20 features per
  cell, **16 common to all three cells** (pairwise Jaccard 0.74–0.82) — the
  transferable core is dominated by failure-burden depth (error_count,
  distinct_error_count, fail_event_index, n_events/actions/observations),
  recovery-attempt observables (attempt_result_same_hash_as_failure,
  has_attempt_result, new_obs_between_failure_and_attempt), observation
  novelty, and payment_actual_total. `tool_diversity_count` was excluded by
  the identifiability gate at AUC **1.000** — a perfect environment
  identifier, exactly the failure mode the gate exists for.

## 6. Feature-selection procedure (leakage-safe)

Per held-out cell, GroupKFold(5) over the training pool's split_group:
per-fold weighted-LR coefficient signs; per-source univariate direction
(sign must agree across BOTH training sources in ≥4/5 folds); coefficient
sign consistency ≥4/5; worst-case one-vs-rest source-identifiability AUC
< 0.85 (measured break: six features ≥0.857, next 0.673); non-constant in
both sources; size clamps [5, 20] by stability score. The held-out source's
rows (features or labels) never enter selection — the critic re-derived the
swegym-cell gate from scratch and matched `t_selection.json` exactly.

## 7. Weighting, preprocessing, estimator, calibration

Primary weighting = parent-balanced × source-balanced (fit only);
parent-only sensitivity preregistered. StandardScaler fit on training-pool
rows only. LogisticRegression(class_weight='balanced', max_iter=1000,
lbfgs, random_state=42), C ∈ {0.01, 0.1, 1} tuned inside the training pool.
Calibration: OOF isotonic iff OOF ECE > 0.05, never fit on the held-out
source. Trigger fired 21/21 (MINOR: no selectivity); isotonic improved
nebius/swegym cells (T: Brier 0.234 → 0.136) but **worsened every swe_smith
arm** (T: 0.234 → 0.295) — the pool's 12.9% positive rate under-corrects
swe_smith's 37.8% base rate: a label-prior shift, honestly reported; AUCs
(raw) are unaffected.

## 8. Held-out-source results (primary; raw-probability ROC-AUC)

| Held-out env | M | F | T | T−M |
|---|---|---|---|---|
| nebius_swe_agent | 0.6512 | 0.7137 | 0.6735 | +0.0223 |
| swe_smith | 0.5777 | 0.6218 | 0.6008 | +0.0231 |
| swegym_openhands | 0.5749 | 0.6450 | 0.6367 | +0.0618 |
| **macro** | **0.6013** | **0.6602** | **0.6370** | **+0.0357** |

- **Primary acceptance: EARNED** (all five frozen conditions).
- **Secondary T-vs-F: REFUTED** — F beats T in 3/3 cells (macro −0.0231).
  Removing features did not improve transfer; the full corrected
  representation is the best transferrer. F−M = +0.0589 macro, 3/3 cells.
- Pooled context only: M 0.5523 / F 0.5686 / T 0.5886 — held-out macro is
  the headline, per the prereg.
- Identity diagnostics: F+id macro 0.6628; on the nebius cell identity arms
  degenerate to near-constant predictions (balanced acc 0.50) — diagnostics
  only, never adopted.
- Parent-only sensitivity: M 0.6161 / T 0.6303 (+0.0142, direction holds).

## 9. Calibration summary

Per held-out cell: ECE/Brier before-after isotonic reported for all arms
(`calibration_summary.json`). Correctable in 2/3 environments; the swe_smith
failure is base-rate shift, not ranking failure.

## 10. Per-source error analysis (T arm; `error_analysis.json`)

- **nebius**: residuals are genuine-dynamics cases (no scaling flags);
  correct quadrants show pool-vs-source z divergence 0.80–0.93; label-prior
  gap 0.141 vs 0.279.
- **swe_smith**: dominant hypothesis **label semantics** on error quadrants
  (held-out positive rate 0.378 vs pool 0.129) — consistent with the
  calibration degradation; the F4 storage-format selection effect (34.3% of
  parents, all successes, yield no episodes) plausibly contributes.
- **swegym**: dominant hypothesis **feature scaling** (z divergence
  0.73–0.93; FP exemplar new_obs_between_failure_and_attempt z_pool 38.8 vs
  z_source 19.4) — wide source distributions; the scaler helped and more is
  available.
- Adapter-semantics and environment-policy causes were not mechanically
  separable from this evidence surface and are recorded as the residual
  category (critic MINOR-1: taxonomy narrowed from six causes to four,
  disclosed in the artifact).

## 11. Source-identity diagnostics

Primary arms contain no source identity (whitelist-guarded, test-proven).
Identity arms are diagnostics only; where identity dominates (nebius), the
diagnostic model collapses — behavior, not identity, carries the transfer.

## 12. Optional fourth source

`nebius/SWE-rebench-openhands-trajectories` (sha `35455389…`, cc-by-4.0,
67,074 trajectories, execution-derived `resolved`): CONDITIONAL-ADMIT,
**deferred** — admission requires its own adapter, resolved-mechanism
verification, and role-semantics precautions; not cheap; three environments
sufficed for the frozen design. Four other candidates REJECTed with evidence
(`.agents/reports/v008-fourth-source.md`).

## 13. Independent critic results

`.agents/reports/v008-critique.md`: **VERDICT: CONFIRM** — zero blockers or
majors. The critic (a) re-derived the T gate for the swegym cell from scratch
and matched the artifact exactly (37 gates pre-trim, identical 20-feature
set), (b) confirmed gate power with a planted perfect source-separator
(excluded at AUC 1.0000), (c) reproduced all nine primary per-cell AUCs and
the mechanical acceptance verdict from raw predictions, (d) re-ran the ENTIRE
matrix from scratch with all seven artifacts byte-identical, (e) verified
source/selection/scaling/calibration isolation, weights, prereg sha, episode
parity, and v006/v007 preservation. Two MINORs recorded (taxonomy narrowing
6→4, disclosed; non-selective calibration trigger). The lead agent
independently reproduced the headline table and T-set provenance before the
critic ran. Determinism: three independent byte-identical executions total.

## 14. Was transfer earned?

Yes — under the frozen rule, and with an important scope statement:

- A **transferable R1 recovery representation exists**: both T (+0.0357) and
  F (+0.0589) beat the minimal baseline on every held-out environment, with
  no degradation anywhere and no identity dependence. Recovery behavior —
  failure burden, attempt observables, observation freshness — transfers
  across three different agent harnesses.
- The specific subset hypothesis (T > F) is **refuted**: the gate-derived
  subset transfers worse than the full representation. The 16-feature common
  core is descriptive evidence about *which* signals transfer, not a
  better model.
- Residual weaknesses, documented: swe_smith base-rate calibration failure
  (label-prior shift), swegym scale divergence (partially addressed by the
  scaler), the swe_smith F4 selection effect, and coarse 3-environment
  macro evidence.

## 15. Smallest next move

Fix the **swe_smith F4 storage-format artifact** (N4 dual-format ingestion —
1,271 success-labeled parents currently yield no episodes), then re-check the
swe_smith cell's calibration under the corrected base rate. This is the
cheapest known-defect fix that hardens the weakest cell. The deferred
SWE-rebench source (a genuinely new harness) is the natural follow-up after
that to test transfer on a fourth environment.

## Artifacts

- Plan: `.agents/plans/godspeed-agent-v008-r1-transfer.yaml`
- Prereg: `.agents/reports/v008-transfer-preregistration.yaml` (b61edc3)
- Audits: `.agents/reports/v008-feature-stability.md`,
  `.agents/reports/v008-adapter-semantics.md`,
  `.agents/reports/v008-fourth-source.md`
- Critique: `.agents/reports/v008-critique.md`
- Artifacts: `data/settlement_datasets/runs/v008-transfer/` (manifest with
  prereg sha + md5s, results, predictions 262,332 rows, T-selection tables,
  calibration, error analysis)
- Code: `scripts/settlement_datasets/run_v008_transfer.py`,
  `tests/test_v008_transfer.py`; normalization diff in the corpus builder +
  three adapters (V1c)
- Normalized corpus/episodes (local-only): `corpora/v008-*`
