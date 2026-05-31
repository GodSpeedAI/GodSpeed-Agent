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

---

# Real Agent Pilot Report (reflection-real-agent-002)

## Scope

- **Pilot ID**: `reflection-real-agent-002`
- **Target Policy**: `require_reflection_before_continuing_after_second_unresolved_error`
- **Intervention Format**: Adjusted (with continuation directive)
- **Agent**: Weaker VS Code agent (not GitHub Copilot)
- **Runs**: 10 (5 baseline + 5 guarded), organized as 5 matched pairs
- **Constraints Held**: No global activation, no metabolization, no lowered thresholds.

## Prior Settlement

- `reflection-real-agent-001`: 6 runs, 3 matched pairs. Original format harmful (run-02). Adjusted format: 1 helpful (Task C), 1 neutral (Task B). Status: `needs_more_evidence`.
- This pilot extends to 5 matched pairs with harder tasks designed to produce more errors.

## Protocol

### Adjusted Checkpoint (all guarded runs)

```
Repeated unresolved errors detected. Before continuing, briefly consider:
1. What failed?
2. What assumption may be wrong?
3. What lower-payment action should happen next?
4. What evidence would show the next step worked?

Now continue fixing the code. Implement your fix and re-run the tests.
```

### Evaluation Protocol

1. **Runner phase**: Human operator runs agents in VS Code, pastes transcripts. Orchestrator records structured events.
2. **Evaluator phase**: Independent blinded evaluator scores all 10 runs on 5 dimensions (1-5 scale) from anonymized event data.
3. **Skeptic phase**: Independent skeptic agent reviews evaluator conclusions for bias, overclaiming, and methodological weaknesses.

## Tasks

| Task | Description | Bugs | Baseline Errors |
|---|---|---|---|
| D (inventory) | Fix inventory management bugs | `>=` vs `>` in restock, missing fields in bulk_add | 1 |
| E (CSV parser) | Add quote handling to CSV parser | No quote/escape handling at all | 3 |
| F (build script) | Fix build script bugs | `--check` flag, `wb` mode, missing imports | 4 |
| G (config) | Fix config validation failures | String port `"5432"`, lowercase `"debug"` | 1 |
| H (HTTP client) | Fix HTTP client bugs | Dict body not encoded, string timeout | 1 |

## Results

### Run-by-Run Summary

| Run | Condition | Task | Errors | Test Runs | Checkpoint | Completed |
|---|---|---|---|---|---|---|
| run-07 | Baseline | D | 1 | 2 | No | Yes |
| run-08 | Guarded | D | 1 | 2 | No | Yes |
| run-09 | Baseline | E | 3 | 4 | No | Yes |
| run-10 | Guarded | E | 1 | 2 | No | Yes |
| run-11 | Baseline | F | 4 | 5 | No | Yes |
| run-12 | Guarded | F | 2 | 3 | **Yes** | Yes |
| run-13 | Baseline | G | 1 | 2 | No | Yes |
| run-14 | Guarded | G | 4 | 4 | **Yes** | Yes |
| run-15 | Baseline | H | 1 | 2 | No | Yes |
| run-16 | Guarded | H | 1 | 2 | No | Yes |

### Matched-Pair Comparisons

#### Task D: No intervention (too easy)

Both runs had 1 error, fixed immediately. The checkpoint could not fire. Inconclusive.

#### Task E: No intervention (guarded run was faster)

Baseline had 3 errors (agent broke file with SyntaxError, then introduced new bugs during rewrite). Guarded had only 1 error (agent went straight to csv module). No checkpoint was delivered. The difference is random variation, not a policy effect. Inconclusive.

#### Task F: Checkpoint delivered — HELPFUL

Baseline had 4 errors across 5 test runs. Agent kept breaking the test file with missing imports (3 times). Guarded had 2 errors across 3 test runs. Checkpoint was delivered after the 2nd error. Post-checkpoint, the agent focused only on build.py, did not corrupt the test file, and fixed the remaining bug correctly on the first attempt.

**Verdict: HELPFUL.** The checkpoint was associated with cleaner recovery, fewer errors, fewer test runs, and no test file corruption.

#### Task G: Checkpoint delivered — NEUTRAL/NEGATIVE

Baseline had 1 error (agent weakened the validator to accept bad data instead of fixing settings.json — debatable fix quality but clean execution). Guarded had 4 errors. The agent's first edit introduced an IndentationError. The checkpoint was delivered after the 2nd error. The agent's immediate post-checkpoint edit was STILL broken (SyntaxError: return outside function). The agent recovered on its own by reading the full file. Reflection answers were post-hoc (written after the fix, not before).

**Verdict: NEUTRAL to NEGATIVE.** The checkpoint did not help — the agent's first post-checkpoint action was worse. The checkpoint also did not redirect the agent's approach (both runs weakened the validator instead of fixing the data).

#### Task H: No intervention (too easy)

Both runs had 1 error, fixed immediately. Inconclusive.

### Blinded Evaluator Scores

An independent evaluator scored all 10 runs from anonymized event data (run IDs replaced with Run-Alpha through Run-Kappa, intervention events removed, revealing metadata stripped).

#### Aggregate Scores (all 5 pairs)

| Dimension | Baseline Avg | Guarded Avg | Delta |
|---|---|---|---|
| Error Recovery Efficiency | 3.8 | 4.2 | +0.4 |
| Edit Quality | 3.6 | 3.8 | +0.2 |
| Diagnostic Accuracy | 3.6 | 4.0 | +0.4 |
| Strategy Adaptation | 4.4 | 4.4 | 0.0 |
| Overall Execution | 3.6 | 4.0 | +0.4 |

#### Intervention-Only Scores (2 pairs where checkpoint was delivered)

| Dimension | Baseline Avg | Guarded Avg | Delta |
|---|---|---|---|
| Error Recovery Efficiency | 3.5 | 3.0 | -0.5 |
| Edit Quality | 3.0 | 2.5 | -0.5 |
| Diagnostic Accuracy | 3.0 | 3.0 | 0.0 |
| Strategy Adaptation | 4.5 | 3.5 | -1.0 |
| Overall Execution | 3.0 | 3.0 | 0.0 |

The aggregate advantage is inflated by Task E (no checkpoint delivered, guarded run was randomly better). When restricted to actual checkpoint deliveries, guarded runs score equal or worse.

### Skeptic Review

An independent skeptic agent reviewed all data and evaluator conclusions. Key findings:

| Claim | Skeptic Rating |
|---|---|
| "Adjusted format is never harmful" | **EVIDENCE AGAINST** — Run-14 received checkpoint, then produced post-checkpoint syntax error and worse scores than baseline |
| "Checkpoint was helpful in Task F" | **WEAK EVIDENCE** — Best favorable signal, but one matched pair is suggestive not conclusive |
| "Checkpoint was neutral in Task G" | **EVIDENCE AGAINST** — Run-14 was worse on every dimension; "neutral" understates unfavorable evidence |
| "Aggregate guarded advantage" | **WEAK EVIDENCE** — Mostly from no-checkpoint runs, cannot attribute to intervention |
| "Intervention-only shows no benefit" | **WEAK EVIDENCE** — N=2 too small for stable estimate |

## Key Findings

### Finding 1: Trigger Reach Is the Primary Constraint

3 of 5 tasks were "too easy" — the agent completed after 1 error, so the checkpoint never fired. The policy's value depends on encountering tasks that produce repeated unresolved errors. This may reflect real-world conditions (many coding tasks resolve quickly) but means the policy has narrow reach.

### Finding 2: Mixed Results When Checkpoint Was Delivered

Of 2 checkpoint deliveries: 1 helpful (Task F), 1 unfavorable (Task G). The helpful case showed cleaner recovery and better scoping. The unfavorable case showed the agent making a worse edit immediately after the checkpoint. The checkpoint did not cause the initial struggle but also did not prevent the post-checkpoint error.

### Finding 3: Aggregate Advantage Is Misleading

The aggregate guarded advantage (+0.4 on several dimensions) is inflated by Task E, where no checkpoint was delivered and the guarded run was randomly better. When restricted to actual interventions, the signal is null or negative.

### Finding 4: Reflection Timing Matters

In Task F (helpful), the agent reflected before acting and the reflection appeared to guide behavior. In Task G (unfavorable), the reflection was post-hoc — the agent answered the questions after already completing the fix. Post-hoc reflection cannot guide behavior.

### Finding 5: The "Never Harmful" Claim Is Not Supported

The skeptic rated this as EVIDENCE AGAINST. Run-14's post-checkpoint behavior was worse than baseline. While causality is uncertain (the agent was already struggling), the universal safety claim is not supported by 2 delivered checkpoints.

### Finding 6: Protocol Error Discovered and Fixed

The reset script for Task G only restored `settings.json`, not `config_loader.py`. Run-13's validator changes persisted into the initial run-14 attempt, producing an invalid run. The script was fixed and run-14 was re-run. This is a protocol integrity finding — reset scripts must restore all mutable files.

## Status Gate

| Criterion | Required | Actual | Met? |
|---|---|---|---|
| At least 5 matched pairs | ≥5 | 5 | Yes |
| Checkpoint delivered in ≥3 pairs | ≥3 | 2 | **No** |
| Majority of deliveries helpful | >50% | 1/2 (50%) | **No** |
| 0 harmful with adjusted format | 0 | 0 clear harm, 1 unfavorable | Marginal |
| Blinded evaluation | Done | Yes | Yes |
| Skeptic review | Done | Yes | Yes |
| Sufficient for activation | ≥5 consistent | 1 helpful, 1 unfavorable | **No** |

**Status**: `needs_more_evidence`

**Not allowed**: `globally_active`, `metabolized`

## Combined Evidence (Both Pilots)

| Metric | Pilot-001 | Pilot-002 | Combined |
|---|---|---|---|
| Total runs | 6 | 10 | 16 |
| Matched pairs | 3 | 5 | 8 |
| Checkpoint deliveries | 2 | 2 | 4 |
| Helpful | 1 | 1 | 2 |
| Neutral | 1 | 0 | 1 |
| Unfavorable | 0 | 1 | 1 |
| Harmful (original format) | 1 | 0 | 1 |
| No intervention | 2 | 6 | 8 |

The combined evidence shows the adjusted format can be delivered without stopping the agent (4/4 completions). Results are mixed: 2 helpful, 1 neutral, 1 unfavorable. The sample is too small for reliable conclusions.

## Artifacts

- Events: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/events.jsonl`
- Policy fires: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/policy_fires.jsonl`
- Interventions: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/interventions.jsonl`
- Runner responses: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/runner_responses.jsonl`
- Run summaries: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/run_summaries.jsonl`
- Blinded evaluator events: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/evaluator_blinded_events.jsonl`
- Evaluator scores: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/evaluator_scores.jsonl`
- Unblinding key: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/unblinding_key.json`
- Skeptic review: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/skeptic_reviews.jsonl`
- Pilot summary: `data/settlement_datasets/real_agent_pilot/reflection-real-agent-002/pilot_summary.json`
- Task workspaces: `tmp/pilot_tasks/task_d/` through `tmp/pilot_tasks/task_h/`
- Reset script: `tmp/pilot_tasks/reset_pilot2.sh`
- This report: `docs/reflection-real-agent-pilot-report.md`

## Recommendations

1. **Design harder tasks** that reliably produce 3+ errors. 3 of 5 tasks were too easy for the policy to trigger. Future tasks should have multiple interacting bugs that require sequential fixes.
2. **Run more matched pairs** with checkpoint-eligible tasks. The current 4 deliveries (2 helpful, 1 neutral, 1 unfavorable) are insufficient for any conclusion.
3. **Investigate reflection timing**. The helpful case (Task F) had pre-action reflection; the unfavorable case (Task G) had post-hoc reflection. The intervention may need to enforce a pause before the agent's next action.
4. **Do not activate the policy globally**. The evidence does not support consistent benefit or consistent safety.
5. **Consider a pilot-003** with 5+ checkpoint-eligible tasks, repeated runs per task (to separate policy effects from stochastic variation), and multiple blinded evaluators.

No policy was globally activated. No metabolization candidate was promoted. No thresholds were lowered.
