---
harness:
  mode: local
  primary_metric: horizon_expansion
  allow_outcome_language: true
  outcome_as_terminal: false
storage:
  root: .godspeed-harness
  format: jsonl
  retain_raw_events: true
  redact_secrets: true
  evolution_enabled: false
  preferred_database: sqlite
  vector_index: ruvector
  min_settlements_for_upgrade: 1000
computation:
  engine: python
  use_pandas: true
  use_numpy: true
  use_sklearn: auto
  model_provider: heuristic
  ml_event_threshold: 200
  simulation_threshold: 1000
experiments:
  enabled: true
  root: .godspeed-harness/experiments
  use_git_worktrees: true
  max_parallel_experiments: 1
  cleanup_failed_experiments: false
absorption:
  enabled: true
  ingest_root: ingest/
  require_license_check: true
  require_pathway: true
  require_settlement_plan: true
safety:
  block_unaffordable_actions: false
  warn_unaffordable_actions: true
  max_payment_burden: 100
  require_human_review_for_absorption: true
  require_human_review_for_disintegration: true
---

# Godspeed Harness Policy

This repository uses local-first developmental memory. Outcomes are accepted as desired-direction language, but outcome completion is not terminal by default. The primary metric is horizon expansion through the next affordable affordance.

Predictive extensions remain suggestion-only and activate only after the configured settlement thresholds are met.

## Settlement and Evidence Authority

- `record-settlement` requires a persisted executable affordance (`current_status == 'affordance'`). Unknown, potential, or possibility identifiers are rejected with a typed `settlement_requires_executable_affordance` error before any settlement-derived state is written.
- External execution evidence (`EvidenceRecorded`) is ingested as `provisional` only: complete non-empty evidence is never settlement, regardless of whether expected and observed results match. Match/mismatch is preserved as an observed proof fact. Missing required evidence is rejected with `incomplete_execution_evidence`.
- Execution evidence writes only the canonical `execution_evidence` ledger and never `settlements`, `capabilities`, `trajectories`, or `repetition_schedules`. A later `record-settlement()` with observable before/after consequence is the only promotion path. Re-delivery of the same `event_id` is idempotent.
- Learning proposals persist through the single `LedgerStore` authority (`agentic_capability_loop` ledger). The adapter writes outbound envelopes to one transport outbox; `settlements`, `capabilities`, and `repetition_schedules` remain the canonical runtime authority.

## Ownership Boundary

Settlement, capability, developmental memory, learning proposals, MCP, and read-only evidence ingestion are owned by GodSpeed-Agent. Software hooks and traces belong to SWE_SEED (F-08): GodSpeed-Agent registers no host hooks and runs no live trace recorder.

If richer retrieval becomes necessary after enough settlement history exists, prefer SQLite first and add RuVector for local vector similarity. Treat SurrealDB as an explicitly justified alternative for graph-heavy or multi-actor cases rather than the default next step.
