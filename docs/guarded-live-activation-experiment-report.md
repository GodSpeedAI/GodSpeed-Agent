# Guarded Live Activation Experiment Report

**Date:** 2026-05-31
**Mode:** replay-only guarded activation
**Policy:** `require_reflection_after_repeated_errors`
**Status:** `tested_in_replay`

No policy was globally activated. No candidate was metabolized.

## Commands Run

```bash
uv run pytest tests/test_guarded_activation.py -q

PYTHONPATH=. uv run python scripts/settlement_datasets/replay_guarded_activation.py \
  --input data/settlement_datasets/live_shadow/events.jsonl \
  --run-summaries data/settlement_datasets/live_shadow/run_summaries.jsonl \
  --output data/settlement_datasets/live_activation_experiment \
  --max-runs 400
```

## Artifact Counts

| Artifact | Records |
|---|---:|
| `events.jsonl` | 3123 |
| `policy_fires.jsonl` | 4 |
| `interventions.jsonl` | 4 |
| `run_summaries.jsonl` | 331 |

`experiment_summary.json` records `globally_active: false` and `metabolized: false`.

## Experiment Metrics

| Metric | Value |
|---|---:|
| Runs evaluated | 331 |
| Fires | 4 |
| Interventions | 4 |
| Interventions completed | 0 |
| Interventions after final settlement | 0 |
| Post-intervention recovery count | 0 |
| False-positive count | 4 |
| Harmful intervention count | 0 |
| Uncertain count | 4 |
| Payment cost observed or estimated | null |

The false-positive count means the replay would have inserted a guarded checkpoint into traces that ultimately succeeded without the intervention. This is a friction risk, not observed harm, because replay cannot show an agent response to the checkpoint.

## Timing And Recovery

All guarded interventions occurred before final settlement and included recovery opportunity evidence:

- `run_not_task_complete`
- `final_answer_not_emitted`

Each intervention also included error events, continued same-path evidence, and missing-revision evidence.

## Why Four Interventions Instead Of Five

Live shadow replay produced five would-fire events. Guarded activation injected four interventions because the stricter guarded trigger filtered one prior shadow fire where a strategy revision occurred after the latest error. That exclusion is expected under the guarded experiment's negative conditions.

## Post-Intervention Outcomes

No real guarded run occurred, so no agent completed the checkpoint. Outcomes were copied from the shadow replay baseline only to expose possible friction:

- final outcomes for the four replayed intervention traces were successful
- no intervention completion was observed
- no payment delta was observed
- helpfulness remains `uncertain`

## Recommendation

The policy is ready for a small live guarded run, not global activation. The next run should keep `HARNESS_POLICY_MAX_FIRES_PER_RUN=1`, inspect false-positive friction closely, and compare payment/error deltas against similar shadow-only runs.

Do not mark the policy metabolized. Do not activate `require_explicit_settlement_for_failure`.
