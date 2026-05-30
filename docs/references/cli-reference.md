# CLI Reference

## Purpose

This document explains the operator-facing CLI surfaces that turn the doctrine into local runtime actions.

## Deterministic Review Commands

### `compute-error`

Compares desired and observed state and returns `error_vector` plus `error_magnitude`.

Example:

```bash
uv run godspeed-nav compute-error \
  --desired '{"tests": 3}' \
  --observed '{"tests": 1}'
```

### `estimate-payment`

Computes `payment_burden`, `capacity_norm`, `spendability`, and `dominant_cost`.

### `rank-affordances`

Ranks candidate spendable transformations by expected expansion divided by cost and risk.

### `score-settlement`

Scores whether consequence actually settled from before/after state and evidence.

## Runtime Workflow Commands

Storage-backed commands (`start-direction`, `review-horizon`, `record-settlement`, `runtime-snapshot`, `developmental-report`, `predictive-extensions`, and `validate`) resolve `--storage-root` inside `--workspace-root`. The CLI rejects storage paths outside the workspace boundary.

### `start-direction`

Creates a desired direction and its initial horizon.

```bash
uv run godspeed-nav start-direction \
  --workspace-root . \
  --storage-root .godspeed-harness/session \
  --label "Reference layer" \
  --statement "Add operator reference docs"
```

### `review-horizon`

Evaluates candidate transformations, records payment estimates, applies policy gates, and returns the next spendable affordance.

```bash
uv run godspeed-nav review-horizon \
  --workspace-root . \
  --storage-root .godspeed-harness/session \
  --direction-id <direction-id> \
  --candidates '[{"id":"docs-ref","statement":"Write references","pathway":"edit docs","costs":{"time":2},"capacities":{"time":5},"expected_horizon_delta":3,"risk":0}]'
```

### `record-settlement`

Records before/after consequence, stores settlement evidence, and updates trajectory.

```bash
uv run godspeed-nav record-settlement \
  --workspace-root . \
  --storage-root .godspeed-harness/session \
  --affordance-id docs-ref \
  --before '{"references":0}' \
  --after '{"references":1}' \
  --payment '{"time":2}' \
  --evidence '["docs alignment test passed"]' \
  --horizon-delta 3
```

### `runtime-snapshot`

Returns current ledger counts, active directions, and latest trajectory.

### `absorbability`

Reads the workspace safety policy before deciding whether an absorption review requires human approval.

### `developmental-report`

Returns the observability summary with settlement quality, payment debt, horizon state, metabolization candidates, and trajectory fields such as `circular_motion`.

### `predictive-extensions`

Builds the predictive extension plan without overriding deterministic ranking. `predictive-extensions` only adds suggestions once settlement history crosses the configured thresholds.

### `validate`

Runs the enterprise-readiness audit across package structure, config, runtime workflow, storage, hooks, MCP, reports, and predictive settings.

`validate` uses a scratch runtime store for its sample workflow checks so it does not fabricate settlement history inside the target storage root.

## Interpretation Rule

- Use `start-direction`, `review-horizon`, `record-settlement`, and `developmental-report` together when running a full developmental session.
- Use `score-settlement` when you need to scrutinize whether evidence is consequence or mere intent.
- Use `predictive-extensions` only as a planning aid. It never replaces settlement.
