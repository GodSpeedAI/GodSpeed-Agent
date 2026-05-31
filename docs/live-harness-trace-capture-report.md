# Live Harness Trace Capture Report

## Background

The targeted reflection evidence run (`reflection-target-001`) evaluated whether `require_reflection_before_continuing_after_second_unresolved_error` could fire early enough to matter on the AgentTrove settlement surface.

### AgentTrove Targeting Results

- 500 sampled traces, 270 high-confidence traces
- 174 traces with two or more unresolved errors
- 4 targeted matches forwarded downstream
- 4 authoritative shadow fires, all on `final_turn`
- 0 recovery opportunity across all fires
- 0 pre-settlement fires

### Conclusion from AgentTrove

AgentTrove does not expose enough step-level temporal structure for this intervention. The normalized settlement record captures end-state labels (error counts, recovery attempts, failure modes) but loses the within-run event sequence that the reflection trigger needs. The trigger requires knowing when the second error occurred relative to strategy revision, same-path continuation, and settlement closure.

## What Live Trace Capture Adds

Live harness trace capture records events as they happen during real or local agent runs:

1. **Step-level timing**: Each event carries a step_index and timestamp, preserving the exact sequence of errors, revisions, and settlement.
2. **Settlement signals at each step**: Error detection, task completion, success/failure, test results, and strategy revision are inferred or explicitly recorded per event.
3. **Extended event types**: Beyond the live shadow evaluator's 7 event types, trace capture adds `file_edit`, `command`, `test_run`, and `strategy_revision` for finer-grained analysis.
4. **Policy evidence focus**: Detection functions for duplicate errors, same-path continuation, strategy revision timing, and low-cost inspection support direct evaluation of the reflection trigger.

## Implementation

### Module

`godspeed_nav/trace_capture.py` provides:

- `HarnessTraceCapture`: Main recorder class with convenience methods for each event type.
- `validate_trace_event()`: Schema validation against required fields and signal fields.
- `normalize_trace_event()`: Signal inference from content and event type.
- Detection functions: `detect_duplicate_errors`, `detect_same_path_continuation`, `detect_strategy_revision_after_error`, `detect_low_cost_inspection_after_error`.
- Read functions: `read_trace_events`, `read_run_summary`, `read_settlement_record`, `read_shadow_policy_results`.

### Scripts

- `scripts/settlement_datasets/convert_live_trace_to_settlement_record.py`: Converts captured traces to canonical settlement records.
- `scripts/settlement_datasets/evaluate_live_trace_policies.py`: Runs live shadow policy evaluation over captured traces.

### Configuration

- `HARNESS_TRACE_CAPTURE_ENABLED`: Default `false`. Must be explicitly enabled.
- `HARNESS_TRACE_CAPTURE_DIR`: Default `data/settlement_datasets/live_harness_traces`.

### Output Structure

```
data/settlement_datasets/live_harness_traces/<run_id>/
  events.jsonl
  run_summary.json
  settlement_record.json
  shadow_policy_results.jsonl
```

## Fixture Traces

Six fixture traces under `tests/fixtures/live_harness_traces/` prove the reflection trigger can fire before settlement when appropriate, and that suppressions work:

| Fixture | Scenario | Expected Behavior |
|---|---|---|
| `repeated_error_same_path_continuation` | Two distinct errors, same-path continuation, no revision | Reflection trigger **fires** before settlement |
| `repeated_error_then_strategy_revision` | Strategy revision between errors | Reflection trigger **suppressed** |
| `duplicate_error_only` | Same error content twice | Duplicate detection capability demonstrated |
| `final_turn_only_error` | Error only on final turn | No repeated-error trigger |
| `low_cost_inspection_after_error` | Low-cost inspection between errors | Reflection trigger **suppressed** |
| `successful_recovery_after_second_error` | Two errors followed by successful recovery | No harmful intervention |

## Test Coverage

69 tests in `tests/test_live_harness_trace_capture.py` covering:

- Event schema validation (9 tests)
- Trace capture disabled by default (6 tests)
- Trace writing and file output (7 tests)
- Settlement signal inference (11 tests)
- Strategy revision detection (3 tests)
- Duplicate error suppression (3 tests)
- Same-path continuation detection (3 tests)
- Low-cost inspection suppression (3 tests)
- Conversion to settlement record (7 tests)
- Policy evaluation over fixtures (9 tests)
- No accidental activation (8 tests)

## Verification

```
uv run pytest tests/test_live_harness_trace_capture.py -q    # 69 passed
uv run pytest -q                                               # 442 passed
```

No policy was activated. No metabolization candidate was promoted. No thresholds were lowered.

## What Future Evidence Would Justify Guarded Activation

Live trace capture is instrumentation only. Guarded activation would require:

1. Multiple live runs where the reflection trigger fires before settlement with recovery opportunity still open.
2. Evidence that the trigger fires on genuinely distinct unresolved errors (not duplicates).
3. Evidence that same-path continuation after the second error leads to worse outcomes than strategy revision.
4. Repeated settlement showing the intervention improves outcomes without harmful side effects.
5. No false positives on traces where the agent successfully recovers without intervention.

The path remains:

```
external trace limit discovered
→ live harness trace capture
→ step-level policy evidence
→ guarded experiment only if earned
→ repeated live settlement
→ possible metabolization later
```

This pass completes step 2. The next affordable step is capturing real live runs and evaluating whether the trigger fires early enough to matter.

## Guarded Activation Experiment Follow-Up

The guarded activation experiment (`reflection-guarded-001`) used the 13 baseline traces captured by this infrastructure. The experiment replayed all traces through guarded activation mode and produced 4 interventions (2 potentially helpful, 2 false positives, 0 harmful). See `docs/guarded-activation-experiment-report.md` for the full report.
