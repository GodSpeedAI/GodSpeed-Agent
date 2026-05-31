# require_explicit_settlement_for_failure

## Policy Definition

```yaml
trigger:
  settlement_quality: failure_with_signal
  has_failure_condition_evidence: true
negative_conditions:
- settlement_quality_is_not_failure_with_signal
- no_failure_condition_evidence_available
required_evidence:
- settlement_quality_is_failure_with_signal
- failure_condition_has_observable_evidence_test_output_error_message_or_tool_feedback
action:
  require_operator: failure_analysis
  record: error_correction_signal
```

## Intended Intervention

Failures with observable signals should produce explicit error-correction data backed by actual failure condition evidence.

## Current Support Counts

- Mined support: 8
- Supporting datasets: 2 (`agenttrove`, `swegym`)
- Confidence distribution on supporting traces: `min=0.70`, `max=0.80`, `mean=0.775`
- Would-fire events: 3
- Likely helpful: 2
- Uncertain: 1
- Harmful: 0
- False-positive estimate: `0.0%`
- Semantic replay support: `semantic=0.0%`, `partial=0.0%`, `raw=0.0%`

## Would-Fire Examples

- `api-wrong-tool-003` dataset=apibank assessment=uncertain timing=after_failure_already_settled recovery=False evidence=['settlement_quality=failure_with_signal', 'failure_condition_evidence_present']
- `swe-failed-004` dataset=swegym assessment=likely_helpful timing=after_failure_already_settled recovery=False evidence=['settlement_quality=failure_with_signal', 'failure_condition_evidence_present']
- `swe-premature-005` dataset=swegym assessment=likely_helpful timing=after_failure_already_settled recovery=False evidence=['settlement_quality=failure_with_signal', 'failure_condition_evidence_present']

## Likely Helpful Examples

- `swe-failed-004` dataset=swegym assessment=likely_helpful timing=after_failure_already_settled recovery=False evidence=['settlement_quality=failure_with_signal', 'failure_condition_evidence_present']
- `swe-premature-005` dataset=swegym assessment=likely_helpful timing=after_failure_already_settled recovery=False evidence=['settlement_quality=failure_with_signal', 'failure_condition_evidence_present']

## Uncertain Examples By Reason

### policy_would_fire_too_late

- `api-wrong-tool-003` dataset=apibank assessment=uncertain timing=after_failure_already_settled recovery=False evidence=['settlement_quality=failure_with_signal', 'failure_condition_evidence_present']

The uncertain example is not weak because it is noisy; it is uncertain because the trigger depends on a settled failure label, so the fire arrives after the evaluator has already decided the trace failed.

## Harmful Examples

- None observed.

## Fire Timing Distribution

`{"after_failure_already_settled": 3}`

## Recovery Opportunity Distribution

`{"no_recovery_opportunity": 3}`

## Representative Trace Excerpts

- Trace `api-wrong-tool-003`: settlement=failure_with_signal, failure_mode=wrong_tool, trigger_evidence=['settlement_quality=failure_with_signal', 'failure_condition_evidence_present'], uncertainty=policy_would_fire_too_late.
- Trace `swe-failed-004`: settlement=failure_with_signal, failure_mode=test_failure, trigger_evidence=['settlement_quality=failure_with_signal', 'failure_condition_evidence_present'], uncertainty=n/a.
- Trace `swe-premature-005`: settlement=failure_with_signal, failure_mode=test_failure, trigger_evidence=['settlement_quality=failure_with_signal', 'failure_condition_evidence_present'], uncertainty=n/a.

## What Evidence Is Still Missing

- More likely-helpful shadow fires with recovery opportunity.
- Traces where the policy would fire before failure is fully settled.
- More cross-domain support outside `swegym` `test_failure` traces.
- Cases where the agent is explicitly claiming or implying failure in-line, rather than only failing by final evaluator judgment.

## Policy-Specific Refinement Check

The trigger is tied to observed `failure_with_signal` settlement and explicit failure-condition evidence.
Recovery opportunity fires: 0.
Domain distribution of current fires: `apibank=1`, `swegym=2`.
The two likely-helpful examples are both `swegym` `test_failure` traces, so a code/test-failure variant is plausible.
The broad cross-domain trigger currently lands too late to serve as strong intervention evidence.

## Recommendation

`refine`: keep the policy inactive, but move the trigger earlier or split out a narrower code/test-failure variant so the intervention can be observed before failure is already settled.
