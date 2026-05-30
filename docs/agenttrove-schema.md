# AgentTrove Schema Reference

## Raw Trace Schema (JSONL)

Each row in `data/agenttrove/raw_samples/*.jsonl`:

```json
{
  "trace_id": "at-<hash>",
  "source": "swesmith",
  "teacher": "gpt-4",
  "task_id": "task-abc123",
  "reward": 1.0,
  "metadata": {
    "original_source": "swesmith",
    "original_teacher": "gpt-4",
    "model": "gpt-4o",
    "model_provider": "openai",
    "result": "resolved"
  },
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...", "tool_name": "bash", "metadata": {}},
    {"role": "tool", "content": "..."}
  ]
}
```

### Message Turn Fields

| Field | Type | Required | Description |
|---|---|---|---|
| role | string | Yes | One of: system, user, assistant, tool, unknown |
| content | string | Yes | Turn content text |
| tool_name | string | No | Tool name if applicable |
| metadata | object | No | Additional turn-level metadata |

### Metadata Fields

Preserved from the original AgentTrove row when present:

- `original_source` - Dataset source (swesmith, codeforces, etc.)
- `original_teacher` - Teacher model name
- `model` - Model used
- `model_provider` - Model provider
- `task` / `task_id` - Task identifier
- `result` - Outcome label
- `reward` - Numeric reward
- `episode`, `trajectory_id`, `sandbox_id` - Session identifiers

## Trace Profile Schema (JSONL)

Each row in `data/agenttrove/profiles/trace_profile.jsonl`:

| Field | Type | Description |
|---|---|---|
| trace_id | string | Unique trace identifier |
| source | string | Dataset source |
| teacher | string | Teacher model |
| reward | float/null | Numeric reward |
| turn_count | int | Total number of turns |
| system_turn_count | int | Number of system turns |
| user_turn_count | int | Number of user turns |
| assistant_turn_count | int | Number of assistant turns |
| tool_turn_count | int | Number of tool turns |
| command_like_action_count | int | Turns with command-like content |
| error_like_output_count | int | Turns with error-like content |
| first_error_turn | int/null | Index of first error-like turn |
| final_turn_role | string | Role of the last turn |
| has_final_answer | bool | Whether the trace ends with a final answer marker |

## Settlement Trace Schema (JSONL)

Each row in `data/agenttrove/settlements/settlement_traces.jsonl`:

```json
{
  "trace_id": "at-<hash>",
  "source": "swesmith",
  "teacher_model": "gpt-4",
  "task_id": "task-abc123",
  "desired_direction": {
    "type": "implementation | diagnosis | action | artifact | strategy | theory | unknown",
    "description": "...",
    "settlement_target": "..."
  },
  "representational_state": {
    "start": "general_abstract | specific_abstract | general_concrete | specific_concrete | unknown",
    "desired": "general_abstract | specific_abstract | general_concrete | specific_concrete | unknown",
    "path_shape": "GA_to_SA_to_SC | GA_to_GC_to_SC | direct_jump | direct_action_with_feedback | thrash | loop | unknown"
  },
  "payment": {
    "turn_count": 0,
    "tool_call_count": 0,
    "command_count": 0,
    "error_count": 0,
    "recovery_attempt_count": 0,
    "estimated_complexity": "low | medium | high | unknown"
  },
  "affordance_path": {
    "actions": [
      {"turn_index": 0, "role": "assistant", "is_command": true}
    ],
    "recovery_events": [
      {"error_turn": 2, "recovery_turn": 3, "recovered": true}
    ]
  },
  "outcome": {
    "reward": 1.0,
    "settlement_quality": "clean_success | recovered_success | partial_success | brittle_success | failure_with_signal | failure_without_signal | unknown"
  },
  "cognitive_os_labels": {
    "failure_mode": "premature_closure | tool_thrashing | failed_recovery | representation_jump | payment_spiral | context_loss | over_abstraction | premature_concretion | missing_affordance | brittle_success | unknown",
    "metabolization_candidate": "repeated_success_pattern | clean_recovery_pattern | null",
    "harness_policy_signal": "require_reflection_after_repeated_tool_errors | block_premature_final_answer | payment_spiral_reset | force_intermediate_representation_for_direct_jump | null"
  }
}
```

## SQLite Schema

Tables: `traces`, `turns`, `actions`, `settlements`, `labels`, `failure_modes`, `policy_signals`, `eval_memberships`

Key indexes: `source`, `reward`, `settlement_quality`, `failure_mode`, `path_shape`, `desired_direction_type`

## Eval Suite Schema (JSONL)

Each row in `evals/agenttrove/*.jsonl`:

```json
{
  "trace_id": "...",
  "source": "...",
  "input_context": "...",
  "observed_failure_mode": "...",
  "expected_harness_behavior": "...",
  "settlement_criteria": "...",
  "evidence": {}
}
```

## SFT Export Schema (JSONL)

Each row in `data/agenttrove/sft/sharegpt_clean.jsonl`:

```json
{
  "conversations": [
    {"from": "user", "value": "..."},
    {"from": "assistant", "value": "..."}
  ],
  "source": "...",
  "teacher": "...",
  "trace_id": "...",
  "settlement_quality": "clean_success"
}
```
