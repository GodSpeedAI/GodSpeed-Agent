# Storage Evolution Decision Record

## Decision

Keep JSONL ledgers as the active truth surface for the Godspeed Agent Harness. Do not migrate the runtime to a database merely because predictive or ML features exist.

## Trigger For Reconsideration

Reconsider storage only when settlement history, retrieval needs, or local ML memory workflows fail settlement with the current JSONL plus index approach.

## Approved Evolution Path

1. SQLite is the default next step for structured local query and deterministic deployment.
2. RuVector is the default vector layer once local ML retrieval needs similarity search.
3. SurrealDB is allowed only by explicit justification when graph-heavy or multi-actor needs clearly exceed SQLite.

## Non-Negotiables

- Payment and settlement ledgers remain the truth surface.
- Any richer store must preserve local-first operation.
- Human-inspectable export must remain available.
- Predictive or simulation features do not justify replacing settlement evidence.
