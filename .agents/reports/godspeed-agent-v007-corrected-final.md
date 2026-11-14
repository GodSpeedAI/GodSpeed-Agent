# GodSpeed-Agent v007 Corrected Re-Run — Final Report (Correction Slice)

Date: 2026-09-15. Plan: `.agents/plans/godspeed-agent-v007-prefix-correction.yaml`.
Scope: remove the one known leakage defect (v007 critique MAJOR-1), rerun the
already-frozen v007 recovery experiment unchanged, verify independently,
determine whether the v007 conclusions survive. No runtime deployment.

## Classification

```text
SETTLED — corrected evidence confirms the existing v007 conclusion
```

Every round-2 verdict stands under the corrected features. The correction
moved the affected headline cells by −0.0009 to −0.0032 (leak removal
slightly deflated the v007-schema cells, exactly as the audit predicted),
the minimal-recovery control cells are byte-identical, and the R1
representation direction remains positive in all three sources.

## 1. Exact bug

`v005_prefix_compatible_features` computed
`elapsed_raw = parent["n_context_events"] + k` — the FULL trajectory's
context count — so prefix-time features could include future context for
sources where context messages interleave with events. Measured exposure:
swe_smith 1,271/3,708 parents (up to 98 future messages), swegym 918/1,574
(up to 20), nebius 0/4,554 (clean). Affected features:
`payment_predicted_total`, `payment_error`, `horizon_delta`,
`risk_estimate`, `avg_actions_per_step`.

## 2. Exact correction

- Adapters gained `context_positions(raw)` (swegym/nebius/swe_smith
  overrides matching each adapter's action/observation role sets; base-class
  default `[]` with honest `context_scoped=false` marking for unadapted
  sources).
- Corpus events gained per-event `ctx` = number of context messages strictly
  below the event's message index. The parent content-hash excludes `ctx`,
  so parent identity is unchanged. Corrected corpus rebuilt deterministically
  at the SAME revisions (baf3a4e4 / 68195a14 / 08e109b4) into
  `v007c-trajectories`; `v007-trajectories` preserved. Parity verified: all
  9,836 parents identical except the added `ctx`; `trailing_context` = 0
  everywhere.
- `elapsed_raw = events[k-1].ctx + k` replaces the full-count rule;
  schema tag `v005_prefix_compatible` bumped `@1 → @2`;
  `v005_full_semantics@1` (verbatim counts block — full-trajectory H
  semantics) and `v006@1` untouched. Prereg Amendment-2 committed (fc3f984)
  before the rerun; every frozen cell reaffirmed.

## 3. Regression tests (leak cannot silently return)

Truncation equivalence on interleaved-context fixtures for ALL THREE
datasets (features at k from the full raw row == features from the raw row
truncated at the cut, all 11 features exact, cuts before and after
mid-trajectory context), future-append invariance, the five affected
features' ctx-scoped values, unaffected-feature stability, full-semantics
verbatim-counts assertion, unscoped-fallback behavior. Teeth check:
temporarily reinstating the old formula fails 16 regression tests.
Focused gates: 237 passed; full suite 1,062 passed / 2 skipped.

## 4. Dataset/split confirmation

Revisions unchanged (no upstream force). Split = Amendment-1 strata
`(dataset, group_label)`, seed 42; the critic recomputed the split from the
episode table and matched the predictions exactly (428 test groups,
disjoint, all per-source test cells non-empty). Episode construction parity:
74,852 rows with identical keys/cuts/labels; exactly 6,580 rows differ, in
exactly the 5 corrected features (predicted_total strictly decreased in all —
the leak had been inflating elapsed).

## 5. Corrected results (round 3) and old-vs-new deltas

Episode-level test ROC-AUC, with identity (n = 5,769 test rows per cell):

| Cell | Round 2 | Round 3 (corrected) | Delta |
|---|---|---|---|
| R0 LR v007_r0 | 0.7578 | **0.7566** | −0.0012 |
| R0 LGBM v007_r0 | 0.7557 | 0.7525 | −0.0032 |
| R0 LR minimal | 0.7520 | 0.7520 | +0.0000 |
| R1 LR v007_r1 | 0.7658 | **0.7649** | −0.0009 |
| R1 LGBM v007_r1 | 0.7594 | 0.7581 | −0.0013 |
| R1 LR minimal | 0.7529 | 0.7529 | +0.0000 |

Without identity: R0 LR 0.7567 → 0.7558; R1 LR 0.7643 → 0.7636;
R1 LGBM 0.7549 → 0.7536; minimal cells unchanged. The four minimal cells are
metric-identical across rounds — a clean internal control proving the
correction moved only the prefix-family inputs.

## 6. Answers to the six primary questions

1. **Same recovery signal?** Yes. All v007-schema cells moved −0.0009 to
   −0.0032; ranking quality is effectively unchanged.
2. **LightGBM beats LogisticRegression by the threshold?** No — negative at
   both points (LGBM−LR: R0 −0.0041, R1 −0.0069; per-source direction 1/3).
   Falsifier #1 remains realized.
3. **Representation beats minimal by the threshold?** No — attention cell
   R1 v007-LR minus minimal-LR: **+0.0129 → +0.0120**, still below +0.02.
4. **Does the R1 positive direction across sources survive?** Yes — 3/3:
   v007 {nebius 0.6545, swe_smith 0.7079, swegym 0.6481} vs minimal
   {0.6534, 0.6460, 0.6337}. (swegym's v007 cell absorbed the largest
   correction, 0.6616 → 0.6481, and remains above its minimal control.)
5. **Cross-source generalization still the limiting factor?** Yes — macro
   0.6701 vs pooled 0.7649 (R1 LR); LOSO to swegym remains weakest.
6. **Material change to any prior verdict?** No. PRIMARY NOT EARNED,
   SECONDARY NOT EARNED, classification PARTIAL — all confirmed under clean
   features. If anything, the correction slightly strengthened the negative
   estimator verdict (the leak had mildly inflated LGBM more than LR).

## 7. Per-source, LOSO, calibration

- Per-source (R1, LR, with identity, round 3): nebius 0.6547 → 0.6545,
  swe_smith 0.7078 → 0.7079, swegym 0.6616 → 0.6481.
- LOSO (no re-tuning): nebius 0.652–0.677, swe_smith 0.562–0.579, swegym
  0.469–0.589 for v007 schemas vs 0.599/0.601 minimal — unchanged picture.
- Calibration: LR cells trigger OOF-isotonic (OOF ECE 0.21–0.23), Brier
  ≈ 0.21 → ≈ 0.15; LGBM never triggers. Isolation verified (never test-fit).
- Parent-aggregated checks remain below episode-level (conservative).

## 8. Independent verification

Fresh critic (`.agents/reports/v007c-critique.md`): **VERDICT: CONFIRM,
zero blockers, zero majors.** It independently (a) proved leak removal with
20/20 interleaved-parent power (old formula gives different values in 10/10
swe_smith and 10/10 swegym parents; new features equal `ctx + k`
recomputation), (b) 18/18 mutation-invariance checks, (c) reproduced every
headline to 4dp from raw predictions, (d) re-derived the split, calibration
isolation, and weights, (e) re-ran the ENTIRE frozen matrix itself and
reproduced `results.json` byte-identically (md5 `b06ee86b…`) — determinism
is independently reproduced fact, and (f) verified verdict fidelity against
the frozen criteria. The lead agent independently verified the feature diff,
corpus/episode parity, and all headline/per-source numbers before and after
the critic. One MINOR (uncommitted artifacts at audit time — resolved by the
C4 commit) and five NOTEs (nebius correction is a no-op there; swegym test
fraction 27.3% from single-group strata; documentation wording; the
`v007_r0@1` composite tag pins the embedded `@2` prefix family per
Amendment-2).

## 9. Prior conclusions — changed?

No. Round-2 conclusions survive cleanly. The one quantitative shift: the
attention-cell representation delta narrowed from +0.0129 to +0.0120
(still 3/3 positive, still sub-threshold). The recovery predictor's evidence
status is unchanged: PARTIAL under the v007 classification — a real,
calibratable signal at both prediction points, with no preregistered gate
met and cross-source generalization unresolved.

## 10. Smallest next move

Unchanged from the v007 final report, now on clean evidence: the R1
representation direction (3/3 sources, +0.0120) is the only thread worth
re-preregistering — and only if conditional recovery prediction matters
operationally. Otherwise accept the settled negative and keep deterministic
governance as the sole authority.

## Artifacts

- Correction plan: `.agents/plans/godspeed-agent-v007-prefix-correction.yaml`
- Prereg Amendment-2: `.agents/reports/v007-experiment-preregistration.yaml`
- Critique: `.agents/reports/v007c-critique.md`
- Round-3 artifacts: `data/settlement_datasets/runs/v007-recovery/` (results,
  predictions, manifest recording v007c inputs; determinism: two lead-agent
  runs + one critic run, byte-identical)
- Preserved history: `round1-stratum-defect/`, `round2-pre-correction/`
- Corrected corpus/episodes (local-only): `corpora/v007c-*`
