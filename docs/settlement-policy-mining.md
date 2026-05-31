# Settlement Policy Mining

## How Policies Are Mined from Failure Mode Patterns

Policy mining converts labeled settlement records into candidate harness policies. The process:

1. **Aggregate failure modes:** Count failure mode occurrences across all records meeting the confidence threshold, grouped by dataset.
2. **Match templates:** Each policy template specifies a set of failure modes it addresses. The miner sums supporting traces across all matching failure modes.
3. **Filter by support:** Only policies with at least `min_supporting_traces` supporting traces (default 3) are included in the output.
4. **Assemble evidence:** Each policy includes supporting trace count, dataset count, example trace IDs, confidence distribution, and proportion.

The miner operates across all datasets simultaneously, enabling cross-dataset policy discovery. A failure mode observed in both AgentTrove and SWE-Gym produces a policy with stronger cross-dataset evidence than one observed in only a single dataset.

## Confidence Thresholds

**Default: 0.65**

Only records with `outcome.confidence >= min_confidence` are included in policy mining. This excludes:

- Records with `unknown` settlement quality
- Records where the adapter could not determine outcome with sufficient certainty
- Records with `failure_without_signal` (typically confidence < 0.5)

The threshold is configurable via `--min-confidence`:

```bash
uv run python -m scripts.settlement_datasets.mine_policies --min-confidence 0.5
```

Lower thresholds include more records but increase noise. Higher thresholds are more selective but may miss valid patterns in smaller datasets.

## Minimum Supporting Traces

**Default: 3**

A policy must have at least `min_supporting_traces` records with matching failure modes to be included. This prevents single-trace anomalies from generating policies.

The threshold is configurable via `--min-supporting-traces`:

```bash
uv run python -m scripts.settlement_datasets.mine_policies --min-supporting-traces 5
```

## Cross-Dataset Aggregation

Policies aggregate evidence across all loaded datasets. The `evidence.supporting_dataset_count` field shows how many datasets contributed traces to the policy. Cross-dataset policies are stronger signals because the failure pattern is not dataset-specific.

Example output:

```yaml
- id: search_before_patch
  evidence:
    supporting_trace_count: 12
    supporting_dataset_count: 2
    supporting_datasets: ["agenttrove", "swegym"]
```

A policy supported by traces from multiple datasets indicates a domain-general failure pattern that the harness should address. A policy supported by only one dataset may be dataset-specific noise.

## Policy Schema

Each policy in the output YAML contains:

```yaml
id: string                          # Unique policy identifier
trigger:                            # Condition that activates the policy
  condition_key: condition_value
action:                             # Required intervention
  require_operator: string          # What the harness must require
  block: string                     # What the harness must block
rationale: string                   # Why this policy improves settlement
evidence:                           # Supporting evidence
  supporting_trace_count: int       # Total traces with matching failure modes
  supporting_dataset_count: int     # Number of datasets contributing traces
  supporting_datasets: [string]     # List of contributing dataset names
  total_traces_analyzed: int        # Total records processed
  example_trace_ids: [string]       # Up to 5 example trace IDs
  observed_failure_patterns: [string] # Failure modes this policy addresses
  proportion: float                 # supporting_trace_count / total_traces_analyzed
  avg_label_confidence: float       # Average confidence of supporting traces
  confidence_distribution:          # Min/max/mean confidence
  meets_min_supporting_count: bool  # Whether threshold is met
risk:                               # Risk assessment
  false_positive_concern: string    # Known false positive risk
  recommended_review: string        # Review recommendation
activation_status: proposed         # Always "proposed" initially
active_by_default: false            # Always false
```

## Why Policies Default to "proposed"

No generated policy is active by default. Every policy has `activation_status: "proposed"` and `active_by_default: false`. This is because:

1. **Deterministic heuristics have false positive risk.** The failure mode detection that drives policy mining uses rule-based pattern matching, not validated models. Some misclassification is expected.
2. **Correlation is not causation.** A failure mode appearing in many traces does not mean the proposed intervention will fix it.
3. **Settlement must be validated, not declared.** A policy becomes real only after it is activated, tested against eval suites, and shown to improve settlement quality in repeated runs.

Policies must be reviewed by a human operator, evaluated against the evidence, and explicitly activated in the harness configuration.

## Available Policy Templates

| ID | Failure Modes Addressed | Trigger | Required Action |
|---|---|---|---|
| `require_reflection_after_repeated_errors` | tool_thrashing, payment_spiral, failed_recovery | error_count >= 3 | Require reflection operator, block next action until revised plan |
| `search_before_patch` | poor_localization, bad_patch, wrong_tool, wrong_arguments | Edit or API call without prior search | Require search or inspect, block direct edit without context |
| `compare_constraints_before_selection` | constraint_miss, premature_choice, premature_closure | Selection without prior comparison | Require constraint verification, block selection without comparison |
| `inspect_api_schema_before_call` | wrong_tool, wrong_arguments, missing_precondition | API call without prior schema check | Require schema inspection, block API call without schema |
| `reset_plan_after_payment_spiral` | payment_spiral, over_search | step_count >= 8 with no progress | Require positive disintegration, suggest terminate or reset |
| `test_before_final_answer` | brittle_success, premature_closure | Final answer without prior verification | Require verification step, block answer without test |
| `require_explicit_settlement_for_failure` | failed_recovery, test_failure | settlement_quality = failure_with_signal | Require failure analysis, record error-correction signal |
| `prevent_premature_concretion` | premature_concretion, premature_closure | Early specific action (turn_index < 3) | Require intermediate representation, block direct jump |

## Running Policy Mining

```bash
uv run python -m scripts.settlement_datasets.mine_policies --dataset all
uv run python -m scripts.settlement_datasets.mine_policies --dataset swegym --min-confidence 0.7
```

## Shadow Evaluation

Mined policies remain `proposed` until shadow-mode evaluation tests them against settlement records. See `docs/policy-shadow-evaluation.md` for details.

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/evaluate_policies_shadow.py --min-confidence 0.0
PYTHONPATH=. uv run python scripts/settlement_datasets/update_policy_status.py
```

Policies can move from `proposed` to `candidate_for_activation` only after shadow evaluation shows they are helpful (5+ traces), not harmful (0 harmful traces), and have low false-positive risk (<=10%). No policy is activated automatically.

Output: `data/settlement_datasets/policies.yaml`
