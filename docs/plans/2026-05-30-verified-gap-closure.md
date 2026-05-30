# Verified Gap Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the real remaining gaps in the Godspeed Agent Harness by first separating stale gap claims from verified gaps, then finishing the documentation, workflow, policy, and storage surfaces that still fail settlement.

**Architecture:** Keep the current local-first runtime and JSONL ledgers as the truth surface, then extend only the thin slices that still do not satisfy the doctrine in `tmp/cogos.md`: complete operator-visible reference docs, durable repetition and metabolization workflow support, richer absorption and positive disintegration review artifacts, and a gated storage evolution path for ML-era memory retrieval. Treat outcome completion as substrate creation, not as the finish line.

**Tech Stack:** Python 3.11+, `uv`, `pytest`, local JSONL ledgers as the current source of truth, optional SQLite as the first database step if query pressure justifies it, optional SurrealDB only if graph or multi-actor needs outgrow SQLite, and RuVector for local vector retrieval once predictive or memory-retrieval workflows genuinely need embeddings.

---

## Outcome Constraints From `tmp/cogos.md`

Every implementation task below must improve one or more of these operational outcomes:

- Expand the horizon by making the next affordable affordance more legible or more reachable.
- Improve payment and settlement accounting so consequence, not intent, remains the truth surface.
- Convert repeated settled actions into substrate rather than leaving them as narrative claims.
- Support positive disintegration by separating what should dissolve from what should be metabolized.
- Preserve self-critique and revision so doctrine can be corrected when it fails settlement.

Work that does not change those outcomes is not part of this plan.

## Verified Gap Status

The `Current Gap Summary` in [docs/understanding/2026-05-29-cognitive-operating-systems.md](/home/sprime01/projects/godspeed_agent/docs/understanding/2026-05-29-cognitive-operating-systems.md) is now partly stale. Verify that before implementing anything else.

| Legacy gap summary item | Verified status | Evidence surface | Planning consequence |
| --- | --- | --- | --- |
| No orchestration service owns the full navigation loop | Mostly resolved | `godspeed_nav/runtime.py`, CLI workflow commands, validation workflow | Do not rebuild runtime orchestration. Extend only where repetition/metabolization and self-critique are still thin. |
| Desired direction, horizon, affordance, payment, settlement, repetition, and metabolization are not connected as durable workflows | Partially still a gap | Direction, horizon, payment, settlement, and trajectory are connected; repetition and metabolization are still mostly review-time, not runtime-owned | Add durable repetition and metabolization workflow support. |
| Storage is append/read only and lacks atomic temp-file handling, indexes, migrations, backups, and typed envelope metadata | Mostly resolved for current scale; future gap for richer retrieval | `godspeed_nav/storage.py` now has event envelopes, checksums, indexes, backup export, and migration status | Keep JSONL as truth. Plan storage evolution only when real query or ML pressure appears. |
| CLI commands do not yet create or review a complete developmental session | Partially still a gap | Workflow commands exist, but operator-facing reference docs and a guided end-to-end session surface are missing | Add reference docs and one guided workflow example before inventing more CLI. |
| Hooks write partial data but do not reconcile ledgers into horizon state | Partially still a gap | Hooks now record payment, settlement, trajectory, and reports, but prompt hypothesis, horizon review, repetition, and self-critique are not yet stitched into one explainable session flow | Tighten hook-to-runtime reconciliation instead of replacing hooks. |
| Positive disintegration and absorption are deterministic stubs without policy-rich review artifacts | Still a gap | `godspeed_nav/absorption.py`, `godspeed_nav/disintegration.py`, and `godspeed_nav/policies.py` are minimal | Deepen review artifacts, policy explanations, and validation around those surfaces. |
| Enterprise docs, release checks, and operational runbooks are still minimal | Runbooks and release gates are mostly resolved; operator references are still missing | `docs/runbooks/*`, `release-readiness.md`, docs search | Build the missing reference layer instead of duplicating runbooks. |

## Working Rules For Execution

- Commit often. Default to one commit per completed milestone or per tight logical slice.
- Update [CURRENT_STATE.md](/home/sprime01/projects/godspeed_agent/CURRENT_STATE.md) after every meaningful milestone.
- Write or tighten tests before changing behavior.
- Validate each slice with the smallest focused check first, then rerun broader validation when the slice settles.
- Do not add a database merely because one is available. Add one only when the current JSONL truth surface fails settlement for retrieval, indexing, or ML feature support.

## Database Decision Rule

The current repository does not yet require a database to close the verified gaps. If a database becomes necessary during later milestones, use this order:

1. **SQLite first** for local-first structured query, deterministic migration, and simple deployment.
2. **SQLite + RuVector** once predictive extensions or developmental memory retrieval need local vector similarity.
3. **SurrealDB only by explicit justification** if cross-ledger graph traversal, live multi-actor coordination, or document-graph semantics clearly exceed SQLite.

Any database adoption must preserve export back to human-inspectable local records and must not replace payment and settlement ledgers as the truth surface.

## Task 1: Correct The Source Of Truth About Remaining Gaps

Files:

- Modify: `docs/understanding/2026-05-29-cognitive-operating-systems.md`
- Modify: `CURRENT_STATE.md`
- Test: `tests/test_docs_alignment.py`

Step 1.

Write the failing doc-alignment assertions.

- Extend `tests/test_docs_alignment.py` so the understanding document can no longer claim that orchestration, storage durability, and runbooks are entirely missing.
- Assert that the document distinguishes resolved, partial, and open gaps.

Step 2.

Run test to verify it fails.

Run: `uv run pytest tests/test_docs_alignment.py -q`

Expected: FAIL because the old gap summary is still overstated.

Step 3.

Update the understanding document.

- Replace the stale `Current Gap Summary` with a verified status summary.
- Keep the open gaps focused on reference docs, runtime-owned repetition/metabolization, hook reconciliation depth, and absorption/disintegration review depth.

Step 4.

Run test to verify it passes.

Run: `uv run pytest tests/test_docs_alignment.py -q`

Expected: PASS.

Step 5.

Commit.

```bash
git add docs/understanding/2026-05-29-cognitive-operating-systems.md tests/test_docs_alignment.py CURRENT_STATE.md
git commit -m "docs: verify remaining gap summary"
```

## Task 2: Normalize And Populate Operator Reference Docs

Files:

- Modify or rename: the existing `docs` reference directory that currently has a trailing-space name
- Create: `docs/references/ledger-reference.md`
- Create: `docs/references/schema-index.md`
- Create: `docs/references/cli-reference.md`
- Create: `docs/references/policy-reference.md`
- Create: `docs/references/report-interpretation.md`
- Create: `docs/references/runtime-workflow-example.md`
- Modify: `README.md`
- Modify: `docs/understanding/2026-05-29-cognitive-operating-systems.md`
- Test: `tests/test_docs_alignment.py`

Step 1.

Write failing documentation coverage tests.

- Extend `tests/test_docs_alignment.py` to assert that the operator reference documents exist and mention the controlling surfaces they explain.
- Add one assertion that the oddly named reference directory is normalized or intentionally handled.

Step 2.

Run test to verify it fails.

Run: `uv run pytest tests/test_docs_alignment.py -q`

Expected: FAIL on missing reference docs.

Step 3.

Add the reference docs.

- Normalize the empty reference directory into a clean `docs/references/` path.
- Write each reference doc against the actual controlling code, not aspirational architecture.
- Include at least one concrete command example in the CLI reference and one concrete interpretation example in the report guide.

Step 4.

Link the new docs from top-level entry points.

- Update `README.md` and the understanding document so operators can discover the reference layer.

Step 5.

Run test to verify it passes.

Run: `uv run pytest tests/test_docs_alignment.py -q`

Expected: PASS.

Step 6.

Commit.

```bash
git add docs/references README.md docs/understanding/2026-05-29-cognitive-operating-systems.md tests/test_docs_alignment.py CURRENT_STATE.md
git commit -m "docs: add operator reference layer"
```

## Task 3: Make Repetition And Metabolization Runtime-Owned

Files:

- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/metabolization.py`
- Modify: `godspeed_nav/reports.py`
- Modify: `godspeed_nav/cli.py`
- Modify: `hooks/post_tool_use.py`
- Modify: `hooks/stop.py`
- Test: `tests/test_runtime_workflow.py`
- Test: `tests/test_reports.py`
- Test: `tests/test_cli_hooks_mcp.py`

Step 1.

Write the failing workflow tests.

- Add a test proving that repeated successful settlements for the same affordance or capability accumulate reusable repetition evidence in storage.
- Add a report assertion that runtime-owned metabolization candidates reflect ledger history rather than only manually supplied CLI input.

Step 2.

Run the focused tests to verify failure.

Run: `uv run pytest tests/test_runtime_workflow.py tests/test_reports.py tests/test_cli_hooks_mcp.py -q`

Expected: FAIL because runtime-led metabolization evidence does not yet exist.

Step 3.

Implement the minimal durable workflow.

- Extend `NavigationRuntime.record_settlement` so repeated settlements can update capability or repetition records.
- Reuse `compute_metabolization` rather than creating a second metabolization rule set.
- Expose the result in reports and hook outputs.

Step 4.

Rerun the same focused tests.

Run: `uv run pytest tests/test_runtime_workflow.py tests/test_reports.py tests/test_cli_hooks_mcp.py -q`

Expected: PASS.

Step 5.

Commit.

```bash
git add godspeed_nav/runtime.py godspeed_nav/metabolization.py godspeed_nav/reports.py godspeed_nav/cli.py hooks/post_tool_use.py hooks/stop.py tests/test_runtime_workflow.py tests/test_reports.py tests/test_cli_hooks_mcp.py CURRENT_STATE.md
git commit -m "feat: persist repetition and metabolization evidence"
```

## Task 4: Tighten Hook-To-Runtime Session Reconciliation

Files:

- Modify: `hooks/user_prompt_submit.py`
- Modify: `hooks/pre_tool_use.py`
- Modify: `hooks/post_tool_use.py`
- Modify: `hooks/stop.py`
- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/reports.py`
- Test: `tests/test_cli_hooks_mcp.py`

Step 1.

Write failing hook workflow tests.

- Add a test for one explainable session from prompt hypothesis through payment review, settlement, trajectory, and stop report.
- Assert that hook outputs identify the active desired direction or session context instead of writing isolated events.

Step 2.

Run test to verify it fails.

Run: `uv run pytest tests/test_cli_hooks_mcp.py -q`

Expected: FAIL because hook events are not yet stitched into one operator-visible flow.

Step 3.

Implement minimal session reconciliation.

- Record a lightweight session or direction thread key.
- Ensure hook outputs and report entries can be traced back to the same desired direction.
- Do not build a new orchestration framework; strengthen the current runtime and ledger surfaces.

Step 4.

Run test to verify it passes.

Run: `uv run pytest tests/test_cli_hooks_mcp.py -q`

Expected: PASS.

Step 5.

Commit.

```bash
git add hooks/user_prompt_submit.py hooks/pre_tool_use.py hooks/post_tool_use.py hooks/stop.py godspeed_nav/runtime.py godspeed_nav/reports.py tests/test_cli_hooks_mcp.py CURRENT_STATE.md
git commit -m "feat: reconcile hook events into session flow"
```

## Task 5: Deepen Absorption Review Into A Policy-Rich Artifact

Files:

- Modify: `godspeed_nav/absorption.py`
- Modify: `godspeed_nav/policies.py`
- Modify: `docs/runbooks/configuration.md`
- Modify: `agents/absorber.md`
- Test: `tests/test_computation.py`
- Test: `tests/test_policy_gates.py`
- Test: `tests/test_docs_alignment.py`

Step 1.

Write failing review tests.

- Add tests that require absorbability review to distinguish at least: missing pathway, incompatible license, missing settlement plan, review required, and ready-to-absorb.
- Assert that policy decisions are returned in an explainable artifact, not just a status string.

Step 2.

Run focused tests to verify failure.

Run: `uv run pytest tests/test_computation.py tests/test_policy_gates.py tests/test_docs_alignment.py -q`

Expected: FAIL on the missing review depth.

Step 3.

Implement minimal richer review.

- Keep local-first deterministic review.
- Return a structured artifact containing absorbability status, policy gate result, blocking reasons, payment estimate, settlement plan, and required human review steps.

Step 4.

Rerun the focused tests.

Run: `uv run pytest tests/test_computation.py tests/test_policy_gates.py tests/test_docs_alignment.py -q`

Expected: PASS.

Step 5.

Commit.

```bash
git add godspeed_nav/absorption.py godspeed_nav/policies.py docs/runbooks/configuration.md agents/absorber.md tests/test_computation.py tests/test_policy_gates.py tests/test_docs_alignment.py CURRENT_STATE.md
git commit -m "feat: enrich absorption review artifacts"
```

## Task 6: Deepen Positive Disintegration Review And Safeguards

Files:

- Modify: `godspeed_nav/disintegration.py`
- Modify: `godspeed_nav/policies.py`
- Modify: `agents/disintegrator.md`
- Modify: `docs/runbooks/configuration.md`
- Test: `tests/test_computation.py`
- Test: `tests/test_policy_gates.py`
- Test: `tests/test_docs_alignment.py`

Step 1.

Write failing review tests.

- Add tests that require disintegration review to produce explicit dissolution candidates, salvageable elements, blocked high-risk items, and human-review requirements.
- Assert that high-risk destructive candidates cannot appear as plain low-friction recommendations.

Step 2.

Run focused tests to verify failure.

Run: `uv run pytest tests/test_computation.py tests/test_policy_gates.py tests/test_docs_alignment.py -q`

Expected: FAIL on missing safeguard depth.

Step 3.

Implement minimal richer review.

- Separate dissolution from salvage recommendations.
- Attach policy reasoning and review requirements to the result.
- Preserve deterministic behavior and avoid speculative automation.

Step 4.

Rerun the focused tests.

Run: `uv run pytest tests/test_computation.py tests/test_policy_gates.py tests/test_docs_alignment.py -q`

Expected: PASS.

Step 5.

Commit.

```bash
git add godspeed_nav/disintegration.py godspeed_nav/policies.py agents/disintegrator.md docs/runbooks/configuration.md tests/test_computation.py tests/test_policy_gates.py tests/test_docs_alignment.py CURRENT_STATE.md
git commit -m "feat: harden positive disintegration review"
```

## Task 7: Add A Gated Storage Evolution Path For ML-Era Memory

Files:

- Modify: `HARNESS.md`
- Modify: `godspeed_nav/config.py`
- Modify: `godspeed_nav/ml.py`
- Create: `docs/plans/2026-05-30-storage-evolution-decision-record.md`
- Modify: `docs/runbooks/configuration.md`
- Test: `tests/test_config.py`
- Test: `tests/test_validation.py`

Step 1.

Write failing config and validation tests.

- Add tests for explicit storage-mode configuration that still keeps JSONL as the default truth surface.
- Add tests for a future database mode flag that remains disabled until enabled by config and justified by settlement history.

Step 2.

Run focused tests to verify failure.

Run: `uv run pytest tests/test_config.py tests/test_validation.py -q`

Expected: FAIL because storage evolution policy is not yet explicit.

Step 3.

Implement the minimal decision surface.

- Add configuration fields that define when a richer store is allowed.
- Document SQLite as the default next step and RuVector as the vector layer once ML retrieval is justified.
- Mention SurrealDB only as an explicit alternative for graph-heavy or multi-actor needs.
- Do not actually migrate persistence yet unless a separate change proves current storage has failed settlement.

Step 4.

Rerun the focused tests.

Run: `uv run pytest tests/test_config.py tests/test_validation.py -q`

Expected: PASS.

Step 5.

Commit.

```bash
git add HARNESS.md godspeed_nav/config.py godspeed_nav/ml.py docs/plans/2026-05-30-storage-evolution-decision-record.md docs/runbooks/configuration.md tests/test_config.py tests/test_validation.py CURRENT_STATE.md
git commit -m "docs: gate future storage evolution for ml"
```

## Task 8: Run Final Validation And Release-Readiness Checks

Files:

- Modify: `CURRENT_STATE.md`
- Modify: `docs/runbooks/release-readiness.md` only if needed
- Test: `tests/test_docs_alignment.py`
- Test: `tests/test_cli_hooks_mcp.py`
- Test: `tests/test_computation.py`
- Test: `tests/test_reports.py`
- Test: `tests/test_policy_gates.py`
- Test: `tests/test_config.py`
- Test: `tests/test_validation.py`
- Test: `tests/test_runbooks.py`

Step 1.

Run the focused suite for changed surfaces.

Run:

```bash
uv run pytest \
  tests/test_docs_alignment.py \
  tests/test_cli_hooks_mcp.py \
  tests/test_computation.py \
  tests/test_reports.py \
  tests/test_policy_gates.py \
  tests/test_config.py \
  tests/test_validation.py \
  tests/test_runbooks.py -q
```

Expected: PASS.

Step 2.

Run end-to-end validation.

Run:

```bash
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/final-gap-closure-validation
```

Expected: JSON output with `"status": "pass"`.

Step 3.

Update release readiness if anything changed.

- If release gates or required docs changed, update the runbook in the same slice.

Step 4.

Record the final milestone.

- Add the final evidence to `CURRENT_STATE.md`.

Step 5.

Commit.

```bash
git add CURRENT_STATE.md docs/runbooks/release-readiness.md
git commit -m "chore: record verified gap-closure validation"
```

## Definition Of Done

This plan is complete only when all of the following are true:

- The understanding document no longer overstates already-closed gaps.
- Operators can find and use a full reference layer without reading the code first.
- Repetition and metabolization evidence are durably connected to runtime workflow.
- Hook events can be traced through one explainable session flow.
- Absorption and positive disintegration return policy-rich review artifacts rather than thin deterministic stubs.
- Any storage evolution beyond JSONL is explicitly gated, justified, and local-first.
- `CURRENT_STATE.md` was updated at every meaningful milestone.
- Focused tests and `godspeed-nav validate` both pass.
