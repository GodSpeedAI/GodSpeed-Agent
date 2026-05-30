# Settlement Evidence

## Purpose

This reference defines what counts as evidence strong enough to support settlement claims. It exists to keep the harness aligned with consequence instead of narration.

## Decision Rules

- Prefer before/after state, command output, tests, logs, runtime changes, and user-observable effects.
- Reject `intent:` statements, plans, and promises as settlement evidence.
- Accept partial evidence only when it still shows a real environmental consequence.
- Missing observable change should downgrade the result to failed settlement unless the desired state is purely diagnostic.

## Enterprise Notes

- Preserve accepted evidence separately from rejected evidence for auditability.
- Record regressions alongside improvements. Enterprise settlement review must expose mixed outcomes.
- Keep evidence local and reproducible where possible so operators can re-run the same check during incident response.

## Failure Modes

- Confusing successful command execution with successful settlement.
- Ignoring regressions because one target metric improved.
- Marking partial movement as full success.
- Losing the evidence surface after the decision is recorded.

Use this reference to preserve consequence-first evaluation across enterprise reviews.
