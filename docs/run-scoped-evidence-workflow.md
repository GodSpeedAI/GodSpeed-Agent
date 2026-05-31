# Run-Scoped Evidence Workflow

## Purpose

The settlement-dataset pipeline now supports a first-class run-scoped evidence surface so evidence accumulation, shadow evaluation, replay, adjudication, and metabolization review can be rerun without manual module calls.

The root wrapper is:

- `python -m scripts.settlement_datasets.run_evidence_pipeline`

This workflow lowers payment by giving every evidence pass a stable directory, stable defaults for later stages, and a run manifest that records what was asked for and what artifacts were written.

## Run Surface

Default run surfaces live under:

- `data/settlement_datasets/runs/<run-id>/`

Each run surface contains these stage directories:

- `raw/`
- `normalized/`
- `profiles/`
- `settlements/`
- `ledger/`
- `policies/`
- `shadow/`
- `replay/`
- `adjudication/`
- `metabolization/`
- `summaries/`

The run root also contains `run_manifest.json`.

## Shared CLI Flags

The settlement-dataset CLIs now share these run-scoped flags:

- `--run-id`
- `--run-dir`
- `--input-run-dir`
- `--output-run-dir`

The pipeline wrapper also supports:

- `--target-profile`
- `--target-profile-config`
- `--start-stage`
- `--end-stage`
- `--dry-run`
- `--skip-live-shadow`

`--run-dir` uses the same run surface for both input and output. `--input-run-dir` plus `--output-run-dir` lets a later pass read an older run while writing a fresh adjudication or replay surface.

## Typical Commands

Create a new run-scoped evidence surface:

```bash
uv run python -m scripts.settlement_datasets.run_evidence_pipeline \
  --run-id evidence-pass-001 \
  --dataset agenttrove \
  --limit 100 \
  --min-confidence 0.65
```

Record a targeted profile for a later focused pass:

```bash
uv run python -m scripts.settlement_datasets.run_evidence_pipeline \
  --run-id reflection-pass \
  --dataset agenttrove \
  --limit 200 \
  --min-confidence 0.65 \
  --target-profile reflection_second_unresolved_error
```

Dry-run the full workflow without ingesting traces:

```bash
uv run python -m scripts.settlement_datasets.run_evidence_pipeline \
  --run-id smoke-run \
  --dataset agenttrove \
  --limit 10 \
  --min-confidence 0.65 \
  --target-profile reflection_second_unresolved_error \
  --dry-run
```

Rerun from an existing run surface starting at shadow evaluation:

```bash
uv run python -m scripts.settlement_datasets.run_evidence_pipeline \
  --dataset agenttrove \
  --input-run-dir data/settlement_datasets/runs/evidence-pass-001 \
  --output-run-dir data/settlement_datasets/runs/evidence-pass-001-shadow-rerun \
  --start-stage shadow-eval \
  --end-stage summary \
  --min-confidence 0.65
```

Rerun a single stage directly with the stage CLI:

```bash
uv run python -m scripts.settlement_datasets.replay_policy_evals \
  --input-run-dir data/settlement_datasets/runs/evidence-pass-001 \
  --output-run-dir data/settlement_datasets/runs/evidence-pass-001-replay-rerun \
  --min-confidence 0.65
```

## Artifacts

`run_manifest.json` records:

- `run_id`
- `created_at`
- `commands`
- `datasets`
- `limits`
- `min_confidence`
- `input_paths`
- `output_paths`
- `artifact_counts`
- `policy_counts`
- `eval_counts`
- `test_status`

`summaries/summary.json` records:

- trace counts
- confidence distribution
- policy fire counts
- target policy evidence
- harmful and uncertain counts
- live-shadow fire counts
- metabolization candidate status counts
- `policy_activation_count`
- `recommended_next_move`

`summaries/summary.md` is the short operator-facing version of the same run.

## Target Profiles

Target profile definitions live in:

- `configs/settlement_datasets/targeted_trace_queries.yaml`

The initial profile is:

- `reflection_second_unresolved_error`

In this pass the target profile is workflow plumbing, not a new adapter or an activation surface. The wrapper records the selected profile and its query metadata in the run manifest and summary so later passes can specialize trace collection without manual module calls.

## Safety Boundaries

- No policy is activated by this workflow.
- No confidence thresholds are lowered by this workflow.
- No metabolization candidate is promoted to `metabolized` by this workflow.
- Live shadow replay remains replay-only evidence unless a separate guarded activation pass explicitly changes policy.

## Expected Outcome

The evidence surface for a pass is now reproducible:

- one command can allocate the run directory
- later phases can reuse the run directory as input
- adjudication and replay no longer require ad hoc top-level path editing
- targeted trace intent is recorded with the run rather than in shell history
