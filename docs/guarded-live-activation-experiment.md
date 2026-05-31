# Guarded Live Activation Experiment

Guarded activation is a controlled experiment for one policy:

```text
require_reflection_after_repeated_errors
```

It is not global activation. It is not metabolization. It adds a soft checkpoint only when repeated unresolved errors continue without a strategy revision and recovery opportunity remains.

## Safe Defaults

Activation is disabled by default.

```text
HARNESS_POLICY_ACTIVATION_ENABLED=false
HARNESS_POLICY_EXPERIMENT=require_reflection_after_repeated_errors
HARNESS_POLICY_MODE=shadow
HARNESS_POLICY_MAX_FIRES_PER_RUN=1
HARNESS_POLICY_MAX_EXPERIMENT_RUNS=20
```

Replay can enable guarded mode explicitly without changing live harness behavior.

## Guarded Checkpoint

When the trigger settles, the experiment records this checkpoint:

```text
Repeated unresolved errors detected. Before continuing, revise the plan using the latest settlement feedback. Identify what failed, what changed, and the next lower-payment action.
```

The checkpoint is soft. It does not terminate the run. The agent may continue after completing the checkpoint.

## Trigger

The guarded trigger requires:

- two or more unresolved error signals
- the same failing path appears to continue
- no strategy revision or reflection occurred since the latest error
- no final answer or task completion has occurred
- recovery opportunity remains

Each intervention records:

```json
{
  "error_events": [],
  "continued_same_path_evidence": [],
  "missing_revision_evidence": [],
  "recovery_opportunity_evidence": []
}
```

## Negative Conditions

The experiment does not fire when:

- task completion is already true
- final answer has already been emitted
- a strategy revision occurred after the latest error
- errors are resolved
- the next action is low-cost inspection
- only one error exists
- the error signals are duplicate mentions of the same output
- no recovery opportunity remains

## Replay

Run guarded activation over live shadow events:

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/replay_guarded_activation.py \
  --input data/settlement_datasets/live_shadow/events.jsonl \
  --run-summaries data/settlement_datasets/live_shadow/run_summaries.jsonl \
  --output data/settlement_datasets/live_activation_experiment \
  --max-runs 400
```

Outputs:

```text
data/settlement_datasets/live_activation_experiment/
  events.jsonl
  policy_fires.jsonl
  interventions.jsonl
  run_summaries.jsonl
  experiment_summary.json
```

## Status Boundary

Successful replay sets the policy to `tested_in_replay` for this experiment surface. It does not make the policy `globally_active` or `metabolized`.
