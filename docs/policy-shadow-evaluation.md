# Policy Shadow Evaluation

## Why Mined Policies Are Not Automatically Active

Policy mining identifies patterns in settlement data. It creates possibilities, not affordances.

A mined policy becomes an affordance only after evidence shows that activating it would improve settlement quality without creating excessive false positives, payment burden, or blocked successful paths.

The path is:

```text
mined policy (possibility)
→ shadow evaluation (test affordance)
→ promotion evidence (settlement data)
→ candidate_for_activation (affordance)
→ guarded live activation experiment (controlled settlement)
→ metabolized capability (repeated settlement)
```

Skipping shadow evaluation means activating policies based on mining heuristics alone, which is equivalent to treating simulation as capability.

## What Shadow Mode Means

Shadow mode evaluates proposed policies against historical settlement records without enforcing them.

For each settlement record, the shadow evaluator asks:

1. **Would this policy have fired?** — Does the record match the policy trigger?
2. **What was the observed outcome?** — What actually happened in this trace?
3. **Would the policy have helped or harmed?** — Counterfactual assessment.
4. **What is the false-positive risk?** — Would it fire on successful traces?
5. **What is the payment risk?** — Would it add unnecessary cost?
6. **When would it fire?** — Early enough to leave recovery opportunity, or only after settlement?
7. **Why is an uncertain result uncertain?** — Missing outcome signal, weak trigger evidence, late fire, no recovery opportunity, or another recorded reason.

No LLM calls are needed. This is deterministic rule replay against historical data.

## Why Eval Replay Needed Calibration

The original eval replay path compared policy actions and eval expected behaviors too literally.

That produced a `0.0%` raw replay match rate even when both sides were describing the same intervention in different vocabularies. For example, `verification_step` and `verify answer before submitting` are semantically aligned even though they are not raw-string matches.

Replay now uses a canonical harness action ontology from `configs/settlement_datasets/harness_action_ontology.yaml`.

This lets replay distinguish:

- raw format mismatch
- semantic agreement
- ontology unknowns

The replay layer is now an interpretation surface rather than a raw substring check.

## How Would-Have-Fired Analysis Works

Each policy has a trigger specification:

| Trigger                                                   | Meaning                           | Evidence                            |
| --------------------------------------------------------- | --------------------------------- | ----------------------------------- |
| `error_count_gte: N`                                      | Record has N+ errors              | `error_count=actual>=N`             |
| `settlement_quality: X`                                   | Record has settlement quality X   | `settlement_quality=X`              |
| `step_count_gte: N` + `no_progress: true`                 | Long trace with no success        | `steps=actual>=N` + failure quality |
| `final_answer_action: true` + `prior_verification: false` | Final answer without testing      | No test in prior actions            |
| `early_specific_action: true` + `turn_index_lt: N`        | Jumped to action without analysis | Command at early turn               |
| `selection_action: true` + `prior_comparison: false`      | Selection without comparing       | Buy without analysis                |

The evaluator checks each trigger against each record. If the trigger matches, it records the trigger evidence, observed failure mode, observed settlement quality, confidence, fire timing, remaining turns, and recovery opportunity.

## How Counterfactual Assessment Works

For each would-fire event:

| Observed                                  | Counterfactual   | Rationale                             |
| ----------------------------------------- | ---------------- | ------------------------------------- |
| failure + matching failure mode           | `likely_helpful` | Policy addresses the observed failure |
| clean/recovered success + no failure mode | `likely_harmful` | Policy would block a successful path  |
| partial success / unknown                 | `uncertain`      | Ambiguous signal                      |
| trigger not met                           | `no_effect`      | Policy does not apply                 |

Every uncertain would-fire event includes `uncertainty_reason` and `uncertainty_evidence`. Current reasons include `missing_outcome_signal`, `insufficient_trace_context`, `policy_would_fire_too_late`, `policy_action_effect_not_observable_offline`, `ambiguous_failure_mode`, `weak_trigger_evidence`, `conflicting_settlement_evidence`, `no_recovery_opportunity`, and `unknown`.

## How Promotion Scoring Works

After evaluating all records, each policy receives a promotion score:

| Field                          | Meaning                                                                          |
| ------------------------------ | -------------------------------------------------------------------------------- |
| `would_fire_count`             | How many traces would trigger the policy                                         |
| `likely_helpful_count`         | Would-fire events where policy likely helps                                      |
| `likely_harmful_count`         | Would-fire events where policy likely harms                                      |
| `uncertainty_reason_distribution` | Count of uncertain fires by reason                                           |
| `fire_timing_distribution`     | Count of would-fire events by timing bucket                                     |
| `recovery_opportunity_count`   | Fires where post-trigger recovery remained                                      |
| `fires_after_failure_settled_count` | Fires based on already-settled failure state                               |
| `false_positive_rate_estimate` | Fraction of fires with medium/high FP risk                                       |
| `recommendation`               | keep_proposed / candidate_for_activation / refine / reject / needs_more_evidence |

### Promotion Rules

A policy can become `candidate_for_activation` only if:

- `likely_helpful_count >= 5`
- `likely_harmful_count == 0`
- `false_positive_rate_estimate <= 0.10`
- At least 2 datasets or 2 domains support it (unless intentionally domain-specific)

If harmful examples exist: `reject` or `refine`.
If false positives are high: `refine`.
If the policy never fires: `needs_more_evidence`.

## How False-Positive Risk Is Estimated

False-positive risk is estimated by checking whether a policy would fire on successful traces:

| Condition                                 | FP Risk  |
| ----------------------------------------- | -------- |
| clean/recovered success + no failure mode | `high`   |
| clean success + no failure mode           | `medium` |
| failure + matching failure mode           | `low`    |
| everything else                           | `low`    |

The `false_positive_rate_estimate` is the fraction of would-fire events with medium or high FP risk.

## How Metabolization Candidates Move

| Status        | Meaning                                             | Evidence Required                      |
| ------------- | --------------------------------------------------- | -------------------------------------- |
| `candidate`   | Pattern observed in at least one trace              | Initial mining                         |
| `repeated`    | Pattern observed in 3+ traces across datasets       | Cross-trace settlement support         |
| `tested`      | Shadow-mode evaluation supports the pattern         | Shadow evaluation shows likely_helpful |
| `metabolized` | Live harness activation proves repeated improvement | Live harness validation                |

### Why Metabolized Requires Live Evidence

Shadow-mode evaluation tests policies against historical data. It cannot prove that activating a policy in a live harness would actually improve agent behavior.

Live harness activation is the settlement event that metabolizes a pattern into a real capability. Without it, the pattern remains at `tested` — a validated affordance that has not yet been spent.

## Scripts

```bash
# Shadow evaluation
PYTHONPATH=. uv run python scripts/settlement_datasets/evaluate_policies_shadow.py \
  --min-confidence 0.0

# Eval replay
PYTHONPATH=. uv run python scripts/settlement_datasets/replay_policy_evals.py \
  --min-confidence 0.0

# Policy status update
PYTHONPATH=. uv run python scripts/settlement_datasets/update_policy_status.py

# Metabolization candidate update
PYTHONPATH=. uv run python scripts/settlement_datasets/update_metabolization_status.py
```

## Outputs

| Path                                                                          | Content                      |
| ----------------------------------------------------------------------------- | ---------------------------- |
| `data/settlement_datasets/policy_shadow_eval/policy_shadow_results.jsonl`     | Per-trace would-fire results |
| `data/settlement_datasets/policy_shadow_eval/policy_promotion_scores.jsonl`   | Per-policy promotion scores  |
| `data/settlement_datasets/policy_shadow_eval/policy_shadow_summary.csv`       | CSV summary                  |
| `data/settlement_datasets/policy_shadow_eval/eval_replay_results.jsonl`       | Eval replay results          |
| `data/settlement_datasets/policy_shadow_eval/eval_replay_summary.csv`         | Eval replay CSV              |
| `data/settlement_datasets/policy_helpfulness_adjudication/policy_shadow_results.jsonl` | Target-policy adjudication results |
| `data/settlement_datasets/policy_helpfulness_adjudication/policy_shadow_summary.csv` | Target-policy uncertainty/timing/recovery summary |
| `docs/policy-evidence-packs/`                                                 | Target-policy evidence packs |
| `policies/review/policy_status_recommendations.yaml`                          | Status recommendations       |
| `data/settlement_datasets/metabolization_candidates/candidates_updated.jsonl` | Updated candidates           |

## Semantic Replay Metrics

Replay now reports both raw and semantic agreement:

- `raw_match_rate` keeps the original literal comparison surface
- `semantic_match_rate` uses canonical action normalization with exact matches scored as `1.0` and partial family matches scored as `0.5`
- `partial_match_rate` reports how often replay found family-level but not exact action agreement
- unknown policy and eval behaviors remain explicit rather than hidden

Semantic replay is supporting evidence only. It should improve replay interpretation, but it does not override shadow helpful/harmful evidence or justify automatic activation.

## Guarded Activation Experiments

Guarded activation is narrower than global activation. It may add a soft checkpoint for one policy inside a controlled experiment, while preserving status boundaries:

- replay-only guarded evidence can support `tested_in_replay`
- live guarded evidence can support `candidate_for_activation`
- neither status is `globally_active`
- neither status is `metabolized`

The current guarded experiment is limited to `require_reflection_after_repeated_errors`.
