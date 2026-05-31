# Policy Helpfulness Adjudication Report

**Date:** 2026-05-31
**Purpose:** Explain uncertain shadow-mode outcomes and produce evidence packs for two promising policies.
**Result:** No policy was activated. No candidate was marked metabolized. Both target policies remain below the activation gate, and both need refinement rather than promotion.

## Commands Run

```bash
uv run pytest tests/test_policy_shadow_eval.py::TestWouldHaveFiredResultGeneration::test_target_policy_filter_limits_shadow_results tests/test_policy_shadow_eval.py::TestPolicyEvidencePacks -q
uv run pytest tests/test_policy_shadow_eval.py -q
PYTHONPATH=. uv run python - <<'PY'
# Evaluated evidence_accumulation_run settlements at min_confidence=0.65
# and wrote target-policy artifacts under:
# data/settlement_datasets/policy_helpfulness_adjudication_run/
# docs/policy-evidence-packs/
PY
```

## Target Policies Evaluated

The pass evaluated `332` high-confidence policy-record pairs per target policy from the evidence accumulation settlement surface. It produced `664` target-policy shadow results and `5` would-fire events.

| Policy | Mined Support | Would Fire | Helpful | Harmful | Uncertain | Recommendation |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `require_reflection_after_repeated_errors` | 31 | 2 | 0 | 0 | 2 | `refine` |
| `require_explicit_settlement_for_failure` | 8 | 3 | 2 | 0 | 1 | `refine` |

## Uncertainty Reason Distribution

| Policy | Distribution |
| --- | --- |
| `require_reflection_after_repeated_errors` | `{"no_recovery_opportunity": 2}` |
| `require_explicit_settlement_for_failure` | `{"policy_would_fire_too_late": 1}` |

## Fire Timing Distribution

| Policy | Distribution |
| --- | --- |
| `require_reflection_after_repeated_errors` | `{"final_turn": 2}` |
| `require_explicit_settlement_for_failure` | `{"after_failure_already_settled": 3}` |

## Recovery Opportunity Distribution

| Policy | Recovery Opportunity Count | Helpful With Recovery | Uncertain With Recovery | Fires After Failure Settled |
| --- | ---: | ---: | ---: | ---: |
| `require_reflection_after_repeated_errors` | 0 | 0 | 0 | 0 |
| `require_explicit_settlement_for_failure` | 0 | 0 | 0 | 3 |

## Evidence Packs

- [require_reflection_after_repeated_errors](policy-evidence-packs/require_reflection_after_repeated_errors.md)
- [require_explicit_settlement_for_failure](policy-evidence-packs/require_explicit_settlement_for_failure.md)

## Policy Refinement Check

`require_reflection_after_repeated_errors` is not weak because it is harmful; it is weak because its two fires occur on final turns with no spendable recovery path. The trigger needs evidence that repeated errors are unresolved before the trace is effectively over. Reflection is also too broad as currently written; the intervention should be tightened toward reflection plus an explicit revised plan.

`require_explicit_settlement_for_failure` has two likely-helpful fires and no harmful fires, but all three fires occur after failure has already settled. That makes the current evidence more useful for ledger quality than live intervention quality. The likely-helpful examples are both `swegym` `test_failure` traces, so a code/test-failure refinement is now plausible.

## Why No Policy Was Activated

Neither policy meets the activation candidate gate:

- `require_reflection_after_repeated_errors`: `0` likely-helpful fires, below the `>= 5` threshold.
- `require_explicit_settlement_for_failure`: `2` likely-helpful fires, below the `>= 5` threshold.
- Both policies have `0` recovery-opportunity fires in this pass.
- No harmful fires were observed, but absence of harm is not activation evidence by itself.

The bottleneck is not only insufficient evidence. The stronger bottleneck is trigger timing: the available fires occur too late to show that the policy would have changed settlement.

## Recommended Next Move

Refine both policies and keep them inactive. Next, mine or label traces where the same triggers occur before the final turn and before failure settlement, then rerun this adjudication pass. Do not activate either policy until likely-helpful fires with recovery opportunity meet the existing gate.
