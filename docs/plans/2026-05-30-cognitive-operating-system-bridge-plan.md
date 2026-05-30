# Cognitive Operating System Bridge Plan

> **For Claude:** Execute this plan in small verified slices. Commit often. Update `CURRENT_STATE.md` after every meaningful milestone. Do not claim progress from code alone; verify and validate each slice against the outcome it affords.

**Goal:** Bridge the delta between the current Godspeed Agent Harness implementation and the target state defined in `docs/plans/specs/2026-05-30-cognitive-operating-system-spec.md` so the repository materially embodies the developmental runtime described in `tmp/cogos.md`.

**Architecture:** Preserve the current local-first harness as substrate rather than replacing it. Keep JSONL event ledgers, the existing runtime orchestration, CLI, hooks, MCP, reports, and validation as the foundation. Extend the repository by adding the missing cognitive-runtime layers: representational state, representational transition policy, affordance-path planning, environment and identity deltas, runtime-owned repetition scheduling, developmental memory, and self-critique. Predictive and simulation surfaces remain subordinate to deterministic payment, settlement, and policy gates.

**Tech Stack:** Python 3.11+, `uv`, `pytest`, local JSONL ledgers as the truth surface, existing CLI/hooks/MCP surfaces in `godspeed_nav/`, and SQLite-first storage evolution only if deterministic local retrieval pressure genuinely requires it. RuVector remains the preferred local vector path if memory retrieval later needs embeddings.

---

## Outcome Constraints From `tmp/cogos.md`

Every implementation slice in this plan MUST improve one or more of these outcomes:

- Expand the horizon by making the next affordable affordance more visible, more reachable, or more explainable.
- Improve payment and settlement accounting so consequence remains the truth surface.
- Convert repeated settled actions into explicit capability and substrate rather than narrative claims.
- Enforce representational path dependency so the runtime can distinguish lawful adjacent moves from unearned opposition jumps.
- Support positive disintegration by distinguishing what should dissolve, what should be preserved, and what should become body.
- Preserve self-critique so doctrine, policy, and runtime behavior can be revised when they fail settlement.
- Keep cognition local-first, inspectable, and testable.

Work that does not afford at least one of those outcomes is not part of this plan.

## Current State Summary

The repository already has strong substrate:

- Runtime-owned desired directions, horizon review, payment recording, settlement recording, and trajectory updates.
- Durable local storage with checksummed event envelopes, indexes, backup export, migration status, and storage-boundary enforcement.
- Workflow-grade CLI, hook, MCP, report, and validation surfaces.
- Runtime-owned metabolization evidence, session-context reconciliation, and richer absorption/disintegration review artifacts.
- Operator reference docs and enterprise-hardening surfaces.

The remaining gaps to the target spec are not foundation or packaging gaps. They are cognitive-runtime gaps:

- No first-class `RepresentationalState` or `RepresentationalTransition` model exists.
- No explicit opposition-jump blocking or adjacent-move selection policy exists.
- Horizon review still ranks candidates rather than constructing explicit affordance paths with transition sequences.
- Settlement records do not yet update environment state, identity delta, future constraints, or future affordances as first-class runtime objects.
- Repetition is inferred retrospectively, but not yet scheduled as runtime behavior under variation.
- Capability lifecycle is still narrower than the target `latent -> active -> repeated -> metabolized -> brittle -> retired` model.
- Developmental memory exists as ledgers, but not yet as a first-class lineage/query layer.
- Self-critique exists in docs and skills, but not as an executable runtime module with falsification surfaces.
- Validation checks enterprise readiness, but not full cognitive-operating-system conformance.

## Execution Rules

- Commit often. Default to one commit per completed milestone or tight logical slice.
- Update `CURRENT_STATE.md` after every meaningful milestone.
- Write failing tests first for behavioral changes.
- Validate each slice with the narrowest executable check that can falsify the intended outcome.
- After focused validation passes, rerun the smallest broader check needed to prove the slice still composes with the current system.
- For every milestone below, explicitly check whether the resulting change improved the outcome it was meant to afford. If it did not, revise the slice before proceeding.
- Do not add a database or hosted service merely because the target spec mentions richer memory. Keep JSONL as truth until query pressure or settlement history proves otherwise.

## Decision Rules

### Runtime Rule

Prefer extending the existing controlling surfaces in `godspeed_nav/runtime.py`, `godspeed_nav/storage.py`, `godspeed_nav/reports.py`, `godspeed_nav/cli.py`, `hooks/*`, and `mcp/cybernetic_nav_server/server.py` over creating parallel abstractions.

### Storage Rule

Use this order only if the current local truth surface fails settlement:

1. JSONL ledgers with better indexes and lineage views.
2. SQLite for local structured retrieval.
3. SQLite + RuVector for local similarity retrieval.
4. Any graph-first or multi-actor store only by explicit evidence that simpler local options fail.

### Validation Rule

Every milestone must answer two questions:

1. What new outcome did this slice make real?
2. What executable evidence shows the slice survived settlement?

## Milestone 1: Freeze The Delta As Executable Contract

**Purpose:** Turn the target spec into a verifiable bridge target rather than a prose-only ambition.

**Outcome Afforded:** Preserves self-critique and reduces doctrinal drift by making the missing cognitive-runtime surfaces explicit in tests and docs.

Files:

- Modify: `tests/test_docs_alignment.py`
- Modify: `tests/test_validation.py`
- Modify: `docs/understanding/2026-05-29-cognitive-operating-systems.md`
- Modify: `CURRENT_STATE.md`

Step 1.

Write failing assertions that the repository distinguishes between:

- current harness substrate
- target cognitive-runtime layers still missing
- doctrine-level invariants that must remain true during implementation

Step 2.

Add validation expectations for future cognitive-runtime surfaces without yet claiming they exist.

Step 3.

Update the understanding docs so the bridge from current implementation to target-state spec is explicit and operator-visible.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_docs_alignment.py tests/test_validation.py -q`

Expected: PASS with explicit target-state bridge coverage.

Step 5.

Commit.

```bash
git add docs/understanding/2026-05-29-cognitive-operating-systems.md tests/test_docs_alignment.py tests/test_validation.py CURRENT_STATE.md
git commit -m "docs: formalize cognitive runtime bridge"
```

## Milestone 2: Add Representational State As A First-Class Runtime Surface

**Purpose:** Implement the manifesto's missing representational-state engine.

**Outcome Afforded:** Expands the horizon by making the next affordable representational move explicit instead of leaving representation implicit.

Files:

- Modify: `godspeed_nav/schemas.py`
- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/storage.py`
- Modify: `godspeed_nav/cli.py`
- Modify: `godspeed_nav/reports.py`
- Modify: `tests/test_domain_storage.py`
- Modify: `tests/test_runtime_workflow.py`
- Modify: `tests/test_cli_hooks_mcp.py`

Step 1.

Write failing tests for:

- representational state creation and persistence
- representational state attached to a desired direction
- runtime snapshot and reports surfacing the latest representational state

Step 2.

Add first-class records for representational state with stable identifiers and ledger persistence.

Step 3.

Expose minimal public surfaces to inspect and persist representational state without yet adding the full transition engine.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_domain_storage.py tests/test_runtime_workflow.py tests/test_cli_hooks_mcp.py -q`

Expected: PASS with runtime-owned representational state now visible.

Step 5.

Commit.

```bash
git add godspeed_nav/schemas.py godspeed_nav/runtime.py godspeed_nav/storage.py godspeed_nav/cli.py godspeed_nav/reports.py tests/test_domain_storage.py tests/test_runtime_workflow.py tests/test_cli_hooks_mcp.py CURRENT_STATE.md
git commit -m "feat: add representational state runtime surface"
```

## Milestone 3: Implement Representational Transition Policy And Opposition-Jump Blocking

**Purpose:** Make path dependency and adjacent movement enforceable rather than advisory.

**Outcome Afforded:** Improves payment and settlement accounting by preventing unspendable representational jumps from being treated as lawful affordances.

Files:

- Modify: `godspeed_nav/metrics.py`
- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/policies.py`
- Modify: `godspeed_nav/cli.py`
- Modify: `mcp/cybernetic_nav_server/server.py`
- Modify: `tests/test_computation.py`
- Modify: `tests/test_runtime_workflow.py`
- Modify: `tests/test_cli_hooks_mcp.py`

Step 1.

Write failing tests for:

- distance-cost computation between representational states
- adjacent transition selection
- blocked opposition jumps unless a metabolized shortcut exists
- clear operator-visible error surfaces for blocked transitions

Step 2.

Implement representational transition records and policy checks in the runtime.

Step 3.

Expose deterministic CLI and MCP tools for reviewing transition affordability.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_computation.py tests/test_runtime_workflow.py tests/test_cli_hooks_mcp.py -q`

Expected: PASS with opposition-jump blocking and adjacent-move policy enforced.

Step 5.

Commit.

```bash
git add godspeed_nav/metrics.py godspeed_nav/runtime.py godspeed_nav/policies.py godspeed_nav/cli.py mcp/cybernetic_nav_server/server.py tests/test_computation.py tests/test_runtime_workflow.py tests/test_cli_hooks_mcp.py CURRENT_STATE.md
git commit -m "feat: enforce representational transition policy"
```

## Milestone 4: Replace Flat Horizon Candidates With Explicit Affordance Paths

**Purpose:** Stop collapsing destination visibility into path availability.

**Outcome Afforded:** Expands the horizon by turning candidate ideas into spendable, inspectable pathways.

Files:

- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/metrics.py`
- Modify: `godspeed_nav/schemas.py`
- Modify: `godspeed_nav/reports.py`
- Modify: `docs/references/runtime-workflow-example.md`
- Modify: `tests/test_runtime_workflow.py`
- Modify: `tests/test_reports.py`
- Modify: `tests/test_docs_alignment.py`

Step 1.

Write failing tests for affordance paths that include:

- required preconditions
- transition sequence
- expected settlement
- lifecycle status

Step 2.

Extend horizon review so it persists explicit affordance paths and ranks them by pathway quality rather than only by candidate score.

Step 3.

Update reports and docs to explain the difference between visible destination and spendable path.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_runtime_workflow.py tests/test_reports.py tests/test_docs_alignment.py -q`

Expected: PASS with explicit affordance-path records.

Step 5.

Commit.

```bash
git add godspeed_nav/runtime.py godspeed_nav/metrics.py godspeed_nav/schemas.py godspeed_nav/reports.py docs/references/runtime-workflow-example.md tests/test_runtime_workflow.py tests/test_reports.py tests/test_docs_alignment.py CURRENT_STATE.md
git commit -m "feat: persist affordance paths"
```

## Milestone 5: Expand Settlement Into Environment, Identity, And Future-State Accounting

**Purpose:** Make settlement a cognitive event, not only a scored before/after record.

**Outcome Afforded:** Improves consequence accounting so outcomes generate explicit environment change, identity change, and future path visibility.

Files:

- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/schemas.py`
- Modify: `godspeed_nav/reports.py`
- Modify: `hooks/post_tool_use.py`
- Modify: `hooks/stop.py`
- Modify: `tests/test_runtime_workflow.py`
- Modify: `tests/test_reports.py`
- Modify: `tests/test_cli_hooks_mcp.py`

Step 1.

Write failing tests for settlement records that carry:

- observed consequence
- unexpected consequence
- payment variance
- capability delta
- identity delta
- future constraints created
- future affordances created

Step 2.

Extend settlement recording and storage to persist these fields.

Step 3.

Expose these new fields in hook outputs and reports.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_runtime_workflow.py tests/test_reports.py tests/test_cli_hooks_mcp.py -q`

Expected: PASS with richer settlement accounting.

Step 5.

Commit.

```bash
git add godspeed_nav/runtime.py godspeed_nav/schemas.py godspeed_nav/reports.py hooks/post_tool_use.py hooks/stop.py tests/test_runtime_workflow.py tests/test_reports.py tests/test_cli_hooks_mcp.py CURRENT_STATE.md
git commit -m "feat: extend settlement into environment and identity accounting"
```

## Milestone 6: Make Repetition A Scheduled Runtime Primitive

**Purpose:** Move repetition from retrospective inference to active runtime planning.

**Outcome Afforded:** Converts repeated settled action into real capability formation rather than post hoc narrative.

Files:

- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/metabolization.py`
- Modify: `godspeed_nav/reports.py`
- Modify: `godspeed_nav/cli.py`
- Modify: `tests/test_runtime_workflow.py`
- Modify: `tests/test_reports.py`
- Modify: `tests/test_cli_hooks_mcp.py`

Step 1.

Write failing tests for:

- repetition scheduling after successful but non-metabolized settlement
- variation coverage tracking
- delayed retest under changed conditions
- critique escalation after repeated circular motion

Step 2.

Implement a local repetition scheduler and records that remain subordinate to settlement evidence.

Step 3.

Integrate the repetition scheduler into reports and runtime snapshots.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_runtime_workflow.py tests/test_reports.py tests/test_cli_hooks_mcp.py -q`

Expected: PASS with runtime-owned repetition planning.

Step 5.

Commit.

```bash
git add godspeed_nav/runtime.py godspeed_nav/metabolization.py godspeed_nav/reports.py godspeed_nav/cli.py tests/test_runtime_workflow.py tests/test_reports.py tests/test_cli_hooks_mcp.py CURRENT_STATE.md
git commit -m "feat: add repetition scheduler"
```

## Milestone 7: Expand Capability Lifecycle And Identity State

**Purpose:** Match the target lifecycle model and make identity computational rather than rhetorical.

**Outcome Afforded:** Makes capability and identity formation inspectable, reducing confusion between access, success once, and metabolized ability.

Files:

- Modify: `godspeed_nav/schemas.py`
- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/reports.py`
- Modify: `docs/references/report-interpretation.md`
- Modify: `tests/test_domain_storage.py`
- Modify: `tests/test_reports.py`
- Modify: `tests/test_docs_alignment.py`

Step 1.

Write failing tests for lifecycle states:

- `latent`
- `active`
- `repeated`
- `metabolized`
- `brittle`
- `retired`

Step 2.

Add identity-state records that aggregate active directions, capabilities, substrate, and lock-in risks.

Step 3.

Expose capability and identity movement in reports and docs.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_domain_storage.py tests/test_reports.py tests/test_docs_alignment.py -q`

Expected: PASS with richer capability lifecycle and identity state.

Step 5.

Commit.

```bash
git add godspeed_nav/schemas.py godspeed_nav/runtime.py godspeed_nav/reports.py docs/references/report-interpretation.md tests/test_domain_storage.py tests/test_reports.py tests/test_docs_alignment.py CURRENT_STATE.md
git commit -m "feat: model capability lifecycle and identity state"
```

## Milestone 8: Build Developmental Memory As A First-Class Lineage Surface

**Purpose:** Make the local ledgers answer developmental-history questions directly.

**Outcome Afforded:** Preserves local, inspectable memory of how the system became what it is.

Files:

- Modify: `godspeed_nav/storage.py`
- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/reports.py`
- Modify: `mcp/cybernetic_nav_server/server.py`
- Modify: `docs/references/ledger-reference.md`
- Modify: `tests/test_enterprise_storage.py`
- Modify: `tests/test_validation.py`

Step 1.

Write failing tests for developmental-memory queries that answer:

- what path was paid for
- what failed to settle
- which capabilities became substrate
- which critique findings revised later behavior

Step 2.

Add lineage-oriented read surfaces without abandoning the existing ledger truth.

Step 3.

Expose lineage queries through MCP and reports.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_enterprise_storage.py tests/test_validation.py -q`

Expected: PASS with first-class developmental-memory views.

Step 5.

Commit.

```bash
git add godspeed_nav/storage.py godspeed_nav/runtime.py godspeed_nav/reports.py mcp/cybernetic_nav_server/server.py docs/references/ledger-reference.md tests/test_enterprise_storage.py tests/test_validation.py CURRENT_STATE.md
git commit -m "feat: add developmental memory lineage surfaces"
```

## Milestone 9: Add Runtime-Owned Self-Critique And Falsification Surfaces

**Purpose:** Make self-critique executable and evidence-backed.

**Outcome Afforded:** Preserves revision, detects blind spots, and prevents doctrine from calcifying into identity.

Files:

- Modify: `godspeed_nav/runtime.py`
- Modify: `godspeed_nav/reports.py`
- Modify: `godspeed_nav/validation.py`
- Modify: `hooks/stop.py`
- Modify: `agents/evaluator.md`
- Modify: `docs/references/policy-reference.md`
- Modify: `tests/test_reports.py`
- Modify: `tests/test_validation.py`
- Modify: `tests/test_docs_alignment.py`

Step 1.

Write failing tests for self-critique that detect at least:

- dead-end directions with settlement but no horizon expansion
- circular motion with insufficient radial growth
- doctrine drift between docs and runtime
- simulation being misread as real capability evidence

Step 2.

Add critique records and critique reporting.

Step 3.

Make validation fail when mandatory critique surfaces are absent or when doctrine drift becomes explicit.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_reports.py tests/test_validation.py tests/test_docs_alignment.py -q`

Expected: PASS with runtime-owned self-critique.

Step 5.

Commit.

```bash
git add godspeed_nav/runtime.py godspeed_nav/reports.py godspeed_nav/validation.py hooks/stop.py agents/evaluator.md docs/references/policy-reference.md tests/test_reports.py tests/test_validation.py tests/test_docs_alignment.py CURRENT_STATE.md
git commit -m "feat: add runtime self-critique surfaces"
```

## Milestone 10: Close Public-Surface Gaps In CLI, Hooks, MCP, And Validation

**Purpose:** Ensure the new cognitive-runtime behavior is real at the public control surfaces.

**Outcome Afforded:** Keeps cognition inspectable and prevents new behavior from existing only in internal modules.

Files:

- Modify: `godspeed_nav/cli.py`
- Modify: `hooks/user_prompt_submit.py`
- Modify: `hooks/pre_tool_use.py`
- Modify: `hooks/post_tool_use.py`
- Modify: `hooks/stop.py`
- Modify: `mcp/cybernetic_nav_server/server.py`
- Modify: `docs/references/cli-reference.md`
- Modify: `tests/test_cli_hooks_mcp.py`
- Modify: `tests/test_validation.py`

Step 1.

Write failing tests for public surfaces that can:

- inspect representational state and transition policy
- review explicit affordance paths
- surface repetition backlog and critique backlog
- show identity and environment deltas

Step 2.

Extend CLI, hooks, and MCP to expose the new runtime-owned cognition surfaces.

Step 3.

Update operator reference docs to match the new public contract.

Step 4.

Run focused validation.

Run: `uv run pytest tests/test_cli_hooks_mcp.py tests/test_validation.py -q`

Expected: PASS with public cognitive-runtime surfaces aligned.

Step 5.

Commit.

```bash
git add godspeed_nav/cli.py hooks/user_prompt_submit.py hooks/pre_tool_use.py hooks/post_tool_use.py hooks/stop.py mcp/cybernetic_nav_server/server.py docs/references/cli-reference.md tests/test_cli_hooks_mcp.py tests/test_validation.py CURRENT_STATE.md
git commit -m "feat: expose cognitive runtime through public surfaces"
```

## Milestone 11: Add Cognitive-OS Conformance Validation

**Purpose:** Replace informal confidence with executable conformance checks against the target spec.

**Outcome Afforded:** Preserves the truth surface by making target-state compliance falsifiable.

Files:

- Modify: `godspeed_nav/validation.py`
- Modify: `tests/test_validation.py`
- Modify: `docs/references/schema-index.md`
- Modify: `CURRENT_STATE.md`

Step 1.

Write failing validation tests for required target-state surfaces:

- representational state
- representational transition policy
- affordance paths
- environment and identity settlement deltas
- repetition scheduler
- developmental memory lineage
- self-critique findings

Step 2.

Extend validation to check those surfaces directly.

Step 3.

Run focused validation.

Run: `uv run pytest tests/test_validation.py -q`

Expected: PASS with cognitive-operating-system conformance checks.

Step 4.

Commit.

```bash
git add godspeed_nav/validation.py tests/test_validation.py docs/references/schema-index.md CURRENT_STATE.md
git commit -m "feat: validate cognitive operating system conformance"
```

## Milestone 12: Final Settlement Audit Against `tmp/cogos.md`

**Purpose:** Prove the repository now embodies the manifesto rather than only approximating it.

**Outcome Afforded:** Integrates all prior work into a stable developmental runtime and confirms each promised outcome survived settlement.

Files:

- Modify: `docs/understanding/2026-05-29-cognitive-operating-systems.md`
- Modify: `README.md`
- Modify: `CURRENT_STATE.md`

Step 1.

Run a final doctrine-to-runtime audit against:

- `tmp/cogos.md`
- `docs/plans/specs/2026-05-30-cognitive-operating-system-spec.md`
- the public runtime surfaces

Step 2.

Update understanding and top-level docs so the embodied cognitive operating system is discoverable and explained.

Step 3.

Run focused and broad validation.

Run:

```bash
uv run pytest tests/test_docs_alignment.py tests/test_validation.py tests/test_runtime_workflow.py tests/test_reports.py tests/test_cli_hooks_mcp.py tests/test_computation.py tests/test_domain_storage.py tests/test_enterprise_storage.py -q
uv run pytest -q
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/cognitive-os-validation
```

Expected:

- Focused suite passes.
- Repo-wide suite passes.
- `validate` returns `"status": "pass"`.

Step 4.

Commit.

```bash
git add docs/understanding/2026-05-29-cognitive-operating-systems.md README.md CURRENT_STATE.md
git commit -m "docs: record cognitive operating system conformance"
```

## Definition Of Done

This bridge plan is complete only when all of the following are true:

1. The runtime owns representational state, transition policy, explicit affordance paths,
   repetition scheduling, developmental memory, and self-critique as real code paths.
2. Settlement records include environment, identity, and future-path consequences rather than only
   score and status.
3. Capability lifecycle and identity state are explicit and operator-visible.
4. CLI, hooks, MCP, reports, and validation expose the cognitive-runtime state rather than hiding
   it in private modules.
5. Validation can falsify claims of cognitive-operating-system conformance.
6. `CURRENT_STATE.md` records each milestone that survived focused settlement.
7. The resulting repository materially embodies the outcomes in `tmp/cogos.md`, not merely the
   vocabulary.
8. The project is suitable for enterprise deployment as a cognitive operating system rather than only a developmental harness`
