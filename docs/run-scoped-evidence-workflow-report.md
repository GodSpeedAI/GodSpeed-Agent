# Run-Scoped Evidence Workflow Report

## Scope

This pass added workflow plumbing for reproducible evidence collection across the settlement-dataset pipeline. It did not change policy logic, activation thresholds, adapters, or metabolization promotion rules.

## Implemented Surface

Added a shared run-scoped path layer and wrapper:

- `scripts/settlement_datasets/run_scoped_paths.py`
- `scripts/settlement_datasets/run_evidence_pipeline.py`

Added target-profile config:

- `configs/settlement_datasets/targeted_trace_queries.yaml`

Standardized run-scoped flags across these CLIs:

- `ingest_dataset.py`
- `profile_dataset.py`
- `label_dataset.py`
- `export_ledger.py`
- `mine_policies.py`
- `evaluate_policies_shadow.py`
- `replay_policy_evals.py`
- `update_policy_status.py`
- `update_metabolization_status.py`
- `mine_metabolization_candidates.py`
- `replay_live_shadow_from_traces.py`

## Result

Every pass can now write to a stable run surface under `data/settlement_datasets/runs/<run-id>/`.

The wrapper records a manifest and summary for both dry-run and real runs. Later phases can consume a prior run with `--input-run-dir` and emit a fresh replay or adjudication surface with `--output-run-dir`.

The initial target profile `reflection_second_unresolved_error` is now configuration-backed. In this pass it records targeted collection intent and query metadata; it does not yet change adapter retrieval behavior.

## Smoke Validation

Executed:

```bash
uv run python -m scripts.settlement_datasets.run_evidence_pipeline \
  --run-id smoke-run \
  --dataset agenttrove \
  --limit 10 \
  --min-confidence 0.65 \
  --target-profile reflection_second_unresolved_error \
  --dry-run
```

Artifacts written:

- `data/settlement_datasets/runs/smoke-run/run_manifest.json`
- `data/settlement_datasets/runs/smoke-run/summaries/summary.json`
- `data/settlement_datasets/runs/smoke-run/summaries/summary.md`

Observed smoke result:

- `run_id=smoke-run`
- dataset `agenttrove`
- target profile recorded as `reflection_second_unresolved_error`
- all stage commands were planned
- no records were ingested because the run was dry-run
- `policy_activation_count=0`
- `policy_fires=0`
- recommended next move points to rerunning against real traces or a later stage using `--input-run-dir`

## Verification

Focused new workflow tests:

- `uv run pytest tests/test_run_scoped_evidence_workflow.py -q` -> `8 passed`

Adjacent existing settlement-dataset validation:

- `uv run pytest tests/test_settlement_datasets.py tests/test_policy_shadow_eval.py tests/test_live_shadow_policy_eval.py -q` -> `137 passed`

## Boundaries Preserved

- No policy activation was introduced.
- No threshold was lowered.
- No metabolization candidate was promoted.
- No new dataset adapter was added.
- No RuVector dependency was introduced.

## Next Payment-Reducing Move

Use the wrapper for the next real evidence pass so targeted profile intent, stage boundaries, and adjudication outputs all settle into a single reusable run directory instead of being reconstructed from shell history and manual module calls.
