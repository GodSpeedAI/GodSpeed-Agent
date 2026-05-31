# require_explicit_settlement_for_failure

## Historical Late-Trigger Variant

```yaml
id: require_explicit_settlement_for_failure
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

This historical variant identifies real failure-analysis need, but it does so only after the evaluator has already settled the trace as a failure.

Historical late-trigger evidence on the expanded settlement surface:

- Mined support: `8`
- Would-fire events: `3`
- Likely helpful: `2`
- Uncertain: `1`
- Harmful: `0`
- Fire timing: `{"after_failure_already_settled": 3}`
- Recovery opportunity: `{"no_recovery_opportunity": 3}`
- Recommendation: `refine`

The likely-helpful examples stay useful as diagnosis, but they are still postmortem labels rather than harness interventions.

## Refined Pre-Settlement Variant

```yaml
id: require_failure_evidence_before_stopping_on_test_failure
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

The refined variant uses code/test-failure-specific timing. It can now fire at the second failed test when the run still has turns left, rather than waiting for a settled failure label.

Refined pre-settlement evidence on the expanded settlement surface:

- Mined support: `8`
- Would-fire events: `1`
- Likely helpful: `1`
- Uncertain: `0`
- Harmful: `0`
- Fire timing: `{"late": 1}`
- Recovery opportunity: `{"has_recovery_opportunity": 1}`
- Recommendation: `keep_proposed`

Representative refined fire:

- `swe-failed-004` dataset=swegym assessment=likely_helpful timing=`late` recovery=`True` evidence=`['test_failure_signal_detected', 'test_failure_turn=4', 'repeated_test_failure_signal_detected', 'repeated_failure_turn=9']`

## Evidence Comparison

- The historical variant fires `3` times, but every fire arrives `after_failure_already_settled` with zero recovery opportunity.
- The refined variant drops the broad cross-domain late label and recovers one code-domain trace as an actual pre-closure intervention surface.
- The key movement is not count inflation; it is timing movement from settled failure to a still-open recovery window on `swe-failed-004`.
- The remaining evidence is narrow: one helpful code trace is enough to justify keeping the refined variant proposed, but not enough to justify activation.

## Current Recommendation

Keep the historical variant at `refine` for comparison only. Keep the refined code/test-failure variant `proposed` with `keep_proposed` status. It is not activation-ready, but it is the first version of this policy family that produces a likely-helpful fire before settlement closes and while recovery opportunity still exists.
