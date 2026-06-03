# Settlement Dataset Adapter Framework

## Purpose

The Settlement Dataset Adapter Framework converts settlement-bearing external datasets into reusable developmental memory for the Godspeed Agent Harness. Each dataset contains multi-step agent traces with runnable feedback. The adapters normalize these raw traces into canonical settlement records that the harness can mine for failure patterns, recovery behaviors, policy signals, and metabolization candidates.

The purpose is not to collect training examples. The purpose is to refine the harness by learning from settled and failed agent trajectories across diverse domains.

```
Raw trace -> Adapter -> Canonical settlement record -> Policy/Eval/Metabolization mining -> Improved harness
```

## Why These Datasets Are Settlement-Bearing

Each supported dataset contains traces that qualify as settlement records because they exhibit:

- **Multi-step actions:** Agents take sequential actions (commands, API calls, page interactions) that constitute payment-bearing affordance-path attempts.
- **Environment observations:** Every action produces observable feedback (terminal output, API responses, search results) that serves as settlement evidence.
- **Runnable feedback:** Environments provide deterministic feedback (test results, reward scores, constraint checks) that the harness can use for before/after state comparison.
- **Rewards and scores:** Each trace carries an outcome signal (resolved/not-resolved, reward value, test pass rate) that indicates settlement quality.
- **Tool output:** Tool responses, command output, and API response bodies provide the evidence surface for error-correction data.
- **Recovery behavior:** Failed actions followed by retries and corrections reveal the displacement field's actual affordance structure.
- **Cost proxies:** Turn counts, tool call counts, and step counts measure the payment dimension of each affordance-path attempt.

These properties mean each trace records a real settlement event: a desired direction, a payment-bearing affordance-path attempt, observable consequences, and an outcome. This is exactly what the harness needs to learn from.

## Why These Are Spendable Affordances

These datasets are not mere possibilities or potentials. They are spendable affordances because:

1. **Accessible:** Each adapter streams records from local JSONL files or HuggingFace datasets. No gatekeeping infrastructure beyond the adapter contract.
2. **Processable:** Every record follows the canonical schema after normalization. The harness can compare across datasets without custom per-dataset logic.
3. **In the displacement field:** Each trace records what actually happened (actions taken, feedback received, outcome observed), not what was intended or described.

A dataset that cannot be streamed, normalized, or validated is a potential, not an affordance. The adapter contract enforces this distinction.

## How Adapters Convert Raw Traces

### Adapter Contract

Every adapter implements `SettlementDatasetAdapter` with seven required methods:

| Method | Purpose |
|---|---|
| `stream()` | Yield raw records from the dataset source |
| `normalize_task()` | Extract desired direction from raw trace |
| `extract_actions()` | Extract action sequence from raw trace |
| `extract_observations()` | Extract environment feedback from raw trace |
| `extract_outcome()` | Extract success/reward/score from raw trace |
| `extract_payment()` | Extract cost proxy counts from raw trace |
| `infer_settlement_quality()` | Classify settlement quality from outcome and payment |
| `to_settlement_record()` | Assemble the canonical settlement record |
| `validate_record()` | Verify all required fields are present |

### Canonical Schema

Every adapter must produce a record with these top-level fields:

```
dataset, domain, task_id, source_uri, desired_direction, environment,
representational_state, payment, affordance_path, outcome, labels, metadata
```

See `docs/settlement-dataset-schema.md` for the full schema with field descriptions.

## How Outcome Feedback Becomes Error-Correction Data

Settlement records convert raw outcome signals into error-correction data through:

1. **Settlement quality classification:** Raw reward/success is mapped to one of seven quality levels (clean_success, recovered_success, partial_success, brittle_success, failure_with_signal, failure_without_signal, unknown). Each level indicates a different degree of settlement completeness.
2. **Failure mode detection:** Failed or partial settlements are tagged with specific failure modes (premature_closure, tool_thrashing, poor_localization, wrong_tool, constraint_miss, etc.). These identify what went wrong, not just that something went wrong.
3. **Evidence chains:** Every label carries an evidence list documenting why the label was applied. No label without evidence.

This transforms "reward=0.0" into "failure_with_signal, mode=poor_localization, evidence=[first_file_op_at_command=3, no_test_results]" which is actionable error-correction data.

## Why Evidence and Confidence Are Required

The framework enforces two rules:

1. **No label without evidence.** Every failure_mode, harness_policy_signal, and metabolization_candidate label must include an evidence list documenting the specific observations that justify the label. Labels without evidence are noise, not error-correction data.
2. **No confidence without reason.** Every outcome carries a confidence score derived from the strength and consistency of the supporting evidence. Confidence is not a feeling; it is a deterministic function of evidence quantity and quality.

Records below the confidence threshold (default 0.65) are excluded from policy mining and eval construction. Low-confidence records are retained in the ledger but not used to propose harness interventions.

## How Repeated Settlement Patterns Become Metabolization Candidates

When multiple traces from the same or different datasets exhibit the same successful or recovered pattern, the framework identifies them as metabolization candidates. The pattern must:

1. Appear in traces meeting the confidence threshold
2. Show consistent settlement quality (clean_success or recovered_success)
3. Share structural similarity in the affordance path

Candidates are not yet metabolized capabilities. They are patterns that have survived repeated settlement and are ready for harness validation. See `docs/metabolization-candidate-mining.md` for details.

## Pipeline Stages

### Stage 1: Ingest

Stream raw traces through the adapter and produce normalized settlement records.

```bash
uv run python -m scripts.settlement_datasets.ingest_dataset --dataset agenttrove --limit 100
uv run python -m scripts.settlement_datasets.ingest_dataset --dataset swegym
uv run python -m scripts.settlement_datasets.ingest_dataset --dataset all
```

Output: `data/settlement_datasets/raw_samples/{dataset}.jsonl`

### Stage 2: Profile

Generate summary statistics for each dataset.

```bash
uv run python -m scripts.settlement_datasets.profile_dataset --dataset all
```

Output: `data/settlement_datasets/profiles/{dataset}_profile.json`

### Stage 3: Label

Filter records by confidence threshold.

```bash
uv run python -m scripts.settlement_datasets.label_dataset --dataset all --min-confidence 0.65
```

Output: `data/settlement_datasets/settlements/{dataset}.jsonl`

### Stage 4: Export Ledger

Export labeled records to a queryable SQLite database.

```bash
uv run python -m scripts.settlement_datasets.export_ledger --dataset all
```

Output: `data/settlement_datasets/settlement_ledger.sqlite`

### Stage 5: Mine Policies

Mine cross-dataset harness policies from failure mode patterns.

```bash
uv run python -m scripts.settlement_datasets.mine_policies --dataset all --min-confidence 0.65 --min-supporting-traces 3
```

Output: `data/settlement_datasets/policies.yaml`

### Stage 6: Build Evals

Build eval suites organized by failure mode and settlement quality.

```bash
uv run python -m scripts.settlement_datasets.build_eval_suites --dataset all --min-confidence 0.65
```

Output: `data/settlement_datasets/evals/{suite_name}.jsonl`

### Stage 7: Mine Metabolization Candidates

Mine repeated successful patterns as metabolization candidates.

```bash
uv run python -m scripts.settlement_datasets.mine_metabolization_candidates --dataset all --min-confidence 0.65
```

Output: `data/settlement_datasets/metabolization_candidates/candidates.jsonl`

## How to Run the Full Pipeline

```bash
uv run python -m scripts.settlement_datasets.ingest_dataset --dataset all
uv run python -m scripts.settlement_datasets.profile_dataset --dataset all
uv run python -m scripts.settlement_datasets.label_dataset --dataset all --min-confidence 0.65
uv run python -m scripts.settlement_datasets.export_ledger --dataset all
uv run python -m scripts.settlement_datasets.mine_policies --dataset all
uv run python -m scripts.settlement_datasets.build_eval_suites --dataset all
uv run python -m scripts.settlement_datasets.mine_metabolization_candidates --dataset all
```

## How to Inspect Outputs

### Query the SQLite Ledger

```bash
uv run python -m scripts.settlement_datasets.query_ledger --db data/settlement_datasets/settlement_ledger.sqlite --query summarize_by_dataset --format json
uv run python -m scripts.settlement_datasets.query_ledger --query summarize_by_settlement_quality --format json
uv run python -m scripts.settlement_datasets.query_ledger --query summarize_by_failure_mode --format json
uv run python -m scripts.settlement_datasets.query_ledger --query cross_dataset_failure_modes --format json
uv run python -m scripts.settlement_datasets.query_ledger --query high_confidence_records --format table
uv run python -m scripts.settlement_datasets.query_ledger --query policy_signal_summary --format json
uv run python -m scripts.settlement_datasets.query_ledger --query metabolization_summary --format json
```

Available queries: `summarize_by_dataset`, `summarize_by_settlement_quality`, `summarize_by_failure_mode`, `summarize_by_domain`, `summarize_by_path_shape`, `high_confidence_records`, `low_confidence_records`, `cross_dataset_failure_modes`, `policy_signal_summary`, `metabolization_summary`.

### Inspect Profiles

```bash
cat data/settlement_datasets/profiles/agenttrove_profile.json | python -m json.tool
```

### Inspect Policies

```bash
cat data/settlement_datasets/policies.yaml
```

## How to Add a New Dataset Adapter

### Step 1: Create the Adapter Class

Create `scripts/settlement_datasets/{name}_adapter.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from scripts.settlement_datasets.adapter_base import (
    EMPTY_LABELS,
    EMPTY_OUTCOME,
    SettlementDatasetAdapter,
    make_empty_environment,
    make_empty_payment,
    make_empty_representational_state,
)


class MyDatasetAdapter(SettlementDatasetAdapter):
    name = "mydataset"
    domain = "code"  # or "api", "shopping", etc.
    source_uri = "hf:org/my-dataset"

    def stream(self, limit: int | None = None, **kwargs: Any) -> Iterator[dict[str, Any]]:
        input_path = Path(kwargs.get("input_path", "data/mydataset/raw_samples/sample.jsonl"))
        count = 0
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                yield json.loads(line)
                count += 1
                if limit is not None and count >= limit:
                    return

    def normalize_task(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "implementation",
            "description": raw.get("task_description", ""),
            "settlement_target": "task_completion",
        }

    def extract_actions(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        actions = []
        for idx, step in enumerate(raw.get("trajectory", [])):
            if step.get("role") == "assistant":
                actions.append({
                    "turn_index": idx,
                    "role": "assistant",
                    "action_type": step.get("action_type", "text"),
                    "content": step.get("content", ""),
                })
        return actions

    def extract_observations(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        observations = []
        for idx, step in enumerate(raw.get("trajectory", [])):
            if step.get("role") == "tool":
                observations.append({
                    "turn_index": idx,
                    "role": "tool",
                    "content": step.get("content", ""),
                })
        return observations

    def extract_outcome(self, raw: dict[str, Any]) -> dict[str, Any]:
        reward = raw.get("reward", 0.0)
        return {
            "success": reward >= 1.0,
            "reward": reward,
            "score": reward,
            "settlement_quality": "clean_success" if reward >= 1.0 else "failure",
            "confidence": 0.8,
            "evidence": [f"reward:{reward}"],
        }

    def extract_payment(self, raw: dict[str, Any]) -> dict[str, Any]:
        trajectory = raw.get("trajectory", [])
        return {
            "turns": len(trajectory),
            "tool_calls": sum(1 for e in trajectory if e.get("action_type") == "tool_call"),
            "commands": sum(1 for e in trajectory if e.get("action_type") == "command"),
            "page_actions": 0,
            "api_calls": 0,
            "elapsed_steps": len(trajectory),
            "error_count": 0,
            "estimated_complexity": "medium",
            "evidence": [f"steps:{len(trajectory)}"],
        }

    def infer_settlement_quality(self, raw: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
        reward = raw.get("reward", 0.0)
        if reward >= 1.0:
            return {"settlement_quality": "clean_success", "confidence": 0.9}
        return {"settlement_quality": "failure_with_signal", "confidence": 0.5}

    def to_settlement_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        task = self.normalize_task(raw)
        actions = self.extract_actions(raw)
        observations = self.extract_observations(raw)
        outcome = self.extract_outcome(raw)
        payment = self.extract_payment(raw)
        quality = self.infer_settlement_quality(raw, {})

        outcome["settlement_quality"] = quality["settlement_quality"]
        outcome["confidence"] = quality["confidence"]

        return {
            "dataset": self.name,
            "domain": self.domain,
            "task_id": raw.get("task_id", ""),
            "source_uri": self.source_uri,
            "desired_direction": task,
            "environment": {"type": "unknown", "has_runnable_feedback": False, "feedback_type": "unknown"},
            "representational_state": make_empty_representational_state(),
            "payment": payment,
            "affordance_path": {"actions": actions, "observations": observations},
            "outcome": outcome,
            "labels": dict(EMPTY_LABELS),
            "metadata": {},
        }
```

### Step 2: Register the Adapter

Add to `scripts/settlement_datasets/registry.py` in `_lazy_load()`:

```python
from scripts.settlement_datasets.mydataset_adapter import MyDatasetAdapter
register_adapter("mydataset", MyDatasetAdapter)
```

### Step 3: Create Test Fixtures

Create `tests/fixtures/settlement_datasets/mydataset/sample.jsonl` with representative traces.

### Step 4: Write Tests

Add tests to `tests/test_settlement_datasets.py` following the existing pattern (`TestMyDatasetAdapter`).

### Step 5: Update CLI Choices

Add the dataset name to the `--dataset` choices in `ingest_dataset.py`, `label_dataset.py`, `profile_dataset.py`, `export_ledger.py`, `mine_policies.py`, `build_eval_suites.py`, and `mine_metabolization_candidates.py`.

## Dataset Domains

### Code Domain

| Dataset | Source | Description |
|---|---|---|
| **AgentTrove** | open-thoughts/AgentTrove (HuggingFace) | ~1.7M agentic traces from code_contests, codeforces, freelancer, nl2bash, staqc, swesmith, r2egym. Multi-step terminal interaction traces with JSON-structured assistant output. |
| **SWE-Gym** | SWE-Gym | Code repository task traces with issue descriptions, trajectory of analysis and command steps, and test result outcomes. Environment provides runnable test feedback. |

### API Domain

| Dataset | Source | Description |
|---|---|---|
| **API-Bank** | API-Bank | API call task traces with instruction, available API definitions, expected call sequences, and trajectory of API calls and responses. Environment provides structured API response feedback. |

### Shopping Domain

| Dataset | Source | Description |
|---|---|---|
| **WebShop** | WebShop | Shopping task traces with instruction, constraints, trajectory of search/click/buy actions, and reward based on constraint satisfaction. Environment provides state-check feedback. |

## Future Adapters (Not Yet Implemented)

The following datasets are documented as future adapter targets. They are not implemented and should not be referenced in code or CLI choices until an adapter is built:

- **OSWorld** — Full desktop environment interaction traces with GUI actions and application feedback.
- **Mind2Web** — Web navigation traces with HTML DOM interaction and element-level feedback.
- **SWE-Bench** — Software engineering benchmark with repository-level task instances and test-based evaluation.
- **SWE-smith** — Synthetic software engineering task traces generated for training and evaluation.

Each future adapter will follow the same contract and produce canonical settlement records. The adapter framework is designed to accommodate new domains without structural changes.

## Testing

All tests use local fixtures and do not require network access:

```bash
uv run pytest tests/test_settlement_datasets.py -v
```

## Constraints

- Does not require downloading full datasets; adapters stream from local fixtures or samples.
- Does not silently activate generated harness policies.
- Does not assume reward alone equals good trace quality.
- Does not embed raw traces before labeling.
- Prefers deterministic heuristics over ML-backed labeling.
- Each pipeline stage is independently runnable.
- Outputs are reproducible from the same input.
- Cross-dataset operations use the canonical schema, not adapter-specific fields.

## Calibration Pipeline

The calibration pipeline streams external agent trajectory datasets into `external-proxy-settlement` records for model calibration. It does not prove local capability.

```bash
uv sync --extra dev --extra ml
uv run python -m scripts.settlement_datasets.run_calibration_pipeline \
  --manifest configs/settlement_datasets/calibration_sources.yaml \
  --run-id hf-calibration-001 \
  --target-usable-settlements 500 \
  --min-confidence 0.65 \
  --provider sklearn
```

All imported records carry the `external-proxy-settlement` classification. They are valid for calibration experiments, baseline comparison, and model warm-starting only. They must not promote local capabilities, metabolization, or enterprise readiness.

Colab TPU is not useful for scikit-learn/pandas pipeline acceleration; use streaming and CPU.
