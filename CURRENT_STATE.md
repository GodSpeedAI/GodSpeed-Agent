# Current State of the Godspeed Agent Harness Project

This file is the low-payment entrypoint for agents. It should expose the current
horizon, not the full developmental memory. Read `state/current_state.json`
first when a machine-readable view is better, and query the JSONL ledgers only
when the active desired direction requires deeper history.

## Last Settlement

- Date: 2026-09-15
- Summary: v007 correction slice settled (SETTLED - corrected evidence confirms
  the existing v007 conclusion). Removed the v005-prefix context-total leak
  (per-event ctx counts; prefix elapsed = ctx + k; schema @2; truncation-
  equivalence regression tests on all three datasets), rebuilt the corpus at
  the same revisions, and reran the frozen recovery matrix cleanly (round 3).
  Deltas vs round 2: -0.0009..-0.0032 on v007-schema cells; minimal-recovery
  control cells byte-identical. All round-2 verdicts stand: LightGBM does not
  beat LogisticRegression, the representation stays below the +0.02 bar
  (R1 +0.0120, direction 3/3), cross-source generalization remains the limit.
  Independent audit: CONFIRM; critic reproduced the run byte-identically.
- Settlement evidence: 1,062 tests pass / 2 skipped; validate pass; corrected
  report `.agents/reports/godspeed-agent-v007-corrected-final.md`.
- Proof classification: `external-proxy-calibration` (no local claims).
- Known limit: v006 prefix projection inherited this leak (v006 artifacts
  untouched; quantified immaterial there).
  Next move: none required; optional re-preregistration of the R1
  representation direction only if operationally wanted.

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
