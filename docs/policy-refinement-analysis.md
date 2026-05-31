# Policy Refinement Analysis

## Scope and Sources

This pass analyzed the rejected broad policies and the under-evidenced promising policies using these evidence surfaces:

- `docs/policy-shadow-evaluation-report.md`
- `policies/review/policy_status_recommendations.yaml`
- `data/settlement_datasets/policy_shadow_eval/policy_shadow_results.jsonl`
- `data/settlement_datasets/policy_shadow_eval/policy_shadow_summary.csv`

The goal was not to make policies pass artificially. The goal was to preserve successful affordance paths, reduce false positives, and keep intervention bound to evidence likely to improve settlement.

## Rejected Broad Policies

### `test_before_final_answer`

- Original trigger: `final_answer_action = true AND prior_verification = false`
- False-positive pattern: treated any terminal action or successful completion as needing an explicit test, even when the trace already had another valid settlement signal or when testing was not the relevant proof surface.
- Successful traces it would have interrupted: `swe-clean-001`, `swe-bad-patch-003`, `api-clean-001`, `api-multi-002`, `api-recovered-005`, `ws-clean-001`, `ws-multi-search-002`
- Why it harmed successful traces: it would have blocked clean or recovered success traces across code, API, and shopping domains based only on the absence of a literal verification step. That adds payment without new settlement information and interrupts already successful paths.
- Narrower trigger proposal: `require_test_or_settlement_evidence_before_final_for_code_patch`
- Narrower trigger shape:
  - `domain = code`
  - action history includes edit, patch, or implementation
  - final answer or task completion is attempted
  - no settlement evidence exists
- Evidence needed before firing:
  - code-edit action history
  - final answer attempt after the edit
  - no passing test output between edit and final answer
  - no task-complete or explicit evaluator success marker
  - no other relevant successful command output

### `prevent_premature_concretion`

- Original trigger: `early_specific_action = true AND turn_index < 3`
- False-positive pattern: treated early concrete action as suspect even when the action was an affordable or correct next move.
- Successful traces it would have interrupted: `swe-clean-001`, `swe-recovered-002`, `swe-bad-patch-003`
- Why it harmed successful traces: code-repair traces often need an early concrete action after minimal inspection. The original rule could not distinguish a high-payment irreversible jump from an affordable exploratory or implementation step that actually settled the task.
- Narrower trigger proposal: `prevent_high_payment_action_when_constraints_unknown`
- Narrower trigger shape:
  - task constraints are missing or ambiguous
  - a high-payment or irreversible action is attempted
  - no intermediate representation exists
  - no user or environment feedback has resolved the ambiguity
- Evidence needed before firing:
  - missing or ambiguous task constraints
  - destructive, committing, submitting, purchasing, deleting, deploying, or similarly high-payment action
  - no prior analysis or intermediate plan
  - no feedback surface that resolved the ambiguity before the action

### `compare_constraints_before_selection`

- Original trigger: `selection_action = true AND prior_comparison = false`
- False-positive pattern: treated any selection without an explicit comparison step as harmful, even when the chosen option already contained explicit evidence that it matched the constraints.
- Successful traces it would have interrupted: `ws-clean-001`, `ws-multi-search-002`
- Why it harmed successful traces: both successful shopping traces already contained direct evidence that the chosen item met the constraints. Requiring a formal comparison step anyway would have added payment after the selection was already evidence-bound.
- Narrower trigger proposal: `require_constraint_match_before_multi_option_selection`
- Narrower trigger shape:
  - domain in decision-like selection tasks
  - at least two viable options are present
  - user constraints are explicit
  - a real selection is made
  - no explicit evidence shows the selected option satisfies the constraints
- Evidence needed before firing:
  - multi-option observation surface
  - explicit user constraints
  - final selection action
  - no explicit match signal such as `matches all constraints`, `all constraints met`, or equivalent constraint-to-selection evidence

## Promising Policies Strengthened Without Broadening

### `require_reflection_after_repeated_errors`

- Current result: `would_fire = 1`, `likely_helpful = 0`, `likely_harmful = 0`, `uncertain = 1`
- Why it remains promising: it still targets a real failure pattern, but current evidence is too thin to justify promotion.
- Precision added in this pass:
  - required evidence now requires at least three environment or tool error outputs
  - unresolved means the errors remain unsettled by the end of the trace or across the last turns
  - negative condition notes distinguish real error feedback from mere mentions of the word `error`
- Domain-specific trigger note: repeated errors should be counted from action/output feedback such as non-zero exits, failing tests, API/tool errors, or explicit runtime failures, not from narration.

### `require_explicit_settlement_for_failure`

- Current result: `would_fire = 5`, `likely_helpful = 2`, `likely_harmful = 0`, `uncertain = 3`
- Why it remains promising: it has the strongest helpful signal in the current active set, but still falls below the activation threshold.
- Precision added in this pass:
  - required evidence now binds failure claims to observable settlement evidence
  - negative conditions block firing when the trace does not actually settle as `failure_with_signal`
  - the rule now requires a failure claim plus evidence of the failure condition itself
- Domain-specific trigger note: acceptable evidence includes failing test output, non-zero command exits, tool error payloads, API/schema validation failures, or comparable explicit failure surfaces.

## Status and Historical Handling

- The three broad rejected policies were preserved as historical records and marked `status: superseded` in `data/settlement_datasets/policies.yaml`.
- Their refined replacements remain `status: proposed` and `activation_status: proposed`.
- `policies/review/policy_status_recommendations.yaml` now preserves superseded history instead of reclassifying those policies as `needs_more_evidence` merely because they are excluded from active shadow evaluation.

## Resulting Policy Surfaces

- Historical superseded policies:
  - `test_before_final_answer`
  - `prevent_premature_concretion`
  - `compare_constraints_before_selection`
- Narrower replacement policies:
  - `require_test_or_settlement_evidence_before_final_for_code_patch`
  - `prevent_high_payment_action_when_constraints_unknown`
  - `require_constraint_match_before_multi_option_selection`

The broad-trigger failures were used as error-correction data. The refined policies now require evidence that intervention is likely to improve settlement rather than merely sounding prudent in the abstract.
