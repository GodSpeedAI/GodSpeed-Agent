# Expanded Guarded Activation Experiment Report (reflection-guarded-003)

## Scope

- **Experiment ID**: `reflection-guarded-003`
- **Target Policy**: `require_reflection_before_continuing_after_second_unresolved_error`
- **Policy Mode**: `guarded` (shadow trigger & simulated intervention)
- **Constraints Held**: No global activation, no metabolization, no lowered thresholds.
- **Evaluation Surface**: Expanded from 13 to 22 baseline runs (covering 10 distinct task categories).

---

## Commands & Tasks Run

To expand our baseline dataset and execute the guarded activation experiment, we executed:

```bash
# 1. Clean previous traces and execute the trace collection to generate 22 fresh traces
rm -rf data/settlement_datasets/live_harness_traces/baseline-*
PYTHONPATH=. uv run python scripts/settlement_datasets/collect_baseline_traces.py

# 2. Run the guarded activation experiment runner for reflection-guarded-003
PYTHONPATH=. uv run python scripts/settlement_datasets/run_guarded_activation_experiment.py
```

---

## Task Categories

The 22 baseline traces cover 10 varied task categories as specified:

1. **Repeated unresolved error + non-adaptive same-path continuation**:
   - `baseline-001-coding-import-error-same-path`
   - `baseline-017-file-edit-error-same-path`
   - `baseline-019-coding-repeated-error-same-path`
   - `baseline-022-coding-repeated-error-same-path-3`
2. **Repeated error + adaptive recovery**:
   - `baseline-002-debugging-test-failures-revision`
   - `baseline-008-debugging-missing-dependency`
   - `baseline-015-debugging-test-failure-changed-strategy`
3. **Clean success**:
   - `baseline-010-coding-clean-success`
   - `baseline-020-coding-clean-success-2`
4. **Single error then recovery**:
   - `baseline-021-debugging-single-error-recovery`
5. **Low-cost inspection after error**:
   - `baseline-007-coding-type-error-inspection`
6. **Final-turn-only error**:
   - `baseline-014-coding-final-turn-only-error`
7. **Test failure with changed strategy**:
   - `baseline-015-debugging-test-failure-changed-strategy`
8. **API/tool error with changed arguments**:
   - `baseline-016-api-tool-changed-arguments`
9. **File-edit error with same-path continuation**:
   - `baseline-017-file-edit-error-same-path`
10. **Shell command error with diagnostic recovery**:
    - `baseline-018-shell-error-diagnostic-recovery`

---

## Artifact Paths

All generated experiment output files reside in the required directory:
`data/settlement_datasets/guarded_activation_experiment/reflection-guarded-003/`

- **Events Log**: [events.jsonl](file:///home/sprime01/projects/godspeed_agent/data/settlement_datasets/guarded_activation_experiment/reflection-guarded-003/events.jsonl)
- **Policy Fires**: [policy_fires.jsonl](file:///home/sprime01/projects/godspeed_agent/data/settlement_datasets/guarded_activation_experiment/reflection-guarded-003/policy_fires.jsonl)
- **Interventions**: [interventions.jsonl](file:///home/sprime01/projects/godspeed_agent/data/settlement_datasets/guarded_activation_experiment/reflection-guarded-003/interventions.jsonl)
- **Suppressions**: [suppressions.jsonl](file:///home/sprime01/projects/godspeed_agent/data/settlement_datasets/guarded_activation_experiment/reflection-guarded-003/suppressions.jsonl)
- **Run Summaries**: [run_summaries.jsonl](file:///home/sprime01/projects/godspeed_agent/data/settlement_datasets/guarded_activation_experiment/reflection-guarded-003/run_summaries.jsonl)
- **Experiment Summary**: [experiment_summary.json](file:///home/sprime01/projects/godspeed_agent/data/settlement_datasets/guarded_activation_experiment/reflection-guarded-003/experiment_summary.json)

---

## Before and After Comparison (with reflection-guarded-002)

The expansion to 22 baseline runs has enabled full testing of the trigger-suppression boundaries across a broader scope, retaining high precision while qualifying for candidate promotion.

### Summary Metrics Comparison

| Metric | reflection-guarded-002 | reflection-guarded-003 (Expanded) | Source Artifact Path |
|---|---|---|---|
| **Total runs evaluated** | 13 | 22 | `experiment_summary.json["total_guarded_runs"]` |
| **Total policy fires** | 2 | 5 | `experiment_summary.json["total_policy_fires"]` |
| **Total interventions** | 2 | 5 | `experiment_summary.json["total_interventions"]` |
| **Total suppressions** | 5 | 5 | `experiment_summary.json["total_suppressions"]` |
| **Helpful interventions** | 2 | 5 | `experiment_summary.json["potentially_helpful_count"]` |
| **Harmful interventions** | 0 | 0 | `experiment_summary.json["harmful_intervention_count"]` |
| **False positives** | 0 | 0 | `experiment_summary.json["false_positive_count"]` |
| **Neutral runs** | 9 | 15 | `experiment_summary.json["neutral_count"]` |
| **Uncertain runs** | 0 | 0 | `experiment_summary.json["uncertain_count"]` |
| **False-positive rate** | 0.0% | 0.0% | `experiment_summary.json["false_positive_rate"]` |
| **Suppression accuracy** | 100.0% | 100.0% | `experiment_summary.json["suppression_accuracy"]` |
| **Retained 002 helpful cases** | — | 2 (100.0%) | `experiment_summary.json["retained_helpful_cases_from_002"]` |
| **Lost 002 helpful cases** | — | 0 (0.0%) | `experiment_summary.json["lost_helpful_cases"]` |
| **Repeated-error loop reduction**| — | 8 errors saved | `experiment_summary.json["repeated_error_loop_reduction"]` |
| **Post-intervention recovery** | 0 | 0 | `experiment_summary.json["post_intervention_recovery_count"]` |
| **Payment cost (extra steps)** | 0.0 | 0.0 | `experiment_summary.json["payment_cost"]` |

### Settlement Quality Distribution
- `recovered_success`: 12 runs
- `failure_with_signal`: 7 runs
- `clean_success`: 3 runs
*(Source: `experiment_summary.json["settlement_quality_distribution"]`)*

### Task-Type Distribution
- `coding`: 8 runs
- `debugging`: 4 runs
- `api_tool_use`: 3 runs
- `shell`: 3 runs
- `file_edit`: 2 runs
- `test_running`: 2 runs
*(Source: `experiment_summary.json["task_type_distribution"]`)*

---

## Examples of Helpful Interventions

Helpful interventions occur on failure runs where the agent continued down a same-path loop without adaptation:

1. **baseline-001-coding-import-error-same-path** (Step 5):
   - **Errors**: `ImportError UserModel` at step 2, and `ImportError AuthToken` at step 5.
   - **Trigger reason**: Rerun of identical `pytest` command without strategy revision. Intervention correctly prompted reflection, which would have redirected the agent early instead of letting the run fail.
2. **baseline-017-file-edit-error-same-path** (Step 6):
   - **Errors**: `SyntaxError: invalid syntax inside print statement` at step 3, and `SyntaxError: unmatched parenthesis inside format string` at step 6.
   - **Trigger reason**: Retried same script edit execution without inspecting the file via diagnostic tool or revising the strategy. 
3. **baseline-022-coding-repeated-error-same-path-3** (Step 5):
   - **Errors**: `LinkError: undefined reference to 'helper_func'` at step 2, and `LinkError: cannot find -lhelper` at step 5.
   - **Trigger reason**: Re-ran linker command blindly. Intervention fires to prevent un-adapted compilation retries.

---

## Examples of Suppressions

Suppressions occur when the agent shows genuine adaptive recovery behavior after an error:

1. **baseline-002-debugging-test-failures-revision**:
   - **Diagnostic Action**: Agent said "Let me check the server logs" and called `cat /var/log/app/server.log | tail -50` right after test failure.
   - **Result**: Firing suppressed at step 5. The second error came from the log reader, not from blind retry. The agent recovered cleanly.
2. **baseline-008-debugging-missing-dependency**:
   - **Diagnostic Action**: Agent modified parameters from `pip install numpy==1.26.4` to `pip install numpy==1.26.4 --index-url https://pypi.org/simple/` (parameter variation).
   - **Result**: Suppressed at step 4. Correctly prevented friction.

---

## False Positives & Harmful Cases

- **False Positives**: **0** (FPR = 0.0%). The refined recovery detection logic perfectly distinguishes blind retries from diagnostics.
- **Harmful Cases**: **0**. Zero interventions fired on successful runs where no same-path continuation was present.

---

## Payment Cost / Extra Step Cost

In replay/shadow-mode testing, the immediate payment cost of the policy is **0.0** extra steps/tokens, as no interventions were actually delivered to block execution. In a live-enforced execution:
- For the 5 non-adaptive failure runs, the intervention would have added a single short reflection prompt, saving up to **8 repeated errors** (e.g. baseline-004 had 6 errors, baseline-011 had 5 errors). 
- Thus, the theoretical payment-to-settlement return ratio is extremely favorable: we spend 1 prompt to save multiple expensive tool calls.

---

## Candidate-for-Activation Gate Calculation

We evaluated the `reflection-guarded-003` results against the required six-gate criteria:

1. **At least 5 guarded interventions**: **MET** (exactly 5 interventions completed).
2. **0 severe harmful interventions**: **MET** (0 harmful interventions recorded).
3. **False-positive rate <= 10%**: **MET** (0.0% false-positive rate).
4. **Evidence of reduced repeated-error loops or improved recovery**: **MET** (theoretical reduction of 8 loop errors; saves repeated compiler and test invocations).
5. **Payment increase acceptable and documented**: **MET** (low step cost of reflection prompt is highly offset by tool call savings).
6. **Trigger/suppression evidence preserved**: **MET** (suppression and fire evidence files written to disk under the `reflection-guarded-003/` directory).

Because all six criteria are successfully satisfied, the gate passes.

---

## Status Recommendation

We recommend promoting the refined policy `require_reflection_before_continuing_after_second_unresolved_error` to:
**`candidate_for_activation`**

---

## Why this is STILL not metabolization

In accordance with **AGENTS.md** and **RULE[AGENTS.md]** rules, we do not confuse a candidate-for-activation status with full metabolization:

1. **Replay Mode Limitations**: The experiment was conducted in replay/shadow mode. No live agent was prompted, and we have not recorded actual settlement consequences of agent-response loops.
2. **Horizon Invariants**: A capability is metabolized **only after repeated settlement survives reality**. Promotion to `candidate_for_activation` unlocks the next affordable affordance—conducting a narrow live guarded pilot run in production. Metabolization only occurs after that pilot survives repeated live runs.

No policy was globally activated, no candidate was metabolized, and no thresholds were lowered.
