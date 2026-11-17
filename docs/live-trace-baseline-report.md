# Live Trace Baseline Collection Report

> **Superseded by F-08.** GodSpeed-Agent no longer owns live trace capture;
> SWE_SEED is the proven owner. Calibration traces are now explicit synthetic
> fixtures (`scripts/settlement_datasets/synthetic_trace_fixture.py`). This
> report and its generated artifacts are retained as historical provenance only.

## Scope

- Pass: Live Trace Baseline Collection
- Target policy: `require_reflection_before_continuing_after_second_unresolved_error`
- Policy mode: `shadow_only` (no activation, no enforcement)
- Constraints held: no policy activation, no lowered thresholds, no metabolization changes.

## Commands Run

```bash
# Collect 13 baseline traces
PYTHONPATH=. uv run python scripts/settlement_datasets/collect_baseline_traces.py

# Run shadow policy evaluation over all traces
PYTHONPATH=. uv run python scripts/settlement_datasets/evaluate_live_trace_policies.py \
  --traces-root data/settlement_datasets/live_harness_traces

# Convert each trace to canonical settlement record
for d in data/settlement_datasets/live_harness_traces/baseline-*/; do
  PYTHONPATH=. uv run python scripts/settlement_datasets/convert_live_trace_to_settlement_record.py --run-dir "$d"
done
```

## Traces Captured

13 baseline traces collected across 6 task types:

| Run ID | Task Type | Domain | Steps | Errors | Outcome |
|---|---|---|---|---|---|
| baseline-001-coding-import-error-same-path | coding | code | 10 | 4 | failure |
| baseline-002-debugging-test-failures-revision | debugging | code | 14 | 3 | success |
| baseline-003-shell-permission-denied | shell | shell | 12 | 2 | success |
| baseline-004-test-running-flaky-timeouts | test_running | code | 10 | 6 | failure |
| baseline-005-file-edit-syntax-error | file_edit | code | 14 | 3 | success |
| baseline-006-api-rate-limiting | api_tool_use | api | 10 | 0 | success |
| baseline-007-coding-type-error-inspection | coding | code | 14 | 2 | success |
| baseline-008-debugging-missing-dependency | debugging | code | 11 | 3 | success |
| baseline-009-shell-disk-full | shell | shell | 12 | 2 | success |
| baseline-010-coding-clean-success | coding | code | 10 | 0 | success |
| baseline-011-test-running-mixed-results | test_running | code | 13 | 5 | success |
| baseline-012-api-connection-refused | api_tool_use | api | 12 | 0 | success |
| baseline-013-coding-duplicate-error-no-recovery | coding | code | 7 | 2 | failure |

## Valid Settlement Records

All 13 traces converted to canonical settlement records with zero validation errors. Each record contains all required canonical fields (dataset, domain, task_id, source_uri, desired_direction, environment, representational_state, payment, affordance_path, outcome, labels, metadata).

## Shadow Policy Fires

### Summary

| Metric | Value |
|---|---|
| Total runs | 13 |
| Total shadow fires | 12 |
| Runs with fires | 9 |
| Runs without fires | 4 |
| Fires before settlement | 9 |
| Policy activation count | 0 |

### Fire Timing Distribution

| Timing | Count |
|---|---|
| early | 1 |
| middle | 8 |
| final_turn | 3 |
| no_fire | 4 |

### Recovery Opportunity

| Metric | Value |
|---|---|
| Fires with recovery opportunity | 12 |
| Fires without recovery opportunity | 0 |
| Runs with pre-settlement fires and recovery opportunity | 9 |

### By Policy

| Policy | Fires | Pre-Settlement | Recovery Opportunity |
|---|---|---|---|
| `require_reflection_after_repeated_errors` | 9 | 9 | 9 |
| `require_explicit_settlement_for_failure` | 3 | 0 | 3 |

### Final Outcome Distribution

| Outcome | Count |
|---|---|
| success | 10 |
| failure | 3 |

## Fires Before Final Settlement

9 of 12 fires occurred before final settlement. This is a significant improvement over the AgentTrove evidence where all 4 fires were on `final_turn` with 0 recovery opportunity.

## What Happened After Would-Fire Points

### Runs where reflection policy fired and agent succeeded without intervention

| Run | Fire Step | Fire Timing | Post-Fire Outcome |
|---|---|---|---|
| baseline-002-debugging-test-failures-revision | 5 | middle | succeeded_without_intervention |
| baseline-003-shell-permission-denied | 4 | middle | succeeded_without_intervention |
| baseline-005-file-edit-syntax-error | 5 | middle | succeeded_without_intervention |
| baseline-008-debugging-missing-dependency | 4 | middle | succeeded_without_intervention |
| baseline-009-shell-disk-full | 4 | middle | succeeded_without_intervention |
| baseline-011-test-running-mixed-results | 2 | middle | succeeded_without_intervention |

In all 6 cases, the agent eventually recovered without intervention. In 4 of these (002, 003, 005, 009), the agent performed a strategy revision after the fire point, which is exactly the behavior the policy would encourage. In the other 2 (008, 011), the agent found a working approach through continued exploration.

### Runs where reflection policy fired and agent failed

| Run | Fire Step | Fire Timing | Post-Fire Outcome |
|---|---|---|---|
| baseline-001-coding-import-error-same-path | 5 | middle | failed |
| baseline-004-test-running-flaky-timeouts | 2 | early | failed |
| baseline-013-coding-duplicate-error-no-recovery | 4 | middle | failed |

In baseline-001, the agent continued retrying the same failing command after the fire point (same-path continuation). In baseline-004, the agent retried the same flaky test with increasing timeouts. In baseline-013, the agent had duplicate errors and gave up. These are the cases where the policy intervention might have been most helpful.

## Examples of Traces with Fires

### baseline-001: Coding import error with same-path continuation

The agent encountered two distinct ImportError messages (UserModel, then AuthToken) and continued retrying the same pytest command. The reflection policy fired at step 5 (middle timing) with recovery opportunity. The agent did not revise strategy and ultimately failed. This is the strongest candidate for a helpful intervention: the agent was stuck in a same-path loop and a reflection prompt might have redirected it to inspect the module exports.

### baseline-004: Test running with flaky timeouts

The agent encountered repeated TimeoutError from a test and kept increasing the timeout. The reflection policy fired early (step 2) with recovery opportunity. The agent did not revise strategy and ultimately failed. An intervention here might have prompted the agent to investigate the root cause rather than treating it as a timeout issue.

### baseline-009: Shell disk full with strategy revision

The agent encountered two "No space left on device" errors, then performed a strategy revision (cleaning up Docker data). The reflection policy fired at step 4 (middle timing) with recovery opportunity. The agent recovered without intervention. This shows the policy firing on a case where the agent eventually found the right approach, but the fire occurred before the strategy revision.

## Examples with Suppressions

### baseline-006: API rate limiting (no fire)

The agent encountered HTTP 429 rate limiting responses. However, the signal inference did not flag these as `error_detected` because the content "HTTP 429: Rate limit exceeded" does not contain the specific error tokens checked by the inference function. This is a limitation of the current signal inference, not a suppression.

### baseline-007: Coding type error with inspection (no fire)

The agent encountered a TypeError, then immediately inspected the code ("Let me inspect the pipeline code to understand the None handling"). The inspection content triggered `strategy_revision_detected`, which cleared the unresolved error count. A second error occurred later but the count was only 1, so the reflection trigger did not fire. This is a correct suppression: the agent performed low-cost inspection after the first error.

### baseline-010: Clean success (no fire)

No errors occurred. No fires expected.

### baseline-012: API connection refused (no fire)

The agent encountered "Connection refused" errors, but the signal inference did not flag these as `error_detected` because "Connection refused" does not match the specific error tokens. This is a signal inference limitation.

## Limitations

1. **Simulated traces**: These traces were generated through the actual `HarnessTraceCapture` API with realistic agent interaction patterns, but they are not captured from live agent execution against real tasks. They represent plausible agent behavior, not observed agent behavior. The trace capture infrastructure is real; the event sequences are constructed.

2. **Signal inference gaps**: The settlement signal inference misses some error patterns:
   - "HTTP 429: Rate limit exceeded" is not detected as an error
   - "Connection refused" is not detected as an error
   - These gaps mean some runs that should have error signals do not, potentially causing under-counting of policy fires.

3. **Strategy revision detection is broad**: The inference function flags "inspect", "diagnose", "check", "look", and "examine" as strategy revision indicators. This means some low-cost inspection actions that are not true strategy revisions still clear the unresolved error count, potentially suppressing legitimate fires.

4. **Small sample size**: 13 traces is a minimum baseline. Statistical conclusions are not warranted. The evidence supports the hypothesis that the reflection trigger can fire before settlement with recovery opportunity, but does not establish how often this happens in real agent execution.

5. **No real intervention effects**: Because this is shadow-only evaluation, we cannot observe what would have happened if the policy had actually intervened. The "succeeded_without_intervention" outcomes do not prove the intervention would have been harmful; they only show the agent recovered on its own.

6. **No diversity in agent behavior**: All traces represent a single agent behavior pattern. Real agents may exhibit different error recovery patterns, different strategy revision frequencies, and different same-path continuation tendencies.

## Recommendation

### Does the reflection policy have enough live-shadow evidence for a guarded activation experiment?

**Conditional yes, with caveats.**

The baseline shows:

- 9 pre-settlement fires with recovery opportunity across 13 runs (69%)
- 3 runs where the agent failed after the fire point without strategy revision (baseline-001, baseline-004, baseline-013)
- 6 runs where the agent succeeded without intervention after the fire point
- 0 harmful fires (no fires on clean-success runs)
- Correct suppressions for strategy revision and low-cost inspection cases

The strongest evidence for a guarded experiment comes from the 3 failure runs where the agent continued on the same path after the second error without revising strategy. In these cases, a reflection prompt might have redirected the agent toward a more productive approach.

However, the caveats are significant:

1. The traces are simulated, not from live agent execution.
2. The sample size is small (13 runs).
3. The 6 "succeeded_without_intervention" cases mean the policy would have fired on runs that ultimately succeeded, which is the definition of a false positive from the agent's perspective.
4. The signal inference gaps mean the real fire rate may be different in production.

**Recommended next step**: Before a guarded activation experiment, collect traces from actual live agent execution (not simulated). The trace capture infrastructure is ready. The baseline proves the pipeline works end-to-end. The next affordable step is to enable trace capture during real agent work and evaluate whether the same fire patterns appear.

The path remains:

```
simulated baseline (this pass)
→ live agent trace capture (next step)
→ step-level policy evidence from real execution
→ guarded experiment only if earned
→ repeated live settlement
→ possible metabolization later
```

## Guarded Activation Experiment Follow-Up

The guarded activation experiment (`reflection-guarded-001`) has been completed using these 13 baseline traces. Results:

- 4 interventions across 13 runs
- 2 potentially helpful (baseline-001, baseline-004 — both failures with same-path continuation)
- 2 false positives (baseline-002, baseline-008 — both recovered without intervention)
- 0 harmful
- Status: `tested_needs_more_evidence`

See `docs/guarded-activation-experiment-report.md` for the full experiment report.

## Artifacts

- Collection script: `scripts/settlement_datasets/collect_baseline_traces.py`
- Traces: `data/settlement_datasets/live_harness_traces/baseline-*/`
- Manifest: `data/settlement_datasets/live_harness_traces/baseline_collection_manifest.json`
- Shadow summary: `data/settlement_datasets/live_harness_traces/shadow_policy_summary.json`
- This report: `docs/live-trace-baseline-report.md`
