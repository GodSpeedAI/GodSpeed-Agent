# AgentTrove Real-Data Validation Report

**Date:** 2026-05-30
**Dataset:** open-thoughts/AgentTrove (HuggingFace, streaming mode)
**Sample:** 100 traces across 5 sources

## 1. Commands Run

```bash
# Ingestion (custom multi-source sampling script)
uv run python -c "
# Scanned dataset to find source boundaries:
# code_contests: rows 0-48000+
# staqc, freelancer, nl2bash, codeforces: rows 48000+
# Sampled 20 traces from each of 5 sources
"

# Pipeline
uv run python scripts/agenttrove/profile_traces.py \
  --input data/agenttrove/raw_samples/sample.jsonl \
  --output-dir data/agenttrove/profiles

uv run python -m scripts.agenttrove.label_settlements \
  --input data/agenttrove/raw_samples/sample.jsonl \
  --output data/agenttrove/settlements/settlement_traces.jsonl

uv run python -m scripts.agenttrove.export_sqlite \
  --input data/agenttrove/settlements/settlement_traces.jsonl \
  --raw data/agenttrove/raw_samples/sample.jsonl \
  --output data/agenttrove/settlement_ledger.sqlite

uv run python -m scripts.agenttrove.mine_harness_policies \
  --input data/agenttrove/settlements/settlement_traces.jsonl \
  --output policies/generated/agenttrove_harness_policies.yaml

uv run python -m scripts.agenttrove.build_eval_suites \
  --input data/agenttrove/settlements/settlement_traces.jsonl \
  --output-dir evals/agenttrove

# Queries
uv run python -m scripts.agenttrove.query_ledger --query summarize_by_source --format json
uv run python -m scripts.agenttrove.query_ledger --query summarize_by_settlement_quality --format json
uv run python -m scripts.agenttrove.query_ledger --query summarize_by_failure_mode --format json
uv run python -m scripts.agenttrove.query_ledger --query summarize_by_path_shape --format json
uv run python -m scripts.agenttrove.query_ledger --query policy_signal_summary --format json
```

All pipeline stages completed without errors.

## 2. Sample Composition

| Source | Count | Teacher | Avg Turns |
|---|---|---|---|
| code_contests | 20 | GPT-5-mini | 8.1 |
| codeforces | 20 | GLM-4.6 | 19.7 |
| freelancer | 20 | GPT 5.1 Nano | 15.2 |
| nl2bash | 20 | GPT 5.1 Nano | 10.1 |
| staqc | 20 | GPT 5.1 Nano | 11.7 |

**Reward distribution:** 100% null. The AgentTrove dataset does not provide numeric reward values for these traces. Outcome assessment must rely on structural analysis (final answer markers, error presence, terminal output content).

**Teacher distribution:** GPT 5.1 Nano (60), GPT-5-mini (20), GLM-4.6 (20).

## 3. Turn/Tool/Command/Error Statistics

```
Turns:       min=4   max=20   mean=13.0
Commands:    min=0   max=6    mean=0.1  (by regex detection)
Errors:      min=0   max=7    mean=1.0  (by regex detection)
Tool turns:  min=0   max=0    mean=0.0
Has final answer: 37/100
First error turn: 50/100 traces have at least one detected error
Final turn role: 100% assistant
```

### Source-level breakdown

| Source | Avg Turns | Avg Errors | Avg Commands |
|---|---|---|---|
| code_contests | 8.1 | 0.3 | 0.0 |
| codeforces | 19.7 | 0.4 | 0.0 |
| freelancer | 15.2 | 2.2 | 0.5 |
| nl2bash | 10.1 | 0.15 | 0.2 |
| staqc | 11.7 | 1.95 | 0.0 |

## 4. Settlement Quality Distribution

| Settlement Quality | Count |
|---|---|
| failure_with_signal | 38 |
| clean_success | 25 |
| failure_without_signal | 25 |
| unknown | 12 |

## 5. Path Shape Distribution

| Path Shape | Count |
|---|---|
| GA_to_GC_to_SC | 58 |
| unknown | 37 |
| GA_to_SA_to_SC | 3 |
| thrash | 2 |

## 6. Top Detected Failure Modes

| Failure Mode | Count |
|---|---|
| unknown | 45 |
| over_abstraction | 40 |
| context_loss | 36 |
| tool_thrashing | 1 |
| payment_spiral | 1 |

## 7. Five Settlement Record Examples

### Example 1: clean_success (code_contests)

```json
{
  "trace_id": "at-72d875cfe3f6",
  "source": "code_contests",
  "teacher_model": "GPT-5-mini",
  "desired_direction": {
    "type": "action",
    "description": "you are an ai assistant tasked with solving command-line tasks..."
  },
  "representational_state": {
    "start": "unknown", "desired": "unknown", "path_shape": "unknown"
  },
  "payment": {
    "turn_count": 6, "command_count": 0, "error_count": 0,
    "estimated_complexity": "medium"
  },
  "outcome": {"reward": null, "settlement_quality": "clean_success"},
  "cognitive_os_labels": {
    "failure_mode": "unknown",
    "metabolization_candidate": "repeated_success_pattern"
  }
}
```

### Example 2: failure_with_signal (freelancer)

```json
{
  "trace_id": "at-f6f3bdbfbe27",
  "source": "freelancer",
  "teacher_model": "GPT 5.1 Nano",
  "desired_direction": {"type": "implementation"},
  "representational_state": {
    "start": "general_abstract", "desired": "specific_concrete",
    "path_shape": "GA_to_GC_to_SC"
  },
  "payment": {
    "turn_count": 16, "command_count": 0, "error_count": 1,
    "estimated_complexity": "high"
  },
  "outcome": {"reward": null, "settlement_quality": "failure_with_signal"},
  "cognitive_os_labels": {
    "failure_mode": "over_abstraction",
    "metabolization_candidate": null
  }
}
```

### Example 3: failure_with_signal, over_abstraction (staqc)

```json
{
  "trace_id": "at-554757da3a03",
  "source": "staqc",
  "desired_direction": {"type": "artifact"},
  "payment": {
    "turn_count": 16, "command_count": 0, "error_count": 4,
    "estimated_complexity": "high"
  },
  "outcome": {"settlement_quality": "failure_with_signal"},
  "cognitive_os_labels": {
    "failure_mode": "over_abstraction",
    "harness_policy_signal": "require_reflection_after_repeated_tool_errors"
  }
}
```

### Example 4: multi-mode failure (codeforces)

```json
{
  "trace_id": "at-a21aa0e10f91",
  "source": "codeforces",
  "teacher_model": "GLM-4.6",
  "desired_direction": {"type": "action"},
  "payment": {
    "turn_count": 20, "command_count": 0, "error_count": 2,
    "estimated_complexity": "high"
  },
  "outcome": {"settlement_quality": "failure_with_signal"},
  "cognitive_os_labels": {
    "failure_mode": ["context_loss", "over_abstraction"],
    "harness_policy_signal": "require_reflection_after_repeated_tool_errors"
  }
}
```

### Example 5: clean_success (nl2bash)

```json
{
  "trace_id": "at-4d70706baea5",
  "source": "nl2bash",
  "desired_direction": {"type": "implementation"},
  "representational_state": {
    "path_shape": "GA_to_SA_to_SC",
    "start": "general_abstract", "desired": "specific_concrete"
  },
  "payment": {
    "turn_count": 10, "command_count": 1, "error_count": 0,
    "estimated_complexity": "medium"
  },
  "outcome": {"settlement_quality": "clean_success"},
  "cognitive_os_labels": {"failure_mode": "unknown"}
}
```

## 8. Five Generated Harness Policies

### Policy 1: detect_context_loss
- **Supporting traces:** 36/100 (36%)
- **Trigger:** turn_count > 10, later turns missing early keywords
- **Action:** require context check, restate original task
- **Example trace IDs:** at-a9257b14f0bd, at-8483142d3578, at-d316aa830f54
- **Assessment:** High false-positive rate (see Section 12)

### Policy 2: flag_over_abstraction
- **Supporting traces:** 40/100 (40%)
- **Trigger:** assistant_turn_count > 5, command_count == 0, no final answer
- **Action:** require concrete action, suggest tool use
- **Assessment:** High false-positive rate (see Section 12)

### Policy 3: require_reflection_after_repeated_tool_errors
- **Supporting traces:** 1/100 (1%)
- **Trigger:** error_count >= 2
- **Action:** require reflection, block next tool call until revised plan exists
- **Example trace:** at-dc1bb164a210 (freelancer source)
- **Assessment:** Plausible, but error detection has false-positive issues

### Policy 4: payment_cap_for_unproductive_paths
- **Supporting traces:** 47/100 (47%)
- **Trigger:** turn_count > 15, no success
- **Action:** require positive disintegration, suggest terminating path
- **Assessment:** High proportion; many traces are long by nature, not unproductive

### Policy 5: require_explicit_settlement_for_failure
- **Supporting traces:** 63/100 (63%)
- **Trigger:** settlement_quality in [failure_with_signal, failure_without_signal]
- **Action:** require failure analysis, record error correction signal
- **Assessment:** Reasonable; the dataset lacks reward signals so most traces default to failure

## 9. Five Generated Eval Cases

### Eval 1: tool_thrashing
```json
{
  "trace_id": "at-dc1bb164a210",
  "source": "freelancer",
  "observed_failure_mode": "tool_thrashing",
  "expected_harness_behavior": "require revised plan",
  "settlement_criteria": "Agent must break tool loop and propose alternative approach.",
  "evidence": {
    "payment": {"turn_count": 16, "command_count": 6, "error_count": 3},
    "path_shape": "thrash"
  }
}
```

### Eval 2: payment_spirals
```json
{
  "trace_id": "at-dc1bb164a210",
  "source": "freelancer",
  "observed_failure_mode": "payment_spiral",
  "expected_harness_behavior": "reset plan",
  "settlement_criteria": "Agent must recognize unproductive payment and trigger positive disintegration."
}
```

### Eval 3: brittle_successes
Empty. No brittle successes detected in this sample (all rewards are null).

### Eval 4: premature_closure
Empty. The minimum 3-turn threshold with final answer is not met (traces have at least 4 turns).

### Eval 5: successful_recovery_patterns
Empty. No traces classified as recovered_success in this sample.

## 10. SQLite Query Examples and Outputs

### summarize_by_source
```json
[
  {"source": "code_contests", "count": 20, "avg_turns": 8.1, "avg_commands": 0.0, "avg_errors": 0.3},
  {"source": "codeforces", "count": 20, "avg_turns": 19.7, "avg_commands": 0.0, "avg_errors": 0.4},
  {"source": "freelancer", "count": 20, "avg_turns": 15.2, "avg_commands": 0.5, "avg_errors": 2.2},
  {"source": "nl2bash", "count": 20, "avg_turns": 10.1, "avg_commands": 0.2, "avg_errors": 0.15},
  {"source": "staqc", "count": 20, "avg_turns": 11.7, "avg_commands": 0.0, "avg_errors": 1.95}
]
```

### summarize_by_settlement_quality
```json
[
  {"settlement_quality": "failure_with_signal", "count": 38},
  {"settlement_quality": "clean_success", "count": 25},
  {"settlement_quality": "failure_without_signal", "count": 25},
  {"settlement_quality": "unknown", "count": 12}
]
```

### summarize_by_failure_mode
```json
[
  {"failure_mode": "unknown", "count": 45},
  {"failure_mode": "over_abstraction", "count": 40},
  {"failure_mode": "context_loss", "count": 36},
  {"failure_mode": "payment_spiral", "count": 1},
  {"failure_mode": "tool_thrashing", "count": 1}
]
```

### summarize_by_path_shape
```json
[
  {"path_shape": "GA_to_GC_to_SC", "count": 58},
  {"path_shape": "unknown", "count": 37},
  {"path_shape": "GA_to_SA_to_SC", "count": 3},
  {"path_shape": "thrash", "count": 2}
]
```

### policy_signal_summary
```json
[
  {"signal_type": "require_reflection_after_repeated_tool_errors", "count": 23}
]
```

## 11. Schema and Parsing Findings

### 11a. Trace Structure

AgentTrove traces from these sources use a **simulated terminal interaction** pattern:
- **Roles:** alternating `user` and `assistant` (no explicit `tool` role)
- **Assistant messages:** JSON objects with keys `analysis`, `plan`, `commands`, `task_complete`
- **User messages:** system prompt (first), then terminal output
- **Commands:** embedded as `{"commands": [{"keystrokes": "..."}]}` inside assistant JSON

### 11b. Missing Fields

- **reward:** 100% null across the sample
- **tool turns:** 0 across the entire sample (no explicit tool role)
- **task_binary, judgment, verifier_output, ground_truth:** 100% null or absent
- **task_complete field:** Present in assistant JSON but not in top-level metadata

### 11c. Dataset Organization

The dataset is **sorted by source**. The first ~48,000 rows are `code_contests`, followed by `staqc`, `freelancer`, `nl2bash`, `codeforces`. Random sampling with `--max-traces 100` returns only code_contests traces. Multi-source sampling requires either source filtering or offset skipping.

## 12. Questionable Labels

### 12a. over_abstraction: 40/100 — LIKELY FALSE POSITIVE

**Root cause:** The detection checks `assistant_turn_count > 5 AND command_count == 0 AND not has_final_answer`. In alternating user/assistant traces, any trace with >10 turns has >5 assistant turns. The `command_count` is nearly 0 because regex-based command detection does not parse the JSON `commands` field. So every long trace without a final-answer marker is labeled `over_abstraction`.

**Actual commands in data:** Parsing assistant JSON reveals 528/648 assistant messages contain a `commands` array with a total of **2,234 commands**. The regex detector catches almost none of these.

**Verdict:** The over_abstraction label is unreliable in its current form. Most flagged traces are legitimate multi-step problem-solving, not avoidance of payment.

### 12b. context_loss: 36/100 — LIKELY FALSE POSITIVE

**Root cause:** The detection compares word overlap between the first user message (which is the system prompt) and the last assistant message. The system prompt is boilerplate text that naturally has no word overlap with specific terminal output or analysis text.

**Verdict:** The context_loss heuristic is not appropriate for traces where the first user message is a generic system prompt rather than a specific task description.

### 12c. clean_success: 25/100 — POSSIBLE UNDERCOUNT

**Root cause:** Settlement quality relies on `reward` being >= 1.0 for success classification. Since reward is 100% null, the classifier falls through to checking `has_final_answer` and error count. The `has_final_answer` check looks for markers like "the answer is" or "in conclusion" in the last assistant message, but real traces use structured JSON output with `task_complete: true` rather than prose markers.

**Finding:** 26 traces end with `task_complete: true` in the JSON, but only 37 are flagged with `has_final_answer`. The 26 task_complete traces should all be counted as having a final answer, but the regex does not check the `task_complete` JSON field.

### 12d. desired_direction: mostly "action" or "implementation" — LIMITED DISCRIMINATION

The first user message in these traces is a generic system prompt ("You are an AI assistant tasked with solving command-line tasks..."), not the specific task description. The keyword classifier operates on this boilerplate, not the actual task content.

## 13. Recommended Fixes Before Live Harness Use

### Critical (blocks meaningful policy mining)

1. **Parse JSON commands from assistant messages.** The current regex-only approach misses 99%+ of commands. Add a JSON parser that extracts the `commands` field from assistant JSON objects, specifically the `keystrokes` sub-field. This will fix command_count, over_abstraction detection, tool_thrashing detection, and payment estimation.

2. **Use task_complete JSON field for final answer detection.** Add detection for `task_complete: true` in parsed assistant JSON, not just prose markers.

3. **Fix context_loss heuristic.** Do not compare the first user message (which is a system prompt) with the last assistant. Instead, compare the task-specific content (which may appear in later user messages or in the `instruction`/`ground_truth` metadata fields).

### Important (improves label quality)

4. **Parse error-like content from terminal output.** Real errors appear in user messages (terminal output), not just assistant/tool messages. The current detection only checks assistant and tool roles. User messages contain the actual stderr output and should be the primary error source.

5. **Handle null-reward datasets.** When reward is null, the settlement quality classifier should use alternative signals: `task_complete` JSON field, verifier_output metadata, or terminal output analysis. Currently it falls through to weaker heuristics.

6. **Extract desired_direction from task content, not system prompt.** The first user message is boilerplate. The actual task appears in the system prompt or in the ground_truth/instruction metadata. The classifier should skip the system prompt boilerplate.

### Nice-to-have

7. **Add offset-based sampling.** Since the dataset is sorted by source, add a `--skip` CLI arg to sample from different source regions without scanning 50K+ rows.

8. **Handle the "fail" keyword false positive.** The `\bfail(?:ed|ure)?\b` pattern matches 56 assistant messages that contain "fail" in analysis text (e.g., "if the check fails"). Consider requiring "fail" to appear in terminal output context, not in analysis/explanation.

## 14. Assessment: Are Deterministic Labels Good Enough?

**Current state: No.** The deterministic labels have significant systematic biases:

- **over_abstraction** is the dominant label (40%) but is almost entirely false positive due to missed JSON command parsing
- **context_loss** is the second most common (36%) but is false positive due to comparing boilerplate with output
- **clean_success** undercounts because `task_complete` JSON field is not checked
- **command_count** is near zero because JSON commands are not parsed

**Required before policy mining is meaningful:**
1. JSON command parsing (fixes command_count, over_abstraction, tool_thrashing)
2. task_complete detection (fixes settlement quality)
3. Error detection on user/terminal messages (fixes error_count)
4. Context loss heuristic fix (removes false positive)

Once these are fixed, the pipeline structure is sound. The YAML rules framework, SQLite schema, policy mining logic, and eval suite generation are all correctly implemented. The issue is purely in the input feature extraction layer.

## 15. What Works Well

- Streaming ingestion handled 100 traces across 5 sources without errors
- Profile generation produces correct statistics from the data it receives
- SQLite export creates valid, queryable database with proper indexes
- Policy mining generates well-structured policies with evidence
- Eval suite generation correctly filters by failure mode
- SFT export correctly gates on settlement quality
- All 49 unit tests pass against local fixtures
- The pipeline ran end-to-end without manual patching

The architecture is sound. The feature extraction layer needs refinement for this specific dataset schema.
