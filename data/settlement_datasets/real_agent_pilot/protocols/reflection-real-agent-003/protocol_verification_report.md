# Protocol Verification Report: reflection-real-agent-003

## Verdict

approved

## Scope

Reviewed pre-execution protocol artifacts only. The pilot was not run. Required protocol fixes were applied after the initial verifier finding. No `globally_active` or `metabolized` status was assigned.

Artifacts reviewed:
- `pilot_protocol.md`
- `task_specs/`
- `runner_prompts/`
- `evaluator_prompt.md`
- `skeptic_prompt.md`
- `blinding_plan.md`
- `status_gate.yaml`
- `artifact_manifest.yaml`
- `deviation_log.md`
- `protocol_review_checklist.md`

## Summary

The protocol is directionally sound: the hypothesis is explicitly non-directional, the runner initial prompts are matched, the evaluator is blinded by design, harmful and inconclusive outcomes are allowed, and forbidden status values exclude global activation and metabolization.

The protocol is approved for the next pre-execution phase. Runner execution remains blocked until the newly required fixture validation gate is completed and independently reviewed.

The initial review found risks around promotion thresholds, task balance evidence, blinding coverage, and orchestrator discretion. Those risks are now addressed in the protocol documents by stricter status rules, a fixture validation gate, expanded blinding rules, required raw transcript retention, deterministic parsing requirements, and skeptic objection disposition rules.

## Issues Reviewed and Corrected

### 1. Task balance cannot be verified before approval

- **File**: `pilot_protocol.md`
- **Line or section**: lines 109-115, "Phase 2: Task Implementation"; lines 80-99, "Tasks"
- **Issue type**: baseline vs guarded task imbalance / lack of evidence requirements
- **Why it matters**: The protocol asks the verifier to approve task balance before the actual task workspaces are implemented and frozen. The task specs describe intended bugs and difficulty, but they are not settlement evidence that the runnable modules and tests have the stated difficulty, independence, or failure profiles. This leaves a path for implementation-defined imbalance after approval.
- **Required correction**: Move task workspace implementation and fixture validation before final protocol approval, or add a required second verification gate after Phase 2. The gate should require evidence that each buggy workspace fails as expected, each corrected workspace passes, each task has exactly the intended bugs, and baseline/guarded runs use byte-identical reset state.

### 2. Run order is systematically baseline-first

- **File**: `pilot_protocol.md`
- **Line or section**: lines 34-37; lines 116-125; limitation acknowledged at lines 175-184
- **Issue type**: baseline vs guarded task imbalance
- **Why it matters**: Baseline always precedes guarded for each task. Even with workspace reset, operator learning, session effects, task familiarity, or orchestration drift can favor guarded runs. Acknowledging the limitation is useful but does not control it.
- **Required correction**: Randomize or counterbalance condition order per task using a pre-registered seed, or require the final report and status gate to treat order effects as a limiting confound that blocks `candidate_for_activation`.

### 3. Status gate permits promotion too easily

- **File**: `status_gate.yaml`
- **Line or section**: lines 28-50
- **Issue type**: status gate too easy / overclaiming risk
- **Why it matters**: With only 6 matched pairs, `candidate_for_activation` can be assigned from only 3 helpful checkpoint deliveries and 0 harmful deliveries. This is too weak for "broader testing or conditional activation," especially because the protocol already acknowledges small sample size, no repeated runs, no randomization, single operator, and single evaluator.
- **Required correction**: Raise the bar for positive statuses. At minimum, require all or nearly all usable checkpoint deliveries to be helpful, no harmful outcomes in any guarded run, no critical skeptic objection, successful task settlement, and explicit confidence language limiting the claim to "candidate for further study" rather than activation.

### 4. Helpful/neutral/harmful classification ignores non-delivery guarded outcomes

- **File**: `status_gate.yaml`
- **Line or section**: lines 34-50
- **Issue type**: missing neutral/harmful/failure categories / unsupported claims
- **Why it matters**: Step 2 classifies only checkpoint deliveries. A guarded run that does not receive the checkpoint but performs worse than baseline may be excluded from the status decision, while still contributing to aggregate impressions elsewhere. This creates a selection path where only delivered interventions count for harm classification.
- **Required correction**: Add required classifications for every matched pair: `checkpoint_helpful`, `checkpoint_neutral`, `checkpoint_harmful`, `no_fire_better`, `no_fire_neutral`, `no_fire_worse`, `invalid`, and `incomplete`. Positive statuses should require that non-delivery guarded outcomes do not contradict the claimed effect.

### 5. "Helpful" is defined by majority rubric dimensions without effect-size or settlement requirements

- **File**: `status_gate.yaml`
- **Line or section**: lines 34-40
- **Issue type**: lack of evidence requirements / unsupported claims
- **Why it matters**: A guarded run can be labeled helpful by narrowly outperforming baseline on a majority of dimensions even if the task outcome, final tests, introduced bugs, or key settlement evidence are weak. This risks confusing evaluator score movement with actual settlement.
- **Required correction**: Require concrete settlement evidence for helpful classification: final tests pass or outcome is objectively better, no new unresolved bug remains, improvement exceeds a pre-registered minimum margin, and cited step-level evidence supports the causal interpretation.

### 6. Blinding does not explicitly handle checkpoint/user-message content

- **File**: `blinding_plan.md`
- **Line or section**: lines 30-57; `artifact_manifest.yaml` lines 81-95
- **Issue type**: hypothesis leakage to evaluator / missing blinding procedure
- **Why it matters**: The event schema includes `model_message` and `intervention`, but not ordinary user messages. If checkpoint text or operator messages are stored as `model_message`, `tool_call`, `content`, or another event type, the evaluator may see condition-revealing text. The current stripping rule removes only `intervention` event types and neutralizes only `model_message` events that mention selected keywords.
- **Required correction**: Define all transcript event types, including user/operator messages. Require removal or neutralization of every checkpoint-derived user/operator message and every content field across all event types containing condition-revealing terms. Automated checks should scan all string fields, not just event content and metadata keys.

### 7. Blinding transformation may create a new condition cue

- **File**: `blinding_plan.md`
- **Line or section**: lines 54-57
- **Issue type**: hypothesis leakage to evaluator / evaluator bias
- **Why it matters**: Replacing checkpoint-related model content with the fixed sentence "Agent provided analysis of errors and proposed next steps" may itself become a recognizable cue if it appears only in guarded runs after policy fire. It also removes behavioral evidence unevenly from guarded runs.
- **Required correction**: Use a content-neutralization rule that preserves comparable behavioral information across both conditions, or apply the same summarization procedure to all model analysis messages in all runs. The blinding verification should confirm that neutralized placeholders are not condition-specific.

### 8. Operator injection criteria leave subjective discretion

- **File**: `pilot_protocol.md`; `runner_prompts/guarded_runner_prompt.md`
- **Line or section**: `pilot_protocol.md` lines 48-55; `guarded_runner_prompt.md` lines 34-50
- **Issue type**: orchestrator/operator freedom to improvise / task imbalance
- **Why it matters**: Phrases such as "not clearly a subset," "not clearly improving," and "clearly making progress" require judgment during execution. Since the same operator knows which condition is guarded, subjective timing can influence settlement.
- **Required correction**: Replace subjective criteria with a deterministic rule based on parsed test results, such as failed test ID sets, failure counts, or explicit command exit status. If human judgment remains necessary, require immediate deviation logging and later skeptic review of injection timing.

### 9. Orchestrator parsing and report-writing discretion is under-specified

- **File**: `pilot_protocol.md`; `artifact_manifest.yaml`
- **Line or section**: `pilot_protocol.md` lines 125, 150-154; `artifact_manifest.yaml` lines 81-119, 150-168
- **Issue type**: orchestrator freedom to improvise / unsupported claims
- **Why it matters**: The orchestrator parses transcripts into events, computes analysis, writes the report, and applies the status gate. The protocol does not specify deterministic parsing rules, required raw transcript retention, or a claim-to-evidence table. This permits unintentional selective summarization.
- **Required correction**: Require raw transcripts as immutable artifacts, define deterministic event extraction rules, include parser version/hash if automated, and require every report claim to cite run IDs, step indices, evaluator evidence, and skeptic assessment.

### 10. Skeptic challenge happens after draft report but has no explicit blocking power

- **File**: `pilot_protocol.md`; `skeptic_prompt.md`; `status_gate.yaml`
- **Line or section**: `pilot_protocol.md` lines 144-154; `skeptic_prompt.md` lines 89-120; `status_gate.yaml` lines 52-67
- **Issue type**: missing skeptic challenge criteria / unsupported claims
- **Why it matters**: The skeptic is instructed to challenge claims, and the status gate mentions critical methodological flaws, but there is no required mapping from skeptic objections to report changes, invalidated claims, or status downgrades.
- **Required correction**: Add explicit skeptic disposition rules: each skeptic objection must be accepted, rebutted with cited evidence, or cause a status downgrade. Any `NO EVIDENCE`, `EVIDENCE AGAINST`, or critical methodological objection should block positive status unless resolved in the report.

### 11. Artifact manifest permits report completion without raw transcripts

- **File**: `artifact_manifest.yaml`
- **Line or section**: lines 23-34; lines 60-66; lines 171-181
- **Issue type**: lack of evidence requirements / unsupported claims
- **Why it matters**: Runner prompts require full transcripts, but the manifest does not list raw transcripts as required artifacts. Without raw transcripts, reviewers cannot verify event extraction, checkpoint timing, omitted evidence, or whether the evaluator received properly blinded data.
- **Required correction**: Add raw transcript files for all 12 runs as required immutable artifacts, with checksums and references from `events.jsonl`.

### 12. Evaluator rubric allows `uncertain`, but schema does not encode it

- **File**: `evaluator_prompt.md`; `artifact_manifest.yaml`
- **Line or section**: `evaluator_prompt.md` lines 11-14 and 121-149; `artifact_manifest.yaml` lines 121-148
- **Issue type**: missing neutral/harmful/failure categories / evidence requirements
- **Why it matters**: The evaluator is told to score "uncertain" when evidence is missing, but the output schema only shows numeric 1-5 values. This can force missing evidence into numeric scores and make downstream status decisions look more certain than the evidence permits.
- **Required correction**: Update the evaluator output schema to allow `"uncertain"` or `null` per dimension with a required `missing_evidence_reason`. Status calculations must exclude or explicitly handle uncertain dimensions.

### 13. Final report path is an append target, not a pilot-specific immutable artifact

- **File**: `artifact_manifest.yaml`
- **Line or section**: lines 60-66
- **Issue type**: unsupported claims / evidence traceability
- **Why it matters**: The manifest lists `docs/reflection-real-agent-pilot-report.md` as a human-readable report "appended to existing." Appending to a shared report can blur which claims belong to this pilot and makes artifact-level review harder.
- **Required correction**: Require a pilot-specific immutable report path under the protocol directory, or require section anchors/checksums that isolate the exact Pilot-003 report content.

## Checks With No Required Fix

- **Hypothesis neutrality**: `pilot_protocol.md` lines 26-29 uses non-directional language and explicitly allows helpful, neutral, or harmful results.
- **Runner initial prompt parity**: `baseline_runner_prompt.md` lines 7-9 and `guarded_runner_prompt.md` lines 5-9 match.
- **Runner initial hypothesis leakage**: No hypothesis is included in the runner initial prompt. The guarded checkpoint necessarily exposes the intervention during treatment, but not the experimental hypothesis.
- **Evaluator condition blinding intent**: `evaluator_prompt.md` lines 7-16 explicitly forbids condition inference and speculation.
- **Forbidden status controls**: `status_gate.yaml` lines 17-23 and 69-76 forbid `globally_active` and `metabolized`.
- **Deviation logging surface**: `deviation_log.md` lines 7-29 defines deviation fields and severities.

## Required Pre-Execution Disposition

Protocol design is approved. Runner execution must remain blocked until task workspaces are implemented, `fixture_validation.md` is produced, and the fixture validation evidence is independently reviewed.
