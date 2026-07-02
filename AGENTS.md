# AGENTS.md

## Normative Language

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as described in RFC 2119.

Implementation-defined means the behavior is part of the implementation contract, but this specification does not prescribe one universal policy. Implementations MUST document the selected behavior.

## Purpose

This repository implements Godspeed Agent Harness, a local-first cybernetic navigation runtime for agents that is evolving toward the fuller Cognitive Operating System described in `tmp/cogos.md` and the computational core described in `tmp/math.md`. The project is developmental rather than arrival-centric: agents should optimize for horizon expansion through the next affordable affordance, not for static outcome completion.

When working in this repo, treat outcomes as temporary attractors. Once an outcome settles, its value is that it becomes substrate and exposes new affordances.

Do not treat the framework as outcome-dismissive. Outcomes matter because they are settlement events: they provide the richest error-correction data, reveal what payment actually purchased, and become developmental memory for the next cycle.

## Core Operating Model

Agent work in this repository follows the same loop defined in the doctrine:

1. Identify the active desired direction.
2. Check the visible horizon.
3. Check the current representational state and avoid pretending opposites are directly spendable.
4. Separate spendable affordance paths from mere possibilities or potentials.
5. Estimate payment before acting.
6. Execute and record settlement based on consequence, not declared intent.
7. Harvest error-correction data, then repeat or adjust under variation.
8. Count capability as metabolized only after repeated settlement survives.
9. Use the new substrate to expand the next horizon.

Do not claim a capability exists because it was described, scaffolded, or configured. In this project, capabilities become real only after they survive settlement.

Do not confuse a visible destination with a spendable path. The pathway itself is the affordance.

## Repo-Specific Rules

### 1. Preserve the framework vocabulary

Use the project's terms precisely:

- `desired direction` means the active attractor, whether framed as a goal, problem, vision, or outcome.
- `horizon` means what is currently perceivable and actionable.
- `representational state` means the current position in scope and mode-of-givenness space.
- `affordance` means a spendable path through a state space, not merely a visible destination.
- `affordance inventory` means what paths appear available.
- `affordance utilization` means what paths the observer can actually identify, sequence, and spend.
- `horizon expansion` means new perception-action space after settlement and metabolization; it is not the same thing as resource access.
- `potential` and `possibility` are not spendable.
- `payment` is the immediate cost.
- `settlement` is the consequence recorded by reality or by the system's evidence surface.
- `outcome` means a feedback-rich settlement event, not a terminal god.
- `metabolization` requires repetition, time, and successful settlement.
- `identity` means metabolized history, not fixed essence.
- `positive disintegration` means dissolving obsolete structure while salvaging useful substrate.

Use `mode of givenness` or `embodiment` precisely when discussing the abstract/concrete axis. Use `generalization`, `specification`, `abstraction`, and `concretion` for representational moves, not as loose metaphors.

Avoid replacing these terms with generic product language when writing docs, tests, or prompts.

### 2. Keep the project local-first

- Prefer local computation, local files, and local ledgers.
- Do not add external API dependencies by default.
- Document any implementation-defined behavior in `HARNESS.md` and reflect user-facing consequences in `README.md`.

### 3. Deterministic before predictive

- Use deterministic accounting for payment, settlement, trajectory, storage, and policy gates first.
- Only introduce ML-backed behavior where the codebase already expects it and where settlement history justifies it.
- Do not present simulation or prediction as proof of capability.
- Do not let simulated competence become imaginary muscles.

### 4. Evidence over intent

- Settlement is based on before/after state and evidence, not on operator claims.
- Do not mark work complete because code was written; validate the change with the narrowest useful check.
- If a change modifies doctrine, policy, or ledger semantics, update the corresponding docs and tests in the same slice.

### 5. Respect representational path dependency

- Do not assume a direct jump from general to specific or abstract to concrete is affordable.
- When the repo starts modeling representational state explicitly, prefer adjacent moves over opposition jumps unless the shortcut is already proven by repeated settlement.
- If a user request implies a destination with no spendable path, name the missing intermediate state instead of pretending the path exists.

### 6. Identity and governance are not optional

- Desired directions select environments and pressures; pressures shape adaptations; adaptations become capability and identity.
- Do not talk as if more resources automatically mean more horizon.
- The framework describes navigation, not morality. When the work touches values or governance, make the value layer explicit rather than smuggling it in as if the doctrine decided it for you.

### 7. Self-critique is part of the contract

- Preserve or improve falsification surfaces.
- If a design, rule, or document drifts from the doctrine, revise it rather than layering contradictory language on top.
- Prefer small corrections that strengthen the project's explainability.
- Treat the framework itself as subject to settlement, critique, and revision.

## Working Agreements For Agents

### Start from the nearest controlling surface

For code changes, anchor on the file, command, test, or runtime surface that directly controls the behavior. Avoid broad exploration once you can state a local hypothesis.

### Make changes that survive settlement

- Update tests when behavior or contracts change.
- Keep edits minimal and consistent with the existing style.
- Do not invent parallel abstractions when the runtime, ledgers, hooks, or reports already express the concept.
- Do not confuse explanation, access, or installation with metabolized capability.

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
- Keep simulated, inferred, or hypothetical state distinct from settled developmental memory.

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
5. The result does not confuse potential with affordance, destination with path, or intent with settlement.
6. The change does not treat explanation, access, or simulation as proof of capability.
7. If the work changes doctrine, policy, or developmental memory semantics, the falsification surface is preserved or improved.

## If The Doctrine Fails

Use self-critique. If the framework language, policies, or mechanics fail settlement in practice, document the mismatch, revise the relevant surface, and prefer reconstruction over doctrinal drift.

Commit often, and update `CURRENT_STATE.md` at every meaningful milestone.
