# Blinding Plan

## Overview

The evaluator must score runs without knowing which condition (baseline or guarded) each run belongs to. This document describes how blinding is achieved and verified.

## Blinding Procedure

### Step 1: Anonymize Run IDs

After all runner runs are complete, generate a mapping from original run_ids to anonymous labels:

| Original | Anonymous |
|---|---|
| run-17 (baseline, Task I) | Randomly assigned from pool |
| run-18 (guarded, Task I) | Randomly assigned from pool |
| run-19 (baseline, Task J) | Randomly assigned from pool |
| run-20 (guarded, Task J) | Randomly assigned from pool |
| run-21 (baseline, Task K) | Randomly assigned from pool |
| run-22 (guarded, Task K) | Randomly assigned from pool |
| run-23 (baseline, Task L) | Randomly assigned from pool |
| run-24 (guarded, Task L) | Randomly assigned from pool |
| run-25 (baseline, Task M) | Randomly assigned from pool |
| run-26 (guarded, Task M) | Randomly assigned from pool |
| run-27 (baseline, Task N) | Randomly assigned from pool |
| run-28 (guarded, Task N) | Randomly assigned from pool |

Anonymous labels are drawn from a pool of 12 unique identifiers (e.g., Greek letters, color names, or Run-A through Run-L). The assignment is randomized so that paired runs are not adjacent in the label space.

### Step 2: Strip Revealing Events

Remove the following event types from the blinded data:
- `intervention` — reveals that a checkpoint was delivered.
- `user_message` or `operator_message` events containing checkpoint text or checkpoint-related discussion.

If the transcript parser stores user/operator messages under another event type, those messages must still be treated as revealing content and removed or neutralized before evaluator delivery.

### Step 3: Strip Revealing Metadata

Remove the following metadata keys from all events:
- `intervention_type`
- `post_checkpoint`
- `reflection_summary_included`
- `reflection_timing`
- `fix_target`
- `fix_quality`
- `introduced_bug`
- `bug_type`

Keep these metadata keys (they are observable from test output):
- `error_type`
- `failed_tests`
- `caused_by_agent_edit`
- `errors`
- `error_detail`

### Step 4: Neutralize Revealing Content

Scan every string field in every event, including `content`, tool arguments, tool output summaries, metadata values, and nested strings. If any field mentions "reflection", "checkpoint", "intervention", "guarded", "baseline", "policy fire", or the verbatim checkpoint text, the field must be removed or replaced before evaluator delivery.

Neutralization must not create a condition-specific cue. If model analysis content is summarized for one run, comparable model analysis content must be summarized across all runs using the same rule. Do not use a fixed placeholder that appears only in checkpoint-delivery runs.

### Step 5: Shuffle Run Order

The blinded events file should present runs in alphabetical order by anonymous label, not in the original execution order. This prevents the evaluator from inferring pairs from adjacency.

### Step 6: Store Unblinding Key

Write the mapping to `unblinding_key.json`. This file is:
- NOT shared with the evaluator.
- Shared with the skeptic AFTER evaluation is complete.
- Used by the orchestrator for analysis.

## Verification

After generating blinded data, run automated checks:

1. No `intervention` event types remain.
2. No metadata keys contain `checkpoint`, `intervention`, `reflection`, `post_checkpoint`.
3. No string field anywhere in the blinded data contains the words "checkpoint", "intervention", "reflection", "guarded", "baseline", or "policy fire" (case-insensitive).
4. All 12 runs have events in the blinded data.
5. No original run_ids appear in the blinded data.
6. Neutralized placeholders or summaries are not unique to a known condition.

If any check fails, the blinding is invalid and must be regenerated.

## Unblinding

Unblinding occurs AFTER the evaluator has submitted all scores. The orchestrator:
1. Loads `evaluator_scores.jsonl`.
2. Loads `unblinding_key.json`.
3. Maps anonymous labels back to original run_ids and conditions.
4. Computes matched-pair comparisons.
5. Shares unblinded data with the skeptic.

## Compromise Handling

If blinding is compromised (evaluator discovers condition assignments):
1. Record the compromise in `deviation_log.md`.
2. Discard the evaluator's scores for the compromised runs.
3. Re-run evaluation with a new evaluator on re-blinded data, if possible.
4. If re-blinding is not possible, note the compromise in the final report and treat affected scores as potentially biased.
