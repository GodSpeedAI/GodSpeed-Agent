# Settlement Dataset Canonical Schema

## Full JSON Schema

Every adapter must produce records conforming to this structure. Fields marked **required** must always be present. Fields marked **optional** may be null or empty but must still be present as keys.

```json
{
  "dataset": "string (required)",
  "domain": "string (required)",
  "task_id": "string (required)",
  "source_uri": "string (required)",
  "desired_direction": {
    "type": "string (required)",
    "description": "string (required)",
    "settlement_target": "string (optional)"
  },
  "environment": {
    "type": "string (required)",
    "has_runnable_feedback": "boolean (required)",
    "feedback_type": "string (required)"
  },
  "representational_state": {
    "start": "string (required)",
    "desired": "string (required)",
    "path_shape": "string (required)",
    "confidence": "float (required)",
    "evidence": "list[string] (required)"
  },
  "payment": {
    "turns": "integer (required)",
    "tool_calls": "integer (required)",
    "commands": "integer (required)",
    "page_actions": "integer (required)",
    "api_calls": "integer (required)",
    "elapsed_steps": "integer (required)",
    "error_count": "integer (required)",
    "estimated_complexity": "string (required)",
    "evidence": "list[string] (required)"
  },
  "affordance_path": {
    "actions": "list[action] (required)",
    "observations": "list[observation] (optional)",
    "recovery_events": "list[recovery_event] (optional)"
  },
  "outcome": {
    "success": "boolean|null (required)",
    "reward": "float|null (required)",
    "score": "float|null (required)",
    "settlement_quality": "string (required)",
    "confidence": "float (required)",
    "evidence": "list[string] (required)"
  },
  "labels": {
    "failure_mode": "string|null (required)",
    "failure_mode_confidence": "float (required)",
    "failure_mode_evidence": "list[string] (required)",
    "harness_policy_signal": "string|null (required)",
    "harness_policy_signal_confidence": "float (required)",
    "harness_policy_signal_evidence": "list[string] (required)",
    "metabolization_candidate": "string|null (required)",
    "metabolization_candidate_confidence": "float (required)",
    "metabolization_candidate_evidence": "list[string] (required)"
  },
  "metadata": "object (required)"
}
```

## Top-Level Field Descriptions

| Field | Required | Description |
|---|---|---|
| `dataset` | Yes | Adapter name identifier (e.g., "agenttrove", "swegym", "apibank", "webshop") |
| `domain` | Yes | Dataset domain category |
| `task_id` | Yes | Unique task identifier within the dataset |
| `source_uri` | Yes | URI or identifier for the dataset source |
| `desired_direction` | Yes | The active attractor the agent is attempting to reach |
| `environment` | Yes | Description of the execution environment |
| `representational_state` | Yes | The current position in scope and mode-of-givenness space |
| `payment` | Yes | Cost proxy counts for the affordance-path attempt |
| `affordance_path` | Yes | The sequence of actions and observations constituting the path |
| `outcome` | Yes | Settlement result with quality classification |
| `labels` | Yes | Failure mode, policy signal, and metabolization candidate labels |
| `metadata` | Yes | Dataset-specific metadata (source, teacher, repo, etc.) |

## Valid Enum Values

### domain

| Value | Description |
|---|---|
| `code` | Code-related tasks (editing, debugging, testing) |
| `api` | API interaction tasks (calling, parameterizing, sequencing) |
| `shopping` | Shopping/navigation tasks (searching, comparing, selecting) |

### settlement_quality

| Value | Description |
|---|---|
| `clean_success` | Task completed with no errors or retries |
| `recovered_success` | Task completed after encountering and recovering from errors |
| `partial_success` | Task partially completed (some sub-goals met) |
| `brittle_success` | Task completed but with fragile or questionable approach |
| `failure_with_signal` | Task failed but the failure provides usable error-correction data |
| `failure_without_signal` | Task failed with no actionable feedback |
| `unknown` | Settlement quality could not be determined |

### estimated_complexity

| Value | Description |
|---|---|
| `low` / `simple` | Few steps, minimal payment |
| `medium` / `moderate` | Moderate steps and payment |
| `high` / `complex` | Many steps, high payment |

### failure_mode

| Value | Description | Primary Domain |
|---|---|---|
| `premature_closure` | Agent submits answer before verifying | code, api |
| `tool_thrashing` | Repeated tool calls with errors, no strategy change | code |
| `failed_recovery` | Agent attempted recovery but failed | code |
| `representation_jump` | Agent jumped from general to specific without intermediate step | code |
| `payment_spiral` | Excessive steps with no progress | code, api |
| `context_loss` | Later turns ignore early constraints | code |
| `over_abstraction` | Extensive explanation without action | code |
| `premature_concretion` | First action hits immediate error due to no analysis | code |
| `poor_localization` | Edit or patch applied to wrong location | code |
| `bad_patch` | Patch applied but tests still fail | code |
| `test_failure` | Final test suite does not pass | code |
| `wrong_tool` | API call uses tool not in available set | api |
| `wrong_arguments` | API call has missing or incorrect parameters | api |
| `missing_precondition` | API calls made in wrong order | api |
| `constraint_miss` | Selected item violates stated constraints | shopping |
| `premature_choice` | Purchase made without inspecting options | shopping |
| `over_search` | Excessive searches without making progress | shopping |
| `missing_affordance` | Unrecognized action type in trajectory | shopping |

### path_shape

| Value | Description |
|---|---|
| `GA_to_SA_to_SC` | General abstract to specific abstract to specific concrete |
| `GA_to_GC_to_SC` | General abstract to general concrete to specific concrete |
| `direct_jump` | Immediate specific action without intermediate steps |
| `direct_action_with_feedback` | Single action with observable feedback |
| `thrash` | Repeated rapid actions indicating no coherent strategy |
| `loop` | Cyclical action pattern |
| `sequential` | Sequential multi-step completion |
| `sequential_with_analysis` | Sequential steps with prior analysis |
| `mixed_navigation` | Mixed search and navigation pattern |
| `unknown` | Path shape could not be determined |

### environment.type

| Value | Description |
|---|---|
| `simulated_terminal` | Simulated terminal environment (AgentTrove) |
| `code_repository` | Repository with runnable tests (SWE-Gym) |
| `api_sandbox` | API call sandbox with structured responses (API-Bank) |
| `web_shopping` | Web shopping environment with search/browse/buy (WebShop) |
| `unknown` | Environment type could not be determined |

### environment.feedback_type

| Value | Description |
|---|---|
| `tool_output` | Feedback comes from tool/command output |
| `tests` | Feedback comes from test suite execution |
| `state_check` | Feedback comes from environment state comparison |
| `unknown` | Feedback type could not be determined |

## What to Set When a Dataset Cannot Support a Field

When a dataset does not produce data for a required field, use the empty defaults:

| Field | Default When Unsupported |
|---|---|
| `outcome.success` | `null` |
| `outcome.reward` | `null` |
| `outcome.score` | `null` |
| `outcome.settlement_quality` | `"unknown"` |
| `outcome.confidence` | `0.0` |
| `outcome.evidence` | `[]` |
| `payment.*` (all counts) | `0` |
| `payment.estimated_complexity` | `"unknown"` |
| `payment.evidence` | `[]` |
| `representational_state.*` | `"unknown"` / `0.0` / `[]` |
| `environment.type` | `"unknown"` |
| `environment.has_runnable_feedback` | `false` |
| `environment.feedback_type` | `"unknown"` |
| `labels.failure_mode` | `null` |
| `labels.failure_mode_confidence` | `0.0` |
| `labels.failure_mode_evidence` | `[]` |
| `labels.harness_policy_signal` | `null` |
| `labels.harness_policy_signal_confidence` | `0.0` |
| `labels.harness_policy_signal_evidence` | `[]` |
| `labels.metabolization_candidate` | `null` |
| `labels.metabolization_candidate_confidence` | `0.0` |
| `labels.metabolization_candidate_evidence` | `[]` |

Never omit a required field. Set it to its empty default instead. The `validate_record()` method checks for missing fields and reports errors.

## Payment Field Descriptions

| Field | Description |
|---|---|
| `turns` | Total number of conversational turns in the trace |
| `tool_calls` | Number of explicit tool calls made |
| `commands` | Number of commands executed (shell, edit, search) |
| `page_actions` | Number of page interaction actions (click, buy, navigate) |
| `api_calls` | Number of API calls made |
| `elapsed_steps` | Total number of steps in the trajectory (may differ from turns) |
| `error_count` | Number of errors detected in observations |
| `estimated_complexity` | Overall payment complexity estimate |
| `evidence` | List of strings documenting how payment was calculated |

## Labels Sub-Schema

The labels sub-schema contains three parallel label groups. Each has a value, confidence, and evidence:

| Label Group | Value Field | Confidence Field | Evidence Field |
|---|---|---|---|
| Failure mode | `failure_mode` | `failure_mode_confidence` | `failure_mode_evidence` |
| Policy signal | `harness_policy_signal` | `harness_policy_signal_confidence` | `harness_policy_signal_evidence` |
| Metabolization | `metabolization_candidate` | `metabolization_candidate_confidence` | `metabolization_candidate_evidence` |

All three groups are always present. When no label applies, the value is `null`, confidence is `0.0`, and evidence is `[]`.

## Example Records

### AgentTrove (code domain)

```json
{
  "dataset": "agenttrove",
  "domain": "code",
  "task_id": "at-72d875cfe3f6",
  "source_uri": "open-thoughts/AgentTrove",
  "desired_direction": {"type": "action", "description": "Solve command-line task", "settlement_target": "task_completion"},
  "environment": {"type": "simulated_terminal", "has_runnable_feedback": true, "feedback_type": "tool_output"},
  "representational_state": {"start": "unknown", "desired": "unknown", "path_shape": "unknown", "confidence": 0.3, "evidence": []},
  "payment": {"turns": 6, "tool_calls": 0, "commands": 3, "page_actions": 0, "api_calls": 0, "elapsed_steps": 6, "error_count": 0, "estimated_complexity": "medium", "evidence": ["json_command_count:3"]},
  "outcome": {"success": true, "reward": null, "score": null, "settlement_quality": "clean_success", "confidence": 0.85, "evidence": ["task_complete:true"]},
  "labels": {"failure_mode": null, "failure_mode_confidence": 0.0, "failure_mode_evidence": [], "harness_policy_signal": null, "harness_policy_signal_confidence": 0.0, "harness_policy_signal_evidence": [], "metabolization_candidate": "repeated_success_pattern", "metabolization_candidate_confidence": 0.8, "metabolization_candidate_evidence": ["metabolization_pattern:repeated_success_pattern"]}
}
```

### SWE-Gym (code domain)

```json
{
  "dataset": "swegym",
  "domain": "code",
  "task_id": "swegym-001",
  "source_uri": "fixture:swegym_style",
  "desired_direction": {"type": "implementation", "description": "Fix authentication bug", "settlement_target": "pass_all_tests"},
  "environment": {"type": "code_repository", "has_runnable_feedback": true, "feedback_type": "tests"},
  "representational_state": {"start": "general", "desired": "specific_concrete", "path_shape": "GA_to_GC_to_SC", "confidence": 0.7, "evidence": ["analysis_at=1", "first_command_at=3"]},
  "payment": {"turns": 8, "tool_calls": 4, "commands": 3, "page_actions": 0, "api_calls": 0, "elapsed_steps": 8, "error_count": 1, "estimated_complexity": "medium", "evidence": ["commands=3", "tool_responses=4"]},
  "outcome": {"success": true, "reward": 1.0, "score": 1.0, "settlement_quality": "recovered_success", "confidence": 0.8, "evidence": ["test_result.resolved=true"]},
  "labels": {"failure_mode": null, "failure_mode_confidence": 0.0, "failure_mode_evidence": [], "harness_policy_signal": null, "harness_policy_signal_confidence": 0.0, "harness_policy_signal_evidence": [], "metabolization_candidate": "yes", "metabolization_candidate_confidence": 0.8, "metabolization_candidate_evidence": ["resolved=true"]}
}
```

### API-Bank (api domain)

```json
{
  "dataset": "apibank",
  "domain": "api",
  "task_id": "apibank-003",
  "source_uri": "fixture:apibank_style",
  "desired_direction": {"type": "action", "description": "Book a flight from NYC to LA", "settlement_target": "complete_all_api_calls_correctly"},
  "environment": {"type": "api_sandbox", "has_runnable_feedback": true, "feedback_type": "tool_output"},
  "representational_state": {"start": "sequential_api_calls", "desired": "multi_step_api_completion", "path_shape": "sequential", "confidence": 0.8, "evidence": ["api_call_count:3"]},
  "payment": {"turns": 7, "tool_calls": 3, "commands": 0, "page_actions": 0, "api_calls": 3, "elapsed_steps": 7, "error_count": 0, "estimated_complexity": "moderate", "evidence": ["api_calls:3"]},
  "outcome": {"success": true, "reward": 1.0, "score": 1.0, "settlement_quality": "clean_success", "confidence": 0.9, "evidence": ["actual_calls:search_flights,book_flight,confirm_booking"]},
  "labels": {"failure_mode": null, "failure_mode_confidence": 0.0, "failure_mode_evidence": [], "harness_policy_signal": null, "harness_policy_signal_confidence": 0.0, "harness_policy_signal_evidence": [], "metabolization_candidate": "inspect_api_schema_before_call", "metabolization_candidate_confidence": 0.7, "metabolization_candidate_evidence": ["candidate_count:1"]}
}
```

### WebShop (shopping domain)

```json
{
  "dataset": "webshop",
  "domain": "shopping",
  "task_id": "webshop-002",
  "source_uri": "fixture:webshop_style",
  "desired_direction": {"type": "action", "description": "Find a red laptop under $800", "settlement_target": "find_product_matching_all_constraints"},
  "environment": {"type": "web_shopping", "has_runnable_feedback": true, "feedback_type": "state_check"},
  "representational_state": {"start": "general", "desired": "specific", "path_shape": "GA_to_SA_to_SC", "confidence": 0.75, "evidence": ["multiple_searches:2", "comparisons_before_selection"]},
  "payment": {"turns": 5, "tool_calls": 0, "commands": 2, "page_actions": 2, "api_calls": 0, "elapsed_steps": 8, "error_count": 0, "estimated_complexity": "medium", "evidence": ["searches:2", "clicks:1", "buys:1"]},
  "outcome": {"success": true, "reward": 1.0, "score": 1.0, "settlement_quality": "clean_success", "confidence": 0.9, "evidence": ["chosen_item:RedBook-Pro", "reward:1.0"]},
  "labels": {"failure_mode": null, "failure_mode_confidence": 0.0, "failure_mode_evidence": [], "harness_policy_signal": null, "harness_policy_signal_confidence": 0.0, "harness_policy_signal_evidence": [], "metabolization_candidate": "compare_constraints_before_selection", "metabolization_candidate_confidence": 0.8, "metabolization_candidate_evidence": ["successful_comparison_and_purchase"]}
}
```
