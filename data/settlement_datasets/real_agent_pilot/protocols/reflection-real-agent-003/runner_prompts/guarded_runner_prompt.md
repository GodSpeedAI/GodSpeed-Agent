# Guarded Runner Prompt

This is the prompt given to the agent for guarded runs. The agent receives the same task instructions as baseline. The only difference is that the operator may inject a checkpoint message if the policy fires.

## Template (initial prompt — identical to baseline)

```
Fix the failing tests in tmp/pilot_tasks/task_{task_id}/. Run the tests, identify what's wrong, and make the tests pass. Work only in tmp/pilot_tasks/task_{task_id}/. When done, say TASK COMPLETE and describe what you did.
```

## Checkpoint Injection (conditional)

If and only if the policy fire criteria are met (see pilot_protocol.md Section 3.3), the operator injects this message as a user message:

```
Repeated unresolved errors detected. Before continuing, briefly consider:
1. What failed?
2. What assumption may be wrong?
3. What lower-payment action should happen next?
4. What evidence would show the next step worked?

Now continue fixing the code. Implement your fix and re-run the tests.
```

## Usage

Replace `{task_id}` with the lowercase task identifier (i, j, k, l, m, n).

## Rules for Operator

1. Paste the initial prompt exactly as written into a fresh VS Code agent session.
2. Do not add any additional instructions, hints, or context beyond the initial prompt.
3. Do not mention checkpoints, reflection, or the experimental purpose in the initial prompt.
4. Monitor the agent's progress. Count error events using parsed test evidence:
   - Error event 1: Agent runs tests, sees failures.
   - Agent makes at least one edit attempt.
   - Error event 2: Agent runs tests again and still sees failures.
   - Event 2 is not a strict improvement over event 1.
5. If error event 2 occurs, inject the checkpoint text as a user message immediately, before the agent's next action.
6. After injecting the checkpoint, do not intervene further. Let the agent continue normally.
7. If the agent asks clarifying questions about the checkpoint, do not elaborate. The checkpoint text is self-contained.
8. Paste the full transcript back to the orchestrator when the agent finishes.
9. If the agent completes before the 2nd error (no policy fire), record the run as "no intervention delivered."

Strict improvement is determined as follows:
- If failed test node IDs are available, event 2 is a strict improvement only when its failed node ID set is a strict subset of event 1.
- If failed test node IDs are unavailable but failure counts are available, event 2 is a strict improvement only when the failure count is lower than event 1 and no new failure class appears.
- If neither node IDs nor failure counts can be parsed, do not inject. Record the ambiguity as a deviation.

## When NOT to Inject the Checkpoint

- The agent completed the task before the 2nd error.
- The 2nd test run shows all tests passing.
- The agent has not made an edit attempt between test runs.
- The agent declared TASK COMPLETE.
- The second failed test result is a strict improvement over the first failed test result.
- The failed test evidence cannot be parsed enough to determine whether the policy fire criteria were met.

## What Constitutes a Run

Same as baseline. A run begins when the agent receives the prompt and ends when:
- The agent says "TASK COMPLETE", OR
- The agent has made no progress for 5 minutes, OR
- The agent explicitly gives up.
