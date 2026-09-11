# Current State of the Godspeed Agent Harness Project

This file is the low-payment entrypoint for agents. It should expose the current
horizon, not the full developmental memory. Read `state/current_state.json`
first when a machine-readable view is better, and query the JSONL ledgers only
when the active desired direction requires deeper history.

## Last Settlement

- Date: 2026-09-09
- Summary: Completed hf-calibration-005-features with 5 richer pre-outcome features
  (tool_diversity_count, error_recovery_ratio, action_observation_ratio,
  avg_actions_per_step, dataset_id). Processed 6497 usable settlements across all
  3 external datasets (swegym_openhands: 1892, agenttrove: 51, nebius_swe_agent: 4554).
  Held-out sklearn evaluation achieved ROC-AUC 0.8266, balanced accuracy 0.7428,
  and F1 0.5208, outperforming majority and success-rate baselines. Zero leakage
  detected. Increased solver max_iter to 1000 for clean lbfgs convergence.
- Settlement evidence: 45 tests pass, hf-calibration-005-features exits 0.
- Proof classification: `external-proxy-calibration`.
- Known limit: External proxy data is for calibration only, not local settlement proof.
  Next move: calibrate cognitive model controller weights against local harness execution traces.

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
