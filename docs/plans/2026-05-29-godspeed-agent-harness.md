# Godspeed Agent Harness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local-first Claude Code plugin and Python harness that satisfies the core and developmental conformance requirements in `Godspeed_Agent_Harness_SPEC.md`.

**Architecture:** Package plugin metadata, skills, hooks, agents, monitors, and MCP configuration at the repository root, with deterministic computation in a Python package named `godspeed_nav`. Store developmental memory as local JSONL ledgers under `.godspeed-harness` by default, and expose the same deterministic functions through tests, CLI, hook scripts, and an optional MCP server wrapper.

**Tech Stack:** Python 3.11+, uv, pytest, PyYAML, NumPy, Pandas, optional Scikit-learn after threshold checks.

### Task 1: Plugin Scaffold and Validation Tests

**Files:**
- Create: `pyproject.toml`
- Create: `.claude-plugin/plugin.json`
- Create: `tests/test_plugin_structure.py`
- Modify: `CURRENT_STATE.md`

**Steps:**
1. Write failing pytest tests that assert the plugin manifest exists, has `name` and `description`, and that required skill directories contain `SKILL.md` with YAML frontmatter descriptions.
2. Run `uv run pytest tests/test_plugin_structure.py -q` and verify it fails because the scaffold is missing.
3. Add the plugin manifest, baseline Python project metadata, and placeholder skill files.
4. Run the same tests and verify they pass.
5. Update `CURRENT_STATE.md` with the verified scaffold milestone.
6. Commit with `feat: scaffold plugin package`.

### Task 2: Harness Config Loader

**Files:**
- Create: `godspeed_nav/config.py`
- Create: `tests/test_config.py`
- Create: `HARNESS.md`
- Modify: `CURRENT_STATE.md`

**Steps:**
1. Write failing tests for missing config defaults, YAML parse errors, unknown key tolerance, unsafe storage root rejection, `primary_metric` defaulting to `horizon_expansion`, and `outcome_as_terminal` defaulting to false.
2. Run `uv run pytest tests/test_config.py -q` and verify the expected failures.
3. Implement the config loader and typed validation errors.
4. Add a default `HARNESS.md` documenting implementation-defined policy.
5. Run the tests and verify they pass.
6. Update `CURRENT_STATE.md`.
7. Commit with `feat: add harness config loader`.

### Task 3: Domain Models and Storage

**Files:**
- Create: `godspeed_nav/schemas.py`
- Create: `godspeed_nav/storage.py`
- Create: `schemas/*.schema.json`
- Create: `ledgers/README.md`
- Create: `tests/test_domain_storage.py`
- Modify: `CURRENT_STATE.md`

**Steps:**
1. Write failing tests for potential, possibility, affordance, capability, substrate, desired direction, ledger append/read, secret redaction, and corrupt record quarantine.
2. Run `uv run pytest tests/test_domain_storage.py -q` and verify failures.
3. Implement dataclasses, lifecycle guards, JSON schemas, and append-only JSONL storage.
4. Run the tests and verify they pass.
5. Update `CURRENT_STATE.md`.
6. Commit with `feat: add domain models and ledgers`.

### Task 4: Deterministic Computation

**Files:**
- Create: `godspeed_nav/metrics.py`
- Create: `godspeed_nav/trajectory.py`
- Create: `godspeed_nav/metabolization.py`
- Create: `godspeed_nav/absorption.py`
- Create: `godspeed_nav/disintegration.py`
- Create: `godspeed_nav/ml.py`
- Create: `tests/test_computation.py`
- Modify: `CURRENT_STATE.md`

**Steps:**
1. Write failing tests for error magnitude, payment burden, settlement evidence rejection, trajectory radius growth, circular motion detection, metabolization rejection, affordance ranking, absorbability review, positive disintegration review, and ML threshold refusal.
2. Run `uv run pytest tests/test_computation.py -q` and verify failures.
3. Implement the deterministic functions with no external API calls.
4. Run the tests and verify they pass.
5. Update `CURRENT_STATE.md`.
6. Commit with `feat: add deterministic navigation engine`.

### Task 5: CLI, Hooks, MCP Wrapper, and Reports

**Files:**
- Create: `godspeed_nav/cli.py`
- Create: `bin/godspeed-nav`
- Create: `hooks/*.py`
- Create: `hooks/hooks.json`
- Create: `mcp/cybernetic-nav-server/server.py`
- Create: `mcp/cybernetic-nav-server/pyproject.toml`
- Create: `.mcp.json`
- Create: `monitors/monitors.json`
- Create: `tests/test_cli_hooks_mcp.py`
- Modify: `CURRENT_STATE.md`

**Steps:**
1. Write failing tests for CLI JSON outputs, hook stdin handling, unaffordable action warnings, post-tool settlement events, stop consolidation, and MCP wrapper tool registration.
2. Run `uv run pytest tests/test_cli_hooks_mcp.py -q` and verify failures.
3. Implement the CLI, hook scripts, MCP wrapper metadata, and monitor config.
4. Run the tests and verify they pass.
5. Update `CURRENT_STATE.md`.
6. Commit with `feat: expose harness runtime surfaces`.

### Task 6: Skills, Agents, Evals, Documentation, and Final Verification

**Files:**
- Modify: `skills/*/SKILL.md`
- Create: `skills/*/references/*.md`
- Create: `skills/*/scripts/*.py`
- Create: `agents/*.md`
- Create: `evals/evals.json`
- Create: `README.md`
- Modify: `CURRENT_STATE.md`

**Steps:**
1. Write or extend tests that verify all skill descriptions include trigger context and task purpose, eval prompts include should-trigger and should-not-trigger cases, and docs describe implementation-defined behavior.
2. Run the full suite and verify failures for missing documentation pieces.
3. Fill in focused skill instructions, references, scripts, agents, evals, and README.
4. Run `uv run pytest -q`.
5. Run a sample horizon review, failed settlement, successful settlement, metabolization rejection, and absorption rejection through the CLI.
6. Update `CURRENT_STATE.md` with evidence.
7. Commit with `feat: complete harness documentation and validation`.
