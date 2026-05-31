# require_reflection_before_continuing_after_second_unresolved_error

## Policy Definition

```yaml
trigger:
  second_unresolved_error_before_continuing: true
negative_conditions:
- duplicate_error_signals_only
- strategy_revision_after_latest_error
- low_cost_inspection_after_latest_error
- closure_or_settlement_after_latest_error
required_evidence:
- at_least_2_distinct_error_outputs_from_environment_or_tool
- continued_attempt_after_second_error_without_strategy_revision
- recovery_window_remains_open_after_second_error
action:
  require_operator: reflection
  block_next_action_until: revised_plan_exists
```

## Intended Intervention

The second distinct unresolved error is the earliest spendable point to require reflection before the same path continues.

## Current Support Counts

- Mined support: 31
- Would-fire events: 0
- Likely helpful: 0
- Uncertain: 0
- Harmful: 0

## Would-Fire Examples

- None observed.

## Likely Helpful Examples

- None observed.

## Uncertain Examples By Reason

- None observed.

## Harmful Examples

- None observed.

## Fire Timing Distribution

`{}`

## Recovery Opportunity Distribution

`{}`

## Representative Trace Excerpts

- None observed.

## What Evidence Is Still Missing

- More likely-helpful shadow fires with recovery opportunity.
- Clearer outcome signals after policy trigger points.
- Evidence that the policy action changes settlement, not only that the trigger matches.

## Policy-Specific Refinement Check

No policy-specific refinement check is defined.

## Recommendation

`needs_more_evidence`: Policy never fires on evaluated records.
