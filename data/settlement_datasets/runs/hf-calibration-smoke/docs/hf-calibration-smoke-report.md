# Calibration Run Report: hf-calibration-smoke

**Date:** 2026-06-03T15:03:06Z
**Manifest:** configs/settlement_datasets/calibration_sources.yaml

## Dataset Counts

### swegym_openhands
- Scanned: 116
- Normalized: 116
- Usable: 50
- Rejected: 66
- Adapter errors: 0

## Summary

- Raw rows scanned: 116
- Normalized records: 116
- usable settlements: 50
- Rejected records: 66
- Adapter errors: 0

## Class Balance

- Success: 6 (12.0%)
- Failure: 44 (88.0%)

## Calibration Frame

- Path: `data/settlement_datasets/runs/hf-calibration-smoke/calibration/calibration_frame.csv`
- Rows: 50

## Model Evaluation

- Provider: disabled (deterministic only)

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
