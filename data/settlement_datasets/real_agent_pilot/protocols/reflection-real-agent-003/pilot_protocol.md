# Pilot Protocol: reflection-real-agent-003

## Identity

- **Protocol ID**: `reflection-real-agent-003`
- **Status**: `pre_registered` (frozen, awaiting independent review)
- **Date Registered**: 2026-05-31
- **Policy Under Test**: `require_reflection_before_continuing_after_second_unresolved_error`
- **Intervention Format**: Adjusted with continuation directive (see below)
- **Predecessors**: pilot-001 (6 runs, mixed), pilot-002 (10 runs, mixed)

## Intervention Text (frozen)

```
Repeated unresolved errors detected. Before continuing, briefly consider:
1. What failed?
2. What assumption may be wrong?
3. What lower-payment action should happen next?
4. What evidence would show the next step worked?

Now continue fixing the code. Implement your fix and re-run the tests.
```

This text must be used verbatim for all guarded runs. No modifications permitted during the pilot.

## Hypothesis (non-directional)

The adjusted reflection checkpoint may change agent behavior when delivered after repeated unresolved errors. The direction of change (helpful, neutral, or harmful) is not predicted. This pilot exists to observe what happens, not to confirm a benefit.

## Design

### Matched-Pair Structure

- 6 tasks (I through N), each run twice: once baseline, once guarded.
- Total: 12 runs.
- Run order: counterbalanced by task using the frozen order table below.
- Each task is independent. No task shares code or dependencies with another.

### Frozen Run Order

Condition order is fixed before execution to reduce systematic baseline-first bias:

| Task | First Run | Second Run |
|---|---|---|
| I | Baseline | Guarded |
| J | Guarded | Baseline |
| K | Baseline | Guarded |
| L | Guarded | Baseline |
| M | Baseline | Guarded |
| N | Guarded | Baseline |

Each run must start from a reset workspace. The reset state used for baseline and guarded runs of the same task must be byte-identical.

### Conditions

| Condition | Description |
|---|---|
| Baseline | Agent receives task prompt only. No checkpoint. |
| Guarded | Agent receives task prompt. If the agent encounters a 2nd unresolved error (test still failing after a fix attempt), the operator injects the checkpoint text as a user message. |

### Policy Fire Criteria

A "policy fire" occurs when:

1. The agent has run tests and observed failures (error event 1).
2. The agent has made at least one edit attempt to fix the failures.
3. The agent has run tests again and observed failures (error event 2).
4. The second failed test result is not a strict improvement over the first failed test result.

Strict improvement is determined from parsed test evidence:

- If failed test node IDs are available, event 2 is a strict improvement only when its failed node ID set is a strict subset of event 1.
- If failed test node IDs are unavailable but failure counts are available, event 2 is a strict improvement only when the failure count is lower than event 1 and no new failure class appears.
- If neither node IDs nor failure counts can be parsed, the operator must not inject and must record an ambiguity deviation.

The operator injects the checkpoint text immediately after observing condition 4, before the agent's next action. The evidence used for the decision must be recorded in `policy_fires.jsonl`.

### When NOT to Inject

- If the agent completed the task before the 2nd error.
- If the 2nd test run shows all tests passing.
- If the agent has not made an edit attempt between test runs.
- If the agent declares TASK COMPLETE.
- If the second failed test result is a strict improvement over the first failed test result.
- If the failure evidence cannot be parsed enough to determine whether the policy fire criteria were met.

## Roles

| Role | Agent | Responsibilities |
|---|---|---|
| Operator | Human | Runs agents in VS Code, pastes transcripts, injects checkpoints |
| Orchestrator | This system | Records events, manages artifacts, coordinates phases |
| Evaluator | Independent agent | Scores blinded traces against rubric |
| Skeptic | Independent agent | Reviews for bias, overclaiming, protocol deviations |
| Verifier | Independent human | Reviews this protocol before execution |

Role separation rules:
- The evaluator must not know condition assignments during scoring.
- The skeptic must not be the same agent as the evaluator.
- The operator must not evaluate or score runs.
- The orchestrator must not influence evaluator or skeptic conclusions.

## Tasks

6 tasks, each with 3 bugs designed to produce sequential errors. See `task_specs/` for full specifications.

| Task | Module | Bug Count | Expected Error Profile |
|---|---|---|---|
| I | Event logger | 3 | 3-5 errors (formatting + filtering + counter) |
| J | LRU cache | 3 | 3-5 errors (eviction + TTL + access order) |
| K | Token auth | 3 | 3-4 errors (expiry + signature + refresh) |
| L | Priority queue | 3 | 3-5 errors (ordering + duplicates + peek) |
| M | Config validator | 3 | 3-4 errors (nested keys + coercion + field check) |
| N | Rate limiter | 3 | 3-5 errors (window + reset + per-key) |

Task design principles:
- Each task has exactly 3 bugs.
- Bugs interact: fixing one may expose or interact with another.
- Bugs require reading the test output carefully (not just the error message).
- The correct fix requires editing the module, not the tests.
- Tests are comprehensive enough to catch partial fixes.

## Phases

### Phase 1: Protocol Review (pre-execution)

1. Independent verifier reviews this protocol.
2. Verifier checks: task balance, prompt neutrality, blinding plan, status gate, rubric fairness.
3. Verifier approves, requests changes, or rejects.
4. Approval at this phase only approves the protocol design. It does not approve execution until the task fixture verification gate in Phase 2 also passes.

### Phase 2: Task Implementation (pre-execution)

1. Implement all 6 task workspaces (module + tests + reset script).
2. Verify all tests fail in the buggy state.
3. Verify all tests pass after correct fixes.
4. Freeze task code. No changes after this point.
5. Record fixture validation evidence for each task:
   - buggy-state test command and failing output summary;
   - corrected-state test command and passing output summary;
   - checksum of each frozen module, test file, and reset fixture;
   - evidence that baseline and guarded reset states are byte-identical.
6. A verifier must review the fixture validation evidence before runner execution begins.

### Phase 3: Runner Execution

1. For each task I through N:
   a. Reset workspace.
   b. Run the first condition from the Frozen Run Order table.
   c. Record transcript as structured events.
   d. Reset workspace.
   e. Run the second condition from the Frozen Run Order table.
   f. Record transcript as structured events.
2. Operator pastes full transcripts. Raw transcripts are stored as immutable artifacts before event parsing.
3. Orchestrator parses transcripts into events using deterministic extraction rules documented in the artifact manifest.

### Phase 4: Blinding

1. Generate blinded event data (see `blinding_plan.md`).
2. Generate unblinding key (stored separately, not shared with evaluator).

### Phase 5: Evaluation

1. Evaluator receives blinded events and rubric.
2. Evaluator scores all 12 runs independently.
3. Evaluator writes scores to `evaluator_scores.jsonl`.

### Phase 6: Unblinding and Analysis

1. Unblind evaluator scores using the key.
2. Compute matched-pair comparisons.
3. Compute aggregate statistics.

### Phase 7: Skeptic Review

1. Skeptic receives: evaluator scores, raw artifacts, unblinding key, analysis.
2. Skeptic reviews for bias, overclaiming, task imbalance, false positives.
3. Skeptic writes review to `skeptic_reviews.jsonl`.

### Phase 8: Report

1. Write pilot report incorporating evaluator scores and skeptic review.
2. Include a claim-to-evidence table. Every claim must cite run IDs, step indices, evaluator evidence, and skeptic disposition.
3. Apply status gate.
4. Update CURRENT_STATE.md.

## Artifact Requirements

See `artifact_manifest.yaml` for the complete list. Every artifact must exist before the pilot is considered complete.

## Status Gate

See `status_gate.yaml`. The gate defines allowed and forbidden statuses. The pilot must not conclude with a forbidden status.

## Deviation Handling

See `deviation_log.md`. Any deviation from this protocol must be recorded with:
- What happened
- When it happened
- Why it happened
- What was done about it
- Whether it affects any conclusions

Deviations that affect blinding, randomization, or condition assignment invalidate the affected runs.

## Known Limitations

1. **Counterbalanced but not randomized at execution time**: Condition order is fixed before execution. This reduces systematic baseline-first bias but does not remove order effects.
2. **Single operator**: The same human runs all agents, introducing potential operator bias.
3. **Single evaluator**: One blinded evaluator, no inter-rater reliability measure.
4. **Small sample**: 6 matched pairs may be insufficient for statistical conclusions.
5. **Agent variability**: VS Code agent behavior is stochastic. Same task, same agent may produce different results on different runs.
6. **No repeated runs per condition**: Each task is run once per condition. No measure of within-condition variance.
7. **Task design bias**: Tasks are designed to produce errors. Real-world tasks may not trigger the policy as often.
8. **Operator injection timing**: The operator follows deterministic parsed-test criteria, but timing may still vary if transcript/tool output visibility is delayed.

## Cancellation Criteria

The pilot is cancelled if:
- The operator cannot run agents (tool failure, environment issues).
- Task workspaces cannot be properly reset between runs.
- Blinding is compromised before evaluation is complete.
- Fewer than 4 matched pairs produce usable data.

## Predecessor Evidence

### Pilot-001 (6 runs)
- Original format: 1 harmful (agent stopped after reflection).
- Adjusted format: 1 helpful (Task C), 1 neutral (Task B).
- Key finding: format matters. Continuation directive prevents stop behavior.

### Pilot-002 (10 runs)
- Adjusted format only.
- 2 checkpoint deliveries: 1 helpful (Task F), 1 unfavorable (Task G).
- 3 tasks too easy for policy to fire.
- Aggregate advantage was inflated by no-intervention runs.
- Skeptic found "never harmful" claim unsupported.

### Implications for Pilot-003
- Tasks must be harder (3+ bugs each) to ensure policy fires.
- More matched pairs (6 vs 5) to increase checkpoint delivery odds.
- Pre-registered protocol to prevent post-hoc adjustments.
- Blinded evaluation with explicit rubric.
- Skeptic review before final report.
