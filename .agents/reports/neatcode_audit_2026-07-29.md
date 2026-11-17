# NeatCode Repository Audit

**NeatCode · audit** · repository (646 tracked files; 33,512 tracked Python lines) · depth: deep

**Summary** · The established `godspeed_nav` runtime has strong local-first storage and broad
test coverage, but its core lifecycle can metabolize an arbitrary, never-reviewed identifier.
The newer event adapter repeats settlement and capability authority with weaker rules, is absent
from built distributions, and stores learning proposals outside the canonical ledger. These are
evidence-integrity defects, not style debt: the system can record capability that did not follow
a spendable affordance path, while its primary test and validation commands still report green.

## Scope

The repository was inspected structurally, then the following consequential paths were traced:

- Navigation lifecycle: candidate review -> payment -> settlement -> capability -> repetition.
- Event lifecycle: `EvidenceRecorded` -> `SettlementRecorded` -> `CapabilityUpdated` -> local
  persistence -> optional NATS forwarding.
- Storage lifecycle: append, checksum, index, quarantine, backup, and learning-proposal writes.
- Release evidence: Hatch package selection, built wheel contents, default pytest collection,
  focused adapter tests, full tests, and enterprise validation.

All tracked files were assessed at morphology/search level. Line-level review concentrated on
`godspeed_nav/`, `agentic_capability_loop/`, their tests, packaging, hooks, and controlling docs.
The large calibration and guarded-activation scripts were assessed by file shape, recent history,
entry points, and their test surfaces, not audited line by line. Dataset payloads, generated run
artifacts, external sibling repositories, and live NATS/Postgres behavior were not audited.

## Structural Picture

- The repository is organized around a flat deterministic package, `godspeed_nav/`, with CLI,
  hooks, MCP, reports, validation, and a separate mirrored test suite (`README.md:58-64`).
- A second domain/package, `agentic_capability_loop/`, was added in commit `5d501f9` for event
  contracts, learning proposals, and NATS publication. It has its own tests beneath the package.
- Current development gravity is split between published settlement events and calibration data.
  The last 30 commits are dominated by `agentic_capability_loop/` and
  `scripts/settlement_datasets/`.
- Source size is concentrated in research/activation code: four executable scripts and three test
  modules exceed 1,000 lines. No finding is raised on size alone; these files warrant focused
  audits when their behavior next changes.
- The designed public release surface is narrower than the repository surface. Hatch includes
  only `godspeed_nav` (`pyproject.toml:27-32`), while the README now claims event consumption and
  publication owned by `agentic_capability_loop` (`README.md:10-18`).

## Architecture Conformance

**Claim** · GSA is the settlement/navigation runtime. It owns settlement classification,
capability lifecycle, developmental memory, and learning proposals, but does not own routing,
hooks, traces, or proof gating (`README.md:8-22`).

**Observed** · Settlement and capability decisions exist in both
`godspeed_nav/runtime.py:348-437` and `agentic_capability_loop/adapters.py:125-258`, with different
rules. The repository still packages trace capture (`godspeed_nav/trace_capture.py:1-9`), ships
hook implementations (`hooks/pre_tool_use.py:25-67`), and describes hooks as a current runtime
surface (`README.md:30-37`, `README.md:217-234`). `AGENTS.md:130-133` also treats hooks as part of
the repository map.

**Verdict** · **Contradictory.** The source expresses a broad local harness plus a second event
adapter, while the newest boundary statement assigns harness concerns to SWE_SEED. The conflict
is both documentary and functional: two modules now own settlement/capability transitions.

**Consequence** · Maintainers cannot tell which lifecycle is canonical or which hook/trace work
belongs here. The two lifecycle implementations have already diverged enough to admit false
capability evidence (Finding 2).

**Correction** · Make one explicit boundary decision. If F-08 is controlling, keep
settlement/capability/event translation here and move or retire hook/trace/policy-activation
ownership through a documented migration. If the broad harness is the actual product, remove the
F-08 exclusion and document the split intentionally. In either direction, route both event and
CLI/MCP settlement paths through one lifecycle authority.

**Confidence** · confirmed for this repository. The claimed SWE_SEED side of the boundary was
not inspected, so this audit does not judge whether it is ready to receive any moved surface.

## Findings

### S1 — Settlement bypass creates metabolized capability without an affordance

**Confidence** · confirmed

**Location** · `godspeed_nav/runtime.py:348-437`, `godspeed_nav/runtime.py:509-553`,
`godspeed_nav/schemas.py:98-124`, `tests/test_runtime_workflow.py:99-123`

**Evidence** · `NavigationRuntime.record_settlement()` accepts any `affordance_id`, never checks
the `affordances` ledger, and then updates capability evidence. Three direct calls for
`never-reviewed` produced `settlement_count: 3`, `lifecycle_state: metabolized`, and
`status: substrate_candidate`. The existing metabolization test deliberately exercises the same
direct path without first reviewing a horizon. Domain objects say a potential cannot execute and
a possibility cannot metabolize, but the runtime path does not use those guards.

**Cause** · The domain rule is represented in optional dataclasses, while the production runtime
mutates untyped ledger records directly. State-machine authority is descriptive rather than
enforced at the write boundary.

**Consequence** · Any CLI, MCP, hook, or Python caller can turn a visible destination or invented
identifier into settled, metabolized capability. Developmental memory can therefore certify an
imaginary muscle, violating the repository's central evidence contract.

**Correction** · In `NavigationRuntime.record_settlement()`, require a matching persisted
affordance in an executable lifecycle state before writing any settlement. Reject identifiers
found only in `potentials` or `possibilities`, and reject unknown identifiers with a typed domain
error. Keep capability counting derived from the validated settlement ledger.

**Verification** · Add tests through runtime, CLI, and MCP that attempt to settle an unknown ID,
a potential, and a possibility; each must fail and leave settlements, capabilities, trajectories,
and repetition schedules unchanged. Preserve the existing connected-cycle success test.

### S1 — The event adapter can fabricate usable settlement and metabolized capability evidence

**Confidence** · confirmed

**Location** · `agentic_capability_loop/adapters.py:125-176`,
`agentic_capability_loop/adapters.py:214-258`, `README.md:10-13`

**Evidence** · `handle_evidence_recorded()` defaults both missing `observed_result` and
`expected_result` to `""`, then tests equality before testing emptiness. An event containing only
`work_request_id` returns `outcome: usable`. `update_capability_ledger()` treats both `usable` and
`partial` as eligible for `metabolized` when the caller supplies `settlement_count >= 3`; a
single partial event plus `settlement_count=3` returns `status: metabolized`. The function's own
docstring and `README.md:12` require at least three usable settlements.

**Cause** · The adapter is a parallel lifecycle authority. It infers settlement from transport
strings and trusts a caller-provided aggregate instead of delegating to the runtime's persisted
settlement evidence and metabolization calculation.

**Consequence** · Missing evidence can become usable settlement, and partial evidence can become
metabolized capability. If published, those false events become durable downstream truth with a
valid v1 envelope and idempotency key.

**Correction** · Validate non-empty required evidence before comparison. Make absent expected or
observed results unusable (or reject the event under the external contract). Remove caller-owned
metabolization: derive usable settlement count and variation evidence from the canonical ledger,
then call the same lifecycle authority used by `NavigationRuntime`.

**Verification** · Add contract cases for absent, empty, partial, and usable evidence. A partial
event at any supplied count must not metabolize; three independently persisted usable settlements
under the required variation rule must be the first metabolizing case.

### S1 — The claimed event integration is absent from the release artifact and primary tests

**Confidence** · confirmed

**Location** · `README.md:10-18`, `pyproject.toml:27-35`,
`agentic_capability_loop/tests/test_v1_contract.py:1-11`

**Evidence** · `uv build --wheel` succeeded, but the wheel contains only `godspeed_nav/*`; it
contains no `agentic_capability_loop` module. The sdist include list also omits it.
`uv run pytest --collect-only -q` collected 540 tests under `tests/` and did not collect the 19
tests under `agentic_capability_loop/tests/`. Running those tests explicitly passes, which proves
the source-checkout path but not the installed product. Textual caller search found no production
caller for `persist_to_ledger()` and only tests calling the adapter emit/consume functions.

**Cause** · The new package landed outside both explicit Hatch package selection and pytest's
configured `testpaths`, with tests using `sys.path` insertion to make the source checkout import.

**Consequence** · Wheel/container users cannot import the functionality the README says GSA owns,
and the standard test command cannot regress it. Green CI and a successful build can therefore
ship a product missing its newly advertised integration.

**Correction** · If the event adapter is public, include `agentic_capability_loop` in wheel and
sdist package selection, move or include its tests in the primary collection, and add an
installed-wheel smoke test that imports and executes the supported entry point. If it is not a
shipped surface, remove the public claim and keep it explicitly experimental rather than
silently source-only.

**Verification** · Build and install the wheel into a clean environment, import the supported
adapter API without repository `sys.path`, then run two distinct tests: (1) an evidence
ingestion test asserting the proof is persisted as **provisional** and emits neither
`SettlementRecorded` nor any capability-state update; and (2) a separate canonical settlement
test exercising `record_settlement()` and asserting the settlement effect. Assert the primary
pytest command collects both.

### S2 — Learning proposals bypass canonical storage integrity and backup

**Confidence** · confirmed

**Location** · `agentic_capability_loop/adapters.py:343-368`,
`agentic_capability_loop/learning_proposals.py:14-59`, `godspeed_nav/storage.py:35-45`,
`godspeed_nav/storage.py:103-169`

**Evidence** · The three event ledgers use `LedgerStore.append_event()`, but learning proposals
instantiate a separate `LearningProposalLedger(ledger_store.root)` and append raw JSONL at the
storage root. That path has no canonical `ledgers/` placement, checksum, sequence, redaction,
index, file lock, fsync, quarantine, or backup inclusion. A temporary-store execution confirmed
the proposal file existed while `LedgerStore.read("agentic_learning_proposals")` returned zero
records and `export_backup()` omitted it.

**Cause** · A second storage authority was added for query convenience instead of extending the
existing ledger API.

**Consequence** · Learning proposals can be lost from backups, become invisible to standard
read/validation tools, expose fields the configured redactor would remove, and corrupt under
concurrent writers. This splits developmental memory exactly where lineage matters.

**Correction** · Persist proposals with `LedgerStore.append_event()` under
`ledgers/agentic_learning_proposals.jsonl`; implement domain-area/open queries as reads over that
canonical store. If root-level proposal files already exist in deployed workspaces, provide a
one-time, idempotent migration before removing the old reader.

**Verification** · Assert proposal writes are readable through `LedgerStore`, included in backup,
redacted, checksum-validated, and monotonic under concurrent appends. Add a migration fixture if
persisted legacy files exist.

### S2 — Enterprise validation validates presence, not the highest-risk invariants

**Confidence** · confirmed

**Location** · `godspeed_nav/validation.py:153-184`, `godspeed_nav/validation.py:284-318`,
`tests/test_validation.py:1-96`

**Evidence** · `godspeed-nav validate` returned `status: pass` after the audit reproduced an
unknown affordance becoming metabolized. Its runtime workflow checks only a valid happy path,
the hook check tests file presence, and no check covers the event package, built artifact, or
learning-proposal backup path. The full configured suite also passed (`538 passed, 2 skipped`).

**Cause** · The validator grew as a surface inventory. It proves that named components exist and
a sample cycle runs, but not that forbidden lifecycle transitions remain impossible.

**Consequence** · The command named enterprise-readiness can remain green through failures in
the repository's defining data-integrity rules. Operators receive stronger assurance than the
evidence supports.

**Correction** · Keep the inexpensive presence checks, but add a small invariant section: reject
settlement without an executable affordance, reject non-usable metabolization, verify every
advertised package is in the built artifact, and verify every truth ledger participates in
backup/integrity handling. Report these as distinct checks so failures identify the owner.

**Verification** · Mutation-test each invariant locally: remove the affordance guard, omit the
adapter package, and route a truth ledger outside `ledgers/`; each mutation must make `validate`
fail for a specific reason.

## What Is Working

- `LedgerStore.append_event()` serializes concurrent append sequence assignment under an
  exclusive file lock and adds checksum/index metadata (`godspeed_nav/storage.py:103-126`,
  `godspeed_nav/storage.py:383-404`). The concurrency-focused storage test passed in the focused
  and full suites.
- The established runtime derives capability counts from persisted successful settlements rather
  than accepting a count parameter (`godspeed_nav/runtime.py:509-534`). Once the missing
  affordance guard is added, this is the stronger lifecycle authority to preserve.
- Predictive extensions remain advisory and threshold-gated; the enterprise validator reported
  `deterministic_only` with the heuristic provider under current configuration.
- The test suite is broad and executable: 538 configured tests passed, with two service-dependent
  E2E tests skipped. The 19 adapter tests also pass when invoked explicitly. The weakness is test
  selection and missing adverse assertions, not a generally broken suite.
- The event publisher uses stable content-derived idempotency keys and an ordered local buffer;
  focused adapter tests cover watermark resume behavior and v1 envelope shape
  (`agentic_capability_loop/publisher.py:143-175`,
  `agentic_capability_loop/tests/test_publisher.py:57-125`). Live transport was not exercised.

## Highest-Leverage Corrections

1. Put one guard and one owner in front of settlement/capability transitions. This removes the
   direct runtime bypass and the adapter's weaker parallel lifecycle.
2. Make the release and evidence surfaces honest: either ship and validate the event package
   through the canonical ledger, or stop advertising it as part of the installed runtime.

## Evidence

- `git log --oneline -30` · exit 0 · established recent repository gravity.
- `git ls-files '*.py' | xargs wc -l | sort -nr` · exit 0 · measured tracked Python morphology.
- `uv run pytest --collect-only -q` · exit 0 · 540 configured tests collected; package-local
  adapter tests absent.
- `uv run pytest agentic_capability_loop/tests -q` · exit 0 · 19 passed.
- `uv run pytest tests/test_runtime_workflow.py tests/test_enterprise_storage.py tests/test_guarded_activation.py -q`
  · exit 0 · 82 passed.
- `uv run pytest -q` · exit 0 · 538 passed, 2 skipped in 53.31s.
- `uv build --wheel --out-dir /tmp/opencode/neatcode-audit-wheel` · exit 0 · wheel built.
- `unzip -l /tmp/opencode/neatcode-audit-wheel/godspeed_agent_harness-0.1.0-py3-none-any.whl`
  · exit 0 · confirmed no `agentic_capability_loop` files.
- `uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation`
  · exit 0 · validator returned `status: pass`.
- Four targeted Python executions · exit 0 · reproduced unknown-affordance metabolization,
  empty-evidence `usable`, partial-evidence `metabolized`, and proposal backup omission.
- `just context-check` · not run · this checkout has no `context-check` recipe.

## Limits

- Caller discovery was textual. Dynamic imports, external repositories, and deployed consumers
  may call the event adapter even though no in-repository production caller was found.
- No live NATS/Postgres transport, concurrent learning-proposal write, dependency vulnerability
  scan, or performance/load test ran.
- The two E2E tests were skipped because their external services were unavailable; their source
  was inspected, not executed.
- This was an audit, not a fix. No production source, tests, configuration, or persisted runtime
  data was intentionally changed.

## Audit Critique

`correctness 4 · repository fit 5 · semantic integrity 4 · restraint 5 · operational credibility 3 · evidence 5`

Operational credibility is 3 because local failure modes were executed but live transport,
cross-process concurrency, external ownership, and load behavior remain unverified.

**Count** · `3 S1 · 2 S2 · 0 S3 · 0 S4 · 0 S5`
