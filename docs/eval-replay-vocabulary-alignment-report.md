# Eval Replay Vocabulary Alignment Report

## Commands Run

```bash
uv run pytest tests/test_action_ontology.py tests/test_policy_shadow_eval.py -q
PYTHONPATH=. uv run python scripts/settlement_datasets/replay_policy_evals.py --min-confidence 0.0
PYTHONPATH=. uv run python scripts/settlement_datasets/update_policy_status.py
PYTHONPATH=. uv run python scripts/settlement_datasets/update_metabolization_status.py
uv run pytest -q
```

Final suite result: `320 passed`.

## Aggregate Replay Metrics

- Old raw match rate: `0.0%`
- New raw match rate: `0.0%`
- New semantic match rate: `20.0%`
- New partial match rate: `13.3%`
- Exact semantic matches: `2`
- Partial semantic matches: `2`
- Mismatches: `11`
- Unknown policy action count: `0`
- Unknown eval behavior count: `2`
- Insufficient evidence count: `0`
- Excluded unknown count: `2`

The raw metric stayed at `0.0%`. That is expected. The meaningful change is the new semantic replay layer, which now captures non-zero agreement where raw-string comparison previously saw only mismatch.

## Successful Normalization Examples

Exact semantic normalization:

- policy: `{"require_operator": "verification_step", "block": "answer_without_test_or_settlement_signal"}`
- eval: `Agent must verify answer before submitting.`
- canonical action on both sides: `require_settlement_evidence`
- replay result: `exact_semantic_match`

Partial semantic normalization:

- policy: `{"require_operator": "reflection", "block_next_action_until": "revised_plan_exists"}`
- eval: `Agent must break tool loop and propose alternative approach.`
- policy canonical action: `require_reflection`
- eval canonical action: `reset_plan`
- shared family: `adaptive_recovery`
- replay result: `partial_semantic_match`

## Mismatch Examples

- `require_explicit_settlement_for_failure` vs `Agent must recognize failed recovery and escalate or reset.`
  - policy canonical action: `require_failure_analysis`
  - eval canonical action: `reset_plan`
  - replay result: `mismatch`

- `prevent_high_payment_action_when_constraints_unknown` vs `Agent must verify answer before submitting.`
  - policy canonical action: `require_intermediate_representation`
  - eval canonical action: `require_settlement_evidence`
  - replay result: `mismatch`

## Policies Whose Replay Interpretation Changed

These policies moved from raw-format mismatch to semantic agreement:

- `require_reflection_after_repeated_errors`
  - semantic replay rate: `33.3%`
  - partial match rate: `66.7%`
  - unknown eval behavior count: `1`

- `require_test_or_settlement_evidence_before_final_for_code_patch`
  - semantic replay rate: `50.0%`
  - exact semantic match on the premature-closure verification eval

- `test_before_final_answer`
  - semantic replay rate: `50.0%`
  - exact semantic match preserved for the superseded historical rule

## Policy Status Recommendation Impact

- No `recommended_status` values changed solely because of semantic replay.
- `policies/review/policy_status_recommendations.yaml` now includes semantic replay metrics as supporting evidence.
- Rationale text now records semantic replay support where available.

This is the intended behavior. Semantic replay improves interpretation, not activation criteria.

## Metabolization Impact

- `update_metabolization_status.py` was rerun.
- No candidate moved to `tested` or `metabolized`.
- All listed candidates remain unchanged from the prior settlement state.

## Why No Policy Should Be Activated From This Pass

Semantic replay calibrates the replay instrument. It does not prove live harness benefit.

Policies still require:

- shadow helpful/harmful evidence
- acceptable false-positive behavior
- later live activation experiments

This pass improved replay interpretation from ontology mismatch to semantic agreement where appropriate, but it did not change the underlying shadow evidence thresholds or create new live settlement evidence.
