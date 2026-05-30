# Payment And Settlement

## Purpose

This reference defines the difference between what must be spent and what reality actually accepts. It exists to keep affordability analysis and settlement evaluation from collapsing into one vague judgment.

## Decision Rules

- Payment is estimated across time, compute, risk, complexity, maintenance, attention, and coordination.
- Settlement records observed consequences only.
- A candidate with no pathway is not affordable because it is not yet spendable.
- A candidate whose payment burden exceeds current capacity remains `possibility` even if strategically attractive.
- Payment is immediate cost. Settlement is post-action consequence.

## Enterprise Notes

- Record dominant payment dimensions so operators can see what actually constrains execution.
- Preserve the original payment estimate and the actual payment spent. Enterprise review depends on comparing the two.
- Do not hide attention or coordination costs. These dimensions often drive enterprise failures even when code changes look cheap.

## Failure Modes

- Treating unknown payment as zero.
- Conflating payment estimate with proof of outcome.
- Ignoring policy gates when payment appears affordable.
- Using settlement language before the environment has produced observable evidence.

Use this reference when payment and settlement need to stay separable under audit.
