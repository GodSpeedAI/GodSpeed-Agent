# Real Agent Pilot Report (reflection-real-agent-001)

## Scope

- **Pilot ID**: `reflection-real-agent-001`
- **Target Policy**: `require_reflection_before_continuing_after_second_unresolved_error`
- **Agent**: Weaker VS Code agent (not GitHub Copilot)
- **Runs**: 6 (3 baseline + 3 guarded), organized as 3 matched pairs
- **Constraints Held**: No global activation, no metabolization, no lowered thresholds.

## Prior Settlement

- `reflection-guarded-003`: 5/5 helpful fires, 0% FP rate in replay. Status: `candidate_for_activation`.
- `reflection-live-pilot-001`: 10 simulated runs, 7 fires, 6 helpful, 0 harmful. Status: `live_pilot_tested`.
- Both used **simulated** agent responses. This pilot uses **real** agents.

## Protocol

### Original Checkpoint (run-02 only)

```
Repeated unresolved errors detected.
Before continuing, revise the plan using the latest settlement feedback:
1. What failed?
2. What assumption may be wrong?
3. What lower-payment action should happen next?
4. What evidence would show the next step worked?
```

### Adjusted Checkpoint (runs 04, 06)

```
Repeated unresolved errors detected. Before continuing, briefly consider:
1. What failed?
2. What assumption may be wrong?
3. What lower-payment action should happen next?
4. What evidence would show the next step worked?

Now continue fixing the code. Implement your fix and re-run the tests.
```

The adjustment adds a single continuation directive after the reflection questions.

## Tasks

| Task | Description | Trap |
|---|---|---|
| A (pipeline) | Fix data transformation bugs | Two bugs: email stripping + status lowercasing |
| B (server) | Fix database path + server issues | Bad config path + row_factory + duplicate items |
| C (scheduler) | Fix overdue detection logic | `>=` vs `>` boundary + `summary()` not passing `as_of` |

## Results

### Run-by-Run Summary

| Run | Condition | Task | Outcome | Errors | Test Runs | Same-Path Retries | Completed |
|---|---|---|---|---|---|---|---|
| run-01 | Baseline | A | Success | 2 | 2 | 0 | Yes |
| run-02 | Guarded (original) | A | **Failure** | 1 | 1 | 0 | **No** |
| run-03 | Baseline | B | Success | 3 | 4 | 0 | Yes |
| run-04 | Guarded (adjusted) | B | Success | 5 | 6 | 1 | Yes |
| run-05 | Baseline | C | Success | 3 | 4 | 1 | Yes |
| run-06 | Guarded (adjusted) | C | Success | 2 | 3 | 0 | Yes |

### Matched-Pair Comparisons

#### Task A: Baseline success vs Guarded failure

The original checkpoint format caused the agent to stop after producing a correct analysis. The agent identified all 3 bugs, proposed fixes, and listed evidence criteria — but never implemented any changes. The code was unchanged and tests still failed.

**Verdict: HARMFUL.** The intervention prevented task completion.

#### Task B: Baseline 4 test runs vs Guarded 6 test runs

The adjusted format prevented the stop behavior. The agent continued working after the checkpoint and completed the task. However, the guarded run took more test runs (6 vs 4) and hit more errors (5 vs 3). The checkpoint did not improve efficiency.

**Verdict: NEUTRAL (slightly negative).** The intervention was not harmful but did not help.

#### Task C: Baseline 4 test runs vs Guarded 3 test runs

The adjusted format prompted the agent to read the code more carefully before re-running tests. The guarded run had fewer test runs (3 vs 4), fewer errors (2 vs 3), and no same-path retry (baseline had 1). The agent produced a structured reflection summary mapping to the 4 questions.

**Verdict: HELPFUL.** The intervention improved agent behavior on all measured metrics.

## Key Findings

### Finding 1: Checkpoint Format Is Critical

The original format (questions only) caused the agent to treat the reflection as a final task. The adjusted format (adding "Now continue fixing the code.") prevented this. This is the most actionable finding from the pilot — the policy's intervention text must include an explicit continuation directive for weaker agents.

### Finding 2: Mixed Helpfulness with Adjusted Format

With the adjusted format, results were mixed: neutral in Task B and helpful in Task C. The helpful signal from Task C is encouraging but a single data point.

### Finding 3: Agent Sophistication Matters

GitHub Copilot (tested in preliminary runs) adapted after a single error and never triggered the policy. The weaker agent was more likely to hit repeated errors and benefit from intervention. The policy's value is agent-dependent.

### Finding 4: Small Sample

6 runs with 3 matched pairs is insufficient for statistical conclusions. The helpful signal from Task C could be noise. More runs are needed.

### Finding 5: No Metabolization

This pilot does not metabolize the policy. It provides real-agent evidence that must be combined with existing replay and simulated pilot evidence.

## Status Gate

| Criterion | Required | Actual | Met? |
|---|---|---|---|
| At least 3 matched pairs | ≥3 | 3 | Yes |
| At least 1 helpful intervention | ≥1 | 1 | Yes |
| 0 harmful with adjusted format | 0 | 0 | Yes |
| Clear format finding | present | Yes | Yes |
| Sufficient for activation | ≥5 consistent | 1 helpful, 1 neutral | No |

**Status**: `needs_more_evidence`

**Not allowed**: `globally_active`, `metabolized`

## Artifacts

- Pilot plan: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-001/PILOT_PLAN.md`
- Events: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-001/events.jsonl`
- Policy fires: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-001/policy_fires.jsonl`
- Interventions: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-001/interventions.jsonl`
- Runner responses: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-001/runner_responses.jsonl`
- Run summaries: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-001/run_summaries.jsonl`
- Pilot summary: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-001/pilot_summary.json`
- Task workspaces: `tmp/pilot_tasks/task_a/`, `tmp/pilot_tasks/task_b/`, `tmp/pilot_tasks/task_c/`
- This report: `docs/reflection-real-agent-pilot-report.md`

## Recommendations

1. **Update the intervention text** to include the continuation directive before any further testing.
2. **Run additional matched pairs** (at least 5 more) with the adjusted format to determine whether the Task C helpful signal is consistent.
3. **Test with multiple agent models** to map the policy's effectiveness across the agent sophistication spectrum.
4. **Do not activate the policy globally** until the adjusted format shows consistent helpful results across multiple agents and task types.

No policy was globally activated. No metabolization candidate was promoted. No thresholds were lowered.
