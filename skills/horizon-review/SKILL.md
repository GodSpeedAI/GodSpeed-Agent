---
description: Use this skill when a user asks to turn a goal, problem, desired outcome, code task, or agent behavior into a horizon review that identifies the next affordable affordance rather than treating the outcome as terminal.
---

# Horizon Review

## Overview

Use this workflow to convert a desired direction into visible affordances, hidden potentials, payment estimates, and the next spendable transformation. The point is not to describe the final outcome in more detail. The point is to identify what is spendable from the current horizon.

Always distinguish potential, possibility, affordance, capability, and substrate. Treat completed outcomes as substrate that may expose new affordances.

## When To Use

Use this skill when the request asks some version of:

- What is the next move?
- What is visible from here?
- Which candidates are real affordances versus wishful thinking?
- How should this goal be reframed as a developmental path?

Do not use this skill for pure writing cleanup, isolated implementation details, or final retrospective scoring after the work is already complete.

## Inputs

- The active desired direction, including goal, problem, vision, or outcome language.
- The current horizon: visible constraints, capabilities, tools, and environmental facts.
- Candidate transformations, if any already exist.
- Payment and capacity cues: time, risk, attention, coordination, compute, maintenance.
- Recent settlement evidence that may have changed what is visible.

## Workflow

1. Restate the desired direction in neutral form. Keep the attractor, but remove terminal language.
2. List the candidates currently visible from the horizon.
3. Classify each candidate:
	- `potential` if it has no validated pathway.
	- `possibility` if a pathway seems plausible but payment or unknowns prevent spending.
	- `affordance` if a pathway exists and payment appears affordable.
4. For each affordance candidate, note expected horizon expansion, likely payment, and the capability basis that makes it reachable.
5. Reject imaginary muscles explicitly. If the candidate depends on capabilities the system does not yet possess, say so.
6. Rank the spendable affordances by expected horizon expansion, strategic alignment, and affordability.
7. Recommend one next affordance, not a full roadmap unless the user explicitly asks for a portfolio.
8. Record blind spots and unknowns that would change the review if resolved.

## Output

Return all of the following:

- The active desired direction.
- The next recommended affordance.
- Ranked affordances with brief payment notes.
- Rejected potentials and possibilities with reasons.
- Blind spots or missing pathway information.

## Common Failure Modes

- Treating the desired outcome as if it were already reachable from the current horizon.
- Calling a candidate an affordance without a pathway.
- Ignoring payment and ranking only by ambition.
- Collapsing multiple steps into one unaffordable transformation.
- Confusing previous success in another context with current visibility in this one.

Use `references/glossary.md` when the distinction language starts to drift, and `scripts/horizon_review.py` when a structured horizon-review scaffold is needed.

