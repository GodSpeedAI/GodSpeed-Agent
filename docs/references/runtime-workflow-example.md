# Runtime Workflow Example

## Purpose

This example shows one local developmental session from desired direction through horizon review, settlement, report inspection, and the beginning of metabolization.

## Step 1: Start A Desired Direction

```bash
uv run godspeed-nav start-direction \
  --label "Close docs gaps" \
  --statement "Add the operator reference layer"
```

Outcome:

- A record is written to `desired_directions`.
- An initial horizon is written to `horizons`.

## Step 2: Review The Horizon

```bash
uv run godspeed-nav review-horizon \
  --direction-id <direction-id> \
  --candidates '[{"id":"docs-reference","statement":"Write docs references","pathway":"edit markdown","costs":{"time":2},"capacities":{"time":5},"expected_horizon_delta":3,"risk":0}]'
```

Outcome:

- Payment is estimated and written to `payments`.
- The candidate is classified as potential, possibility, or affordance.
- The runtime persists an explicit spendable path with required preconditions, transition sequence, expected settlement, and lifecycle status.
- The runtime returns the next recommended spendable transformation rather than confusing a visible destination with a spendable path.

The distinction matters: a visible destination is something the operator can name, but a spendable path is a pathway the runtime can actually sequence and pay for under present conditions. Path quality should therefore reward explicit transition sequence and readiness, not just outcome desirability.

## Step 3: Record Settlement

```bash
uv run godspeed-nav record-settlement \
  --affordance-id docs-reference \
  --before '{"reference_docs":0}' \
  --after '{"reference_docs":1}' \
  --payment '{"time":2}' \
  --evidence '["tests/test_docs_alignment.py passed"]' \
  --horizon-delta 3
```

Outcome:

- A settlement record is written to `settlements`.
- A trajectory update is written to `trajectories`.
- The system can now inspect whether the action actually expanded the horizon.

## Step 4: Review The Developmental Report

```bash
uv run godspeed-nav developmental-report
```

Look for:

- whether settlement quality improved
- whether payment stayed affordable
- whether `circular_motion` stayed false
- whether any capabilities are becoming metabolization candidates

## Step 5: Repeat Until Capability Becomes Substrate

One success is not metabolization. Repeat the same settled path in multiple contexts until the capability stops consuming active attention. That is the practical bridge between a one-off win and substrate.

## Predictive Extensions Rule

If settlement history later grows large enough, `predictive-extensions` may suggest likely next moves. It still does not replace `record-settlement`, because simulation is not settlement.
