# v007 Dataset Research (T01a) — recovery-prediction corpus candidates

Date: 2026-09-15. Scope: screen public agent-trajectory datasets for the v007
recovery-prediction experiment. Requirements: (1) genuine execution failures in
trajectory observations, (2) post-failure behavior observable, (3) defensible
terminal outcome (execution/test-derived), (4) stable parent IDs, (5) usable
licensing (ambiguous must be recorded as such; raw trajectory content never
committed — v006 precedent).

Method: HF API metadata (`/api/datasets/<id>`), datasets-server `/rows`
samples (network streaming via `load_dataset` stalled on large shards; rows API
used instead — values may be server-truncated, noted where relevant), README
frontmatter, and paper (arXiv 2504.21798) for label provenance. Error test:
case-insensitive keywords `error|failed|traceback|exception|assertionerror`;
strict test: `Traceback (most recent call last)|FAILED|AssertionError|...`
"mid-trajectory" = hit with >=2 subsequent messages (an action + an observation
follow it).

## Screening table

| Candidate | Revision | License | Error content mid-trajectory? | Post-failure behavior? | Terminal label defensibility | Parent ID | VERDICT |
|---|---|---|---|---|---|---|---|
| SWE-bench/SWE-smith-trajectories | `08e109b4a59eaeebf80e4675cd125d42e7ac99a4` | **mit** (card + README frontmatter) | YES: 10/10 sampled rows have kw hits in tool-role observations with continuation (74 hits/10 rows); strict traceback-level: 4/10 rows, 10 hits | YES: hits followed by assistant action + tool observation in all sampled rows | STRONG: `resolved` bool is execution-derived (SWE-bench F2P/P2P test run; paper Sec "Trajectory Collection") | `instance_id` (task) + `traj_id` (unique attempt) — stable, first-class fields | **ADMIT** (tool split) |
| nebius/SWE-agent-trajectories (re-check) | `68195a1450865274106246d0d0296a1d6807b88e` (unchanged since v006) | cc-by-4.0 (card) | YES: 10/10 sampled rows have kw hits in user-role observations mid-trajectory (5-10 obs hits/row); strict traceback excerpt verified | YES: ai(mask=true) action + user(mask=false) observation follow hits | UNCHANGED from v006: `target` bool + `exit_status` + `eval_logs` (execution-derived) | `instance_id` (+`model_name` separates runs) | **REVIVABLE** — v006 zero-error finding was an adapter bug, not a dataset property |
| SWE-Gym/SWE-Gym (original) | `bb94ed9e39bbeb96a7fcbfb533b80f25a7fd59cb` | mit (card) | n/a | n/a | n/a (FAIL_TO_PASS/PASS_TO_PASS are task metadata, not trajectory outcomes) | n/a | **EXCLUDED** — no trajectory content at all |
| R2E-Gym/R2EGym-SFT-Trajectories | `63ab4eb37668f8be0104133c21d896bedbcf8404` | **absent** (no license key in README frontmatter; API null); GitHub repo Apache-2.0 | kw hits exist in messages (10-14 msgs/row sampled) but unverifiable as failures without outcome context | not assessable | **NONE**: schema is `messages` only — no outcome field of any kind | **NONE**: no instance/run ID field; ids not cleanly derivable | **REJECT** |
| R2E-Gym/R2EGym-Verifier-Trajectories | `d8340c4605bb1a00a206a1978813cee35daeff8c` | **absent** (API null) | error text only inside flattened log embedded in verifier prompt | no (3-message verifier conversation, not an agent trajectory) | WEAK: `rewards` float is verifier-model reward, judge-derived, not a test-run resolution | absent (`docker_images` string only, not a stable task id) | **REJECT** |
| NeoHorse paper refs (arXiv 2609.08183v1, beyond Toucan) | n/a | paper states none | n/a | n/a | n/a | n/a | **NOTHING ADMISSIBLE** — primary corpus (routing-harness trajectories w/ outcomes) is internal/unreleased; public refs are generic SFT sets (OASST2, Aya, OpenThoughts3, OpenR1-Math, ToolACE, APIGen, Nemotron-SFT-SWE-v3 [already REJECTed in v006], HelpSteer2, UltraFeedback) |

## Per-candidate evidence

### SWE-bench/SWE-smith-trajectories — ADMIT
- API: https://huggingface.co/api/datasets/SWE-bench/SWE-smith-trajectories —
  sha `08e109b4a59eaeebf80e4675cd125d42e7ac99a4`, license `mit`, 12,679
  downloads, splits tool (24,100) / xml (26,076) / ticks (25,826); features:
  `messages` (string, JSON-encoded OpenAI-format list), `instance_id`,
  `resolved` (bool), `model`, `traj_id`, `patch`.
- README: https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories —
  trajectories from SWE-agent (ReAct harness) + claude-3-7-sonnet-20250219
  (also 3.5-sonnet/gpt-4o comparison runs per paper) on SWE-smith
  fault-injection task instances.
- Label provenance (paper https://arxiv.org/abs/2504.21798, "Trajectory
  Collection"): execution-based resolution — patch run against repo test suite;
  F2P tests must flip to passing, P2P must not break. 17,906 attempts on 8,686
  instances; release includes BOTH resolved=true and resolved=false rows
  (sample: 8 true / 2 false). This satisfies "verified success/fail" exactly.
- Sample (datasets-server rows, tool split, rows 0-9): every row has
  assistant/tool_call + tool-role observation structure (n_msgs 29-65);
  broad-kw tool-role hits 74 total across 10 rows (all 10 rows), strict
  traceback-level hits 10 across 4 rows.
- Genuine failure excerpt (row traj_id
  `tkrajina__gpxpy.09fc46b3...grix6fbc.8qa84d2e`, msg 19/37, role=tool):
  `OBSERVATION: Traceback (most recent call last): ... UnboundLocalError: local
  variable 'found' referenced before assignment` — followed by assistant then
  tool messages. Post-failure behavior confirmed.
- Caveats: (a) failures arise from *injected* faults (synthetic bug mutation),
  not only naturally-occurring bugs — same domain caveat applies to swegym
  episodes being natural-bug-only; v007 should record domain provenance.
  (b) Broad keyword matches include benign hits (source display containing
  `django.core.exceptions` import) — adapter should use structural failure
  signals (Traceback headers, pytest FAILED lines, shell exit markers), not
  bare substrings. (c) `messages` is a JSON string needing one parse step.
  (d) Some source repos are GPL-variant (paper Table 6): keep the standing
  rule — trajectory content is used locally, never committed.

### nebius/SWE-agent-trajectories — REVIVABLE (re-check verdict)
- Re-check result: raw rows DO contain error content in observation-like
  fields. 10/10 sampled rows (instance AnalogJ__lexicon-336, model
  swe-agent-llama-70b, all target=false) have kw hits in role=user,
  mask=false observation events with >=2 subsequent events (5-10 such
  observation hits per row), in addition to the issue-statement hit at event 1
  and kw content in ai-role messages. eval_logs (label side) also kw-positive.
- Strict excerpt (event 3/93, role=user, mask=false):
  `Traceback (most recent call last): File "/opt/conda/envs/lexicon/bin/lexicon"
  ... File "/lexicon/lexicon/client.py", line 64, in execute
  self.provider.authenticate() ...` — a genuine command-execution failure
  observation, followed by ai(mask=true) and user(mask=false) events.
- ROOT CAUSE of the v006 "zero error-keyword observations" finding — an adapter
  bug, not a dataset property. `scripts/settlement_datasets/nebius_swe_agent_adapter.py`:
  `_parse_trajectory` (lines 26-36) returns entries unchanged, and entries carry
  field `text` (HF schema: cutoff_date/mask/role/system_prompt/text), but
  `extract_actions` (line ~97) and `extract_observations` (line ~113) read
  `entry.get("content", "")` — every extracted action/observation was an empty
  string, so no keyword could ever match. `extract_payment` counts error-like
  keywords only in `eval_logs` (line ~164), so v006's nebius error_count never
  reflected trajectory observations, and `infer_settlement_quality`'s
  "recovered_success" branch (target=true + errors) could only fire off
  eval_logs, never observations.
- Required change (one line each in extract_actions/extract_observations):
  `entry.get("content", "")` -> `entry.get("text", "")` (optionally carry
  `mask`). After the fix, re-run the v006 corpus builder for nebius before
  admitting its failure episodes; label machinery (target/exit_status/
  eval_logs) needs no change. Exclude eval_logs/generated_patch/exit_status/
  target from features (v006 leak rule unchanged).
- Sample caveat: first 10 rows are all one instance/model and target=false
  (dataset appears instance-ordered); class balance must be verified on the
  full stream during ingestion, not from this sample.

### SWE-Gym/SWE-Gym — EXCLUDED
- Streamed row (train): features are exactly instance-level: instance_id,
  hints_text, patch, test_patch, created_at, problem_statement, repo,
  base_commit, version, PASS_TO_PASS, FAIL_TO_PASS. No trajectory field of any
  kind (e.g. getmoto__moto-7365 row verified). This is the *environment/task*
  dataset; agent trajectories live in SWE-Gym/OpenHands-Sampled-Trajectories
  (sha `baf3a4e4...`, already admitted in v006 as swegym_openhands).

### R2E-Gym datasets — REJECT both
- Org scan (https://huggingface.co/api/datasets?author=R2E-Gym): no
  "Traj-8k"-style set exists; the trajectory sets are R2EGym-SFT-Trajectories
  (3,231 rows), R2EGym-Verifier-Trajectories (5,750), and
  R2EGym-TestingAgent-SFT-Trajectories.
- SFT set: features = `messages` only. No outcome, no IDs. First user message
  embeds a github issue; last roles end assistant (synthesis-style). An SFT
  set of this kind is success-filtered by construction (R2E-Gym paper uses
  successful runs for SFT), so even a derived label would be degenerate.
  License ABSENT (frontmatter has no license key; API null) — recorded as such.
- Verifier set: 3-message verifier conversations (system/user/assistant) over
  a flattened interaction log inside the user message; `rewards` float is
  verifier-model reward (sampled rows: 0.0), i.e. judge-derived — fails
  requirement 3. No stable parent ID (`docker_images` only). License ABSENT.
- The R2E-Gym GitHub repo is Apache-2.0 (LICENSE verified via GitHub API), but
  that does not cure the missing outcome/ID structure; license-by-inheritance
  would be the only defensible reading and is unnecessary given REJECT.

### NeoHorse paper (arXiv 2609.08183v1) — nothing admissible
- Paper page (https://arxiv.org/html/2609.08183v1): the outcome-labeled
  trajectory corpus (~1e5-1e6 routing-harness trajectories with terminal
  outcomes and semantic-eval verdicts) is internal and not released; no HF
  dataset card exists for it. Public dataset refs are generic SFT/preference
  sets; Nemotron-SFT-SWE-v3 was already REJECTed in v006 (no outcome label).
  No candidate beyond Toucan (already rejected in v006).

## Recommendation for v007

1. **ADMIT `SWE-bench/SWE-smith-trajectories`** as the new failure-episode
   source. Config sketch:
   - `source_uri: SWE-bench/SWE-smith-trajectories`, revision
     `08e109b4a59eaeebf80e4675cd125d42e7ac99a4`, split `tool` (OpenAI
     tool-call format; xml/ticks are alternate format variants — do not mix).
   - events: parse `messages` (JSON string); assistant msgs with `tool_calls`
     = actions (signature from `tool_calls[].function.{name,arguments}`);
     role `tool` msgs = observations (pair via `tool_call_id` — same closure
     rule as swegym_openhands); first user msg = task input; drop `system`.
   - outcome: `resolved` (bool) — execution-derived; terminal-label defensibility
     strongest of all screened candidates. Exclude `patch`, `resolved` from features.
   - parent: `instance_id` (task); run key: `traj_id` (unique; multiple
     attempts per instance exist).
   - failure detector: structural signals (Traceback headers, `FAILED`/pytest
     lines, exit-code markers) in tool-role content; avoid bare substring
     matching (benign source-display hits).
   - license: mit — identified; still do not commit raw trajectory content.
2. **REVIVE `nebius/SWE-agent-trajectories`** by fixing the `content`->`text`
   field bug in `scripts/settlement_datasets/nebius_swe_agent_adapter.py`
   (extract_actions + extract_observations), then rebuild its slice of the
   corpus and re-run the error-incidence profile. This potentially turns nebius
   from a failure-episode-free source into a second failure-episode source at
   near-zero cost (cc-by-4.0, labels unchanged).
3. No other screened candidate is admissible.

UNDETERMINED (do not guess; resolve during T01b ingestion):
- SWE-smith: exact row accounting across tool/xml/ticks splits and whether any
  non-claude-3.7 rows exist in `tool` (sample showed only claude-3-7-sonnet);
  if model mixing matters for the experiment, filter on `model`.
- Nebius: class balance and per-instance coverage across the full 80,036-row
  stream (sample was single-instance, all target=false).
- SWE-smith episodes where the FIRST failure is the by-design repro-script
  failure: decide whether to treat it as a legitimate episode opener or a
  baseline event (affects failure-episode enumeration semantics).
