# Godspeed Agent Harness Specification

Status: Draft v1 (language-agnostic)

Purpose: Define a Claude Code plugin and local agent harness that operationalizes the horizon-centric Version 10 cybernetic navigation framework for capability formation, settlement accounting, metabolization, and positive disintegration.

## Normative Language

The key words `MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, `SHOULD NOT`, `RECOMMENDED`, `MAY`, and `OPTIONAL` in this document are to be interpreted as described in RFC 2119.

`Implementation-defined` means the behavior is part of the implementation contract, but this specification does not prescribe one universal policy. Implementations MUST document the selected behavior.

`Framework-defined` means the behavior follows the Version 10 horizon-centric cybernetic navigation model defined in this specification.

`Plugin-defined` means the behavior follows the Claude Code plugin package contract chosen by an implementation.

`Skill-defined` means the behavior follows the `SKILL.md` instructions and bundled resources inside a Claude Code skill.

## 1. Problem Statement

Godspeed Agent Harness is a local-first agent harness packaged as a Claude Code plugin. It turns agent work from one-off task execution into a repeatable developmental loop.

The harness is not primarily designed to complete final outcomes. Outcomes are treated as temporary attractors. When an outcome is achieved, it stops producing the same pressure, becomes substrate, and exposes new affordances. The harness therefore optimizes for horizon expansion through the next affordable affordance, not for static goal completion.

The harness solves six operational problems:

- It converts desired directions into explicit horizon checks, affordance candidates, payment estimates, and settlement events.
- It records developmental memory so an agent can answer: `How did this system become what it is?`
- It prevents premature absorption by distinguishing potential, possibility, affordance, capability, and substrate.
- It gives agents deterministic computation tools for error, payment burden, settlement scoring, trajectory tracking, and metabolization review.
- It packages the framework into Claude Code-compatible plugin components: skills, agents, hooks, MCP servers, monitors, settings, and local executables.
- It provides enough observability to debug whether work is expanding the horizon or merely creating circular motion.

Important boundary:

- Godspeed Agent Harness is a developmental runtime and plugin package.
- It is not a general-purpose distributed scheduler.
- It is not a values system.
- It is not a theory of reality.
- It is not a claim that reality literally obeys Pythagoras, Euler, or control equations.
- It uses mathematical projections as computational instruments that preserve useful relationships.

## 2. Goals and Non-Goals

### 2.1 Goals

- Package the harness as a Claude Code plugin with a valid `.claude-plugin/plugin.json` manifest.
- Provide Claude Code skills under plugin-root `skills/<skill-name>/SKILL.md` directories.
- Provide OPTIONAL agents, hooks, MCP servers, monitors, settings, and executable tools at plugin-root locations rather than inside `.claude-plugin/`.
- Maintain a local developmental memory store for horizon, affordance, payment, settlement, capability, trajectory, metabolization, and disintegration records.
- Compute cybernetic error, payment burden, settlement score, trajectory growth, circular motion, and metabolization candidates.
- Run deterministic rule-based accounting before ML-based prediction.
- Support Scikit-learn only after enough settlement diversity exists to justify learned pattern detection or prediction.
- Support local simulation for high-risk affordance candidates before real settlement attempts.
- Expose a clear distinction between potential, possibility, affordance, capability, and substrate.
- Preserve self-revision: the framework itself MUST be subject to settlement, disintegration, and replacement.

### 2.2 Non-Goals

- Mandating one final business workflow for Godspeed AI.
- Mandating one issue tracker, CRM, repository host, or cloud provider.
- Mandating remote APIs or SaaS services.
- Mandating a rich UI.
- Mandating that every deployment use ML.
- Mandating that every deployment expose an MCP server.
- Mandating that every deployment run autonomous code edits.
- Treating generated documents as proof of capability.
- Treating installed skills as metabolized capabilities.
- Treating outcome completion as the primary measure of success.

## 3. System Overview

### 3.1 Main Components

1. `Plugin Package`
   - Contains `.claude-plugin/plugin.json`.
   - Contains all plugin components at plugin root level.
   - Provides namespaced skills such as `/godspeed-harness:horizon-review`.

2. `Skill Layer`
   - Provides task-specific `SKILL.md` instructions.
   - Uses progressive disclosure: metadata triggers the skill, body guides the workflow, references/scripts provide deeper context.
   - SHOULD keep each `SKILL.md` body focused and move large content into `references/` or `scripts/`.

3. `Agent Layer` (OPTIONAL)
   - Provides custom Claude Code agents for specialized harness roles.
   - Example roles: `navigator`, `evaluator`, `metabolizer`, `absorber`, `disintegrator`.

4. `Hook Layer` (OPTIONAL but RECOMMENDED)
   - Captures lifecycle events such as prompt submit, pre-tool-use, post-tool-use, and stop/session-end.
   - Converts agent activity into ledger events.

5. `MCP Tool Layer` (OPTIONAL but RECOMMENDED)
   - Exposes deterministic computation tools to Claude.
   - Tools compute error, payment burden, settlement score, trajectory update, metabolization score, and circular motion detection.

6. `Local Computation Library`
   - Implements deterministic accounting using Python, Pandas, and NumPy.
   - MAY implement ML extensions using Scikit-learn after sufficient settlement history exists.

7. `Developmental Memory Store`
   - Stores events, ledgers, trajectories, capability records, and horizon snapshots.
   - MUST be local-first unless the user explicitly enables external storage.

8. `Horizon Controller`
   - Maintains the current visible affordance horizon.
   - Prioritizes next affordable affordances over final outcomes.

9. `Affordance Engine`
   - Distinguishes potential, possibility, affordance, capability, and substrate.
   - Rejects premature absorption.

10. `Payment Engine`
    - Estimates required payment across time, compute, risk, complexity, maintenance, attention, and coordination dimensions.

11. `Settlement Evaluator`
    - Compares before and after state.
    - Records consequence only, not declared intent.

12. `Trajectory Engine`
    - Tracks developmental spiral movement.
    - Distinguishes circular motion from horizon-expanding growth.

13. `Metabolization Engine`
    - Identifies capabilities that have become substrate through settlement, repetition, and time.
    - MUST NOT treat operator declaration as metabolization.

14. `Positive Disintegration Engine`
    - Finds structures that should dissolve.
    - Finds successful patterns that should become body.

15. `Absorption Engine`
    - Compares an external project, skill, agent, or system against the root project.
    - Determines whether an external capability is currently absorbable.
    - MUST reject external capabilities that lack a pathway into the receiving system.

16. `Observability Surface`
    - Emits structured logs, local reports, snapshots, and optionally monitor notifications.

### 3.2 Abstraction Levels

Godspeed Agent Harness is easiest to implement when kept in these layers:

1. `Doctrine Layer`
   - Horizon-centric framework principles.
   - Definitions for affordance, payment, settlement, metabolization, substrate, and horizon.

2. `Plugin Layer`
   - Claude Code plugin manifest and package structure.
   - Skills, agents, hooks, MCP, monitors, settings, and bin tools.

3. `Policy Layer`
   - `HARNESS.md` or project-level configuration.
   - Team-specific rules for acceptable payments, settlement criteria, and review thresholds.

4. `Computation Layer`
   - Python/Pandas/NumPy deterministic tools.
   - OPTIONAL Scikit-learn models.

5. `Coordination Layer`
   - Session lifecycle, hooks, event ingestion, state updates, and periodic review.

6. `Execution Layer`
   - Agent actions, workspace changes, code edits, experiments, and worktree operations.

7. `Storage Layer`
   - Local ledgers and developmental memory.

8. `Observability Layer`
   - Logs, reports, snapshots, and monitor outputs.

### 3.3 External Dependencies

Required:

- Claude Code installation compatible with plugin loading.
- Local filesystem access.
- Python 3.11+ or implementation-defined equivalent runtime.
- Pandas and NumPy for deterministic accounting.
- Devbox (system dependacies), mise (runtime dependacies), uv (python dependacies)

Optional:

- Scikit-learn for learned pattern detection and prediction.
- Git CLI for worktrees and experiment isolation.
- MCP runtime for external tool exposure to Claude.
- Claude Code hooks and monitors.
- Local SQLite/DuckDB/RuVector or implementation-defined stores for larger ledgers.

## 4. Core Domain Model

### 4.1 Entities

#### 4.1.1 Desired Direction

A polymorphic attractor that may appear as a goal, problem, vision, outcome, aim, mission, need, or JTBD.

Fields:

- `id` (string)
- `label` (string)
- `kind` (enum: `problem`, `goal`, `vision`, `outcome`, `aim`, `mission`, `need`, `jtbd`, `other`)
- `statement` (string)
- `source` (string or null)
- `created_at` (timestamp)
- `status` (enum: `active`, `settled`, `dead`, `archived`)
- `horizon_id` (string)
- `pressure_notes` (string or null)
- `success_criteria` (list of evaluator refs)
- `death_criteria` (list of conditions indicating the attractor no longer produces useful pressure)

Important rule:

- A settled desired direction MUST NOT be treated as final completion.
- It SHOULD be converted into substrate and used to expose new affordances.

#### 4.1.2 Horizon

The boundary of currently visible and spendable transformations for the observer.

Fields:

- `id` (string)
- `observer_id` (string)
- `visible_affordance_ids` (list)
- `potential_ids` (list)
- `blindspot_notes` (string or null)
- `capability_basis` (list of capability IDs)
- `substrate_basis` (list of substrate IDs)
- `radius` (number, optional Euler projection coordinate)
- `created_at` (timestamp)
- `updated_at` (timestamp)

#### 4.1.3 Potential

A transformation that can be imagined or described but lacks a validated pathway for the observer.

Fields:

- `id`
- `statement`
- `required_capabilities`
- `missing_pathway_reason`
- `current_status` = `potential`

Rule:

- Potential MUST NOT be scheduled for execution as if it were an affordance.

#### 4.1.4 Possibility

A transformation that can be represented and may have a plausible path, but has not yet been proven spendable.

Fields:

- `id`
- `statement`
- `candidate_pathway`
- `unknowns`
- `current_status` = `possibility`

Rule:

- Possibility MAY enter experiment lab evaluation.
- Possibility MUST become affordance only after spendability is established.

#### 4.1.5 Affordance

The next spendable transformation visible from the current horizon.

Fields:

- `id`
- `description`
- `desired_direction_id`
- `horizon_id`
- `preconditions` (list of capability/substrate refs)
- `payment_estimate_id`
- `expected_horizon_delta`
- `expected_error_delta`
- `risk_level`
- `status` (enum: `candidate`, `spendable`, `in_experiment`, `settled`, `failed`, `archived`)

Rules:

- Affordance MUST have a pathway.
- Affordance MUST have a payment estimate.
- Affordance MUST be within current capacity.
- Affordance MUST NOT be confused with potential or possibility.

#### 4.1.6 Payment Estimate

The expected cost required to attempt an affordance.

Fields:

- `id`
- `affordance_id`
- `cost_vector` (map dimension -> number)
- `weights` (map dimension -> number)
- `burden_norm` (number)
- `capacity_norm` (number)
- `spendability` (enum: `affordable`, `marginal`, `unaffordable`)
- `schedule` (enum: `compressed`, `distributed`, `unknown`)
- `notes`

#### 4.1.7 Settlement Event

Reality's audit record for an attempted affordance.

Fields:

- `id`
- `affordance_id`
- `desired_direction_id`
- `before_state` (map)
- `after_state` (map)
- `payment_actual` (map)
- `observed_consequence` (string)
- `settlement_score` (number)
- `status` (enum: `settled`, `partial`, `failed`, `inconclusive`)
- `unexpected_effects` (list)
- `created_at`

Rule:

- Settlement records consequence only.
- Settlement MUST NOT record intention as proof.

#### 4.1.8 Capability

A transformation that repeatedly survives settlement under relevant conditions.

Fields:

- `id`
- `name`
- `origin_affordance_ids`
- `settlement_event_ids`
- `reuse_count`
- `context_diversity`
- `success_stability`
- `maintenance_burden`
- `status` (enum: `explicit`, `stabilizing`, `metabolized`, `retired`)

Rule:

- Capability is settled into existence.
- Capability is not installed, declared, or imagined into existence.

#### 4.1.9 Substrate

Metabolized capability that no longer requires explicit attention.

Fields:

- `id`
- `capability_id`
- `compiled_form` (enum: `skill`, `hook`, `script`, `schema`, `workflow`, `muscle_memory`, `culture`, `other`)
- `attention_reduction_evidence`
- `horizon_delta_evidence`
- `created_at`

Rule:

- Substrate MUST be earned by settlement + repetition + time.

#### 4.1.10 Developmental Memory

A time-indexed record of transformations.

Fields:

- `events` (list of event refs)
- `settlements` (list of settlement refs)
- `capabilities` (list of capability refs)
- `substrates` (list of substrate refs)
- `horizon_snapshots` (list of horizon refs)
- `disintegrations` (list of disintegration refs)

Question answered:

- `How did this system become what it is?`

#### 4.1.11 Trajectory Record

A computational projection of developmental movement.

Fields:

- `id`
- `desired_direction_id`
- `theta` (number)
- `radius` (number)
- `z_real` (number)
- `z_imag` (number)
- `cycle_index` (integer)
- `radius_delta`
- `settlement_score`
- `interpretation` (string)

#### 4.1.12 Disintegration Event

A record of dissolved structure and metabolized residue.

Fields:

- `id`
- `target_id`
- `target_kind`
- `reason`
- `dissolved_elements`
- `metabolized_elements`
- `risk_notes`
- `created_at`

#### 4.1.13 Absorption Proposal

A proposal for importing affordance delta from an external system.

Fields:

- `id`
- `source_path_or_ref`
- `source_license_summary`
- `observed_external_capability`
- `root_desired_direction_id`
- `absorbability_status` (enum: `potential`, `possible`, `affordance`, `rejected`)
- `pathway`
- `payment_estimate_id`
- `proposed_patch_plan`
- `worktree_path`
- `settlement_plan`

Rule:

- External capability is not absorbable unless a pathway exists, the receiving system can afford it, and settlement is possible.

### 4.2 Stable Identifiers and Normalization Rules

- IDs SHOULD use stable prefixed identifiers: `dir_`, `hor_`, `aff_`, `pay_`, `set_`, `cap_`, `sub_`, `traj_`, `dis_`, `abs_`.
- Paths MUST be normalized to absolute paths before tool execution.
- Capability and affordance names SHOULD be lowercase kebab-case.
- Ledger event timestamps MUST be UTC ISO-8601 unless implementation-defined otherwise.
- Status values MUST be normalized to lowercase.

## 5. Claude Code Plugin Package Specification

### 5.1 Plugin Structure

A conforming plugin package SHOULD use this layout:

```text
godspeed-agent-harness/
  .claude-plugin/
    plugin.json
  README.md
  HARNESS.md
  settings.json
  skills/
    horizon-review/
      SKILL.md
      references/
        glossary.md
        computational-projections.md
        framework-invariants.md
      scripts/
        horizon_review.py
    affordance-accounting/
      SKILL.md
      references/
        payment-and-settlement.md
      scripts/
        compute_affordance.py
    settlement-evaluation/
      SKILL.md
      scripts/
        settlement.py
    metabolization-review/
      SKILL.md
      scripts/
        metabolization.py
    positive-disintegration/
      SKILL.md
      scripts/
        disintegrate.py
    absorption-review/
      SKILL.md
      scripts/
        absorb.py
  agents/
    navigator.md
    evaluator.md
    metabolizer.md
    absorber.md
    disintegrator.md
  hooks/
    hooks.json
    user_prompt_submit.py
    pre_tool_use.py
    post_tool_use.py
    stop.py
  mcp/
    cybernetic-nav-server/
      server.py
      pyproject.toml
  .mcp.json
  monitors/
    monitors.json
  bin/
    godspeed-nav
  schemas/
    desired_direction.schema.json
    horizon.schema.json
    affordance.schema.json
    payment.schema.json
    settlement.schema.json
    capability.schema.json
    substrate.schema.json
    trajectory.schema.json
  ledgers/
    README.md
    .gitkeep
  evals/
    evals.json
```

Rules:

- `.claude-plugin/plugin.json` MUST contain plugin identity metadata.
- `skills/`, `agents/`, `hooks/`, `.mcp.json`, `.lsp.json`, `monitors/`, `bin/`, and `settings.json` MUST live at plugin root level when present.
- Implementations MUST NOT place skills, hooks, agents, monitors, MCP config, or bin tools inside `.claude-plugin/`.

### 5.2 Plugin Manifest

A minimal manifest:

```json
{
  "name": "godspeed-agent-harness",
  "description": "Horizon-centric cybernetic navigation harness for affordance accounting, settlement evaluation, metabolization review, and developmental memory.",
  "version": "0.1.0",
  "author": {
    "name": "Godspeed AI"
  }
}
```

Requirements:

- `name` MUST be unique within the user/plugin environment.
- `description` SHOULD state what the plugin does and when it should be used.
- `version` SHOULD be present for release distribution.
- Implementations MAY include `repository`, `homepage`, and `license` fields.

### 5.3 Skill Authoring Contract

Each skill MUST include:

- `SKILL.md`
- YAML frontmatter with `description`
- Markdown instructions

Each skill SHOULD keep `SKILL.md` under approximately 500 lines and put large materials under `references/` or `scripts/`.

The skill description SHOULD include both what the skill does and the specific contexts in which Claude should use it. It SHOULD be explicit enough to avoid under-triggering.

Example:

```markdown
---
description: Use this skill whenever the user asks to assess whether a goal, project, feature, code change, or agent behavior is actually affordable from the current horizon. It identifies potentials, possibilities, affordances, capabilities, and substrate; estimates payment; and recommends the next spendable transformation.
---

# Horizon Review

Use this skill to convert a requested outcome into a horizon-centric navigation review.

Always distinguish:

1. Potential
2. Possibility
3. Affordance
4. Capability
5. Substrate

Never treat the final outcome as the target. Identify the next affordable affordance visible from the current horizon.
```

### 5.4 Skill Set

A conforming initial plugin SHOULD include these skills:

1. `horizon-review`
   - Determines current horizon, visible affordances, hidden potentials, and next affordable transformation.

2. `affordance-accounting`
   - Computes or narratively estimates payment burden and spendability.

3. `settlement-evaluation`
   - Scores whether an action settled successfully.

4. `metabolization-review`
   - Determines whether repeated settlement + repetition + time has become substrate.

5. `positive-disintegration`
   - Identifies what must dissolve and what should become body.

6. `absorption-review`
   - Evaluates whether an external project or capability can be absorbed.

7. `framework-reconstruction`
   - Rebuilds framework documents when prior doctrine fails settlement.

### 5.5 Agent Definitions

Custom agents are OPTIONAL. If implemented, they SHOULD be kept in `agents/`.

Recommended agents:

- `navigator`: selects the next affordable affordance.
- `evaluator`: computes settlement against evidence.
- `metabolizer`: reviews repeated settlement history.
- `absorber`: analyzes external systems for absorbable affordance deltas.
- `disintegrator`: performs positive disintegration reviews.

### 5.6 Hooks

Hooks are OPTIONAL but RECOMMENDED.

Recommended hooks:

- `UserPromptSubmit`
  - Extract desired direction and current horizon hypothesis.

- `PreToolUse`
  - Estimate payment burden and block or warn on unaffordable actions.

- `PostToolUse`
  - Record observed consequence and settlement evidence.

- `Stop`
  - Consolidate developmental memory and update trajectory/metabolization state.

Hook commands MUST accept hook input according to Claude Code hook conventions and SHOULD read JSON from stdin.

### 5.7 MCP Servers

An MCP server is OPTIONAL but RECOMMENDED when deterministic computations should be callable by Claude.

Recommended MCP tool namespace: `cybernetic_nav`.

Recommended tools:

- `compute_error`
- `estimate_payment`
- `score_settlement`
- `update_trajectory`
- `detect_circular_motion`
- `compute_metabolization`
- `rank_affordances`
- `review_absorbability`
- `review_positive_disintegration`

### 5.8 Monitors

Monitors are OPTIONAL.

Recommended monitors:

- `settlement-log-monitor`
- `horizon-drift-monitor`
- `circular-motion-monitor`
- `unaffordable-action-monitor`

### 5.9 Settings

If `settings.json` is shipped, it MAY activate a custom agent or status line. Unknown settings SHOULD be ignored by Claude Code according to Claude Code behavior.

## 6. Harness Specification (Repository Contract)

### 6.1 File Discovery and Path Resolution

The harness MAY use a project-level `HARNESS.md` file to define local policy and runtime settings.

Path precedence:

1. Explicit command/runtime setting.
2. `HARNESS.md` in current workspace root.
3. Plugin bundled defaults.

Loader behavior:

- If `HARNESS.md` is absent, use plugin defaults.
- If `HARNESS.md` is present but invalid, keep the last known good config and emit an operator-visible error.

### 6.2 File Format

`HARNESS.md` is a Markdown file with OPTIONAL YAML front matter.

Parsing rules:

- If the file starts with `---`, parse YAML front matter until the next `---`.
- YAML front matter MUST decode to a map/object.
- Markdown body becomes the local doctrine/policy prompt.
- Unknown top-level keys SHOULD be ignored for forward compatibility.

### 6.3 Front Matter Schema

Top-level keys:

- `harness`
- `storage`
- `skills`
- `hooks`
- `mcp`
- `computation`
- `experiments`
- `absorption`
- `safety`
- `observability`

#### 6.3.1 `harness` object

Fields:

- `mode` (string)
  - Default: `local`
  - Supported values: `local`, `workspace`, `experimental`.

- `primary_metric` (string)
  - Default: `horizon_expansion`
  - MUST NOT default to `goal_completion`.

- `allow_outcome_language` (boolean)
  - Default: `true`
  - If true, outcome terms MAY be accepted as aliases for desired direction.

- `outcome_as_terminal` (boolean)
  - Default: `false`
  - MUST NOT be true unless explicitly chosen and documented.

#### 6.3.2 `storage` object

Fields:

- `root` (path)
  - Default: `.godspeed-harness`

- `format` (string)
  - Default: `jsonl`
  - Supported values: `jsonl`, `sqlite`, `duckdb`, `parquet`.

- `retain_raw_events` (boolean)
  - Default: `true`

- `redact_secrets` (boolean)
  - Default: `true`

#### 6.3.3 `computation` object

Fields:

- `engine` (string)
  - Default: `python`

- `use_pandas` (boolean)
  - Default: `true`

- `use_numpy` (boolean)
  - Default: `true`

- `use_sklearn` (boolean)
  - Default: `auto`

- `ml_event_threshold` (integer)
  - Default: `200`

- `simulation_threshold` (integer)
  - Default: `1000`

#### 6.3.4 `experiments` object

Fields:

- `enabled` (boolean)
  - Default: `true`

- `root` (path)
  - Default: `.godspeed-harness/experiments`

- `use_git_worktrees` (boolean)
  - Default: `true`

- `max_parallel_experiments` (integer)
  - Default: `1`

- `cleanup_failed_experiments` (boolean)
  - Default: `false`

#### 6.3.5 `absorption` object

Fields:

- `enabled` (boolean)
  - Default: `true`

- `ingest_root` (path)
  - Default: `ingest/`

- `require_license_check` (boolean)
  - Default: `true`

- `require_pathway` (boolean)
  - Default: `true`

- `require_settlement_plan` (boolean)
  - Default: `true`

#### 6.3.6 `safety` object

Fields:

- `block_unaffordable_actions` (boolean)
  - Default: `false`

- `warn_unaffordable_actions` (boolean)
  - Default: `true`

- `max_payment_burden` (number)
  - Default: implementation-defined.

- `require_human_review_for_absorption` (boolean)
  - Default: `true`

- `require_human_review_for_disintegration` (boolean)
  - Default: `true`

### 6.4 Validation and Error Surface

Error classes:

- `missing_harness_config`
- `harness_parse_error`
- `harness_front_matter_not_a_map`
- `invalid_storage_root`
- `invalid_payment_threshold`
- `unavailable_python_dependency`
- `unavailable_mcp_server`
- `unsupported_storage_format`

Dispatch gating behavior:

- Invalid harness config MUST block new automatic ledger mutations.
- Invalid harness config SHOULD NOT block read-only reports.
- Tool execution that would mutate files SHOULD be blocked if preflight validation fails.

## 7. Configuration Specification

### 7.1 Configuration Resolution Pipeline

Configuration is resolved in this order:

1. Load plugin defaults.
2. Load `.claude-plugin/plugin.json` identity.
3. Load `settings.json` if present.
4. Load `HARNESS.md` if present.
5. Apply environment variable indirection only where explicitly declared.
6. Coerce and validate typed values.
7. Expose typed getters to tools and hooks.

### 7.2 Dynamic Reload Semantics

Dynamic reload is RECOMMENDED.

- Skills are reloaded according to Claude Code plugin reload behavior.
- Harness config SHOULD be re-read by hook scripts and MCP tools before mutating ledgers.
- Invalid reloads MUST NOT corrupt ledger state.
- Last known good config SHOULD be retained.

### 7.3 Preflight Validation

Preflight validation MUST run before:

- Creating a new experiment worktree.
- Writing to settlement ledger.
- Performing absorption proposal generation.
- Performing positive disintegration actions.
- Running ML model training.

Preflight validation SHOULD check:

- Storage root exists or can be created.
- Ledger files are parseable.
- Python dependencies are available.
- Worktree root is under allowed workspace root.
- Safety settings are coherent.

## 8. Runtime State Machine

### 8.1 Desired Direction Lifecycle

States:

1. `Proposed`
2. `Active`
3. `Settling`
4. `Settled`
5. `Dead`
6. `Archived`

Rules:

- `Settled` means the direction has produced consequence.
- `Dead` means the direction no longer generates pressure.
- `Dead` desired directions SHOULD be reviewed for substrate and new affordances.

### 8.2 Affordance Lifecycle

States:

1. `Potential`
   - Imagined but no pathway.

2. `Possibility`
   - Representable with plausible pathway, not yet proven spendable.

3. `Candidate`
   - Under payment/spendability review.

4. `Spendable`
   - Pathway exists and payment is affordable.

5. `InExperiment`
   - Being tested in lab/worktree.

6. `Settled`
   - Consequence accepted by settlement evaluator.

7. `Failed`
   - Settlement failed or payment exceeded capacity.

8. `Archived`
   - No longer relevant.

### 8.3 Capability Lifecycle

States:

1. `Explicit`
   - Known and usable with attention.

2. `Stabilizing`
   - Repeatedly settles across contexts.

3. `Metabolized`
   - Became substrate through settlement + repetition + time.

4. `Retired`
   - No longer demanded or no longer settles.

Rule:

- The system MAY label capability status.
- The system MUST NOT claim true metabolization without evidence of reduced attention burden or repeated reliable settlement.

### 8.4 Experiment Lifecycle

States:

1. `Planned`
2. `WorktreeCreated`
3. `Running`
4. `SettlementPending`
5. `Settled`
6. `Failed`
7. `Absorbed`
8. `Discarded`

### 8.5 Absorption Lifecycle

States:

1. `Discovered`
2. `Potential`
3. `Possibility`
4. `Affordance`
5. `Experimenting`
6. `Settled`
7. `Rejected`
8. `Absorbed`

Rules:

- Absorption MUST NOT copy external systems wholesale by default.
- Absorption SHOULD target the smallest change that captures the largest affordable affordance delta.

## 9. Horizon Review, Scheduling, and Reconciliation

### 9.1 Horizon Review Loop

The harness SHOULD run horizon reviews at these points:

- When a user asks for strategy, planning, architecture, or next steps.
- Before starting an experiment.
- Before absorbing an external system.
- After major settlement events.
- At session stop if hooks are enabled.

Review sequence:

1. Identify desired direction.
2. Identify current horizon.
3. Separate potential, possibility, affordance, capability, and substrate.
4. Estimate payment for candidate affordances.
5. Recommend next affordable affordance.
6. Define settlement criteria.
7. Record expected horizon delta.

### 9.2 Reconciliation

Reconciliation aligns declared state with observed state.

- Affordances without settlement SHOULD be downgraded to possibility.
- Capabilities without repeated settlement SHOULD be downgraded to explicit or candidate status.
- Desired directions that no longer produce pressure SHOULD be marked dead and converted into substrate review.
- Experiments that exceed payment or stall SHOULD be reviewed for disintegration.

### 9.3 Circular Motion Detection

Circular motion is activity without horizon expansion.

Signals:

- Repeated sessions with no increase in capability radius.
- Repeated planning with no settlement.
- High payment burden with low error reduction.
- High generated possibilities but few spendable affordances.

Response:

- Trigger positive disintegration review.
- Reduce scope to a smaller affordable affordance.
- Add settlement criteria.

## 10. Workspace and Local Storage Management

### 10.1 Storage Layout

Default storage root:

```text
.godspeed-harness/
  config/
  ledgers/
    desired_directions.jsonl
    horizons.jsonl
    affordances.jsonl
    payments.jsonl
    settlements.jsonl
    capabilities.jsonl
    substrates.jsonl
    trajectories.jsonl
    disintegrations.jsonl
    absorptions.jsonl
  experiments/
  reports/
  models/
  cache/
```

### 10.2 Storage Safety

- Storage root MUST remain inside the project workspace unless explicitly configured.
- Path traversal MUST be rejected.
- Ledger writes SHOULD use atomic file-write or append-safe logic.
- Corrupt ledgers SHOULD be quarantined and reported.
- Secrets MUST be redacted from events.

### 10.3 Worktree Safety

If Git worktrees are used:

- Worktree paths MUST remain under `experiments.root`.
- Branch names MUST be sanitized.
- External ingest work MUST NOT be added as dependency by default.
- Absorption proposals MUST produce patch plans, not hidden side effects.

## 11. Computational Engine Protocol

### 11.1 Source of Truth

The computational engine exposes deterministic functions. It does not replace judgment. The model interprets tool outputs, but the tools compute stable values.

### 11.2 Python Library Contract

Suggested package:

```text
godspeed_nav/
  __init__.py
  schemas.py
  storage.py
  metrics.py
  trajectory.py
  metabolization.py
  disintegration.py
  absorption.py
  ml.py
  cli.py
```

### 11.3 Core Functions

#### 11.3.1 `compute_error`

Input:

- `desired_state` map
- `observed_state` map
- OPTIONAL weights

Output:

- `error_vector`
- `error_magnitude`
- `dominant_error`

Semantics:

- Computes cybernetic error.
- Used to detect pressure, not final outcome completion.

#### 11.3.2 `estimate_payment`

Input:

- cost dimensions
- weights
- capacity dimensions

Output:

- `payment_burden`
- `capacity_norm`
- `spendability`
- `dominant_cost`

Semantics:

- Uses generalized Pythagorean projection.
- `payment_burden = sqrt(sum((weight_i * cost_i)^2))`.

#### 11.3.3 `score_settlement`

Input:

- before state
- after state
- desired direction
- payment actual
- evaluator config

Output:

- settlement score
- status
- evidence summary

Semantics:

- Records consequence only.
- MUST NOT treat intent as evidence.

#### 11.3.4 `update_trajectory`

Input:

- previous theta
- previous radius
- settlement score
- horizon delta

Output:

- new theta
- new radius
- complex coordinate
- circular motion flags

Semantics:

- Uses Euler projection.
- Radius growth indicates capability/horizon expansion.
- Repeated rotation without radius growth indicates circular motion.

#### 11.3.5 `compute_metabolization`

Input:

- capability ID
- settlement events
- reuse frequency
- context diversity
- stability
- maintenance burden
- attention burden evidence

Output:

- metabolization score
- status recommendation
- missing evidence

Semantics:

- Metabolization is settlement + repetition + time.
- The function recommends a label; it does not declare reality.

#### 11.3.6 `review_absorbability`

Input:

- root project state
- external project state
- desired direction
- capability delta
- license summary

Output:

- absorbability status
- missing pathway
- payment estimate
- settlement plan
- proposed worktree plan

#### 11.3.7 `rank_affordances`

Input:

- candidate affordances
- payment estimates
- expected horizon deltas
- risk estimates

Output:

- ranked affordance list
- next recommended affordance
- rejected candidates with reasons

### 11.4 Scikit-learn Use Thresholds

Use rule-based methods first.

Maturity levels:

1. `<50 settlement events`
   - Use deterministic rules only.
   - Problem: visibility and ledger discipline.

2. `50-200 settlement events`
   - Use Pandas summaries, thresholds, and simple charts.
   - Problem: recurring pattern detection.

3. `200-1000 settlement events`
   - Use Scikit-learn for clustering, anomaly detection, and simple success prediction.
   - Problem: prediction better than rules.

4. `1000+ settlement events`
   - Use cross-validation, model comparison, and next-move ranking.
   - Problem: trajectory optimization.

5. `10000+ settlement events`
   - Consider policy learning or simulation-heavy strategy generation.
   - Problem: discovering new operators or strategies.

Rules:

- ML MUST NOT replace deterministic settlement evaluators early.
- ML SHOULD produce suggestions, not final truth.
- Models MUST be evaluated against held-out settlement history.

## 12. MCP Server Contract

### 12.1 Server Purpose

The MCP server exposes local computation to Claude Code without requiring remote APIs.

### 12.2 Tools

Required if MCP is implemented:

- `cybernetic_nav.compute_error`
- `cybernetic_nav.estimate_payment`
- `cybernetic_nav.score_settlement`
- `cybernetic_nav.update_trajectory`
- `cybernetic_nav.compute_metabolization`
- `cybernetic_nav.rank_affordances`

Recommended:

- `cybernetic_nav.detect_circular_motion`
- `cybernetic_nav.review_absorbability`
- `cybernetic_nav.review_positive_disintegration`
- `cybernetic_nav.write_ledger_event`
- `cybernetic_nav.read_developmental_memory`

### 12.3 Error Handling

Tool errors SHOULD use structured error codes:

- `invalid_input`
- `missing_ledger`
- `corrupt_ledger`
- `unaffordable_action`
- `insufficient_settlement_history`
- `pathway_missing`
- `unsafe_path`
- `dependency_missing`

### 12.4 Security

- MCP tools MUST NOT call external APIs unless explicitly configured.
- MCP tools MUST NOT read arbitrary filesystem paths.
- MCP tools MUST restrict ledger operations to configured storage root.
- MCP tools MUST redact secrets.

## 13. Skill and Agent Protocol

### 13.1 Skill Invocation Contract

Skills should be invoked when the user asks about:

- agent harness design
- Claude Code plugin design
- affordance accounting
- horizon expansion
- metabolization
- capability development
- positive disintegration
- absorption of external systems
- settlement evaluation
- strategy framed as next affordable move

### 13.2 Skill Output Contract

Skill outputs SHOULD include:

- current horizon
- desired direction
- next affordable affordance
- payment estimate
- settlement plan
- metabolization consideration
- risks and blind spots
- next action

### 13.3 Agent Role Contract

If agents are shipped:

- `navigator` SHOULD select next affordable affordance.
- `evaluator` SHOULD score settlement.
- `metabolizer` SHOULD review substrate candidates.
- `absorber` SHOULD inspect external systems.
- `disintegrator` SHOULD identify dissolution targets.

Agents MUST NOT claim they can absorb capabilities without a pathway.

## 14. Failure Model and Recovery Strategy

### 14.1 Failure Classes

1. `Plugin Structure Failures`
   - Missing `.claude-plugin/plugin.json`.
   - Skills placed inside `.claude-plugin/` instead of plugin root.
   - Missing `SKILL.md`.
   - Invalid skill frontmatter.

2. `Harness Config Failures`
   - Invalid `HARNESS.md` YAML.
   - Unknown required config values.
   - Unsafe storage root.

3. `Computation Failures`
   - Missing Python dependencies.
   - Invalid input vectors.
   - Corrupt ledger data.
   - ML attempted before enough settlement history.

4. `Ledger Failures`
   - Write failure.
   - Parse failure.
   - Schema mismatch.
   - Duplicate ID.

5. `Experiment Failures`
   - Worktree creation failure.
   - Test command failure.
   - Payment exceeded estimate.
   - No settlement evidence.

6. `Absorption Failures`
   - Missing pathway.
   - License conflict.
   - External system too large to inspect.
   - Proposed patch fails settlement.

7. `Metabolization Failures`
   - Insufficient repetition.
   - Low context diversity.
   - High maintenance burden.
   - No evidence of attention reduction.

### 14.2 Recovery Behavior

- Plugin structure failures SHOULD be surfaced to the operator with exact path and missing component.
- Config failures SHOULD keep the last known good config.
- Computation failures SHOULD return structured tool errors.
- Ledger failures SHOULD quarantine corrupt records and preserve raw data.
- Experiment failures SHOULD preserve worktree by default unless configured otherwise.
- Absorption failures SHOULD downgrade the external capability to potential or possibility.
- Metabolization failures SHOULD leave the capability explicit or stabilizing.

### 14.3 Partial State Recovery

After restart:

- Load ledgers from storage root.
- Rebuild horizon from latest horizon snapshot and capability records.
- Recompute trajectory summaries if missing.
- Do not assume prior running experiments are still valid.
- Mark interrupted experiments as `settlement_pending` or `failed` depending on evidence.

## 15. Security and Operational Safety

### 15.1 Trust Boundary Assumption

Each implementation defines its trust boundary.

The harness may run agent-generated code, execute hooks, read local ledgers, and create worktrees. This can be dangerous if untrusted inputs are allowed to trigger execution.

Implementations SHOULD document:

- whether the plugin is for trusted local use only;
- whether hooks are enabled;
- whether MCP write tools are enabled;
- whether external API access is disabled or enabled;
- whether human approval is required for absorption/disintegration.

### 15.2 Filesystem Safety

Mandatory:

- Storage root MUST remain under configured project or user-approved root.
- Worktree paths MUST remain under configured experiments root.
- Path traversal MUST be rejected.
- Secrets MUST be redacted from ledgers.

### 15.3 Hook Safety

- Hooks are trusted configuration.
- Hooks SHOULD be minimal and deterministic.
- Hooks SHOULD log start, failure, and timeout.
- Hook outputs SHOULD be truncated in logs.

### 15.4 Absorption Safety

- External code MUST NOT be imported wholesale by default.
- License compatibility SHOULD be reviewed.
- Absorption SHOULD occur via worktree patch proposals.
- Human review SHOULD be required before merging absorption patches.

### 15.5 Doctrine Safety

The framework itself can become dogma.

Implementations MUST include a self-critique pathway that can mark framework assumptions as failed settlement when they stop improving navigation.

## 16. Observability

### 16.1 Structured Logs

Required context fields:

- `event`
- `timestamp`
- `desired_direction_id` when available
- `affordance_id` when available
- `settlement_id` when available
- `capability_id` when available
- `horizon_id` when available

### 16.2 Reports

Recommended reports:

- `horizon_report.md`
- `affordance_report.md`
- `settlement_report.md`
- `metabolization_report.md`
- `positive_disintegration_report.md`
- `absorption_report.md`

### 16.3 Runtime Snapshot

A runtime snapshot SHOULD include:

- active desired directions
- current horizon radius
- visible affordances
- recent settlements
- stabilizing capabilities
- metabolized substrates
- circular motion warnings
- disintegration candidates

## 17. Reference Algorithms

### 17.1 Horizon Review

```text
function horizon_review(context):
  desired_direction = extract_desired_direction(context)
  horizon = load_current_horizon()
  candidates = generate_candidate_transformations(context)

  classified = classify_candidates(candidates, horizon)
  affordances = filter_spendable(classified)

  for affordance in affordances:
    affordance.payment = estimate_payment(affordance)
    affordance.expected_horizon_delta = estimate_horizon_delta(affordance)

  ranked = rank_affordances(affordances)
  return next_affordable_affordance(ranked)
```

### 17.2 Candidate Classification

```text
function classify_candidate(candidate, horizon):
  if candidate cannot be perceived or described:
    return null

  if no pathway exists:
    return Potential

  if pathway is plausible but spendability unknown:
    return Possibility

  if pathway exists and payment is affordable:
    return Affordance

  if repeated settlement exists:
    return Capability

  if repeated settlement + repetition + time reduced attention burden:
    return Substrate
```

### 17.3 Payment Estimate

```text
function estimate_payment(cost_vector, weights, capacity):
  burden = sqrt(sum((weights[i] * cost_vector[i])^2))
  capacity_norm = sqrt(sum(capacity[i]^2))

  if burden <= capacity_norm * 0.7:
    status = affordable
  else if burden <= capacity_norm:
    status = marginal
  else:
    status = unaffordable

  return PaymentEstimate(burden, capacity_norm, status)
```

### 17.4 Settlement Score

```text
function score_settlement(before, after, expected, payment_actual):
  expected_delta = compute_expected_delta(expected)
  observed_delta = compute_observed_delta(before, after)
  burden = estimate_actual_burden(payment_actual)

  if burden == 0:
    score = observed_delta
  else:
    score = observed_delta / burden

  if observed_delta > 0 and score >= threshold:
    status = settled
  else if observed_delta > 0:
    status = partial
  else:
    status = failed

  return SettlementEvent(score, status, evidence)
```

### 17.5 Trajectory Update

```text
function update_trajectory(previous, settlement):
  theta = previous.theta + phase_step
  radius_delta = max(settlement.score, 0) * growth_weight
  radius = previous.radius + radius_delta
  z = radius * exp(i * theta)
  return TrajectoryRecord(theta, radius, real(z), imag(z))
```

### 17.6 Metabolization Review

```text
function metabolization_review(capability):
  reuse = count_successful_reuse(capability)
  diversity = count_distinct_contexts(capability)
  stability = compute_success_stability(capability)
  maintenance = compute_maintenance_burden(capability)
  attention = assess_attention_reduction(capability)
  time = elapsed_time_since_first_settlement(capability)

  if reuse and diversity and stability and attention and time exceed thresholds:
    return metabolized_candidate
  else:
    return stabilizing_or_explicit
```

### 17.7 Positive Disintegration Review

```text
function positive_disintegration_review(system_state):
  stale = find_low_settlement_structures(system_state)
  overfit = find_high_payment_low_delta_structures(system_state)
  substrate = find_metabolized_candidates(system_state)

  return {
    dissolve: stale + overfit,
    metabolize: substrate,
    risks: estimate_disintegration_risks()
  }
```

### 17.8 Absorption Review

```text
function absorption_review(root, external):
  delta = identify_external_capability_delta(root, external)
  pathway = find_pathway(root, delta)

  if pathway missing:
    return Potential(reason="no pathway")

  payment = estimate_payment(pathway.costs)

  if payment unaffordable:
    return Possibility(reason="unaffordable")

  plan = create_minimal_patch_plan(pathway)
  settlement = define_settlement_plan(plan)

  return AbsorptionProposal(status="affordance", plan, settlement)
```

## 18. Test and Validation Matrix

A conforming implementation SHOULD include tests that cover the behaviors defined in this specification.

Validation profiles:

- `Core Conformance`: deterministic tests REQUIRED for conforming implementations.
- `Plugin Conformance`: REQUIRED for Claude Code plugin packaging.
- `Extension Conformance`: REQUIRED only for OPTIONAL features implemented.
- `Real Harness Profile`: environment-dependent checks RECOMMENDED before production use.

### 18.1 Plugin Structure Tests

- `.claude-plugin/plugin.json` exists.
- `plugin.json` contains `name` and `description`.
- Skill directories are under plugin-root `skills/`.
- Each skill contains `SKILL.md`.
- Each `SKILL.md` includes YAML frontmatter with description.
- Large reference content is placed under `references/`.
- Executable deterministic scripts are placed under `scripts/` or plugin-root `bin/`.
- Hooks are placed under plugin-root `hooks/`.
- MCP config is placed at plugin root `.mcp.json` if implemented.

### 18.2 Harness Config Tests

- Missing `HARNESS.md` uses defaults.
- Invalid YAML reports typed error.
- Unknown keys are ignored.
- Storage root path is normalized.
- Unsafe path traversal is rejected.
- `primary_metric` defaults to `horizon_expansion`.
- `outcome_as_terminal` defaults to false.

### 18.3 Domain Model Tests

- Potential cannot be executed as affordance.
- Possibility cannot be metabolized.
- Affordance requires pathway and payment estimate.
- Capability requires repeated settlement.
- Substrate requires evidence of metabolization.
- Desired direction can die and generate new affordance review.

### 18.4 Computation Tests

- `compute_error` produces expected vector and magnitude.
- `estimate_payment` computes weighted norm.
- `score_settlement` rejects intent-only evidence.
- `update_trajectory` increases radius only on positive settlement.
- `detect_circular_motion` flags high activity without radius growth.
- `compute_metabolization` rejects low-diversity repetition.
- Scikit-learn tools refuse to train below configured threshold.

### 18.5 Hook Tests

- User prompt hook extracts desired direction without treating final outcome as terminal.
- Pre-tool hook warns or blocks unaffordable actions.
- Post-tool hook records settlement evidence.
- Stop hook consolidates developmental memory.
- Hook failures do not corrupt ledgers.

### 18.6 Absorption Tests

- External capability without pathway remains potential.
- Unaffordable external capability remains possibility.
- Absorption proposal includes payment estimate.
- Absorption proposal includes settlement plan.
- Absorption worktree path stays under experiment root.
- License review is required when configured.

### 18.7 Positive Disintegration Tests

- Low-settlement structures become dissolution candidates.
- Repeatedly settled low-attention capabilities become metabolization candidates.
- Positive disintegration requires human review when configured.
- Disintegration reports include risk notes.

### 18.8 Observability Tests

- Ledger write events include identifiers and timestamps.
- Reports can be generated from local ledgers.
- Corrupt ledger records are quarantined.
- Secrets are redacted.

### 18.9 Skill Creator Alignment Tests

- Skill descriptions include both trigger context and task purpose.
- Skill eval prompts are realistic and include should-trigger and should-not-trigger cases.
- Eval files are stored under `evals/evals.json`.
- Description optimization can be performed after human review.

## 19. Implementation Checklist

### 19.1 REQUIRED for Core Conformance

- Plugin manifest at `.claude-plugin/plugin.json`.
- At least one skill: `horizon-review`.
- `SKILL.md` frontmatter description.
- Local storage root.
- Domain schemas for desired direction, horizon, affordance, payment, settlement, capability, substrate, and trajectory.
- Deterministic computation for error, payment, settlement, and trajectory.
- Ledger writing and reading.
- Distinction between potential, possibility, affordance, capability, and substrate.
- Horizon review algorithm.
- Self-critique section or skill.
- No external API calls by default.

### 19.2 REQUIRED for Developmental Harness Conformance

- Affordance ledger.
- Settlement ledger.
- Developmental memory.
- Metabolization review.
- Positive disintegration review.
- Circular motion detection.
- Next affordable affordance recommendation.

### 19.3 RECOMMENDED Extensions

- MCP server exposing deterministic tools.
- Hook scripts for lifecycle capture.
- Agent roles.
- Monitors.
- Git worktree experiment lab.
- Absorption engine.
- Scikit-learn prediction after enough settlement events.
- SQLite/DuckDB storage for larger histories.

### 19.4 Operational Validation Before Use

- Run plugin validation.
- Run skill trigger evals.
- Run deterministic computation tests.
- Run one sample horizon review.
- Run one failed settlement case.
- Run one successful settlement case.
- Run one metabolization rejection case.
- Run one absorption rejection case.

## Appendix A. Sample `plugin.json`

```json
{
  "name": "godspeed-agent-harness",
  "description": "A Claude Code plugin for horizon-centric cybernetic navigation: horizon review, affordance accounting, payment estimation, settlement evaluation, metabolization review, positive disintegration, and absorption planning.",
  "version": "0.1.0",
  "author": {
    "name": "Godspeed AI"
  },
  "homepage": "https://example.invalid/godspeed-agent-harness",
  "license": "UNLICENSED"
}
```

## Appendix B. Sample `HARNESS.md`

```markdown
---
harness:
  mode: local
  primary_metric: horizon_expansion
  outcome_as_terminal: false

storage:
  root: .godspeed-harness
  format: jsonl
  redact_secrets: true

computation:
  engine: python
  use_pandas: true
  use_numpy: true
  use_sklearn: auto
  ml_event_threshold: 200
  simulation_threshold: 1000

experiments:
  enabled: true
  root: .godspeed-harness/experiments
  use_git_worktrees: true

absorption:
  enabled: true
  ingest_root: ingest/
  require_license_check: true
  require_pathway: true
  require_settlement_plan: true

safety:
  warn_unaffordable_actions: true
  block_unaffordable_actions: false
  require_human_review_for_absorption: true
  require_human_review_for_disintegration: true
---

# Local Harness Policy

Optimize for horizon expansion, not terminal outcome completion.

Always identify the next affordable affordance visible from the current horizon.

Never claim metabolization without settlement, repetition, and time.
```

## Appendix C. Sample `horizon-review/SKILL.md`

```markdown
---
description: Use this skill whenever the user asks for strategy, planning, next steps, agent harness design, capability formation, affordance accounting, or whether an outcome is actually reachable. This skill converts goals/outcomes into horizon-centric navigation: current horizon, next affordable affordance, payment, settlement, capability, metabolization, and horizon expansion.
---

# Horizon Review

Use this skill to prevent outcome-centric drift.

Always do the following:

1. Translate the user’s stated goal/problem/outcome into a desired direction.
2. Identify the current horizon.
3. Separate potential, possibility, affordance, capability, and substrate.
4. Select the next affordable affordance, not the final destination.
5. Estimate payment and define settlement evidence.
6. Explain what horizon may expand if settlement succeeds.
7. Identify what cannot be absorbed yet.

Never say a capability exists merely because it can be described.
```

## Appendix D. Mathematical Projection Notes

The mathematical projections are computational instruments.

- Pythagorean projection computes payment burden across cost dimensions.
- Euler projection tracks developmental rotation and radius growth.
- Cybernetic projection computes error and feedback.

The harness MUST NOT claim that reality literally obeys these equations.

## Appendix E. Official Documentation Alignment

This specification aligns with these official or primary sources:

- Claude Code plugin documentation: https://code.claude.com/docs/en/plugins
- Claude Code skills documentation: https://code.claude.com/docs/en/skills
- Anthropic Skill Creator guidance: https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md

