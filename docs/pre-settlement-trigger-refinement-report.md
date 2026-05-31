# Pre-Settlement Trigger Refinement Report

## Scope

This pass refined only two target policy families:

- `require_reflection_after_repeated_errors`
- `require_explicit_settlement_for_failure`

No policy was activated. No thresholds were lowered. No new datasets or adapters were introduced. No metabolization candidate was promoted.

All refinement artifacts for this pass live under `data/settlement_datasets/pre_settlement_trigger_refinement_run/`.

## Method

The refinement run reused the expanded evidence surface from `data/settlement_datasets/evidence_accumulation_run/settlements/`.

The historical late-trigger variants were preserved as `status: refine` so their prior evidence remains visible. Two new proposed variants were added:

- `require_reflection_before_continuing_after_second_unresolved_error`
- `require_failure_evidence_before_stopping_on_test_failure`

The offline evaluator was tightened so the refined variants operate on pre-settlement evidence instead of end-state labels:

- repeated-error refinement now counts only tool or environment feedback as spendable error evidence
- duplicate error text, revised strategy, low-cost inspection, and closure-like endings suppress the reflection trigger
- failure-evidence refinement now recognizes repeated failing test outputs in code traces and can fire before final settlement if the run is still open

The expanded run loaded `336` records, of which `332` met the existing `--min-confidence 0.65` filter. The four tracked target policies therefore produced `1328` shadow result rows.

## Results

### Reflection family

Historical late variant:

- `require_reflection_after_repeated_errors` still fired `2` times
- both fires remained `final_turn`
- both remained `uncertain`
- recovery opportunity stayed `0`

Refined pre-settlement variant:

- `require_reflection_before_continuing_after_second_unresolved_error` fired `0` times
- harmful false positives on the successful SWE traces were eliminated
- current recommendation is `needs_more_evidence`

Interpretation:

- the refinement did improve precision by refusing assistant-analysis mentions and by suppressing revised-plan or low-cost-inspection traces
- the expanded evidence surface does not yet contain a clean example of second unresolved environment feedback followed by same-path continuation with recovery still open
- this family remains inactive; the late marker is still a postmortem label, and the pre-settlement variant is still under-evidenced

### Failure-evidence family

Historical late variant:

- `require_explicit_settlement_for_failure` fired `3` times
- `2` were likely helpful and `1` remained uncertain
- all `3` fires remained `after_failure_already_settled`
- recovery opportunity stayed `0`

Refined pre-settlement variant:

- `require_failure_evidence_before_stopping_on_test_failure` fired `1` time
- the fire was `likely_helpful`
- the fire occurred on `swe-failed-004` at the second repeated failed test (`repeated_failure_turn=9`)
- timing moved to `late` rather than `after_failure_already_settled`
- recovery opportunity improved from `0` to `1`
- current recommendation is `keep_proposed`

Interpretation:

- this refinement achieved the intended directional change: a known useful failure-analysis signal moved from postmortem labeling into a still-open intervention window
- evidence remains narrow and code-specific, so activation is still unjustified

## Decision

The late historical variants stay preserved for comparison only:

- `require_reflection_after_repeated_errors`: keep as `refine`
- `require_explicit_settlement_for_failure`: keep as `refine`

The refined variants stay proposed but inactive:

- `require_reflection_before_continuing_after_second_unresolved_error`: `needs_more_evidence`
- `require_failure_evidence_before_stopping_on_test_failure`: `keep_proposed`

No activation recommendation is justified by this pass.

## Artifact Summary

Run-scoped outputs written by this pass:

- `data/settlement_datasets/pre_settlement_trigger_refinement_run/policies.yaml`
- `data/settlement_datasets/pre_settlement_trigger_refinement_run/policy_shadow_results.jsonl`
- `data/settlement_datasets/pre_settlement_trigger_refinement_run/policy_promotion_scores.jsonl`
- `data/settlement_datasets/pre_settlement_trigger_refinement_run/policy_shadow_summary.csv`
- `data/settlement_datasets/pre_settlement_trigger_refinement_run/eval_replay_results.jsonl`
- `data/settlement_datasets/pre_settlement_trigger_refinement_run/eval_replay_summary.csv`
- `data/settlement_datasets/pre_settlement_trigger_refinement_run/policy_status_recommendations.yaml`
- `data/settlement_datasets/pre_settlement_trigger_refinement_run/evidence_packs/`

## Outcome

The central claim from the helpfulness adjudication still holds: a policy that fires too late is not a harness intervention.

This pass converted one target family into an actual pre-settlement signal with recovery opportunity, and converted the other into a cleaner but still under-evidenced candidate. That is enough to preserve the direction of refinement, but not enough to pay for activation.

## Workflow Follow-Through

This refinement pass originally required manual module calls across multiple top-level settlement-dataset scripts.

The repository now includes a run-scoped evidence workflow wrapper at `scripts/settlement_datasets/run_evidence_pipeline.py` plus shared run-scoped CLI flags across the settlement-dataset surfaces. Future refinements of these same target policies can therefore reuse a single run directory, record targeted query intent in the run manifest, and rerun shadow evaluation, replay, adjudication, and metabolization review without rebuilding the path surface by hand.
