# Godspeed Agent Harness

Godspeed Agent Harness is a local-first Claude Code plugin and Python runtime for horizon-centric cybernetic navigation. It turns desired directions into horizon checks, affordance review, payment estimates, settlement events, developmental memory, and runtime validation.

The harness is developmental rather than arrival-centric. In this project, outcome completion is not terminal: a settled outcome becomes substrate and should expose new affordances.

The doctrine in `tmp/cogos.md` is not outcome-dismissive. Outcomes matter because they are settlement events: they reveal consequence, produce error-correction data, and become developmental memory for the next loop.

The current repository implements the local-first developmental harness and the core cognitive-runtime layers described in `tmp/cogos.md`: explicit representational-state handling, path dependency, environment and identity deltas, repetition scheduling, developmental memory lineage, and runtime-owned self-critique.

## What It Does

- Converts desired-direction language into an explicit navigation loop.
- Distinguishes potentials, possibilities, affordances, capabilities, and substrate.
- Treats affordances as spendable paths, not merely visible destinations.
- Records payment, settlement, trajectory, and developmental memory in local ledgers.
- Exposes runtime and review workflows through a Python CLI, hooks, MCP servers, and skill packages.
- Keeps the system open to self-critique so doctrine can be revised when it fails settlement.

## Computational Model Layer

The planned computational core in `docs/plans/2026-06-03-cognitive-model-computational-core.md` turns the mathematical model in `tmp/math.md` into executable decision support. Once implemented, the harness will have a computational model layer for representational burden, payment fit, hard gates, spendability, risk, debt, controller ranking, settlement calibration records, and calibration datasets.

That makes the model computational, not automatically authoritative. Deterministic gates run first. Learned prediction through the built-in scikit-learn provider remains dormant until configured settlement-history thresholds are met, and even then it stays advisory. Settlement evidence determines whether calibrated weights or learned predictions deserve more influence.

## Doctrine Alignment

The manifesto in `tmp/cogos.md` sharpens several rules that govern this repository:

- Horizon expansion is the primary metric, but resources, affordance inventory, affordance utilization, and horizon expansion are not the same thing.
- Representational movement matters. General/specific and abstract/concrete are not casual labels; they describe how the observer is currently representing the problem and what adjacent move is affordable next.
- Opposites are usually not directly spendable. The path between states matters more than the declared destination.
- Outcome, payment, settlement, repetition, and metabolization are coupled. Explanation, access, or simulation are not proof of capability.
- Positive disintegration requires both dissolution and salvage. Destruction alone is not development.
- Self-critique is mandatory. Doctrine, policy, and runtime behavior remain subject to revision when they fail settlement.

The target-state contract lives in `docs/plans/specs/2026-05-30-cognitive-operating-system-spec.md`, and the bridge plan from the earlier harness substrate to that target lives in `docs/plans/2026-05-30-cognitive-operating-system-bridge-plan.md`. The main bridge milestones are now implemented and validated through the runtime, hooks, MCP, reports, and enterprise-readiness audit.

## Package

- `.claude-plugin/plugin.json` contains plugin identity metadata.
- `skills/`, `agents/`, `hooks/`, `mcp/`, `monitors/`, `bin/`, and settings files live at plugin root level.
- `godspeed_nav/` contains deterministic local computation, storage, runtime, policy, reporting, and validation code.
- `docs/` contains plans, runbooks, and framework understanding notes.
- `tests/` contains the executable contract for CLI behavior, docs alignment, runtime workflow, policies, storage, and reports.

## Quick Start

Prerequisites:

- Python 3.11+
- `uv`
- Node.js for the local RuVector bridge

Install dependencies and run the test suite:

```bash
uv sync --extra dev
pushd tools/ruvector >/dev/null && npm install && popd >/dev/null
uv run pytest -q
```

Run the CLI directly:

```bash
uv run python -m godspeed_nav.cli runtime-snapshot
```

Or use the installed script entrypoint:

```bash
uv run godspeed-nav runtime-snapshot
```

## Using The Harness With A Project

Keep this repository separate from the projects that use it. This repository is the harness implementation. A receiving project keeps its ordinary files in its own root, and the harness records that project's developmental memory inside that workspace.

Recommended layout:

```text
/home/sprime01/projects/
  godspeed_agent/        # harness source and runtime
  my-project/            # receiving project
    src/
    tests/
    HARNESS.md           # optional project policy
    ingest/
      absorption/
    .godspeed-harness/   # local ledgers and reports for this project
```

When running storage-backed commands, point `--workspace-root` at the receiving project:

```bash
uv run godspeed-nav start-direction \
  --workspace-root /home/sprime01/projects/my-project \
  --storage-root .godspeed-harness \
  --label "Initial project direction" \
  --statement "Build the first usable slice"
```

The harness does not become the project, and the project does not need to live inside the harness repository. The project keeps its normal code, tests, docs, and tools at its own root. The harness keeps navigation evidence: desired directions, horizon reviews, affordance paths, payment, settlement, repetition, critiques, and capability state.

## Project Learning And Absorption

A project may absorb capabilities from another project, repository, library, agent, or skill. Stage those candidates under the receiving project's configured ingest root, usually `ingest/absorption/<candidate-name>/`. Use the absorption ingest runbook for the local folder contract, candidate notes, license summary, and settlement plan.

Absorbed material remains `potential` until the receiving project has a spendable pathway. It becomes `absorbable` only when pathway, payment, license, policy, and settlement plan align. It becomes settled only through local consequence in the receiving project. It becomes metabolized only after repeated settlement lowers attention burden.

This distinction matters: the project learns project-specific capabilities, while the harness learns from the project's navigation evidence. For example, a project may learn PDF ingestion. The harness records whether the path used to absorb that parser was affordable, what payment it required, what settled, what failed, and whether repeated use turned the capability into substrate.

## Core Workflow

The harness operationalizes the same loop described in the doctrine:

1. Start a desired direction.
2. Review the visible horizon.
3. Distinguish spendable paths from visible-but-unaffordable possibilities.
4. Estimate payment before acting.
5. Record outcome and settlement based on consequence.
6. Review developmental reports, trajectory, and metabolization signals.
7. Repeat or adjust until capability stabilizes.
8. Expand the horizon and continue from the new substrate.

The fuller doctrine described in `tmp/cogos.md` inserts an explicit representational-state check and affordance-path identification step between horizon review and action. The current runtime now models that layer directly and exposes it through public operator surfaces.

Sample commands:

```bash
uv run godspeed-nav start-direction \
  --label "Enterprise runtime" \
  --statement "Connect workflow commands"

uv run godspeed-nav review-horizon \
  --direction-id <direction-id> \
  --candidates '[{"id":"cli-loop","statement":"Use runtime CLI","pathway":"call CLI","costs":{"time":1},"capacities":{"time":5},"expected_horizon_delta":4,"risk":0}]'

uv run godspeed-nav record-settlement \
  --affordance-id cli-loop \
  --before '{"cli":0}' \
  --after '{"cli":1}' \
  --payment '{"time":1}' \
  --evidence '["cli workflow test passed"]' \
  --horizon-delta 4

uv run godspeed-nav developmental-report
```

## CLI Surfaces

The CLI exposes deterministic and workflow-grade commands.

- `compute-error` compares desired and observed state.
- `estimate-payment` scores payment burden and spendability.
- `rank-affordances` orders candidates by expected expansion and cost.
- `score-settlement` evaluates consequence from before/after state and evidence.
- `metabolization` reviews whether repeated settlement is strong enough to count as substrate.
- `absorbability` checks whether an external capability is potential, possible, or absorbable.
- `start-direction`, `review-horizon`, `record-settlement`, and `runtime-snapshot` operate the local runtime.
- `developmental-report` summarizes settlement quality, payment burden, trajectory, and active directions.
- `search-developmental-memory` runs local RuVector-backed semantic retrieval over structured developmental-memory summaries.
- `validate` runs an enterprise-readiness audit over package shape, config, storage, hooks, MCP, runtime, and reports.

These surfaces implement the cognitive-runtime substrate directly. Representational state, transition policy, explicit affordance paths, identity-state accounting, repetition backlog, developmental memory lineage, and runtime-owned self-critique are now inspectable through the public surfaces.

The RuVector bridge lives under `tools/ruvector/` and is intentionally local-first: Python owns the developmental ledgers, while a small Node sidecar uses the published `ruvector` package to run similarity search over structured settlement and critique summaries rather than raw traces.

## Implementation-defined Behavior

Implementation-defined defaults are documented in `HARNESS.md`. This implementation uses `.godspeed-harness` as the local storage root, JSONL ledgers, Python deterministic computation, and a default maximum payment burden of `100`.

No external API calls by default. MCP tools and hook scripts operate on local input, local computation, and configured local storage.

## Repository Guide

- `AGENTS.md` defines how human and machine agents should work in this repository.
- `HARNESS.md` documents the active policy defaults and implementation-defined behavior.
- `docs/references/` contains the operator-facing ledger, schema, CLI, policy, report, and workflow references.
- `docs/runbooks/` documents installation, configuration, absorption ingest, backup and restore, incident recovery, and release readiness.
- `docs/plans/` captures implementation, hardening, and target-state bridge plans.
- `docs/understanding/` captures the doctrine and enterprise framing that shaped the runtime.

## Self-Critique

The harness doctrine is not protected from review. Use the `framework-reconstruction` skill when doctrine, policy, skills, or navigation assumptions fail settlement. Failed structure should dissolve or be replaced, and repeated successful patterns should become substrate.

The manifesto's falsification rule applies here: if repeated use does not produce observable horizon expansion or capability formation, if payment and settlement stop correlating with capability, or if the framework cannot identify its own blind spots, the relevant surface should be revised rather than defended.

## Verification

Run:

```bash
uv run pytest -q
```

Focused checks:

```bash
uv run pytest tests/test_docs_alignment.py -q
uv run pytest tests/test_cli_hooks_mcp.py -q
uv run python -m godspeed_nav.cli search-developmental-memory --query "timeout recovery"
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation
```

Sample CLI:

```bash
uv run python -m godspeed_nav.cli compute-error --desired '{"tests": 3}' --observed '{"tests": 1}'
```
