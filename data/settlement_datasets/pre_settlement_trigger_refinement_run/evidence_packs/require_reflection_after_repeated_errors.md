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
- Would-fire events: 2
- Likely helpful: 0
- Uncertain: 2
- Harmful: 0

## Would-Fire Examples

- `task_1119` dataset=agenttrove assessment=uncertain timing=final_turn recovery=False evidence=['error_count=4>=3', 'errors_unresolved=4_of_4']
- `swe-failed-004` dataset=swegym assessment=uncertain timing=final_turn recovery=False evidence=['error_count=3>=3', 'errors_unresolved=3_of_3']

## Likely Helpful Examples

- None observed.

## Uncertain Examples By Reason

### no_recovery_opportunity

- `task_1119` dataset=agenttrove assessment=uncertain timing=final_turn recovery=False evidence=['error_count=4>=3', 'errors_unresolved=4_of_4']
- `swe-failed-004` dataset=swegym assessment=uncertain timing=final_turn recovery=False evidence=['error_count=3>=3', 'errors_unresolved=3_of_3']

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
- Clearer outcome signals after policy trigger points.
- Evidence that the policy action changes settlement, not only that the trigger matches.

## Policy-Specific Refinement Check

Repeated errors should remain constrained to unresolved tool or environment errors.
Late, final, or already-settled fires: 2.
Reflection remains plausible when recovery opportunity exists; traces that need a revised plan should refine the intervention before activation.
Offline evaluator limitation signals: 0.

## Recommendation

`keep_proposed`: Insufficient evidence for promotion.
