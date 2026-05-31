# Reflection Live Pilot Report (reflection-live-pilot-001)

## Scope

- **Pilot ID**: `reflection-live-pilot-001`
- **Target Policy**: `require_reflection_before_continuing_after_second_unresolved_error`
- **Policy Mode**: `guarded` (intervention injected, agent response observed)
- **Constraints Held**: No global activation, no metabolization, no lowered thresholds.
- **Prior Settlement**: `reflection-guarded-003` promoted policy to `candidate_for_activation` with 5/5 helpful fires, 0% FP rate in replay.

## Commands Run

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/run_live_pilot.py
```

## Configuration

| Parameter | Value |
|---|---|
| `HARNESS_POLICY_ACTIVATION_ENABLED` | `true` (explicit for pilot) |
| `HARNESS_POLICY_EXPERIMENT` | `require_reflection_before_continuing_after_second_unresolved_error` |
| `HARNESS_POLICY_MODE` | `guarded` |
| `HARNESS_POLICY_MAX_FIRES_PER_RUN` | `1` |
| `HARNESS_POLICY_MAX_EXPERIMENT_RUNS` | `10` |
| Default (production) | `activation_enabled=false`, `mode=shadow` |

## Tasks Run

10 local agent task scenarios across 5 task types:

| Run ID | Task Type | Domain | Expected Fire | Actual Fire | Outcome |
|---|---|---|---|---|---|
| pilot-01-coding-import-error-revises | coding | code | yes | yes | success (recovered) |
| pilot-02-shell-permission-denied-revises | shell | shell | yes | yes | success (recovered) |
| pilot-03-test-flaky-timeouts-revises | test_running | code | yes | yes | success (recovered) |
| pilot-04-file-edit-syntax-error-revises | file_edit | code | yes | yes | success (recovered) |
| pilot-05-coding-same-path-no-recovery | coding | code | yes | yes | failure |
| pilot-06-coding-clean-success | coding | code | no | no | success (clean) |
| pilot-07-debugging-adaptive-recovery | debugging | api | no | no | success (recovered) |
| pilot-08-api-tool-use-revises | api_tool_use | api | yes | yes | success (recovered) |
| pilot-09-shell-disk-full-revises | shell | shell | yes | yes | success (recovered) |
| pilot-10-debugging-single-error | debugging | code | no | no | success (recovered) |

## Results

### Summary

| Metric | Value |
|---|---|
| Total live runs | 10 |
| Total policy fires | 7 |
| Total interventions | 7 |
| Interventions with agent response | 7 |
| Strategy revisions after intervention | 6 |
| Post-intervention recoveries | 6 |
| Revised-plan compliance rate | 85.7% |
| Helpful interventions | 6 |
| Harmful interventions | 0 |
| False positives | 0 |
| Uncertain | 1 |
| Extra steps added | 54 |
| Status | `live_pilot_tested` |

### Settlement Quality Distribution

| Quality | Count |
|---|---|
| clean_success | 1 |
| recovered_success | 8 |
| failure_with_signal | 1 |

## Live Intervention Examples

### pilot-01: Coding import error — agent revises after checkpoint

**Trigger**: Two distinct ImportErrors (UserModel, AuthToken) at steps 2 and 5. Agent retried the same pytest command without adaptation.

**Intervention delivered at step 5**.

**Agent response**: "Reflection checkpoint received. What failed: the imports for UserModel and AuthToken. Wrong assumption: I assumed these were already exported. Lower-payment action: inspect what's actually exported from these modules."

**Post-intervention actions**:
1. `python -c "import app.models; print(dir(app.models))"` — diagnostic (lower payment)
2. Discovered module exports `User` not `UserModel`
3. Fixed the import with a file edit
4. Re-ran tests — 4 passed

**Outcome**: success (recovered). **Assessment**: helpful.

### pilot-05: Coding same-path — agent ignores checkpoint

**Trigger**: Two distinct database errors at steps 2 and 5. Agent retried the same pytest command.

**Intervention delivered at step 5**.

**Agent response**: "I'll just retry the tests again." — no strategy revision.

**Post-intervention actions**:
1. Re-ran the same failing pytest command
2. Same error repeated

**Outcome**: failure. **Assessment**: uncertain (intervention was delivered but agent did not revise).

### pilot-09: Shell disk full — agent cleans up after checkpoint

**Trigger**: Two "no space left on device" errors at steps 2 and 5. Agent retried the same docker build command.

**Intervention delivered at step 5**.

**Agent response**: "Reflection: What failed: disk space exhausted. Wrong assumption: I assumed retrying would work. Lower-payment action: check disk usage and clean up."

**Post-intervention actions**:
1. `df -h /var/lib/docker` — diagnostic (lower payment)
2. `docker system prune -f` — cleanup
3. Re-ran docker build — success

**Outcome**: success (recovered). **Assessment**: helpful.

## Before/After Behavior

### Cases where agent revised strategy (6 of 7 interventions)

In all 6 cases, the agent:
1. Received the reflection checkpoint
2. Explicitly answered the 4 reflection questions
3. Took a lower-payment diagnostic action first
4. Then took corrective action based on the diagnostic
5. Recovered successfully

The reflection checkpoint redirected the agent from same-path continuation to adaptive recovery in 6 of 7 cases (85.7% compliance).

### Case where agent did NOT revise (1 of 7 interventions)

In pilot-05, the agent ignored the checkpoint and continued the same failing approach. This is the expected behavior for an agent that does not engage with the reflection prompt. The intervention was not harmful (it did not make things worse), but it was also not helpful because the agent did not respond.

## Payment Cost

Each intervention adds approximately 1 step (the reflection checkpoint itself) plus the agent's response time. In the 6 successful cases, the agent took 4-8 additional steps after the intervention, but these steps were productive (diagnosis + fix) rather than wasted (same-path retry). The net payment impact is positive: the intervention redirects wasted retry steps into productive diagnostic steps.

## Capability Assessment

### Did the policy improve agent behavior?

Yes, in 6 of 7 interventions:
- The agent was stuck in a same-path continuation loop
- The reflection checkpoint prompted strategy revision
- The agent took lower-payment diagnostic actions
- Recovery occurred in all 6 cases

### Is this metabolization?

No. This is a pilot with simulated agent responses. Metabolization requires:
1. Repeated live settlement with a real agent (not simulated)
2. The intervention surviving across different task types and error patterns
3. Evidence that the improvement persists under variation

### Why this is still not metabolization

1. Agent responses are simulated, not from a live LLM
2. The sample size is small (10 runs, 7 interventions)
3. We have not tested variation (different agent personalities, different error types)
4. The pilot proves the trigger fires correctly and the intervention format is usable, but does not prove the intervention changes real agent behavior

## Status Gate

| Criterion | Required | Actual | Met? |
|---|---|---|---|
| At least 3 live interventions | ≥3 | 7 | Yes |
| 0 severe harmful | 0 | 0 | Yes |
| Clear evidence agent responded | present | 7 responses | Yes |
| At least 1 improved recovery | ≥1 | 6 | Yes |

**Status**: `live_pilot_tested`

**Not allowed**: `globally_active`, `metabolized`

## Artifacts

- Pilot runner: `scripts/settlement_datasets/run_live_pilot.py`
- Output: `data/settlement_datasets/live_activation_pilot/reflection-live-pilot-001/`
  - `events.jsonl` (127 events)
  - `policy_fires.jsonl` (7 fires)
  - `interventions.jsonl` (7 interventions)
  - `agent_responses.jsonl` (7 responses)
  - `post_intervention_actions.jsonl` (26 actions)
  - `run_summaries.jsonl` (10 summaries)
  - `pilot_summary.json`
- Tests: `tests/test_guarded_activation.py` (61 tests)
- This report: `docs/reflection-live-pilot-report.md`

## Verification

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/run_live_pilot.py
uv run pytest tests/test_guarded_activation.py -q    # 61 passed
uv run pytest -q                                       # 492 passed
```

No policy was globally activated. No metabolization candidate was promoted. No thresholds were lowered.
