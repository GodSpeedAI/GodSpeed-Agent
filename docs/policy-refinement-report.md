# Policy Refinement Report

## Summary

This pass refined the three broad rejected policies into narrower evidence-bound variants, strengthened the two promising policies with stricter evidence requirements, reran shadow evaluation and eval replay, and kept all policies inactive. No candidate was marked metabolized.

Current verification:

```bash
uv run pytest -q
PYTHONPATH=. uv run python scripts/settlement_datasets/mine_policies.py --dataset all --min-confidence 0.0 --min-supporting-traces 1
PYTHONPATH=. uv run python scripts/settlement_datasets/evaluate_policies_shadow.py --min-confidence 0.0
PYTHONPATH=. uv run python scripts/settlement_datasets/replay_policy_evals.py --min-confidence 0.0
PYTHONPATH=. uv run python scripts/settlement_datasets/update_policy_status.py
PYTHONPATH=. uv run python scripts/settlement_datasets/update_metabolization_status.py
```

Validation settled with `320 passed` after the replay-alignment test additions.

## Original Rejected Policies and Replacements

| Historical policy                      | Historical status | Refined replacement                                               | Current replacement status |
| -------------------------------------- | ----------------- | ----------------------------------------------------------------- | -------------------------- |
| `test_before_final_answer`             | `superseded`      | `require_test_or_settlement_evidence_before_final_for_code_patch` | `proposed`                 |
| `prevent_premature_concretion`         | `superseded`      | `prevent_high_payment_action_when_constraints_unknown`            | `proposed`                 |
| `compare_constraints_before_selection` | `superseded`      | `require_constraint_match_before_multi_option_selection`          | `proposed`                 |

## Before/After False-Positive Reduction

The key comparison is each broad policy against its refined replacement.

| Pair                                                                                               | Before would-fire | Before harmful | Before uncertain | Before FP rate | After would-fire | After harmful | After uncertain | After FP rate |
| -------------------------------------------------------------------------------------------------- | ----------------: | -------------: | ---------------: | -------------: | ---------------: | ------------: | --------------: | ------------: |
| `test_before_final_answer` -> `require_test_or_settlement_evidence_before_final_for_code_patch`    |                13 |              7 |                6 |          53.8% |                0 |             0 |               0 |          0.0% |
| `prevent_premature_concretion` -> `prevent_high_payment_action_when_constraints_unknown`           |                11 |              3 |                8 |          27.3% |                1 |             0 |               1 |          0.0% |
| `compare_constraints_before_selection` -> `require_constraint_match_before_multi_option_selection` |                 5 |              2 |                3 |          40.0% |                1 |             0 |               1 |          0.0% |

Aggregate for the three refined slices:

- Before: `29` would-fire, `12` harmful, `17` uncertain
- After: `2` would-fire, `0` harmful, `2` uncertain

This is the core settlement result of the refinement pass: the replacements sharply reduced false positives without fabricating helpful counts.

## Current Shadow Evaluation

Current active-policy shadow results from `data/settlement_datasets/policy_shadow_eval/policy_shadow_summary.csv`:

| Policy                                                            | Would-fire | Helpful | Harmful | Uncertain | Recommendation        |
| ----------------------------------------------------------------- | ---------: | ------: | ------: | --------: | --------------------- |
| `require_reflection_after_repeated_errors`                        |          1 |       0 |       0 |         1 | `keep_proposed`       |
| `search_before_patch`                                             |          5 |       0 |       0 |         5 | `keep_proposed`       |
| `require_constraint_match_before_multi_option_selection`          |          1 |       0 |       0 |         1 | `keep_proposed`       |
| `inspect_api_schema_before_call`                                  |          0 |       0 |       0 |         0 | `needs_more_evidence` |
| `reset_plan_after_payment_spiral`                                 |          1 |       0 |       0 |         1 | `keep_proposed`       |
| `require_test_or_settlement_evidence_before_final_for_code_patch` |          0 |       0 |       0 |         0 | `needs_more_evidence` |
| `require_explicit_settlement_for_failure`                         |          5 |       2 |       0 |         3 | `keep_proposed`       |
| `prevent_high_payment_action_when_constraints_unknown`            |          1 |       0 |       0 |         1 | `keep_proposed`       |

Historical superseded policies remain in `data/settlement_datasets/policies.yaml` and in `policies/review/policy_status_recommendations.yaml`, but they are excluded from active shadow scoring.

## Eval Replay Results

Eval replay is now calibrated at the ontology layer.

- Total replay items: `17`
- Raw match rate: `0.0%`
- Semantic match rate: `20.0%`
- Partial match rate: `13.3%`
- Exact semantic matches: `2`
- Partial semantic matches: `2`
- Unknown eval behavior count: `2`
- Mismatches: `11`

Per-policy replay summary from `data/settlement_datasets/policy_shadow_eval/eval_replay_summary.csv`:

- `require_reflection_after_repeated_errors`: semantic `33.3%`, partial `66.7%`
- `require_test_or_settlement_evidence_before_final_for_code_patch`: semantic `50.0%`
- `test_before_final_answer`: semantic `50.0%`
- `require_explicit_settlement_for_failure`: semantic `0.0%`, unknown eval `1`
- `compare_constraints_before_selection`: semantic `0.0%`
- `prevent_high_payment_action_when_constraints_unknown`: semantic `0.0%`
- `prevent_premature_concretion`: semantic `0.0%`

This improves replay interpretation, but it is still not evidence for activation.

## Policy Status After Refinement

Policies that remain proposed or proposal-adjacent:

- `require_reflection_after_repeated_errors`: `keep_proposed`
- `search_before_patch`: `keep_proposed`
- `require_constraint_match_before_multi_option_selection`: `keep_proposed`
- `reset_plan_after_payment_spiral`: `keep_proposed`
- `require_explicit_settlement_for_failure`: `keep_proposed`
- `prevent_high_payment_action_when_constraints_unknown`: `keep_proposed`
- `inspect_api_schema_before_call`: `needs_more_evidence`
- `require_test_or_settlement_evidence_before_final_for_code_patch`: `needs_more_evidence`

Historical policies retained as superseded:

- `compare_constraints_before_selection`
- `test_before_final_answer`
- `prevent_premature_concretion`

Policies qualifying as `candidate_for_activation`:

- None

Why no policy should be activated yet:

- no policy reached the `5+ helpful, 0 harmful, FP <= 10%` threshold
- semantic replay improved interpretation but does not replace shadow evidence
- the strongest policy, `require_explicit_settlement_for_failure`, still has only `2` helpful traces
- the refined replacements reduced harmful fires, but two of them remain under-evidenced and one remains uncertain-only

## Metabolization Status

- `update_metabolization_status.py` updated the candidate ledger with no metabolization promotions
- all seven listed candidates remain `repeated`
- no candidate was moved to `tested`
- no candidate was moved to `metabolized`

## Outcome

This refinement pass succeeded on the intended path:

- rejected broad policies were preserved and superseded, not deleted
- narrower replacement policies now exist with explicit negative conditions and required evidence
- false-positive rates decreased sharply on the refined slices
- no successful trace is interrupted by the refined replacements in the current fixture evaluation
- promising policies now require more precise evidence instead of broader governance
- shadow evaluation, eval replay, policy review output, and metabolization status were rerun offline
- no policy was activated
- no candidate was marked metabolized
