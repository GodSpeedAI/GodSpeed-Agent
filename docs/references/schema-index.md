# Schema Index

## Purpose

This index links each schema file under `schemas/` to the runtime concept or workflow it represents. The schemas define the intended record shapes for the developmental operating model even when the current implementation uses lighter-weight JSON records in some paths.

## Schema Map

### `schemas/desired_direction.schema.json`

- Runtime concept: desired direction
- Main producers: `godspeed-nav start-direction`, `NavigationRuntime.start_direction`, `hooks/user_prompt_submit.py`
- Main ledger: `desired_directions`

### `schemas/horizon.schema.json`

- Runtime concept: visible horizon and affordance visibility
- Main producers: `NavigationRuntime.start_direction`
- Main ledgers: `horizons`, `horizon_reviews`

### `schemas/affordance.schema.json`

- Runtime concept: spendable transformation visible from the current horizon
- Main producers: `godspeed-nav review-horizon`, `NavigationRuntime.review_horizon`
- Main ledger: `affordances`

### `schemas/payment.schema.json`

- Runtime concept: payment estimate or actual payment record
- Main producers: `estimate-payment`, `review-horizon`, `pre_tool_use`, `record-settlement`
- Main ledgers: `payments`, `tool_payments`

### `schemas/settlement.schema.json`

- Runtime concept: before/after consequence plus evidence
- Main producers: `score-settlement`, `godspeed-nav record-settlement`, `hooks/post_tool_use.py`
- Main ledgers: `settlements`, `post_tool_use_events`

### `schemas/trajectory.schema.json`

- Runtime concept: Euler-style trajectory update and circular-motion analysis
- Main producers: `update_trajectory`, `record-settlement`, `hooks/stop.py`
- Main ledgers: `trajectories`, `stop_events`

### `schemas/capability.schema.json`

- Runtime concept: latent, active, or metabolized capability
- Main producers: capability and metabolization review paths
- Main ledger: `capabilities`

### `schemas/substrate.schema.json`

- Runtime concept: metabolized capability that has become reusable body
- Main producers: future runtime-owned metabolization and substrate promotion paths
- Main reporting surface: developmental metabolization summary

## Reading Rule

Use this index in both directions:

- Start from a runtime command when you need to know which conceptual schema it should satisfy.
- Start from a schema file when you need to know which workflow or ledger should produce evidence for it.

## Current Implementation Note

The repository already has `desired_direction.schema.json` and `settlement.schema.json` as normative conceptual files, but not every runtime write path performs explicit schema validation on each append. Treat this index as the contract surface that future strict validation should converge on.
