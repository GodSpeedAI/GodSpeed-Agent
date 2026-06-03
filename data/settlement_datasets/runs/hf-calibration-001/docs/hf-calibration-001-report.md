# Calibration Run Report: hf-calibration-001

**Date:** 2026-06-03T15:37:43Z
**Manifest:** configs/settlement_datasets/calibration_sources.yaml

## Dataset Counts

### swegym_openhands
- Scanned: 799
- Normalized: 799
- Usable: 500
- Rejected: 299
- Adapter errors: 0

## Summary

- Raw rows scanned: 799
- Normalized records: 799
- usable settlements: 500
- Rejected records: 299
- Adapter errors: 0

## Class Balance

- Success: 53 (10.6%)
- Failure: 447 (89.4%)

## Calibration Frame

- Path: `data/settlement_datasets/runs/hf-calibration-001/calibration/calibration_frame.csv`
- Rows: 500

## Model Evaluation

- Provider: sklearn
- Evaluation: [{"candidate_id": "eval_candidate", "success_probability": 0.8964, "predicted_horizon_delta": 0.8964, "rationale": "sklearn_logistic_regression"}]

## Proof Classification

external-proxy-calibration

All imported dataset records are classified as `external-proxy-settlement`.
They are valid for calibration experiments, baseline comparison, and model
warm-starting. They are not local Godspeed settlement evidence.

## Non-Claims

This report does not claim local capability, metabolization, enterprise readiness,
or local settlement proof from external proxy data.

## Next Move

Run the fixture path first, then live HF only after local tests pass.
