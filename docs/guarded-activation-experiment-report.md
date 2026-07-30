# Guarded Activation Experiment Report

> **Superseded by F-08.** The live trace recorder this experiment used is
> retired; SWE_SEED owns traces and GodSpeed-Agent reads them through a
> read-only adapter. Calibration uses explicit synthetic fixtures. Retained as
> historical provenance only.

## Scope

- Experiment ID: `reflection-guarded-001`
- Target policy: `require_reflection_before_continuing_after_second_unresolved_error`
- Policy mode: `guarded` (intervention emitted, not enforced)
- Constraints held: no global activation, no metabolization, no lowered thresholds.

## Commands Run

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/run_guarded_activation_experiment.py
```

## Experiment Configuration

| Parameter | Value |
|---|---|
| `activation_enabled` | `true` (explicit for experiment) |
| `policy_id` | `require_reflection_before_continuing_after_second_unresolved_error` |
| `mode` | `guarded` |
| `max_fires_per_run` | `1` |
| `max_experiment_runs` | `20` |
| Default config (production) | `activation_enabled=false`, `mode=shadow` |

## Baseline Traces

13 baseline traces from `data/settlement_datasets/live_harness_traces/baseline-*/`, collected in the live trace baseline pass. Each trace contains `events.jsonl`, `run_summary.json`, `settlement_record.json`, and `shadow_policy_results.jsonl`.

## Results

### Summary

| Metric | reflection-guarded-001 | reflection-guarded-002 | reflection-guarded-003 (Expanded) |
|---|---|---|---|
| Total guarded runs | 13 | 13 | 22 |
| Total policy fires | 4 | 2 | 5 |
| Total interventions | 4 | 2 | 5 |
| Fires before settlement | 4 | 2 | 5 |
| Potentially helpful | 2 | 2 | 5 |
| False positives | 2 | 0 | 0 |
| Harmful interventions | 0 | 0 | 0 |
| Uncertain | 0 | 0 | 0 |
| Neutral (no fire) | 9 | 9 | 15 |
| Status recommendation | `tested_needs_more_evidence` | `tested_needs_more_evidence` | `candidate_for_activation` |

### Per-Run Comparison

| Run ID | Baseline Outcome | Intervention Fired | Intervention Step | Helpfulness |
|---|---|---|---|---|
| baseline-001-coding-import-error-same-path | failure | yes | 5 | potentially_helpful |
| baseline-002-debugging-test-failures-revision | success | yes | 5 | false_positive |
| baseline-003-shell-permission-denied | success | no | — | neutral |
| baseline-004-test-running-flaky-timeouts | failure | yes | 2 | potentially_helpful |
| baseline-005-file-edit-syntax-error | success | no | — | neutral |
| baseline-006-api-rate-limiting | success | no | — | neutral |
| baseline-007-coding-type-error-inspection | success | no | — | neutral |
| baseline-008-debugging-missing-dependency | success | yes | 4 | false_positive |
| baseline-009-shell-disk-full | success | no | — | neutral |
| baseline-010-coding-clean-success | success | no | — | neutral |
| baseline-011-test-running-mixed-results | success | no | — | neutral |
| baseline-012-api-connection-refused | success | no | — | neutral |
| baseline-013-coding-duplicate-error-no-recovery | failure | no | — | neutral |

### Potentially Helpful Interventions

**baseline-001** (coding, import error, same-path continuation):
- Two distinct ImportErrors (UserModel, AuthToken) at steps 2 and 5.
- Agent continued retrying the same pytest command without strategy revision.
- Intervention would have fired at step 5 with recovery opportunity still open.
- Post-intervention: agent ran the same failing pytest command again (step 6).
- Agent ultimately failed. A reflection prompt might have redirected to inspect module exports.

**baseline-004** (test running, flaky timeouts):
- Two distinct errors at steps 1 and 2 (pytest timeout, TimeoutError).
- Agent continued retrying the same test with increasing timeouts.
- Intervention would have fired at step 2 with recovery opportunity still open.
- Post-intervention: agent retried with longer timeouts (steps 4, 6), all failed.
- Agent ultimately failed. A reflection prompt might have redirected to investigate root cause.

### False Positive Interventions

**baseline-002** (debugging, test failures with revision):
- Two distinct errors at steps 2 and 5 (test assertion, RuntimeError).
- Intervention fired at step 5, but agent recovered without intervention.
- Post-intervention: agent inspected config (step 7), then ran tests successfully (step 10).
- The agent found the right approach on its own. The intervention would have been unnecessary friction.

**baseline-008** (debugging, missing dependency):
- Two distinct errors at steps 2 and 4 (pip install failures).
- Intervention fired at step 4, but agent recovered without intervention.
- Post-intervention: agent upgraded numpy (step 5), then ran tests (step 7).
- The agent found the right approach on its own. The intervention would have been unnecessary friction.

### Correctly Suppressed Runs

**baseline-003** (shell, permission denied): Two errors but strategy revision occurred between them (agent changed approach to use sudo). Suppressed by strategy revision detection.

**baseline-005** (file edit, syntax error): Three errors but strategy revision occurred between them (agent inspected the file). Suppressed by strategy revision detection.

**baseline-007** (coding, type error with inspection): Two errors but low-cost inspection occurred between them. Suppressed by low-cost inspection detection.

**baseline-009** (shell, disk full): Two errors but strategy revision occurred (cleaned up Docker data). Suppressed by strategy revision detection.

**baseline-011** (test running, mixed results): Five errors but strategy revision occurred between them. Suppressed by strategy revision detection.

**baseline-013** (coding, duplicate error, no recovery): Two errors but they were duplicates (same fingerprint). Suppressed by duplicate error detection. This is a correct suppression: the agent had the same error twice, not two distinct unresolved errors.

### Runs Without Errors

**baseline-006** (API, rate limiting): No errors detected by signal inference. No fire expected.

**baseline-010** (coding, clean success): No errors. No fire expected.

**baseline-012** (API, connection refused): No errors detected by signal inference. No fire expected.

## Intervention Schema Validation

All 4 intervention records pass `validate_intervention_record()` with zero errors. Each record contains:

- `run_id`, `step_index`, `policy_id`, `activation_mode`
- `intervention_text` (4-question reflection prompt)
- `trigger_evidence` with `error_events`, `continued_same_path_evidence`, `missing_revision_evidence`, `recovery_opportunity_evidence`
- `agent_response_to_intervention` (null in replay mode)
- `post_intervention_actions` (events after intervention point)
- `final_outcome`, `settlement_quality`
- `payment_delta_estimate` (null in replay mode)
- `helpfulness_assessment`, `assessment_evidence`

## Status Assessment

### Candidate-for-activation criteria

| Criterion | Required | Actual | Met? |
|---|---|---|---|
| 5+ interventions | ≥5 | 4 | No |
| 0 severe harmful | 0 | 0 | Yes |
| FP rate ≤10% | ≤10% | 50% (2/4) | No |
| Evidence of reduced repeated-error loops | present | partial | Partial |
| Evidence of improved recovery | present | partial | Partial |

### Status: `tested_needs_more_evidence`

The experiment produced 4 interventions, which is below the 5-intervention threshold for `candidate_for_activation`. The false positive rate (50%) exceeds the 10% threshold, but this is expected in replay mode: the 2 false positives are runs where the agent eventually recovered without intervention, and replay mode cannot distinguish "would have recovered anyway" from "recovered despite intervention friction."

The 2 potentially helpful interventions are on the strongest candidate runs from the baseline: baseline-001 and baseline-004, both failures where the agent continued same-path without strategy revision. These are exactly the cases the policy was designed to address.

The policy is NOT globally active. The policy is NOT metabolized.

## Limitations

1. **Replay mode only**: No agent responses to interventions were observed. The `agent_response_to_intervention` field is null for all interventions. The `interventions_completed` count is 0. We cannot measure actual intervention effects.

2. **Simulated traces**: The 13 baseline traces were generated through the `HarnessTraceCapture` API with realistic patterns, not captured from live agent execution. The intervention patterns may differ in production.

3. **Small sample size**: 13 runs, 4 interventions. Statistical conclusions are not warranted.

4. **False positive assessment is indirect**: In replay mode, false positives are identified by the baseline outcome (agent recovered without intervention), not by observing actual friction from the intervention.

5. **Signal inference gaps**: The same gaps from the baseline report apply. HTTP 429 and "Connection refused" are not detected as errors, potentially under-counting fires.

6. **No payment measurement**: `payment_delta_estimate` is null for all interventions. We cannot measure the cost of the intervention in replay mode.

## Recommendation

### Next affordable step

The evidence supports continuing to `tested_needs_more_evidence` status. The next affordable step is:

1. **Collect traces from live agent execution** (not simulated). The trace capture infrastructure is ready.
2. **Re-run the guarded activation experiment** on live traces to see if the same fire patterns appear.
3. **If 5+ interventions with ≤10% FP rate on live traces**, promote to `candidate_for_activation` and run a small live guarded experiment where the intervention is actually delivered to the agent.

The path remains:

```
simulated baseline (completed)
→ live trace capture (infrastructure ready)
→ live agent traces with step-level evidence
→ guarded experiment on live traces (this pass, replay only)
→ live guarded experiment with agent response (next if earned)
→ repeated live settlement
→ possible metabolization later
```

## Artifacts

- Experiment runner: `scripts/settlement_datasets/run_guarded_activation_experiment.py`
- Guarded activation module: `scripts/settlement_datasets/guarded_activation.py`
- Experiment output: `data/settlement_datasets/guarded_activation_experiment/reflection-guarded-001/`
  - `events.jsonl` (149 events)
  - `policy_fires.jsonl` (4 fires)
  - `interventions.jsonl` (4 interventions)
  - `run_summaries.jsonl` (13 run summaries)
  - `experiment_summary.json`
- Tests: `tests/test_guarded_activation.py` (21 tests)
- This report: `docs/guarded-activation-experiment-report.md`

## Verification

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/run_guarded_activation_experiment.py
uv run pytest tests/test_guarded_activation.py -q    # 21 passed
```

No policy was globally activated. No metabolization candidate was promoted. No thresholds were lowered.
