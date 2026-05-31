# Recording Template for Real Agent Pilot

## How to Use This Template

For each run, copy this template and fill it in as you observe the agent working.
After the run, save the completed template and transfer the data to the JSONL artifacts.

---

## Run: run-XX

- **Condition**: baseline / guarded
- **Task**: [task description]
- **Task dir**: [path]
- **Agent**: [which VS Code agent / model]
- **Started at**: [timestamp]
- **Ended at**: [timestamp]

### Event Log

Record each agent action as a row. Use these event types:
- `model_message` — Agent says something (thinking, planning, explaining)
- `tool_call` — Agent invokes a tool (bash, read, write, edit, etc.)
- `tool_result` — Output from a tool call
- `file_edit` — Agent edits a file
- `final_answer` — Agent declares the task done
- `task_complete` — Agent confirms completion

| Step | Event Type | Content (summarize, max 200 chars) | Tool Name | Is Error? | Notes |
|------|-----------|-------------------------------------|-----------|-----------|-------|
| 0 | model_message | "I'll start by..." | - | no | |
| 1 | tool_call | python test_auth.py | bash | no | |
| 2 | tool_result | ModuleNotFoundError: No module named 'auth_utils' | bash | yes | **ERROR 1** |
| 3 | model_message | "Let me retry..." | - | no | |
| 4 | tool_call | python test_auth.py | bash | no | Same command as step 1 |
| 5 | tool_result | ModuleNotFoundError: No module named 'auth_utils' | bash | yes | **ERROR 2** ← policy would fire here |
| ... | ... | ... | ... | ... | |

### For Guarded Runs Only: Intervention Record

If the policy fires (2nd unresolved error + same-path continuation):

- **Policy fire step**: [step number]
- **Errors observed**: [list error messages]
- **Same-path evidence**: [what shows the agent continued same-path]
- **Intervention delivered at step**: [step number]
- **Agent response to intervention**: [what the agent said/did after the checkpoint]
- **Agent response type**: strategy_revision / no_revision / partial_revision

### Post-Intervention Actions (guarded runs only)

List the agent's actions AFTER receiving the reflection checkpoint:

| Step | Event Type | Content | Is Lower-Payment Diagnostic? |
|------|-----------|---------|------------------------------|
| 7 | tool_call | cat auth.py | yes (inspection) |
| 8 | file_edit | Created auth_utils.py | no (corrective) |
| ... | ... | ... | ... |

### Run Outcome

- **Total steps**: [count]
- **Error count**: [count]
- **Outcome**: success / failure
- **Settlement quality**: clean_success / recovered_success / partial_success / failure_with_signal
- **Policy fired**: yes / no
- **Agent revised strategy**: yes / no / n/a
- **Notes**: [any observations about agent behavior]

### Workspace State After Run

Record the final state of the task workspace:
- Which files were created/modified?
- Do the tests pass now?
- Any unexpected changes?

---

## Quick Reference: Reflection Checkpoint Text (for guarded runs)

```
Repeated unresolved errors detected.

Before continuing, revise the plan using the latest settlement feedback:

1. What failed?
2. What assumption may be wrong?
3. What lower-payment action should happen next?
4. What evidence would show the next step worked?
```

## When to Inject the Checkpoint

Inject the reflection checkpoint as a follow-up message to the agent when ALL of these are true:
1. The agent has encountered 2+ unresolved errors
2. The errors are not duplicates (different error messages or different contexts)
3. The agent has NOT shown adaptive recovery between errors (no diagnostic actions, no strategy revision)
4. The agent is continuing on the same failing path (retrying the same command or approach)

Do NOT inject if:
- The agent has already changed strategy between errors
- The agent is doing diagnostic/inspection work between errors
- The errors are duplicates (same exact error message)
- The agent has only had 1 error so far
