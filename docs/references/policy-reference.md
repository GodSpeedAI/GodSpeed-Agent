# Policy Reference

## Purpose

This document maps `HARNESS.md` policy settings to runtime consequences. Policy is part of the settlement surface because it determines which actions are blocked, warned, or sent to human review.

## Source Of Truth

- Configuration source: `HARNESS.md`
- Loader: `godspeed_nav/config.py`
- Enforcement: `godspeed_nav/policies.py`

Public surfaces inherit these settings through the workspace loader. The CLI, hooks, MCP wrapper, and validation command do not trust caller-supplied storage roots or ad hoc policy flags when a workspace policy exists.

## Core Harness Invariants

- `primary_metric: horizon_expansion`
- `outcome_as_terminal: false`

These keep the runtime aligned with the doctrine in which outcomes are temporary attractors and horizon expansion is the primary operating metric.

## Safety Settings

### `block_unaffordable_actions`

- Location: `HARNESS.md` under `safety`
- Enforcement: `enforce_payment_policy`
- Runtime consequence: unaffordable candidates are blocked instead of merely warned.

### `warn_unaffordable_actions`

- Enforcement: `enforce_payment_policy`
- Runtime consequence: the candidate remains a possibility and receives an explainable warning.

### `max_payment_burden`

- Current role: documented policy threshold for local operation.
- Practical operator use: compare it with `payment_burden` in reports and horizon review output.

### `require_human_review_for_absorption`

- Enforcement: `enforce_absorption_review`
- Runtime consequence: absorption proposals cannot proceed without human review when enabled.

### `require_human_review_for_disintegration`

- Enforcement: `enforce_disintegration_review`
- Runtime consequence: destructive change paths remain gated behind human review.

## Absorption Settings

### `require_license_check`

- A compatible license is part of absorbability review.

### `require_pathway`

- Without a pathway, the capability is still potential rather than absorbable.

### `require_settlement_plan`

- The review should explain how the absorbed capability will be proven through local settlement.

## Computation Settings

### `model_provider`

- Controls which local predictive adapter powers `predictive-extensions`.

### `ml_event_threshold`

- Predictive suggestions activate only after this many settlement events.

### `simulation_threshold`

- Simulation suggestions activate only after this higher threshold.

## Operator Rule

If a policy setting changes in `HARNESS.md`, rerun:

```bash
uv run pytest -q
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation
```

Policy changes are not prose-only edits. They alter runtime behavior and therefore require validation.
