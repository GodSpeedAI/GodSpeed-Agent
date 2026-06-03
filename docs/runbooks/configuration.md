# Configuration Runbook

## Purpose

Configure local policy without breaking the horizon-centric invariants.

## Source

Configuration is read from `HARNESS.md` unless an explicit path is supplied by a caller. YAML front matter controls runtime behavior; markdown body documents local doctrine.

## Required Invariants

- `primary_metric` should remain `horizon_expansion`.
- `outcome_as_terminal` must stay false unless the operator explicitly documents why terminal outcome behavior is needed.
- Storage root should remain inside the workspace.
- Absorption candidates should use the configured `absorption.ingest_root`; see `docs/runbooks/absorption-ingest.md`.
- Human review should remain enabled for absorption and positive disintegration in enterprise settings.
- `computation.model_provider` should point at a local, explainable provider unless an operator has approved a different adapter.
- `computation.ml_event_threshold` and `computation.simulation_threshold` should be adjusted in `HARNESS.md`, not hard-coded in scripts.
- `storage.format` should remain `jsonl` unless a separate storage-evolution decision has passed scrutiny.
- `storage.evolution_enabled` should remain false until settlement history justifies a richer retrieval layer.
- `storage.preferred_database` should default to SQLite first, with `vector_index: ruvector` once ML retrieval needs local vector similarity.
- SurrealDB should be treated as an explicitly justified alternative when graph-heavy or multi-actor needs clearly exceed SQLite.

## Validation

After editing `HARNESS.md`, run:

```bash
uv run pytest -q
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation
```

Treat provider changes and predictive threshold changes as governed `HARNESS.md` edits so validation can confirm the new operating contract.

Treat storage-evolution settings the same way. They do not authorize an immediate migration on their own; they only define the approved path once the current JSONL truth surface no longer satisfies retrieval or ML needs.

## Built-In Predictive Providers

### `heuristic` (default)

The default provider. Uses local heuristic scoring based on settlement count, payment burden, and risk. No external dependencies. Always available.

### `sklearn`

A built-in scikit-learn provider that uses logistic regression for settlement success prediction. This provider is:

- **Registered** in the provider registry but **dormant** below the configured `ml_event_threshold`.
- **Dependency-gated**: requires scikit-learn installed via `uv sync --extra ml`. If scikit-learn is not installed, the provider raises a clear error directing the operator to install the `ml` extra.
- **Threshold-gated**: `build_predictive_extension_plan` returns `stage: deterministic_only` below `ml_event_threshold` (default 200) and never calls the sklearn provider.
- **Advisory only**: ML predictions never override deterministic ranking, hard gates, governance, payment, settlement-access, risk, or debt gates.

To activate:

1. Install the `ml` extra: `uv sync --extra ml`
2. Set `computation.model_provider: sklearn` in `HARNESS.md` front matter.
3. Ensure settlement history exceeds `ml_event_threshold`.

The sklearn provider trains only from extracted calibration rows with sufficient usable data. If calibration rows are insufficient even though the event-count threshold passed, it returns empty predictions with an explanatory note instead of fabricating confidence.
