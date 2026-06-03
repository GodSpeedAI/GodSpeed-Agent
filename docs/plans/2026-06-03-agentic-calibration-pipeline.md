# Agentic Calibration Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a low-touch, GLM 5.1-supervised calibration pipeline that streams external agent trajectory datasets, normalizes them into proxy settlement records, reaches 500+ usable settlements, evaluates the cognitive model's scikit-learn provider, and writes evidence without letting external data become local capability proof.

**Architecture:** Reuse the existing settlement dataset adapter framework and run-scoped evidence surfaces. Deterministic Python scripts own streaming, normalization, confidence filtering, calibration-frame construction, sklearn evaluation, resumability, and evidence artifacts. GLM 5.1 acts only as an operator and exception handler: it starts the pipeline, monitors counts, inspects adapter failures, proposes patches when schemas drift, and stops when the configured usable-settlement target is reached.

**Tech Stack:** Python 3.11, Hugging Face `datasets` streaming, existing `scripts.settlement_datasets` adapters, YAML manifests, JSONL run artifacts, pandas calibration frames from `godspeed_nav.cognitive_model`, scikit-learn through `godspeed_nav.ml.SklearnPredictiveModelAdapter`, pytest, local run directories under `data/settlement_datasets/runs/`.

## Outcome Contract

The finished workflow should let an agent run one command:

```bash
uv run python -m scripts.settlement_datasets.run_calibration_pipeline \
  --manifest configs/settlement_datasets/calibration_sources.yaml \
  --run-id hf-calibration-001 \
  --target-usable-settlements 500 \
  --min-confidence 0.65 \
  --provider sklearn
```

The command should:

1. Read a manifest of external datasets.
2. Stream rows from Hugging Face or local fixtures.
3. Normalize rows through registered adapters.
4. Label and filter usable proxy settlements.
5. Stop once the target usable-settlement count is reached.
6. Export a run-scoped ledger and calibration frame.
7. Evaluate sklearn predictions against deterministic/heuristic baselines.
8. Write `summary.json`, `summary.md`, and a report under `docs/calibration-runs/`.

## Proof Language

External datasets must be classified as:

```text
external-proxy-settlement
```

They are valid for calibration experiments, baseline comparison, and model warm-starting. They are not local Godspeed settlement evidence and must not promote local capabilities, metabolization, or enterprise readiness by themselves.

## Existing Surfaces To Reuse

- `scripts/settlement_datasets/adapter_base.py` — adapter contract and JSONL helpers.
- `scripts/settlement_datasets/registry.py` — adapter registry.
- `scripts/settlement_datasets/ingest_dataset.py` — current single-dataset ingestion command.
- `scripts/settlement_datasets/run_scoped_paths.py` — run directories and summary helpers.
- `scripts/settlement_datasets/agenttrove_adapter.py` — existing AgentTrove adapter.
- `scripts/settlement_datasets/swegym_adapter.py` — existing SWE-Gym adapter.
- `godspeed_nav/cognitive_model.py` — calibration-frame builder and deterministic model functions.
- `godspeed_nav/ml.py` — sklearn provider and predictive extension orchestration.
- `docs/cognitive-model-computational-core-report.md` — proof state and thresholds.
- `docs/settlement-dataset-adapter-framework.md` — current adapter semantics.

## Dataset Priorities

Implement the manifest in this order:

1. `SWE-Gym/OpenHands-Sampled-Trajectories` — first because it has verifier-like `resolved` and `test_result` fields and 6k+ rows.
2. `open-thoughts/AgentTrove` — second because it is large and an adapter already exists.
3. `nebius/SWE-agent-trajectories` — third because it has 80k+ SWE-agent trajectories and explicit `target` labels, but needs a new adapter.
4. Existing small fixtures and already supported datasets — use for tests and held-out validation, not for volume.

## Task 1: Add Calibration Source Manifest

**Files:**
- Create: `configs/settlement_datasets/calibration_sources.yaml`
- Create: `tests/test_calibration_pipeline.py`

**Step 1: Write the failing test**

Create `tests/test_calibration_pipeline.py`:

```python
from pathlib import Path

import yaml


def test_calibration_sources_manifest_declares_priority_and_external_proxy_classification():
    path = Path("configs/settlement_datasets/calibration_sources.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert data["target_usable_settlements"] == 500
    assert data["settlement_classification"] == "external-proxy-settlement"
    assert data["min_confidence"] == 0.65

    names = [item["name"] for item in data["datasets"]]
    assert names[:3] == [
        "swegym_openhands",
        "agenttrove",
        "nebius_swe_agent",
    ]

    for source in data["datasets"]:
        assert source["source_uri"]
        assert source["adapter"]
        assert source["split"]
        assert source["max_rows"] > 0
        assert source["priority"] > 0
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py::test_calibration_sources_manifest_declares_priority_and_external_proxy_classification -q
```

Expected: fail because the manifest does not exist.

**Step 3: Add the manifest**

Create:

```yaml
target_usable_settlements: 500
min_confidence: 0.65
settlement_classification: external-proxy-settlement

stopping:
  stop_when_target_reached: true
  max_adapter_error_rate: 0.20
  require_success_and_failure_classes: true

datasets:
  - name: swegym_openhands
    source_uri: SWE-Gym/OpenHands-Sampled-Trajectories
    adapter: swegym_openhands
    split: train.raw
    max_rows: 3000
    priority: 1
    streaming: true

  - name: agenttrove
    source_uri: open-thoughts/AgentTrove
    adapter: agenttrove
    split: train
    max_rows: 5000
    priority: 2
    streaming: true

  - name: nebius_swe_agent
    source_uri: nebius/SWE-agent-trajectories
    adapter: nebius_swe_agent
    split: train
    max_rows: 5000
    priority: 3
    streaming: true
```

**Step 4: Run test**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py -q
```

Expected: pass.

**Step 5: Commit**

```bash
git add configs/settlement_datasets/calibration_sources.yaml tests/test_calibration_pipeline.py
git commit -m "feat: add calibration source manifest"
```

## Task 2: Add Hugging Face Streaming Helper

**Files:**
- Create: `scripts/settlement_datasets/hf_stream.py`
- Modify: `tests/test_calibration_pipeline.py`

**Step 1: Write the failing tests**

Add:

```python
from scripts.settlement_datasets.hf_stream import iter_limited, load_hf_stream


def test_iter_limited_stops_after_limit():
    rows = list(iter_limited(iter([{"id": 1}, {"id": 2}, {"id": 3}]), limit=2))
    assert rows == [{"id": 1}, {"id": 2}]


def test_load_hf_stream_is_lazy_and_patchable(monkeypatch):
    calls = []

    def fake_load_dataset(source_uri, split, streaming=True):
        calls.append((source_uri, split, streaming))
        return iter([{"id": "row-1"}])

    monkeypatch.setattr("scripts.settlement_datasets.hf_stream.load_dataset", fake_load_dataset)

    stream = load_hf_stream("repo/name", split="train")
    assert list(stream) == [{"id": "row-1"}]
    assert calls == [("repo/name", "train", True)]
```

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py -q -k "hf_stream or iter_limited"
```

Expected: fail because `hf_stream.py` does not exist.

**Step 3: Implement helper**

Create:

```python
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

try:
    from datasets import load_dataset
except ImportError:  # pragma: no cover - exercised by dependency tests if needed
    load_dataset = None  # type: ignore[assignment]


def require_datasets() -> None:
    if load_dataset is None:
        raise RuntimeError("datasets_dependency_required: install with uv sync")


def load_hf_stream(source_uri: str, split: str) -> Iterable[dict[str, Any]]:
    require_datasets()
    return load_dataset(source_uri, split=split, streaming=True)


def iter_limited(rows: Iterable[dict[str, Any]], limit: int | None) -> Iterator[dict[str, Any]]:
    for index, row in enumerate(rows):
        if limit is not None and index >= limit:
            return
        yield dict(row)
```

**Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py -q -k "hf_stream or iter_limited"
```

Expected: pass.

**Step 5: Commit**

```bash
git add scripts/settlement_datasets/hf_stream.py tests/test_calibration_pipeline.py
git commit -m "feat: add Hugging Face streaming helper"
```

## Task 3: Add SWE-Gym OpenHands Adapter

**Files:**
- Create: `scripts/settlement_datasets/swegym_openhands_adapter.py`
- Modify: `scripts/settlement_datasets/registry.py`
- Create: `tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl`
- Modify: `tests/test_calibration_pipeline.py`

**Step 1: Write fixture**

Create a two-line JSONL fixture with one resolved and one unresolved row:

```json
{"instance_id":"repo__issue-1","run_id":"run-1","resolved":true,"messages":[{"role":"user","content":"Fix failing tests"},{"role":"assistant","content":"Run pytest and patch code"},{"role":"tool","content":"pytest passed"}],"tools":[{"name":"bash"},{"name":"apply_patch"},{"name":"finish"}],"test_result":{"passed":true}}
{"instance_id":"repo__issue-2","run_id":"run-2","resolved":false,"messages":[{"role":"user","content":"Fix failing tests"},{"role":"assistant","content":"Run pytest repeatedly"},{"role":"tool","content":"pytest failed with AssertionError"}],"tools":[{"name":"bash"},{"name":"apply_patch"},{"name":"finish"}],"test_result":{"passed":false}}
```

**Step 2: Write failing tests**

Add:

```python
from scripts.settlement_datasets.registry import get_adapter, available_datasets


def test_swegym_openhands_adapter_registered_and_validates_fixture():
    assert "swegym_openhands" in available_datasets()
    adapter = get_adapter("swegym_openhands")
    fixture = Path("tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl")

    records = [adapter.to_settlement_record(raw) for raw in adapter.stream(input_path=str(fixture))]

    assert len(records) == 2
    assert records[0]["dataset"] == "swegym_openhands"
    assert records[0]["outcome"]["success"] is True
    assert records[1]["outcome"]["success"] is False
    assert all(adapter.validate_record(record) == [] for record in records)
```

**Step 3: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py::test_swegym_openhands_adapter_registered_and_validates_fixture -q
```

Expected: fail because the adapter is not registered.

**Step 4: Implement adapter**

Implement `SWEGymOpenHandsAdapter(SettlementDatasetAdapter)`.

Rules:

- `name = "swegym_openhands"`
- `domain = "code"`
- `source_uri = "SWE-Gym/OpenHands-Sampled-Trajectories"`
- `stream()` should use local `input_path` when provided; otherwise use `load_hf_stream(...)`.
- `extract_outcome()` maps `resolved: true` to `success: True`, `settlement_quality: clean_success`, confidence `0.9`.
- `resolved: false` maps to `success: False`, `settlement_quality: failure_with_signal`, confidence `0.8` when `test_result` exists.
- Payment proxies: message count, tool count, bash/tool mentions, error-like observations, elapsed steps.
- Metadata must include `settlement_classification: external-proxy-settlement`, `source_run_id`, and `raw_source_uri`.

**Step 5: Register adapter**

In `scripts/settlement_datasets/registry.py`, lazy-load and register:

```python
from scripts.settlement_datasets.swegym_openhands_adapter import SWEGymOpenHandsAdapter
register_adapter("swegym_openhands", SWEGymOpenHandsAdapter)
```

**Step 6: Run tests**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py tests/test_settlement_datasets.py -q
```

Expected: pass.

**Step 7: Commit**

```bash
git add scripts/settlement_datasets/swegym_openhands_adapter.py scripts/settlement_datasets/registry.py tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl tests/test_calibration_pipeline.py
git commit -m "feat: add SWE-Gym OpenHands settlement adapter"
```

## Task 4: Add Nebius SWE-Agent Adapter

**Files:**
- Create: `scripts/settlement_datasets/nebius_swe_agent_adapter.py`
- Modify: `scripts/settlement_datasets/registry.py`
- Create: `tests/fixtures/settlement_datasets/nebius_swe_agent/sample.jsonl`
- Modify: `tests/test_calibration_pipeline.py`

**Step 1: Write fixture**

Create one successful and one failed row with fields from the dataset card:

```json
{"instance_id":"repo__123","model_name":"swe-agent-test","target":true,"trajectory":"[{\"role\":\"system\",\"content\":\"agent\"},{\"role\":\"ai\",\"content\":\"edit file\"},{\"role\":\"user\",\"content\":\"tests passed\"}]","exit_status":"submitted","generated_patch":"diff --git a/file.py b/file.py","eval_logs":"PASS"}
{"instance_id":"repo__124","model_name":"swe-agent-test","target":false,"trajectory":"[{\"role\":\"system\",\"content\":\"agent\"},{\"role\":\"ai\",\"content\":\"edit file\"},{\"role\":\"user\",\"content\":\"tests failed\"}]","exit_status":"submitted","generated_patch":"diff --git a/file.py b/file.py","eval_logs":"FAIL AssertionError"}
```

**Step 2: Write failing test**

```python
def test_nebius_swe_agent_adapter_registered_and_validates_fixture():
    assert "nebius_swe_agent" in available_datasets()
    adapter = get_adapter("nebius_swe_agent")
    fixture = Path("tests/fixtures/settlement_datasets/nebius_swe_agent/sample.jsonl")

    records = [adapter.to_settlement_record(raw) for raw in adapter.stream(input_path=str(fixture))]

    assert len(records) == 2
    assert records[0]["outcome"]["success"] is True
    assert records[1]["outcome"]["success"] is False
    assert records[0]["payment"]["commands"] >= 0
    assert all(adapter.validate_record(record) == [] for record in records)
```

**Step 3: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py::test_nebius_swe_agent_adapter_registered_and_validates_fixture -q
```

Expected: fail because adapter is not registered.

**Step 4: Implement adapter**

Implement `NebiusSWEAgentAdapter`.

Rules:

- Parse `trajectory` when it is a JSON string; tolerate parse failure by using an empty list and recording evidence.
- `target` is the settlement success label.
- `eval_logs` supplies runnable feedback evidence.
- Payment counts should use trajectory length, AI/action turns, patch size, and error-like log count.
- Metadata must include `model_name`, `exit_status`, `settlement_classification: external-proxy-settlement`, and `raw_source_uri`.

**Step 5: Register adapter and run tests**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py tests/test_settlement_datasets.py -q
```

Expected: pass.

**Step 6: Commit**

```bash
git add scripts/settlement_datasets/nebius_swe_agent_adapter.py scripts/settlement_datasets/registry.py tests/fixtures/settlement_datasets/nebius_swe_agent/sample.jsonl tests/test_calibration_pipeline.py
git commit -m "feat: add Nebius SWE-agent settlement adapter"
```

## Task 5: Add Calibration Pipeline Orchestrator

**Files:**
- Create: `scripts/settlement_datasets/run_calibration_pipeline.py`
- Modify: `tests/test_calibration_pipeline.py`

**Step 1: Write failing tests**

Add tests for manifest loading and stop conditions:

```python
from scripts.settlement_datasets.run_calibration_pipeline import (
    CalibrationRunState,
    load_calibration_manifest,
    should_stop_for_target,
)


def test_load_calibration_manifest_orders_sources_by_priority():
    manifest = load_calibration_manifest("configs/settlement_datasets/calibration_sources.yaml")
    assert [source["name"] for source in manifest["datasets"]][:3] == [
        "swegym_openhands",
        "agenttrove",
        "nebius_swe_agent",
    ]


def test_should_stop_for_target_when_enough_usable_settlements():
    state = CalibrationRunState(target_usable_settlements=500)
    state.usable_settlements = 500
    assert should_stop_for_target(state) is True
```

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py -q -k "calibration_manifest or stop_for_target"
```

Expected: fail because orchestrator does not exist.

**Step 3: Implement orchestrator skeleton**

Create:

- `CalibrationRunState` dataclass with counts: scanned, normalized, usable, rejected, adapter_errors, dataset_counts.
- `load_calibration_manifest(path)` that validates required manifest fields and sorts datasets by priority.
- `should_stop_for_target(state)`.
- `run_pipeline(...)` that creates a `RunScope`, writes `run_manifest.json`, and iterates datasets.

At this step, it may use fixture/local input only. Full HF streaming comes in Task 6.

**Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py -q
```

Expected: pass.

**Step 5: Commit**

```bash
git add scripts/settlement_datasets/run_calibration_pipeline.py tests/test_calibration_pipeline.py
git commit -m "feat: add calibration pipeline orchestrator skeleton"
```

## Task 6: Implement Dataset Iteration, Filtering, And Resumable Outputs

**Files:**
- Modify: `scripts/settlement_datasets/run_calibration_pipeline.py`
- Modify: `tests/test_calibration_pipeline.py`

**Step 1: Write failing integration test with fixtures**

```python
def test_calibration_pipeline_processes_fixture_sources_until_target(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 2
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 10
    priority: 1
    streaming: false
""",
        encoding="utf-8",
    )

    result = run_pipeline(
        manifest_path=str(manifest),
        run_id="fixture-calibration",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=2,
        min_confidence=0.65,
        provider="disabled",
    )

    assert result["usable_settlements"] == 2
    assert (tmp_path / "run" / "settlements" / "swegym_openhands.jsonl").exists()
    assert (tmp_path / "run" / "summary.json").exists()
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py::test_calibration_pipeline_processes_fixture_sources_until_target -q
```

Expected: fail because `run_pipeline` does not process records.

**Step 3: Implement processing**

Pipeline behavior:

- For each source, resolve adapter by manifest `adapter`.
- If `input_path` exists, call `adapter.stream(input_path=...)`.
- Otherwise call adapter streaming with source URI and split fields. Adapter-specific implementation may use `hf_stream`.
- Convert raw row with `adapter.to_settlement_record`.
- Validate record.
- Set or preserve `metadata.settlement_classification = "external-proxy-settlement"`.
- Keep records where `outcome.confidence >= min_confidence` and `outcome.success is not None`.
- Write:
  - `raw/{dataset}.jsonl`
  - `normalized/{dataset}.jsonl`
  - `settlements/{dataset}.jsonl`
  - `summary.json`
  - `summaries/summary.md`
- Stop when target usable settlements is reached.

**Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py -q
```

Expected: pass.

**Step 5: Commit**

```bash
git add scripts/settlement_datasets/run_calibration_pipeline.py tests/test_calibration_pipeline.py
git commit -m "feat: process calibration sources into usable settlements"
```

## Task 7: Add Calibration Frame Export And Sklearn Evaluation

**Files:**
- Modify: `scripts/settlement_datasets/run_calibration_pipeline.py`
- Modify: `tests/test_calibration_pipeline.py`

**Step 1: Write failing test**

```python
def test_calibration_pipeline_writes_calibration_frame_and_model_metrics(tmp_path):
    # Reuse fixture manifest from previous test with target 2.
    result = run_pipeline(
        manifest_path="configs/settlement_datasets/calibration_sources.yaml",
        run_id="fixture-calibration",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=0,
        min_confidence=0.65,
        provider="disabled",
        dry_run=True,
    )

    assert "calibration_frame_path" in result
    assert "model_evaluation" in result
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py::test_calibration_pipeline_writes_calibration_frame_and_model_metrics -q
```

Expected: fail because frame/model outputs are missing.

**Step 3: Implement calibration transformation**

External adapter records do not have the runtime settlement `model_calibration` shape. Add a conversion function:

```python
def external_record_to_model_calibration(record: dict[str, Any]) -> dict[str, Any]:
    payment = record["payment"]
    outcome = record["outcome"]
    return {
        "id": f"{record['dataset']}:{record['task_id']}",
        "model_calibration": {
            "payment_predicted": {"steps": payment.get("elapsed_steps", 0)},
            "payment_actual": {
                "turns": payment.get("turns", 0),
                "tool_calls": payment.get("tool_calls", 0),
                "commands": payment.get("commands", 0),
                "errors": payment.get("error_count", 0),
            },
            "settlement_success": bool(outcome.get("success")),
            "settlement_score": 1.0 if outcome.get("success") else 0.0,
            "horizon_delta": 1.0 if outcome.get("success") else 0.0,
            "risk_estimate": min(1.0, payment.get("error_count", 0) / max(payment.get("elapsed_steps", 1), 1)),
            "debt_estimate": 0.0,
        },
        "metadata": {
            "settlement_classification": "external-proxy-settlement",
            "source_dataset": record["dataset"],
        },
    }
```

Use `godspeed_nav.cognitive_model.build_calibration_frame(...)` and write:

- `calibration/calibration_frame.csv`
- `calibration/model_calibration_records.jsonl`
- `calibration/model_evaluation.json`

If provider is `sklearn`, compare:

- deterministic baseline rate;
- heuristic provider predictions if useful;
- sklearn provider predictions when enough rows and both classes exist.

If provider cannot run because `uv sync --extra ml` was not used, record `sklearn_extra_required` in metrics and keep pipeline successful.

**Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py tests/test_computation.py -q
```

Expected: pass.

**Step 5: Commit**

```bash
git add scripts/settlement_datasets/run_calibration_pipeline.py tests/test_calibration_pipeline.py
git commit -m "feat: export calibration frame and model metrics"
```

## Task 8: Add CLI Entry Point And Resume Behavior

**Files:**
- Modify: `scripts/settlement_datasets/run_calibration_pipeline.py`
- Modify: `tests/test_calibration_pipeline.py`

**Step 1: Write failing CLI test**

Use `subprocess.run` with a fixture manifest:

```python
import subprocess


def test_calibration_pipeline_cli_runs_fixture_manifest(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 1
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 1
    priority: 1
    streaming: false
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "scripts.settlement_datasets.run_calibration_pipeline",
            "--manifest",
            str(manifest),
            "--run-id",
            "cli-fixture",
            "--output-run-dir",
            str(tmp_path / "run"),
            "--target-usable-settlements",
            "1",
            "--provider",
            "disabled",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "usable_settlements" in result.stdout
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py::test_calibration_pipeline_cli_runs_fixture_manifest -q
```

Expected: fail if CLI is missing.

**Step 3: Implement CLI**

Arguments:

- `--manifest`
- `--run-id`
- `--run-dir`
- `--input-run-dir`
- `--output-run-dir`
- `--target-usable-settlements`
- `--min-confidence`
- `--provider`
- `--resume`
- `--dry-run`

Resume rule:

- If `--resume` and run summary exists, load existing counts and continue only incomplete datasets.
- Do not duplicate records already present in `settlements/*.jsonl`.
- Keep implementation simple: use task IDs as de-duplication keys.

**Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py -q
```

Expected: pass.

**Step 5: Commit**

```bash
git add scripts/settlement_datasets/run_calibration_pipeline.py tests/test_calibration_pipeline.py
git commit -m "feat: add calibration pipeline CLI"
```

## Task 9: Add GLM 5.1 Calibration Operator Agent

**Files:**
- Create: `agents/calibration_operator.md`
- Modify: `tests/test_docs_alignment.py`
- Modify: `README.md`

**Step 1: Write failing docs test**

Add a docs alignment assertion:

```python
def test_calibration_operator_agent_documents_external_proxy_boundary():
    text = Path("agents/calibration_operator.md").read_text(encoding="utf-8")
    assert "GLM 5.1" in text
    assert "external-proxy-settlement" in text
    assert "must not promote local capabilities" in text
    assert "run_calibration_pipeline" in text
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_docs_alignment.py::test_calibration_operator_agent_documents_external_proxy_boundary -q
```

Expected: fail because the agent file does not exist.

**Step 3: Create operator agent**

`agents/calibration_operator.md` must include:

- Purpose: supervise calibration pipeline runs.
- Model: GLM 5.1.
- Command template.
- Allowed actions:
  - start/resume pipeline;
  - inspect run summary;
  - inspect adapter errors;
  - patch adapters only when deterministic tests fail;
  - write evidence report.
- Forbidden actions:
  - invent labels;
  - override confidence thresholds without explicit rationale;
  - count external-proxy settlements as local settlement;
  - promote capabilities or metabolization;
  - claim enterprise readiness from external data.
- Stop conditions:
  - target usable settlements reached;
  - adapter error rate exceeds manifest threshold;
  - only one class remains after filtering;
  - sklearn underperforms baseline.

**Step 4: Update README**

Add a short section near the computational model layer:

```markdown
## Calibration Pipeline

The calibration pipeline can stream external agent trajectory datasets into `external-proxy-settlement` records. A GLM 5.1 operator agent may run and monitor the pipeline, but deterministic scripts own labels and filtering. External proxy records calibrate models; they do not prove local capability.
```

**Step 5: Run tests**

Run:

```bash
uv run pytest tests/test_docs_alignment.py -q
```

Expected: pass.

**Step 6: Commit**

```bash
git add agents/calibration_operator.md README.md tests/test_docs_alignment.py
git commit -m "docs: add GLM calibration operator contract"
```

## Task 10: Add Evidence Report Generation

**Files:**
- Modify: `scripts/settlement_datasets/run_calibration_pipeline.py`
- Create directory on demand: `docs/calibration-runs/`
- Modify: `tests/test_calibration_pipeline.py`

**Step 1: Write failing test**

```python
def test_calibration_pipeline_writes_docs_report(tmp_path):
    result = run_pipeline(
        manifest_path=str(fixture_manifest_path),
        run_id="fixture-report",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=1,
        min_confidence=0.65,
        provider="disabled",
        report_dir=tmp_path / "docs",
    )

    report_path = Path(result["report_path"])
    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    assert "external-proxy-settlement" in text
    assert "usable settlements" in text
    assert "Proof Classification" in text
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py::test_calibration_pipeline_writes_docs_report -q
```

Expected: fail because report generation is missing.

**Step 3: Implement report generation**

Report path:

```text
docs/calibration-runs/{run_id}-report.md
```

Report sections:

- Date and run id.
- Manifest path.
- Dataset counts.
- Raw rows scanned.
- Normalized records.
- Usable settlements.
- Rejected records.
- Adapter errors.
- Success/failure class balance.
- Calibration frame path.
- Model evaluation summary.
- Proof classification: `external-proxy-calibration`.
- Explicit non-claims.
- Next move.

**Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py tests/test_docs_alignment.py -q
```

Expected: pass.

**Step 5: Commit**

```bash
git add scripts/settlement_datasets/run_calibration_pipeline.py tests/test_calibration_pipeline.py
git commit -m "feat: write calibration evidence reports"
```

## Task 11: Add Live Smoke Command Documentation

**Files:**
- Modify: `docs/settlement-dataset-adapter-framework.md`
- Modify: `docs/runbooks/configuration.md`
- Modify: `tests/test_docs_alignment.py`

**Step 1: Write failing docs test**

```python
def test_docs_include_calibration_pipeline_smoke_command():
    framework = Path("docs/settlement-dataset-adapter-framework.md").read_text(encoding="utf-8")
    config = Path("docs/runbooks/configuration.md").read_text(encoding="utf-8")
    assert "run_calibration_pipeline" in framework
    assert "--target-usable-settlements 500" in framework
    assert "external-proxy-settlement" in framework
    assert "model_provider: sklearn" in config
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_docs_alignment.py::test_docs_include_calibration_pipeline_smoke_command -q
```

Expected: fail until docs are updated.

**Step 3: Update docs**

Add:

```bash
uv sync --extra dev --extra ml
uv run python -m scripts.settlement_datasets.run_calibration_pipeline \
  --manifest configs/settlement_datasets/calibration_sources.yaml \
  --run-id hf-calibration-001 \
  --target-usable-settlements 500 \
  --min-confidence 0.65 \
  --provider sklearn
```

Document that Colab TPU is not useful for scikit-learn/pandas pipeline acceleration; use streaming and CPU.

**Step 4: Run docs tests**

Run:

```bash
uv run pytest tests/test_docs_alignment.py -q
```

Expected: pass.

**Step 5: Commit**

```bash
git add docs/settlement-dataset-adapter-framework.md docs/runbooks/configuration.md tests/test_docs_alignment.py
git commit -m "docs: document calibration pipeline operation"
```

## Task 12: Final Validation

**Files:**
- Modify if needed: `docs/calibration-runs/fixture-report.md`
- Modify: `CURRENT_STATE.md`

**Step 1: Run focused tests**

Run:

```bash
uv run pytest tests/test_calibration_pipeline.py tests/test_settlement_datasets.py tests/test_computation.py tests/test_docs_alignment.py -q
```

Expected: pass.

**Step 2: Run full suite**

Run:

```bash
uv run pytest -q
```

Expected: pass.

**Step 3: Run fixture pipeline**

Run:

```bash
uv run python -m scripts.settlement_datasets.run_calibration_pipeline \
  --manifest configs/settlement_datasets/calibration_sources.yaml \
  --run-id fixture-calibration-smoke \
  --output-run-dir data/settlement_datasets/runs/fixture-calibration-smoke \
  --target-usable-settlements 5 \
  --min-confidence 0.65 \
  --provider disabled \
  --dry-run
```

Expected: command exits 0 and writes summary/report artifacts without contacting Hugging Face.

**Step 4: Optional live smoke**

Only run if network and time are acceptable:

```bash
uv run python -m scripts.settlement_datasets.run_calibration_pipeline \
  --manifest configs/settlement_datasets/calibration_sources.yaml \
  --run-id hf-calibration-smoke \
  --target-usable-settlements 25 \
  --min-confidence 0.65 \
  --provider disabled
```

Expected: command exits 0 or writes a clear adapter/network error summary without corrupting run artifacts.

**Step 5: Update `CURRENT_STATE.md`**

Add a concise milestone entry:

- Calibration pipeline implemented.
- GLM 5.1 operator contract added.
- Fixture validation passed.
- Live HF smoke status.
- Proof classification: `external-proxy-calibration` if live smoke runs; otherwise `local-confidence`.

**Step 6: Commit**

```bash
git add CURRENT_STATE.md data/settlement_datasets/runs/fixture-calibration-smoke docs/calibration-runs
git commit -m "chore: validate calibration pipeline"
```

## GLM 5.1 Operating Prompt

Point GLM 5.1 at this plan and use this operator prompt:

```text
You are the Godspeed calibration operator for GLM 5.1.

Objective:
Run the calibration pipeline until it reaches the configured usable-settlement target or hits a documented stop condition.

Rules:
- Use docs/plans/2026-06-03-agentic-calibration-pipeline.md as the implementation plan.
- Deterministic scripts own labels, confidence, filtering, and model metrics.
- Do not invent labels.
- Do not lower confidence thresholds without writing a rationale.
- Do not count external-proxy-settlement records as local Godspeed settlement evidence.
- Do not promote capabilities, metabolization, enterprise readiness, or local runtime authority from external datasets.
- If an adapter fails because a schema changed, write or update a fixture, add a failing test, then patch the adapter.
- Stop when target usable settlements are reached, adapter error rate exceeds the manifest ceiling, only one outcome class remains, or sklearn underperforms baseline.

Primary command:
uv run python -m scripts.settlement_datasets.run_calibration_pipeline \
  --manifest configs/settlement_datasets/calibration_sources.yaml \
  --run-id hf-calibration-001 \
  --target-usable-settlements 500 \
  --min-confidence 0.65 \
  --provider sklearn

Required final output:
- Summarize raw rows scanned, normalized records, usable settlements, rejected records, adapter errors, class balance, sklearn metrics, baseline comparison, report path, and proof classification.
- Name the next move.
```

## Success Criteria

The implementation is done when:

- One command can run the pipeline from manifest to report.
- The pipeline can stop at 500 usable external-proxy settlements.
- Dataset artifacts are run-scoped and resumable.
- New adapters validate against fixtures.
- sklearn evaluation is attempted only when configured and data is sufficient.
- Reports clearly separate external proxy calibration from local settlement proof.
- GLM 5.1 has an agent contract that keeps it inside operator boundaries.

## Expected Proof Classification

- After fixture-only implementation: `local-confidence`.
- After live Hugging Face smoke with 25+ usable records: `external-proxy-calibration-smoke`.
- After 500+ usable external proxy records and model report: `external-proxy-calibration`.

Do not classify as `enterprise-shippable` or local capability proof.
