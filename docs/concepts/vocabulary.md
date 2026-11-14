# Domain Vocabulary & Conceptual Taxonomy

This document establishes the normative terminology of the GodSpeed-Agent repository. Terms in this codebase carry precise cybernetic meanings and must not be replaced with generic software or product management jargon.

---

## 1. Desired Direction
- **What it is**: The active attractor that exerts developmental pressure on the observer. It may be framed as a goal, problem, vision, outcome, aim, mission, need, or job-to-be-done.
- **What it is not**: A terminal destination, a permanent commitment, or a definition of completion.
- **Relationship**: It establishes the initial horizon and sets the success and death criteria for actions. When settled, it becomes substrate.
- **Implementation**:
  - Schema: `schemas/desired_direction.schema.json`
  - Dataclass/Model: `godspeed_nav/runtime.py` (`start_direction`)
  - Ledger: `.godspeed-harness/ledgers/desired_directions.jsonl`

---

## 2. Horizon
- **What it is**: The boundary of transformations currently perceivable and actionable by the observer, based on its active capabilities and accumulated substrate.
- **What it is not**: The sum of all imaginable or theoretical actions in the universe; not merely accessible disk or memory space.
- **Relationship**: Encapsulates visible affordance candidates and potentials. Horizon expansion is the primary metric of the system.
- **Implementation**:
  - Schema: `schemas/horizon.schema.json`
  - Runtime: `godspeed_nav/runtime.py` (`review_horizon`)
  - Polar Coordinate: `godspeed_nav/trajectory.py` (`new_radius`, `radius_growth`)

---

## 3. Representational State
- **What it is**: The observer's current position within representational space, defined across two continuous axes: scope ($0.0 = \text{general} \leftrightarrow 1.0 = \text{specific}$) and mode of givenness / embodiment ($0.0 = \text{abstract} \leftrightarrow 1.0 = \text{concrete}$).
- **What it is not**: A casual label, an emotional state, or an unconstrained text prompt.
- **Relationship**: Dictates whether an intended transition is adjacent and affordable, or an un-metabolized opposition jump that must be blocked.
- **Implementation**:
  - Data Structure: `godspeed_nav/cognitive_model.py` (`RepresentationalCoordinates`)
  - Transition Review: `godspeed_nav/metrics.py` (`review_representational_transition`)
  - Ledger: `.godspeed-harness/ledgers/representational_states.jsonl`

---

## 4. Affordance
- **What it is**: A spendable path through state space. An affordance connects the observer's current state to an expected settlement via a concrete pathway, with quantified costs falling strictly within capacity.
- **What it is not**: A visible destination without a path, an unvalidated idea, or an unaffordable wish.
- **Relationship**: Derived from candidate review. Only persisted affordances (`current_status == 'affordance'`) are legally eligible for execution and settlement.
- **Implementation**:
  - Schema: `schemas/affordance.schema.json`
  - Ledger: `.godspeed-harness/ledgers/affordances.jsonl` and `affordance_paths.jsonl`
  - Enforcement: `godspeed_nav/runtime.py` (`_require_executable_affordance`)

---

## 5. Potential vs. Possibility
- **Potential**: A conceived transformation that lacks a validated, concrete pathway for the observer.
  - *Status*: `potential`.
  - *Ledger*: `.godspeed-harness/ledgers/potentials.jsonl`.
- **Possibility**: A transformation that has an identified pathway, but whose estimated payment exceeds current capacity.
  - *Status*: `possibility`.
  - *Ledger*: `.godspeed-harness/ledgers/possibilities.jsonl`.
- **Key Invariant**: Neither potentials nor possibilities can be scheduled or executed as affordances.

---

## 6. Affordance Inventory vs. Affordance Utilization
- **Affordance Inventory**: The set of paths that appear theoretically available in the environment.
- **Affordance Utilization**: The subset of paths that the observer can actively perceive, correctly sequence, afford, and spend based on its own metabolized capability.
- **Contrast**: Having access to a GPU cluster increases inventory; knowing how to write efficient CUDA kernels increases utilization.

---

## 7. Horizon Expansion
- **What it is**: An increase in the observer's spendable perception-action space resulting from settled action and capability metabolization.
- **What it is not**: Merely acquiring more resources, downloading more libraries, or storing more data.
- **Metric**: Measured as radial growth $\Delta r$ in the trajectory engine.
- **Implementation**: `godspeed_nav/trajectory.py` (`radius_growth = max(0.0, settlement_score - 0.5) * max(0.0, horizon_delta)`)

---

## 8. Payment & Payment Burden
- **What it is**: The immediate, multidimensional cost required to execute an affordance, measured across time, compute, risk, technical debt, and coordination.
- **Payment Burden**: The Euclidean norm of weighted costs ($\sqrt{\sum (c_i \cdot w_i)^2}$).
- **Spendability Rule**: An affordance is spendable only if payment burden $\le$ capacity norm ($\sqrt{\sum \text{cap}_i^2}$).
- **Implementation**:
  - Calculation: `godspeed_nav/metrics.py` (`estimate_payment`)
  - Policy Gate: `godspeed_nav/policies.py` (`enforce_payment_policy`)
  - Ledger: `.godspeed-harness/ledgers/payments.jsonl`

---

## 9. Settlement
- **What it is**: The empirical consequence recorded by reality or the system's evidence surface after an action is taken.
- **What it is not**: Model-generated declarations of success, unverified assertions, or execution attempts.
- **Status Classification**:
  - `success`: Score $\ge 0.7$ with zero regressions across observed state keys.
  - `partial`: Measurable progress made, but incomplete or accompanied by minor regressions.
  - `failed`: No observable change, score collapsed to $0$, regressions dominant, or intent-only evidence.
- **Implementation**:
  - Scorer: `godspeed_nav/metrics.py` (`score_settlement`)
  - Execution Gate: `godspeed_nav/runtime.py` (`record_settlement`)
  - Ledger: `.godspeed-harness/ledgers/settlements.jsonl`

---

## 10. Outcome
- **What it is**: A feedback-rich settlement event that provides error-correction data, reveals what payment actually purchased, and becomes developmental memory for subsequent cycles.
- **What it is not**: A terminal god or permanent endpoint that stops execution.

---

## 11. Provisional Evidence
- **What it is**: External execution records (e.g. `EvidenceRecorded` emitted by test harnesses or external agents) ingested into GodSpeed-Agent.
- **Invariant**: Software proof alone is **never** settlement. Complete matching evidence is classified strictly as `provisional` and written only to `execution_evidence.jsonl`. A separate, explicit `record_settlement` call evaluating consequence is required for promotion.
- **Implementation**: `godspeed_nav/evidence_ingest.py`, `godspeed_nav/runtime.py` (`ingest_execution_evidence`)

---

## 12. Metabolization
- **What it is**: The empirical process by which a settled capability becomes effortless, reliable **substrate**.
- **Normative Requirements**:
  1. $\ge 3$ successful settlement events.
  2. Reuse frequency $\ge 3$.
  3. Context diversity $\ge 2$ (distinct before/after states).
  4. Stability $\ge 0.8$ average score.
  5. Maintenance burden $\le 0.3$.
  6. Attention burden $\le 0.3$.
- **What it is not**: A label declared by an engineer, an installed package, or a passing single unit test.
- **Implementation**: `godspeed_nav/metabolization.py` (`compute_metabolization`)

---

## 13. Substrate
- **What it is**: Metabolized capability that operates predictably in the background, requiring near-zero attention burden, thereby exposing new affordances and expanding the visible horizon.
- **Contrast**: Writing code by manually copying byte sequences is active burden; calling a thoroughly metabolized compiler is substrate.

---

## 14. Identity
- **What it is**: The cumulative history of metabolized capabilities, recorded settlements, and settled adaptations.
- **What it is not**: A static prompt, a system instruction string, or a fixed essence.
- **Implementation**: Tracked via `identity_delta` in settlements and compiled in developmental reports.

---

## 15. Positive Disintegration
- **What it is**: The deliberate dissolution of obsolete, brittle, or high-debt structures while salvaging useful components and integrating them into new substrate.
- **What it is not**: Destructive deletion without salvage, or mindless accumulation without pruning.
- **Implementation**:
  - Review: `godspeed_nav/disintegration.py` (`review_positive_disintegration`)
  - Governance: `godspeed_nav/policies.py` (`enforce_disintegration_review`)

---

## 16. Trajectory & Circular Motion
- **Trajectory**: The developmental path recorded in polar coordinates $(\theta, r)$.
- **Circular Motion**: Stagnation where the system completes angular turns ($\Delta\theta \ge 2\pi$) while achieving negligible radial expansion ($\Delta r \le 0.1$).
- **Implementation**: `godspeed_nav/trajectory.py` (`detect_circular_motion`)
