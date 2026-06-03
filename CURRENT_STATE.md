# Current State of the Godspeed Agent Harness Project

This file is the low-payment entrypoint for agents. It should expose the current
horizon, not the full developmental memory. Read `state/current_state.json`
first when a machine-readable view is better, and query the JSONL ledgers only
when the active desired direction requires deeper history.

## Last Settlement

- Date: 2026-06-03
- Summary: Fixed calibration label leakage in `external_record_to_model_calibration`.
  `horizon_delta` now derives from pre-outcome proxy signals (inverse risk,
  payment efficiency) instead of `outcome.success`. Added leakage audit that
  flags features with >= 0.95 correlation to the label. Re-ran as
  hf-calibration-002: 500 usable settlements, 0 adapter errors, 0 leaked
  features. sklearn success_probability dropped from 0.8964 (leaked) to
  0.1687 (honest), vs deterministic baseline 0.106. sklearn is now meaningful
  but weak due to class imbalance (10.6% success).
- Settlement evidence: 533 tests pass, hf-calibration-002 exits 0, leakage
  audit clean, sklearn metrics valid.
- Proof classification: `external-proxy-calibration`.
- Known limit: class imbalance (10.6% success) makes sklearn predictions
  weak. Next move: include agenttrove and nebius_swe_agent datasets for
  better class balance, or apply stratified sampling.
- Known limit: class imbalance (10.6% success) and horizon_delta leakage
  mean sklearn predictions are not yet meaningful for affordance ranking.
  Next move: fix `external_record_to_model_calibration` to derive
  `horizon_delta` from payment/error signals rather than the success label,
  then re-evaluate sklearn.

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
