# Reflection Targeted Evidence Run Report

## Scope

- Run id: `reflection-target-001`
- Run directory: `data/settlement_datasets/runs/reflection-target-001/`
- Dataset: `agenttrove`
- Governing question: Can we find traces where `require_reflection_before_continuing_after_second_unresolved_error` would fire early enough to matter?
- Constraints held: no policy activation, no lowered thresholds, no metabolization changes.

## Command

```bash
uv run python -m scripts.settlement_datasets.run_evidence_pipeline \
  --run-id reflection-target-001 \
  --dataset agenttrove \
  --input data/settlement_datasets/evidence_accumulation_run/raw_samples/agenttrove.jsonl \
  --limit 500 \
  --min-confidence 0.65 \
  --target-profile reflection_second_unresolved_error \
  --enable-live-shadow-replay
```

## Result

Answer: no on this 500-trace slice.

The refined reflection policy now has real supporting fires on the targeted slice, but every fire lands on the final turn with no recovery opportunity remaining. That means the run found traces that satisfy the normalized evidence profile, but it did not find any trace where the policy would fire early enough to change the path before settlement closed.

## Counts

- Sampled traces: `500`
- High-confidence traces at `>= 0.65`: `270`
- Target-profile matches: `4`
- Normalized targeted records forwarded downstream: `4`
- Labeled targeted records: `4`
- Traces with two or more unresolved errors: `174`
- Traces with same-path continuation after the second error: `199`
- Traces with no strategy revision after the latest error: `500`
- Traces with recovery actions after error: `232`
- Traces with recovery opportunity remaining under the target filter: `159`
- Reflection policy `would_fire_count`: `4`
- Reflection policy `pre_settlement_fire_count`: `0`
- Reflection policy `recovery_opportunity_count`: `0`
- Reflection-policy fire timing distribution: `final_turn=4`
- Reflection-policy assessment distribution: `uncertain=4`
- Total shadow fires across all policies on the targeted slice: `5`
- Reflection-policy activation count: `0`
- Live-shadow fires: `0`

## Target Filter Behavior

The target filter worked after alignment with the actual normalized AgentTrove evidence surface. The important correction was to treat normalized deterministic signals as spendable evidence when explicit copied terminal-output observations were absent.

Operational evidence used by the final run:

- `payment.error_count`
- `payment.evidence` entries such as `recovery_attempt_count:N`
- `labels.failure_mode_evidence` entries such as `error_at_turn:N`
- Explicit observation-level error outputs when they exist

This made the run operationally honest about the preserved schema instead of pretending copied terminal output was the only usable error surface.

## Qualifying Trace Examples

- `at-1fa6dff6686c`: target match, inferred second error, `recovery_attempt_count=3`, target-filter fire timing `middle`, shadow result `would_fire=true`, final-turn fire, no recovery opportunity.
- `codeforces-00033`: target match, inferred second error, `recovery_attempt_count=2`, target-filter fire timing `middle`, shadow result `would_fire=true`, final-turn fire, no recovery opportunity.
- `codeforces-00090`: target match, inferred second error, `recovery_attempt_count=3`, target-filter fire timing `middle`, shadow result `would_fire=true`, final-turn fire, no recovery opportunity.
- `codeforces-00091`: target match, inferred second error, `recovery_attempt_count=2`, target-filter fire timing `middle`, shadow result `would_fire=true`, final-turn fire, no recovery opportunity.

## Rejected Examples

- `at-61bf56ea495a`: rejected for `low_cost_inspection_after_error` and `recovery_window_not_open`.
- `at-132b1cb5612c`: rejected for `no_tool_or_environment_error`, `fewer_than_two_unresolved_errors`, `no_same_path_continuation_after_second_error`, and `recovery_window_not_open`.
- `at-ee280494f975`: rejected for `fewer_than_two_unresolved_errors`, `no_same_path_continuation_after_second_error`, and `recovery_window_not_open`.
- `at-988b662a5d70`: rejected for `no_tool_or_environment_error`, `fewer_than_two_unresolved_errors`, `no_same_path_continuation_after_second_error`, and `recovery_window_not_open`.
- `at-8e77a719a1ac`: rejected for `below_min_confidence`, `fewer_than_two_unresolved_errors`, `no_same_path_continuation_after_second_error`, and `recovery_window_not_open`.

## Interpretation

The targeted pass answers two different questions separately:

1. Can we now isolate traces that look like second-unresolved-error continuation cases on the normalized AgentTrove surface?
   Yes. The corrected target filter isolated `4` such traces.

2. Do those traces show the refined reflection policy firing early enough to matter?
   No. All `4` authoritative shadow fires were `final_turn` fires with `0` recovery opportunity.

So the current evidence does not justify a guarded experiment for this refined reflection policy on this slice.

## Recommendation

- Run recommendation: `needs_more_evidence`
- Policy row recommendation in the shadow summary: `keep_proposed`

Reasoning: the policy now has real would-fire support, but that support is entirely late and non-intervenable on this slice. The result strengthens the case that the refined trigger is more precise than the earlier broad version, but it does not yet demonstrate spendable pre-settlement leverage.

## Follow-Up: Live Harness Trace Capture

The AgentTrove limitation identified in this report (all fires on `final_turn` with `0` recovery opportunity) led to the implementation of live harness trace capture (`godspeed_nav/trace_capture.py`). Live traces record step-level events with settlement signals preserved at each step, enabling evaluation of whether the reflection trigger could fire before settlement closes in real harness execution.

See `docs/live-harness-trace-capture.md` and `docs/live-harness-trace-capture-report.md` for details.
