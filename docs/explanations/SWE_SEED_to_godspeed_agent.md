# Canonical Boundary: GodSpeed-Agent and SWE_SEED

Treat this document as the controlling responsibility boundary between GodSpeed-Agent and SWE_SEED. Current repository structure may contain historical overlap or incomplete migration. Do not infer canonical ownership merely from where code currently lives.

## Core Distinction

```text
SWE_SEED = verified software-work execution loop
GodSpeed-Agent = developmental navigation and capability-formation loop
```

SWE_SEED answers:

> Was this software job executed according to its declared work contract, and what evidence proves the result?

GodSpeed-Agent answers:

> What does this result mean for settlement, developmental memory, capability, repetition, and the observer’s future affordance horizon?

Canonical shorthand:

```text
SWE_SEED proves the work.
GodSpeed-Agent interprets and compounds the outcome.
```

## SWE_SEED Owns

SWE_SEED owns the mechanics and evidence of agentic software work:

* task and job-contract routing;
* required-context loading;
* work-loop instructions;
* artifact contracts;
* proof commands and proof gates;
* command results and exit codes;
* execution traces;
* repository and tool hooks;
* reflection attached to a work attempt;
* evidence packaging;
* reporting whether the declared work contract passed or failed.

SWE_SEED may say:

```text
The required artifact was produced.
The declared proof commands ran.
These commands passed or failed.
This trace records the attempt.
These files and systems changed.
```

SWE_SEED must not say:

```text
This capability is metabolized.
The organization has learned this.
This settlement is developmentally usable.
Three executions automatically prove capability.
```

Those are GodSpeed-Agent decisions.

## GodSpeed-Agent Owns

GodSpeed-Agent owns CognitiveOS navigation and developmental state:

* desired directions;
* horizon review;
* affordance review;
* payment estimates;
* settlement classification;
* settlement-reliability assessment;
* canonical settlement records;
* capability lifecycle;
* variation and transfer evidence;
* repetition scheduling;
* developmental memory;
* earned-compression decisions;
* learning proposals;
* capability promotion, demotion, quarantine, and retirement.

GodSpeed-Agent may say:

```text
This evidence corresponds to an existing spendable affordance.
This outcome is usable, provisional, pending, or quarantined.
This attempt should update capability with this weight.
This capability requires repetition under additional variation.
This capability has or has not satisfied metabolization criteria.
This result creates a learning proposal.
```

GodSpeed-Agent must not independently duplicate SWE_SEED’s task router, coding hooks, trace collector, or software proof gate.

## Required Interaction

### 1. Form or identify an affordance

Before GodSpeed-Agent records settlement, the attempted work must correspond to a persisted affordance that is both executable and authorized.

A potential, possibility, unknown identifier, invented path, retired affordance, or unauthorized affordance cannot be settled.

```text
unknown path → reject
potential only → reject
possibility only → reject
retired or unauthorized state → reject
persisted spendable or attempted affordance, executable and authorized → eligible for evidence review
```

Route both checks through the canonical lifecycle (executable state) and authority surfaces before evidence review; an affordance that fails either is rejected.

### 2. Create the SWE_SEED work contract

The work contract should contain at least:

```yaml
work_request_id:
affordance_id:
route:
required_context:
artifact_contract:
proof_commands:
trace_policy:
expected_result:
```

### 3. Execute through SWE_SEED

SWE_SEED performs the software work, runs the proof commands, captures the evidence, and produces an immutable evidence bundle.

Example shape:

```yaml
evidence_bundle:
  work_request_id:
  affordance_id:
  artifact_references:
  context_references:
  commands_executed:
  exit_codes:
  proof_results:
  expected_result:
  observed_result:
  trace_references:
  authority_references:
  timestamps:
```

SWE_SEED reports observed facts. It does not promote capability.

### 4. Submit evidence to GodSpeed-Agent

GodSpeed-Agent validates:

* the evidence bundle is complete;
* required values are non-empty;
* the affordance exists;
* the affordance was executable;
* the evidence belongs to the identified work request;
* the result is attributable;
* the settlement signal is reliable enough to use;
* the record has not already been processed.

Missing expected or observed results must never become usable merely because two empty strings compare as equal.

### 5. Classify settlement

GodSpeed-Agent classifies the evidence according to its canonical settlement rules.

The list below is conceptual vocabulary for discussion, not a wire contract:

```text
usable
provisional
pending
quarantined
rejected
```

Adapters must emit only the canonical settlement statuses the runtime defines (see the ledger reference), mapping any implementation status onto that closed set. A passing SWE_SEED proof is relevant evidence, but it does not force a usable settlement classification.

### 6. Persist before deriving capability

GodSpeed-Agent writes the settlement through the canonical ledger and storage authority.

Capability state must be derived from persisted settlement records—not from:

* a caller-provided settlement count;
* transport metadata;
* a single event payload;
* an adapter-local cache;
* an alternate JSONL file;
* an unverified aggregate.

### 7. Update capability only from canonical evidence

Capability promotion must consider:

* usable settlement history;
* relevant variation;
* performance;
* attribution and reliability;
* attention or orchestration reduction;
* transfer;
* recovery after disruption;
* failure and decay evidence.

A partial or provisional result cannot become metabolized merely because a caller sends `settlement_count: 3`.

### 8. Feed learning back without transferring authority

GodSpeed-Agent may emit:

```text
SettlementRecorded
CapabilityUpdated
RepetitionPlanned
LearningProposalRecorded
AffordanceStateChanged
```

SWE_SEED may consume these events to improve future routes, context requirements, proof contracts, or harness behavior.

This feedback does not transfer ownership of settlement or capability state to SWE_SEED.

## Adapter Rule

Any event adapter between SWE_SEED and GodSpeed-Agent must be a thin translation layer.

It may:

* validate event shape;
* map external fields to canonical commands;
* enforce schema versions;
* calculate idempotency keys;
* call the canonical GodSpeed-Agent lifecycle service;
* translate canonical results into outbound events.

It must not:

* independently decide settlement;
* independently update capability;
* accept caller-owned metabolization state;
* maintain a parallel capability ledger;
* write developmental truth outside canonical storage.

```text
Adapter translates.
Domain authority decides.
Ledger persists.
```

## Storage Rule

All developmental truth must use one canonical storage authority.

This includes:

* affordances;
* settlements;
* capabilities;
* trajectories;
* repetition schedules;
* learning proposals.

Developmental records must receive the same:

* locking;
* sequencing;
* checksums;
* redaction;
* indexing;
* validation;
* quarantine;
* backup;
* migration handling.

A conveniently queryable side file is not an acceptable second source of truth.

## Invariants

The implementation is incorrect if any of these statements can become true:

1. An unknown affordance can be settled.
2. A potential or possibility can be metabolized.
3. Missing evidence is classified as usable.
4. Partial evidence can become metabolized.
5. A caller can force promotion by supplying a settlement count.
6. SWE_SEED and GodSpeed-Agent both own capability state.
7. An event adapter contains separate lifecycle rules.
8. Learning proposals bypass canonical storage.
9. A public integration is missing from the built distribution.
10. The default test and validation commands ignore the integration.

## Architecture Test

For any function, class, module, event, or storage path, ask:

```text
Is this about executing and proving this software job?
→ SWE_SEED

Is this about interpreting consequence and changing developmental state?
→ GodSpeed-Agent

Is this about deciding whether an action is authorized before side effects?
→ SEA-Forge
```

When a component appears to answer more than one of these questions, split the responsibilities or route it through the canonical authority.

## Final Model

```text
SWE_SEED produces execution evidence.
GodSpeed-Agent produces developmental meaning.
SEA-Forge provides runtime authority.
DomainForge provides executable domain meaning.
```

For the two-harness relationship specifically:

```text
SWE_SEED makes software work verifiable.
GodSpeed-Agent makes verified outcomes cumulative.
```
