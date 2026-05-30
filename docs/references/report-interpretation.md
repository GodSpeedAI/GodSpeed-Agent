# Report Interpretation

## Purpose

`godspeed-nav developmental-report` is only useful if operators know what to do when it shows stress, drift, or circular motion. This guide explains the main fields and the operator response each one should trigger.

## Settlement Quality

### `success`

- Meaning: the runtime found observable consequence, acceptable score, and no blocking regression.
- Operator response: consider whether repeated success is now strong enough to count toward metabolization.

### `partial`

- Meaning: some improvement occurred, but the result is mixed, incomplete, or accompanied by regression.
- Operator response: inspect the settlement evidence before repeating the same move. `partial` is often a sign that the next affordable affordance should be narrower.

### `failed`

- Meaning: evidence was intent-only, no observable change occurred, or consequence moved away from the desired direction.
- Operator response: stop calling the action a capability. Reassess pathway, payment, or desired direction.

## Payment Debt

### `total_burden`

- Meaning: accumulated payment across the recorded payment ledger.
- Operator response: rising burden without matching horizon growth is a scrutiny trigger.

### `unaffordable`

- If horizon review or payment analysis marks a candidate `unaffordable`, it should remain a possibility rather than a spendable affordance.
- Operator response: reduce scope, increase capacity, or choose a cheaper transformation.

## Trajectory

### `circular_motion`

- Meaning: the system appears to be rotating without meaningful outward radius growth.
- Operator response: treat this as a self-critique alert. Repeating the same loop is no longer proof of progress.

### `radius_growth`

- Meaning: observed outward development in the sampled trajectory window.
- Operator response: compare growth against payment debt. Cheap growth is better than expensive spinning.

## Horizon

### `active_direction_count`

- Meaning: number of directions still open.
- Operator response: too many active directions can indicate diffusion rather than development.

## Metabolization

### `candidate_count`

- Meaning: number of capabilities that are at least plausible candidates for substrate.
- Operator response: inspect whether those candidates are backed by repeated settlement, not narrative optimism.

## Governing Rule

The report is a scrutiny surface, not a dashboard trophy. If `partial`, `unaffordable`, or `circular_motion` appears, the correct response is to change behavior or revise direction, not to decorate the output.
