# Godspeed Agent Harness

Godspeed Agent Harness is a local-first Claude Code plugin and Python runtime for horizon-centric cybernetic navigation. It turns desired directions into horizon checks, affordance candidates, payment estimates, settlement events, developmental memory, and runtime validation.

The harness is developmental rather than arrival-centric. In this project, outcome completion is not terminal: a settled outcome becomes substrate and should expose new affordances.

## What It Does

- Converts desired-direction language into an explicit navigation loop.
- Distinguishes potentials, possibilities, affordances, capabilities, and substrate.
- Records payment, settlement, trajectory, and developmental memory in local ledgers.
- Exposes runtime and review workflows through a Python CLI, hooks, MCP servers, and skill packages.
- Keeps the system open to self-critique so doctrine can be revised when it fails settlement.

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

Install dependencies and run the test suite:

```bash
uv sync --extra dev
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

## Core Workflow

The harness operationalizes the same loop described in the doctrine:

1. Start a desired direction.
2. Review the visible horizon.
3. Rank spendable affordances.
4. Record payment and settlement.
5. Review developmental reports and metabolization signals.
6. Expand the horizon and repeat.

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
- `validate` runs an enterprise-readiness audit over package shape, config, storage, hooks, MCP, runtime, and reports.

## Implementation-defined Behavior

Implementation-defined defaults are documented in `HARNESS.md`. This implementation uses `.godspeed-harness` as the local storage root, JSONL ledgers, Python deterministic computation, and a default maximum payment burden of `100`.

No external API calls by default. MCP tools and hook scripts operate on local input, local computation, and configured local storage.

## Repository Guide

- `AGENTS.md` defines how human and machine agents should work in this repository.
- `HARNESS.md` documents the active policy defaults and implementation-defined behavior.
- `docs/runbooks/` documents installation, configuration, backup and restore, incident recovery, and release readiness.
- `docs/plans/` captures implementation and hardening plans.
- `docs/understanding/` captures the doctrine and enterprise framing that shaped the runtime.

## Self-Critique

The harness doctrine is not protected from review. Use the `framework-reconstruction` skill when doctrine, policy, skills, or navigation assumptions fail settlement. Failed structure should dissolve or be replaced, and repeated successful patterns should become substrate.

## Verification

Run:

```bash
uv run pytest -q
```

Focused checks:

```bash
uv run pytest tests/test_docs_alignment.py -q
uv run pytest tests/test_cli_hooks_mcp.py -q
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation
```

Sample CLI:

```bash
uv run python -m godspeed_nav.cli compute-error --desired '{"tests": 3}' --observed '{"tests": 1}'
```# Godspeed Agent Harness

Godspeed Agent Harness is a local-first Claude Code plugin and Python harness for horizon-centric cybernetic navigation. It converts desired directions into horizon checks, affordance candidates, payment estimates, settlement events, and developmental memory.

Outcome completion is not terminal. A settled outcome becomes substrate and should expose new affordances.

## Package

- `.claude-plugin/plugin.json` contains plugin identity metadata.
- `skills/`, `agents/`, `hooks/`, `mcp/`, `monitors/`, `bin/`, and settings files live at plugin root level.
- `godspeed_nav/` contains deterministic local computation and storage code.

## Implementation-defined Behavior

Implementation-defined defaults are documented in `HARNESS.md`. This implementation uses `.godspeed-harness` as the local storage root, JSONL ledgers, Python deterministic computation, and a default maximum payment burden of `100`.

No external API calls by default. MCP tools and hook scripts operate on local input, local computation, and configured local storage.

## Self-Critique

The harness doctrine is not protected from review. Use the `framework-reconstruction` skill when doctrine, policy, skills, or navigation assumptions fail settlement. Failed structure should dissolve or be replaced, and repeated successful patterns should become substrate.

## Verification

Run:

```bash
uv run pytest -q
```

Sample CLI:

```bash
uv run python -m godspeed_nav.cli compute-error --desired '{"tests": 3}' --observed '{"tests": 1}'
```
