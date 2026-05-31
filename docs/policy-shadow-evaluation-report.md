# Policy Shadow Evaluation Validation Report

**Date:** 2026-05-30
**Policies Evaluated:** 8
**Settlement Records:** 20 (agenttrove: 5, swegym: 5, apibank: 5, webshop: 5)
**Confidence Threshold:** 0.0 (all records included)

## 1. Commands Run

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/evaluate_policies_shadow.py --min-confidence 0.0
PYTHONPATH=. uv run python scripts/settlement_datasets/replay_policy_evals.py --min-confidence 0.0
PYTHONPATH=. uv run python scripts/settlement_datasets/update_policy_status.py
PYTHONPATH=. uv run python scripts/settlement_datasets/update_metabolization_status.py

uv run pytest tests/test_policy_shadow_eval.py -v   # 27 passed
uv run pytest -q                                       # 297 passed
```

## 2. Number of Policies Evaluated

8 proposed policies evaluated against 20 settlement records = 160 policy-record pairs.

## 3. Number of Settlement Records Evaluated

| Dataset | Records | Domain |
|---|---|---|
| agenttrove | 5 | code |
| swegym | 5 | code |
| apibank | 5 | api |
| webshop | 5 | shopping |

## 4. Would-Fire Counts by Policy

| Policy | Would-Fire | Total Pairs |
|---|---|---|
| test_before_final_answer | 13 | 20 |
| prevent_premature_concretion | 11 | 20 |
| search_before_patch | 6 | 20 |
| compare_constraints_before_selection | 5 | 20 |
| require_explicit_settlement_for_failure | 5 | 20 |
| reset_plan_after_payment_spiral | 3 | 20 |
| require_reflection_after_repeated_errors | 2 | 20 |
| inspect_api_schema_before_call | 0 | 20 |

## 5. Likely Helpful / Harmful / Uncertain Counts

| Counterfactual | Count (of would-fire events) |
|---|---|
| uncertain | 30 |
| likely_harmful | 12 |
| likely_helpful | 3 |

**Key finding:** Most would-fire events are `uncertain` (67%) or `likely_harmful` (27%). Only 7% are `likely_helpful`. This suggests the current policy triggers are too broad — they fire on many traces where the policy's failure mode is not the primary issue.

## 6. Promotion Recommendations

| Policy | Helpful | Harmful | FP Rate | Recommendation |
|---|---|---|---|---|
| require_reflection_after_repeated_errors | 1 | 0 | 0.0% | keep_proposed |
| search_before_patch | 0 | 0 | 0.0% | keep_proposed |
| compare_constraints_before_selection | 0 | 2 | 40.0% | **reject** |
| inspect_api_schema_before_call | 0 | 0 | 0.0% | needs_more_evidence |
| reset_plan_after_payment_spiral | 0 | 0 | 0.0% | keep_proposed |
| test_before_final_answer | 0 | 7 | 53.8% | **reject** |
| require_explicit_settlement_for_failure | 2 | 0 | 0.0% | keep_proposed |
| prevent_premature_concretion | 0 | 3 | 27.3% | **reject** |

## 7. Policies Recommended for Refinement

Three policies are recommended for **rejection** due to high harmful counts:

1. **test_before_final_answer** — Would fire on 13 traces, harming 7 successful ones. The trigger (`final_answer_action` without `prior_verification`) matches most traces with terminal output because it cannot distinguish between verified and unverified final answers. Needs tighter trigger logic.

2. **prevent_premature_concretion** — Would fire on 11 traces, harming 3 successful ones. The `early_specific_action` trigger matches many code repair traces where early action is appropriate (e.g., `cat file` to inspect before editing). Needs to distinguish inspection commands from premature edits.

3. **compare_constraints_before_selection** — Would fire on 5 traces, harming 2 successful ones. The `selection_action` trigger matches buy actions but the `prior_comparison` check is too strict for simple purchases. Needs calibration for purchase complexity.

## 8. Policies Recommended for Possible Activation

No policies meet the `candidate_for_activation` threshold (5+ helpful, 0 harmful, FP <= 10%).

The closest policies are:

- **require_explicit_settlement_for_failure**: 2 helpful, 0 harmful, 0% FP. Needs more supporting traces from additional datasets.
- **require_reflection_after_repeated_errors**: 1 helpful, 0 harmful, 0% FP. Needs more traces with high error counts.

## 9. Eval Replay Summary

13 eval items replayed against 5 matching policies:

| Match Result | Count |
|---|---|
| mismatch | 13 |
| match | 0 |

**Finding:** All eval-policy pairs show `mismatch`. The policy actions (e.g., `require_operator: reflection`) do not match the expected harness behaviors in the eval items (e.g., "Agent must break tool loop and propose alternative approach"). The eval expectations use natural language descriptions while policies use structured operator requirements. This is a format mismatch, not a semantic one.

**Recommended fix:** Align eval expected_behavior descriptions with policy action vocabulary, or implement semantic matching.

## 10. Metabolization Candidate Status Changes

| Candidate | Before | After | Change |
|---|---|---|---|
| reflect_after_repeated_tool_error | repeated | repeated | no change |
| test_before_final_answer | repeated | repeated | no change |
| search_before_patch | repeated | repeated | no change |
| inspect_api_schema_before_call | repeated | repeated | no change |
| compare_constraints_before_selection | repeated | repeated | no change |
| reset_plan_after_payment_spiral | repeated | repeated | no change |
| route_through_intermediate_representation | repeated | repeated | no change |

No candidates moved to `tested` because shadow-mode evaluation did not produce sufficient `likely_helpful` evidence for their corresponding policies. No candidates moved to `metabolized` (requires live harness activation).

## 11. Known Weaknesses

1. **Trigger logic is too coarse** — Many triggers fire on traces where the policy's target failure mode is not the primary issue. The `test_before_final_answer` trigger fires on 65% of traces, most of which are successful.

2. **Counterfactual assessment depends on failure mode labeling** — If the adapter's failure mode label is missing or incorrect, the counterfactual assessment will be `uncertain` rather than `likely_helpful` or `likely_harmful`.

3. **Eval replay uses exact keyword matching** — The match between policy actions and eval expectations is based on keyword overlap, which produces false mismatches.

4. **Small sample size** — 20 fixture records are insufficient for reliable promotion scoring. The 5+ helpful threshold cannot be met with only 5 records per dataset.

5. **No cross-dataset variation** — Each adapter has only 5 fixture records with limited failure mode diversity. Real data would produce more varied trigger patterns.

6. **FP risk estimation is binary** — Currently checks only settlement quality and failure mode presence. Does not consider context, domain-specific norms, or trace length.

## 12. Recommended Next Step

1. **Refine trigger logic** for the 3 rejected policies. Narrow triggers to fire only when the target failure mode is present, not on all traces with the general pattern.

2. **Add real data** — Run shadow evaluation on the 100 AgentTrove traces (already available) plus real SWE-Bench or API-Bank data to increase sample size.

3. **Align eval-policy vocabulary** — Map policy `require_operator` values to eval `expected_harness_behavior` descriptions through a vocabulary bridge.

4. **Run shadow evaluation at higher confidence** — Re-run at `--min-confidence 0.65` to focus on high-confidence records where counterfactual assessment is most reliable.
