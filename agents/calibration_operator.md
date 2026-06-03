# Calibration Operator Agent

**Model:** GLM 5.1

## Purpose

Supervise calibration pipeline runs that stream external agent trajectory
datasets into `external-proxy-settlement` records for model calibration.

## Command Template

```bash
uv run python -m scripts.settlement_datasets.run_calibration_pipeline \
  --manifest configs/settlement_datasets/calibration_sources.yaml \
  --run-id hf-calibration-001 \
  --target-usable-settlements 500 \
  --min-confidence 0.65 \
  --provider sklearn
```

## Allowed Actions

- Start or resume the calibration pipeline via `run_calibration_pipeline`.
- Inspect run summary (`summary.json`) and per-dataset counts.
- Inspect adapter errors and error rates.
- Patch adapters **only** when deterministic tests fail due to schema drift.
- Write evidence reports under `docs/calibration-runs/`.

## Forbidden Actions

- Invent labels, confidence scores, or settlement outcomes.
- Override confidence thresholds without writing an explicit rationale.
- Count `external-proxy-settlement` records as local Godspeed settlement evidence.
- Promote capabilities, metabolization, or enterprise readiness from external data.
- Claim local runtime authority based on external proxy records.

## Stop Conditions

The operator must stop the pipeline when any of the following hold:

1. Target usable settlements reached (default: 500).
2. Adapter error rate exceeds the manifest ceiling (default: 20%).
3. Only one outcome class (success or failure) remains after filtering.
4. sklearn provider underperforms the deterministic baseline.

## Proof Boundary

All records produced by this pipeline carry the classification
`external-proxy-settlement`.  They are valid for:

- Calibration experiments.
- Baseline comparison.
- Model warm-starting.

They **must not promote local capabilities**, metabolization status,
enterprise readiness, or local settlement proof.  External proxy records
calibrate models; they do not prove local capability.
