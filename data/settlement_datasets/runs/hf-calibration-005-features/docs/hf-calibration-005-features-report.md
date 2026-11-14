# Calibration Run Report: hf-calibration-005-features

**Date:** 2026-09-09T19:20:38Z
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
- Sampling strategy: natural
- Min datasets: 3

## Class Balance

- Success: 1289 (19.8%)
- Failure: 5208 (80.2%)

## Calibration Frame

- Path: `data/settlement_datasets/runs/hf-calibration-005-features/calibration/calibration_frame.csv`
- Rows: 6497

## Model Evaluation

- Provider: sklearn
- Held-out evaluation available

## Held-Out Evaluation

- **Train size:** 5197
- **Test size:** 1300
- **Train success rate:** 0.1984
- **Test success rate:** 0.1985
- **Sampling strategy:** natural
- **Class weight:** balanced
- **Features used:** payment_predicted_total, payment_actual_total, payment_error, horizon_delta, risk_estimate, debt_estimate, tool_diversity_count, error_recovery_ratio, action_observation_ratio, avg_actions_per_step, dataset_id

### Held-Out Metrics

- **raw_accuracy:** 0.7069
- **balanced_accuracy:** 0.7428
- **f1_score:** 0.5208
- **roc_auc:** 0.8266
- **average_precision:** 0.6291
- **brier_score:** 0.1771
- **confusion_matrix:** [[712, 330], [51, 207]]

### Baseline Metrics (matched families)

- **majority_class_raw_accuracy:** 0.8015
- **majority_class_balanced_accuracy:** 0.5
- **majority_class_f1:** 0.0
- **success_rate_raw_accuracy:** 0.3954
- **success_rate_balanced_accuracy:** 0.6024
- **success_rate_f1:** 0.383

### Matched Baseline Comparison

- **sklearn raw_accuracy vs majority raw_accuracy:** False
- **sklearn balanced_accuracy vs majority balanced_accuracy:** True
- **sklearn f1 vs majority f1:** True
- **sklearn balanced_accuracy vs success_rate balanced_accuracy:** True
- **sklearn f1 vs success_rate f1:** True

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
