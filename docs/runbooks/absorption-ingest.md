# Absorption Ingest Runbook

## Purpose

Use this runbook when a project wants to absorb a capability from another project, repository, library, agent, or skill. The ingest area is a local staging surface. Material placed there is not part of the receiving project's substrate until it survives review, payment, settlement, and repetition.

## Recommended Layout

Each project should keep its own absorption candidates inside the configured ingest root:

```text
my-project/
  src/
  tests/
  HARNESS.md
  ingest/
    absorption/
      <candidate-name>/
        source/
        absorption.md
        license.md
        settlement-plan.md
  .godspeed-harness/
```

Use `ingest/absorption/` rather than a root-level folder such as `FOR_ABSORPTION`. The default policy already names `ingest/` as the governed surface:

```yaml
absorption:
  enabled: true
  ingest_root: ingest/
  require_license_check: true
  require_pathway: true
  require_settlement_plan: true
```

The ingest root must remain inside the workspace. Keep harness ledgers under `.godspeed-harness/`; do not store candidate source there.

## Candidate Contents

Each candidate should describe the specific capability delta instead of asking the project to absorb a whole repository.

`source/` may contain a clone, copied files, extracted examples, or notes that point to the external material. Keep large or licensed upstream projects out of the receiving codebase until the absorption review says the pathway is spendable.

`absorption.md` should state:

- Desired direction served by the candidate.
- Capability wanted from the external source.
- Current local gap.
- Proposed pathway into this project.
- Expected horizon expansion.
- Known payment: integration work, maintenance, migration, dependencies, and risk.

`license.md` should state:

- Upstream license.
- Attribution or redistribution obligations.
- Compatibility concerns.
- Whether human review is required before copying code.

`settlement-plan.md` should state:

- The smallest local experiment that can prove the capability.
- Before and after state to compare.
- Evidence required for settlement.
- Focused validation command.
- Repetition threshold before the capability can be treated as substrate.

## Workflow

1. Start with the receiving project's desired direction.
2. Add the external material under `ingest/absorption/<candidate-name>/`.
3. Classify the material as `potential` until there is a real pathway.
4. Write the capability delta, license summary, payment estimate, and settlement plan.
5. Review absorbability before copying code into `src/`, `tests/`, `skills/`, or agent surfaces.
6. Run the smallest safe experiment, preferably in a branch or worktree.
7. Record settlement only from local consequence, not from the external project's claims.
8. Move proven code or docs into the normal project surface only after the settlement plan passes.
9. Schedule repetition when the capability works once but has not yet metabolized.

Do not absorb broad external structure when the desired direction needs only a small fragment. The pathway itself is the affordance.

## Skill Creation

Do not create a skill merely because a candidate repo was dropped into `ingest/absorption/`.

Create a skill only when the absorbed capability is reusable operator or agent guidance. Normal code should become normal project code. A workflow should become a skill only after repeated settlement shows that the project benefits from calling the same guidance again.

A skill candidate is still not metabolized when it is written. It becomes metabolized only after repeated successful use across time, contexts, and lower attention burden.

## Status Language

Use these classifications during review:

- `potential`: the external material exists, but the receiving project has no spendable pathway yet.
- `possibility`: a pathway appears plausible, but payment, license, policy, or settlement remains unresolved.
- `absorbable`: pathway, payment, license, policy, and settlement plan align.
- `settled`: the local experiment produced evidence in the receiving project.
- `metabolized`: repeated settlement shows the capability has become reliable substrate.

Avoid saying a capability has been absorbed because it was copied, cloned, summarized, or scaffolded.

## Validation

After changing absorption policy or adding a candidate that will affect project behavior, run the narrowest useful check:

```bash
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation
```

When the candidate changes code, run the receiving project's focused tests as the settlement evidence. When it changes doctrine, policy, skill behavior, or developmental memory semantics, update the corresponding docs and tests in the same slice.
