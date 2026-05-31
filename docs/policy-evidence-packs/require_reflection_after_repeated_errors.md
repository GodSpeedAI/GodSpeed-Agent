# require_reflection_after_repeated_errors

## Policy Definition

```yaml
trigger:
  error_count_gte: 3
  errors_are_unresolved: true
negative_conditions:
- errors_are_resolved_in_subsequent_turns
- error_count_is_only_analysis_mentions
required_evidence:
- at_least_3_error_outputs_from_environment_or_tool
- errors_remain_unresolved_at_trace_end_or_last_3_turns
action:
  require_operator: reflection
  block_next_action_until: revised_plan_exists
```

## Intended Intervention

Repeated unresolved errors from environment/tool feedback indicate settlement feedback is not being metabolized.

## Current Support Counts

- Mined support: 31
- Supporting datasets: 1 (`agenttrove`)
- Confidence distribution on supporting traces: `min=0.80`, `max=0.80`, `mean=0.80`
- Would-fire events: 2
- Likely helpful: 0
- Uncertain: 2
- Harmful: 0
- False-positive estimate: `0.0%`
- Semantic replay support: `semantic=33.3%`, `partial=66.7%`, `raw=0.0%`

## Would-Fire Examples

- `task_1119` dataset=agenttrove assessment=uncertain timing=final_turn recovery=False evidence=['error_count=4>=3', 'errors_unresolved=4_of_4']
- `swe-failed-004` dataset=swegym assessment=uncertain timing=final_turn recovery=False evidence=['error_count=3>=3', 'errors_unresolved=3_of_3']

## Likely Helpful Examples

- None observed.

## Uncertain Examples By Reason

### no_recovery_opportunity

- `task_1119` dataset=agenttrove assessment=uncertain timing=final_turn recovery=False evidence=['error_count=4>=3', 'errors_unresolved=4_of_4']
- `swe-failed-004` dataset=swegym assessment=uncertain timing=final_turn recovery=False evidence=['error_count=3>=3', 'errors_unresolved=3_of_3']

Both uncertain cases are dominated by the same adjudication problem: the trigger lands on the final available turn, so the evaluator cannot observe whether reflection plus a revised plan would have changed anything.

## Harmful Examples

- None observed.

## Fire Timing Distribution

`{"final_turn": 2}`

## Recovery Opportunity Distribution

`{"no_recovery_opportunity": 2}`

## Representative Trace Excerpts

- Trace `task_1119`: settlement=recovered_success, failure_mode=failed_recovery, trigger_evidence=['error_count=4>=3', 'errors_unresolved=4_of_4'], uncertainty=no_recovery_opportunity.
- Trace `swe-failed-004`: settlement=failure_with_signal, failure_mode=test_failure, trigger_evidence=['error_count=3>=3', 'errors_unresolved=3_of_3'], uncertainty=no_recovery_opportunity.

## What Evidence Is Still Missing

- More likely-helpful shadow fires with recovery opportunity.
- Earlier trigger points on traces with unresolved repeated errors and at least one or two turns left to recover.
- Clearer separation between true unresolved tool or environment errors and generic failed attempts.
- Evidence that the intervention is not just generic reflection but reflection plus an explicit revised plan.

## Policy-Specific Refinement Check

- Repeated errors should remain constrained to unresolved tool or environment errors.
- Final-turn fires: 2.
- Recovery-opportunity fires: 0.
- The current action surface is too broad if interpreted as generic reflection alone; the evidence supports a more explicit revised-plan intervention.
- The lack of helpfulness is at least partly an evaluator and trace-timing problem, not direct evidence that reflection is harmful.

## Recommendation

`refine`: keep the policy inactive, but narrow it toward earlier unresolved-error accumulation and make the intervention explicitly require a revised plan before more action.
