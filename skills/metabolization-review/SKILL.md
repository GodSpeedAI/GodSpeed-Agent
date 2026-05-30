---
description: Use this skill when a user asks whether a repeated capability, workflow, tool, habit, or agent behavior has become substrate through settlement, repetition, time, stability, and lower attention burden.
---

# Metabolization Review

## Overview

Use this skill to decide whether a capability has moved from effortful execution into substrate. Metabolization is not a compliment and not a declaration. It is the consequence of repeated settlement across time, contexts, and attention demands.

Review settlement history, reuse frequency, context diversity, stability, maintenance burden, and attention burden. Recommend metabolization only when evidence shows the capability has become body.

## When To Use

Use this skill when the question is:

- Has this workflow become substrate?
- Is this skill stable enough to rely on without high attention burden?
- Should this behavior be compiled into the body of the system?

Do not use this skill for one-off wins or for actions that have not yet survived repeated settlement.

## Inputs

- Settlement history for the candidate capability.
- Reuse frequency.
- Context diversity across successful uses.
- Stability of outcomes.
- Maintenance burden and attention burden.
- Any evidence of brittleness or dependence on one operator.

## Workflow

1. Confirm there is real settlement history. Without repeated settlement, stop.
2. Count reuse frequency and note how much time the capability has been in use.
3. Check context diversity. A capability proven only in one narrow context is not yet substrate.
4. Evaluate stability. Ask whether the capability holds under normal variance.
5. Evaluate maintenance and attention burden. Metabolized capability should cost less conscious control over time.
6. Classify the result:
	- `not_metabolized` when evidence is sparse or brittle.
	- `substrate_candidate` when evidence is strong but still worth watching.
	- `metabolized` only when repetition, time, stability, and low attention burden align.
7. State what further repetition or evidence would change the decision.

## Output

Return all of the following:

- Status recommendation.
- The evidence supporting or blocking metabolization.
- Weak points that still require conscious attention.
- Clear next conditions for re-review.

## Common Failure Modes

- Promoting a fresh success to substrate.
- Ignoring context diversity and stability.
- Confusing operator familiarity with true metabolization.
- Overlooking the ongoing maintenance burden.
- Declaring metabolization because the capability is strategically important.

Use `references/metabolization.md` for the doctrinal threshold, and `scripts/metabolization.py` when you need a structured evaluation scaffold.

