# Source Traceability Map

This document establishes symbol-level traceability between architectural concepts, operational capabilities, policy invariants, and the concrete Python source files, classes, methods, schemas, and test suites in the repository.

---

## 1. Core Domain Concepts & Types

| Concept / Abstraction | Source File | Symbols / Types | Test Suite |
| :--- | :--- | :--- | :--- |
| **Desired Direction** | `godspeed_nav/runtime.py`<br>`godspeed_nav/schemas.py` | `NavigationRuntime.start_direction`<br>`DesiredDirection` schema | `tests/test_runtime_workflow.py`<br>`tests/test_domain_storage.py` |
| **Horizon** | `godspeed_nav/runtime.py` | `NavigationRuntime.review_horizon`<br>`NavigationRuntime.review_horizon_with_memory` | `tests/test_runtime_workflow.py`<br>`tests/test_convergence_t10_developmental_memory_feedback.py` |
| **Representational Coordinates** | `godspeed_nav/cognitive_model.py` | `RepresentationalCoordinates`<br>`BurdenParameters` | `tests/test_computation.py`<br>`tests/test_action_ontology.py` |
| **Representational Transition** | `godspeed_nav/metrics.py`<br>`godspeed_nav/policies.py` | `review_representational_transition`<br>`enforce_representational_transition_policy` | `tests/test_computation.py`<br>`tests/test_policy_gates.py` |
| **Affordance & Affordance Path** | `godspeed_nav/runtime.py`<br>`godspeed_nav/schemas.py` | `NavigationRuntime._require_executable_affordance`<br>`Affordance` schema | `tests/test_runtime_workflow.py`<br>`tests/test_enterprise_storage.py` |
| **Potential & Possibility** | `godspeed_nav/runtime.py` | `NavigationRuntime._potential_record`<br>`possibilities` ledger append | `tests/test_runtime_workflow.py`<br>`tests/test_policy_gates.py` |
| **Payment Estimation** | `godspeed_nav/metrics.py`<br>`godspeed_nav/policies.py` | `estimate_payment`<br>`enforce_payment_policy` | `tests/test_computation.py`<br>`tests/test_policy_gates.py` |
| **Settlement Scoring** | `godspeed_nav/metrics.py`<br>`godspeed_nav/runtime.py` | `score_settlement`<br>`NavigationRuntime.record_settlement` | `tests/test_computation.py`<br>`tests/test_runtime_workflow.py` |
| **Trajectory & Circular Motion** | `godspeed_nav/trajectory.py` | `update_trajectory`<br>`detect_circular_motion` | `tests/test_computation.py`<br>`tests/test_reports.py` |
| **Metabolization** | `godspeed_nav/metabolization.py`<br>`godspeed_nav/schemas.py` | `compute_metabolization`<br>`infer_capability_lifecycle` | `tests/test_computation.py`<br>`tests/test_convergence_t09_developmental_memory.py` |
| **Repetition Planning** | `godspeed_nav/metabolization.py`<br>`godspeed_nav/runtime.py` | `plan_repetition`<br>`NavigationRuntime._schedule_repetition` | `tests/test_runtime_workflow.py`<br>`tests/test_convergence_t12_variation.py` |
| **Positive Disintegration** | `godspeed_nav/disintegration.py`<br>`godspeed_nav/policies.py` | `review_positive_disintegration`<br>`enforce_disintegration_review` | `tests/test_policy_gates.py` |
| **Absorption Review** | `godspeed_nav/absorption.py`<br>`godspeed_nav/policies.py` | `review_absorbability`<br>`enforce_absorption_review` | `tests/test_policy_gates.py`<br>`tests/test_runbooks.py` |
| **Self-Critique** | `godspeed_nav/runtime.py` | `NavigationRuntime.review_self_critique` | `tests/test_runtime_workflow.py`<br>`tests/test_reports.py` |

---

## 2. Invariant & Boundary Enforcement Gates

| Invariant / Frozen Edge | Source File | Controlling Symbol / Gate | Enforcement Mechanism | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **Executable Affordance Required for Settlement** | `godspeed_nav/runtime.py` | `NavigationRuntime._require_executable_affordance` | Raises `DomainRuleError("settlement_requires_executable_affordance")` if candidate is not persisted or status $\ne$ `'affordance'`. | `tests/test_runtime_workflow.py`<br>`tests/test_validation.py` |
| **Provisional Execution Evidence (Edge E8)** | `godspeed_nav/evidence_ingest.py` | `ingest_evidence_recorded`<br>`ProvisionalEvidence` | Verifies producer is `realitytrace`, binds cryptographic difference hashes, writes strictly to `execution_evidence`. Never settles. | `tests/test_convergence_t08_evidence_recorded.py`<br>`tests/test_swe_seed_trace_ingestion.py` |
| **Exclusive Producer for Developmental Events (Edge E9)** | `godspeed_nav/developmental_events.py` | `project_developmental_event`<br>`PRODUCER = "godspeed-agent"` | All 5 event types (`SettlementRecorded`, etc.) reject non-GSA producers and pseudo-hashes. | `tests/test_canonical_events.py`<br>`tests/test_convergence_t09_developmental_memory.py` |
| **Durable Memory Write Gate (I3, I8, I9, I14, I15)** | `godspeed_nav/developmental_memory.py` | `persist_developmental_event`<br>`DevelopmentalMemoryGate` | Enforces structural hash, parent causality, and earned promotion requirements before write. Deduplicates under lock. | `tests/test_convergence_t09_developmental_memory.py` |
| **Gate-Evaluation-After-Memory (Edge E10 / Invariant I12)** | `godspeed_nav/runtime.py` | `NavigationRuntime.rank_candidates_with_memory`<br>`review_horizon_with_memory` | Memory retrieval applies candidate boost; hard gates (governance, capacity, risk) evaluate *after* boost. Memory never creates affordance. | `tests/test_convergence_t10_developmental_memory_feedback.py` |
| **Opposition Jump Blocking** | `godspeed_nav/metrics.py`<br>`godspeed_nav/policies.py` | `review_representational_transition`<br>`enforce_representational_transition_policy` | Blocks diagonal representational moves unless previously recorded in `metabolized_shortcuts`. | `tests/test_computation.py`<br>`tests/test_policy_gates.py` |
| **Ledger Concurrency & Quarantine** | `godspeed_nav/storage.py` | `LedgerStore.append`<br>`LedgerStore.append_event_if_absent` | Uses `fcntl.flock` and `os.fsync`. Isolates corrupted or checksum-mismatched lines to `cache/quarantine/`. | `tests/test_enterprise_storage.py` |
| **Zero Live Hooks & Trace Recording (F-08)** | `README.md`<br>`HARNESS.md` | Stack boundary definition | GSA registers no IDE/host hooks and runs no live trace recorders. Owned by SWE_SEED. | `tests/test_docs_alignment.py` |

---

## 3. Mathematical & Cognitive Core

| Component | Source File | Key Symbols | Specification Reference | Test Suite |
| :--- | :--- | :--- | :--- | :--- |
| **Representational Coordinates** | `godspeed_nav/cognitive_model.py` | `RepresentationalCoordinates.vector` | Section 4 of math spec | `tests/test_computation.py` |
| **Burden Kernel Matrix** | `godspeed_nav/cognitive_model.py` | `BurdenParameters.matrix`<br>`compute_representational_burden` | Section 5 of math spec: $M + \delta I$ positive-definite matrix | `tests/test_computation.py` |
| **Hard Gates & Spendability** | `godspeed_nav/cognitive_model.py` | `evaluate_candidate_model`<br>`_spendability_factors` | Section 7: Governance, access, payment fit, capability support | `tests/test_computation.py` |
| **Cybernetic Controller** | `godspeed_nav/cognitive_model.py` | `rank_candidates_by_controller`<br>`CONTROLLER_WEIGHTS` | Section 13: Advisory objective ranking $\min(J)$ | `tests/test_computation.py` |
| **Risk & Debt Ceilings** | `godspeed_nav/cognitive_model.py` | `RISK_CEILINGS`<br>`DEBT_CEILINGS` | Section 13.1 by context (`production`, `exploration`, etc.) | `tests/test_computation.py` |
| **Calibration Frame Builder** | `godspeed_nav/cognitive_model.py` | `build_calibration_frame` | Section 17 calibration dataset extraction | `tests/test_calibration_pipeline.py`<br>`tests/test_settlement_datasets.py` |

---

## 4. Physical Storage & Schema Mapping

| Ledger Name | Disk Location | Schema File | Primary Writer Method | Primary Reader Method |
| :--- | :--- | :--- | :--- | :--- |
| `desired_directions` | `.godspeed-harness/ledgers/desired_directions.jsonl` | `schemas/desired_direction.schema.json` | `NavigationRuntime.start_direction` | `LedgerStore.read("desired_directions")` |
| `horizons` | `.godspeed-harness/ledgers/horizons.jsonl` | `schemas/horizon.schema.json` | `NavigationRuntime.start_direction` | `LedgerStore.read("horizons")` |
| `representational_states` | `.godspeed-harness/ledgers/representational_states.jsonl` | None (internal dict) | `NavigationRuntime.set_representational_state` | `LedgerStore.read("representational_states")` |
| `representational_transitions` | `.godspeed-harness/ledgers/representational_transitions.jsonl` | None (internal dict) | `NavigationRuntime.review_representational_transition` | `LedgerStore.read("representational_transitions")` |
| `potentials` | `.godspeed-harness/ledgers/potentials.jsonl` | `schemas/potential.schema.json` | `NavigationRuntime.review_horizon` | `LedgerStore.read("potentials")` |
| `possibilities` | `.godspeed-harness/ledgers/possibilities.jsonl` | `schemas/possibility.schema.json` | `NavigationRuntime.review_horizon` | `LedgerStore.read("possibilities")` |
| `affordances` | `.godspeed-harness/ledgers/affordances.jsonl` | `schemas/affordance.schema.json` | `NavigationRuntime.review_horizon` | `LedgerStore.read("affordances")` |
| `affordance_paths` | `.godspeed-harness/ledgers/affordance_paths.jsonl` | None (internal dict) | `NavigationRuntime.review_horizon` | `LedgerStore.read("affordance_paths")` |
| `payments` | `.godspeed-harness/ledgers/payments.jsonl` | `schemas/payment.schema.json` | `NavigationRuntime.review_horizon` (envelope) | `LedgerStore.read_events("payments")` |
| `settlements` | `.godspeed-harness/ledgers/settlements.jsonl` | `schemas/settlement.schema.json` | `NavigationRuntime.record_settlement` (envelope) | `LedgerStore.read_events("settlements")` |
| `trajectories` | `.godspeed-harness/ledgers/trajectories.jsonl` | `schemas/trajectory.schema.json` | `NavigationRuntime.record_settlement` | `LedgerStore.read("trajectories")` |
| `capabilities` | `.godspeed-harness/ledgers/capabilities.jsonl` | `schemas/capability.schema.json` | `NavigationRuntime._update_capability_evidence` | `LedgerStore.read("capabilities")` |
| `repetition_schedules` | `.godspeed-harness/ledgers/repetition_schedules.jsonl` | None (internal dict) | `NavigationRuntime._schedule_repetition` | `LedgerStore.read("repetition_schedules")` |
| `critique_findings` | `.godspeed-harness/ledgers/critique_findings.jsonl` | None (internal dict) | `NavigationRuntime.review_self_critique` | `LedgerStore.read("critique_findings")` |
| `execution_evidence` | `.godspeed-harness/ledgers/execution_evidence.jsonl` | None (internal envelope) | `NavigationRuntime.ingest_execution_evidence` | `LedgerStore.read_events("execution_evidence")` |
| `canonical_execution_evidence` | `.godspeed-harness/ledgers/canonical_execution_evidence.jsonl` | None (canonical envelope) | `NavigationRuntime.ingest_canonical_evidence_recorded` | `LedgerStore.read_events("canonical_execution_evidence")` |
| `developmental_events` | `.godspeed-harness/ledgers/developmental_events.jsonl` | None (canonical envelope) | `persist_developmental_event` | `LedgerStore.read_events("developmental_events")` |

---

## 5. Public CLI & MCP Surface Mapping

| CLI Command | MCP Tool Name | Implementation Function | Primary Subsystem |
| :--- | :--- | :--- | :--- |
| `compute-error` | `cybernetic_nav.compute_error` | `godspeed_nav.metrics.compute_error` | Metrics |
| `estimate-payment` | `cybernetic_nav.estimate_payment` | `godspeed_nav.metrics.estimate_payment` | Metrics / Policy |
| `rank-affordances` | `cybernetic_nav.rank_affordances` | `godspeed_nav.metrics.rank_affordances` | Metrics / Cognitive Core |
| `review-representational-transition` | `cybernetic_nav.review_representational_transition` | `NavigationRuntime.review_representational_transition` | Runtime / Policy |
| `score-settlement` | `cybernetic_nav.score_settlement` | `godspeed_nav.metrics.score_settlement` | Metrics |
| `metabolization` | `cybernetic_nav.compute_metabolization` | `godspeed_nav.metabolization.compute_metabolization` | Metabolization |
| `absorbability` | `cybernetic_nav.review_absorbability` | `godspeed_nav.absorption.review_absorbability` | Absorption / Policy |
| `runtime-snapshot` | `cybernetic_nav.runtime_snapshot` | `NavigationRuntime.snapshot` | Runtime |
| `cognitive-surfaces` | `cybernetic_nav.cognitive_surfaces` | `NavigationRuntime.cognitive_surfaces` | Runtime / Reporting |
| `repetition-plan` | N/A | `godspeed_nav.reports.generate_developmental_report` | Reporting |
| `set-representational-state` | N/A | `NavigationRuntime.set_representational_state` | Runtime |
| `start-direction` | `cybernetic_nav.start_direction` | `NavigationRuntime.start_direction` | Runtime |
| `review-horizon` | `cybernetic_nav.review_horizon` | `NavigationRuntime.review_horizon` | Runtime |
| `record-settlement` | `cybernetic_nav.record_settlement` | `NavigationRuntime.record_settlement` | Runtime |
| `developmental-report` | `cybernetic_nav.developmental_report` | `godspeed_nav.reports.generate_developmental_report` | Reporting |
| `predictive-extensions` | `cybernetic_nav.predictive_extensions` | `godspeed_nav.ml.run_predictive_extensions` | Machine Learning |
| `search-developmental-memory` | `cybernetic_nav.search_developmental_memory` | `LedgerStore.search_developmental_memory` | Storage / RuVector |
| `validate` | `cybernetic_nav.validate_enterprise_readiness` | `godspeed_nav.validation.validate_enterprise_readiness` | Validation |

---

### Source Trail
- CLI Definition: `godspeed_nav/cli.py`
- MCP Server Definition: `mcp/cybernetic_nav_server/server.py`
- Core Contract Tests: `tests/test_cli_hooks_mcp.py`, `tests/test_runtime_workflow.py`
