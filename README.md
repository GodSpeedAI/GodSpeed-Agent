# GodSpeed-Agent

### Make the next move depend on what reality actually taught you.

An agent completes a difficult task.

The tests pass.

The work settles.

Now what?

Most systems throw away the most valuable part.

They keep the artifact, maybe the transcript, and approach the next task as if nothing fundamental changed.

But successful work can change what is possible next.

A path that required constant supervision may now require less.

A failure may expose a distinction nobody represented before.

A repeated pattern may become reliable enough to reuse.

A shortcut may finally be earned.

A capability you thought you had may turn out to exist only under one narrow condition.

And while work is still unfolding, the shape of the trajectory itself may reveal whether an agent is recovering from difficulty or simply spending more budget on the same failure.

Those are developmental changes.

**GodSpeed-Agent is a CognitiveOS navigation and capability-formation controller. It turns desired directions and current conditions into affordable next moves, evaluates settlement evidence, maintains developmental memory, and promotes repeated successful work into capability only when the evidence justifies it.**

The controller combines three forms of reasoning:

```text
deterministic constraints
        +
computational navigation
        +
empirically calibrated trajectory priors
```

Hard gates decide which paths are eligible.

Explicit CognitiveOS state determines what the system can currently represent, reach, pay for, recover from, and settle.

An advisory predictive model can then help distinguish execution trajectories that appear to be making progress from trajectories that are beginning to spiral.

Prediction informs navigation.

It does not become authority.

Plainly:

> **GodSpeed-Agent decides what should become easier to do next because of what actually happened before.**

Its developmental loop is:

```text
desired direction
      ↓
current horizon
      ↓
available affordances
      ↓
payment + constraints
      ↓
next affordable move
      ↓
execution
      ↓
settlement evidence
      ↓
developmental memory
      ↓
capability update
      ↓
changed future horizon
```

And as empirical history accumulates, another loop begins to strengthen it:

```text
historical trajectories
        ↓
pre-outcome behavioral signals
        ↓
calibrated predictive priors
        ↓
current horizon review
        ↓
real execution
        ↓
local settlement
        ↓
future calibration
```

GodSpeed-Agent is local-first.

The current implementation is a Python runtime, CLI, MCP surface, developmental ledger, computational model, reporting layer, external evidence adapter, and optional local semantic-memory integration.

It is not the executor.

It is not the authority layer.

It is not the software-work harness.

Its object is **development over time**.

---

## The missing question after “done”

Most agent systems optimize for:

```text
request
   ↓
work
   ↓
result
```

That is useful.

It leaves another question unanswered:

> **What should this result change about the system's future behavior?**

Suppose an agent successfully fixes a database migration problem.

One response is:

```text
Task complete.
```

Another is:

```text
This class of migration failure has settled once.

The agent required heavy operator guidance.

The same pattern has not been tested under another database version.

Recovery from a failed attempt required manual intervention.

Do not promote this to direct capability yet.
```

Later, perhaps:

```text
The pattern has now settled repeatedly.

It survived materially different migrations.

Operator intervention fell.

The agent recovered after a failed attempt.

The route now has stronger capability standing.
```

That is a different kind of system.

GodSpeed-Agent works on that second problem.

---

## A successful task does not automatically create capability

Access is not capability.

Knowing the procedure is not capability.

Running the tool once is not capability.

A passing test is not capability.

One accepted settlement is not capability.

Even several successful repetitions may not be enough if they are effectively the same case.

A capability claim becomes stronger when performance survives:

```text
repetition

relevant variation

transfer

reduced orchestration burden

recovery after disruption

continued evidence quality
```

The important progression is closer to:

```text
potential
   ↓
possibility
   ↓
reachable pathway
   ↓
affordance
   ↓
attempt
   ↓
settlement evidence
   ↓
repeated settlement
   ↓
variation
   ↓
transfer
   ↓
recovery
   ↓
reduced burden
   ↓
capability
   ↓
substrate
```

The runtime may use conservative numerical thresholds as implementation rules.

Those thresholds are not the definition of capability.

Evidence is.

---

## The horizon is the real starting point

A desired future state is not yet a path.

Suppose the direction is:

```text
Make releases autonomous.
```

That may be strategically useful.

It is not currently spendable merely because the system can describe it.

The current horizon might contain:

```text
automatically build release artifacts

run release verification

generate a release candidate

prepare a deployment

request deployment approval
```

while:

```text
autonomously deploy production changes
```

remains blocked by authority, recovery, evidence, or capability.

GodSpeed-Agent begins from that distinction.

A **horizon** is the portion of possibility the observer can presently make consequential given:

```text
representation

capability

resources

authority

payment capacity

settlement access

recovery capacity
```

The system should navigate from what can actually be spent.

Not from the most attractive thing it can name.

---

## Possibility and affordance are different

This distinction is central to GodSpeed-Agent.

A possibility might be:

```text
use an autonomous agent to deploy production
```

For that to become a current affordance, the path must be sufficiently:

```text
visible

reachable

authorized

payable

executable

recoverable

settleable
```

If authorization is absent, the path is not currently spendable.

If the required capability does not exist, it is not currently spendable.

If failure would consume the recovery reserve, it is not currently spendable.

If no meaningful consequence can be observed afterward, it is not a useful developmental move.

GodSpeed-Agent therefore asks:

> **Which path can this observer actually pay for and learn from now?**

rather than:

> What is theoretically possible?

---

## Start with one direction

Create a desired direction:

```bash
uv run godspeed-nav start-direction \
  --label "Enterprise runtime" \
  --statement "Connect workflow commands"
```

That records a direction.

It does not pretend the direction is already a plan.

Next, review the visible horizon:

```bash
uv run godspeed-nav review-horizon \
  --direction-id <direction-id> \
  --candidates '[
    {
      "id": "cli-loop",
      "statement": "Use runtime CLI",
      "pathway": "call CLI",
      "costs": {"time": 1},
      "capacities": {"time": 5},
      "expected_horizon_delta": 4,
      "risk": 0
    }
  ]'
```

The important question is not whether `cli-loop` sounds useful.

It is whether it is currently a spendable path.

If it settles, record the consequence:

```bash
uv run godspeed-nav record-settlement \
  --affordance-id cli-loop \
  --before '{"cli":0}' \
  --after '{"cli":1}' \
  --payment '{"time":1}' \
  --evidence '["cli workflow test passed"]' \
  --horizon-delta 4
```

Then inspect what the history actually changed:

```bash
uv run godspeed-nav developmental-report
```

That is the basic developmental loop.

---

## Desired direction is not the same as a goal

GodSpeed-Agent can navigate toward more than terminal objectives.

A direction may represent:

```text
goal
need
problem
opportunity
obligation
mission
open direction
```

Those have different dynamics.

A goal terminates when the specified state is reached.

A mission may not terminate.

A problem is a present discrepancy to remove.

An opportunity may expire.

An obligation may come from external authority.

Treating all of them as generic goals destroys useful information about how navigation should proceed.

The runtime therefore treats desired direction as the pressure selecting which paths matter.

---

## Representation changes what becomes visible

Sometimes the next move is blocked because the system lacks resources.

Sometimes it is blocked because the system cannot yet represent the problem well enough.

Consider:

```text
Improve deployment reliability.
```

That is broad and abstract.

The immediate answer may not be another action.

The affordable move may be representational:

```text
Identify which deployment failure class is recurring.
```

Then:

```text
Distinguish configuration failures
from authority failures
from environment failures.
```

Then:

```text
Define one observable transition
and its settlement criterion.
```

Only then may a concrete execution path become visible.

GodSpeed-Agent explicitly models representational state instead of assuming every navigation problem is an action-selection problem.

---

## General, specific, abstract, and concrete are independent

CognitiveOS uses two representational axes:

```text
General ↔ Specific

Abstract ↔ Concrete
```

These mean different things.

A representation can be:

```text
General + Abstract
"Reliable systems need recovery."

Specific + Abstract
"This service requires idempotent retry semantics."

Specific + Concrete
"On this checkout call, request 123 may be retried
after timeout without creating a second charge."

General + Concrete
"A collection of real retry incidents across services."
```

Moving directly from a broad principle to a highly situated action may sometimes be justified.

Sometimes it is an unearned jump.

GodSpeed-Agent can price the representational move itself instead of assuming representation is free.

---

## Payment is a vector

Every move costs something.

Not only money.

GodSpeed-Agent can reason about currencies such as:

```text
time
attention
compute
coordination
verification
recovery
maintenance
risk
opportunity
representational effort
```

Those currencies should not automatically collapse into one number.

Five dollars of compute cannot necessarily compensate for insufficient operator attention.

A low engineering cost cannot compensate for irreversible risk.

A high expected payoff cannot buy authority the system does not have.

The controller therefore separates **hard gates** from **ranking**.

---

## Some constraints are gates

A path should not receive a high score and then outweigh a governance violation.

Before ranking a candidate, the system asks questions such as:

```text
Is it authorized?

Can its consequence be observed?

Can the required payment be afforded?

Does risk remain below the applicable ceiling?

Does the system retain enough recovery capacity?

Does the move violate a non-compensable constraint?
```

If the answer fails a hard gate, the path is blocked or escalated.

Only paths that survive those conditions should enter continuous ranking.

Conceptually:

```text
governance
payment capacity
settlement access
irreversible-harm constraints
recovery constraints
        ↓
hard gates
        ↓
eligible affordances
        ↓
ranking / prediction
```

A scoring function should never be able to optimize its way through a boundary that was meant to be non-compensable.

---

## Payment fit is not resource inventory

An observer may gain more resources without gaining a larger useful horizon.

For example:

```text
more compute
more tools
more context
more agents
```

can increase the number of visible possibilities.

They do not automatically create the ability to use those possibilities well.

The relevant question is whether those resources can be converted into a reachable, governable, recoverable, settleable path.

Resources can increase affordance inventory.

They do not guarantee affordance utilization.

And neither automatically guarantees horizon expansion.

GodSpeed-Agent keeps those transitions separate.

---

# Predictive navigation

## The controller can learn from trajectories without letting prediction become authority

GodSpeed-Agent's navigation layer is not limited to fixed heuristics and hand-authored scoring.

The runtime includes an empirically calibrated advisory predictive model that can estimate whether an agent execution trajectory appears likely to resolve successfully before the agent exhausts its available execution budget.

The current model is deliberately simple and inspectable:

```text
scikit-learn LogisticRegression
class_weight = "balanced"
```

It operates on **pre-outcome trajectory features**.

That timing matters.

The model is intended to recognize patterns in the path toward an outcome without being handed the outcome itself.

Its role is not:

```text
predict success
      ↓
grant permission
```

It is:

```text
eligible path
      ↓
observe trajectory shape
      ↓
estimate viability
      ↓
inform horizon review
```

The predictor can be wrong.

That is why it advises the controller instead of governing it.

---

## Errors themselves are not the important signal

Real problem solving contains errors.

An agent encountering a compiler error does not necessarily mean the trajectory is failing.

An agent running a command that does not work does not necessarily mean the task is doomed.

The more useful question is:

> **What happens after the error?**

One trajectory looks like:

```text
error
  ↓
inspect
  ↓
adapt
  ↓
new observation
  ↓
progress
```

Another looks like:

```text
error
  ↓
repeat
  ↓
same error
  ↓
repeat
  ↓
more payment
```

Both contain errors.

Only one is recovering.

That distinction is exactly the kind of trajectory structure the predictive layer is meant to expose.

---

## What the current model observes

The latest calibration model uses eleven pre-outcome features.

The original computational features include signals related to:

```text
predicted payment

actual payment

payment error

horizon-related change

risk estimate

debt estimate
```

The latest calibration added richer behavioral signals.

### Error recovery ratio

```text
error_recovery_ratio
```

Measures how often an error observation is followed by a subsequent non-error observation.

It is a rough indicator of whether the trajectory is recovering instead of repeatedly colliding with the same failure.

---

### Tool diversity

```text
tool_diversity_count
```

Counts distinct tools used during the trajectory.

Tool diversity can provide information about whether the agent is decomposing and investigating the problem rather than repeatedly exercising one failing mechanism.

It is a predictive feature.

It is not a rule that more tools are always better.

---

### Action-observation balance

```text
action_observation_ratio
```

Measures assistant actions relative to tool observations.

This gives the model information about how much acting is occurring relative to feedback from the environment.

---

### Action pacing

```text
avg_actions_per_step
```

Represents the average number of actions taken per trajectory step.

It provides another view of execution pacing and granularity.

---

### Dataset context

```text
dataset_id
```

Preserves benchmark-environment identity as a model feature.

This improves representation of the current mixed calibration distribution but also means the present evaluation should **not** be interpreted as proof of generalization to completely unseen agent environments.

That stronger claim requires separate evaluation.

---

## Current empirical result

The current calibration run is:

```text
hf-calibration-005-features
```

It was trained from external agent trajectories sourced from:

```text
SWE-Gym / OpenHands Sampled Trajectories

OpenThoughts / AgentTrove

Nebius / SWE-agent trajectories
```

The pipeline scanned:

```text
8,100 raw rows
```

and produced:

```text
7,659 normalized records

6,497 usable external proxy settlements

1,162 rejected low-confidence or unlabeled records
```

The usable calibration set contained:

```text
1,289 successes  (19.8%)

5,208 failures   (80.2%)
```

The evaluation used a stratified 80/20 split.

The held-out test set contained:

```text
1,300 unseen test samples
```

with approximately the same success-rate distribution.

### Held-out results

| Metric            | Current result |
| ----------------- | -------------: |
| ROC-AUC           |     **0.8266** |
| Balanced accuracy |     **74.28%** |
| F1                |     **0.5208** |
| Average precision |     **0.6291** |
| Success recall    |      **80.2%** |
| Brier loss        |     **0.1771** |

The confusion matrix on the held-out set was:

```text
                   Actual Failure    Actual Success

Predicted Failure:      712               51

Predicted Success:      330              207
```

The model correctly identified 207 of 258 successful held-out trajectories.

The result supports a narrow but useful claim:

> **The current pre-outcome representation contains meaningful predictive signal for distinguishing successful and failed trajectories within the evaluated mixed distribution.**

It does not establish universal agent-success prediction.

---

## The calibration improved as the representation improved

The current model is the fifth major calibration iteration.

The progression was:

| Run            | Usable traces | Datasets | Features |    ROC-AUC | Balanced Accuracy |         F1 | Avg. Precision |
| -------------- | ------------: | -------: | -------: | ---------: | ----------------: | ---------: | -------------: |
| `001`          |           500 |        1 |        6 |     0.6812 |            0.6410 |     0.3210 |         0.4120 |
| `002`          |           500 |        1 |        6 |     0.6954 |            0.6520 |     0.3440 |         0.4350 |
| `003`          |         1,943 |        2 |        6 |     0.7481 |            0.7015 |     0.4038 |         0.5120 |
| `004-natural`  |         6,497 |        3 |        6 |     0.7995 |            0.7191 |     0.4968 |         0.5906 |
| `005-features` |     **6,497** |    **3** |   **11** | **0.8266** |        **0.7428** | **0.5208** |     **0.6291** |

The useful lesson is not simply that a larger dataset improved performance.

The largest recent improvement came from changing what the controller could represent about the trajectory.

Earlier features mostly measured how much error or payment occurred.

The later representation added information about **recovery dynamics and execution behavior**.

The controller became more discriminating because its representation of the path became richer.

That is directly consistent with the larger CognitiveOS premise:

> Better navigation often begins with a better representation of what is happening.

---

## The predictor was audited for outcome leakage

A trajectory-success model is useless if the answer leaks into the inputs.

The latest calibration therefore includes a feature-leakage audit.

For `hf-calibration-005-features`:

```text
leakage_detected: false

leaked_features: []
```

The audit reported no leaked outcome features.

Individual feature correlations with the target remained modest rather than revealing an obvious proxy label.

This does not prove that every conceivable form of leakage is impossible.

It establishes that the implemented audit found no post-outcome feature leakage in the current calibration frame.

That is the claim the evidence supports.

---

## Current evaluation does not yet prove unseen-environment transfer

The current result is a stratified train/test split over the combined three-dataset distribution.

All three datasets appear in the overall calibration environment.

`dataset_id` is also one of the model features.

So this result should **not** be described as:

```text
proven cross-domain generalization
```

or:

```text
prediction transfers to arbitrary agent systems
```

Those are stronger claims.

A stronger next evaluation would train on some environments and test entirely on one that the model did not see during fitting.

Another useful test is frozen-model evaluation against local Gauntlet trajectories.

Until those evaluations settle, the present claim stays narrower:

> The model discriminates useful trajectory structure within the evaluated external proxy distribution.

That is already useful.

There is no need to inflate it.

---

## External trajectories provide priors. Local settlement provides standing.

Every imported calibration record is classified as:

```text
external-proxy-settlement
```

That classification is load-bearing.

External trajectory datasets can teach GodSpeed-Agent statistical regularities such as:

```text
trajectories with this pattern
tend to recover

trajectories with this pattern
tend to fail

this amount of payment often accompanies
this kind of trajectory

this behavior often precedes successful resolution
```

They cannot establish:

```text
this project possesses this capability

this agent can reliably perform this work here

this route has metabolized

this action is authorized

this capability transfers to the current environment
```

External experience influences expectation.

Local consequence changes developmental state.

Conceptually:

```text
external trajectories
        ↓
empirical priors
        ↓
navigation advice


local execution
        ↓
local settlement
        ↓
developmental standing
```

This lets GodSpeed-Agent arrive with useful priors without arriving with imaginary capability.

---

## Prediction comes after hard gates

The predictive model does not get to trade probability against governance.

The controller's order matters:

```text
authority
payment capacity
settlement access
irreversible-harm constraints
recovery constraints
        ↓
hard gates
        ↓
eligible paths
        ↓
computational ranking
        ↓
predictive advisory signal
        ↓
horizon review
```

A 99% predicted probability of success cannot:

```text
authorize a prohibited action

create missing settlement access

make an unaffordable payment affordable

remove irreversible downside

replace recovery capacity

turn missing evidence into settlement

promote a route into capability
```

Prediction answers:

> Given the represented execution behavior so far, how viable does this trajectory appear?

It does not answer:

> May we do this?

or:

> Has this become capability?

Those are separate questions.

---

## Computational navigation and empirical prediction are different layers

GodSpeed-Agent now has three distinct forms of control.

### 1. Deterministic constraints

These include hard gates that prediction cannot override.

Examples:

```text
authority

payment ceiling

settlement accessibility

recovery requirements

non-compensable risk
```

---

### 2. Computational navigation

The CognitiveOS mathematical layer represents and scores things such as:

```text
representational burden

payment fit

spendability

risk

debt

expected horizon gain

settlement reliability

capability evidence
```

This makes the framework computable instead of leaving every decision as prose.

---

### 3. Empirical calibration

Historical trajectories provide learned priors about patterns the deterministic representation alone may not capture well.

The current predictive model can contribute a probability-like advisory signal during horizon review.

That signal earns influence empirically.

It does not receive authority merely because it came from machine learning.

---

## The learned model remains inspectable

The current predictive core deliberately uses a straightforward scikit-learn logistic regression rather than hiding the first calibration layer inside a large learned model.

The implementation uses:

```text
LogisticRegression(class_weight="balanced")
```

with the solver iteration budget increased to:

```text
max_iter = 1000
```

after the richer feature matrix exposed a convergence limit in the earlier configuration.

The current solver converges under the corrected configuration.

This implementation can change as evidence improves.

The architecture does not depend on logistic regression specifically.

The load-bearing boundary is:

```text
predictive model
        ↓
advisory signal
```

rather than:

```text
predictive model
        ↓
authority
```

---

## Settlement is where consequence enters the loop

An action does not become developmental evidence merely because it finished.

Something must happen outside the claim itself.

GodSpeed-Agent treats an outcome as a settlement event:

```text
expected
   ↓
attempt
   ↓
observed consequence
   ↓
evidence
   ↓
settlement evaluation
```

Settlement asks:

```text
What happened?

What did we expect?

What payment was spent?

How reliable is the feedback?

What should this change?
```

That final question is why GodSpeed-Agent exists.

---

## Evidence enters provisionally

GodSpeed-Agent can receive externally produced evidence through its public event adapter.

For example:

```text
EvidenceRecorded
```

may contain evidence produced by software verification, RealityTrace, or another system.

Receiving that event does **not** automatically mean:

```text
settlement established
```

and certainly not:

```text
capability established
```

The event is provisional developmental evidence.

The controller evaluates it before emitting stronger state transitions such as:

```text
SettlementRecorded

CapabilityUpdated
```

Otherwise any system capable of producing an `EvidenceRecorded` event could effectively promote itself into capability.

---

## RealityTrace tells GodSpeed-Agent what happened

RealityTrace asks:

> What did we expect, what did we observe, and what difference remains?

GodSpeed-Agent asks:

> What does that evidence justify changing about future navigation?

The relationship is:

```text
expected outcome
      ↓
RealityTrace
      ↓
observed outcome
+ difference
+ evidence
+ provenance
      ↓
GodSpeed-Agent
      ↓
developmental evaluation
      ↓
memory / capability update
```

RealityTrace owns the expected-versus-observed evidence binding.

GodSpeed-Agent owns the developmental consequence.

Observation and development should not collapse into the same system judgment.

---

## Settlement quality matters

Not every outcome should update capability equally.

A feedback signal may be:

```text
timely

delayed

clearly attributable

confounded

corroborated

weakly supported

incentive-aligned

distorted

externally costly
```

GodSpeed-Agent therefore treats settlement reliability as part of the developmental decision.

Weak or corrupted evidence may remain:

```text
provisional

quarantined

pending
```

instead of strengthening capability.

Bad feedback produces bad learning faster than no feedback.

---

## Developmental memory is not ordinary memory

A conversation memory system might store:

```text
The user prefers PostgreSQL.
```

Developmental memory stores something closer to:

```text
This route was attempted.

It required this payment.

This evidence settled.

This failure repeated.

This correction closed the residual.

This variation broke the pattern.

This recovery path worked.

Operator burden decreased after repetition.
```

The object being remembered is not simply information.

It is the history of transformation and consequence.

That makes developmental memory useful for deciding what should become easier next.

---

## The ledger keeps the messy history

Development is not a clean sequence of wins.

Useful history includes:

```text
attempts

failures

payments

residuals

corrections

retries

recoveries

settlements

critiques

promotions

demotions
```

GodSpeed-Agent stores developmental records locally.

The current implementation uses JSONL-backed ledgers under a workspace-specific storage root such as:

```text
.godspeed-harness/
```

The historical naming remains for compatibility.

The conceptual product is GodSpeed-Agent, not a generic harness.

---

## A project owns its capability history

Keep the GodSpeed-Agent repository separate from the project using it.

For example:

```text
/home/user/projects/
  godspeed_agent/
  my-project/
    src/
    tests/
    ingest/
    .godspeed-harness/
```

Point storage-backed commands at the receiving project:

```bash
uv run godspeed-nav start-direction \
  --workspace-root /home/user/projects/my-project \
  --storage-root .godspeed-harness \
  --label "Initial project direction" \
  --statement "Build the first usable slice"
```

The project retains its ordinary:

```text
code
tests
documentation
tools
```

GodSpeed-Agent maintains the developmental record associated with that project.

The runtime does not become the project.

---

## External capability is potential until locally earned

A project may discover something useful elsewhere:

```text
library
agent
repository
skill
workflow
model
```

That is not automatically local capability.

Suppose another project has a reliable PDF-ingestion pipeline.

For the receiving project it initially represents:

```text
potential
```

A spendable path still requires:

```text
compatible implementation

license

authority

payment capacity

integration path

settlement plan
```

Only then can it become a current affordance.

And even after successful integration, one use is not metabolization.

The capability must settle locally under the receiving project's conditions.

GodSpeed-Agent's absorption workflow preserves that distinction.

---

## Absorption does not mean copying

External material can be staged under a project ingest path such as:

```text
ingest/absorption/<candidate>/
```

The system can evaluate whether it is:

```text
potential

possible

absorbable
```

based on factors such as:

```text
pathway

payment

license

policy

settlement access
```

The receiving project has not learned something merely because files were copied into it.

Capability has to survive local consequence.

---

## Repetition should reduce burden

A useful capability does more than keep succeeding.

It should often become cheaper to re-enter.

At first:

```text
operator supplies detailed context

operator selects tool

operator checks every step

operator recovers manually
```

Later:

```text
system recognizes situation

system selects proven route

operator reviews exceptions
```

That reduction in orchestration burden is developmental evidence.

If repeated executions still require the same amount of operator reconstruction, something may have been repeated without becoming substrate.

---

## Transfer matters

A route that works only in one exact situation may be memorized rather than capable.

Suppose an agent successfully resolves:

```text
timeout in service A
```

several times.

Now it encounters:

```text
timeout in service B
```

If the underlying pattern transfers, capability evidence strengthens.

If the agent collapses because the filenames changed, the prior successes were narrower than they appeared.

GodSpeed-Agent should preserve the variation classes under which capability was actually demonstrated.

---

## Recovery matters

A capability that works only when nothing interrupts it is brittle.

Useful evidence includes whether the observer can recover from:

```text
failed invocation

bad intermediate state

tool outage

context loss

process restart

incorrect hypothesis

environmental change
```

without reconstructing the entire capability from zero.

Recovery therefore participates in capability standing.

It is not merely an operational convenience.

The predictive calibration reinforces this idea experimentally: trajectory recovery behavior contains useful signal about eventual success.

That does not make `error_recovery_ratio` the definition of recovery capability.

It makes recovery dynamics empirically worth paying attention to.

---

## Metabolization is earned compression

As capability stabilizes, intermediate reasoning and orchestration may compress.

That is desirable.

An expert does not need to consciously replay every beginner step.

An agent does not need to search the entire transformation space every time a proven route applies.

But the shortcut is only earned when the skipped path has been supported by settlement history.

Otherwise:

```text
faster
```

can mean:

```text
less checking
```

rather than:

```text
more capability
```

GodSpeed-Agent's job is partly to distinguish those cases.

---

## Capability can weaken

Promotion should not become permanent mythology.

A route can become less reliable because:

```text
environment changed

dependency changed

policy changed

model changed

task distribution changed

previous assumptions stopped holding

recovery degraded
```

Historical capability evidence remains useful.

It does not override current conditions.

The controller must be able to demote, quarantine, or require renewed verification when current settlement no longer supports previous standing.

---

## Historical capability is evidence, not authority

Suppose an agent has repeatedly deployed staging environments successfully.

That may support capability.

It does not automatically authorize:

```text
production deployment
```

today.

Authority remains contextual.

Governance can change.

Risk can change.

A capable actor can still be prohibited from an action.

GodSpeed-Agent therefore does not treat capability as permission.

SEA-Forge owns runtime authority in the broader stack.

---

## The controller does not execute the work

GodSpeed-Agent may select or recommend a current affordance.

It does not need to become the system that performs every transformation.

Within the broader stack:

```text
GodSpeed-Agent
selects developmental next move
        ↓
Context Kernel
supplies relevant context
        ↓
SWE_SEED
defines software-work contract
        ↓
SEA-Forge
authorizes consequential operations
        ↓
Gauntlet
executes difficult long-horizon work
        ↓
RealityTrace
binds expected and observed result
        ↓
GodSpeed-Agent
evaluates developmental consequence
```

The loop closes back at GodSpeed-Agent.

That is why its object is not task execution.

Its object is how task history changes future spendability.

---

## SWE_SEED and GodSpeed-Agent solve different problems

SWE_SEED asks:

> What kind of software task is this, what context does it require, what artifact should exist, and what proof must run?

GodSpeed-Agent asks:

> What does the evidence from this and prior work justify about future capability?

Conceptually:

```text
SWE_SEED
route + context + artifact + proof
        ↓
software work
        ↓
proof evidence
        ↓
GodSpeed-Agent
developmental evaluation
```

GodSpeed-Agent consumes SWE_SEED evidence.

It does not reproduce SWE_SEED's:

```text
routing

host hooks

trace machinery

proof gating
```

---

## Context Kernel and GodSpeed-Agent solve different memory problems

Context Kernel asks:

> What relevant source material does this task need now?

GodSpeed-Agent asks:

> What has prior settlement taught us about what this system can reliably do?

Those are both forms of memory.

They are not interchangeable.

```text
Context Kernel
retrieval memory

GodSpeed-Agent
developmental memory
```

One helps the agent know.

The other helps the system decide what experience has earned.

---

## Gauntlet and GodSpeed-Agent solve different control problems

Gauntlet manages execution over a long horizon:

```text
agents

tools

critics

verification

correction

recovery

bounded retries
```

GodSpeed-Agent manages development across runs:

```text
horizon

affordance

payment

trajectory priors

settlement history

capability

future navigation
```

A Gauntlet run may last hours.

A developmental history may span weeks, months, or many different Gauntlet runs.

This distinction creates an important future empirical test.

A frozen GodSpeed-Agent calibration model can be evaluated against real Gauntlet trajectories without treating those trajectories as training data first.

If the signal transfers, the predictive representation earns stronger standing.

Until then, the current external calibration remains a prior.

---

## DomainForge gives navigation explicit meaning

A `.sea` model can provide a canonical semantic representation of the domain in which navigation occurs.

DomainForge compiles `.sea` into that semantic model.

GodSpeed-Agent can then reason about current and desired states against an explicit representation rather than reconstructing the domain from prose every time.

The division is:

```text
DomainForge
What does this domain mean?

GodSpeed-Agent
Given that represented domain and current evidence,
what affordable move should become consequential next?
```

Representation precedes useful navigation.

It does not dictate the navigation automatically.

---

## RealityTrace gives the controller reality-facing evidence

RealityTrace preserves:

```text
expected state

observed state

difference

evidence

provenance
```

GodSpeed-Agent consumes that information developmentally.

That means a trajectory predictor can say:

```text
this execution currently appears viable
```

while RealityTrace later says:

```text
the expected consequence did not occur
```

Reality wins.

The prediction remains historical evidence about what the controller believed before settlement.

It does not get to rewrite the result.

---

## CEP keeps the developmental semantics portable

CEP, the Canonical Evaluation Protocol, preserves distinctions such as:

```text
claim ≠ evidence

completion ≠ settlement

settlement ≠ capability

authority ≠ capability

possibility ≠ affordance

score ≠ capability
```

GodSpeed-Agent can consume or emit CEP-compatible evaluation records without treating CEP conformance as proof that the underlying claim is true.

CEP preserves evaluation meaning.

GodSpeed-Agent decides developmental consequence.

---

## Computational model

The CognitiveOS mathematical layer projects navigation concepts into executable decision support.

Current and planned computational concerns include:

```text
representational burden

payment fit

hard gates

spendability

risk

debt

expected horizon change

controller ranking

settlement reliability

capability evidence

calibration records

predictive trajectory priors
```

This makes the framework computational.

It does not make computation automatically authoritative.

The runtime follows the conservative order:

```text
hard deterministic gates
        ↓
eligible paths
        ↓
computational ranking
        ↓
advisory learned prediction
        ↓
observer / runtime decision
```

A learned model cannot override governance, payment limits, settlement access, irreversible-harm constraints, or recovery requirements.

---

## Data maturity should govern mathematical ambition

A new system has little local settlement history.

That means there is little local evidence for fitted weights or project-specific prediction.

GodSpeed-Agent can begin with:

```text
explicit gates

deterministic computation

bootstrapped priors

external proxy calibration
```

As local settlement history accumulates, the system can evaluate whether local evidence justifies recalibration of:

```text
payment estimates

risk estimates

horizon-gain estimates

trajectory-success priors

capability predictions
```

Learned prediction earns influence through measured performance.

It does not receive authority because a model exists.

---

## External calibration and local learning should remain separate

The completed calibration pipeline provides a useful warm start from external agent trajectories.

That is different from a project learning from its own developmental history.

The architecture deliberately separates:

```text
external-proxy-settlement
```

from:

```text
local settlement evidence
```

The first can help answer:

> What usually happens to trajectories shaped like this?

The second answers:

> What happened here, under our conditions?

Those are both useful.

Only one directly changes local developmental standing.

---

## Current computational surfaces

The CLI exposes deterministic computation:

```text
compute-error

estimate-payment

rank-affordances

score-settlement

metabolization

absorbability
```

Workflow-oriented surfaces include:

```text
start-direction

review-horizon

record-settlement

runtime-snapshot

developmental-report

search-developmental-memory

validate
```

Predictive trajectory scoring is integrated into the navigation layer through the runtime's predictive-model adapter and remains advisory to horizon review.

The implementation exposes internal state so controller behavior can be inspected rather than inferred from a final recommendation alone.

---

## Executable affordances are required before settlement

`record-settlement` does not accept arbitrary identifiers and manufacture developmental history from them.

The referenced path must already exist as an executable affordance.

If its current standing is merely:

```text
potential
```

or:

```text
possibility
```

the runtime rejects settlement creation before settlement-derived state is written.

The typed error is:

```text
settlement_requires_executable_affordance
```

This protects a central CognitiveOS distinction:

> A visible destination is not the same thing as a path the system was actually able to spend.

---

## Local-first storage

The current implementation uses:

```text
Python deterministic computation

JSONL developmental ledgers

workspace-local storage

optional RuVector semantic retrieval

scikit-learn predictive calibration
```

The default storage root is:

```text
.godspeed-harness
```

The historical directory name is an implementation detail.

No external API calls are required by default for the core local runtime.

MCP tools operate against local inputs, local computation, and configured local storage.

The external calibration pipeline is a separate training workflow and does not turn ordinary navigation into a mandatory hosted dependency.

---

## Developmental-memory search

Structured developmental records can be searched semantically.

For example:

```bash
uv run python -m godspeed_nav.cli \
  search-developmental-memory \
  --query "timeout recovery"
```

The RuVector bridge lives under:

```text
tools/ruvector/
```

Python remains authoritative for developmental ledgers.

A small Node sidecar uses the published `ruvector` package for similarity search over structured settlement and critique summaries.

Semantic search is retrieval.

It does not alter settlement or capability standing.

---

## Calibration pipeline

The external calibration pipeline streams agent-trajectory datasets, normalizes them into canonical proxy records, derives pre-outcome features, trains the predictive adapter, evaluates the model, and preserves run-scoped calibration artifacts.

The current pipeline lives under:

```text
scripts/settlement_datasets/
```

with source configuration under:

```text
configs/settlement_datasets/
```

Its important boundary is:

```text
external trajectory
      ↓
normalize
      ↓
external-proxy-settlement
      ↓
feature extraction
      ↓
model calibration
      ↓
held-out evaluation
      ↓
advisory prior
```

Not:

```text
external benchmark success
      ↓
local capability
```

That conversion is forbidden by the developmental model.

---

## Calibration data is not local capability evidence

External agent trajectories may help calibrate predictive models.

They do not prove that the local project possesses the same capability.

An external dataset can support:

```text
systems with this trajectory pattern
often succeed
```

It cannot establish:

```text
this system settled this capability here
```

Local capability remains grounded in local consequence.

---

## Self-critique is part of the runtime

GodSpeed-Agent should be able to discover that its own representation is wrong.

That includes:

```text
navigation rules

payment assumptions

capability thresholds

policy assumptions

representational structure

feature representation

learned ranking behavior

predictive calibration
```

A framework that explains every failure without allowing its own structure to become the failure locus is not learning.

It is defending itself.

The runtime therefore preserves self-critique and structural-revision pathways.

---

## Structural revision should be difficult

A failed settlement does not automatically mean the framework should rewrite itself.

The failure may come from:

```text
route selection

capability implementation

payment shortfall

bad evidence

environment drift

incorrect expectation

authority failure

representation defect

predictive-model error
```

Structural revision should occur only after cheaper explanations have been tested and a credible candidate revision exists.

Useful sequence:

```text
divergence
    ↓
diagnosis
    ↓
local correction
    ↓
still unresolved?
    ↓
candidate structural revision
    ↓
sandbox evaluation
    ↓
regression
    ↓
governance decision
    ↓
adopt or rollback
```

The system should be revisable.

It should not be structurally impulsive.

---

## Installation

The package builds as a wheel and source distribution using Hatchling.

The current package name retains earlier `harness` terminology for compatibility.

The product itself is framed as a navigation and capability-formation controller.

### Global CLI

Using `uv`:

```bash
uv tool install godspeed-agent-harness
```

Or install a locally built wheel:

```bash
uv build

uv tool install \
  dist/godspeed_agent_harness-0.1.0-py3-none-any.whl
```

Then:

```bash
godspeed-nav runtime-snapshot
```

---

## Container

Build:

```bash
docker build -t godspeed-agent .
```

Run against a workspace:

```bash
docker run --rm \
  -v "$PWD:/work" \
  -w /work \
  godspeed-agent \
  runtime-snapshot \
  --workspace-root /work \
  --storage-root .godspeed-harness
```

RuVector is optional.

Enable it during image build with:

```bash
docker build \
  --build-arg INSTALL_RUVECTOR=1 \
  -t godspeed-agent .
```

---

## Development installation

Install dependencies:

```bash
uv sync --extra dev
```

Run tests:

```bash
uv run pytest -q
```

If using the local RuVector bridge:

```bash
pushd tools/ruvector >/dev/null
npm install
popd >/dev/null
```

---

## Publish

Build distribution artifacts:

```bash
uv build
```

Publish when credentials are configured:

```bash
uv publish
```

The repository expects the appropriate `uv` publishing credentials or environment configuration.

---

## Plugin structure

The repository also packages GodSpeed-Agent for Claude Code.

Important surfaces include:

```text
.claude-plugin/plugin.json

skills/

agents/

mcp/

monitors/

bin/
```

The Python runtime lives under:

```text
godspeed_nav/
```

External developmental evidence enters through:

```text
agentic_capability_loop/
```

Calibration logic and dataset processing live under:

```text
scripts/settlement_datasets/
```

Documentation and verification live under:

```text
docs/

tests/
```

---

## Repository guide

### `AGENTS.md`

Defines how human and machine agents work in this repository.

### `HARNESS.md`

Contains current implementation-defined defaults and historical harness terminology.

### `docs/references/`

Operator-facing references for ledgers, schemas, CLI behavior, policies, reports, and workflows.

### `docs/runbooks/`

Installation, configuration, absorption, backup, restore, incident recovery, and release-readiness procedures.

### `docs/plans/`

Implementation, calibration, and hardening plans.

### `docs/understanding/`

Theory and architectural understanding material.

---

## Verification

Run the complete test suite:

```bash
uv run pytest -q
```

Focused checks:

```bash
uv run pytest tests/test_docs_alignment.py -q

uv run pytest tests/test_cli_hooks_mcp.py -q
```

Search developmental memory:

```bash
uv run python -m godspeed_nav.cli \
  search-developmental-memory \
  --query "timeout recovery"
```

Run the validation surface:

```bash
uv run python -m godspeed_nav.cli \
  validate \
  --workspace-root . \
  --storage-root .godspeed-harness/validation
```

Example deterministic computation:

```bash
uv run python -m godspeed_nav.cli \
  compute-error \
  --desired '{"tests": 3}' \
  --observed '{"tests": 1}'
```

---

## What GodSpeed-Agent is not

### Not a foundation model

GodSpeed-Agent has an empirically trained predictive component.

That does not mean GodSpeed-Agent itself is an end-to-end trained language model or learned policy.

The controller combines deterministic, computational, and learned mechanisms.

### Not a coding agent

It does not need to write the implementation itself.

### Not a software-work harness

SWE_SEED owns routing, software-work contracts, host projections, proof obligations, hooks, and traces.

### Not the authority layer

SEA-Forge owns pre-action runtime authority for consequential operations.

Capability does not grant permission.

Prediction certainly does not grant permission.

### Not the long-horizon executor

Gauntlet coordinates difficult multi-agent and tool execution.

GodSpeed-Agent reasons over developmental state across such runs.

### Not the observation system

RealityTrace binds expected and observed outcomes with evidence and provenance.

GodSpeed-Agent consumes that evidence developmentally.

### Not a generic memory database

Its memory concerns attempts, settlement, payment, recovery, repetition, transfer, and capability formation.

### Not a leaderboard

A score is not capability.

An AUC is not capability.

A benchmark trajectory is not local capability.

### Not an outcome-dismissal system

Outcomes matter because they register consequence.

The outcome is not the end of development.

It is where the next update becomes possible.

---

## Where it fits

GodSpeed-Agent can be used locally as a CognitiveOS navigation runtime.

Within the broader GodSpeed stack:

```text
desired direction
        ↓
GodSpeed-Agent
selects affordable next move
using gates + computation + advisory priors
        ↓
Context Kernel
supplies relevant context
        ↓
SWE_SEED
defines software-work contract
        ↓
SEA-Forge
authorizes consequential action
        ↓
Gauntlet
executes long-horizon work when needed
        ↓
RealityTrace
binds expectation to observation
        ↓
GodSpeed-Agent
evaluates developmental consequence
        ↓
capability + memory + changed horizon
```

DomainForge can provide canonical semantic meaning beneath the loop.

CEP can preserve evaluation semantics across the systems participating in it.

The larger progression becomes:

```text
representation
   ↓
navigation
   ↓
context
   ↓
work contract
   ↓
authority
   ↓
execution
   ↓
observation
   ↓
development
```

GodSpeed-Agent owns the first navigation decision and the final developmental update.

It does not need to own every layer in between.

---

## When GodSpeed-Agent is probably worth trying

GodSpeed-Agent starts to earn its cost when:

* successful agent work keeps disappearing into isolated task histories
* you want future decisions to depend on actual settlement evidence
* one successful task is repeatedly being mistaken for capability
* agent supervision burden should decrease as routes become proven
* you need to distinguish visible possibilities from currently spendable paths
* payment and recovery capacity matter to which move should happen next
* active trajectory behavior could help identify recovery versus costly thrashing
* capabilities need to weaken when the environment changes
* externally acquired skills or systems should be locally proven before promotion
* you want developmental history to survive individual agent sessions
* you need a controller that can learn empirical priors without allowing those priors to become authority
* you need a controller that can question its own representations and assumptions

If the problem is simply:

> Did this coding task pass its tests?

use the software-work verification layer.

If the problem is:

> Is this long-running task still progressing?

execution telemetry and Gauntlet matter.

If the problem is:

> What should become easier next because of everything that has happened so far?

that is where GodSpeed-Agent begins.

---

## Current proof boundary

GodSpeed-Agent now has empirical evidence that its current pre-outcome trajectory representation contains useful predictive signal.

That is significant.

It is not the end of the evidence ladder.

The current calibration supports:

```text
useful discrimination
within the evaluated external proxy distribution
```

It does not yet establish:

```text
unseen-environment transfer

causal importance of individual features

optimal autonomous intervention thresholds

local project capability

cross-agent universality
```

Those are future settlement questions.

The architecture is designed so they can be tested instead of assumed.

---

## The short version

Start from the current horizon.

Do not confuse the destination with the path.

Represent the problem at a level you can actually spend.

Price the payment.

Keep governance and recovery as gates.

Choose the next affordable move.

Use empirical trajectory priors where they have earned predictive value.

Do not let prediction authorize anything.

Observe what actually happened.

Treat external experience as a prior.

Treat local consequence as standing.

Do not promote one success into capability.

Repeat under variation.

Look for transfer.

Measure whether orchestration burden falls.

Test recovery.

Keep developmental memory.

Demote what stops working.

Let earned compression become substrate.

Then ask again:

> **Given what reality just taught us, what can we afford to do next that we could not reliably do before?**

That is GodSpeed-Agent.
