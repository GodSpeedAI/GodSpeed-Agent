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

If richer retrieval becomes necessary after enough settlement history exists, prefer SQLite first and add RuVector for local vector similarity. Treat SurrealDB as an explicitly justified alternative for graph-heavy or multi-actor cases rather than the default next step.
