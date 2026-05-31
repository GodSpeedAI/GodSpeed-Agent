# Deviation Log

## Purpose

Record any deviations from the pre-registered protocol. Deviations may affect the validity of specific runs or the entire pilot.

## Deviation Format

Each deviation is recorded with:

| Field | Description |
|---|---|
| deviation_id | Unique identifier (DEV-001, DEV-002, etc.) |
| timestamp | When the deviation was discovered |
| phase | Which phase it occurred in (runner, blinding, evaluation, etc.) |
| description | What happened |
| affected_runs | Which runs are affected (run-ids or "all") |
| severity | low / medium / high / critical |
| resolution | What was done about it |
| impact_on_conclusions | Whether and how this affects conclusions |

## Severity Definitions

| Severity | Meaning |
|---|---|
| Low | Minor procedural issue. Does not affect data validity. |
| Medium | Procedural issue that may affect some scores but not overall conclusions. |
| High | Issue that may invalidate one or more runs. |
| Critical | Issue that invalidates the pilot or compromises blinding. |

## Active Deviations

### DEV-001: Sub-agent runner instead of human operator

- **Timestamp**: 2026-05-31
- **Phase**: Runner execution (Phase 3)
- **Description**: The protocol specifies a human operator who runs agents in VS Code, pastes transcripts, and injects checkpoints mid-conversation. This execution uses sub-agents (Task tool) instead of a human operator. The guarded condition is implemented by including the checkpoint text in the initial prompt (pre-baked context) rather than injecting it mid-conversation after observing a second failed test run. This removes operator timing bias but changes the intervention from "mid-conversation injection" to "pre-baked context."
- **Affected Runs**: run-18, run-20, run-22, run-24, run-26, run-28 (all guarded runs)
- **Severity**: Medium
- **Resolution**: Documented. The evaluator and skeptic are informed of this deviation. The intervention text is included verbatim in the guarded prompt. The policy fire criteria are still evaluated from the sub-agent's output (test results after edits), but the timing is different: the agent sees the reflection prompt from the start rather than after a second failure.
- **Impact on Conclusions**: This changes the intervention mechanism. Pre-baked context means the agent has the reflection framework available from the beginning, which may lead to earlier self-correction (potentially inflating guarded benefit) or may be ignored as part of a long prompt (potentially deflating guarded benefit). The skeptic must assess whether this deviation invalidates comparison with pilot-001 and pilot-002 results.

## Deviation Records

#### DEV-001: Sub-agent runner instead of human operator

- **Timestamp**: 2026-05-31
- **Phase**: Runner execution (Phase 3)
- **Description**: The protocol specifies a human operator who runs agents in VS Code, pastes transcripts, and injects checkpoints mid-conversation. This execution uses sub-agents (Task tool) instead of a human operator. The guarded condition is implemented by including the checkpoint text in the initial prompt (pre-baked context) rather than injecting it mid-conversation after observing a second failed test run.
- **Affected Runs**: run-18, run-20, run-22, run-24, run-26, run-28 (all guarded runs)
- **Severity**: Medium
- **Resolution**: Documented. Evaluator and skeptic informed.
- **Impact on Conclusions**: Changes intervention mechanism from mid-conversation injection to pre-baked context. May inflate or deflate guarded benefit. Skeptic must assess comparability with prior pilots.

---

### Template for New Deviations

```
#### DEV-NNN: [Title]

- **Timestamp**: 
- **Phase**: 
- **Description**: 
- **Affected Runs**: 
- **Severity**: 
- **Resolution**: 
- **Impact on Conclusions**: 
```
