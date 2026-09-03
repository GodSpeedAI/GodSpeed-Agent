# Documentation Map & Diátaxis Index

This document is the architectural index of the GodSpeed-Agent technical knowledge system. It classifies every document by its **Diátaxis purpose**, identifies target audience needs, and provides prerequisite and related links.

---

## 1. Diátaxis Framework Overview

The documentation system is organized strictly according to the Diátaxis framework to prevent cognitive friction and maintain functional clarity:

| Diátaxis Mode | Reader Need | Orientation | Repo Directory |
| :--- | :--- | :--- | :--- |
| **Tutorials** | "Teach me how to use this through a guided, successful experience." | Learning-oriented | `docs/tutorials/` |
| **How-To Guides** | "Show me how to solve a specific problem or complete a real task." | Problem-oriented | `docs/how-to/`, `docs/runbooks/` |
| **Explanation** | "Help me understand why the system is built this way and the rationale behind it." | Understanding-oriented | `docs/explanations/`, `docs/concepts/` |
| **Reference** | "Give me precise, comprehensive technical facts, signatures, and schemas." | Information-oriented | `docs/references/`, `docs/subsystems/` |

---

## 2. Complete Document Catalog

### Orientation & Foundations

| Document | Path | Diátaxis Mode | Primary Audience Need | Prerequisites | Related Documents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Documentation Hub** | `docs/index.md` | Orientation / Gateway | Rapid orientation, system summary, intent-based entry points. | None | `getting-started.md`, `architecture.md` |
| **Getting Started** | `docs/getting-started.md` | Tutorial (Onboarding) | Install, configure, and run first commands in <10 minutes. | Python 3.11+ | `tutorials/first-developmental-loop.md` |
| **System Mental Model** | `docs/concepts/mental-model.md` | Explanation | Understand cybernetic principles, attractors, and representational space. | `docs/index.md` | `concepts/vocabulary.md`, `architecture.md` |
| **Domain Vocabulary** | `docs/concepts/vocabulary.md` | Reference / Glossary | Look up precise, normative definitions of framework terms. | None | `concepts/mental-model.md`, `references/schema-index.md` |

---

### Architecture & Canonical Specifications

| Document | Path | Diátaxis Mode | Primary Audience Need | Prerequisites | Related Documents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Architecture Specification** | `docs/architecture.md` | Reference / Architecture | Understand system boundaries, runtime topology, data flows, and security. | `concepts/mental-model.md` | `source-map.md`, all subsystem docs |
| **Source Traceability Map** | `docs/source-map.md` | Reference (Traceability) | Map domain concepts and invariants directly to Python symbols, files, and tests. | `docs/architecture.md` | All subsystem docs, `tests/` |
| **Documentation Map** | `docs/documentation-map.md` | Meta-Documentation | Navigate docs by Diátaxis quadrant, audience need, and dependency order. | None | `docs/index.md` |

---

### Subsystem Guides (Deep Reference & Mechanism)

| Document | Path | Diátaxis Mode | Primary Audience Need | Prerequisites | Related Documents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Runtime Coordinator** | `docs/subsystems/runtime-coordinator.md` | Reference / Architecture | Understand `NavigationRuntime` orchestration, state transitions, and loops. | `docs/architecture.md` | `workflows/core-developmental-cycle.md` |
| **Storage & Ledgers** | `docs/subsystems/storage-and-ledgers.md` | Reference / Architecture | Inspect `LedgerStore`, file locking, envelope schemas, and quarantine. | `docs/architecture.md` | `references/ledger-reference.md` |
| **Cognitive Computational Core** | `docs/subsystems/cognitive-computational-core.md` | Reference / Architecture | Understand mathematical burden matrix, hard gates, spendability, and controller. | `concepts/mental-model.md` | `explanations/representational-path-dependency.md` |
| **Developmental Memory & Events** | `docs/subsystems/developmental-memory-and-events.md` | Reference / Architecture | Inspect E9 projection, E10 memory retrieval, and invariant gates (I3/I8/I9/I14/I15). | `docs/architecture.md` | `workflows/memory-informed-navigation.md` |
| **Evidence Ingestion** | `docs/subsystems/evidence-ingestion.md` | Reference / Architecture | Understand fail-closed E8 admission for provisional proof from RealityTrace. | `docs/architecture.md` | `workflows/evidence-ingestion-trace.md` |
| **Metabolization & Lifecycle** | `docs/subsystems/metabolization-and-lifecycle.md` | Reference / Architecture | Understand 6-factor metabolization score and repetition planning under variation. | `concepts/mental-model.md` | `workflows/core-developmental-cycle.md` |
| **Policy & Governance** | `docs/subsystems/policy-and-governance.md` | Reference / Architecture | Inspect payment enforcement, opposition jump blocking, and human review gates. | `docs/architecture.md` | `references/policy-reference.md` |
| **Agentic Loop Adapters** | `docs/subsystems/agentic-loop-adapters.md` | Reference / Architecture | Understand CEP-0008 SS15 wire schemas and offline-tolerant NATS publisher. | `docs/architecture.md` | `subsystems/developmental-memory-and-events.md` |
| **MCP & CLI Surfaces** | `docs/subsystems/mcp-and-cli-surfaces.md` | Reference / Architecture | Explore CLI commands and the 21 JSON-RPC MCP tools for Claude Code. | `getting-started.md` | `references/cli-reference.md` |
| **Validation & Observability** | `docs/subsystems/validation-and-observability.md` | Reference / Architecture | Understand the 12-point enterprise audit suite and developmental reports. | `docs/architecture.md` | `how-to/run-enterprise-validation.md` |
| **ML & Semantic Search** | `docs/subsystems/ml-and-semantic-search.md` | Reference / Architecture | Understand the dormant sklearn provider and local RuVector Node bridge. | `docs/architecture.md` | `how-to/add-a-custom-predictive-provider.md` |

---

### Workflows & Execution Traces

| Document | Path | Diátaxis Mode | Primary Audience Need | Prerequisites | Related Documents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Core Developmental Cycle** | `docs/workflows/core-developmental-cycle.md` | Explanation / Trace | Follow end-to-end execution from `start-direction` to `substrate_candidate`. | `subsystems/runtime-coordinator.md` | `tutorials/first-developmental-loop.md` |
| **Evidence Ingestion Trace** | `docs/workflows/evidence-ingestion-trace.md` | Explanation / Trace | Trace inbound `EvidenceRecorded` through E8 admission into provisional storage. | `subsystems/evidence-ingestion.md` | `explanations/settlement-versus-intent.md` |
| **Memory-Informed Navigation** | `docs/workflows/memory-informed-navigation.md` | Explanation / Trace | Trace durable memory retrieval, candidate boosting, and hard gating (E10). | `subsystems/developmental-memory-and-events.md` | `subsystems/cognitive-computational-core.md` |
| **Absorption Lifecycle** | `docs/workflows/absorption-lifecycle.md` | Explanation / Trace | Trace external capability evaluation, license audit, pathway check, and worktrees. | `concepts/mental-model.md` | `tutorials/absorbing-a-capability.md` |
| **Self-Critique & Stagnation** | `docs/workflows/self-critique-and-detection.md` | Explanation / Trace | Trace circular motion detection and stagnation findings in trajectories. | `concepts/mental-model.md` | `how-to/troubleshoot-common-failures.md` |

---

### Explanations & Design Rationale

| Document | Path | Diátaxis Mode | Primary Audience Need | Prerequisites | Related Documents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Why Horizon Over Outcomes** | `docs/explanations/why-horizon-over-outcomes.md` | Explanation | Understand the cybernetic critique of arrival-centricity and Goodhart's law. | `concepts/mental-model.md` | `concepts/vocabulary.md` |
| **Why Local-First & Deterministic** | `docs/explanations/why-local-first-deterministic.md` | Explanation | Understand why deterministic accounting must precede predictive machine learning. | `docs/architecture.md` | `subsystems/cognitive-computational-core.md` |
| **Representational Path Dependency** | `docs/explanations/representational-path-dependency.md` | Explanation | Learn why opposition jumps fail and the mathematics of representational burden. | `concepts/mental-model.md` | `subsystems/cognitive-computational-core.md` |
| **Settlement Versus Intent** | `docs/explanations/settlement-versus-intent.md` | Explanation | Understand why consequence is the only truth surface and software proof is provisional. | `concepts/mental-model.md` | `subsystems/evidence-ingestion.md` |

---

### Tutorials (Guided Practice)

| Document | Path | Diátaxis Mode | Primary Audience Need | Prerequisites | Related Documents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **First Developmental Loop** | `docs/tutorials/first-developmental-loop.md` | Tutorial | Step-by-step hands-on terminal exercise executing a real navigation cycle. | `getting-started.md` | `workflows/core-developmental-cycle.md` |
| **Absorbing a Capability** | `docs/tutorials/absorbing-a-capability.md` | Tutorial | Hands-on exercise staging, auditing, and absorbing an external module. | `getting-started.md` | `workflows/absorption-lifecycle.md` |

---

### How-To Guides & Operations

| Document | Path | Diátaxis Mode | Primary Audience Need | Prerequisites | Related Documents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Run Enterprise Validation** | `docs/how-to/run-enterprise-validation.md` | How-To Guide | Run and interpret the 12 enterprise readiness checks. | `getting-started.md` | `subsystems/validation-and-observability.md` |
| **Configure Harness Policy** | `docs/how-to/configure-harness-policy.md` | How-To Guide | Tune capacities, risk ceilings, and review gates in `HARNESS.md`. | `getting-started.md` | `references/policy-reference.md` |
| **Add Custom Predictive Provider** | `docs/how-to/add-a-custom-predictive-provider.md` | How-To Guide | Implement and register a custom `PredictiveModelPort`. | `docs/architecture.md` | `subsystems/ml-and-semantic-search.md` |
| **Troubleshoot Common Failures** | `docs/how-to/troubleshoot-common-failures.md` | How-To Guide | Diagnose and recover from blocked transitions, unaffordable actions, and circularity. | `getting-started.md` | `workflows/self-critique-and-detection.md` |

---

### References (Technical Facts & Schemas)

| Document | Path | Diátaxis Mode | Primary Audience Need | Prerequisites | Related Documents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CLI Reference** | `docs/references/cli-reference.md` | Reference | Command flags, input argument types, and JSON outputs. | None | `subsystems/mcp-and-cli-surfaces.md` |
| **Ledger Reference** | `docs/references/ledger-reference.md` | Reference | Exact JSONL field definitions for all 12 system ledgers. | None | `subsystems/storage-and-ledgers.md` |
| **Policy Reference** | `docs/references/policy-reference.md` | Reference | Full catalog of configuration keys and runtime defaults. | None | `subsystems/policy-and-governance.md` |
| **Report Interpretation** | `docs/references/report-interpretation.md` | Reference | Detailed field-by-field guide to `developmental-report` JSON. | None | `subsystems/validation-and-observability.md` |
| **Runtime Workflow Example** | `docs/references/runtime-workflow-example.md` | Reference | Canonical multi-command JSON input/output payload examples. | None | `workflows/core-developmental-cycle.md` |
| **Schema Index** | `docs/references/schema-index.md` | Reference | Index of all JSON Schemas in `schemas/`. | None | `concepts/vocabulary.md` |
