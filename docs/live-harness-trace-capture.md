# Live Harness Trace Capture

> **Superseded by F-08.** GodSpeed-Agent no longer owns software hooks or a live
> trace recorder; SWE_SEED is the proven owner. Synthetic calibration traces
> live in `scripts/settlement_datasets/synthetic_trace_fixture.py`, and SWE_SEED
> trace exports are read through `scripts/settlement_datasets/swe_seed_trace_reader.py`.
> The recorder API below is historical and no longer exists in `godspeed_nav`.

## Purpose

Live harness trace capture records step-level events from real or local agent runs, preserving the temporal structure needed to evaluate whether policies like `require_reflection_before_continuing_after_second_unresolved_error` could fire before settlement closes.

## Why AgentTrove Was Insufficient

The targeted reflection evidence run (`reflection-target-001`) demonstrated that AgentTrove traces do not expose enough step-level temporal structure for this intervention:

- All 4 authoritative shadow fires occurred on `final_turn` with `0` recovery opportunity.
- AgentTrove preserves actions and observations but not the fine-grained step timing needed to detect when a second unresolved error occurs relative to strategy revision, same-path continuation, and settlement closure.
- The normalized settlement record schema captures end-state labels well but loses the within-run event sequence that the reflection trigger needs.

Live harness trace capture addresses this by recording events as they happen, with timestamps, step indices, and settlement signals preserved at each step.

## Event Schema

Each captured event follows this structure:

```json
{
  "run_id": "unique-run-identifier",
  "step_index": 0,
  "timestamp": "2026-05-31T00:00:00Z",
  "event_type": "model_message | tool_call | tool_result | error | file_edit | command | test_run | final_answer | task_complete | evaluator_result | strategy_revision",
  "content": "event content text",
  "tool_name": null,
  "metadata": {},
  "settlement_signals": {
    "error_detected": false,
    "task_complete": false,
    "success_signal": false,
    "failure_signal": false,
    "test_passed": false,
    "test_failed": false,
    "strategy_revision_detected": false
  }
}
```

### Event Types

| Event Type | Description |
|---|---|
| `model_message` | Agent reasoning or planning message |
| `tool_call` | Tool invocation (bash, read, write, etc.) |
| `tool_result` | Tool output or response |
| `error` | Explicit error event |
| `file_edit` | File modification action |
| `command` | Shell command execution |
| `test_run` | Test execution output |
| `final_answer` | Agent's final answer |
| `task_complete` | Task completion marker |
| `evaluator_result` | Evaluation score or result |
| `strategy_revision` | Strategy change or reflection |

### Settlement Signals

Signals are inferred from event content and type when not explicitly provided:

- `error_detected`: True for error events or content containing error/traceback/exception/failed/failure/timeout
- `task_complete`: True for task_complete events or content containing "task complete"
- `success_signal`: True when content indicates success (unless failure_signal is also present)
- `failure_signal`: True when content indicates failure
- `test_passed`: True when content indicates tests passed
- `test_failed`: True when content indicates tests failed
- `strategy_revision_detected`: True for strategy_revision events or content containing revised plan/reflect/diagnose/inspect

## Output Structure

Captured traces are written under:

```
data/settlement_datasets/live_harness_traces/<run_id>/
  events.jsonl              # Step-level events, one JSON per line
  run_summary.json          # Run metadata and counts
  settlement_record.json    # Canonical settlement record
  shadow_policy_results.jsonl  # Policy evaluation results (after evaluation)
```

## Enabling and Disabling

Trace capture is **disabled by default**.

### Environment Variables

```bash
# Enable trace capture
export HARNESS_TRACE_CAPTURE_ENABLED=true

# Custom output directory (default: data/settlement_datasets/live_harness_traces)
export HARNESS_TRACE_CAPTURE_DIR=/path/to/traces
```

### Programmatic Usage

```python
from godspeed_nav.trace_capture import HarnessTraceCapture

# Create capture instance (enabled explicitly)
capture = HarnessTraceCapture(
    "my-run-id",
    enabled=True,
    trace_dir="data/settlement_datasets/live_harness_traces",
)

# Record events
capture.record_model_message("Starting task")
capture.record_tool_call("pytest tests/", tool_name="bash")
capture.record_tool_result("2 passed, 1 failed")
capture.record_error("ImportError: module not found")
capture.record_strategy_revision("Revised plan: install missing dependency")
capture.record_task_complete()

# Finalize and write summary files
capture.finalize_run(final_outcome="success", settlement_quality="recovered_success")
```

### Convenience Methods

| Method | Event Type |
|---|---|
| `record_model_message(content)` | `model_message` |
| `record_tool_call(content, tool_name=)` | `tool_call` |
| `record_tool_result(content, tool_name=)` | `tool_result` |
| `record_error(content)` | `error` |
| `record_file_edit(content)` | `file_edit` |
| `record_command(content)` | `command` |
| `record_test_run(content)` | `test_run` |
| `record_final_answer(content)` | `final_answer` |
| `record_task_complete(content)` | `task_complete` |
| `record_evaluator_result(content)` | `evaluator_result` |
| `record_strategy_revision(content)` | `strategy_revision` |

## Converting Traces to Settlement Records

Use the conversion script to transform captured traces into the canonical settlement record schema:

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/convert_live_trace_to_settlement_record.py \
  --run-dir data/settlement_datasets/live_harness_traces/<run_id>/
```

Optional `--output` flag writes to a custom path.

The conversion:
- Maps events to actions (tool_call, command, file_edit, model_message, strategy_revision) and observations (tool_result, error, test_run, evaluator_result)
- Counts turns, tool_calls, commands, errors
- Detects settlement quality from final events
- Includes error_steps, strategy_revision_steps, test_passed/failed_steps in metadata
- Detects same_path_continuation_after_second_error, duplicate_errors, low_cost_inspection_after_error

## Running Policy Evaluation Over Captured Traces

Use the evaluation script to run live shadow policy evaluation:

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/evaluate_live_trace_policies.py \
  --traces-root data/settlement_datasets/live_harness_traces/
```

Or evaluate a single trace:

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/evaluate_live_trace_policies.py \
  --trace-dir data/settlement_datasets/live_harness_traces/<run_id>/
```

The evaluation reports:
- Policy fires (would_fire, fire_timing, recovery_opportunity)
- Uncertainty reasons
- Post-fire outcome
- Whether the trigger occurred before settlement
- Cross-run summary with total fires, timing distribution, and recovery counts

All results have `activation_status: shadow_only` and `enforced: false`. No policy is activated.

## Policy Evidence Focus

The trace capture specifically supports evaluating:

```
require_reflection_before_continuing_after_second_unresolved_error
```

It preserves enough detail to detect:
- First and second unresolved errors (distinct vs duplicate)
- Same-path continuation after second error
- Strategy revision after error
- Low-cost inspection actions after error
- High-payment continuation actions
- Remaining recovery opportunity
- Final settlement timing

## Detection Functions

The module provides standalone detection functions:

| Function | Purpose |
|---|---|
| `detect_duplicate_errors(events)` | True if any two error events have identical content |
| `detect_same_path_continuation(events)` | True if agent continues with high-payment actions after second error |
| `detect_strategy_revision_after_error(events)` | True if strategy revision occurs after latest error |
| `detect_low_cost_inspection_after_error(events)` | True if low-cost inspection occurs within 2 steps of latest error |

## What Future Evidence Would Justify Guarded Activation

Live trace capture is instrumentation only. Guarded activation would require:

1. Multiple live runs where the reflection trigger fires before settlement with recovery opportunity still open.
2. Evidence that the trigger fires on genuinely distinct unresolved errors (not duplicates).
3. Evidence that same-path continuation after the second error leads to worse outcomes than strategy revision.
4. Repeated settlement showing the intervention improves outcomes without harmful side effects.
5. No false positives on traces where the agent successfully recovers without intervention.

The path is:

```
external trace limit discovered
→ live harness trace capture
→ step-level policy evidence
→ guarded experiment only if earned
→ repeated live settlement
→ possible metabolization later
```

## Integration with Existing Systems

- **Live Shadow Policy Evaluator**: Trace events are mapped to the evaluator's event schema via `evaluate_live_trace_policies.py`.
- **Settlement Dataset Adapter Framework**: Converted traces use the canonical settlement record schema.
- **LedgerStore**: Trace capture is independent of the ledger system but writes to compatible JSONL format.
- **Hooks**: Trace capture can be called from hook surfaces if desired, but is not coupled to them.
