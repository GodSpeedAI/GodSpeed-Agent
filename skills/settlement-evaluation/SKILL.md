---
description: Use this skill when a user asks whether an attempted action actually settled, improved the system, produced consequences, or should be recorded as failed, partial, or successful settlement evidence.
---

# Settlement Evaluation

## Overview

Use this skill to decide what reality actually recorded. Settlement evaluation compares before and after state, weighs the evidence surface, and records consequence instead of intent. It is the main guard against declaring success because a plan was written or a tool was run.

Compare before and after states. Record observed consequence only, and do not treat declared intent, generated documents, or installed tools as proof of capability.

## When To Use

Use this skill when the question is:

- Did this action work?
- Should this count as settlement?
- Is this success, failure, or partial movement?
- What evidence is strong enough to record?

Do not use this skill to decide affordability before action or to decide whether a stable capability has become substrate.

## Inputs

- Before state.
- After state.
- Desired direction or affordance being tested.
- Payment actually spent.
- Evidence such as test output, logs, user-observable behavior, generated artifacts, or runtime deltas.

## Workflow

1. Establish the before state and after state in comparable terms.
2. List the evidence surface. Favor tests, logs, runtime effects, and observable outputs.
3. Reject evidence that only reports intention, belief, or narration.
4. Compare the actual consequence against the claimed change.
5. Score the result as one of:
	- `success` when the after state shows the desired consequence.
	- `partial` when movement occurred but the desired consequence is incomplete.
	- `failed` when the relevant state did not improve or regressed.
6. Record surprises and side effects. Settlement includes unintended consequence.
7. State what this result should change in the next horizon review.

## Output

Return all of the following:

- Settlement status.
- A brief explanation grounded in before/after evidence.
- Evidence accepted and evidence rejected.
- Payment spent.
- Consequences that should affect the next decision.

## Common Failure Modes

- Treating generated code, prose, or configuration as proof without execution evidence.
- Calling a settlement successful because the operator intended the right thing.
- Ignoring regressions because one metric improved.
- Forgetting to note unexpected side effects.
- Treating a failed settlement as neutral.

Use `references/settlement-evidence.md` when the evidence surface is disputed, and `scripts/settlement.py` when you want a structured evaluation scaffold.

