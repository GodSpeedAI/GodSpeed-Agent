# Live Shadow Policy Instrumentation

Live shadow instrumentation records proposed policy would-fire events during a run without enforcing them.

It is a counterfactual ledger:

```text
At step N, policy P would have fired because evidence E was present.
The harness allowed the agent to continue unchanged.
Later, outcome O occurred.
```

This keeps live evidence distinct from activation evidence. No policy blocks behavior, changes prompts, or marks a capability metabolized.

## Event Schema

Step-level events follow [live_shadow_run_event.schema.json](../schemas/live_shadow_run_event.schema.json).

Required fields include `run_id`, `step_index`, `timestamp`, `event_type`, `content`, `tool_name`, `metadata`, and `settlement_signals`.

Settlement signals are deterministic booleans:

- `error_detected`
- `task_complete`
- `success_signal`
- `failure_signal`
- `test_passed`
- `test_failed`

## Evaluator

The evaluator lives in `scripts/settlement_datasets/live_shadow_policy_eval.py`.

Use `LiveShadowPolicyEvaluator.record_event(event)` after each model message, tool call, tool result, error, final answer, task completion, or evaluator result. The method returns would-fire records and never returns an enforcement decision.

The default runtime switch is off:

```bash
SHADOW_POLICY_EVAL_ENABLED=true
```

Code can also pass `enabled=True` directly for replay and tests.

## Target Policies

`require_reflection_after_repeated_errors` fires only when two or more unresolved error signals appear, no strategy revision has happened after the latest error, the run is not settled, closure is not already likely, and recovery opportunity remains.

The shadow action is `would_require_reflection_or_revised_plan`.

`require_explicit_settlement_for_failure` fires when a failure condition is detected, finalization or closure is likely, no explicit settlement evidence has been recorded, and the task is not already settled.

The shadow action is `would_require_explicit_settlement_evidence`.

## Outputs

Replay and live wrappers write:

```text
data/settlement_datasets/live_shadow/
  events.jsonl
  policy_fires.jsonl
  run_summaries.jsonl
```

Run summaries include total steps, final outcome, settlement quality, shadow fires, first fire step, fires before final, fires with recovery opportunity, post-fire outcome, and empty activation recommendations.

## Replay

Replay existing settlement traces step by step:

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/replay_live_shadow_from_traces.py \
  --input data/settlement_datasets/evidence_accumulation_run/settlements/agenttrove.jsonl \
  --output data/settlement_datasets/live_shadow
```

Replay tests whether the same evidence surface can see policy triggers before final settlement closes. It is still shadow mode.

## Guarded Replay Boundary

Guarded activation experiments build on live shadow events. The replay-first guarded experiment lives in `scripts/settlement_datasets/replay_guarded_activation.py` and writes to `data/settlement_datasets/live_activation_experiment/`.

Guarded replay may record soft checkpoint interventions, but this is still not global activation. It is an experiment surface for deciding whether a small live guarded run is worth paying for.
