---
description: Use this skill when a user asks whether an action, feature, experiment, or agent move is affordable from the current horizon and needs payment burden, capacity, risk, and spendability accounting.
---

# Affordance Accounting

## Overview

Use this skill to decide whether a candidate can actually be spent from the current horizon. Affordance accounting is not cost estimation in the abstract. It is a decision about whether a transformation is reachable now, affordable now, and worth paying for given the expected horizon expansion.

Estimate payment across time, compute, risk, complexity, maintenance, attention, and coordination. Reject candidates that have no pathway or exceed configured safety thresholds.

## When To Use

Use this skill when the real question is:

- Can we afford this move?
- What is the burden of this candidate?
- Is this still an affordance, or has it degraded into possibility?
- Which payment dimensions are doing the blocking?

Do not use this skill for post-hoc settlement scoring or capability metabolization review.

## Inputs

- A candidate transformation with a concrete pathway.
- Cost dimensions such as time, risk, complexity, maintenance, attention, and coordination.
- Capacity limits or policy thresholds.
- Expected horizon delta or strategic benefit.
- Any relevant human-review gates.

## Workflow

1. Confirm the candidate has a pathway. Without a pathway, stop and classify it as `potential`.
2. Enumerate payment dimensions explicitly. If a dimension is unknown, mark it unknown instead of assuming zero.
3. Compare payment against current capacities and policy thresholds.
4. Determine spendability:
	- `affordable` when burden fits current capacity.
	- `unaffordable` when burden exceeds capacity or triggers blocking policy.
5. Explain which dimension dominates the burden. One expensive dimension often matters more than many cheap ones.
6. If unaffordable, say whether the candidate should remain a `possibility`, be decomposed into smaller affordances, or be dropped.
7. If affordable, report the price clearly so the operator understands what will be spent.

## Output

Return all of the following:

- Payment burden and spendability.
- Dominant cost dimensions.
- Capacity comparison.
- Policy implications or required review gates.
- A recommendation: spend now, decompose, wait, or reject.

## Common Failure Modes

- Treating missing data as free payment.
- Ignoring coordination or attention burden because they are harder to quantify.
- Calling a candidate affordable because it is strategically attractive.
- Forgetting that blocked candidates remain `possibility`, not `affordance`.
- Estimating burden without checking capacity.

Use `references/payment-and-settlement.md` to keep the payment vocabulary precise, and `scripts/compute_affordance.py` when a structured burden calculation is needed.

