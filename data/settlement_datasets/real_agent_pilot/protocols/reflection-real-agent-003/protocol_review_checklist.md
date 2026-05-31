# Protocol Review Checklist

## Purpose

This checklist is for the independent verifier to review the protocol before execution. The verifier should check each item and record pass/fail/needs-changes.

## Verifier Information

- **Verifier Name**: _______________
- **Review Date**: _______________
- **Protocol Version**: reflection-real-agent-003

## Checklist

### 1. Protocol Document

| # | Check | Status | Notes |
|---|---|---|---|
| 1.1 | Protocol ID is unique and traceable | ☐ Pass ☐ Fail | |
| 1.2 | Hypothesis is non-directional (does not assume benefit) | ☐ Pass ☐ Fail | |
| 1.3 | Intervention text is frozen and verbatim | ☐ Pass ☐ Fail | |
| 1.4 | Design is clearly described (matched pairs, conditions) | ☐ Pass ☐ Fail | |
| 1.5 | Roles are separated (operator, evaluator, skeptic, verifier) | ☐ Pass ☐ Fail | |
| 1.6 | Phases are ordered and dependencies are clear | ☐ Pass ☐ Fail | |
| 1.7 | Known limitations are honestly stated | ☐ Pass ☐ Fail | |
| 1.8 | Cancellation criteria are defined | ☐ Pass ☐ Fail | |
| 1.9 | Predecessor evidence is accurately summarized | ☐ Pass ☐ Fail | |
| 1.10 | Task fixture validation gate occurs before runner execution | ☐ Pass ☐ Fail | |

### 2. Task Specifications

| # | Check | Status | Notes |
|---|---|---|---|
| 2.1 | All 6 tasks have complete specs | ☐ Pass ☐ Fail | |
| 2.2 | Each task has exactly 3 bugs | ☐ Pass ☐ Fail | |
| 2.3 | Bugs are described precisely (location, fix) | ☐ Pass ☐ Fail | |
| 2.4 | Expected error profiles are realistic (3+ errors) | ☐ Pass ☐ Fail | |
| 2.5 | Tasks are independent (no shared code) | ☐ Pass ☐ Fail | |
| 2.6 | Difficulty assessments are reasonable | ☐ Pass ☐ Fail | |
| 2.7 | No task is trivially easy (1-error fix) | ☐ Pass ☐ Fail | |
| 2.8 | No task is impossibly hard (agent cannot fix) | ☐ Pass ☐ Fail | |

### 3. Runner Prompts

| # | Check | Status | Notes |
|---|---|---|---|
| 3.1 | Baseline and guarded initial prompts are identical | ☐ Pass ☐ Fail | |
| 3.2 | Prompts do not reveal the experimental hypothesis | ☐ Pass ☐ Fail | |
| 3.3 | Prompts do not mention checkpoints or reflection | ☐ Pass ☐ Fail | |
| 3.4 | Guarded prompt specifies exact injection criteria | ☐ Pass ☐ Fail | |
| 3.5 | Guarded prompt specifies when NOT to inject | ☐ Pass ☐ Fail | |
| 3.6 | Operator instructions are clear and unambiguous | ☐ Pass ☐ Fail | |
| 3.7 | Injection criteria rely on deterministic parsed test evidence | ☐ Pass ☐ Fail | |

### 4. Evaluator Prompt

| # | Check | Status | Notes |
|---|---|---|---|
| 4.1 | Evaluator does not receive condition assignments | ☐ Pass ☐ Fail | |
| 4.2 | Rubric dimensions are well-defined with clear criteria | ☐ Pass ☐ Fail | |
| 4.3 | Each score level (1-5) has specific criteria | ☐ Pass ☐ Fail | |
| 4.4 | Evaluator must cite specific evidence (run_id, step_index) | ☐ Pass ☐ Fail | |
| 4.5 | "Uncertain" scoring is allowed for missing evidence | ☐ Pass ☐ Fail | |
| 4.6 | Output format is specified and machine-readable | ☐ Pass ☐ Fail | |
| 4.7 | Evaluator is instructed not to speculate about conditions | ☐ Pass ☐ Fail | |
| 4.8 | Output schema encodes uncertain scores and missing evidence reasons | ☐ Pass ☐ Fail | |

### 5. Skeptic Prompt

| # | Check | Status | Notes |
|---|---|---|---|
| 5.1 | Skeptic receives all relevant data (scores, artifacts, unblinding key) | ☐ Pass ☐ Fail | |
| 5.2 | Skeptic is instructed to challenge positive claims | ☐ Pass ☐ Fail | |
| 5.3 | Skeptic must assess task balance and difficulty | ☐ Pass ☐ Fail | |
| 5.4 | Skeptic must identify false positive risk | ☐ Pass ☐ Fail | |
| 5.5 | Skeptic must check for protocol deviations | ☐ Pass ☐ Fail | |
| 5.6 | Claim rating scale is defined (STRONG/MODERATE/WEAK/NO/EVIDENCE AGAINST) | ☐ Pass ☐ Fail | |
| 5.7 | Output format is specified and machine-readable | ☐ Pass ☐ Fail | |
| 5.8 | Skeptic objections have explicit blocking or report-change dispositions | ☐ Pass ☐ Fail | |

### 6. Blinding Plan

| # | Check | Status | Notes |
|---|---|---|---|
| 6.1 | Run ID anonymization procedure is specified | ☐ Pass ☐ Fail | |
| 6.2 | Revealing event types are identified for removal | ☐ Pass ☐ Fail | |
| 6.3 | Revealing metadata keys are identified for removal | ☐ Pass ☐ Fail | |
| 6.4 | Content neutralization rules are specified | ☐ Pass ☐ Fail | |
| 6.5 | Automated verification checks are defined | ☐ Pass ☐ Fail | |
| 6.6 | Unblinding timing is specified (after evaluation only) | ☐ Pass ☐ Fail | |
| 6.7 | Compromise handling procedure is defined | ☐ Pass ☐ Fail | |
| 6.8 | User/operator checkpoint messages are removed or neutralized | ☐ Pass ☐ Fail | |
| 6.9 | Neutralization does not create condition-specific cues | ☐ Pass ☐ Fail | |

### 7. Status Gate

| # | Check | Status | Notes |
|---|---|---|---|
| 7.1 | Allowed statuses are clearly defined | ☐ Pass ☐ Fail | |
| 7.2 | Forbidden statuses include `globally_active` and `metabolized` | ☐ Pass ☐ Fail | |
| 7.3 | Decision rules are unambiguous | ☐ Pass ☐ Fail | |
| 7.4 | Override conditions are specified | ☐ Pass ☐ Fail | |
| 7.5 | Gate does not assume positive outcome | ☐ Pass ☐ Fail | |
| 7.6 | Negative and mixed outcomes have clear paths | ☐ Pass ☐ Fail | |
| 7.7 | Positive status requires strong settlement evidence and no unresolved skeptic blocker | ☐ Pass ☐ Fail | |
| 7.8 | Non-delivery guarded outcomes are classified and considered | ☐ Pass ☐ Fail | |

### 8. Artifact Manifest

| # | Check | Status | Notes |
|---|---|---|---|
| 8.1 | All required artifacts are listed | ☐ Pass ☐ Fail | |
| 8.2 | Artifact schemas are specified | ☐ Pass ☐ Fail | |
| 8.3 | Completeness check is defined | ☐ Pass ☐ Fail | |
| 8.4 | pilot_summary.json schema includes required fields | ☐ Pass ☐ Fail | |
| 8.5 | pilot_summary.json requires `metabolized: false` and `globally_active: false` | ☐ Pass ☐ Fail | |
| 8.6 | Raw transcripts and checksums are required artifacts | ☐ Pass ☐ Fail | |
| 8.7 | Pilot-specific immutable report is required | ☐ Pass ☐ Fail | |
| 8.8 | Claim-to-evidence table is required | ☐ Pass ☐ Fail | |

### 9. Deviation Log

| # | Check | Status | Notes |
|---|---|---|---|
| 9.1 | Deviation format is specified | ☐ Pass ☐ Fail | |
| 9.2 | Severity levels are defined | ☐ Pass ☐ Fail | |
| 9.3 | Impact assessment is required | ☐ Pass ☐ Fail | |

### 10. Overall Protocol Integrity

| # | Check | Status | Notes |
|---|---|---|---|
| 10.1 | No language assumes the policy helps | ☐ Pass ☐ Fail | |
| 10.2 | No status allows `globally_active` or `metabolized` | ☐ Pass ☐ Fail | |
| 10.3 | Protocol can produce a negative result | ☐ Pass ☐ Fail | |
| 10.4 | Protocol can produce an inconclusive result | ☐ Pass ☐ Fail | |
| 10.5 | Predecessor lessons are incorporated (harder tasks, blinded eval, skeptic) | ☐ Pass ☐ Fail | |
| 10.6 | Protocol is frozen — no changes after verifier approval | ☐ Pass ☐ Fail | |
| 10.7 | Orchestrator parsing and reporting discretion is constrained | ☐ Pass ☐ Fail | |

## Verdict

- ☐ **Approved** — Protocol may proceed to execution.
- ☐ **Approved with Changes** — Listed changes must be made before execution.
- ☐ **Rejected** — Protocol requires fundamental revision.

## Required Changes (if any)

1. ...
2. ...

## Verifier Signature

_______________________________
Date: _______________
