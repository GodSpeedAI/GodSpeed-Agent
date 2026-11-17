# Implementation Plan — Restore Canonical Settlement Authority

**Created:** 2026-07-29
**Source of truth:** `.agents/reports/neatcode_audit_2026-07-29.md`
**Originating context:** Deep NeatCode repository audit on the current working tree, resolved
against the controlling responsibility boundaries in
`docs/explanations/SEA_Forge_to_godspeed_agent.md` and
`docs/explanations/SWE_SEED_to_godspeed_agent.md`.
**Status of the work today:** `godspeed_nav` contains the stronger persisted lifecycle, but it
accepts settlement for unknown paths. `agentic_capability_loop` repeats weaker lifecycle rules,
writes one developmental ledger outside `LedgerStore`, and is omitted from builds and default
test collection. Historical GodSpeed-Agent hook and trace producers overlap tested SWE_SEED
owners.

---

## 0. How to use this plan (agent operating instructions)

- Execute tasks in order unless the dependency graph marks them independent. Tasks 1-3 establish
  canonical authority; Task 4 ships it; Task 5 makes validation enforce it. Tasks 6-8 complete
  the cross-repository boundary migration. Task 9 aligns user-facing contracts. Task 10 is the
  final proof and handoff.
- **Every task ends with a verification gate.** Do not mark a task done until its gate command
  exits 0.
- **Adapter translates. Domain authority decides. Ledger persists.** This controlling rule comes
  from `docs/explanations/SWE_SEED_to_godspeed_agent.md:225-250`; never restore lifecycle logic or
  developmental truth storage inside an adapter.
- Match runtime and storage idioms in `godspeed_nav/runtime.py`, `godspeed_nav/storage.py`, and
  `tests/test_runtime_workflow.py`. Match event-envelope translation in
  `agentic_capability_loop/adapters.py:55-122`.
- The explanation documents are the responsibility source of truth. Update public docs only after
  tests prove the corresponding behavior.
- Use test-driven development for every behavior change. Confirm each new adverse-path test fails
  against the pre-task implementation before making it pass.
- Commit each task separately after its focused and global gates pass. Do not include unrelated
  dirty-worktree files.
- Before Task 8 deletes historical hook or trace producers, obtain explicit user confirmation for
  the exact deletion list. Approval of this plan is not deletion approval.

### Dependency graph

```text
Task 1 enforce executable-affordance settlement
  └─ Task 2 move external evidence decisions into NavigationRuntime
       └─ Task 4 ship adapter and collect its tests
            └─ Task 5 validate lifecycle, storage, and distribution invariants

Task 3 canonicalize learning-proposal storage
  ├─ Task 4 ship adapter and collect its tests
  └─ Task 5 validate lifecycle, storage, and distribution invariants

SWE_SEED hook/trace proof
  └─ Task 6 add read-only SWE_SEED execution-evidence ingestion
       └─ Task 7 isolate synthetic trace generation outside runtime
            └─ Task 8 retire GodSpeed-Agent hook and trace producers

Tasks 1-8
  └─ Task 9 align package identity and operator documentation
       └─ Task 10 final conformance, review, and handoff
```

### Global verification gates (must stay green after every task)

```bash
uv run pytest tests/test_runtime_workflow.py tests/test_enterprise_storage.py tests/test_validation.py -q
uv run pytest agentic_capability_loop/tests -q
uv run pytest -q
git diff --check
```

Rebuild steps after changing package selection, package identity, or distributed files:

```bash
DIST_DIR="$(mktemp -d /tmp/opencode/godspeed-audit-fix.XXXXXX)"
uv build --wheel --sdist --out-dir "$DIST_DIR"
```

---

## Key facts already discovered (do not re-derive)

| Thing | Location |
|---|---|
| Controlling three-system authority split | `docs/explanations/SEA_Forge_to_godspeed_agent.md:3-19` |
| Unknown, potential, and possibility paths cannot settle | `docs/explanations/SWE_SEED_to_godspeed_agent.md:96-109` |
| Evidence completeness and non-empty values are required | `docs/explanations/SWE_SEED_to_godspeed_agent.md:150-164` |
| Capability must derive from persisted canonical settlements | `docs/explanations/SWE_SEED_to_godspeed_agent.md:181-207` |
| Adapter is translation only | `docs/explanations/SWE_SEED_to_godspeed_agent.md:225-250` |
| All developmental truth uses one storage authority | `docs/explanations/SWE_SEED_to_godspeed_agent.md:252-277` |
| Canonical invariant list matching all audit findings | `docs/explanations/SWE_SEED_to_godspeed_agent.md:279-292` |
| Runtime currently settles any identifier | `godspeed_nav/runtime.py:348-437` |
| Runtime capability calculation derives from persisted successes | `godspeed_nav/runtime.py:509-553` |
| Domain objects already name potential/possibility rejection | `godspeed_nav/schemas.py:98-124` |
| Adapter currently classifies evidence and accepts caller counts | `agentic_capability_loop/adapters.py:125-258` |
| Adapter currently creates parallel developmental ledgers | `agentic_capability_loop/adapters.py:343-384` |
| Learning proposals currently bypass canonical storage | `agentic_capability_loop/learning_proposals.py:14-59` |
| Canonical storage integrity and backup owner | `godspeed_nav/storage.py:35-169` |
| Package and test selection omit the adapter | `pyproject.toml:27-35` |
| Enterprise validation currently proves only a valid sample flow | `godspeed_nav/validation.py:150-219` |
| SWE_SEED explicitly owns hooks and traces | `/home/sprime01/projects/SWE_SEED/README.md:7-18` |
| SWE_SEED has required hook contracts and tests | `/home/sprime01/projects/SWE_SEED/docs/specs/0005-normalized-hook-runtime.md:44-112` |
| SWE_SEED has a tested trace lifecycle | `/home/sprime01/projects/SWE_SEED/crates/swe-seed-core/tests/trace_lifecycle.rs:68-169` |
| GodSpeed-Agent runtime trace producer and consumers | `godspeed_nav/trace_capture.py:1-653` |
| GodSpeed-Agent host hook registration | `hooks/hooks.json:1-9` |

---

## Task 1 — Reject settlement without an executable affordance (core lifecycle · S1)

**Goal:** `NavigationRuntime.record_settlement()` rejects unknown, potential, and possibility
identifiers before writing any settlement-derived state, while connected affordance settlement
continues to work.

**Why this shape:** The runtime write boundary owns the invariant. CLI, MCP, adapters, and future
callers must receive the same decision without duplicating checks at each entry point.

### Interfaces

- Add `NavigationRuntime._require_executable_affordance(affordance_id: str) -> dict[str, Any]`.
- Raise `DomainRuleError` with code `settlement_requires_executable_affordance` for unknown,
  potential-only, possibility-only, or non-executable affordance records.
- Treat only persisted `affordances` records with `current_status == "affordance"` as executable.
  Add an attempted state later only with its own tested transition; no producer exists today.

### Steps

1. Add failing runtime tests for unknown, potential-only, and possibility-only IDs. Snapshot all
   settlement-derived ledgers before the call and assert no settlement, trajectory, capability,
   or repetition record appears — file: `tests/test_runtime_workflow.py:6-123`.
2. Add failing CLI and MCP tests that assert the typed error code reaches both public surfaces —
   file: `tests/test_cli_hooks_mcp.py:220-295,799-818`.
3. Run the focused tests and confirm they fail because the runtime currently accepts the IDs.
4. Implement `_require_executable_affordance()` and call it as the first operation in
   `record_settlement()` — files: `godspeed_nav/runtime.py:348-437,489-553`,
   `godspeed_nav/schemas.py:12-17,98-124`.
5. Catch `DomainRuleError` at the CLI process boundary, write a JSON error object containing
   `code` and `message` to stderr, and exit 2. Preserve the typed exception
   from `call_tool()` for in-process MCP callers and serialize the same error shape/exit code in
   MCP `main()` — files: `godspeed_nav/cli.py:294-302`,
   `mcp/cybernetic_nav_server/server.py:70-191,194-209`.
6. Update existing tests that call `record_settlement()` directly to seed an executable
   affordance first; do not weaken the new guard or add a test-only bypass — files:
   `tests/test_runtime_workflow.py:6-425`, `tests/test_reports.py:1-204`.

### Gate

```bash
uv run pytest tests/test_runtime_workflow.py tests/test_reports.py tests/test_cli_hooks_mcp.py -q
```

**Done when:** All three forbidden identifier classes raise
`settlement_requires_executable_affordance`, all affected ledgers remain unchanged, and the
connected runtime/CLI/MCP flow still records settlement. Temporarily removing the guard must make
at least one adverse-path test fail.

**Redesign trigger:** If a persisted external work attempt legitimately reaches settlement without
an `affordances` record, stop and model its explicit affordance import/attempt transition. Do not
add an `allow_unknown` flag.

---

## Task 2 — Make external evidence ingestion provisional and capability-neutral (event boundary · S1)

**Goal:** `EvidenceRecorded` translation cannot declare usable settlement or promote capability
inside `agentic_capability_loop`; `NavigationRuntime` validates and persists execution evidence as
provisional input for a later consequence-based settlement.

**Why this shape:** The explanation documents explicitly identify adapter-local settlement,
caller-provided promotion counts, and parallel capability ledgers as GodSpeed-Agent failures. They
also state that passing software proof is not equivalent to reliable settlement. Moving the exact
string comparison into the runtime would relocate the defect rather than remove it.

### Interfaces

- Add `NavigationRuntime.ingest_execution_evidence(event: dict[str, Any]) -> dict[str, Any]`.
- Require non-empty `event_id`, `payload.affordance_id`, `payload.work_request_id`,
  `payload.proof_result_id`, `payload.expected_result`, and `payload.observed_result`.
- Reuse `_require_executable_affordance()` from Task 1.
- Persist a deterministic record in canonical `execution_evidence`, keyed by evidence event ID.
  Re-delivery must return the existing record and produce no duplicate writes.
- Runtime-owned ingestion results: complete non-empty evidence is `provisional` regardless of
  whether expected and observed strings match; missing required evidence is rejected with
  `incomplete_execution_evidence`. Preserve match/mismatch as an observed proof fact, not a
  settlement decision.
- `ingest_execution_evidence()` must not write `settlements`, `capabilities`, `trajectories`, or
  `repetition_schedules`. A later `record_settlement()` call with observable before/after
  consequence remains the only promotion path.
- Replace adapter-local `update_capability_ledger(..., settlement_count=...)` with pure
  `emit_capability_updated(capability_record, settlement_event) -> dict[str, Any]`.
- Change `handle_evidence_recorded(event, runtime)` to call `runtime.ingest_execution_evidence()`
  and translate its returned result into `ExecutionEvidenceIngested` when provisional. Rejection
  raises a typed error and emits nothing. Reserve `SettlementRecorded` for translation of a
  canonical `NavigationRuntime.record_settlement()` result; execution evidence alone emits neither
  `SettlementRecorded` nor `CapabilityUpdated`.
- Replace `persist_to_ledger()` parallel truth writes with an outbound-event outbox writer. The
  outbox stores transport envelopes only; `settlements`, `capabilities`, and
  `repetition_schedules` remain canonical.

### Steps

1. Extend the v1 fixture helper with `affordance_id` and add failing tests for missing/empty
   expected and observed values, matching values, differing values, duplicate event delivery, and
   unknown affordance — file: `agentic_capability_loop/tests/test_v1_contract.py:39-164`.
2. Add failing runtime tests proving repeated matching and differing execution evidence remains
   provisional and leaves settlement/capability/trajectory/repetition ledgers empty — file:
   `tests/test_runtime_workflow.py:99-123`.
3. Add `ingest_execution_evidence()` using Task 1 eligibility and canonical
   `execution_evidence` storage, with no capability derivation — file:
   `godspeed_nav/runtime.py:348-437`.
4. Reduce the adapter to input validation, runtime invocation, correlation/idempotency mapping,
   and outbound envelope construction. Delete caller-owned count handling only after explicit
   confirmation at execution time — file: `agentic_capability_loop/adapters.py:125-258,343-384`.
5. Update publisher tests to drain one outbound event ledger rather than three parallel domain
   ledgers — files: `agentic_capability_loop/publisher.py:143-206`,
   `agentic_capability_loop/tests/test_publisher.py:38-125`.
6. Document provisional execution-evidence ingestion, match/mismatch fact preservation,
   consequence-based settlement, and idempotency after tests pass — files: `HARNESS.md:1-50`,
   `README.md:8-28,236-240`.

### Gate

```bash
uv run pytest tests/test_runtime_workflow.py agentic_capability_loop/tests/test_v1_contract.py agentic_capability_loop/tests/test_publisher.py -q
```

**Done when:** Missing evidence is rejected; matching and differing software proof remain
provisional; execution evidence alone writes no settlement-derived state or settlement-shaped
event; caller counts no longer exist; duplicates are idempotent; and every emitted event translates
a canonical runtime result. Reintroducing `settlement_count=3`, classifying a string match as
usable, or emitting `SettlementRecorded` during ingestion must make the gate fail.

**Redesign trigger:** If the upstream `EvidenceRecorded` contract cannot add `affordance_id`, do
not infer one from work-request text. Define and approve a separate persisted
work-request-to-affordance correlation record before continuing.

---

## Task 3 — Move learning proposals into LedgerStore (storage · S2)

**Goal:** Learning proposals receive canonical locking, sequencing, checksum, redaction, index,
quarantine, backup, and migration behavior, with no root-level JSONL truth file.

**Why this shape:** Query convenience does not earn a second storage authority or a stateful
ledger wrapper. Keep domain validation/query helpers in the existing module, but pass the one
canonical `LedgerStore` into them.

### Interfaces

- Replace `LearningProposalLedger` with
  `append_learning_proposal(store: LedgerStore, event: dict[str, Any]) -> dict[str, Any]` and
  `query_learning_proposals(store: LedgerStore, *, domain_area: str | None = None, status: str | None = None) -> list[dict[str, Any]]`.
- Use ledger name `agentic_learning_proposals`; helpers may validate/filter records but may not
  open files.
- Add `migrate_legacy_learning_proposals(store: LedgerStore) -> dict[str, int]` for the persisted
  legacy path.
- Add idempotent legacy migration from `storage_root/agentic_learning_proposals.jsonl` into canonical
  enveloped records, deduplicated by event ID. Archive the old file under
  `storage_root/cache/migrations/` only after all records verify.

### Steps

1. Replace existing root-file assertions with failing tests for canonical path, checksum envelope,
   secret redaction, index lookup, backup inclusion, and concurrent append ordering — files:
   `agentic_capability_loop/tests/test_learning_proposals.py:16-97`,
   `tests/test_enterprise_storage.py:19-120`.
2. Add a legacy raw-JSONL fixture with duplicate IDs and a malformed line. Assert valid unique
   records migrate once, malformed input blocks archival, and a second migration is a no-op —
   file: `agentic_capability_loop/tests/test_learning_proposals.py:34-97`.
3. Replace the stateful wrapper with the store-accepting functions; remove the class only after
   explicit confirmation at execution time — file:
   `agentic_capability_loop/learning_proposals.py:14-77`.
4. Change adapter persistence to write learning proposals through the canonical helper —
   file: `agentic_capability_loop/adapters.py:343-368`.
5. Add learning proposals to developmental-memory backup documentation after the gate passes —
   files: `docs/references/ledger-reference.md:7-81`,
   `docs/runbooks/backup-restore.md:7-20`.

### Gate

```bash
uv run pytest agentic_capability_loop/tests/test_learning_proposals.py tests/test_enterprise_storage.py -q
```

**Done when:** No new root-level proposal file is created, proposal reads and backup use
`LedgerStore`, concurrent sequences are monotonic, and legacy migration is idempotent and
fail-safe. Replacing `append_event()` with direct file append must fail checksum/backup tests.

**Redesign trigger:** If deployed roots contain a different legacy shape than the current event
envelope, stop migration and capture an anonymized fixture before defining a converter.

---

## Task 4 — Ship the adapter and run its tests by default (distribution · S1)

**Goal:** Wheel, sdist, container source, and the default pytest command include the public
`agentic_capability_loop` integration and its contract tests.

**Why this shape:** The controlling explanations and README make the evidence adapter a public
boundary. A source-checkout-only package is not a shipped capability.

### Steps

1. Add a distribution contract test that builds wheel and sdist into `tmp_path`, inspects both
   with `zipfile`/`tarfile`, and asserts `godspeed_nav` and `agentic_capability_loop` are present — create:
   `tests/test_distribution.py`.
2. Add clean-environment smoke commands to the focused gate that install each built artifact and
   import the adapter without repository `sys.path`.
3. Add `agentic_capability_loop` to Hatch wheel and sdist package selection, and add
   `agentic_capability_loop/tests` to pytest `testpaths` — file: `pyproject.toml:27-35`.
4. Copy `agentic_capability_loop/` into the container build context before project installation —
   file: `Dockerfile:21-41`.
5. Add a deterministic Dockerfile assertion to `tests/test_distribution.py` that the adapter copy
   precedes project installation. If Docker is available in release CI, also build the image in
   Task 10.
6. Remove package-test `sys.path.insert()` workarounds and prove imports still succeed through
   normal project configuration — files: `agentic_capability_loop/tests/test_v1_contract.py:13-30`,
   `agentic_capability_loop/tests/test_publisher.py:7-18`,
   `agentic_capability_loop/tests/test_learning_proposals.py:2-13`.

### Gate

```bash
uv run pytest tests/test_distribution.py agentic_capability_loop/tests -q
DIST_DIR="$(mktemp -d /tmp/opencode/godspeed-audit-fix.XXXXXX)"
uv build --wheel --sdist --out-dir "$DIST_DIR"
uv run --isolated --with "$DIST_DIR"/*.whl python -c "import agentic_capability_loop, godspeed_nav"
uv run --isolated --with "$DIST_DIR"/*.tar.gz python -c "import agentic_capability_loop, godspeed_nav"
uv run pytest --collect-only -q | rg 'agentic_capability_loop/tests/test_v1_contract.py'
```

**Done when:** The wheel and sdist contain the adapter, the container copies it, default collection
lists its tests, and clean wheel/sdist imports succeed. Removing either Hatch package entry or the
Dockerfile copy must make `tests/test_distribution.py` fail.

**Redesign trigger:** If the adapter is intentionally internal rather than public, stop and amend
the explanation/README contract before excluding it. Do not leave public claims and source-only
delivery inconsistent.

---

## Task 5 — Make enterprise validation enforce defining invariants (validation · S2)

**Goal:** `validate` fails when settlement eligibility, adapter authority, developmental storage,
distribution, or default-test-selection invariants regress.

**Why this shape:** Keep validation deterministic and local. It should exercise forbidden states
in a temporary store and inspect controlling package configuration, not run the full suite or
build artifacts during every operator validation.

### Interfaces

- Add checks named `settlement_invariants`, `developmental_truth_storage`,
  `adapter_authority`, and `distribution_configuration`.
- Each check returns specific boolean details, not one aggregate flag.
- Continue using the temporary validation workspace; never write sample settlement into the
  operator's target storage.

### Steps

1. Add failing validation tests asserting all four named checks exist and pass in the corrected
   tree — file: `tests/test_validation.py:11-60`.
2. Add behavioral tests showing each check fails against a controlled mutation/fixture: unknown
   settlement accepted, execution evidence producing settlement-derived writes, proposal storage
   omitted from canonical lookup/backup, and omitted Hatch/testpaths entry — file:
   `tests/test_validation.py:11-96`.
3. Implement settlement adverse-path probes in the scratch runtime and assert zero derived writes
   after rejection — file: `godspeed_nav/validation.py:150-219`.
4. Execute a complete and incomplete `EvidenceRecorded` flow against the scratch runtime. Assert
   provisional/rejected results and zero settlement/capability/trajectory/repetition writes — file:
   `godspeed_nav/validation.py:150-219`.
5. Persist a learning proposal through the canonical helper, verify indexed lookup and backup
   inclusion, and report those observed properties in `developmental_truth_storage` — file:
   `godspeed_nav/validation.py:79-95,150-219`.
6. Parse `pyproject.toml` with `tomllib` to report `distribution_configuration`; explicitly state
   this is configuration evidence, while Task 4/10 owns built-artifact proof — file:
   `godspeed_nav/validation.py:24-32,314-319`.
7. Update CLI reference wording from surface inventory to invariant-aware validation after tests
   pass — file: `docs/references/cli-reference.md:119-129`.

### Gate

```bash
uv run pytest tests/test_validation.py -q
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation-plan
```

**Done when:** The command reports all four checks and fails under each controlled behavioral
regression while leaving target ledgers empty. Removing the runtime settlement guard, allowing
execution evidence to write capability, or bypassing canonical proposal storage must fail a named
check. `distribution_configuration` must not claim that an artifact was built.

**Redesign trigger:** If validation starts importing tests or running build tools, stop and move
that proof to `tests/test_distribution.py`; operator validation must remain bounded and local.

---

## Task 6 — Consume SWE_SEED traces through a read-only evidence adapter (boundary migration · S2)

**Goal:** GodSpeed-Agent can ingest SWE_SEED trace/evidence exports for settlement analysis without
owning trace capture or mutation.

**Why this shape:** SWE_SEED already owns and tests trace lifecycle. GodSpeed-Agent needs a
read-only translator from that evidence into its settlement-dataset shape, not another recorder.

### Interfaces

- Create `scripts/settlement_datasets/swe_seed_trace_reader.py` with read-only
  `read_swe_seed_trace_record(trace_root: Path, trace_path: Path) -> dict[str, Any]` and
  `read_swe_seed_hook_events(hook_log_dir: Path, trace_id: str) -> list[dict[str, Any]]`, plus
  `to_trace_analysis_record(record: dict[str, Any], hook_events: list[dict[str, Any]]) -> dict[str, Any]`.
- Read SWE_SEED's actual trace-record shape: `trace_id`, `created_at`, `task`,
  `route_decision_record`, `route`, `events`, `verification`, `unresolved_risks`, and
  `completion_claim` (`/home/sprime01/projects/SWE_SEED/crates/swe-seed-core/src/trace/record.rs:17-31`).
- Validate required identifiers, preserve route/verification/risk provenance, and reject paths
  outside `trace_root/.agent-harness/traces/records/`.
- Read only SWE_SEED `events-*.jsonl` hook logs and filter by exact `trace_id`; preserve
  `event`, `status`, `timestamp`, and redacted `attributes`
  (`/home/sprime01/projects/SWE_SEED/crates/swe-seed-core/src/hooks/runtime.rs:64-94`).
- Do not read `HARNESS_TRACE_CAPTURE_*`, create directories, append events, or finalize runs.
- The analysis record is external/provisional evidence only. It must not fabricate
  `affordance_id`, `work_request_id`, `proof_result_id`, expected/observed result, or call Task 2
  ingestion. A separate verified work-contract correlation is required before runtime ingestion.

### Steps

1. Run SWE_SEED ownership proof before changing consumers — external workspace:
   `/home/sprime01/projects/SWE_SEED`.
2. Add failing reader tests using a minimal SWE_SEED trace-record fixture plus hook-event JSONL.
   Cover malformed input, missing IDs, cross-trace hook events, traversal, and symlinks — create:
   `tests/test_swe_seed_trace_ingestion.py`.
3. Implement the read-only adapter — create:
   `scripts/settlement_datasets/swe_seed_trace_reader.py`.
4. Add one explicit SWE_SEED trace-analysis entry path to the conversion CLI without changing the
   existing historical run-directory path yet — file:
   `scripts/settlement_datasets/convert_live_trace_to_settlement_record.py:1-295`.
5. Keep the existing historical run-directory consumers unchanged until Task 7 extracts their
   fixture parser; do not make the SWE_SEED reader accept that format.
6. Keep canonical settlement classification in GodSpeed-Agent after trace analysis; do not
   map SWE_SEED `verification` or `completion_claim` directly to usable or metabolized state.

### Gate

```bash
cargo test --manifest-path /home/sprime01/projects/SWE_SEED/Cargo.toml -p swe-seed-core --test trace_lifecycle --test trace_ledger
uv run pytest tests/test_swe_seed_trace_ingestion.py tests/test_live_shadow_policy_eval.py tests/test_guarded_activation.py -q
```

**Done when:** The conversion surface can consume an actual SWE_SEED trace record plus correlated
hook events as provisional analysis without work-contract identifiers, cannot submit that analysis
to `ingest_execution_evidence()` until a separate verified correlation supplies the required IDs,
and no reader can write or finalize traces. Adding a write, inferred identifier, or direct runtime
submission must fail a test.

**Redesign trigger:** If SWE_SEED changes `TraceRecord`, version the reader explicitly and pin the
accepted fields with a copied fixture. Do not make one permissive parser silently accept both the
SWE_SEED record and GodSpeed-Agent's historical run-directory shape.

---

## Task 7 — Isolate synthetic trace generation as dataset fixtures (research boundary · S2)

**Goal:** Synthetic baseline generation remains available for calibration tests but cannot be
mistaken for live harness trace capture or imported from the runtime package.

**Why this shape:** Synthetic dataset generation is legitimate research support. Naming and
placing it as a runtime `HarnessTraceCapture` creates the ownership conflict and encourages live
use.

### Interfaces

- Create `scripts/settlement_datasets/synthetic_trace_fixture.py` with
  `SyntheticTraceFixture` plus the historical run-directory readers and analytical helpers
  currently used by calibration (`infer_settlement_signals`, duplicate-error, same-path,
  strategy-revision, and low-cost-inspection detection). Generated records must declare
  `trace_source: synthetic_fixture`.
- The fixture must require an explicit output directory. It must not activate from environment
  variables or default into a live-trace directory.

### Steps

1. Add failing tests that environment variables cannot activate synthetic capture and that every
   generated run is labeled synthetic — create: `tests/test_synthetic_trace_fixtures.py`.
2. Move only fixture-building behavior needed by baseline generation into
   `SyntheticTraceFixture` — create:
   `scripts/settlement_datasets/synthetic_trace_fixture.py`.
3. Inventory every symbol imported from `godspeed_nav.trace_capture`; move each retained
   run-directory reader or analytical helper and its regression cases into the synthetic/dataset
   owner before deleting the runtime module — files: `godspeed_nav/trace_capture.py:21-653`,
   `tests/test_live_harness_trace_capture.py:25-707`.
4. Update baseline generation, historical conversion, policy evaluation, and guarded replay to use
   the explicit synthetic/dataset module — files:
   `scripts/settlement_datasets/collect_baseline_traces.py:1-1417`,
   `scripts/settlement_datasets/convert_live_trace_to_settlement_record.py:1-295`,
   `scripts/settlement_datasets/evaluate_live_trace_policies.py:1-325`,
   `scripts/settlement_datasets/run_guarded_activation_experiment.py:1-430`.
5. Rename output metadata away from `live_capture` without rewriting existing generated artifacts.
6. Keep synthetic generation and analytical assertions separate from read-only SWE_SEED ingestion — file:
   `tests/test_synthetic_trace_fixtures.py`.
7. Preserve existing generated datasets as historical artifacts; do not rewrite them to simulate
   new settlement evidence.

### Gate

```bash
uv run pytest tests/test_synthetic_trace_fixtures.py tests/test_settlement_datasets.py -q
```

**Done when:** Synthetic traces can still be generated explicitly, are always labeled synthetic,
all existing analytical regression cases survive under the dataset owner, and no environment flag
turns GodSpeed-Agent into a live trace collector. Restoring `HARNESS_TRACE_CAPTURE_ENABLED` or
dropping any migrated analytical case must make the gate fail.

**Redesign trigger:** If a calibration experiment requires direct live host capture, implement it
in SWE_SEED and consume its export through Task 6. Do not restore a GodSpeed-Agent recorder.

---

## Task 8 — Retire duplicate host hooks and runtime trace producer (boundary cleanup · S2)

**Goal:** GodSpeed-Agent no longer registers repository/tool hooks or ships a live trace producer;
SWE_SEED remains the proven owner, while GodSpeed-Agent keeps settlement, learning proposals,
MCP, and read-only evidence ingestion.

**Why this shape:** This is the physical completion of F-08. Keeping inactive duplicate files
would preserve ambiguous authority and invite future drift.

### Steps

1. Obtain explicit user confirmation to delete: `hooks/hooks.json`, `hooks/common.py`,
   `hooks/user_prompt_submit.py`, `hooks/pre_tool_use.py`, `hooks/post_tool_use.py`,
   `hooks/stop.py`, `godspeed_nav/trace_capture.py`, and
   `tests/test_live_harness_trace_capture.py`.
2. Prove the destination owners before deletion — external tests in SWE_SEED for hook runtime and
   trace lifecycle.
3. Add failing structure tests asserting the GodSpeed plugin has no host hook registration and
   `godspeed_nav.trace_capture` is absent — files: `tests/test_plugin_structure.py:1-66`,
   `tests/test_docs_alignment.py:1-270`.
4. Remove hook paths and the `hooks` presence check from enterprise validation — files:
   `godspeed_nav/validation.py:13-21,284-285`, `tests/test_validation.py:11-60`.
5. Remove hook execution tests from `tests/test_cli_hooks_mcp.py`; retain CLI and MCP settlement
   tests because those remain GodSpeed-Agent surfaces — file:
   `tests/test_cli_hooks_mcp.py:563-796`. The retained trace-reader, analytical, and synthetic
   fixture contracts must already live in the Task 6-7 test files with no reduction in case count.
6. Delete the confirmed files only after Tasks 6-7 remove all legitimate imports.
7. Update active ownership surfaces or add explicit supersession notices: `AGENTS.md:130-133`,
   `docs/live-harness-trace-capture.md:1-221`, `docs/live-harness-trace-capture-report.md:1-113`,
   `docs/live-trace-baseline-report.md:1-226`,
   `docs/guarded-activation-experiment-report.md:155-179`, and
   `docs/reflection-targeted-evidence-run-report.md:100`.
8. Search all active source/docs for remaining imports, registrations, or current ownership claims.
   Historical files under `docs/plans/` and `.agents/reports/` may retain provenance only when
   clearly historical.

### Gate

```bash
cargo test --manifest-path /home/sprime01/projects/SWE_SEED/Cargo.toml -p swe-seed-core --test hooks_runtime --test trace_lifecycle --test trace_ledger
uv run pytest tests/test_plugin_structure.py tests/test_docs_alignment.py tests/test_cli_hooks_mcp.py tests/test_validation.py -q
! test -e hooks/hooks.json
! test -e godspeed_nav/trace_capture.py
! rg -n 'from godspeed_nav\.trace_capture|python hooks/|GodSpeed-Agent.*owns.*hooks' AGENTS.md README.md HARNESS.md godspeed_nav scripts tests .claude-plugin docs --glob '!docs/plans/**' --glob '!docs/*report.md'
rg -q 'Superseded.*F-08' docs/live-harness-trace-capture-report.md
rg -q 'Superseded.*F-08' docs/live-trace-baseline-report.md
rg -q 'Superseded.*F-08' docs/guarded-activation-experiment-report.md
rg -q 'Superseded.*F-08' docs/reflection-targeted-evidence-run-report.md
```

**Done when:** SWE_SEED hook/trace tests pass, GodSpeed-Agent has no hook registration or live
trace producer, every trace analytical regression case has a new owner, and active code/docs
contain no old import, command, or ownership claim. Restoring `hooks/hooks.json`, the runtime
capture module, or deleting a migrated analytical test must fail a named test.

**Redesign trigger:** If a current GodSpeed-Agent consumer cannot use SWE_SEED hooks/traces, stop
before deletion and document that consumer as a migration blocker. Do not keep duplicate ownership
without a named compatibility window and removal criterion.

---

## Task 9 — Align package identity and operator documentation (public contract · S2)

**Goal:** Active metadata and docs consistently describe GodSpeed-Agent as the settlement/navigation
runtime, document executable-affordance and evidence rules, and point hook/trace users to SWE_SEED.

**Why this shape:** Code and packaging changes are incomplete while active documentation still
teaches the superseded harness boundary.

### Steps

1. Update package/plugin descriptions to settlement/navigation runtime language. If the
   distribution or plugin name changes from `godspeed-agent-harness`, first confirm it has not
   been published or consumed; otherwise create a separate compatibility migration — files:
   `pyproject.toml:1-5`, `.claude-plugin/plugin.json:1-8`.
2. Update current ownership, installation, package map, and workflow language — file:
   `README.md:1-37,58-112,217-240`.
3. Remove hook-ledger ownership and add canonical learning proposals/outbound outbox descriptions —
   files: `docs/references/ledger-reference.md:46-81`,
   `docs/references/schema-index.md:1-50`.
4. State that `record-settlement` requires a persisted executable affordance and document its
   typed rejection — files: `docs/references/cli-reference.md:65-79`,
   `docs/references/runtime-workflow-example.md:20-53`.
5. Update `HARNESS.md` implementation-defined behavior for external evidence completeness,
   idempotency, provisional classification, and canonical proposal storage — file:
   `HARNESS.md:1-50`.
6. Keep historical plans/reports unchanged; add a short supersession note only where an active
   reader could mistake historical hook/trace guidance for current operation.
7. Extend docs-alignment assertions to pin the boundary and new invariants — file:
   `tests/test_docs_alignment.py:1-270`.

### Gate

```bash
uv run pytest tests/test_docs_alignment.py tests/test_plugin_structure.py -q
! rg -n 'Godspeed Agent Harness|GodSpeed-Agent.*owns.*hooks|godspeed_nav/trace_capture.py' AGENTS.md README.md HARNESS.md .claude-plugin pyproject.toml docs --glob '!docs/plans/**' --glob '!docs/*report.md'
rg -q 'Superseded.*F-08' docs/live-harness-trace-capture-report.md
rg -q 'Superseded.*F-08' docs/live-trace-baseline-report.md
rg -q 'Superseded.*F-08' docs/guarded-activation-experiment-report.md
rg -q 'Superseded.*F-08' docs/reflection-targeted-evidence-run-report.md
```

**Done when:** Active docs name one owner for hooks/traces and one owner for settlement/capability,
operator examples cannot settle an unreviewed path, and metadata no longer contradicts F-08.
Reintroducing a current hook-ownership claim must fail docs alignment.

**Redesign trigger:** If package/plugin identifiers are externally published, preserve identifiers
temporarily but change descriptions now; write a separate deprecation plan with named consumers
and a removal date.

---

## Task 10 — Final conformance, review, and handoff (whole change · release gate)

**Goal:** All audit findings are closed by executable evidence, the cross-repository boundary is
consistent, and the resulting change is ready for human review without unverified claims.

**Why this shape:** Individual green tasks do not prove distribution, full-suite, architecture,
and documentation conformance together.

### Steps

1. Run the complete GodSpeed-Agent suite and explicit adapter suite after default collection is
   fixed — repository root.
2. Build wheel and sdist, inspect both for `godspeed_nav` and `agentic_capability_loop`, and run a
   clean installed-artifact smoke test.
3. Run enterprise validation in a temporary storage root and confirm all four invariant checks.
4. Run SWE_SEED hook and trace ownership tests; record exact command output in handoff status.
5. Run the service-backed settlement roundtrip and require two passes, not skips.
6. Run `code-review-and-quality` over the full change. Record the review result as a handoff
   prerequisite and resolve all S1-S2 findings before handoff.
7. Update `.agents/CURRENT_STATUS.md` with changed files, exact verification results, remaining
   risks, and any deletion/migration decision. Update `CURRENT_STATE.md` only if the implementation
   reaches a meaningful project milestone.
8. Attempt `just context-check`; if the recipe remains unavailable, record that exact limitation
   rather than reporting a pass.

### Gate

```bash
uv run pytest -q
uv run pytest tests/test_distribution.py -q
DIST_DIR="$(mktemp -d /tmp/opencode/godspeed-audit-fix.XXXXXX)"
uv build --wheel --sdist --out-dir "$DIST_DIR"
uv run --isolated --with "$DIST_DIR"/*.whl python -c "import agentic_capability_loop, godspeed_nav"
uv run --isolated --with "$DIST_DIR"/*.tar.gz python -c "import agentic_capability_loop, godspeed_nav"
docker build -t godspeed-agent-audit-fix .
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation-final
cargo test --manifest-path /home/sprime01/projects/SWE_SEED/Cargo.toml -p swe-seed-core --test hooks_runtime --test trace_lifecycle --test trace_ledger
E2E_LOG="$(mktemp /tmp/opencode/godspeed-e2e.XXXXXX)"
set -o pipefail
uv run pytest tests/e2e/test_settlement_roundtrip.py -q | tee "$E2E_LOG"
rg -q '^2 passed' "$E2E_LOG"
if just --list | rg -q 'context-check'; then just context-check; else printf '%s\n' 'context-check unavailable: record in handoff'; fi
git diff --check
```

**Done when:** All applicable commands exit 0; the E2E output says `2 passed` with no skips; the
default suite includes adapter tests; wheel, sdist, and container contain both packages; validation
catches all four invariant families; SWE_SEED proves hook/trace ownership; context-check status is
recorded honestly; and an independent review reports no unresolved S1-S2 findings. Deliberately
removing the settlement guard, adapter package entry, or canonical proposal write must fail a named
test.

**Redesign trigger:** If live cross-repository E2E services are unavailable, do not claim live
transport proof. Record the skipped E2E gate and keep release status blocked until the service-backed
roundtrip runs.

---

## Final acceptance checklist (whole plan)

- [x] Unknown, potential, and possibility identifiers cannot settle, and the adverse tests have
  teeth. *(Task 1)*
- [x] Execution evidence remains provisional in `NavigationRuntime`; adapters emit no settlement
  or caller-owned capability state from proof alone. *(Task 2)*
- [x] Learning proposals use canonical `LedgerStore` integrity, backup, and idempotent migration.
  *(Task 3)*
- [x] Wheel, sdist, container, and default pytest collection include the event adapter. *(Task 4)*
- [x] Enterprise validation fails on lifecycle, storage, adapter-authority, and distribution
  configuration regressions without claiming artifact proof. *(Task 5)*
- [x] GodSpeed-Agent analyzes SWE_SEED traces through a read-only, versioned adapter without
  inventing work-contract identifiers. *(Task 6)*
- [x] Synthetic calibration traces are explicit fixtures, never live capability evidence.
  *(Task 7)*
- [x] SWE_SEED proves hook/trace ownership and confirmed duplicate GodSpeed producers are removed.
  *(Task 8)*
- [x] Active metadata, README, HARNESS, references, and examples reflect the controlling boundary.
  *(Task 9)*
- [x] Full tests, artifacts, validation, cross-repo ownership tests, and independent review pass.
  *(Task 10)*
- [x] `git diff --check` exits 0.
- [x] No status claim appears before its corresponding test or artifact proof.
- [x] All global gates are green and distributed artifacts are rebuilt.

## Guardrails (do not violate)

- Do not let SEA-Forge authorization or SWE_SEED proof status directly promote capability.
- Do not infer an affordance ID or silently create an affordance while recording settlement.
- Do not add adapter-local settlement scoring, capability state, retries, caches, or truth ledgers.
- Do not treat provisional, synthetic, simulated, or external proxy evidence as metabolized
  capability.
- Do not weaken local-first storage, redaction, checksum, quarantine, backup, or policy gates.
- Do not rewrite historical reports or generated calibration artifacts to make current claims look
  cleaner.
- Do not delete host hooks, runtime trace capture, or public adapter functions without explicit
  confirmation and caller search at execution time.
- Do not add a new dependency unless the standard library and installed stack cannot implement the
  required contract.
- Keep each task in its own commit; stage only the files named by that task.
