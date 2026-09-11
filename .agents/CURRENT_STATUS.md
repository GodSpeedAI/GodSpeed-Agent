# Current Status

Updated: 2026-09-09

## Active Objective

Complete and verify Hugging Face dataset calibration pipeline run `hf-calibration-005-features` with richer pre-outcome features and ensure solver convergence. **Status: Complete.**

## Last Completed Task

Implemented the full 10-task correction plan on branch
`audit-corrections/neatcode-2026-07-29` (one commit per task):

- **Task 1** — `record_settlement()` rejects unknown/potential/possibility IDs
  via `_require_executable_affordance()` before any settlement-derived write;
  CLI/MCP surface the typed `settlement_requires_executable_affordance` error.
- **Task 2** — `ingest_execution_evidence()` persists external proof as
  `provisional` (match/mismatch is a proof fact, not settlement); writes only
  `execution_evidence`; adapter emits `ExecutionEvidenceIngested`, never
  `SettlementRecorded`/caller-owned capability from proof; outbox replaces
  parallel truth ledgers.
- **Task 3** — learning proposals moved into `LedgerStore`
  (`append_learning_proposal`/`query`/`migrate_legacy_learning_proposals`);
  idempotent fail-safe legacy migration.
- **Task 4** — `agentic_capability_loop` ships in wheel/sdist/container; default
  pytest collection includes its tests; `tests/test_distribution.py` proves it.
- **Task 5** — validation enforces `settlement_invariants`,
  `adapter_authority`, `developmental_truth_storage`, `distribution_configuration`
  with per-check teeth.
- **Task 6** — read-only SWE_SEED trace reader
  (`swe_seed_trace_reader.py`); provisional analysis, no fabricated IDs.
- **Task 7** — synthetic trace generation isolated as explicit fixtures
  (`synthetic_trace_fixture.py`); no env-var activation; labeled synthetic.
- **Task 8** — deleted host hooks + `trace_capture.py` (user-confirmed);
  structure tests pin the boundary; F-08 supersession notices added.
- **Task 9** — package/README/HARNESS/ledger docs aligned to settlement/navigation
  runtime + F-08 boundary; docs-alignment assertions extended.
- **Task 10** — final conformance + independent review; resolved all S2 findings
  (atomic `append_event_if_absent` fixes idempotency races) + container gap.

## Verification

- `uv run pytest -q` → **601 passed, 2 skipped** (the 2 skips are the live-service
  E2E roundtrip; run with services up below).
- `uv run pytest tests/test_distribution.py -q` → 6 passed; wheel + sdist built,
  clean isolated import of both packages succeeds.
- `docker build -t godspeed-agent-audit-fix .` succeeds; container imports
  `agentic_capability_loop` + `godspeed_nav`.
- `validate` → status `pass`; all four invariant checks pass.
- E2E: `docker compose -f tests/e2e/docker-compose.yml up -d` then
  `uv run pytest tests/e2e/test_settlement_roundtrip.py -q` → **2 passed**
  (live NATS+Postgres roundtrip). Default suite skips these when services are down.
- SWE_SEED ownership: `cargo test -p swe-seed-core --test hooks_runtime
  --test trace_lifecycle --test trace_ledger` → all pass (3+5+10).
- Independent `code-review-and-quality` review: **no S1 findings**; all S2
  findings resolved.
- `git diff --check` clean.

## Changed Files (summary)

`godspeed_nav/runtime.py`, `godspeed_nav/cli.py`, `godspeed_nav/storage.py`,
`godspeed_nav/validation.py`, `mcp/cybernetic_nav_server/server.py`,
`pyproject.toml`, `Dockerfile`, `.dockerignore`, `.claude-plugin/plugin.json`,
`AGENTS.md`, `README.md`, `HARNESS.md`, `agentic_capability_loop/adapters.py`,
`agentic_capability_loop/learning_proposals.py`, 4 settlement-dataset scripts,
new `scripts/settlement_datasets/{swe_seed_trace_reader,synthetic_trace_fixture}.py`,
new tests (`test_distribution`, `test_swe_seed_trace_ingestion`,
`test_synthetic_trace_fixtures`), deleted `hooks/*`, `godspeed_nav/trace_capture.py`,
`tests/test_live_harness_trace_capture.py`, superseded doc notices.

## Next Steps / Blockers

- None blocking the plan. The only environment-dependent gate is the live E2E
  roundtrip, which passes when `tests/e2e/docker-compose.yml` services are up.
- `just context-check` is unavailable in this checkout (no recipe) — recorded
  honestly here per plan Task 10.

## Decisions

- F-08 controlling: SWE_SEED owns hooks/traces; GodSpeed-Agent owns settlement
  + developmental state.
- Package/plugin name kept as `godspeed-agent-harness` (not externally renamed);
  only descriptions changed to settlement/navigation runtime language.
- Task 8 deletions were explicitly user-confirmed.
