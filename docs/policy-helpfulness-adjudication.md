# Policy Helpfulness Adjudication

Policy helpfulness adjudication explains shadow-mode evidence before any policy is activated.

Mining support is not activation evidence. A mined policy remains a possibility until shadow evaluation shows where it would fire, whether the fire has recovery opportunity, and whether the observed settlement supports a helpful, harmful, or uncertain counterfactual.

## Target Policies

This pass focuses only on:

- `require_reflection_after_repeated_errors`
- `require_explicit_settlement_for_failure`

No new adapters, confidence-threshold changes, policy activation, or metabolization status promotion are part of this pass.

## Uncertainty Reasons

Every uncertain would-fire result must include:

```json
{
  "counterfactual_assessment": "uncertain",
  "uncertainty_reason": "missing_outcome_signal",
  "uncertainty_evidence": []
}
```

Valid reasons are:

- `missing_outcome_signal`
- `insufficient_trace_context`
- `policy_would_fire_too_late`
- `policy_action_effect_not_observable_offline`
- `ambiguous_failure_mode`
- `weak_trigger_evidence`
- `conflicting_settlement_evidence`
- `no_recovery_opportunity`
- `unknown`

These reasons separate weak policy evidence from offline evaluator limits. An uncertain result can still be useful if it explains what signal is missing.

## Fire Timing

Each would-fire event records `fire_turn_index`, `fire_timing`, and `remaining_turns_after_fire`.

Timing values are `early`, `middle`, `late`, `final_turn`, `after_failure_already_settled`, and `unknown`.

A fire after failure settlement is not strong activation evidence. It can show that the trigger matches the outcome label, but it does not show that the policy could have changed the trace.

## Recovery Opportunity

Each would-fire event records whether a realistic recovery path remained after the trigger through `recovery_opportunity` and `recovery_opportunity_evidence`.

Examples:

- repeated error followed by more actions: recovery opportunity exists
- final-turn trigger: no recovery opportunity
- failure followed by corrective action: recovery opportunity exists
- trigger based on settled failure label: no recovery opportunity

## Summary Metrics

Shadow summaries include:

- `uncertainty_reason_distribution`
- `fire_timing_distribution`
- `recovery_opportunity_count`
- `helpful_with_recovery_opportunity_count`
- `uncertain_with_recovery_opportunity_count`
- `fires_after_failure_settled_count`

These metrics prevent activation from relying on raw would-fire counts alone.

## Evidence Packs

Evidence packs live in `docs/policy-evidence-packs/`.

Each pack includes the policy definition, intended intervention, current support counts, would-fire examples, helpful examples, uncertain examples by reason, harmful examples, fire timing, recovery opportunity, representative trace excerpts, missing evidence, refinement checks, and recommendation.

## Activation Gate

Uncertainty cleanup does not promote a policy.

The activation candidate gate remains:

```text
likely_helpful_count >= 5
likely_harmful_count == 0
false_positive_rate_estimate <= 0.10
sufficient domain/source support unless intentionally domain-specific
```

No policy becomes active from this pass alone.
