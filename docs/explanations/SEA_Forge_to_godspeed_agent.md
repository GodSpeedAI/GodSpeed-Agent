# Relationship to SEA-Forge

SEA-Forge, SWE_SEED, and GodSpeed-Agent participate in one governed capability loop, but they hold different kinds of authority.

```text
SEA-Forge = action authority
SWE_SEED = software execution and proof authority
GodSpeed-Agent = settlement and developmental authority
```

Canonical shorthand:

```text
SEA-Forge authorizes the attempt.
SWE_SEED proves the work.
GodSpeed-Agent metabolizes the result.
```

These responsibilities must not collapse into one another.

## The Three Questions

Every governed software-work cycle contains three separate questions.

### 1. May this action happen?

SEA-Forge answers this question.

It evaluates:

```text
actor
+ operation
+ resource
+ context
+ declared policy
→ allow / deny / escalate
```

SEA-Forge acts before consequential side effects whenever authority evaluation is required.

Examples include:

* reading protected files;
* writing files;
* invoking APIs;
* modifying infrastructure;
* creating commits;
* opening or merging pull requests;
* using credentials;
* delegating to another agent;
* changing production systems;
* performing an action above a defined risk threshold.

SEA-Forge records the authority decision and the evidence supporting it.

### 2. Did the software work satisfy its contract?

SWE_SEED answers this question.

It manages the software-work loop:

```text
route
→ required context
→ work instructions
→ artifact
→ proof command
→ execution trace
```

SWE_SEED determines whether the required artifact was produced and whether the declared software proof passed.

It records facts such as:

* files created or changed;
* commands executed;
* test results;
* lint and type-check results;
* build results;
* exit codes;
* generated artifacts;
* trace references;
* authority-decision references;
* deviations from the work contract.

SWE_SEED does not decide whether the organization has acquired or metabolized a capability.

### 3. What does this outcome teach the system?

GodSpeed-Agent answers this question.

It determines:

* whether the work corresponded to a real affordance;
* whether the outcome reached settlement;
* whether the settlement signal is reliable;
* what error became visible;
* whether capability evidence should change;
* whether the work should repeat under variation;
* whether a learning proposal should be created;
* whether a shortcut has become earned;
* whether the result expands the current affordance horizon.

GodSpeed-Agent acts on canonical settlement and developmental records. It must not infer capability merely because SEA-Forge allowed an action or because SWE_SEED reported passing tests.

## Full Governed Capability Loop

```text
Desired direction
    ↓
GodSpeed-Agent identifies or reviews an affordance
    ↓
SWE_SEED forms a software-work contract
    ↓
SEA-Forge evaluates required authority
    ↓
allow / deny / escalate
    ↓
SWE_SEED executes the authorized work
    ↓
SWE_SEED produces artifact, proof, and trace
    ↓
GodSpeed-Agent validates the evidence relationship
    ↓
GodSpeed-Agent classifies settlement reliability
    ↓
Canonical settlement is persisted
    ↓
Capability state is derived from settlement history
    ↓
Repetition, correction, quarantine, retirement, or metabolization
```

This is not necessarily one linear request-response transaction. A job may require several SEA-Forge authority decisions as SWE_SEED encounters different protected operations.

Example:

```text
Read public source file
→ no elevated authority required

Write application source
→ SEA-Forge allow

Run local tests
→ allowed by workspace policy

Access deployment secret
→ SEA-Forge escalate

Modify production infrastructure
→ SEA-Forge deny until approval
```

SWE_SEED must preserve these authority decisions inside the evidence bundle so GodSpeed-Agent can interpret the final outcome in context.

## SEA-Forge Owns

SEA-Forge owns:

* actor identity and authenticated context;
* operation and resource classification;
* declared authority evaluation;
* policy enforcement before consequential action;
* allow, deny, and escalate decisions;
* approval requirements;
* authority evidence;
* tamper-evident action-decision records;
* runtime enforcement;
* policy and authority drift detection;
* fail-closed behavior for protected operations.

SEA-Forge may say:

```text
This actor is permitted to perform this operation on this resource
under these conditions.

This operation requires human approval.

This operation is prohibited.

This authority decision was evaluated against these policies.
```

SEA-Forge must not say:

```text
The software change is correct.

The proof contract passed.

The capability is metabolized.

The organization learned this pattern.
```

## SWE_SEED Owns

SWE_SEED owns:

* software-task routing;
* context loading;
* work instructions;
* artifact requirements;
* proof commands;
* repository-oriented hooks;
* software execution traces;
* test, build, lint, and validation evidence;
* work-contract pass or failure;
* evidence packaging for downstream interpretation.

SWE_SEED may request authority from SEA-Forge, but it does not grant itself authority.

SWE_SEED may report a passing proof, but it does not promote capability.

## GodSpeed-Agent Owns

GodSpeed-Agent owns:

* desired directions;
* horizon and affordance review;
* payment estimates;
* settlement classification;
* settlement reliability;
* developmental memory;
* capability lifecycle;
* variation requirements;
* transfer and recovery evidence;
* repetition scheduling;
* learning proposals;
* earned compression;
* horizon updates.

GodSpeed-Agent consumes SEA-Forge and SWE_SEED evidence, but it does not replace either system.

## Evidence Relationships

A complete developmental record should preserve three distinct evidence classes.

```yaml
authority_evidence:
  decision_id:
  actor:
  operation:
  resource:
  context:
  decision: allow | deny | escalate
  policy_references:
  approval_references:
  timestamp:

execution_evidence:
  work_request_id:
  route:
  artifact_references:
  commands_executed:
  proof_results:
  expected_result:
  observed_result:
  trace_references:
  authority_decision_references:

developmental_evidence:
  affordance_id:
  settlement_id:
  settlement_classification:
  reliability:
  error_delta:
  payment_variance:
  capability_effect:
  variation_dimensions:
  repetition_decision:
  learning_proposal_reference:
```

These evidence classes may be linked, but they must not be treated as interchangeable.

```text
Authority evidence proves permission was evaluated.

Execution evidence proves the work attempt and its technical result.

Developmental evidence records what the consequence means for future capability.
```

## Critical Non-Equivalences

The implementation must preserve these distinctions:

```text
authorized action ≠ correct action

correct software output ≠ reliable settlement

passing test ≠ metabolized capability

denied action ≠ failed capability

escalated action ≠ failed work contract

repeated work ≠ variation-tested capability

available tool ≠ absorbed capability
```

A denied SEA-Forge decision may indicate that governance worked correctly. It should not be recorded as SWE_SEED execution failure or capability failure.

A SWE_SEED proof failure may still produce a useful GodSpeed-Agent settlement because the failure exposes a real error and creates reliable developmental evidence.

A SWE_SEED proof pass may still produce provisional or quarantined settlement if attribution, corroboration, externalities, or evidence completeness are weak.

## Failure Ownership

Route failures according to the layer that owns the violated invariant.

### SEA-Forge failure

Examples:

* an unauthorized side effect occurred;
* policy was not evaluated;
* the wrong actor or resource was used;
* an escalation was bypassed;
* authority evidence is missing;
* protected execution failed open.

### SWE_SEED failure

Examples:

* required context was not loaded;
* the expected artifact was not produced;
* proof commands were not run;
* tests failed;
* the route was incorrect;
* the execution trace is incomplete.

### GodSpeed-Agent failure

Examples:

* an unknown affordance was settled;
* unreliable evidence updated capability;
* a caller-provided count forced metabolization;
* variation was not considered;
* learning records bypassed canonical storage;
* capability promotion did not derive from persisted settlements.

## Adapter Rule

Adapters between these systems translate contracts. They do not inherit domain authority.

An adapter may:

* validate schemas;
* translate identifiers;
* attach correlation IDs;
* calculate idempotency keys;
* transport evidence;
* call the canonical owner;
* publish the owner’s resulting event.

An adapter must not independently:

* authorize protected action;
* declare software proof successful;
* classify developmental settlement;
* update capability;
* maintain a competing truth ledger.

```text
Transport moves evidence.
Domain services interpret evidence.
Canonical ledgers preserve truth.
```

## Boundary Test

For every component, ask:

```text
Does it decide whether an action may occur?
→ SEA-Forge

Does it execute and prove a software-work contract?
→ SWE_SEED

Does it interpret consequence and update developmental state?
→ GodSpeed-Agent
```

If one component answers more than one of these questions, inspect it for responsibility leakage.

## Canonical Stack

```text
DomainForge defines the domain and executable meaning.

SEA-Forge governs authority before consequential action.

SWE_SEED routes, executes, and proves agentic software work.

GodSpeed-Agent converts reliable settled outcomes into developmental
memory, repetition decisions, and capability evidence.
```

Final formulation:

```text
DomainForge tells the system what things mean.
SEA-Forge determines what actors may do.
SWE_SEED proves what software work occurred.
GodSpeed-Agent determines what the system has learned to do reliably.
```
