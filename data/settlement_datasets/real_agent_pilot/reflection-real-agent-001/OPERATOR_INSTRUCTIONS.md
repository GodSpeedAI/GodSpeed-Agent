# Real Agent Pilot — Operator Instructions (Revised)

## What you actually do

For each run:

1. **Reset** the workspace: `bash tmp/pilot_tasks/reset_tasks.sh`
2. **Open a fresh VS Code agent session** (new conversation)
3. **Paste the task prompt** (I'll give it to you for each run)
4. **Let the agent work** — interact normally
5. **For guarded runs only**: When the agent hits its 2nd unresolved error AND continues same-path, paste the reflection checkpoint as a follow-up message
6. **When the agent finishes**, copy the full conversation transcript
7. **Come back and paste it** — say "run-XX done" with the transcript

## What I need from you

Just two things per run:

1. **The full conversation transcript** — copy-paste from VS Code. Include everything: agent messages, tool calls, tool outputs, your messages.
2. **A brief note** on:
   - Did the agent complete the task? (yes/no/partial)
   - For guarded runs: at what point did you inject the reflection checkpoint?
   - Anything unusual?

## What I do with it

I parse the transcript into structured events, score the run, and store the artifacts. You don't touch JSONL files.

## Reflection Checkpoint (guarded runs only)

Inject this as a follow-up message when the agent has hit 2+ unresolved errors AND is continuing same-path:

```
Repeated unresolved errors detected.

Before continuing, revise the plan using the latest settlement feedback:

1. What failed?
2. What assumption may be wrong?
3. What lower-payment action should happen next?
4. What evidence would show the next step worked?
```

## When to inject (guarded runs)

Inject when ALL of these are true:
- Agent has encountered 2+ unresolved errors (different errors, not duplicates)
- Agent has NOT changed strategy between errors (no diagnostic actions)
- Agent is retrying the same failing approach

Do NOT inject if:
- Agent already changed strategy
- Agent is doing diagnostic/inspection work
- Only 1 error so far
- Errors are exact duplicates
