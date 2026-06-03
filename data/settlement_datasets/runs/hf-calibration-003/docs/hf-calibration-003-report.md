# Calibration Run Report: hf-calibration-003

**Date:** 2026-06-03T17:48:42Z
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

## Summary

- Raw rows scanned: 3100
- Normalized records: 3100
- usable settlements: 1943
- Rejected records: 1157
- Adapter errors: 0
- Datasets processed: 2
- Sampling strategy: natural
- Min datasets: 2

## Class Balance

- Success: 291 (15.0%)
- Failure: 1652 (85.0%)

## Calibration Frame

- Path: `data/settlement_datasets/runs/hf-calibration-003/calibration/calibration_frame.csv`
- Rows: 1943

## Model Evaluation

- Provider: sklearn
- Held-out evaluation available

## Held-Out Evaluation

- **Train size:** 1554
- **Test size:** 389
- **Train success rate:** 0.1499
- **Test success rate:** 0.1491
- **Sampling strategy:** natural
- **Class weight:** balanced
- **Features used:** payment_predicted_total, payment_actual_total, payment_error, horizon_delta, risk_estimate, debt_estimate

### Held-Out Metrics

- **roc_auc:** 0.7481
- **average_precision:** 0.4402
- **balanced_accuracy:** 0.7015
- **brier_score:** 0.1977
- **f1_score:** 0.4038
- **confusion_matrix:** [[219, 112], [15, 43]]

### Baseline Metrics

- **majority_class_accuracy:** 0.8509
- **success_rate_predictor_accuracy:** 0.1799
- **majority_class_f1:** 0.0

### Baseline Comparison

- **sklearn_beats_majority_baseline:** False
- **sklearn_beats_success_rate_baseline:** True

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
