# Current State of the Godspeed Agent Harness Project

This file is the low-payment entrypoint for agents. It should expose the current
horizon, not the full developmental memory. Read `state/current_state.json`
first when a machine-readable view is better, and query the JSONL ledgers only
when the active desired direction requires deeper history.

## Last Settlement

- Date: 2026-09-15
- Summary: v007 recovery-predictor plan settled (PARTIAL). Built failure-episode
  corpus from 3 admitted sources (37,426 episodes / 74,852 R0+R1 rows, 21.4%
  positive): swegym 1,574 parents, nebius 4,554 (REVIVED — v006's zero-error
  finding was an adapter text-vs-content field bug, fixed), swe_smith 3,708
  (newly admitted, MIT). Frozen preregistration executed twice (Amendment-1
  fixed a degenerate test draw; round-1 evidence preserved). Round-2 verdicts:
  PRIMARY NOT EARNED (LightGBM <= LogisticRegression at both points),
  SECONDARY NOT EARNED (representation +0.0129 at R1, direction 3/3, below the
  +0.02 bar). Signal exists (ROC-AUC 0.76/0.77 pooled; 0.63-0.73 per-source)
  but cross-source generalization is weak (macro ~0.67) and nothing was
  deployed. Independent audit: CONFIRM, zero blockers; one verdict-immaterial
  inherited leak flagged in the v005-prefix family (context-count assumption).
- Settlement evidence: 1,039 tests pass / 2 skipped; validate gate pass; final
  report `.agents/reports/godspeed-agent-v007-recovery-final.md`.
- Proof classification: `external-proxy-calibration` (no local settlement claims).
- Known limit: external proxy data only; v005-prefix context-total leak needs a
  correction slice before any future re-freeze.
  Next move: operator decision — context-total correction slice + one clean
  re-run, or accept the negative settlement.

## Active Desired Direction

Keep project state easy for agents to traverse without forcing the full
developmental history into the context window.

## Current Horizon

- `.github/copilot-instructions.md` exists and is an active project-specific
  context surface after `AGENTS.md`.
- `state/current_state.json` carries the latest machine-readable state.
- `state/milestones.jsonl` carries append-only settlement history.
- `state/lessons.jsonl`, `state/missing.jsonl`, and `state/decisions.jsonl`
  separate durable lessons, open gaps, and state-management decisions.

## Next Spendable Affordance

- For future milestones, update `state/current_state.json`, append one record to
  the relevant `state/*.jsonl` ledger, and keep this file compact.
- When deeper history is needed, query `state/milestones.jsonl` by date,
  artifact, status, or desired direction instead of reading the whole ledger.
- Continue using the harness in real agent work, collect real settlement
  history, and compare any future provider against the built-in heuristic
  adapter before promoting it beyond the config-controlled port.

## Still Missing

- No known gaps in the local-first enterprise hardening scope described by
  `docs/plans/2026-05-29-enterprise-hardening.md`.
- Future productization may add packaged distribution, hosted multi-user
  services, or richer ML once settlement history exists.

## Lessons To Preserve

- `CURRENT_STATE.md` should remain a compact horizon index, not the complete
  developmental memory.
- JSONL is the preferred append-only format for settlement history because each
  record is independently parseable and merge-friendly.
- `state/current_state.json` is the first read path for next steps, missing
  gaps, lessons learned, and the last settlement.
- Migrated history is preserved substrate, not proof of new capability.

## Detailed State Ledgers

- `state/current_state.json`: current snapshot for low-payment agent reads.
- `state/milestones.jsonl`: append-only settlement and milestone history.
- `state/lessons.jsonl`: durable lessons learned.
- `state/missing.jsonl`: current and historical missing gaps.
- `state/decisions.jsonl`: decisions about state-management structure.
