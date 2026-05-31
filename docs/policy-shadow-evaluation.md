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
→ live activation experiment (real settlement)
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

No LLM calls are needed. This is deterministic rule replay against historical data.

## How Would-Have-Fired Analysis Works

Each policy has a trigger specification:

| Trigger | Meaning | Evidence |
|---|---|---|
| `error_count_gte: N` | Record has N+ errors | `error_count=actual>=N` |
| `settlement_quality: X` | Record has settlement quality X | `settlement_quality=X` |
| `step_count_gte: N` + `no_progress: true` | Long trace with no success | `steps=actual>=N` + failure quality |
| `final_answer_action: true` + `prior_verification: false` | Final answer without testing | No test in prior actions |
| `early_specific_action: true` + `turn_index_lt: N` | Jumped to action without analysis | Command at early turn |
| `selection_action: true` + `prior_comparison: false` | Selection without comparing | Buy without analysis |

The evaluator checks each trigger against each record. If the trigger matches, it records the trigger evidence, observed failure mode, observed settlement quality, and confidence.

## How Counterfactual Assessment Works

For each would-fire event:

| Observed | Counterfactual | Rationale |
|---|---|---|
| failure + matching failure mode | `likely_helpful` | Policy addresses the observed failure |
| clean/recovered success + no failure mode | `likely_harmful` | Policy would block a successful path |
| partial success / unknown | `uncertain` | Ambiguous signal |
| trigger not met | `no_effect` | Policy does not apply |

## How Promotion Scoring Works

After evaluating all records, each policy receives a promotion score:

| Field | Meaning |
|---|---|
| `would_fire_count` | How many traces would trigger the policy |
| `likely_helpful_count` | Would-fire events where policy likely helps |
| `likely_harmful_count` | Would-fire events where policy likely harms |
| `false_positive_rate_estimate` | Fraction of fires with medium/high FP risk |
| `recommendation` | keep_proposed / candidate_for_activation / refine / reject / needs_more_evidence |

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

| Condition | FP Risk |
|---|---|
| clean/recovered success + no failure mode | `high` |
| clean success + no failure mode | `medium` |
| failure + matching failure mode | `low` |
| everything else | `low` |

The `false_positive_rate_estimate` is the fraction of would-fire events with medium or high FP risk.

## How Metabolization Candidates Move

| Status | Meaning | Evidence Required |
|---|---|---|
| `candidate` | Pattern observed in at least one trace | Initial mining |
| `repeated` | Pattern observed in 3+ traces across datasets | Cross-trace settlement support |
| `tested` | Shadow-mode evaluation supports the pattern | Shadow evaluation shows likely_helpful |
| `metabolized` | Live harness activation proves repeated improvement | Live harness validation |

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

| Path | Content |
|---|---|
| `data/settlement_datasets/policy_shadow_eval/policy_shadow_results.jsonl` | Per-trace would-fire results |
| `data/settlement_datasets/policy_shadow_eval/policy_promotion_scores.jsonl` | Per-policy promotion scores |
| `data/settlement_datasets/policy_shadow_eval/policy_shadow_summary.csv` | CSV summary |
| `data/settlement_datasets/policy_shadow_eval/eval_replay_results.jsonl` | Eval replay results |
| `data/settlement_datasets/policy_shadow_eval/eval_replay_summary.csv` | Eval replay CSV |
| `policies/review/policy_status_recommendations.yaml` | Status recommendations |
| `data/settlement_datasets/metabolization_candidates/candidates_updated.jsonl` | Updated candidates |
