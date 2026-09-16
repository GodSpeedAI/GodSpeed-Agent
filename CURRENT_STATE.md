# Current State of the Godspeed Agent Harness Project

This file is the low-payment entrypoint for agents. It should expose the current
horizon, not the full developmental memory. Read `state/current_state.json`
first when a machine-readable view is better, and query the JSONL ledgers only
when the active desired direction requires deeper history.

## Last Settlement

- Date: 2026-09-15
- Summary: v008 R1-transfer plan settled (SETTLED - transferable R1 recovery
  representation earned). Leave-one-source-out with LR only, after semantic
  normalizations N1-N3 (nebius ai-role marker gating; swegym tool_calls
  rendering; nebius issue-text reclassification) and a frozen preregistration.
  Held-out macro ROC-AUC: minimal 0.6013, full v007 representation 0.6602,
  transfer subset 0.6370 - T earned the preregistered gate (+0.0357, 3/3
  environments, no degradation, identity-free), and the full corrected
  representation transfers best. Secondary T>F refuted. Independent audit:
  CONFIRM; three byte-identical executions. No runtime deployment.
- Settlement evidence: 1,099 tests pass / 2 skipped; validate pass; final
  report `.agents/reports/godspeed-agent-v008-r1-transfer-final.md`.
- Proof classification: `external-proxy-calibration` (no local claims).
- Known limit: swe_smith base-rate calibration failure (label-prior shift);
  F4 selection effect; 3-environment evidence only.
  Next move: N4 swe_smith dual-format ingestion fix + calibration re-check;
  SWE-rebench fourth environment as follow-up.

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
