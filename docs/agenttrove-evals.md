# AgentTrove Evaluation Suites

## Overview

Eval suites are subsets of labeled settlement traces organized by failure mode. Each suite contains traces that exhibit a specific failure pattern along with the expected harness behavior that would address it.

## Suite Files

Suites are written to `evals/agenttrove/*.jsonl`:

| Suite | Failure Mode | Expected Harness Behavior |
|---|---|---|
| `premature_closure.jsonl` | premature_closure | require reflection |
| `tool_thrashing.jsonl` | tool_thrashing | require revised plan |
| `failed_recovery.jsonl` | failed_recovery | require reflection |
| `direct_jump_failures.jsonl` | representation_jump | route through intermediate state |
| `payment_spirals.jsonl` | payment_spiral | reset plan |
| `brittle_successes.jsonl` | brittle_success | require settlement evidence |
| `successful_recovery_patterns.jsonl` | (recovered_success) | record as metabolization candidate |

## Using Eval Suites

### Regression Testing

Use eval suites to verify that harness policy changes correctly handle known failure patterns:

1. Load the eval suite for a failure mode
2. For each eval item, verify the expected harness behavior is triggered
3. Verify settlement criteria are met

### Manual Inspection

```bash
cat evals/agenttrove/tool_thrashing.jsonl | python -m json.tool --no-ensure-ascii
```

### Building Suites

```bash
python scripts/agenttrove/build_eval_suites.py --input data/agenttrove/settlements/settlement_traces.jsonl
```

## Eval Item Schema

Each item contains:

- `trace_id` - The source trace identifier
- `source` - Dataset source
- `input_context` - Summary of the trace context
- `observed_failure_mode` - The detected failure mode
- `expected_harness_behavior` - What the harness should do
- `settlement_criteria` - What constitutes successful handling
- `evidence` - Settlement quality, failure modes, payment, path shape

## Determinism

Eval suites are deterministic and reproducible. Running `build_eval_suites.py` on the same settlement input always produces the same output.
