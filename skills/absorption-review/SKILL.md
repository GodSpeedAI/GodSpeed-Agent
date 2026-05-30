---
description: Use this skill when a user asks whether an external project, library, repository, skill, agent, or capability can be absorbed into the receiving system without pretending potential is already affordance.
---

# Absorption Review

## Overview

Use this skill to decide whether an external capability can enter the receiving system as more than fantasy. External material remains potential until a real pathway, acceptable payment, compatible license position, and settlement plan exist.

Compare the external system against the root project. Require a pathway, payment estimate, license summary, settlement plan, and safe worktree plan before recommending absorption.

## When To Use

Use this skill when the question is:

- Can we absorb this repo, agent, tool, or library?
- Is this outside capability reachable from our current substrate?
- What blocks safe incorporation?

Do not use this skill for internal cleanup or for capabilities already proven inside the current system.

## Inputs

- The receiving system state.
- The external capability or repository state.
- Desired direction motivating the absorption.
- Capability delta between the two systems.
- License summary.
- Proposed pathway, settlement plan, and review constraints.

## Workflow

1. Clarify why the external capability matters to the desired direction.
2. Compare the external state to the current substrate and identify the capability delta.
3. Confirm there is a pathway into the receiving system. Without one, stop and classify as `potential`.
4. Review payment: integration cost, coordination, maintenance, migration burden, and risk.
5. Review license and policy gates.
6. Decide whether the candidate is:
	- `potential` with no viable pathway.
	- `possibility` with a plausible path but unresolved payment or policy.
	- `absorbable` only when pathway, payment, license, and settlement plan all align.
7. State the smallest safe next step, such as experiment, worktree trial, or documentation review.

## Output

Return all of the following:

- Absorbability status.
- Capability delta summary.
- Pathway and blockers.
- Payment and maintenance implications.
- License or review constraints.
- Smallest safe next step.

## Common Failure Modes

- Treating external capability as instantly available because it looks impressive.
- Ignoring license compatibility.
- Underestimating maintenance and integration burden.
- Skipping a settlement plan.
- Absorbing broad external structure when only a small fragment is needed.

Use `references/absorption.md` to keep the criteria precise, and `scripts/absorb.py` when a structured review scaffold is needed.

