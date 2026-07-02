# Outcome-to-Code Map: Godspeed Agent Harness

## 1. Executive Summary

| Field | Value |
|-------|-------|
| **Repo name** | `godspeed-agent-harness` (directory: `godspeed_agent`) |
| **Audit date** | 2026-06-14 |
| **Languages/frameworks** | Python 3.11+, Node.js (RuVector sidecar), JSONL storage, numpy/pandas, optional scikit-learn |
| **Main purpose** | Local-first horizon-centric cybernetic navigation harness packaged as a Claude Code plugin — turns desired directions into horizon checks, affordance review, payment estimates, settlement events, developmental memory, and runtime validation |
| **Outcomes found** | 25 |
| **Implemented** | 18 |
| **Partially implemented** | 4 |
| **Declared only** | 1 |
| **Config only** | 1 |
| **Contradicted** | 0 |
| **Unclear** | 1 |

**Top 5 risks:**

1. **No real settlement history exists.** The `ledgers/` root directory is empty. `.godspeed-harness/` contains only validation scratch directories. The system has never been exercised through actual agent navigation — all evidence is self-referential (the system validates itself).
2. **Hooks are observability-only, not enforcement.** `hooks/pre_tool_use.py` always exits 0 and outputs JSON; it does not block tools at the Claude Code level. Policy enforcement exists inside `review_horizon` but not at the hook boundary.
3. **Default policy warns rather than blocks unaffordable actions.** `HARNESS.md` has `block_unaffordable_actions: false`. The runtime rejects unaffordable candidates from becoming affordances, but the default posture is warn-only.
4. **No explicit developmental state-machine enforcement.** The spec defines a 13-state machine with transition triggers (Section 7), but there are no guards preventing out-of-order operations (e.g., calling `record_settlement` without `review_horizon`).
5. **Calibration evidence is external proxy data, not local capability proof.** The calibration pipeline streams HuggingFace agent-trajectory datasets. This is explicitly acknowledged in docs but could be misread as proof of local capability.

---

## 2. Method

### Files/directories inspected

- **Root docs**: `README.md`, `AGENTS.md`, `HARNESS.md`, `CURRENT_STATE.md`, `pyproject.toml`, `Godspeed_Agent_Harness_SPEC.md` (partial, 200 lines)
- **Plan docs**: `docs/plans/specs/2026-05-30-cognitive-operating-system-spec.md` (full, 918 lines), `docs/plans/2026-05-30-cognitive-operating-system-bridge-plan.md` (full, 701 lines), `docs/plans/2026-05-29-enterprise-hardening.md` (full), `docs/plans/2026-06-03-cognitive-model-computational-core.md` (full, 868 lines)
- **Reference docs**: `docs/references/cli-reference.md`, `policy-reference.md`, `ledger-reference.md`
- **Workflow docs**: `docs/run-scoped-evidence-workflow.md`
- **Core runtime** (all fully read): `godspeed_nav/runtime.py` (598 lines), `cli.py` (302), `storage.py` (404), `metrics.py` (282), `policies.py` (87), `validation.py` (323), `cognitive_model.py` (439), `ml.py` (392), `reports.py` (130), `absorption.py` (60), `disintegration.py` (46), `metabolization.py` (53), `trajectory.py` (47), `ruvector_bridge.py` (63)
- **Hooks** (all fully read): `common.py`, `pre_tool_use.py`, `post_tool_use.py`, `stop.py`, `hooks.json`
- **MCP**: `mcp/cybernetic_nav_server/server.py` (209 lines), `mcp/cybernetic-nav-server/server.py` (shim), `.mcp.json`
- **Plugin**: `.claude-plugin/plugin.json`
- **Schemas**: All 9 JSON schemas in `schemas/`
- **State**: `state/current_state.json`, `state/*.jsonl` (line counts)
- **Storage inspection**: `.godspeed-harness/` directory tree, `ledgers/` root directory
- **Tests**: File listing (24 test files), collection count (538 tests)
- **Scripts**: File listing of `scripts/settlement_datasets/` (38 modules) and `scripts/agenttrove/` (9 modules)

### Commands run

- `git log --oneline -10`, `git status`
- `find` over all source directories
- `grep` for `TODO|FIXME|XXX|HACK|NotImplemented|placeholder|stub|pytest.mark.skip|pytest.mark.xfail` → 2 matches (both ABC abstract methods, correct)
- `uv run pytest --co -q` → 538 tests collected

### Tools used

Direct file reads, `grep`, `find`, `ast_grep` (available but not needed — manual reads sufficed), `uv run pytest --co`.

### Limitations

- The full test suite was NOT executed (only collection). The CURRENT_STATE.md claims 536 passing; 538 are now collected.
- `scripts/settlement_datasets/` modules (38 files) were not individually read — the calibration pipeline was assessed through entrypoints, configs, and CURRENT_STATE.md evidence.
- `tmp/cogos.md` (doctrine manifesto, 57KB) and `tmp/math.md` (mathematical model, 58KB) were not fully read — outcomes were extracted from plans/specs that reference them.
- `agentic_capability_loop/` module (containing `adapters.py` and untracked `learning_proposals.py`) was not deeply inspected.

### Areas not inspected and why

- `evals/agenttrove/*.jsonl` — eval fixture data, not implementation
- `data/settlement_datasets/runs/*` — calibration run artifacts, not implementation
- `tmp/pilot_tasks/*` — pilot task scaffolding, not core harness
- Individual test function bodies — assessed via file structure and grep, not line-by-line

---

## 3. Outcome Inventory

| ID | Outcome | Actor/User | Status | Confidence | Primary Evidence |
| -- | ------- | ---------- | ------ | ---------- | ---------------- |
| OUT-001 | Converts desired-direction language into an explicit navigation loop | Agent / developer | implemented | high | `runtime.py::NavigationRuntime` |
| OUT-002 | Distinguishes potentials, possibilities, affordances, capabilities, and substrate as separate runtime states | Agent / developer | implemented | high | `runtime.py::review_horizon` |
| OUT-003 | Treats affordances as spendable paths with preconditions and transition sequences, not merely destinations | Agent | implemented | high | `runtime.py::review_horizon` → `affordance_paths` ledger |
| OUT-004 | Records payment, settlement, trajectory, and developmental memory in durable local ledgers with checksums | Operator / downstream system | implemented | high | `storage.py::LedgerStore` |
| OUT-005 | Enforces representational path dependency and blocks unearned opposition jumps | Agent | implemented | high | `metrics.py::review_representational_transition` |
| OUT-006 | Exposes CLI, hooks, MCP, and validation surfaces wired to the runtime | Developer / operator | implemented | high | `cli.py`, `hooks/*.py`, `mcp/.../server.py` |
| OUT-007 | Keeps predictive/ML extensions dormant until settlement-history thresholds are met | Operator | implemented | high | `ml.py::build_predictive_extension_plan` |
| OUT-008 | Implements deterministic computational model (burden kernel, hard gates, spendability, controller ranking) | Developer | implemented | high | `cognitive_model.py` |
| OUT-009 | Records model calibration fields on settlement for future weight fitting | Developer / researcher | implemented | high | `runtime.py::record_settlement` → `model_calibration` |
| OUT-010 | Runs runtime-owned self-critique with falsification surfaces | Agent / operator | implemented | high | `runtime.py::review_self_critique` |
| OUT-011 | Enterprise-readiness validation that can fail when structure drifts | Operator | implemented | high | `validation.py::validate_enterprise_readiness` |
| OUT-012 | Operates local-first with no external API calls by default | Operator | implemented | high | `HARNESS.md`, `storage.py`, no external imports in core |
| OUT-013 | Redacts secrets in storage and logs | Operator / security | implemented | high | `storage.py::_redact` |
| OUT-014 | Reviews absorption with license, pathway, settlement plan, and human-review gate | Developer / operator | implemented | high | `absorption.py::review_absorbability` |
| OUT-015 | Reviews positive disintegration with dissolution, salvage, and human-review gate | Developer / operator | implemented | high | `disintegration.py::review_positive_disintegration` |
| OUT-016 | Answers developmental-memory lineage queries (paid paths, failed settlements, substrate, revised critiques) | Agent / operator | implemented | high | `storage.py::query_developmental_memory` |
| OUT-017 | Provides semantic search over developmental memory via local RuVector | Agent / operator | implemented | medium | `storage.py::search_developmental_memory`, `ruvector_bridge.py` |
| OUT-018 | Schedules repetition as runtime behavior under variation with critique escalation | Agent | implemented | high | `runtime.py::_schedule_repetition`, `metabolization.py::plan_repetition` |
| OUT-019 | Tracks capability lifecycle through latent → active → repeated → metabolized → brittle → retired | Developer / operator | implemented | high | `schemas.py::infer_capability_lifecycle`, `reports.py` |
| OUT-020 | Blocks unaffordable actions at the hook boundary before tool execution | Agent / operator | partially_implemented | high | `hooks/pre_tool_use.py` (observability-only), `HARNESS.md::block_unaffordable_actions: false` |
| OUT-021 | Enforces developmental state-machine ordering (13 states with transition guards) | Agent / runtime | partially_implemented | medium | `docs/plans/specs/...spec.md` §7 (declared), no explicit guard in `runtime.py` |
| OUT-022 | Emits runtime events (onSettlementRecorded, onHorizonChecked, etc.) for observability subscribers | Downstream system | partially_implemented | medium | Spec §10.4 declares events; ledgers record data but no pub/sub |
| OUT-023 | Has been exercised through real agent navigation with actual settlement history | Operator / auditor | declared_only | high | `ledgers/` empty, `.godspeed-harness/` validation-only |
| OUT-024 | Blocks unaffordable actions by default (not just warns) | Agent / operator | config_only | high | `HARNESS.md::block_unaffordable_actions: false` |
| OUT-025 | Maintains identity state as metabolized history (active directions, capabilities, substrate, lock-in risks) | Agent / operator | implemented | high | `reports.py::identity_state`, `runtime.py::cognitive_surfaces` |

---

## 4. Detailed Outcome Maps

### OUT-001 — Explicit Navigation Loop

**Outcome statement:** The system converts desired-direction language into an explicit navigation loop: start direction → review horizon → identify affordance → estimate payment → record settlement → update trajectory → review metabolization → schedule repetition.

**Actor/User:** Agent / developer invoking the CLI or runtime.

**Settlement / success criterion:** A full cycle through `start-direction` → `review-horizon` → `record-settlement` writes consistent records across `desired_directions`, `horizons`, `horizon_reviews`, `affordances`, `affordance_paths`, `payments`, `settlements`, `trajectories`, `capabilities`, and `repetition_schedules` ledgers.

**Status:** `implemented`

**Confidence:** `high`

**Declared evidence:**
- `README.md::Core Workflow` — lists the 8-step loop
- `docs/plans/specs/2026-05-30-cognitive-operating-system-spec.md::§7 Developmental State Machine` — defines 13 states with transition triggers
- `docs/plans/2026-05-29-enterprise-hardening.md::Phase 1` — describes runtime orchestration foundation

**Implementation evidence:**
- `godspeed_nav/runtime.py::NavigationRuntime` (598 lines) — `start_direction`, `review_horizon`, `record_settlement`, `set_representational_state`, `review_representational_transition`, `cognitive_surfaces`, `review_self_critique`, `snapshot`
- `godspeed_nav/cli.py::run` — dispatches 18 commands to runtime methods

**Test evidence:**
- `tests/test_runtime_workflow.py` — exercises full runtime cycle (file exists, test names visible in collection)
- `tests/test_cli_hooks_mcp.py` — CLI integration tests

**Runtime path:** CLI `start-direction` → `NavigationRuntime.start_direction` (writes `desired_directions` + `horizons`) → CLI `review-horizon` → `NavigationRuntime.review_horizon` (writes `payments`, `affordances`, `affordance_paths`, `horizon_reviews`) → CLI `record-settlement` → `NavigationRuntime.record_settlement` (writes `settlements`, `trajectories`, `capabilities`, `repetition_schedules`)

**Missing links / gaps:**
- No explicit state-machine guard prevents out-of-order invocation (see OUT-021).

**Reviewer notes:** Inspect `tests/test_runtime_workflow.py` to confirm full-cycle assertions. Run a live `start-direction → review-horizon → record-settlement → developmental-report` cycle in a clean workspace.

---

### OUT-002 — Five-State Affordance Classification

**Outcome statement:** The system distinguishes potentials, possibilities, affordances, capabilities, and substrate as separate runtime states with explicit classification criteria.

**Actor/User:** Agent reviewing what is visible vs spendable.

**Settlement / success criterion:** A candidate without a pathway is classified as `potential`; a candidate with a pathway but unaffordable payment is classified as `possibility`; an affordable candidate with a pathway is classified as `affordance`; repeated settlement promotes to `capability`; metabolized capability becomes `substrate`.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/runtime.py::review_horizon` — lines 100-178: candidates without `pathway` → `potentials` ledger; unaffordable → `possibilities` ledger; affordable → `affordances` + `affordance_paths` ledgers
- `godspeed_nav/runtime.py::_update_capability_evidence` — builds `capabilities` ledger with lifecycle states
- `godspeed_nav/metabolization.py::compute_metabolization` — evaluates 6 factors, `substrate_candidate` at score ≥ 0.75

**Test evidence:**
- `tests/test_runtime_workflow.py` — exercises candidate classification

**Runtime path:** `review_horizon` loops candidates, checks `pathway` presence → `estimate_payment` → checks `spendability` → classifies and persists to appropriate ledger.

**Missing links / gaps:** None material.

---

### OUT-003 — Affordances as Spendable Paths

**Outcome statement:** The system treats affordances as spendable paths with required preconditions, transition sequences, expected settlement, and lifecycle status — not merely ranked destinations.

**Actor/User:** Agent deciding what to do next.

**Settlement / success criterion:** `review_horizon` produces `affordance_paths` records containing `required_preconditions`, `transition_sequence`, `expected_settlement`, `lifecycle_status`, and `pathway_quality`.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/runtime.py::review_horizon` lines 158-177 — persists `affordance_paths` with all specified fields
- `godspeed_nav/metrics.py::rank_affordances` — ranks by `expected_horizon_delta * pathway_quality / (burden * (1 + risk))`

**Declared evidence:**
- `docs/plans/2026-05-30-cognitive-operating-system-bridge-plan.md::Milestone 4` — "Replace Flat Horizon Candidates With Explicit Affordance Paths"

---

### OUT-004 — Durable Local Ledgers with Checksums

**Outcome statement:** The system records payment, settlement, trajectory, and developmental memory in local JSONL ledgers with file locking, SHA-256 checksums, event envelopes, sequence numbers, indexes, quarantine for corrupt records, and backup/export.

**Actor/User:** Operator / downstream system needing persistent, auditable evidence.

**Settlement / success criterion:** `append_event` writes enveloped records with `schema_version`, `sequence`, `timestamp`, `ledger`, `record`, `checksum`. `read_events` validates checksums and quarantines corrupt lines. `export_backup` produces a portable snapshot.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/storage.py::LedgerStore` (404 lines) — `append`, `read`, `append_event`, `read_events`, `read_event_by_record_id`, `export_backup`, `migration_status`, `query_developmental_memory`, `search_developmental_memory`
- `_lock_handle` uses `fcntl.flock(LOCK_EX)` for concurrency safety
- `_checksum` uses SHA-256 over canonical JSON
- `_write_quarantine` isolates corrupt records
- `_update_index` maintains per-record lookup index
- `_redact` redacts secret keys (`api_key`, `password`, `token`, etc.)

**Test evidence:**
- `tests/test_enterprise_storage.py` — storage durability tests
- `tests/test_domain_storage.py` — domain ledger tests

---

### OUT-005 — Opposition-Jump Blocking

**Outcome statement:** The system enforces representational path dependency by blocking unearned opposition jumps between representational states unless a metabolized shortcut exists.

**Actor/User:** Agent attempting a representational transition.

**Settlement / success criterion:** A transition with `phase_gap == 2` (opposition jump) that is not in `metabolized_shortcuts` returns `status: "blocked"` with `code: "blocked_opposition_jump"` and recommended adjacent phases.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/metrics.py::review_representational_transition` lines 236-252 — blocks opposition jumps, recommends adjacent phases
- `godspeed_nav/policies.py::enforce_representational_transition_policy` — blocks when `status == "blocked"`
- `godspeed_nav/runtime.py::review_representational_transition` — persists blocked transitions to `representational_transitions` ledger

**Declared evidence:**
- `docs/plans/2026-05-30-cognitive-operating-system-bridge-plan.md::Milestone 3` — "Implement Representational Transition Policy And Opposition-Jump Blocking"

**Test evidence:**
- `tests/test_computation.py` — transition computation tests
- `tests/test_policy_gates.py` — policy enforcement tests

---

### OUT-006 — CLI, Hooks, MCP, and Validation Surfaces

**Outcome statement:** The system exposes operator-grade CLI, hooks, MCP tools, and an enterprise-readiness validation command, all wired to the core runtime.

**Actor/User:** Developer / operator / Claude Code integration.

**Settlement / success criterion:** CLI has 18 commands dispatching to real runtime functions. 4 hooks read JSON from stdin and record to ledgers. MCP server exposes 21 tools dispatching to runtime functions. `validate` runs 15+ checks and can fail.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/cli.py::build_parser` — 18 subcommands, all with `run()` dispatch
- `hooks/hooks.json` — registers `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`
- `hooks/pre_tool_use.py`, `post_tool_use.py`, `stop.py`, `user_prompt_submit.py` — all call `godspeed_nav.*` functions
- `mcp/cybernetic_nav_server/server.py::TOOL_NAMES` — 21 tools, `call_tool` dispatches to runtime
- `godspeed_nav/validation.py::validate_enterprise_readiness` — 15+ checks

**Missing links / gaps:**
- `.mcp.json` references `mcp/cybernetic-nav-server/server.py` (hyphen) which is a 10-line shim to `mcp/cybernetic_nav_server/server.py` (underscore, real implementation). Works but fragile.
- `hooks/pre_tool_use.py` always returns exit code 0 — it is observability, not enforcement (see OUT-020).

---

### OUT-007 — ML/Predictive Threshold Gating

**Outcome statement:** The system keeps predictive and ML extensions dormant until settlement-history thresholds are met (`ml_event_threshold: 200`, `simulation_threshold: 1000`), and even when active, predictions remain advisory — never overriding deterministic gates.

**Actor/User:** Operator / researcher.

**Settlement / success criterion:** Below 200 settlements, `predictive-extensions` returns `stage: "deterministic_only"` with empty `ml_predictions`. Above 200 but below 1000, returns `stage: "ml_assisted"`. Above 1000, returns `stage: "simulation_assisted"`.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/ml.py::build_predictive_extension_plan` lines 295-338 — stage logic based on `settlement_event_count` vs thresholds
- `godspeed_nav/ml.py::SklearnPredictiveModelAdapter` — lazy `import sklearn` inside `_require_sklearn()`; returns empty predictions with explanatory note if calibration data insufficient
- `godspeed_nav/ml.py::run_predictive_extensions` — reads settlements from ledger, resolves provider from config

**Declared evidence:**
- `HARNESS.md` — `ml_event_threshold: 200`, `simulation_threshold: 1000`, `model_provider: heuristic`
- `docs/plans/2026-06-03-cognitive-model-computational-core.md::Task 7` — sklearn provider behind evidence gate

**Test evidence:**
- `tests/test_computation.py` — sklearn provider threshold-gating tests (visible in collection)

---

### OUT-008 — Deterministic Computational Model

**Outcome statement:** The system implements a deterministic computational model layer from the math specification: representational burden kernel (quadratic form), hard gates (governance, settlement access, payment capacity, risk ceilings, debt ceilings), spendability scoring (visibility, reachability, payment fit, capability support), and advisory controller ranking.

**Actor/User:** Developer / runtime decision support.

**Settlement / success criterion:** `compute_representational_burden` returns delta, burden, burden_max, scope_overflow using a strictly positive-definite matrix. `evaluate_candidate_model` blocks on hard gates before scoring. `rank_candidates_by_controller` ranks allowed candidates by objective function without overriding gates.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/cognitive_model.py` (439 lines) — `RepresentationalCoordinates`, `BurdenParameters`, `compute_representational_burden`, `evaluate_candidate_model`, `rank_candidates_by_controller`, `build_calibration_frame`
- `RISK_CEILINGS` and `DEBT_CEILINGS` by context (`exploration`, `production`, `recovery`, `safety_critical`)
- `SPENDABILITY_WEIGHTS` — visibility 0.20, reachability 0.25, payment_fit 0.35, capability_support 0.20
- `CONTROLLER_WEIGHTS` — burden 0.5, risk 1.5, debt 0.8, horizon_gain 0.3, direction 0.5
- `godspeed_nav/runtime.py::review_horizon` lines 187-214 — calls `rank_candidates_by_controller` in advisory mode

**Declared evidence:**
- `docs/plans/2026-06-03-cognitive-model-computational-core.md` — 8-task implementation plan
- `README.md::Computational Model Layer`

---

### OUT-009 — Settlement Calibration Fields

**Outcome statement:** The system records model calibration fields on each settlement event (predicted vs actual payment, settlement success/score, horizon delta, risk/debt estimates) for future weight fitting.

**Actor/User:** Researcher / developer calibrating the model.

**Settlement / success criterion:** Every settlement record includes a `model_calibration` object with `payment_predicted`, `payment_actual`, `settlement_success`, `settlement_score`, `horizon_delta`, `risk_estimate`, `debt_estimate`.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/runtime.py::record_settlement` lines 408-416 — includes `model_calibration` object in settlement record
- `godspeed_nav/cognitive_model.py::build_calibration_frame` lines 375-439 — extracts calibration fields to pandas DataFrame with 14 columns including `tool_diversity_count`, `error_recovery_ratio`, `action_observation_ratio`

---

### OUT-010 — Runtime Self-Critique

**Outcome statement:** The system runs runtime-owned self-critique that detects dead-end directions (settlement without horizon expansion), circular motion (rotation outpacing radial growth), and simulation misread as capability evidence.

**Actor/User:** Agent / operator reviewing system health.

**Settlement / success criterion:** `review_self_critique` produces critique findings with codes `dead_end_direction`, `circular_motion`, `simulation_is_not_capability` and persists them to `critique_findings` ledger.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/runtime.py::review_self_critique` lines 277-346 — detects all three failure modes, persists findings
- `godspeed_nav/trajectory.py::detect_circular_motion` — `rotation >= math.tau and radius_growth <= 0.1`
- `hooks/stop.py` — calls `review_self_critique` on session stop

**Declared evidence:**
- `docs/plans/2026-05-30-cognitive-operating-system-bridge-plan.md::Milestone 9` — "Runtime-Owned Self-Critique And Falsification Surfaces"

---

### OUT-011 — Enterprise-Readiness Validation

**Outcome statement:** The system runs an enterprise-readiness audit across package structure, config, storage, hooks, MCP, runtime workflow, reports, and cognitive-OS conformance — and can FAIL when structure drifts.

**Actor/User:** Operator / CI pipeline.

**Settlement / success criterion:** `validate` returns `{"status": "pass"}` only when ALL checks pass. Any missing file, config mismatch, or runtime failure produces `{"status": "fail"}`.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/validation.py::validate_enterprise_readiness` (323 lines) — 15 checks: `plugin_structure`, `config`, `predictive_extensions`, `storage`, `developmental_memory`, `self_critique`, `public_cognitive_surfaces`, `runtime_workflow`, `mcp`, `reports`, `cognitive_os_conformance`, `hooks`, `agents`, `cognitive_runtime_bridge`
- Lines 314-318: `status = "pass" if all(check["status"] == "pass" ...) else "fail"`
- Uses scratch `tempfile.TemporaryDirectory` for sample workflow so it does not pollute target storage

**Test evidence:**
- `tests/test_validation.py::test_validate_enterprise_readiness_checks_core_surfaces`
- `tests/test_validation.py::test_cli_validate_outputs_pass_status`
- `tests/test_validation.py::test_validate_enterprise_readiness_does_not_mutate_target_storage`

---

### OUT-012 — Local-First, No External API by Default

**Outcome statement:** The system operates local-first with no external API calls in the core runtime. MCP tools and hooks operate on local input, local computation, and configured local storage.

**Actor/User:** Operator concerned about data sovereignty.

**Settlement / success criterion:** No HTTP/network imports in `godspeed_nav/` core. Storage is local JSONL. RuVector runs as local Node sidecar.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/` — no `requests`, `httpx`, `urllib`, or network calls in core modules
- `godspeed_nav/ruvector_bridge.py` — calls local `node` subprocess, not a remote API
- `HARNESS.md` — `mode: local`

**Declared evidence:**
- `README.md::Implementation-defined Behavior` — "No external API calls by default."

**Missing links / gaps:**
- `scripts/settlement_datasets/hf_stream.py` uses the `datasets` library to stream from HuggingFace, but this is in the calibration pipeline (scripts/), not the core runtime. The `datasets` dependency is in `pyproject.toml`.

---

### OUT-013 — Secret Redaction

**Outcome statement:** The system redacts secrets in storage and logs using a known set of sensitive keys.

**Actor/User:** Security / operator.

**Settlement / success criterion:** Records containing keys like `api_key`, `password`, `token`, `secret` have their values replaced with `[REDACTED]` before persistence.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/storage.py::SECRET_KEYS` — `{"api_key", "apikey", "authorization", "password", "secret", "token"}`
- `godspeed_nav/storage.py::_redact` — recursive redaction for dict/list/scalar
- `LedgerStore.__init__` — `redact_secrets=True` by default

---

### OUT-014 — Absorption Review

**Outcome statement:** The system reviews whether an external capability is absorbable by checking pathway presence, license compatibility, and enforcing human review, with an explicit settlement plan.

**Actor/User:** Developer considering absorbing an external library/capability.

**Settlement / success criterion:** `review_absorbability` returns `absorbability_status` of `potential` (no pathway), `blocked` (incompatible license), or `absorbable` (pathway + compatible license), with `required_human_review` from policy.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/absorption.py::review_absorbability` (60 lines) — checks pathway, license, enforces policy, generates settlement plan and worktree plan
- `godspeed_nav/policies.py::enforce_absorption_review` — `requires_review` when `require_human_review_for_absorption: true` (default)

---

### OUT-015 — Positive Disintegration Review

**Outcome statement:** The system reviews structures for positive disintegration: identifies dissolution candidates (low settlement score), metabolization candidates (high score + low burden + enough repetitions), salvageable elements, and blocks high-risk dissolution without human review.

**Actor/User:** Developer / operator reviewing what should dissolve vs persist.

**Settlement / success criterion:** `review_positive_disintegration` separates blocked, dissolution, and metabolization candidates, generates a salvage plan, and enforces human review for high-risk items.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/disintegration.py::review_positive_disintegration` (46 lines) — classifies structures, generates salvage plan, enforces policy

---

### OUT-016 — Developmental Memory Lineage Queries

**Outcome statement:** The system answers developmental-history lineage questions: what path was paid for, what failed to settle, which capabilities became substrate, which critique findings revised later behavior.

**Actor/User:** Agent / operator asking "how did this system become what it is?"

**Settlement / success criterion:** `query_developmental_memory` returns `paid_paths`, `failed_settlements`, `substrate_capabilities`, `revised_critique_findings`.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/storage.py::query_developmental_memory` lines 191-222 — reads payments, settlements, capabilities, critique_findings; returns four lineage keys
- `godspeed_nav/runtime.py::read_developmental_memory` — delegates to store
- `godspeed_nav/validation.py` — checks lineage keys match expected set

---

### OUT-017 — Semantic Memory Search via RuVector

**Outcome statement:** The system provides local semantic search over structured developmental-memory summaries using RuVector (settlement summaries and critique findings, not raw traces).

**Actor/User:** Agent needing recall over prior settlement patterns.

**Settlement / success criterion:** `search-developmental-memory --query "..."` returns ranked results from local RuVector index.

**Status:** `implemented`

**Confidence:** `medium`

**Implementation evidence:**
- `godspeed_nav/storage.py::search_developmental_memory` — builds documents from settlements + critique_findings, calls bridge
- `godspeed_nav/ruvector_bridge.py::search_documents` — subprocess to Node, validates node/npm/ruvector availability
- `tools/ruvector/search_memory.cjs` — Node sidecar script

**Missing links / gaps:**
- Requires `npm install` in `tools/ruvector/` (not automatic)
- Returns empty results when no documents have `summary` or `finding` fields — depends on settlement record shape

---

### OUT-018 — Repetition Scheduling

**Outcome statement:** The system schedules repetition as runtime behavior after successful but non-metabolized settlement, tracking variation coverage and escalating to critique on circular motion.

**Actor/User:** Agent managing capability formation.

**Settlement / success criterion:** After `record_settlement`, a `repetition_schedules` record is created with `status: "scheduled"` (or `"satisfied"` if substrate candidate), `variation_coverage`, and `critique_escalation` when circular motion is detected.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/runtime.py::_schedule_repetition` lines 555-597 — creates schedule unless substrate_candidate
- `godspeed_nav/metabolization.py::plan_repetition` — returns schedule with trigger, next_condition, critique_escalation

---

### OUT-019 — Capability Lifecycle Tracking

**Outcome statement:** The system tracks capability lifecycle through `latent → active → repeated → metabolized → brittle → retired`.

**Actor/User:** Developer / operator reviewing capability maturity.

**Settlement / success criterion:** `reports.py` lifecycle_counts includes all 6 states. `infer_capability_lifecycle` assigns the correct state based on settlement_count, stability, metabolization_score.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/schemas.py::infer_capability_lifecycle` — referenced by runtime and reports
- `godspeed_nav/reports.py` lines 47-62 — counts all 6 lifecycle states
- `godspeed_nav/runtime.py::_update_capability_evidence` — computes settlement_count, stability, metabolization_score

---

### OUT-020 — Hook-Level Blocking of Unaffordable Actions

**Outcome statement:** The system blocks unaffordable actions at the hook boundary before tool execution.

**Actor/User:** Agent attempting a tool call that exceeds payment capacity.

**Settlement / success criterion:** When `pre_tool_use.py` determines a candidate is unaffordable AND blocking is enabled, the tool call is prevented from executing.

**Status:** `partially_implemented`

**Confidence:** `high`

**Declared evidence:**
- `docs/references/policy-reference.md::block_unaffordable_actions` — "unaffordable candidates are blocked instead of merely warned"

**Implementation evidence:**
- `hooks/pre_tool_use.py` — estimates payment, enforces policy, classifies candidate status, records to `tool_payments` ledger, outputs JSON with `decision`
- `godspeed_nav/policies.py::enforce_payment_policy` — returns `block` when `block_unaffordable_actions: true` and payment is unaffordable

**Missing links / gaps:**
- **`hooks/pre_tool_use.py` always returns exit code 0** (line 67: `return 0`). Claude Code hooks block by exiting non-zero or by outputting a specific JSON shape. This hook outputs the decision as data but does not actually prevent tool execution. The hook is **observability-only**, not enforcement.
- `HARNESS.md` has `block_unaffordable_actions: false` by default, so even the policy decision is `warn`, not `block`.

**Reviewer notes:** Determine whether Claude Code's hook framework interprets the output JSON's `"decision": "block"` as a blocking signal. If not, the hook cannot enforce payment policy at the tool boundary. The runtime's `review_horizon` does reject unaffordable candidates from becoming affordances, but this only applies when the agent explicitly goes through `review_horizon`.

---

### OUT-021 — Developmental State-Machine Enforcement

**Outcome statement:** The system enforces a 13-state developmental state machine with transition triggers, preventing out-of-order operations.

**Actor/User:** Agent / runtime ensuring developmental ordering.

**Settlement / success criterion:** The runtime refuses operations that violate state ordering (e.g., `record_settlement` before `review_horizon`, or `review_horizon` before `start_direction`).

**Status:** `partially_implemented`

**Confidence:** `medium`

**Declared evidence:**
- `docs/plans/specs/2026-05-30-cognitive-operating-system-spec.md::§7 Developmental State Machine` — defines 13 states (`DirectionSelected` through `SelfCritiqued`) and transition triggers

**Implementation evidence:**
- `godspeed_nav/runtime.py` — implements all the ACTIONS corresponding to states but does NOT guard against out-of-order invocation
- `godspeed_nav/runtime.py::record_settlement` — can be called with any `affordance_id` even if no prior `review_horizon` created that affordance

**Missing links / gaps:**
- No state-machine guard: the runtime trusts the caller to invoke methods in the correct order. A caller could call `record_settlement` without ever calling `start_direction` or `review_horizon`.

---

### OUT-022 — Runtime Event Emission

**Outcome statement:** The system emits runtime events (`onSettlementRecorded`, `onHorizonChecked`, `onAffordancePathSelected`, etc.) for observability subscribers.

**Actor/User:** Downstream monitoring / dashboard system.

**Settlement / success criterion:** External subscribers can receive notifications when runtime state transitions occur.

**Status:** `partially_implemented`

**Confidence:** `medium`

**Declared evidence:**
- `docs/plans/specs/2026-05-30-cognitive-operating-system-spec.md::§10.4 Emitted Runtime Events` — lists 11 event types

**Implementation evidence:**
- Ledgers serve as an append-only event log (each `append_event` is an event), but there is no pub/sub, callback, or observer pattern
- Hooks respond to Claude Code lifecycle events, not internal runtime events

**Missing links / gaps:**
- No event dispatcher, no subscriber registration, no webhook emission. Events are recorded but not emitted.

---

### OUT-023 — Real Settlement History from Actual Navigation

**Outcome statement:** The system has been exercised through real agent navigation work, producing actual settlement history that demonstrates the developmental loop in practice.

**Actor/User:** Operator / auditor validating the system works in production.

**Settlement / success criterion:** `ledgers/` contains real settlement records from actual agent navigation (not validation scratch).

**Status:** `declared_only`

**Confidence:** `high`

**Declared evidence:**
- `state/current_state.json::next_steps` — "Use the harness in real agent work, collect real settlement history"
- `CURRENT_STATE.md::Next Spendable Affordance` — "Continue using the harness in real agent work"

**Implementation evidence:**
- `ledgers/` root directory: **EMPTY** (only `README.md`)
- `.godspeed-harness/`: contains ONLY validation scratch directories (`final-validation*`, `cognitive-os-validation`, `cognitive-model-validation`, etc.) — no real developmental memory
- `state/milestones.jsonl`: 78 records about **building the harness itself**, not about using it for navigation

**Missing links / gaps:**
- This is the single most important gap. The system is extensively tested and self-validating but has zero real-world settlement evidence. All claims of capability rest on test evidence, not use evidence.

---

### OUT-024 — Block Unaffordable Actions by Default

**Outcome statement:** The system blocks unaffordable actions by default (not just warns).

**Actor/User:** Agent / operator.

**Settlement / success criterion:** `block_unaffordable_actions: true` in default config.

**Status:** `config_only`

**Confidence:** `high`

**Declared evidence:**
- `docs/references/policy-reference.md::block_unaffordable_actions` — documents the setting and its enforcement

**Implementation evidence:**
- `HARNESS.md` line 37: `block_unaffordable_actions: false`
- `HARNESS.md` line 38: `warn_unaffordable_actions: true`
- `godspeed_nav/policies.py::enforce_payment_policy` — respects the flag: `false` → `warn`, `true` → `block`

**Missing links / gaps:**
- Default is WARN, not BLOCK. This is a config choice, not a contradiction — but the policy-reference.md describes blocking as the primary consequence without noting the default is warn-only.

---

### OUT-025 — Identity State as Metabolized History

**Outcome statement:** The system maintains identity state as metabolized history: active direction IDs, capability IDs, substrate IDs, identity markers, and lock-in risks.

**Actor/User:** Agent / operator understanding what the system has become.

**Settlement / success criterion:** `developmental-report` and `cognitive-surfaces` expose `identity_state` with active directions, capabilities, substrate, and lock-in risks.

**Status:** `implemented`

**Confidence:** `high`

**Implementation evidence:**
- `godspeed_nav/reports.py::identity_state` lines 113-118 — aggregates `active_direction_ids`, `capability_ids`, `substrate_ids`, `lock_in_risks`
- `godspeed_nav/runtime.py::cognitive_surfaces` — exposes `identity_state` from report

---

## 5. Cross-Cutting Architecture Map

### Entrypoints

| Surface | File | Purpose |
|---------|------|---------|
| CLI | `godspeed_nav/cli.py::main` | 18 subcommands, JSON output |
| Hooks | `hooks/{pre_tool_use,post_tool_use,stop,user_prompt_submit}.py` | Claude Code lifecycle integration |
| MCP | `mcp/cybernetic_nav_server/server.py::main` | 21 tools via stdin/stdout JSON protocol |
| Plugin | `.claude-plugin/plugin.json` | Claude Code plugin manifest |

### Core Domain Modules

| Module | File | Role |
|--------|------|------|
| Runtime | `godspeed_nav/runtime.py` (598 lines) | Navigation loop coordination |
| Metrics | `godspeed_nav/metrics.py` (282 lines) | Deterministic computation (error, payment, settlement, affordance ranking, transition review) |
| Cognitive Model | `godspeed_nav/cognitive_model.py` (439 lines) | Math-spec burden kernel, gates, spendability, controller ranking |
| Storage | `godspeed_nav/storage.py` (404 lines) | JSONL ledgers with checksums, locking, indexes |
| Policies | `godspeed_nav/policies.py` (87 lines) | Payment, absorption, disintegration, transition policy gates |
| Reports | `godspeed_nav/reports.py` (130 lines) | Developmental observability |
| ML | `godspeed_nav/ml.py` (392 lines) | Threshold-gated predictive extensions |
| Validation | `godspeed_nav/validation.py` (323 lines) | Enterprise-readiness audit |

### Policy/Governance Layer

- Source: `HARNESS.md` (YAML front matter)
- Loader: `godspeed_nav/config.py::load_config`
- Enforcement: `godspeed_nav/policies.py` — 4 policy functions
- Reference: `docs/references/policy-reference.md`

### Persistence/Ledger Layer

- Format: JSONL with optional event envelopes (schema_version, sequence, timestamp, checksum)
- Root: `.godspeed-harness/` (workspace-local)
- Ledgers: `desired_directions`, `horizons`, `horizon_reviews`, `potentials`, `possibilities`, `affordances`, `affordance_paths`, `payments`, `settlements`, `trajectories`, `repetition_schedules`, `capabilities`, `representational_states`, `representational_transitions`, `critique_findings`, `tool_payments`, `post_tool_use_events`, `stop_events`, `prompt_submissions`
- Features: `fcntl.flock` locking, SHA-256 checksums, quarantine, indexes, backup/export, migration status, secret redaction

### Evidence/Logging Layer

- Settlement records include `model_calibration` objects
- Critique findings persisted to `critique_findings` ledger
- Trajectory records track Euler-spiral movement
- Developmental memory lineage queries (`query_developmental_memory`)

### Schemas/Contracts

- `schemas/*.json` — 9 JSON schemas (affordance, capability, desired_direction, horizon, payment, settlement, substrate, trajectory, live_shadow_run_event)
- `godspeed_nav/schemas.py` — `infer_capability_lifecycle`, `now_iso`

### Adapters/Integrations

- RuVector bridge: `godspeed_nav/ruvector_bridge.py` → `tools/ruvector/search_memory.cjs` (Node subprocess)
- Calibration adapters: `scripts/settlement_datasets/{agenttrove,swegym,swegym_openhands,nebius_swe_agent,apibank,webshop}_adapter.py`

### Tests/Proof Paths

- 538 tests across 24 test files
- Key: `test_runtime_workflow.py`, `test_enterprise_storage.py`, `test_validation.py`, `test_cli_hooks_mcp.py`, `test_computation.py`, `test_policy_gates.py`
- No `pytest.mark.skip` or `pytest.mark.xfail` found

### Build/Deployment Surfaces

- `pyproject.toml` — `godspeed-nav` CLI entrypoint, `uv` managed
- `.claude-plugin/plugin.json` — plugin identity
- `hooks/hooks.json` — hook registration
- `.mcp.json` — MCP server registration
- No Dockerfile, no docker-compose

---

## 6. Contradictions and Overclaims

| Claim / Outcome | Evidence for Claim | Evidence Against / Missing | Risk |
| --------------- | ------------------ | -------------------------- | ---- |
| "Hooks capture lifecycle events and convert agent activity into ledger events" (SPEC §3.1.4) | Hooks ARE wired and DO record to ledgers | `pre_tool_use.py` always exits 0 — it does not BLOCK tools; it is observability, not enforcement | Medium — operators may assume hooks prevent unsafe actions |
| `block_unaffordable_actions` enforcement (policy-reference.md) | Policy function exists and CAN block | Default is `false` (warn-only); `policy-reference.md` does not prominently note this default | Low — documented config choice, but could surprise |
| Spec §10.4 "Emitted Runtime Events" (11 event types) | Ledgers record events | No pub/sub, no callback, no event dispatcher — events are recorded but not emitted | Medium — downstream systems expecting event notifications will find none |
| "The runtime is the sole authority for developmental state transitions" (Spec §7) | Runtime owns all state changes | No guard prevents out-of-order invocation; caller can skip steps | Medium — developmental ordering is conventional, not enforced |
| `.mcp.json` references MCP server | Shim exists at hyphen-path | Shim imports from underscore-path; fragile naming inconsistency | Low — works but confusing |
| Calibration pipeline "ROC AUC: 0.7481" (CURRENT_STATE.md) | `scripts/settlement_datasets/` has full pipeline, run artifacts exist | Uses external proxy data (HuggingFace), explicitly "does not prove local capability" | Low — honestly disclosed |
| "536 tests pass" (CURRENT_STATE.md) | Substantial test suite exists | 538 now collected; not verified as passing in this audit | Low |

---

## 7. Missing Proofs

| Outcome ID | Missing Proof | Suggested Minimal Test | Why It Matters |
| ---------- | ------------- | ---------------------- | -------------- |
| OUT-001 | Full-cycle live run in a real receiving project | `godspeed-nav start-direction → review-horizon → record-settlement → developmental-report` against a real project workspace | Proves the loop works outside test fixtures |
| OUT-020 | Hook actually blocks a tool call | Test `pre_tool_use.py` with unaffordable payment + `block_unaffordable_actions: true`, assert non-zero exit or blocking output | Determines if hooks are enforcement or observability |
| OUT-023 | Any real settlement history | Run the harness for one real development session and inspect `ledgers/settlements.jsonl` | Without this, all capability claims rest on self-test |
| OUT-007 | ML activation after 200 real settlements | Populate 200+ real settlements, run `predictive-extensions`, verify `stage: "ml_assisted"` | Proves the threshold gate works with real data |
| OUT-017 | RuVector search returns results | After real settlements with summaries, run `search-developmental-memory --query "..."`, verify non-zero results | Proves semantic search works beyond empty-state |

---

## 8. Frontier Model Audit Brief

### Most Important Outcomes

1. **OUT-001**: Explicit navigation loop (start → horizon → affordance → payment → settlement → trajectory → metabolization)
2. **OUT-004**: Durable local ledgers with checksums, locking, indexes
3. **OUT-005**: Opposition-jump blocking for representational path dependency
4. **OUT-007**: ML/predictive threshold gating (dormant until 200 settlements)
5. **OUT-008**: Deterministic computational model (burden kernel, hard gates, spendability)
6. **OUT-010**: Runtime self-critique (dead-end, circular motion, simulation-as-capability)
7. **OUT-011**: Enterprise validation that can fail
8. **OUT-020**: Hook-level blocking (PARTIAL — observability only)
9. **OUT-023**: Real settlement history (DECLARED ONLY — none exists)

### Highest-Risk Gaps

1. **No real settlement history** — the system has never been used for actual navigation. All evidence is self-referential.
2. **Hooks don't enforce** — `pre_tool_use.py` exits 0 always; policy enforcement is inside `review_horizon`, not at the tool boundary.
3. **No state-machine guards** — operations can be called out of order.
4. **No event emission** — spec declares 11 event types but there is no pub/sub.
5. **Default warn-not-block** — `block_unaffordable_actions: false` by default.

### First Files to Inspect

1. `godspeed_nav/runtime.py` — the core loop; verify state-machine gaps
2. `hooks/pre_tool_use.py` — verify exit-code behavior and whether Claude Code interprets JSON output for blocking
3. `godspeed_nav/policies.py` — verify enforcement vs documentation gap
4. `godspeed_nav/validation.py` — verify which checks are substantive vs structural
5. `ledgers/` (empty) — confirms OUT-023 gap
6. `godspeed_nav/ml.py::build_predictive_extension_plan` — verify threshold logic
7. `godspeed_nav/cognitive_model.py` — verify math-spec alignment

### Open Architectural Questions

1. Does Claude Code's hook framework interpret `"decision": "block"` in stdout JSON as a blocking signal, or does it require non-zero exit?
2. Should the runtime enforce state-machine ordering, or is conventional ordering sufficient for the developmental model?
3. Is JSONL-with-indexes sufficient for the long term, or should SQLite evolution be prioritized?
4. Should the calibration pipeline's external proxy data be more prominently separated from local settlement data?
5. Is the MCP shim (`cybernetic-nav-server` → `cybernetic_nav_server`) intentional packaging or accidental?

### Recommended Next Prompt

```
You are an adversarial auditor for the Godspeed Agent Harness. A prior audit produced an outcome-to-code map at .agents/reports/outcome_code_map_godspeed_agent_2026-06-14.md.

Focus your audit on these high-risk findings:
1. hooks/pre_tool_use.py always returns exit code 0 — determine whether this means the hook CANNOT block tool execution at the Claude Code level. If so, flag "policy enforcement" as overclaimed.
2. ledgers/ is empty and .godspeed-harness/ contains only validation scratch — determine whether ANY real settlement history exists anywhere in the repo. If not, flag all capability claims as test-only.
3. godspeed_nav/runtime.py has no state-machine guards — verify whether out-of-order operations (e.g., record_settlement without review_horizon) produce silent inconsistencies.
4. HARNESS.md has block_unaffordable_actions: false — verify whether any test or runtime path actually hard-blocks unaffordable actions, or whether all blocking is advisory.
5. scripts/settlement_datasets/ calibration pipeline uses external HuggingFace data — verify whether any local settlement data has ever been used for calibration.

For each finding, cite specific file paths, line numbers, and code symbols. Flag any claim in README.md, CURRENT_STATE.md, or docs/ that is undermined by the code evidence.
```
