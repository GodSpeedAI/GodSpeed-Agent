# Baseline Runner Prompt

This is the prompt given to the agent for baseline runs. The agent receives only task instructions. No mention of checkpoints, reflection, or experimental conditions.

## Template

```
Fix the failing tests in tmp/pilot_tasks/task_{task_id}/. Run the tests, identify what's wrong, and make the tests pass. Work only in tmp/pilot_tasks/task_{task_id}/. When done, say TASK COMPLETE and describe what you did.
```

## Usage

Replace `{task_id}` with the lowercase task identifier (i, j, k, l, m, n).

## Rules for Operator

1. Paste this prompt exactly as written into a fresh VS Code agent session.
2. Do not add any additional instructions, hints, or context.
3. Do not mention checkpoints, reflection, or the experimental purpose.
4. Do not intervene during the run, even if the agent struggles.
5. Paste the full transcript back to the orchestrator when the agent finishes.
6. If the agent asks clarifying questions, respond with: "Just follow the instructions as given."

## What Constitutes a Run

A run begins when the agent receives the prompt and ends when:
- The agent says "TASK COMPLETE", OR
- The agent has made no progress for 5 minutes, OR
- The agent explicitly gives up.

The operator records the full transcript including all tool calls, test outputs, and agent messages.
