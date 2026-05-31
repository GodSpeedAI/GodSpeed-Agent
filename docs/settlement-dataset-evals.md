# Settlement Dataset Eval Suites

## How Eval Suites Are Built from Settlement Records

Eval suites are subsets of labeled settlement records organized by failure mode or settlement quality. Each suite contains traces that exhibit a specific behavioral pattern along with the expected harness behavior that would address it.

The `build_eval_suites.py` script:

1. Loads settlement records from all datasets.
2. Filters by confidence threshold (default 0.65).
3. For each suite definition, matches records by failure mode, settlement quality, or metabolization candidate presence.
4. Writes matched records as eval items to per-suite JSONL files.

## Available Eval Suites

| Suite | Filter | Expected Harness Behavior |
|---|---|---|
| `premature_closure` | failure_mode = premature_closure | Agent must verify answer before submitting |
| `tool_thrashing` | failure_mode = tool_thrashing | Agent must break tool loop and propose alternative approach |
| `failed_recovery` | failure_mode = failed_recovery | Agent must recognize failed recovery and escalate or reset |
| `direct_jump_failures` | failure_mode = representation_jump | Agent must use intermediate representation before action |
| `payment_spirals` | failure_mode = payment_spiral | Agent must recognize unproductive payment and trigger positive disintegration |
| `brittle_successes` | failure_mode = brittle_success | Agent must verify result robustness, not just surface correctness |
| `successful_recovery_patterns` | settlement_quality = recovered_success | Agent should apply similar recovery strategy when facing errors |
| `metabolization_candidates` | has metabolization_candidate label | Agent should recognize reusable pattern and apply it |

## Eval Item Schema

Each item in an eval suite contains:

```json
{
  "dataset": "string",
  "trace_id": "string",
  "domain": "string",
  "input_context": "string (summarized from affordance path actions)",
  "observed_failure_mode": "string | none",
  "expected_harness_behavior": "string",
  "settlement_criteria": "string",
  "confidence": "float",
  "evidence": {
    "settlement_quality": "string",
    "failure_modes": ["string"],
    "payment": {},
    "path_shape": "string"
  }
}
```

## Confidence Filtering

Only records with `outcome.confidence >= min_confidence` (default 0.65) are included in eval suites. This ensures:

- Eval items are based on reliably labeled traces.
- Low-confidence or `unknown` quality records do not pollute eval suites.
- The eval suite is a high-signal subset, not a comprehensive dump.

The threshold is configurable:

```bash
uv run python -m scripts.settlement_datasets.build_eval_suites --min-confidence 0.5
```

## Cross-Dataset Eval Construction

Eval suites are built across all loaded datasets. A single suite may contain items from AgentTrove, SWE-Gym, API-Bank, and WebShop. Cross-dataset evals are valuable because they test whether the harness handles a failure pattern consistently regardless of domain.

The `dataset` and `domain` fields on each eval item enable per-dataset analysis of eval results without building separate suites.

## Building Eval Suites

```bash
uv run python -m scripts.settlement_datasets.build_eval_suites --dataset all
uv run python -m scripts.settlement_datasets.build_eval_suites --dataset swegym --min-confidence 0.7
```

Output: `data/settlement_datasets/evals/{suite_name}.jsonl`

## Determinism

Eval suites are deterministic and reproducible. Running `build_eval_suites.py` on the same settlement input always produces the same output. The only source of variation is the confidence threshold and dataset selection.
