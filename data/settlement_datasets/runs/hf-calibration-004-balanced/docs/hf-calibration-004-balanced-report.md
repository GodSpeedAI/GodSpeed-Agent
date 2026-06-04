# Calibration Run Report: hf-calibration-004-balanced

**Date:** 2026-06-04T11:16:58Z
**Manifest:** configs/settlement_datasets/calibration_sources.yaml

## Dataset Counts

### swegym_openhands
- Scanned: 3000
- Normalized: 3000
- Usable: 1892
- Rejected: 1108
- Adapter errors: 0

### agenttrove
- Scanned: 100
- Normalized: 100
- Usable: 51
- Rejected: 49
- Adapter errors: 0

### nebius_swe_agent
- Scanned: 5000
- Normalized: 4559
- Usable: 4554
- Rejected: 5
- Adapter errors: 441

## Summary

- Raw rows scanned: 8100
- Normalized records: 7659
- usable settlements: 6497
- Rejected records: 1162
- Adapter errors: 441
- Datasets processed: 3
- Sampling strategy: balanced
- Min datasets: 3

## Class Balance

- Success: 1289 (19.8%)
- Failure: 5208 (80.2%)

## Calibration Frame

- Path: `data/settlement_datasets/runs/hf-calibration-004-balanced/calibration/calibration_frame.csv`
- Rows: 6497

## Model Evaluation

- Provider: sklearn
- Held-out evaluation available

## Held-Out Evaluation

- **Train size:** 2062
- **Test size:** 1300
- **Train success rate:** 0.5
- **Test success rate:** 0.1985
- **Sampling strategy:** balanced
- **Class weight:** balanced
- **Features used:** payment_predicted_total, payment_actual_total, payment_error, horizon_delta, risk_estimate, debt_estimate

### Held-Out Metrics

- **raw_accuracy:** 0.6892
- **balanced_accuracy:** 0.7172
- **f1_score:** 0.4937
- **roc_auc:** 0.7982
- **average_precision:** 0.5854
- **brier_score:** 0.1891
- **confusion_matrix:** [[699, 343], [61, 197]]

### Baseline Metrics (matched families)

- **majority_class_raw_accuracy:** 0.8015
- **majority_class_balanced_accuracy:** 0.5
- **majority_class_f1:** 0.0
- **success_rate_raw_accuracy:** 0.6892
- **success_rate_balanced_accuracy:** 0.7172
- **success_rate_f1:** 0.4937

### Matched Baseline Comparison

- **sklearn raw_accuracy vs majority raw_accuracy:** False
- **sklearn balanced_accuracy vs majority balanced_accuracy:** True
- **sklearn f1 vs majority f1:** True
- **sklearn balanced_accuracy vs success_rate balanced_accuracy:** False
- **sklearn f1 vs success_rate f1:** False

### Leakage Audit

- **Leakage detected:** False


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
