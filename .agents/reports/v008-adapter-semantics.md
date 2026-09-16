# v008 Adapter Semantics Audit (V1b, plan godspeed-agent-v008-r1-transfer)

Date: 2026-09-16. Scope: for each of the 54 features in the `v007_r1@1`
schema, document the per-source extraction path, transformation, semantic
meaning, and missing/default behavior over the three admitted sources
(`swegym_openhands`, `nebius_swe_agent`, `swe_smith`), then issue a per-feature
verdict for the R1 transfer representation T: **SHARED** (same semantics across
sources) / **NORMALIZABLE** (same concept, different encoding; normalization
proposed) / **SOURCE-SPECIFIC** (different meaning; exclude from T).

Method: code read of the three adapters, the corpus builder, and the feature
extractors (file:line cites below), plus a FULL pass over the corrected corpus
`data/settlement_datasets/corpora/v007c-trajectories/*.jsonl` (15,736 usable
parents, corpus manifest sha256s per `corpus_manifest.json`) and raw-row
probes via the HF datasets-server (`/rows`, ≤10 rows per call). Existing
measurements are cited to `.agents/reports/v007-critique.md` (v007-crit) and
`.agents/reports/v007-dataset-research.md` (v007-dsr). Only this report was
written; no repo file changed.

## 1. Schema inventory

The 54 features = 29 + 10 + 5 + 10 (confirmed by `data/settlement_datasets/corpora/v007c-episodes/manifest.json`,
`feature_schemas.r1_total.n_features = 54`):

| Block | Count | Definition |
|---|---|---|
| v006 family (`V006_FEATURES`) | 29 | `scripts/settlement_datasets/v006_features.py:163-202` |
| v005 prefix family minus `dataset_id` (`_V005_PREFIX_FEATURES`) | 10 | `V005_FEATURES` (`v006_features.py:149-161`) minus `dataset_id` (`v007_recovery.py:265-268`) |
| R0 episode-positional (`R0_EPISODE_FEATURES`) | 5 | `v007_recovery.py:257-263` |
| R1 additions (`R1_ADDITIONS`) | 10 | `v007_recovery.py:275-286` |

`R0_FEATURES` (44) at `v007_recovery.py:272`; `R1_FEATURES = R0_FEATURES + R1_ADDITIONS` (54) at line 288.
`dataset_id` is NOT one of the 54: `build_episode_frame` pops it from family
outputs and carries it as an identity column (`v007_recovery.py:790,807`).
Note for transfer: `DATASET_ID_MAP` (`v006_features.py:135-139`) has no
`swe_smith` entry, so swe_smith rows carry the `-1` sentinel
(`v007_recovery.py:790`); a fourth source would also get `-1`. It enters the
7-feature ablation schema (`v005_minimal_recovery@1`), not R0/R1.

### Corpus event primitives (what features actually read)

Every event is built by `_event_from_entry` (`build_trajectory_corpus.py:247-268`):

| Field | Derivation (source-independent) | Cite |
|---|---|---|
| `i` | raw `turn_index` = index in the source message/entry list | :255 |
| `kind` | `action` / `observation` per adapter partition | :247 |
| `role` | raw role carried through (`assistant`/`tool`, `ai`/`user`, `assistant`/`tool`) | :249 |
| `content_len` | `len(content)` | :258 |
| `hash` | `sha1(content)[:10]` | :259 |
| `mentions_bash` | `kind==action AND role=='assistant' AND 'bash' in content.lower()` | :260 |
| `is_error` | `kind==observation AND any kw in content.lower()`, kw = `error, fail, traceback, exception, assertionerror` | :134,:261-262 |
| `cmd_family` | `kind==action AND role=='assistant'` only; first-match keyword regexes `git > install > test > python > edit > inspect`, else `other`; empty content -> `None` | :136-166,:236-244,:263-265 |
| `has_terminal_output` | observation contains `"New Terminal Output:"` (agenttrove marker) | :266-267 |
| `ctx` | count of adapter `context_positions(raw)` strictly below `i` | :385-388 |

Feature readers use ONLY: `kind`, `is_error`, `hash`, `cmd_family`,
`mentions_bash`, `ctx`, `i` (verified across `v006_features.py:344-651` and
`v007_recovery.py:551-676`). `content_len` and `has_terminal_output` feed NO
feature in the 54. `has_terminal_output` is 0 for all 47,443 observations in
v007c (full-corpus scan): the marker is agenttrove-only and agenttrove is
rejected; the OpenHands/SWE-smith observation prefix is `"OBSERVATION:"`
(raw rows, datasets-server). Dead marker, retained for schema stability.

Events are stably sorted by `i` with actions before observations at ties;
`i` values are unique per parent because actions/observations are
role-partitioned over the same raw index space (`build_trajectory_corpus.py:375-378`).

## 2. Per-source extraction path

| | swegym_openhands | nebius_swe_agent | swe_smith |
|---|---|---|---|
| Raw rows read | `raw['messages']` (roles: system/user/assistant/tool) | `raw['trajectory']` entries (`role`,`text`|`content`,`mask`) | `raw['messages']` JSON string (`swe_smith_adapter.py:67-77`); OpenAI format with typed content parts and `tool_calls` |
| Actions | role `assistant` (`swegym_openhands_adapter.py:80-92`); content = `msg['content']` ONLY — `tool_calls` NOT rendered | role `ai`/`assistant` (`nebius_swe_agent_adapter.py:92-108`); content = `text` or `content` (C1 fix, :105) | role `assistant` (`swe_smith_adapter.py:166-184`); content = flattened text **plus rendered `tool_calls[].function.{name,arguments}`** (:93-105,:171-175) |
| Observations | role `tool` (:94-105) | role `user`/`tool` (:110-125) — **includes the issue statement and harness prompts** | role `tool` (:186-198); content flattened from typed parts (:80-90) |
| Context (`context_positions`) | roles not in (assistant, tool) (:107-120) | roles not in (ai, assistant, user, tool) (:127-140) → system only | roles not in (assistant, tool) (:200-214) |
| Terminal outcome | `resolved` + `test_result` (:122-159); undefined `resolved` -> False w/ low confidence | `target` + `eval_logs` (:142-170) | `resolved` tri-state; null -> rejected (:216-248) |
| Payment `commands` | bash-mention count (:169-175,:207) | **ai-turn count** (:200) — not a command count | bash-mention count over rendered actions (:256-260) |
| Payment `error_count` | kw over tool messages (:177-192) | kw over terminal `eval_logs` ONLY (:183-187) — terminal, not in-trajectory | kw over extracted observations (:262-275) |
| `tool_names` manifest | extracted from `raw['tools']` (:241-255,:311) | absent (metadata: model_name, exit_status; :284-289) | omitted — no tools column (docstring :41-42) |
| Payment counters used by the 54 features | NOT used: the 54 read only prefix-derived events + ctx; the verbatim `counts` block feeds only `v005_full_semantics`, absent from v007 schemas (v007-crit checklist 3) | same | same |

## 3. Measured per-source rates (FULL v007c corpus scan)

| Metric | swegym_openhands | nebius_swe_agent | swe_smith |
|---|---|---|---|
| Parents | 1,574 | 4,554 | 3,708 |
| Events (actions/obs) | 34,454 / 31,674 | 113,494 / 113,494 | 103,745 / 66,321 |
| Empty-content actions | **16,529 (47.97%)** (per-parent mean 52.66%) | 0 | 0 |
| `cmd_family == None` | 16,529 (47.97%, empty content) | **113,494 (100%, role gate)** | 0 |
| cmd_family populated: other/inspect/python/edit/git/test/install | 11,720/4,404/1,329/288/130/**26**/28 | –/–/–/–/–/**0**/– | 8,092/11,282/29,238/50,890/476/**2,904**/863 |
| `cmd_family=='test'` share of actions | 0.075% | **0.000%** | 2.80% |
| `mentions_bash` share of actions | 0.34% | **0.000%** | 40.04% |
| `is_error` share of observations | 55.54% | 48.26% | 42.59% |
| FIRST observation `is_error` | 464/1,574 parents (29.5%) | **4,554/4,554 parents (100%)** | 1,184/3,708 (31.9%) |
| Parents w/ ≥1 error obs | 1,574/1,574 (100%) | 4,554/4,554 (100%) | 2,435/3,708 (65.7%) |
| Parents with ZERO observation events | 0 | 0 | **1,271 (34.3%), all label=1** |
| Parents with mid-stream context (some `ctx < n_context_events`) | 918/1,574 (58.3%) — matches v007-crit MAJOR-1 | 0/4,554 — matches v007-crit | **1,271/3,708 — EXACTLY the zero-observation set** |
| `n_context_events` mean/parent | 3.25 | 1.00 | 2.0 (observing parents) / up to ~30 (no-obs parents) |
| `trailing_context > 0` | 0 | 0 | 0 |

Cross-validation: the 918 / 1,271 / 0 interleaved counts equal the v007-crit
MAJOR-1 head-only test (918/1574 swegym, 1271/3708 swe_smith, 0/4554 nebius);
nebius `leading_error_runs = 4,554 = parents_scanned` in the v007c episode
manifest.

### New structural findings (this audit)

**F1 — Nebius role gate kills cmd_family/mentions_bash for the whole source.**
`_event_from_entry` computes `cmd_family`/`mentions_bash` only when
`role == 'assistant'` (`build_trajectory_corpus.py:253,260,263-265`), but the
nebius adapter carries the raw role `ai`
(`nebius_swe_agent_adapter.py:97-101`). Result (measured): 100% of nebius
actions have `cmd_family=None` and `mentions_bash=False`. Under
`_family_value = cmd_family or 'none'` (`v006_features.py:244-246`), every
nebius action is the pseudo-family `none` — so `used_family_diversity ≡ 1`,
`tool_switch_rate ≡ 0`, `strategy_change_after_first_failure ≡ 0`,
`attempt_family_change ≡ 0`, and all four verification features ≡ 0 for
nebius. Note this is a ROLE-GATE `None`, not the documented empty-content
`None` (v007_recovery.py:101-105): nebius empty-content actions = 0%.

**F2 — swegym tool_calls are never rendered; 48% of swegym actions are
empty.** Raw swegym assistant messages carry the actual command in
`tool_calls[].function.{name,arguments}` with `content` usually `""`
(datasets-server rows, `SWE-Gym/OpenHands-Sampled-Trajectories` train.raw:
assistant messages with `content_len=0`, `has_tool_calls=True`, e.g.
`execute_bash`, `str_replace_editor`). The swegym adapter reads only
`msg['content']` (:89) — unlike the swe_smith adapter, which renders calls
(:93-105). Consequences: (a) 48% of swegym actions share the empty-string
hash, so hash-identity features (`repeated_action_rate`,
`max_repeated_action_run`, `stuck_cycle_max`,
`attempt_repeats_prior_action`) count distinct tool calls as "repeats";
(b) `cmd_family` classifies PROSE, not commands (an assistant message saying
"let me check the files" lands in `inspect`); (c) `mentions_bash` (0.34%) is a
prose-mention rate, not a shell-command rate.

**F3 — Nebius observations conflate task input and harness prompts with tool
output.** Raw nebius `user`/`mask=false` entries include the issue statement
(raw position 1: "We're currently solving the following issue... ISSUE: ...
TypeError..."), shell/traceback output, and `bash-$` prompt scaffolding
(datasets-server row, `AnalogJ__lexicon-336`). Measured: 100% of nebius
parents have `is_error` on their FIRST observation — the issue statement
commonly names the bug ("TypeError"). This is why the episode manifest shows
`leading_error_runs = 4,554 = every parent` (leading runs never open episodes,
`v007_recovery.py:484-492`, but they DO enter `error_count`, `error_rate`,
`distinct_error_count`, `has_failure ≡ 1`, and `recovery_attempt_count` —
every parent's first action follows the "error" and counts as a recovery
attempt).

**F4 — swe_smith `tool` split contains TWO storage formats; 34.3% of the
ingested slice lost its observations.** Raw probes (datasets-server):
offsets 0–5,000 include canonical rows (`system:1, user:1, assistant:N,
tool:N-1`); offsets 12,000/20,000 rows are user-alternating
(`system:1, user:N-1, assistant:N` — observations stored as `user` messages,
including for `resolved=False` rows; models claude-3-7 / claude-3-5). The
swe_smith adapter extracts observations from `tool` role only (:186-198), so
user-alternating rows produce parents with ZERO observation events and all
their (real) observations swallowed into `context_positions`. Measured in
v007c: 1,271/3,708 swe_smith parents (34.3%) have zero observation events,
**all label=1**, with `n_context_events ≈ n_actions + 2`. This set is exactly
the v007 "interleaved context" set (F1 note: v007-crit MAJOR-1's "swe_smith
1271/3708 interleave" is this artifact, not true interleaved user context).
Their actions still carry rendered tool_calls (cmd_family populated: edit
15,318 / python 10,403 / inspect 4,619 / test 1,175 / mentions_bash 43.8%).
Because episodes require error observations, these 1,271 parents contribute
ZERO episodes to `v007c-episodes` (parents_with_episodes 2,413 vs 3,708
scanned) — swe_smith failure episodes are drawn only from the canonical-format
sub-population, and the swallowed successes skew episode-parent label
composition. The exact class skew deeper in the split (beyond the 5,000-row
ingestion window) is UNDETERMINED.

**F5 — swegym mid-stream context is genuine but small.** All 918 interleaved
swegym parents have `ctx` growing between first and last event; the excess
context at/after the first event is 1–20 messages (median 2). The C1 `ctx`
rule handles these correctly (v007c-critique §1). Whether these user-role
messages are true user context or user-role observations is UNDETERMINED from
hashed events (raw probe of 10 rows found none; they occur deeper in the
window) — impact bounded at ≤20 messages/parent.

## 4. Feature-by-feature audit

Legend: inputs = the event primitives each feature reads. "Per-source
delta" summarizes the semantic difference; "missing/default" is the value when
the quantity is undefined (v006 convention: 0.0 + `has_*` indicator where
disambiguation matters, `v006_features.py:100-104`).

### 4.1 Depth and closure (kind-based)

| Feature | Inputs | Per-source semantics / delta | Missing→default | Verdict |
|---|---|---|---|---|
| `n_events` | kind | Count over `events[:k]`. `i`-sorted merge is faithful for all three (role-partitioned indices, stable sort). Nebius obs population includes issue statement + prompts (F3); swe_smith no-obs parents have actions only but contribute no episodes (F4). | – | SHARED |
| `n_actions` | kind | Assistant(ai)-message count. Comparable "agent step" semantics in all three. | 0 | SHARED |
| `n_observations` | kind | swegym/swe_smith: tool outputs. nebius: tool output + issue statement + harness prompts (F3). swe_smith user-alternating rows: 0 (observations missing entirely, F4) — absent from the episode frame. | 0 | NORMALIZABLE (nebius leading-issue → context reclass; swe_smith dual-format adapter fix) |
| `unresolved_action_rate` | kind | "resolved iff any later observation" (`v006_features.py:446-452`). Same formula; nebius alternation inflates closure toward 1 (every ai followed by user entry); F4 parents absent from frame. | 0.0 | NORMALIZABLE (same fixes) |
| `action_observation_closure_ratio` | kind | 1 − unresolved rate. Same deltas. | 0.0 | NORMALIZABLE (same fixes) |

### 4.2 Tool dynamics (cmd_family + action hash)

| Feature | Inputs | Per-source semantics / delta | Missing→default | Verdict |
|---|---|---|---|---|
| `used_family_diversity` | cmd_family | Distinct `_family_value` over actions. swe_smith: real command taxonomy (F4 caveat: prose-only for user-alternating rows — absent from frame). swegym: prose taxonomy + 48% `none`. nebius: ≡1 (constant; F1). As encoded, the feature means different things per source. | – | SOURCE-SPECIFIC |
| `tool_switch_rate` | cmd_family | Adjacent-family transition rate. nebius ≡0; swegym counts prose↔`none` transitions; swe_smith counts command-family switches. | 0.0 | SOURCE-SPECIFIC |
| `repeated_action_rate` | hash | Adjacent equal action hashes. swegym: 48% of actions hash to sha1("") → distinct tool calls counted as repeats (F2). nebius/swe_smith: text-level identity is meaningful. | 0.0 | SOURCE-SPECIFIC |
| `max_repeated_action_run` | hash | Longest identical-action run. Same swegym empty-hash distortion (F2). | 0.0 | SOURCE-SPECIFIC |

### 4.3 Errors (is_error over observations)

| Feature | Inputs | Per-source semantics / delta | Missing→default | Verdict |
|---|---|---|---|---|
| `error_count` | is_error | Same keyword encoding (`build_trajectory_corpus.py:134`). swegym/swe_smith: tool-output failures (benign substring hits exist — e.g. displayed `django.core.exceptions` imports; v007-dsr SWE-smith caveats). nebius: +1 spurious error per parent (issue statement, F3) → floor of 1 and `has_failure ≡ 1`. | 0.0 | NORMALIZABLE (F3 reclass; encoding otherwise identical) |
| `error_rate` | is_error | error_count / prefix length. Same deltas. | 0.0 | NORMALIZABLE (F3) |
| `distinct_error_count` | is_error+hash | Distinct error hashes. nebius: issue-statement hash adds a per-instance constant. Otherwise comparable (hashes well-defined; observations never empty in any source). | 0.0 | NORMALIZABLE (F3) |
| `repeated_error_rate` | is_error+hash | Repeated error-payload rate. Same basis; comparable. | 0.0 | NORMALIZABLE (F3) |
| `has_failure` | is_error | error_count > 0. Currently ≡1 for swegym (100% parents have error obs) and nebius (F3); 65.7% for swe_smith. | 0.0 | NORMALIZABLE (F3; post-fix nebius < 100%) |

### 4.4 Recovery (is_error + kind + i)

| Feature | Inputs | Per-source semantics / delta | Missing→default | Verdict |
|---|---|---|---|---|
| `recovery_attempt_count` | kind+is_error | Action at `error_pos + 1` (list adjacency). nebius: first action of EVERY parent counts (follows the issue-statement "error", F3). swegym/swe_smith: action following a genuine failed output. | 0.0 | NORMALIZABLE (F3 reclass removes the spurious first-action attempts) |
| `recovery_rate` | kind+is_error | attempts / errors. Same deltas. | 0.0 | NORMALIZABLE (F3) |
| `recovery_latency_mean` | kind+is_error | Event-position gap error→next non-error observation. Comparable once F3 fixed; nebius latency currently shortened by prompt scaffolding. | 0.0 | NORMALIZABLE (F3) |
| `first_recovery_latency` | kind+is_error | Same, first error only. | 0.0 | NORMALIZABLE (F3) |
| `strategy_change_after_first_failure` | cmd_family+is_error | Family change across first error. nebius ≡0 (all `none`, F1); swegym prose-families; swe_smith command-families. | 0.0 | SOURCE-SPECIFIC |
| `error_recovery_ratio` | is_error+i | H turn-index rule over observations (`v006_features.py:296-313,391-405`); `i` is the raw sequence index in all three — same spacing semantics. Inherits F3. | 0.0 | NORMALIZABLE (F3) |
| `has_recovery` | kind+is_error | ≥1 error followed by non-error obs in prefix. | 0.0 | NORMALIZABLE (F3) |

### 4.5 Verification (cmd_family == "test")

Task question: does each harness's taxonomy contain test commands comparably?
**No.** `cmd_family=='test'` share of actions: swegym 0.075% (26 actions —
prose mentions only; real pytest runs hide in unrendered `execute_bash`
arguments, F2), nebius 0.000% (role gate, F1), swe_smith 2.80% (2,904
rendered calls). Additionally the taxonomy counts only
pytest/unittest/tox/nosetests/npm test/make test/cargo test; `check`/`diff`
forms land in inspect/git (`v006_features.py:73-79`).

| Feature | Verdict |
|---|---|
| `verification_action_count` | SOURCE-SPECIFIC |
| `verification_rate` | SOURCE-SPECIFIC |
| `verification_after_edit_count` | SOURCE-SPECIFIC (also inherits edit-family divergence: swegym prose-edit 288 vs swe_smith rendered 50,890) |
| `verification_after_recovery_count` | SOURCE-SPECIFIC |

### 4.6 Evidence (observation hash + kind)

| Feature | Inputs | Per-source semantics / delta | Missing→default | Verdict |
|---|---|---|---|---|
| `observation_novelty_rate` | hash | First-occurrence share of observation hashes. Observations never empty in any source; repeated identical tool outputs (verified in raw swegym: duplicate `str_replace_editor view` loops) are genuine repeats everywhere. | 0.0 | SHARED |
| `actions_since_last_observation` | kind | Trailing action count. | 0.0 | SHARED |
| `actions_without_observation_rate` | kind+hash | No-later-observation OR next-obs-hash == prev-obs-hash rule (`v006_features.py:583-594`). Same semantics; obs hashes well-defined in all sources. | 0.0 | SHARED |

### 4.7 Stuck loop (action hash + error hash)

| Feature | Per-source semantics / delta | Verdict |
|---|---|---|
| `stuck_cycle_max` | Signature (action hash, error obs hash) chained adjacently (`v006_features.py:597-617`). swegym: constant empty action hash makes spurious chains possible when identical error outputs repeat (F2). nebius/swe_smith: meaningful. | SOURCE-SPECIFIC |
| `stuck_loop_indicator` | `stuck_cycle_max >= 2`. Same. | SOURCE-SPECIFIC |

### 4.8 v005 prefix family (ctx, kind, mentions_bash, is_error, i)

Post-C1 all three sources are `context_scoped: true` (v007c corpus manifest),
`elapsed_raw = ctx_of_last_event + k` (`v006_features.py:372-374`).

| Feature | Inputs | Per-source semantics / delta | Missing→default | Verdict |
|---|---|---|---|---|
| `payment_predicted_total` | ctx | Witnessed-message estimate. Rule identical; nebius ctx ≡1 (leading system only, F3 context is head-only), swegym/swe_smith ctx grows mid-stream (918 / 1,271 parents — the swe_smith mass is F4-swallowed observations, counted as context: numerically right for "messages witnessed", semantically the events are missing). | elapsed=max(raw,1) | SHARED (definition); distribution skews noted |
| `payment_actual_total` | kind, mentions_bash, is_error | actions+obs+commands+errors. `commands = mentions_bash` differs in MEANING: swe_smith ≈ shell-call rate (the substring `bash` fires inside the rendered tool NAME `execute_bash`, F2 note), swegym ≈ prose mention rate, nebius ≡0 (F1). Composite therefore source-skewed. | 0.0 | NORMALIZABLE (after N1/N2 below; re-measure before admitting to T) |
| `payment_error` | above | \|actual − predicted\|. Inherits the commands divergence. | 0.0 | NORMALIZABLE (same) |
| `horizon_delta` | above | Blend of inverse risk and payment efficiency. Inherits error (F3) + commands (F1/F2) divergences. | 0.0 | NORMALIZABLE (N1+N2+N3) |
| `risk_estimate` | is_error | min(1, error_count/elapsed). Inherits F3. | 0.0 | NORMALIZABLE (F3) |
| `debt_estimate` | kind | Nonzero only when actions exist and no observation yet; identical rule, mostly 0 in all sources. | 0.0 | SHARED |
| `tool_diversity_count` | parent `tool_names_manifest` | Pre-trajectory tool config. Populated ONLY for swegym (raw `tools` column); nebius and swe_smith have none → 0. Documented dataset skew (`v006_features.py:55-59`). The feature means "configured tools" and is structurally absent for 2/3 sources. | 0 | SOURCE-SPECIFIC |
| `error_recovery_ratio` | is_error, i | See 4.4. | 0.0 | NORMALIZABLE (F3) |
| `action_observation_ratio` | kind | Actions/observations. Inherits nebius population skew (+1 issue-statement obs per parent, F3); F4 parents absent from frame. | 0.0 | NORMALIZABLE (F3) |
| `avg_actions_per_step` | kind, ctx | n_actions / (ctx+k). Post-C1 rule identical; comparable. | 0.0 | SHARED |

### 4.9 R0 episode-positional (episode scan; `v007_recovery.py:590-604`)

| Feature | Per-source semantics / delta | Missing→default | Verdict |
|---|---|---|---|
| `fail_event_index` | Absolute opening index `e` in the same `i`-sorted event space for all three. Nebius indices shifted by the leading issue observation (+1 obs); swe_smith no-obs parents contribute no episodes. | – | SHARED |
| `prior_episode_count` | Episodes opened before this one; same scan rule. Inherits F3 only via episode enumeration (leading runs never open episodes — issue statement excluded by design). | 0.0 | SHARED |
| `prior_escape_count` | Prior episodes' escape positions < e; == prior_episode_count by the maximality argument (v007_recovery.py:70-80; v007-crit NOTE-4). Same note as above. | 0.0 | SHARED |
| `errors_opening_run_available_at_r0` | Constant 1.0 by construction (:84-87,:600). | 1.0 | SHARED |
| `current_streak_prior_nonerror` | Backward non-error-observation walk from e (:571-587). Nebius: the leading issue-statement error bounds every streak (its is_error is spurious, F3). | ≥1 by construction; 0.0 n/a | NORMALIZABLE (F3) |

### 4.10 R1 additions (`v007_recovery.py:607-676`)

| Feature | Per-source semantics / delta | Missing→default | Verdict |
|---|---|---|---|
| `recovery_attempt_present` | 1.0 on every R1 row by construction (:622). | 0.0 on R0 rows | SHARED |
| `has_prior_action` | Kind walk; identical. | 0.0 | SHARED |
| `has_pre_failure_action` | Kind walk; identical (coincides with prior action by the first-attempt argument, :96-100). | 0.0 | SHARED |
| `attempt_repeats_prior_action` | Action hash equality. swegym: empty-hash distortion (F2). nebius/swe_smith: text identity meaningful. | 0.0 + indicators | SOURCE-SPECIFIC |
| `attempt_family_change` | cmd_family comparison. nebius ≡0 (F1); swegym prose families; swe_smith commands. | 0.0 | SOURCE-SPECIFIC |
| `obs_between_failure_and_attempt` | kind counts in (e, attempt). Nebius mid-trajectory user entries are mostly genuine tool output; minor scaffolding. | 0.0 | SHARED |
| `new_obs_between_failure_and_attempt` | hash novelty in window. Observations never empty; comparable. | 0.0 | SHARED |
| `attempt_result_is_error` | is_error of `events[attempt+1]`. Same keyword encoding; genuine tool output in all sources at this position. | 0.0 + `has_attempt_result` 0.0 | NORMALIZABLE (F3 residual scaffolding only) |
| `has_attempt_result` | kind check; identical. | 0.0 | SHARED |
| `attempt_result_same_hash_as_failure` | "exact same failure payload repeated". Observation hashes well-defined everywhere. | 0.0 | SHARED |

## 5. Verdict tally

| Verdict | Count | Features |
|---|---|---|
| SHARED | 19 | n_events, n_actions, observation_novelty_rate, actions_since_last_observation, actions_without_observation_rate, payment_predicted_total, debt_estimate, avg_actions_per_step, fail_event_index, prior_episode_count, prior_escape_count, errors_opening_run_available_at_r0, recovery_attempt_present, has_prior_action, has_pre_failure_action, obs_between_failure_and_attempt, new_obs_between_failure_and_attempt, has_attempt_result, attempt_result_same_hash_as_failure |
| NORMALIZABLE | 21 | n_observations, unresolved_action_rate, action_observation_closure_ratio, error_count, error_rate, distinct_error_count, repeated_error_rate, has_failure, recovery_attempt_count, recovery_rate, recovery_latency_mean, first_recovery_latency, error_recovery_ratio, has_recovery, payment_actual_total, payment_error, horizon_delta, risk_estimate, action_observation_ratio, current_streak_prior_nonerror, attempt_result_is_error |
| SOURCE-SPECIFIC | 14 | used_family_diversity, tool_switch_rate, repeated_action_rate, max_repeated_action_run, strategy_change_after_first_failure, verification_action_count, verification_rate, verification_after_edit_count, verification_after_recovery_count, stuck_cycle_max, stuck_loop_indicator, tool_diversity_count, attempt_repeats_prior_action, attempt_family_change |

## 6. Normalizations worth preregistering (highest value first)

- **N1 — swegym tool-call rendering** (`swegym_openhands_adapter.py:89`):
  append `_render_tool_calls`-style signatures (port `swe_smith_adapter.py:93-105`)
  to action content. Fixes F2 wholesale: restores command-level `cmd_family`
  (incl. `test`), makes `mentions_bash` a shell-call rate, and removes the
  48% empty-string action hash. Unblocks 8 of the 14 SOURCE-SPECIFIC features.
- **N2 — nebius role gate** (`build_trajectory_corpus.py:253` or
  `nebius_swe_agent_adapter.py:101`): treat `ai` as assistant (or map the
  role at the adapter). Restores `cmd_family`/`mentions_bash` computability.
  Caveat: nebius ai text is reasoning prose; measure post-fix coverage before
  admitting family features to T.
- **N3 — nebius leading-context reclass**
  (`nebius_swe_agent_adapter.py:127-140`): include user-role entries before
  the first ai entry in `context_positions` (the issue statement). Removes the
  100% leading error run, the spurious `error_count` floor, `has_failure ≡ 1`,
  and the spurious first recovery attempts. Changes episode enumeration →
  requires a correction slice and corpus rebuild (v007c → v008-class), not a
  feature-side patch.
- **N4 — swe_smith dual-format adapter** (`swe_smith_adapter.py:186-198,200-214`):
  detect user-alternating rows (tool responses as user messages paired to
  assistant `tool_calls` by position) and extract them as observations +
  context properly. Recovers the 1,271 swallowed-observation parents (34.3% of
  the slice, all label=1 in the current window) or justifies excluding the
  variant rows explicitly.
- Post-N1–N4, re-measure per-source `cmd_family=='test'` coverage and
  `mentions_bash` semantics before re-classifying the verification and
  tool-dynamics features; `tool_diversity_count` stays excluded regardless
  (manifest exists only for swegym).

## 7. Bottom line for T

As encoded, 14 of 54 features are source-specific (constant or
differently-meaning for at least one source) and 21 more inherit one of three
mechanical encoding divergences (F1 role gate, F2 unrendered tool calls, F3
issue-statement-as-observation). A pooled transfer model over the current
v007c corpus would treat harness format as signal. Either transfer over the
19-feature SHARED core, or preregister N1–N4, rebuild the corpus, and
re-audit with the same measurements before widening T.
