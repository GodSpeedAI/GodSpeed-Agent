# Current State of the Godspeed Agent Harness Project

This file is the low-payment entrypoint for agents. It should expose the current
horizon, not the full developmental memory. Read `state/current_state.json`
first when a machine-readable view is better, and query the JSONL ledgers only
when the active desired direction requires deeper history.

## Last Settlement

- Date: 2026-09-15
- Summary: v006 dual-model settlement classifier plan settled (PARTIAL).
  Implemented corrected ingestion (agenttrove HF streaming, nebius null-safety:
  441 crashes -> 0), a shared 1799-parent trajectory corpus (swegym 1574,
  nebius 225; agenttrove REJECTED at live revision — label columns null;
  Toucan-1.5M REJECTED — no verified outcome), three feature families
  (v005_full_semantics bit-exact vs H, v005_prefix_compatible, v006@1 with 29
  trajectory-state features), six causal prefix cuts, lightgbm 4.7.0 via uv,
  and a frozen-preregistration experiment matrix. No preregistered gain earned
  (representation -0.012, estimator +0.012, combined -0.010 macro-AUC vs the
  +0.02 bar); v006 helps only near the trajectory end. Independent audit:
  CONFIRM, zero blockers. Runtime default unchanged; historical v005 intact.
- Settlement evidence: 907 tests pass / 2 skipped; validate gate pass; final
  report `.agents/reports/godspeed-agent-v006-final.md`.
- Proof classification: `external-proxy-calibration` (unchanged; no local
  settlement claims made).
- Known limit: H's recorded 0.8266 is not comparable to current grouped-split
  numbers; swegym dataset license formally undetermined (corpus uncommitted).
  Next move: operator decision — re-preregister a late-cut-only v006 endpoint
  on a fresh corpus revision, or accept the negative settlement.

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
