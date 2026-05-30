# Horizon Review Glossary

## Purpose

This glossary keeps horizon review anchored to the project doctrine. It exists to prevent agents from using attractive but imprecise language when they classify the next move.

## Decision Rules

- `potential`: imaginable transformation without a validated pathway from the current horizon.
- `possibility`: plausible transformation that still lacks proven spendability or affordable payment.
- `affordance`: visible transformation with a pathway, a payment estimate, and current spendability.
- `capability`: repeated successful settlement that can now support further transformation.
- `substrate`: metabolized capability that lowers future attention burden and expands the horizon.
- If a candidate depends on capabilities the system does not yet possess, do not upgrade it past `potential` or `possibility`.
- If payment exceeds current capacity, treat the candidate as `possibility`, not `affordance`.

## Enterprise Notes

- Use the same classification terms across skills, hooks, agents, reports, and MCP tools so enterprise audit surfaces stay consistent.
- Record why a candidate was rejected. Enterprise operators need to know whether the blocker was pathway, payment, policy, or evidence.
- Preserve local-first review. Horizon review should not require remote dependencies to decide whether a transformation is visible.

## Failure Modes

- Treating ambitious language as proof of visibility.
- Calling a transformation an affordance without checking pathway and payment.
- Confusing prior success in another environment with current capability in this one.
- Recommending a full roadmap when only the next affordable move is justified.

Use this glossary as the audit-safe vocabulary surface for horizon review decisions.
