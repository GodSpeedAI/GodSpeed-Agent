# Eval Replay Vocabulary Alignment

## Why Raw Replay Was Reporting `0.0%`

The original replay path compared policy actions and eval expected behaviors as raw strings or narrow structured fragments.

That failed for a simple reason: the two surfaces were describing the same intervention in different vocabularies.

Examples:

- policy action: `require_operator: verification_step`
- eval behavior: `Agent must verify answer before submitting.`

- policy action: `require_operator: reflection` plus `block_next_action_until: revised_plan_exists`
- eval behavior: `Agent must break tool loop and propose alternative approach.`

Those are not raw-string matches, but they are clearly related harness interventions. Raw replay treated them as mismatches, so replay was measuring formatting agreement rather than semantic agreement.

## Canonical Action Ontology

This pass adds a canonical harness action ontology at `configs/settlement_datasets/harness_action_ontology.yaml`.

The ontology defines canonical action ids, aliases, compatible policy-action structures, compatible eval-behavior phrases, and action families.

Current canonical actions include:

- `require_reflection`
- `require_settlement_evidence`
- `reset_plan`
- `require_constraint_match`
- `require_intermediate_representation`
- `search_or_inspect_context`
- `inspect_api_schema`
- `require_failure_analysis`
- `recognize_reusable_pattern`

Families let replay recognize partial semantic agreement when two actions are different but belong to the same intervention family, such as `require_reflection` and `reset_plan` both falling under adaptive recovery.

## Normalization

`scripts/settlement_datasets/action_ontology.py` now normalizes both sides of replay:

- policy actions are flattened from structured YAML action records into ontology candidates
- eval expected behaviors are normalized from natural-language phrases into the same ontology

Each normalization returns:

- raw input
- canonical action id or `null`
- family
- confidence
- matched evidence tokens
- unmatched tokens

Unknowns remain explicit. The normalization layer does not silently force a match when ontology evidence is weak.

## Semantic Replay

`scripts/settlement_datasets/replay_policy_evals.py` still uses the existing policy-to-eval context filter, but it no longer scores replay by raw string comparison alone.

For each replay item it now records:

- `policy_raw_action`
- `eval_raw_expected_behavior`
- `policy_canonical_action`
- `eval_canonical_action`
- `semantic_match`
- `match_confidence`
- `match_evidence`
- `mismatch_reason`

Replay categories are now:

- `exact_semantic_match`
- `partial_semantic_match`
- `mismatch`
- `unknown_policy_action`
- `unknown_eval_behavior`
- `insufficient_evidence`

Scoring:

- exact semantic match = `1.0`
- partial semantic match = `0.5`
- mismatch = `0.0`
- unknown and insufficient-evidence cases are surfaced explicitly and excluded from semantic-rate aggregates

## How Unknowns Are Handled

Unknowns are calibration signals, not noise to hide.

- `unknown_policy_action` means the policy action could not be mapped into the ontology
- `unknown_eval_behavior` means the eval phrase could not be mapped into the ontology
- `insufficient_evidence` means the eval record did not provide enough expected-behavior text to score semantically

These cases remain visible in replay summaries so ontology gaps can be refined later without pretending they are resolved.

## Policy Status Recommendations

`scripts/settlement_datasets/update_policy_status.py` now includes semantic replay metrics in `policies/review/policy_status_recommendations.yaml` as supporting evidence.

Semantic replay does not promote a policy on its own.

Shadow helpful/harmful evidence still controls activation posture. Semantic replay only improves the interpretation layer by distinguishing ontology mismatch from actual policy mismatch.

## Why Semantic Replay Does Not Equal Live Settlement

Semantic replay is instrument calibration.

It answers a narrower question:

- does the replay system understand that the policy action and the eval behavior refer to the same harness intervention?

It does not answer the live settlement question:

- would activating this policy in the live harness improve outcomes without unacceptable payment or false positives?

That still requires shadow evidence first, and live activation experiments later.
