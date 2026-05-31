# Live Shadow Policy Instrumentation Report

**Date:** 2026-05-31
**Result:** Live shadow instrumentation exists, replay works offline, and no policy was activated.

## What Was Instrumented

Added `scripts/settlement_datasets/live_shadow_policy_eval.py` with:

- step-level live run event normalization and validation
- deterministic settlement signal inference
- run-state tracking for unresolved errors, strategy revision, task completion, and settlement evidence
- target policy would-fire evaluation
- run-level summaries
- optional config through `SHADOW_POLICY_EVAL_ENABLED`, default off

Added `scripts/settlement_datasets/replay_live_shadow_from_traces.py` for step-level replay from existing settlement records.

Added `schemas/live_shadow_run_event.schema.json` for the event contract.

## How Live Shadow Differs From Offline Shadow

Offline shadow evaluates a completed trace and asks whether a policy would have fired somewhere in the final record.

Live shadow evaluates each step as it arrives. It can record that a policy would have fired before final settlement, then compare that fire to the eventual outcome. This tests whether a policy has a spendable intervention window rather than only a post-hoc label match.

## Target Policies Monitored

- `require_reflection_after_repeated_errors`
- `require_explicit_settlement_for_failure`

Both remain shadow-only. Would-fire records carry `activation_status: shadow_only` and `enforced: false`.

## Replay Output

Replay command:

```bash
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
from scripts.settlement_datasets.adapter_base import read_records_jsonl
from scripts.settlement_datasets.live_shadow_policy_eval import replay_records_to_live_shadow

records = []
for path in sorted(Path("data/settlement_datasets/evidence_accumulation_run/settlements").glob("*.jsonl")):
    records.extend(read_records_jsonl(path))
replay_records_to_live_shadow(records, output_dir="data/settlement_datasets/live_shadow", enabled=True)
PY
```

Artifacts:

| File | Records |
|---|---:|
| `data/settlement_datasets/live_shadow/events.jsonl` | 3123 |
| `data/settlement_datasets/live_shadow/policy_fires.jsonl` | 5 |
| `data/settlement_datasets/live_shadow/run_summaries.jsonl` | 336 |

## Earlier Fire Evidence

Step-level replay produced `5` would-fire events, all for `require_reflection_after_repeated_errors`.

| Metric | Count |
|---|---:|
| Early fires | 1 |
| Middle fires | 3 |
| Late fires | 1 |
| Fires before final | 5 |
| Fires with recovery opportunity | 5 |

This is new temporal evidence. The prior offline adjudication found only final-turn fires for this policy. Live replay shows that step-level instrumentation can see repeated unresolved errors before final settlement closes.

`require_explicit_settlement_for_failure` did not fire in this replay. The current replay surface did not expose a near-closure failure claim without settlement evidence before the task was already settled.

## Limitations

- Replay from historical records approximates live timing from `turn_index`; it is not a real harness run.
- Strategy revision detection is deterministic text matching.
- Recovery opportunity is conservative: a non-settled live step counts as recoverable, but actual recovery still requires later settlement evidence.
- The explicit-settlement policy needs live runs or richer traces with pre-final failure claims.
- No activation recommendation is emitted from this pass.

## Next Validation Needed

Enable `SHADOW_POLICY_EVAL_ENABLED=true` in a controlled harness run and write live events to `data/settlement_datasets/live_shadow/`. Compare post-fire outcomes against runs with no shadow fire. Activation still requires likely-helpful evidence, no harm, acceptable false-positive rate, and live settlement evidence.
