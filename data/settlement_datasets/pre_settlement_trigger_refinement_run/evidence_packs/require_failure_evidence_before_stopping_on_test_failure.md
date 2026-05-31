# require_failure_evidence_before_stopping_on_test_failure

## Policy Definition

```yaml
trigger:
  closure_without_failure_evidence_after_test_failure: true
negative_conditions:
- domain_is_not_code
- failure_evidence_already_present
- task_already_settled
required_evidence:
- code_domain_test_failure_signal_detected_before_closure
- closure_or_stop_attempt_after_test_failure
- no_explicit_failure_evidence_recorded_before_closure
action:
  require_operator: failure_analysis
  record: error_correction_signal
```

## Intended Intervention

A failing test should produce explicit failure evidence before the agent closes the run, while recovery opportunity still exists.

## Current Support Counts

- Mined support: 8
- Would-fire events: 1
- Likely helpful: 1
- Uncertain: 0
- Harmful: 0

## Would-Fire Examples

- `swe-failed-004` dataset=swegym assessment=likely_helpful timing=late recovery=True evidence=['test_failure_signal_detected', 'test_failure_turn=4', 'repeated_test_failure_signal_detected', 'repeated_failure_turn=9']

## Likely Helpful Examples

- `swe-failed-004` dataset=swegym assessment=likely_helpful timing=late recovery=True evidence=['test_failure_signal_detected', 'test_failure_turn=4', 'repeated_test_failure_signal_detected', 'repeated_failure_turn=9']

## Uncertain Examples By Reason

- None observed.

## Harmful Examples

- None observed.

## Fire Timing Distribution

`{"late": 1}`

## Recovery Opportunity Distribution

`{"has_recovery_opportunity": 1}`

## Representative Trace Excerpts

- Trace `swe-failed-004`: settlement=failure_with_signal, failure_mode=test_failure, trigger_evidence=['test_failure_signal_detected', 'test_failure_turn=4', 'repeated_test_failure_signal_detected', 'repeated_failure_turn=9'], uncertainty=n/a.

## What Evidence Is Still Missing

- More likely-helpful shadow fires with recovery opportunity.
- Clearer outcome signals after policy trigger points.
- Evidence that the policy action changes settlement, not only that the trigger matches.

## Policy-Specific Refinement Check

No policy-specific refinement check is defined.

## Recommendation

`keep_proposed`: Helpful on 1 traces but below activation threshold (need 5+).
