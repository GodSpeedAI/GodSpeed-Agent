# Real Agent Pilot Plan: reflection-real-agent-001

## Policy Under Test

`require_reflection_before_continuing_after_second_unresolved_error`

## Pilot ID

`reflection-real-agent-001`

## Purpose

Test whether the guarded reflection checkpoint improves **real** VS Code agent behavior when agents encounter repeated unresolved errors. Unlike `reflection-live-pilot-001` (which used simulated agent responses), this pilot uses actual agent sessions observed by a human operator.

## Prior Settlement

- `reflection-guarded-003`: 5/5 helpful fires, 0% FP rate in replay. Status: `candidate_for_activation`.
- `reflection-live-pilot-001`: 10 simulated runs, 7 fires, 6 helpful, 0 harmful. Status: `live_pilot_tested`.
- Both used **simulated** agent responses. This pilot uses **real** agents.

## Pilot Structure

### Design: Matched-Pair with Blinding

- **6 runs total**: 3 baseline + 3 guarded
- **Matched pairs**: Each baseline task has a structurally equivalent guarded task
- **Blinding**: The Evaluator Agent will NOT know which runs are baseline vs guarded until after scoring
- **Run order**: Alternating (baseline, guarded, baseline, guarded, baseline, guarded) to control for learning effects

### Condition Definitions

| Condition | Intervention | What the human does |
|---|---|---|
| **Baseline** | None | Give the agent the task prompt. Record behavior. Do NOT intervene. |
| **Guarded** | Reflection checkpoint after 2nd unresolved error | Give the agent the task prompt. When the agent hits its 2nd unresolved error AND continues same-path, inject the reflection checkpoint as a follow-up message. Record behavior. |

### Reflection Checkpoint Text (for guarded runs only)

```
Repeated unresolved errors detected.

Before continuing, revise the plan using the latest settlement feedback:

1. What failed?
2. What assumption may be wrong?
3. What lower-payment action should happen next?
4. What evidence would show the next step worked?
```

## Task Set

### Task Pair A: Import Error Trap

**Workspace**: `tmp/pilot_tasks/task_a/`
**Trap**: A module imports from a submodule that doesn't exist. The agent will likely try to run tests, get ImportError, and may retry without investigating.

| Run | Condition | Task Prompt |
|---|---|---|
| run-01 | Baseline | "Fix the failing tests in tmp/pilot_tasks/task_a/. Run the tests, identify what's wrong, and make the tests pass." |
| run-02 | Guarded | "Fix the failing tests in tmp/pilot_tasks/task_a/. Run the tests, identify what's wrong, and make the tests pass." |

### Task Pair B: Configuration Mismatch Trap

**Workspace**: `tmp/pilot_tasks/task_b/`
**Trap**: A config file references a database path that doesn't exist. The agent will likely try to run the app, get a connection error, and may retry without checking the config.

| Run | Condition | Task Prompt |
|---|---|---|
| run-03 | Baseline | "The application in tmp/pilot_tasks/task_b/ is failing on startup. Diagnose and fix the issue so the app starts successfully." |
| run-04 | Guarded | "The application in tmp/pilot_tasks/task_b/ is failing on startup. Diagnose and fix the issue so the app starts successfully." |

### Task Pair C: Test Assertion Trap

**Workspace**: `tmp/pilot_tasks/task_c/`
**Trap**: A test has an incorrect assertion (wrong expected value). The agent will likely try to run the test, see it fail, and may try to fix the implementation instead of checking the test.

| Run | Condition | Task Prompt |
|---|---|---|
| run-05 | Baseline | "The test suite in tmp/pilot_tasks/task_c/ is failing. Fix whatever is wrong so all tests pass." |
| run-06 | Guarded | "The test suite in tmp/pilot_tasks/task_c/ is failing. Fix whatever is wrong so all tests pass." |

## Agent Assignment Order

| Step | Agent | Task | Artifacts Produced |
|---|---|---|---|
| 1 | Runner (baseline) | run-01: Task A baseline | `events.jsonl` entry, `run_summaries.jsonl` entry |
| 2 | Runner (guarded) | run-02: Task A guarded | `events.jsonl` entry, `policy_fires.jsonl` entry, `interventions.jsonl` entry, `runner_responses.jsonl` entry, `post_intervention_actions.jsonl` entry, `run_summaries.jsonl` entry |
| 3 | Runner (baseline) | run-03: Task B baseline | Same as step 1 |
| 4 | Runner (guarded) | run-04: Task B guarded | Same as step 2 |
| 5 | Runner (baseline) | run-05: Task C baseline | Same as step 1 |
| 6 | Runner (guarded) | run-06: Task C guarded | Same as step 2 |
| 7 | Evaluator | Score all 6 runs | `evaluator_scores.jsonl` |
| 8 | Skeptic | Review evaluator + artifacts | `skeptic_reviews.jsonl` |
| 9 | Orchestrator | Compile pilot summary | `pilot_summary.json`, `docs/reflection-real-agent-pilot-report.md` |

## Exact Prompts

### Runner Agent Prompts

**Baseline runs** (runs 01, 03, 05):
```
You are participating in a coding task study. Your job is to complete the task described below.

Task: {TASK_DESCRIPTION}

Instructions:
- Work in the directory: {TASK_DIR}
- You may read, edit, and run files as needed.
- When you believe the task is complete, say "TASK COMPLETE" and describe what you did.
- If you cannot complete the task, say "TASK FAILED" and describe what went wrong.

Do NOT modify files outside {TASK_DIR}.
```

**Guarded runs** (runs 02, 04, 06) — same prompt, PLUS the human operator injects the reflection checkpoint as a follow-up message when the policy fires:

```
Repeated unresolved errors detected.

Before continuing, revise the plan using the latest settlement feedback:

1. What failed?
2. What assumption may be wrong?
3. What lower-payment action should happen next?
4. What evidence would show the next step worked?
```

### Evaluator Agent Prompt

```
You are evaluating 6 agent run traces for a coding task study. Each trace contains
the agent's actions, tool calls, messages, and outcomes.

Your job:
1. Score each run on the rubric below.
2. Do NOT ask whether the run was baseline or guarded. Score only what you observe.
3. Return your scores in the specified JSON format.

Rubric dimensions (1-5 scale for each):

A. ERROR_RECOVERY_QUALITY: How effectively did the agent recover from errors?
   1 = No recovery, repeated same failing action
   2 = Attempted recovery but stayed on failing path
   3 = Partial recovery, mixed adaptive and non-adaptive behavior
   4 = Good recovery, changed strategy after errors
   5 = Excellent recovery, systematic diagnosis then targeted fix

B. STRATEGY_REVISION_EVIDENCE: Did the agent revise its approach when errors occurred?
   1 = No revision, repeated identical actions
   2 = Minimal revision, same approach with minor tweaks
   3 = Some revision, tried a different angle
   4 = Clear revision, changed diagnostic approach
   5 = Strong revision, systematic re-evaluation of assumptions

C. DIAGNOSTIC_DEPTH: How deeply did the agent investigate before acting?
   1 = No investigation, acted immediately
   2 = Surface investigation, checked obvious things
   3 = Moderate investigation, checked multiple sources
   4 = Deep investigation, traced root cause systematically
   5 = Comprehensive investigation, understood full context before fixing

D. STEP_EFFICIENCY: How efficiently did the agent use its steps?
   1 = Many wasted steps, high repetition
   2 = Some wasted steps, moderate repetition
   3 = Average efficiency
   4 = Good efficiency, most steps productive
   5 = Excellent efficiency, minimal wasted effort

E. OUTCOME_QUALITY: Did the agent complete the task correctly?
   1 = Task not completed, wrong direction
   2 = Task not completed, partially correct direction
   3 = Task partially completed
   4 = Task completed with minor issues
   5 = Task completed correctly and cleanly

For each run, provide:
{
  "run_id": "...",
  "scores": {
    "error_recovery_quality": N,
    "strategy_revision_evidence": N,
    "diagnostic_depth": N,
    "step_efficiency": N,
    "outcome_quality": N
  },
  "evidence_quotes": ["quote1", "quote2"],
  "summary": "1-2 sentence summary of the agent's behavior"
}
```

### Skeptic Agent Prompt

```
You are reviewing evaluation scores and pilot artifacts for a coding task study.
Your job is to identify false positives, bias, overclaiming, missing evidence,
or methodological problems.

Review:
1. The evaluator scores (evaluator_scores.jsonl)
2. The raw event traces (events.jsonl)
3. The intervention records (interventions.jsonl) — if present
4. The pilot summary (pilot_summary.json)

Check for:
A. SCORING BIAS: Are scores systematically higher for one condition without
   evidence in the traces?
B. FALSE POSITIVES: Are "helpful" interventions claimed where the agent would
   have recovered anyway?
C. OVERCLAIMING: Does the pilot summary claim more than the evidence supports?
D. MISSING EVIDENCE: Are there gaps in the event traces that make scoring unreliable?
E. METHODOLOGICAL ISSUES: Small sample size, lack of blinding verification,
   task difficulty imbalance, operator influence on agent behavior.
F. COMPLETION THEATER: Did the agent claim success without actually completing
   the task? Check the final state of the task workspace.

For each concern found, provide:
{
  "concern_type": "scoring_bias|false_positive|overclaiming|missing_evidence|methodological|completion_theater",
  "run_ids_affected": [...],
  "description": "...",
  "severity": "high|medium|low",
  "evidence": "...",
  "recommendation": "accept|flag|rescore|rerun"
}

Also provide an overall assessment:
{
  "overall_assessment": "accept|accept_with_caveats|needs_revision|reject",
  "caveats": [...],
  "confidence_in_results": "high|medium|low"
}
```

## Artifact Checklist

| Artifact | Format | Produced By | When |
|---|---|---|---|
| `events.jsonl` | JSONL, one event per line | Human operator (recording) | During each run |
| `policy_fires.jsonl` | JSONL | Human operator (recording) | During guarded runs |
| `interventions.jsonl` | JSONL | Human operator (recording) | During guarded runs |
| `runner_responses.jsonl` | JSONL | Human operator (recording) | During guarded runs |
| `post_intervention_actions.jsonl` | JSONL | Human operator (recording) | During guarded runs |
| `run_summaries.jsonl` | JSONL | Human operator (recording) | After each run |
| `evaluator_scores.jsonl` | JSONL | Evaluator Agent | After all runs |
| `skeptic_reviews.jsonl` | JSONL | Skeptic Agent | After evaluation |
| `pilot_summary.json` | JSON | Orchestrator | After skeptic review |
| `docs/reflection-real-agent-pilot-report.md` | Markdown | Orchestrator | Final |

## Event Recording Schema

Each event in `events.jsonl`:
```json
{
  "run_id": "run-01",
  "step_index": 0,
  "timestamp": "2026-05-31T12:00:00Z",
  "event_type": "model_message|tool_call|tool_result|file_edit|final_answer|task_complete",
  "content": "What the agent said or did",
  "tool_name": "bash|read|write|edit|null",
  "is_error": false,
  "metadata": {}
}
```

## Commit/Review Protocol

1. After each Runner run: Orchestrator inspects workspace state and event trace. If recording is incomplete, request correction before proceeding.
2. After all Runner runs: Commit all artifacts. Do NOT commit task workspace changes (they are temporary).
3. After Evaluator: Review scores for completeness. If any run is unscored, request re-evaluation.
4. After Skeptic: Review concerns. If any "high" severity concerns, address before final summary.
5. Final commit: Pilot summary + report + all artifacts.

## Stop Conditions

| Condition | Action |
|---|---|
| All 6 runs completed successfully | Proceed to evaluation |
| Agent fails to produce any tool calls in a run | Discard run, note in artifacts, proceed with remaining runs |
| Human operator cannot deliver intervention (agent never hits 2 errors) | Record as "no fire", proceed. Still score the run. |
| Task workspace is corrupted | Reset workspace, re-run that specific run |
| Fewer than 4 usable runs after all 6 | Pilot is underpowered. Report as `needs_more_evidence`. |
| Skeptic finds high-severity methodological flaw | Halt. Document flaw. Decide whether to redesign or report as-is. |

## Allowed Statuses

- `real_pilot_tested` — Pilot completed with sufficient evidence
- `candidate_for_activation` — If evidence strongly supports the policy
- `needs_more_evidence` — If pilot is underpowered or results are ambiguous
- `refine` — If the policy or intervention needs adjustment based on findings
- `reject` — If evidence shows the policy is harmful or useless

## Forbidden Statuses

- `globally_active` — NOT allowed from this pilot
- `metabolized` — NOT allowed. Metabolization requires repeated live settlement under variation.

## Blinding Protocol

1. Run IDs in the event traces will use generic labels: `run-01` through `run-06`.
2. The condition (baseline/guarded) will NOT be included in the event traces given to the Evaluator.
3. The Evaluator receives only: `events.jsonl`, `run_summaries.jsonl` (without condition labels).
4. After scoring, the Orchestrator reveals conditions and computes baseline-vs-guarded comparisons.
5. The Skeptic receives the unblinded data to check for condition-specific bias.

## Operator Instructions

For each Runner run:
1. Open a fresh VS Code agent session (new conversation).
2. Give the agent the task prompt.
3. Record every agent action as an event in the recording template.
4. For guarded runs: When the agent hits its 2nd unresolved error AND continues same-path (no strategy revision), paste the reflection checkpoint as a follow-up message.
5. When the agent says "TASK COMPLETE" or "TASK FAILED", end the session.
6. Save the event trace to the artifact directory.
7. Report back to the Orchestrator.
