# Godspeed Cognitive Operating System Specification

Status: Draft v1 (repository target state)

Purpose: Define the ultimate desired state for this repository as a local-first cognitive operating system that fully embodies the manifesto in `tmp/cogos.md`.

## Normative Language

The key words `MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, `SHOULD NOT`, `RECOMMENDED`, `MAY`, and
`OPTIONAL` in this document are to be interpreted as described in RFC 2119.

`Implementation-defined` means the behavior belongs to the contract surface, but this
specification allows the repository to choose and document the concrete policy.

## 1. Problem Statement

The current repository is a strong local-first developmental navigation harness, but it is not yet a
complete cognitive operating system in the sense defined by `tmp/cogos.md`.

The target system solves the following developmental problems:

- It turns desired directions into a full cognitive loop rather than a partial navigation loop.
- It represents not only payment and settlement, but also representational state, path dependency,
  environmental pressure, identity shift, and self-critique.
- It distinguishes visible destinations from spendable paths and blocks unearned opposition jumps.
- It converts repeated settled action into explicit capability and substrate state instead of
  leaving metabolization as a report-time inference alone.
- It preserves local-first, inspectable truth surfaces while allowing richer memory, critique, and
  predictive support only when settlement history justifies it.

Important boundary:

- This specification defines the desired repository end state, not a claim that the current code
  already satisfies all sections below.
- JSONL developmental ledgers remain the current truth surface unless an explicitly documented
  storage evolution path proves necessary.
- Predictive or simulated behavior MUST remain subordinate to deterministic payment, settlement,
  and policy gates.

## 2. Goals and Non-Goals

### 2.1 Goals

- Implement the full manifesto loop: desired direction, horizon check, representational state
  check, affordance path identification, payment, settlement, repetition, metabolization, horizon
  expansion, positive disintegration, and self-critique.
- Represent cognition as stateful, local, inspectable, and testable repository-owned runtime
  behavior.
- Preserve outcome-as-settlement semantics while rejecting outcome idolatry.
- Model identity as metabolized history shaped by direction, pressure, payment, settlement, and
  repetition.
- Distinguish affordance inventory, affordance utilization, and horizon expansion as separate
  runtime concepts.
- Expose operator-grade CLI, hook, report, MCP, and validation surfaces that make the cognitive
  state legible.

### 2.2 Non-Goals

- Replacing local-first evidence with opaque hosted services.
- Treating simulation, explanation, installation, or access as proof of capability.
- Building a generic AI platform unrelated to the manifesto's doctrine.
- Collapsing representational topology into ad hoc heuristics with no explicit state model.
- Allowing predictive or ML outputs to override deterministic safety or settlement accounting.

## 3. System Overview

### 3.1 Main Components

1. `Desired Direction Registry`
   - Stores active desired directions as polymorphic attractors.
   - Records pressure notes, value constraints, status, and expected horizon expansion.

2. `Representational State Engine`
   - Tracks scope, mode of givenness, phase, quadrant, radius, and confidence.
   - Prices representational movement and blocks unearned opposition jumps.

3. `Horizon Tracker`
   - Maintains visible transformations, spendable paths, blocked paths, and emerging affordances.
   - Separates affordance inventory from affordance utilization.

4. `Affordance Path Engine`
   - Builds spendable transition paths rather than only ranking candidate destinations.
   - Persists preconditions, transition sequence, expected settlement, and lifecycle state.

5. `Payment Processor`
   - Prices direct and hidden costs across time, attention, risk, debt, and other configured axes.
   - Rejects unaffordable transformations through policy-aware gates.

6. `Environment Interface`
   - Executes transformations and senses outcomes.
   - Updates environment state from observed consequence rather than declared intent.

7. `Settlement Ledger`
   - Records before/after consequence, unexpected consequence, payment variance, horizon delta,
     capability delta, identity delta, and new constraints or affordances.

8. `Repetition Scheduler`
   - Plans repeated settlement under variation.
   - Distinguishes one-off success from durable capability formation.

9. `Metabolization Engine`
   - Determines when repeated settled action becomes capability or substrate.
   - Downgrades brittle or insufficiently repeated behavior.

10. `Positive Disintegration Engine`
    - Identifies obsolete structures, dissolution cost, salvageable substrate, and lock-in risks.
    - Couples dissolution with selective metabolization.

11. `Developmental Memory`
    - Preserves local lineage of directions, paths, payments, settlements, repetitions,
      metabolizations, failures, and critiques.
    - Answers how the system became what it is.

12. `Self-Critique Module`
    - Evaluates blind spots, doctrine drift, misuse risk, dead-end directions, and failed
      assumptions.
    - Produces revision prompts and falsification evidence.

13. `Observability Layer`
    - Exposes runtime snapshots, developmental reports, session traces, and validation results.

### 3.2 Abstraction Levels

The repository SHOULD converge on these layers:

1. `Doctrine Layer`
   - `tmp/cogos.md`, understanding docs, and reference docs that define the framework.

2. `Contract Layer`
   - `HARNESS.md`, schemas, policy references, and validation rules.

3. `Cognitive Runtime Layer`
   - Desired directions, representational state, affordance paths, payment, settlement,
     repetition, metabolization, disintegration, identity, and critique.

4. `Execution Layer`
   - CLI commands, hooks, MCP tools, and local automation surfaces.

5. `Storage and Memory Layer`
   - JSONL ledgers, indexes, backups, scratch validation state, and future SQLite-first retrieval
     evolution if justified.

6. `Observability Layer`
   - Reports, validation, references, and operator-visible session state.

### 3.3 External Dependencies

- Local filesystem as the primary evidence surface.
- Python runtime and local CLI environment.
- OPTIONAL local database evolution, with SQLite first if query pressure justifies it.
- OPTIONAL local vector retrieval, with RuVector preferred if retrieval needs exceed deterministic
  search.
- OPTIONAL model providers for predictive extensions, activated only after settlement thresholds are
  met.

## 4. Core Domain Model

### 4.1 Entities

#### 4.1.1 Desired Direction

Normalized attractor used by runtime orchestration.

Fields:

- `id`
- `label`
- `type` (`goal`, `problem`, `vision`, `mission`, `JTBD`, `need`, `question`, `pressure`)
- `statement`
- `timeframe`
- `intensity`
- `expected_horizon_expansion`
- `value_constraints`
- `environment_context`
- `pressure_notes`
- `status`

#### 4.1.2 Representational State

Current representational position for the observer.

Fields:

- `id`
- `scope_position`
- `mode_of_givenness_position`
- `embodiment_position` (implementation alias)
- `phase`
- `quadrant`
- `radius`
- `confidence`

#### 4.1.3 Representational Transition

Possible move between representational states.

Fields:

- `id`
- `from_state`
- `to_state`
- `scope_shift`
- `embodiment_shift`
- `phase_shift`
- `distance_cost`
- `continuity_risk`
- `is_adjacent`
- `is_opposition_jump`
- `status`

#### 4.1.4 Affordance Path

Spendable path through a state space.

Fields:

- `id`
- `description`
- `current_horizon`
- `required_preconditions`
- `transition_sequence`
- `cost_vector`
- `expected_settlement`
- `expected_horizon_expansion`
- `risks`
- `status`

#### 4.1.5 Payment Record

Resource expenditure for an attempted transformation.

Fields:

- `time`
- `energy`
- `money`
- `attention`
- `risk`
- `social_cost`
- `technical_debt`
- `opportunity_cost`
- `timestamp`
- `environment_context`

#### 4.1.6 Settlement Event

Observed consequence and its downstream effects.

Fields:

- `id`
- `action_id`
- `affordance_path_id`
- `before_state`
- `after_state`
- `observed_consequence`
- `unexpected_consequence`
- `payment_variance`
- `horizon_delta`
- `capability_delta`
- `identity_delta`
- `future_constraints_created`
- `future_affordances_created`
- `status`

#### 4.1.7 Capability

Transformation pattern tracked through developmental stages.

Fields:

- `id`
- `name`
- `status` (`latent`, `active`, `repeated`, `metabolized`, `brittle`, `retired`)
- `origin_history`
- `required_repetition`
- `settlement_count`
- `variation_coverage`
- `time_to_metabolize`
- `attention_requirement`

#### 4.1.8 Identity State

Current metabolized history expressed as active pressures, stabilized capabilities, and substrate.

Fields:

- `id`
- `active_direction_ids`
- `capability_ids`
- `substrate_ids`
- `identity_markers`
- `lock_in_risks`
- `updated_at`

#### 4.1.9 Developmental Memory Entry

Linked record of how the system changed through action and consequence.

Fields:

- `id`
- `desired_direction_id`
- `representational_state_id`
- `affordance_path_id`
- `payment_id`
- `settlement_id`
- `capability_id`
- `identity_state_id`
- `critique_id`
- `created_at`

#### 4.1.10 Self-Critique Finding

Structured criticism against runtime behavior, policy, or doctrine.

Fields:

- `id`
- `scope` (`runtime`, `policy`, `skill`, `doctrine`, `storage`, `operator_use`)
- `failure_mode`
- `evidence`
- `falsification_status`
- `recommended_revision`
- `settlement_plan`

### 4.2 Stable Identifiers and Normalization Rules

- `Desired Direction ID`
  - Stable identifier for the current attractor.
- `Representational State ID`
  - Stable identifier for a representational position snapshot.
- `Affordance Path ID`
  - Stable identifier for a spendable pathway, not merely a destination label.
- `Settlement ID`
  - Stable identifier for a reality-audited consequence event.
- `Capability ID`
  - Stable identifier for a repeated transformation pattern across time.

## 5. Repository Contract Specification

### 5.1 File Discovery and Path Resolution

The repository MUST maintain these core doctrine and contract surfaces:

1. `tmp/cogos.md` as the canonical manifesto source.
2. `HARNESS.md` as the implementation-defined runtime policy surface.
3. `docs/references/` as operator-facing contract and interpretation material.
4. `godspeed_nav/` as the authoritative runtime implementation.
5. `tests/` as the executable evidence surface.

### 5.2 Contract Format

The runtime contract is repository-owned and local-first.

Parsing and interpretation rules:

- `HARNESS.md` front matter defines typed runtime policy.
- Doctrine docs define conceptual invariants and MUST NOT silently contradict runtime behavior.
- Reference docs explain active implementation surfaces rather than aspirational ones.
- Validation MUST fail when public runtime behavior drifts from mandatory repository structure.

### 5.3 Contract Schema

Top-level contract surfaces include:

- `harness`
- `storage`
- `computation`
- `experiments`
- `absorption`
- `safety`
- future `cognition` section for representational state, repetition, identity, and self-critique
  settings

### 5.4 Runtime Surface Contract

The public runtime contract MUST eventually expose first-class commands or tools for:

- desired direction registration
- horizon review
- representational state review
- representational transition selection
- affordance path planning
- payment estimation
- settlement recording
- repetition scheduling
- metabolization review
- positive disintegration review
- self-critique review
- runtime snapshot
- developmental report
- enterprise and doctrine validation

### 5.5 Validation and Error Surface

The target repository MUST expose operator-visible errors for at least:

- invalid config
- invalid storage root
- unsupported storage evolution path
- blocked opposition jump
- insufficient repetition evidence
- critique-required doctrine drift
- simulation-not-settlement misuse

## 6. Configuration Specification

### 6.1 Configuration Resolution Pipeline

Configuration resolution SHOULD remain:

1. load repository-owned contract file
2. parse typed settings
3. apply defaults
4. enforce workspace-local path safety
5. validate cognitive-runtime invariants before execution

### 6.2 Dynamic Reload Semantics

Dynamic reload SHOULD remain enabled for future doctrine-safe config changes.

Reloaded config MUST affect future:

- horizon review
- policy gating
- representational transition policy
- repetition scheduling
- predictive-extension thresholds
- self-critique thresholds

### 6.3 Dispatch and Runtime Preflight Validation

Preflight validation MUST eventually verify:

- doctrine and contract files are readable
- required runtime surfaces exist
- storage migration status is current
- representational transition policy is configured
- critique surfaces are present
- predictive extensions remain subordinate to deterministic thresholds

### 6.4 Core Config Fields Summary

Core configuration in the ultimate target state SHOULD cover:

- primary metric
- outcome terminality policy
- storage truth surface
- storage evolution thresholds
- predictive provider and thresholds
- representational distance limits
- opposition jump policy
- repetition and metabolization thresholds
- critique thresholds
- human review requirements for absorption and disintegration

## 7. Developmental State Machine

The runtime is the sole authority for developmental state transitions.

### 7.1 Internal Developmental States

1. `DirectionSelected`
2. `HorizonChecked`
3. `RepresentationalStateChecked`
4. `AffordancePathPlanned`
5. `PaymentPriced`
6. `TransformationAttempted`
7. `SettlementRecorded`
8. `RepetitionPlanned`
9. `CapabilityUpdated`
10. `MetabolizationReviewed`
11. `HorizonExpanded`
12. `PositiveDisintegrationReviewed`
13. `SelfCritiqued`

### 7.2 Transition Triggers

- `Direction registered`
- `Horizon review requested`
- `Representational error detected`
- `Affordance path selected`
- `Payment exceeds capacity`
- `Settlement recorded`
- `Repetition threshold not yet met`
- `Metabolization threshold met`
- `Circular motion detected`
- `Critique criterion triggered`

### 7.3 Idempotency and Recovery Rules

- Settlement events are authoritative and append-only.
- Simulated results MUST NOT be promoted to settled capability evidence.
- Retried or repeated attempts MUST preserve lineage to the originating direction and path.
- Recovery after restart MUST reconstruct useful state from local developmental memory rather than
  from operator claims.

## 8. Horizon, Scheduling, and Reconciliation

### 8.1 Horizon Loop

Each runtime cycle SHOULD:

1. inspect current horizon
2. inspect representational state
3. generate candidate paths
4. block unearned opposition jumps
5. price payment and continuity risk
6. choose the next affordable path
7. record settlement
8. schedule repetition or critique

### 8.2 Candidate Selection Rules

A candidate path is spendable only if all are true:

- a path exists, not only a destination
- payment is affordable
- preconditions are met
- settlement can be observed
- the move does not violate representational transition policy unless the shortcut is already
  metabolized

### 8.3 Concurrency and Capacity Control

Capacity is not only CPU or process slots. The cognitive runtime SHOULD model at least:

- time capacity
- attention capacity
- risk tolerance
- maintenance burden
- policy-imposed human review limits

### 8.4 Repetition and Backoff

Repetition scheduling SHOULD distinguish:

- continuation after a successful but not yet metabolized settlement
- retry after failure or ambiguous settlement
- delayed retest under changed conditions
- critique escalation for repeated circular motion

### 8.5 Reconciliation

Reconciliation MUST eventually update:

- active desired directions
- current horizon records
- representational state
- capability lifecycle state
- identity state
- critique backlog

## 9. Storage Management and Safety

### 9.1 Storage Layout

Storage root remains `.godspeed-harness` unless configuration documents otherwise.

The target layout SHOULD include ledgers or equivalent local records for:

- desired directions
- horizons
- representational states
- representational transitions
- affordance paths
- payments
- settlements
- repetitions
- capabilities
- identity states
- critiques
- trajectories

### 9.2 Storage Persistence and Reuse

- Local records are reused across sessions and validations unless scratch storage is explicitly
  requested.
- Developmental memory MUST remain inspectable and exportable.

### 9.3 Optional Storage Evolution

- JSONL remains the current truth surface.
- SQLite is the first approved step for richer local query.
- SQLite plus RuVector is the preferred vector retrieval path if retrieval pressure justifies it.
- SurrealDB or any graph-first replacement requires explicit evidence that simpler local options
  fail settlement.

### 9.4 Safety Invariants

- Storage paths MUST remain inside the workspace.
- Checksummed event envelopes MUST remain authoritative for append-only evidence.
- Simulation logs MUST remain distinguishable from settlement ledgers.
- Capability promotion MUST require repeated settled evidence.

## 10. Agent and Tool Integration Protocol

### 10.1 Launch Contract

Hooks, CLI, and MCP integrations MUST operate against the workspace-local runtime and storage root.

### 10.2 Session Startup Responsibilities

At session start, the runtime SHOULD be able to:

- infer or register desired direction context
- create or load session context
- attach representational and horizon context where available
- expose critique and policy surfaces to downstream tools

### 10.3 Streaming Turn Processing

Streaming execution SHOULD feed back into:

- payment review
- settlement evidence
- trajectory updates
- repetition signals
- critique triggers

### 10.4 Emitted Runtime Events

The target system SHOULD expose events such as:

- `onDirectionSelected`
- `onHorizonChecked`
- `onRepresentationalStateChanged`
- `onAffordancePathSelected`
- `onPaymentSpent`
- `onSettlementRecorded`
- `onCapabilityRepeated`
- `onMetabolization`
- `onHorizonExpansion`
- `onPositiveDisintegration`
- `onSelfCritique`

### 10.5 Approval and User Input Policy

Approval behavior remains implementation-defined, but MUST NOT bypass:

- payment policy
- absorption review policy
- positive disintegration review policy
- local storage boundary checks

### 10.6 Error Mapping

Recommended normalized categories:

- `invalid_storage_root`
- `unaffordable_action`
- `blocked_opposition_jump`
- `missing_settlement_evidence`
- `insufficient_repetition`
- `critique_required`
- `doctrine_drift_detected`

## 11. Environment Integration Contract

### 11.1 Required Operations

The environment interface MUST eventually support:

1. observing current local state
2. executing a transformation
3. recording before and after consequence
4. updating environment context for future horizon review

### 11.2 Query and Update Semantics

- Environment updates MUST be consequence-driven.
- Hidden or delayed consequence MAY be recorded later as additional settlement evidence.
- Environment state MUST be distinguishable from internal representation state.

### 11.3 Normalization Rules

- Before/after states SHOULD remain structured and machine-readable.
- Identity deltas, capability deltas, and future affordances SHOULD use stable identifiers where
  possible.

### 11.4 Error Handling Contract

- Missing observable consequence MUST remain a first-class failure or ambiguity surface.
- Environment read failures SHOULD not silently become settlement success.

### 11.5 Boundary

Environment execution is not proof of metabolization. Only repeated settled survival qualifies.

## 12. Context Construction and Assembly

### 12.1 Inputs

Inputs to any cognitive runtime decision SHOULD include:

- desired direction
- current horizon
- current representational state
- developmental memory
- environment state
- applicable policy and value constraints

### 12.2 Rendering Rules

- Unknown required context SHOULD fail clearly rather than degrade silently.
- Prompt and tool context SHOULD preserve lineage to the active desired direction.

### 12.3 Retry and Continuation Semantics

Continuation and retry SHOULD distinguish:

- ongoing repetition toward metabolization
- corrective retry after failed settlement
- critique-driven pause because the current loop is no longer developmental

### 12.4 Failure Semantics

If critical context assembly fails, the attempt SHOULD fail or degrade explicitly, not pretend the
system still has cognitive continuity.

## 13. Logging, Status, and Observability

### 13.1 Logging Conventions

Logs SHOULD make these entities traceable:

- desired direction
- representational state
- affordance path
- settlement
- capability
- critique finding

### 13.2 Logging Outputs and Sinks

- Operators MUST be able to inspect failures without attaching a debugger.
- Loss of one observability sink SHOULD NOT destroy runtime correctness.

### 13.3 Runtime Snapshot and Monitoring

The target runtime snapshot SHOULD expose at least:

- active directions
- latest representational state
- current horizon counts
- payment burden totals
- settlement quality
- trajectory and circular motion
- metabolization candidates
- critique backlog

### 13.4 Human-Readable Status Surface

If present, a human-readable status surface SHOULD explain:

- what the system is trying to become
- what it can currently afford
- what it recently paid for
- what reality settled
- what must now repeat, dissolve, or be revised

### 13.5 Metrics and Runtime Accounting

The system SHOULD preserve and explain at least:

- error magnitude
- payment burden
- settlement score
- affordance rank score
- metabolization score
- trajectory radius growth
- circular motion detection
- identity and capability movement

### 13.6 Humanized Event Summaries

Humanized summaries are optional, but MUST remain downstream of structured evidence.

### 13.7 Optional HTTP or Dashboard Extension

Any future dashboard MUST remain an observability surface, not a replacement for local ledger truth.

## 14. Failure Model and Recovery Strategy

### 14.1 Failure Classes

1. `Doctrine and Contract Failures`
   - doctrine drift
   - missing reference surfaces
   - invalid runtime contract

2. `Representational Failures`
   - blocked opposition jumps
   - missing intermediate states
   - excessive representational distance

3. `Settlement Failures`
   - missing observable change
   - mixed consequence
   - hidden debt discovered after the fact

4. `Capability Failures`
   - brittle capability
   - insufficient repetition
   - transfer failure across contexts

5. `Critique Failures`
   - blind spot not surfaced
   - circular motion not detected
   - doctrine revision path absent

### 14.2 Recovery Behavior

- Failed settlement SHOULD trigger retry, adjustment, or critique depending on evidence.
- Representational failure SHOULD trigger path decomposition rather than destination worship.
- Critique failure SHOULD trigger reconstruction work rather than doctrinal defense.

### 14.3 Partial State Recovery

After restart, the system SHOULD reconstruct developmental continuity from local memory, including:

- active directions
- last known horizon state
- latest representational state
- outstanding repetition requirements
- latest capability and critique state

### 14.4 Operator Intervention Points

Operators intervene by:

- updating the contract in `HARNESS.md`
- revising doctrine and references when settlement falsifies them
- reviewing blocked absorption or disintegration actions
- inspecting critique findings and deciding whether to reconstruct a surface

## 15. Security and Operational Safety

### 15.1 Trust Boundary Assumption

The target system remains local-first, but MUST assume that prompts, repositories, and tool inputs
can still contain misleading or harmful instructions.

### 15.2 Filesystem Safety Requirements

- All runtime storage MUST remain workspace-local unless explicitly configured otherwise.
- Validation and experiments SHOULD use scratch storage when they would otherwise pollute truth
  ledgers.

### 15.3 Secret Handling

- Secrets MUST remain redacted in storage and logs.
- Critique or report surfaces MUST not leak secret-bearing payloads.

### 15.4 Hook and Tool Safety

- Hooks and tools are trusted execution surfaces and MUST remain policy-aware.
- The runtime MUST not silently bypass policy because a call originated from a hook or MCP tool.

### 15.5 Harness Hardening Guidance

Hardening in the target state SHOULD focus on preserving truthful settlement and safe payment, not
on pretending cognition exists where only access exists.

## 16. Reference Algorithms

### 16.1 Cognitive Runtime Startup

```text
function start_cognitive_runtime():
  load_contract_surfaces()
  validate_doctrine_and_runtime_alignment()
  open_local_storage()
  restore_latest_developmental_state()
  expose_cli_hook_mcp_surfaces()
  enter_developmental_loop()
```

### 16.2 Horizon-and-Path Cycle

```text
function review_next_affordable_path(direction):
  horizon = load_current_horizon(direction)
  representation = load_current_representational_state(direction)
  candidates = generate_candidate_distinctions(horizon, representation)
  transitions = filter_by_transition_policy(candidates, representation)
  paths = build_affordance_paths(transitions)
  priced = price_payment_and_continuity(paths)
  return rank_by_horizon_expansion_and_affordability(priced)
```

### 16.3 Settlement-and-Metabolization Cycle

```text
function settle_and_update(path, before_state, after_state, evidence):
  settlement = record_settlement(path, before_state, after_state, evidence)
  update_environment_state(settlement)
  update_representational_state(settlement)
  update_capability_state(settlement)
  if not metabolized(settlement.capability):
    schedule_repetition(path)
  else:
    promote_to_substrate(settlement.capability)
    expand_horizon()
  return settlement
```

### 16.4 Critique and Reconstruction Cycle

```text
function run_self_critique():
  findings = evaluate_failure_modes_and_blind_spots()
  if doctrine_or_policy_failed_settlement(findings):
    write_critique_finding(findings)
    produce_reconstruction_plan(findings)
  return findings
```
