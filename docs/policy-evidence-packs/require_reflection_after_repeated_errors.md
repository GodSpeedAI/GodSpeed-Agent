# require_reflection_after_repeated_errors

## Historical Late-Trigger Variant

```yaml
id: require_reflection_after_repeated_errors
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

This historical variant remains useful as a late diagnostic marker, but it does not qualify as a harness intervention on the expanded adjudication surface.

Historical late-trigger evidence on the expanded settlement surface:

- Mined support: `31`
- Would-fire events: `2`
- Likely helpful: `0`
- Uncertain: `2`
- Harmful: `0`
- Fire timing: `{"final_turn": 2}`
- Recovery opportunity: `{"no_recovery_opportunity": 2}`
- Recommendation: `refine`

The controlling problem did not change: both fires land on the final available turn, so reflection cannot be observed while recovery still exists.

## Refined Pre-Settlement Variant

```yaml
id: require_reflection_before_continuing_after_second_unresolved_error
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

This refined variant now counts only tool or environment feedback as error evidence and suppresses the cases that previously made the heuristic harmful on successful SWE traces.

Refined pre-settlement evidence on the expanded settlement surface:

- Mined support: `31`
- Would-fire events: `0`
- Likely helpful: `0`
- Uncertain: `0`
- Harmful: `0`
- Fire timing: `{}`
- Recovery opportunity: `{}`
- Recommendation: `needs_more_evidence`

## Evidence Comparison

- The historical variant still fires, but only on final-turn traces with no remaining recovery window.
- The refined variant no longer overfires on successful SWE traces because assistant analysis text is no longer treated as spendable error evidence.
- On the expanded evidence surface, no trace currently shows the exact combination this refined policy requires: a second distinct tool or environment error, continued same-path action, no strategy revision, no low-cost inspection, and remaining recovery window.
- The result is an honest absence of qualifying intervention evidence, not a claim that the historical late marker was already good enough.

## Current Recommendation

Keep the historical variant at `refine` for archival comparison only. Keep the refined variant `proposed`, but treat it as `needs_more_evidence` rather than activation-ready. No activation is justified until real traces show the refined trigger firing before closure with recovery opportunity still open.
