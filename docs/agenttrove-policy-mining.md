# AgentTrove Policy Mining

## Overview

Policy mining converts labeled settlement records into candidate harness policies. Each policy is derived from observed failure patterns in AgentTrove traces and proposes a concrete intervention the harness could enforce.

## Generated Policies

Policies are written to `policies/generated/agenttrove_harness_policies.yaml`.

### Policy Structure

Each policy contains:

```yaml
id: unique_policy_identifier
trigger:
  condition: that activates the policy
action:
  required: intervention
rationale: why this policy improves settlement
evidence:
  supporting_trace_count: N
  total_traces_analyzed: M
  example_trace_ids: [...]
  observed_failure_pattern: [...]
  proportion: 0.XXXX
risk:
  false_positive_concern: ...
  recommended_review: ...
active_by_default: false
```

### Current Policies

1. **require_reflection_after_repeated_tool_errors** - Triggers when error_count >= 2. Requires reflection operator before next tool call.

2. **block_premature_final_answer** - Triggers on premature_closure failure mode. Requires settlement evidence before final answer.

3. **payment_spiral_reset** - Triggers on payment_spiral failure mode. Requires positive disintegration and plan reset.

4. **force_intermediate_representation_for_direct_jump** - Triggers on representation_jump. Requires intermediate representational state before concrete action.

5. **detect_context_loss** - Triggers when later turns ignore early constraints. Requires context check and task restatement.

6. **flag_over_abstraction** - Triggers when agent explains extensively without action. Requires concrete action.

7. **prevent_premature_concretion** - Triggers when first action hits immediate error. Requires constraint gathering first.

8. **require_recovery_evidence_for_brittle_success** - Triggers on brittle_success. Requires metabolization evidence.

9. **escalate_after_three_errors** - Triggers when error_count >= 3. Requires strategy change.

10. **require_explicit_settlement_for_failure** - Triggers on failures. Requires failure analysis recording.

11. **payment_cap_for_unproductive_paths** - Triggers when turn_count > 15 with no success. Suggests terminating unproductive path.

## Using Generated Policies

**Important:** No generated policy is active by default. Each policy must be:

1. Reviewed by a human operator
2. Evaluated against the evidence (trace count, proportion, example traces)
3. Explicitly activated in the harness configuration if desired

To inspect policies:

```bash
cat policies/generated/agenttrove_harness_policies.yaml
```

To run the mining pipeline:

```bash
python scripts/agenttrove/mine_harness_policies.py --input data/agenttrove/settlements/settlement_traces.jsonl
```

## Adding New Policies

New policies can be derived by:

1. Adding failure mode detection in `scripts/agenttrove/label_settlements.py`
2. Adding the failure mode definition in `configs/agenttrove/settlement_label_rules.yaml`
3. Adding the policy mining logic in `scripts/agenttrove/mine_harness_policies.py`
4. Adding tests in `tests/test_agenttrove.py`

The mining script aggregates failure mode frequencies and generates policies from the observed patterns.
