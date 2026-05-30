# AgentTrove Settlement Trace Miner

## Purpose

AgentTrove is treated as an external settlement database for refining the agent harness. Each trace is a developmental memory unit: a record of desired direction, representational state, payment, affordance-path attempt, tool/action sequence, outcome, settlement feedback, error correction, and possible metabolization.

The primary purpose is not to collect training examples. The purpose is to refine the harness by learning from settled and failed agent trajectories.

```
Raw trace -> Normalized trace -> Settlement record -> Failure mode / Recovery pattern -> Harness policy -> Eval suite -> Improved harness
```

## Why AgentTrove as Settlement Memory

AgentTrove contains approximately 1.7M agentic traces from diverse sources (swesmith, codeforces, r2egym, nl2bash, etc.). Rather than treating it primarily as SFT fuel, we treat each trace as:

- A record of a desired direction and the agent's attempt to reach it
- Evidence of payment (turns, tool calls, commands, errors) and settlement (success/failure)
- A potential source of failure-mode signals and recovery patterns
- Material for generating harness policies and evaluation suites

## Raw Field to Cognitive OS Mapping

| AgentTrove Field | Cognitive OS Concept |
|---|---|
| user task / prompt | DesiredDirection |
| system prompt / constraints | Horizon boundary |
| assistant reasoning/actions | AffordancePath attempt |
| tool calls / shell commands | Payment-bearing actions |
| tool output / command output / errors | Settlement feedback |
| reward | Coarse outcome signal |
| full trajectory | DevelopmentalMemoryUnit |
| repeated successful action pattern | MetabolizationCandidate |
| repeated failure pattern | HarnessPolicySignal |

## Phases

### Phase 1: Streaming Ingestion and Profiling

Stream AgentTrove, sample traces, normalize message turns, preserve metadata, and produce trajectory profiles.

```bash
python scripts/agenttrove/ingest_agenttrove.py --max-traces 100 --output data/agenttrove/raw_samples/sample.jsonl
python scripts/agenttrove/profile_traces.py --input data/agenttrove/raw_samples/sample.jsonl
```

Outputs:
- `data/agenttrove/raw_samples/sample.jsonl` - Normalized traces
- `data/agenttrove/profiles/trace_profile.jsonl` - Per-trace profiles
- `data/agenttrove/profiles/source_summary.csv` - Source-level summary

### Phase 2: Cognitive OS Settlement Labeling

Convert normalized traces into settlement records using deterministic labels.

```bash
python scripts/agenttrove/label_settlements.py --input data/agenttrove/raw_samples/sample.jsonl
```

Outputs:
- `data/agenttrove/settlements/settlement_traces.jsonl` - Labeled settlement records

### Phase 3: SQLite Settlement Ledger

Export labeled records into a queryable SQLite database.

```bash
python scripts/agenttrove/export_sqlite.py --input data/agenttrove/settlements/settlement_traces.jsonl --raw data/agenttrove/raw_samples/sample.jsonl
python scripts/agenttrove/query_ledger.py --db data/agenttrove/settlement_ledger.sqlite --query summarize_by_source
```

### Phase 4: Harness Policy Mining

Mine labeled settlement records for concrete harness policies.

```bash
python scripts/agenttrove/mine_harness_policies.py --input data/agenttrove/settlements/settlement_traces.jsonl
```

Output: `policies/generated/agenttrove_harness_policies.yaml`

### Phase 5: Evaluation Suite Generation

Create eval subsets for harness regression testing.

```bash
python scripts/agenttrove/build_eval_suites.py --input data/agenttrove/settlements/settlement_traces.jsonl
```

Output: `evals/agenttrove/*.jsonl` - Per-failure-mode eval suites

### Phase 6: Optional ShareGPT SFT Export

Export clean successful traces for future training. Gated by settlement labels.

```bash
python scripts/agenttrove/export_sharegpt_sft.py --settlements data/agenttrove/settlements/settlement_traces.jsonl --raw data/agenttrove/raw_samples/sample.jsonl
```

## Rebuilding from Scratch

```bash
rm -rf data/agenttrove/raw_samples/*.jsonl data/agenttrove/profiles/* data/agenttrove/settlements/* data/agenttrove/sft/* policies/generated/*.yaml evals/agenttrove/*.jsonl

python scripts/agenttrove/ingest_agenttrove.py --max-traces 100
python scripts/agenttrove/profile_traces.py
python scripts/agenttrove/label_settlements.py
python scripts/agenttrove/export_sqlite.py --raw data/agenttrove/raw_samples/sample.jsonl
python scripts/agenttrove/mine_harness_policies.py
python scripts/agenttrove/build_eval_suites.py
```

## Testing

All tests use local fixtures and do not require network access:

```bash
uv run pytest tests/test_agenttrove.py -v
```

## Constraints

- Does not require full AgentTrove download
- Does not silently activate generated harness policies
- Does not assume reward alone equals good trace quality
- Does not embed raw traces before labeling
- Prefers deterministic heuristics first
- Each phase is independently runnable
- Outputs are reproducible
