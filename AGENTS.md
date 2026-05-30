# AGENTS.md

## Purpose

This repository implements Godspeed Agent Harness, a local-first cybernetic navigation runtime for Claude Code. The project is developmental rather than arrival-centric: agents should optimize for horizon expansion through the next affordable affordance, not for static outcome completion.

When working in this repo, treat outcomes as temporary attractors. Once an outcome settles, its value is that it becomes substrate and exposes new affordances.

## Core Operating Model

Agent work in this repository follows the same loop defined in the doctrine:

1. Identify the active desired direction.
2. Check the visible horizon.
3. Separate spendable affordances from mere possibilities or potentials.
4. Estimate payment before acting.
5. Execute and record settlement based on consequence, not declared intent.
6. Repeat until the capability is stable enough to count as metabolized.
7. Use the new substrate to expand the next horizon.

Do not claim a capability exists because it was described, scaffolded, or configured. In this project, capabilities become real only after they survive settlement.

## Repo-Specific Rules

### 1. Preserve the framework vocabulary

Use the project's terms precisely:

- `desired direction` means the active attractor, whether framed as a goal, problem, vision, or outcome.
- `horizon` means what is currently perceivable and actionable.
- `affordance` means a reachable, spendable transformation with a pathway and affordable payment.
- `potential` and `possibility` are not spendable.
- `payment` is the immediate cost.
- `settlement` is the consequence recorded by reality or by the system's evidence surface.
- `metabolization` requires repetition, time, and successful settlement.
- `positive disintegration` means dissolving obsolete structure while salvaging useful substrate.

Avoid replacing these terms with generic product language when writing docs, tests, or prompts.

### 2. Keep the project local-first

- Prefer local computation, local files, and local ledgers.
- Do not add external API dependencies by default.
- Document any implementation-defined behavior in `HARNESS.md` and reflect user-facing consequences in `README.md`.

### 3. Deterministic before predictive

- Use deterministic accounting for payment, settlement, trajectory, storage, and policy gates first.
- Only introduce ML-backed behavior where the codebase already expects it and where settlement history justifies it.
- Do not present simulation or prediction as proof of capability.

### 4. Evidence over intent

- Settlement is based on before/after state and evidence, not on operator claims.
- Do not mark work complete because code was written; validate the change with the narrowest useful check.
- If a change modifies doctrine, policy, or ledger semantics, update the corresponding docs and tests in the same slice.

### 5. Self-critique is part of the contract

- Preserve or improve falsification surfaces.
- If a design, rule, or document drifts from the doctrine, revise it rather than layering contradictory language on top.
- Prefer small corrections that strengthen the project's explainability.

## Working Agreements For Agents

### Start from the nearest controlling surface

For code changes, anchor on the file, command, test, or runtime surface that directly controls the behavior. Avoid broad exploration once you can state a local hypothesis.

### Make changes that survive settlement

- Update tests when behavior or contracts change.
- Keep edits minimal and consistent with the existing style.
- Do not invent parallel abstractions when the runtime, ledgers, hooks, or reports already express the concept.

### Prefer focused validation

Use the smallest relevant validation first, for example:

- `uv run pytest tests/test_docs_alignment.py -q`
- `uv run pytest tests/test_cli_hooks_mcp.py -q`
- `uv run pytest -q`
- `uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation`

### Respect the storage and policy surfaces

- Runtime state lives under `.godspeed-harness` unless configuration says otherwise.
- Do not bypass policy gates silently.
- If you change storage shape, indexes, manifests, or event envelopes, extend the relevant enterprise storage tests.

## Project Map

- `godspeed_nav/` contains the deterministic runtime, storage, policy, reporting, validation, and computation modules.
- `skills/` contains harness workflows and compiled capability guidance.
- `agents/` contains role contracts for navigator, evaluator, metabolizer, absorber, and disintegrator agents.
- `hooks/` and `mcp/` expose lifecycle and tool surfaces.
- `docs/plans/`, `docs/runbooks/`, and `docs/understanding/` carry the planning, operations, and doctrine context.
- `tests/` is the executable contract. Extend it when changing behavior.

## Definition of Done

Work is complete when all of the following hold:

1. The requested behavior exists at the controlling surface.
2. The change is explained by the framework rather than fighting it.
3. Focused validation passes.
4. User-facing docs are updated when the contract changed.
5. The result does not confuse potential with affordance or intent with settlement.

## If The Doctrine Fails

Use self-critique. If the framework language, policies, or mechanics fail settlement in practice, document the mismatch, revise the relevant surface, and prefer reconstruction over doctrinal drift.

Commit often, and update `CURRENT_STATE.md` at every meaningful milestone.
