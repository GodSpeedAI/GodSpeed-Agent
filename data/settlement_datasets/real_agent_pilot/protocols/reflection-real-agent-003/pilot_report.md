# Pilot Report: reflection-real-agent-003

## Scope

- **Pilot ID**: `reflection-real-agent-003`
- **Target Policy**: `require_reflection_before_continuing_after_second_unresolved_error`
- **Intervention Format**: Adjusted (with continuation directive), delivered as pre-baked context (DEV-001)
- **Agent**: Sub-agent (general type, not human-operated VS Code agent)
- **Runs**: 12 (6 baseline + 6 guarded), organized as 6 matched pairs
- **Constraints Held**: No global activation, no metabolization, no lowered thresholds.

## Prior Settlement

- `reflection-real-agent-001`: 6 runs, 3 matched pairs. Original format harmful (run-02). Adjusted format: 1 helpful (Task C), 1 neutral (Task B). Status: `needs_more_evidence`.
- `reflection-real-agent-002`: 10 runs, 5 matched pairs. Adjusted format only. 2 checkpoint deliveries: 1 helpful (Task F), 1 unfavorable (Task G). 3 tasks too easy. Status: `needs_more_evidence`.
- This pilot extends to 6 matched pairs with harder tasks (3 bugs each) designed to produce more errors.

## Protocol Deviation: DEV-001

**Critical context**: This pilot deviated from the protocol by using sub-agents instead of a human operator. The guarded condition was implemented by including the checkpoint text in the initial prompt (pre-baked context) rather than injecting it mid-conversation after observing a second failed test run.

- **Deviation ID**: DEV-001
- **Severity**: Medium
- **Impact**: Changes the intervention from "mid-conversation injection triggered by observed behavior" to "pre-baked context available from the start." This removes operator timing bias but fundamentally changes what is being tested.
- **Affected runs**: All 6 guarded runs (run-18, run-19, run-22, run-23, run-26, run-27)

## Tasks

| Task | Description | Bugs | Buggy Failing Tests | Total Tests |
|---|---|---|---|---|
| I | Event Logger | 3 (timestamp, level filter, counter) | 4 | 13 |
| J | LRU Cache | 3 (eviction, TTL, access order) | 4 | 13 |
| K | Token Auth | 3 (expiry boundary, signature, refresh) | 2 | 10 |
| L | Priority Queue | 3 (ordering, duplicates, peek copy) | 6 | 12 |
| M | Config Validator | 3 (nested keys, coercion, field check) | 6 | 16 |
| N | Rate Limiter | 3 (window boundary, counter, per-key) | 2 | 10 |

## Results

### Run-by-Run Summary

| Run | Condition | Task | Outcome | Errors | Test Runs | File Edits | Completed |
|---|---|---|---|---|---|---|---|
| run-17 | Baseline | I | Success | 3 | 4 | 3 | Yes |
| run-18 | Guarded | I | Success | 3 | 4 | 3 | Yes |
| run-19 | Guarded | J | Success | 3 | 4 | 3 | Yes |
| run-20 | Baseline | J | Success | 3 | 4 | 3 | Yes |
| run-21 | Baseline | K | Success | 2 | 3 | 2 | Yes |
| run-22 | Guarded | K | Success | 2 | 3 | 2 | Yes |
| run-23 | Guarded | L | Success | 3 | 4 | 3 | Yes |
| run-24 | Baseline | L | Success | 3 | 4 | 3 | Yes |
| run-25 | Baseline | M | Success | 3 | 4 | 3 | Yes |
| run-26 | Guarded | M | Success | 3 | 4 | 3 | Yes |
| run-27 | Guarded | N | Success | 2 | 3 | 2 | Yes |
| run-28 | Baseline | N | Success | 2 | 3 | 2 | Yes |

### Matched-Pair Comparisons

#### Task I: Baseline vs Guarded — NEUTRAL

Both runs fixed all 3 bugs identically. Same scores on all 6 dimensions. The guarded run included a "Pausing to consider" message between fixes but this did not change behavior.

**Verdict: NEUTRAL.** No measurable difference.

#### Task J: Baseline vs Guarded — NEUTRAL

Both runs fixed all 3 bugs identically. Same scores on all 6 dimensions. The guarded run's reflection step was formulaic and did not alter the fix sequence.

**Verdict: NEUTRAL.** No measurable difference.

#### Task K: Baseline vs Guarded — NEUTRAL/SLIGHTLY NEGATIVE

Baseline scored strategy_adaptation=5, overall=5. Guarded scored strategy_adaptation=4, overall=4. The 1-point difference on 2 dimensions may reflect measurement noise. Both runs completed successfully with identical fix sequences.

**Verdict: NEUTRAL to SLIGHTLY NEGATIVE.** The guarded run scored 1 point lower on 2 dimensions, but both runs produced substantively identical outcomes.

#### Task L: Baseline vs Guarded — NEUTRAL

Both runs fixed all 3 bugs identically. Same scores on all 6 dimensions.

**Verdict: NEUTRAL.** No measurable difference.

#### Task M: Baseline vs Guarded — NEUTRAL

Both runs fixed all 3 bugs identically. Same scores on all 6 dimensions.

**Verdict: NEUTRAL.** No measurable difference.

#### Task N: Baseline vs Guarded — NEUTRAL

Baseline scored strategy_adaptation=5, guarded scored 4. One dimension differed by 1 point. Both runs completed successfully.

**Verdict: NEUTRAL.** Minimal score difference, likely noise.

### Blinded Evaluator Scores

#### Aggregate Scores (all 6 pairs)

| Dimension | Baseline Avg | Guarded Avg | Delta |
|---|---|---|---|
| Error Recovery Efficiency | 4.00 | 4.00 | 0.00 |
| Edit Quality | 5.00 | 5.00 | 0.00 |
| Diagnostic Accuracy | 4.00 | 4.00 | 0.00 |
| Strategy Adaptation | 4.33 | 4.00 | -0.33 |
| Scope Discipline | 5.00 | 5.00 | 0.00 |
| Overall Execution | 4.33 | 4.17 | -0.17 |

#### Intervention-Only Analysis (all 6 guarded runs had pre-baked checkpoint)

| Dimension | Baseline Avg | Guarded Avg | Delta |
|---|---|---|---|
| Error Recovery Efficiency | 4.00 | 4.00 | 0.00 |
| Edit Quality | 5.00 | 5.00 | 0.00 |
| Diagnostic Accuracy | 4.00 | 4.00 | 0.00 |
| Strategy Adaptation | 4.33 | 4.00 | -0.33 |
| Scope Discipline | 5.00 | 5.00 | 0.00 |
| Overall Execution | 4.33 | 4.17 | -0.17 |

The aggregate and intervention-only analyses are identical because all guarded runs received the pre-baked checkpoint (DEV-001). There is no positive signal on any dimension.

### Metric Comparison

| Metric | Baseline Avg | Guarded Avg | Delta |
|---|---|---|---|
| Total steps | 18.7 | 19.7 | +1.0 |
| Error events | 2.7 | 2.7 | 0.0 |
| Test runs | 3.7 | 3.7 | 0.0 |
| File edits | 2.7 | 2.7 | 0.0 |
| File reads | 2.0 | 2.0 | 0.0 |

Guarded runs averaged 1 more step (the reflection message) with no improvement in any outcome metric.

### Skeptic Review

An independent skeptic reviewed all data. Key findings:

| Claim | Skeptic Rating |
|---|---|
| "Pre-baked reflection improves sub-agent performance" | **NO EVIDENCE** — Zero dimensions improved across 6 matched pairs |
| "Pre-baked reflection is never harmful" | **WEAK EVIDENCE** — Task K showed 1-point decline on 2 dimensions, possibly noise |
| "Pre-baked reflection adds cost without benefit" | **MODERATE EVIDENCE** — Consistent +1 step with zero improvement across all pairs |
| "Results generalize to mid-conversation injection" | **EVIDENCE AGAINST** — DEV-001 changes the intervention mechanism fundamentally |
| "Tasks were appropriately difficult" | **WEAK EVIDENCE** — Baseline performance at ceiling (all 4-5 scores) suggests tasks may be too easy for the policy to matter |

#### Skeptic Objections

1. **[blocks_positive_status]** DEV-001 changes the intervention from mid-conversation injection to pre-baked context. Results do not speak to the protocol's intended mechanism.
2. **[blocks_positive_status]** Baseline performance was at ceiling (4-5 on all dimensions). The policy cannot improve what is already near-maximal. Tasks may be too straightforward for the policy to have an observable effect.
3. **[requires_report_change]** The report must not claim the policy "does not work" — it can only claim that pre-baked reflection instructions did not improve sub-agent performance on these specific tasks.
4. **[requires_report_change]** The report must explicitly state that this pilot tests a different intervention than pilot-001 and pilot-002, and results are not directly comparable.
5. **[monitor_only]** Single evaluator, no inter-rater reliability.
6. **[monitor_only]** Sub-agent behavior may differ from VS Code agent behavior.
7. **[monitor_only]** Small sample (6 pairs) insufficient for statistical conclusions.

## Key Findings

### Finding 1: Pre-baked Reflection Does Not Improve Sub-Agent Performance

Across 6 matched pairs with 3-bug tasks, pre-baked reflection instructions in the initial prompt produced zero improvement on any measured dimension. The intervention added exactly 1 step per run (a formulaic "Pausing to consider" message) without changing fix strategy, diagnostic accuracy, or outcome quality.

### Finding 2: Baseline Performance at Ceiling

All baseline runs scored 4-5 on every dimension. The sub-agent fixed bugs correctly on the first attempt in every run. This ceiling effect means the policy had no room to improve performance even if the reflection were genuinely helpful.

### Finding 3: Formulaic Compliance, Not Genuine Reflection

The reflection content produced by the pre-baked instruction was generic and identical across all guarded runs ("Pausing to consider: 1) Tests still failing... 2) Additional bugs... 3) Read test output... 4) Next test run..."). This suggests mechanical compliance with the instruction rather than genuine reflective reasoning that could change behavior.

### Finding 4: DEV-001 Is a Different Intervention

Pre-baked context (available from the start) is fundamentally different from mid-conversation injection (triggered by observed repeated failure). The pre-baked version cannot interrupt a failing approach because it is present before any approach is taken. This limits what can be concluded about the protocol's intended mechanism.

### Finding 5: No Metabolization

This pilot does not metabolize the policy. It provides evidence that must be combined with prior pilot evidence.

## Claim-to-Evidence Table

| Claim | Run IDs | Step Indices | Evaluator Evidence | Skeptic Disposition |
|---|---|---|---|---|
| Pre-baked reflection did not improve performance | All 12 runs | N/A (all equal) | Zero delta on 4/6 dimensions; -0.33 on strategy | Accepted (MODERATE EVIDENCE) |
| Pre-baked reflection added 1 step per run | run-18,19,22,23,26,27 | Reflection step in each | +1.0 avg step delta | Accepted (MODERATE EVIDENCE) |
| Task K showed slight guarded disadvantage | run-21, run-22 | N/A | -1 on strategy_adaptation and overall | Monitor (WEAK EVIDENCE, possibly noise) |
| Baseline was at ceiling | All baseline runs | N/A | All scores 4-5 | Accepted (MODERATE EVIDENCE) |
| Results do not generalize to mid-conversation injection | DEV-001 | N/A | N/A | Accepted (blocks_positive_status) |

## Status Gate

| Criterion | Required | Actual | Met? |
|---|---|---|---|
| At least 6 matched pairs | ≥6 | 6 | Yes |
| Checkpoint delivered in ≥4 pairs | ≥4 | 6 (pre-baked) | Yes |
| Majority of deliveries helpful | >50% | 0/6 (0%) | **No** |
| 0 harmful with adjusted format | 0 | 0 clear harm, 1 slight negative | Marginal |
| Blinded evaluation | Done | Yes | Yes |
| Skeptic review | Done | Yes | Yes |
| Sufficient for activation | ≥5 consistent | 0 helpful, 0 harmful clear | **No** |

**Status**: `needs_more_evidence`

**Not allowed**: `globally_active`, `metabolized`

**Rationale**: The pre-baked intervention produced no improvement on any dimension. However, DEV-001 means this pilot tested a different mechanism than intended. The null result is legitimate but narrow. The policy's intended mechanism (mid-conversation injection) remains untested with harder tasks and sub-agents.

## Artifacts

- Events: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/events.jsonl`
- Policy fires: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/policy_fires.jsonl`
- Interventions: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/interventions.jsonl`
- Runner responses: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/runner_responses.jsonl`
- Run summaries: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/run_summaries.jsonl`
- Blinded evaluator events: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/evaluator_blinded_events.jsonl`
- Evaluator scores: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/evaluator_scores.jsonl`
- Unblinding key: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/unblinding_key.json`
- Skeptic review: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/skeptic_reviews.jsonl`
- Analysis: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/analysis.json`
- Pilot summary: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/pilot_summary.json`
- Task workspaces: `tmp/pilot_tasks/task_i/` through `tmp/pilot_tasks/task_n/`
- Reset script: `tmp/pilot_tasks/reset_pilot3.sh`
- This report: `data/settlement_datasets/real_agent_pilot/protocols/reflection-real-agent-003/pilot_report.md`

## Recommendations

1. **Do not activate the policy globally.** The evidence does not support consistent benefit from pre-baked reflection instructions.
2. **Test the intended mechanism.** A future pilot should use mid-conversation injection (as in pilot-001 and pilot-002) with harder tasks to test the protocol's actual intended intervention.
3. **Design tasks that produce baseline struggle.** All baseline runs scored 4-5 on every dimension. The policy can only help when the agent is struggling. Future tasks should be harder or should use weaker agents.
4. **Investigate whether reflection content quality matters.** The formulaic reflection in this pilot was identical across runs. Genuine reflection (specific to the failure) may produce different results.
5. **Do not conclude the policy "does not work."** This pilot tested pre-baked context, not mid-conversation injection. The null result applies only to the tested mechanism.

No policy was globally activated. No metabolization candidate was promoted. No thresholds were lowered.
