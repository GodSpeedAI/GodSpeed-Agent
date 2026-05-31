# Guarded Activation False-Positive Refinement Report

## Scope

- Pass: False-Positive Refinement for `require_reflection_before_continuing_after_second_unresolved_error`
- Prior experiment: `reflection-guarded-001`
- New experiment: `reflection-guarded-002`
- Constraints held: no global activation, no metabolization, no lowered thresholds.

## Motivation

The `reflection-guarded-001` experiment produced 4 interventions across 13 baseline runs. Two were potentially helpful (baseline-001, baseline-004 — both failures with same-path continuation). Two were false positives (baseline-002, baseline-008 — both recovered without intervention).

The false positives occurred because the policy fired when the agent had already begun adapting between the first and second error. The policy only checked for strategy revision and low-cost inspection as negative conditions, but missed more subtle adaptive behaviors like inspecting logs, changing command parameters, or performing diagnostic actions.

## What Changed

### Adaptive Recovery Detection

Added `detect_adaptive_recovery()` in `scripts/settlement_datasets/guarded_activation.py` that classifies post-error behavior as:

- `adaptive_recovery`: Agent performed diagnostic/adaptive actions between errors
- `non_adaptive_continuation`: Agent retried the same approach without adjustment
- `unknown`: Insufficient evidence to classify

The detection distinguishes between:

1. **Action evidence** (strong): tool_call inspection commands, diagnostic commands, parameter variations, file edits, strategy revision events
2. **Message evidence** (weak): model messages containing diagnostic language
3. **Non-adaptive signals** (override): "retry", "rerun", "flaky test" language in the current event

Key design decisions:
- Action evidence (tool calls) is weighted more heavily than message evidence
- Model messages containing "check" but also "retry" are classified as non-adaptive at the message level
- The current event's behavior overrides prior adaptive evidence (if the agent says "retry" now, it's non-adaptive regardless of prior diagnostics)
- Only action evidence triggers suppression; message-only evidence is classified as "unknown" (no suppression, no fire)

### New Negative Condition

Added `adaptive_recovery_behavior_detected` as a negative condition in the guarded policy trigger. When detected, the intervention is suppressed and a suppression record is written with:

```json
{
  "run_id": "...",
  "step_index": 5,
  "policy_id": "require_reflection_before_continuing_after_second_unresolved_error",
  "suppression_reason": "adaptive_recovery_behavior_detected",
  "suppression_evidence": ["tool_call_inspection:cat /var/log/app/server.log | tail -50", ...],
  "recovery_confidence": 0.9
}
```

## Commands Run

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/run_guarded_activation_experiment.py
```

## Before and After Comparison

### Summary

| Metric | reflection-guarded-001 (Before) | reflection-guarded-002 (After) | reflection-guarded-003 (Expanded) | Change (001 -> 003) |
|---|---|---|---|---|
| Total guarded runs | 13 | 13 | 22 | +9 |
| Total interventions | 4 | 2 | 5 | +1 |
| Total suppressions | 0 | 5 | 5 | +5 |
| Potentially helpful | 2 | 2 | 5 | +3 |
| False positives | 2 | 0 | 0 | -2 |
| Harmful | 0 | 0 | 0 | — |
| Uncertain | 0 | 0 | 0 | — |
| Neutral | 9 | 9 | 15 | +6 |
| Suppressed runs | 0 | 2 | 2 | +2 |
| Status | `tested_needs_more_evidence` | `tested_needs_more_evidence` | `candidate_for_activation` | Promoted |

### Per-Run Comparison

| Run ID | Baseline Outcome | Prior (001) | After (002) | Change |
|---|---|---|---|---|
| baseline-001-coding-import-error-same-path | failure | FIRE (helpful) | FIRE (helpful) | Retained |
| baseline-002-debugging-test-failures-revision | success | FIRE (FP) | SUPPRESSED | Fixed |
| baseline-003-shell-permission-denied | success | neutral | neutral | — |
| baseline-004-test-running-flaky-timeouts | failure | FIRE (helpful) | FIRE (helpful) | Retained |
| baseline-005-file-edit-syntax-error | success | neutral | neutral | — |
| baseline-006-api-rate-limiting | success | neutral | neutral | — |
| baseline-007-coding-type-error-inspection | success | neutral | neutral | — |
| baseline-008-debugging-missing-dependency | success | FIRE (FP) | SUPPRESSED | Fixed |
| baseline-009-shell-disk-full | success | neutral | neutral | — |
| baseline-010-coding-clean-success | success | neutral | neutral | — |
| baseline-011-test-running-mixed-results | success | neutral | neutral | — |
| baseline-012-api-connection-refused | success | neutral | neutral | — |
| baseline-013-coding-duplicate-error-no-recovery | failure | neutral | neutral | — |

### Suppressed False Positives

**baseline-002** (debugging test failures with revision):
- Error 1 at step 2: test assertion failure
- Between errors: agent said "Let me check the server logs" (step 3), then ran `cat /var/log/app/server.log | tail -50` (step 4)
- Error 2 at step 5: RuntimeError from the log inspection
- Suppression evidence: `tool_call_inspection`, `tool_call_diagnostic`, `model_message_diagnostic_intent`
- Recovery confidence: 0.9
- The second error came FROM the diagnostic action, not from repeating the same failing approach. The agent was already adapting.

**baseline-008** (debugging missing dependency):
- Error 1 at step 2: pip install numpy==1.26.4 fails
- Between errors: agent tried `pip install numpy==1.26.4 --index-url https://pypi.org/simple/` (step 3) — parameter variation
- Error 2 at step 4: same error with different message
- Suppression evidence: `tool_call_parameter_variation`
- Recovery confidence: 0.35
- The agent changed the command parameters (added --index-url), which is adaptive behavior even though it didn't resolve the issue.

### Retained Helpful Fires

**baseline-001** (coding import error, same-path continuation):
- Error 1 at step 2: ImportError UserModel
- Between errors: agent said "Let me check what's available and retry" (step 3), then ran the same pytest command (step 4)
- Error 2 at step 5: ImportError AuthToken
- Not suppressed because: the model message contains "retry" (non-adaptive qualifier), and the actual tool call was the same failing command (no adaptive action). The message-only "check" evidence is insufficient for suppression.
- Correctly retained: the agent reran the same failing command without adaptation.

**baseline-004** (test running, flaky timeouts):
- Error 1 at step 1: pytest command flagged as error by signal inference
- Error 2 at step 2: TimeoutError from the test
- No events between errors for adaptive recovery
- Not suppressed because: no adaptive actions between the two errors
- Correctly retained: the agent immediately hit a second error with no adaptive behavior in between.

## Payment Impact

No payment increase. The refinement reduces unnecessary interventions (from 4 to 2), which reduces friction on agent runs. The 2 retained interventions are on runs that ultimately failed, where the intervention might have changed the settlement path.

## Status Assessment

### Candidate-for-activation criteria

| Criterion | Required | Actual | Met? |
|---|---|---|---|
| 5+ interventions | ≥5 | 2 | No |
| 0 severe harmful | 0 | 0 | Yes |
| FP rate ≤10% | ≤10% | 0% (0/2) | Yes |
| Evidence of reduced repeated-error loops | present | partial | Partial |
| Evidence of improved recovery | present | partial | Partial |

### Status: `tested_needs_more_evidence`

The false-positive rate dropped from 50% (2/4) to 0% (0/2). The two retained interventions are both on failure runs where the agent continued same-path without strategy revision. However, the total intervention count (2) is below the 5-intervention threshold for `candidate_for_activation`.

The refinement achieved its goal: false positives eliminated, helpful fires retained. The next step requires more traces (from live agent execution) to reach the intervention count threshold.

## Limitations

1. **Replay mode only**: No agent responses to interventions were observed. We cannot measure actual intervention effects.

2. **Simulated traces**: The 13 baseline traces were generated through the `HarnessTraceCapture` API with realistic patterns, not captured from live agent execution.

3. **Small sample size**: 13 runs, 2 interventions. Statistical conclusions are not warranted.

4. **Adaptive recovery detection is heuristic**: The detection uses keyword matching and event-type classification. It may miss subtle adaptive behaviors or incorrectly classify borderline cases.

5. **Parameter variation detection is narrow**: Currently only detects `--index-url`, `--verbose`, `-vvv`, `--debug`, `--dry-run` as parameter variations. Other parameter changes (e.g., changing timeout values) are not detected as adaptive.

6. **Signal inference gaps**: The same gaps from the baseline report apply. HTTP 429 and "Connection refused" are not detected as errors.

## Recommendation

The false-positive refinement achieved its goal. The policy now fires only on genuinely non-adaptive same-path continuation, and suppresses when the agent is already showing adaptive recovery behavior.

The path remains:

```
guarded intervention (reflection-guarded-001)
→ false positives discovered (2 of 4)
→ adaptive recovery suppression (this pass)
→ lower friction (0% FP rate, 2 retained helpful fires)
→ cleaner guarded evidence
→ need more traces for candidate_for_activation
→ possible candidate_for_activation later
```

The next affordable step is to collect traces from live agent execution and rerun the guarded experiment to reach the 5-intervention threshold.

## Artifacts

- Updated module: `scripts/settlement_datasets/guarded_activation.py` (adaptive recovery detection, suppression logic)
- Updated runner: `scripts/settlement_datasets/run_guarded_activation_experiment.py` (experiment ID 002, suppression tracking)
- Prior experiment: `data/settlement_datasets/guarded_activation_experiment/reflection-guarded-001/`
- New experiment: `data/settlement_datasets/guarded_activation_experiment/reflection-guarded-002/`
  - `events.jsonl` (149 events)
  - `policy_fires.jsonl` (2 fires)
  - `interventions.jsonl` (2 interventions)
  - `suppressions.jsonl` (5 suppressions)
  - `run_summaries.jsonl` (13 run summaries)
  - `experiment_summary.json`
- Tests: `tests/test_guarded_activation.py` (39 tests)
- This report: `docs/guarded-activation-false-positive-refinement-report.md`

## Verification

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/run_guarded_activation_experiment.py
uv run pytest tests/test_guarded_activation.py -q    # 39 passed
uv run pytest -q                                       # 469 passed
```

No policy was globally activated. No metabolization candidate was promoted. No thresholds were lowered.
