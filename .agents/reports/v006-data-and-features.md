# v006 Data and Features: NeoHorse-1 trajectory distinctions + dataset admissibility

Date: 2026-09-15. Read-only research; no repo files modified.
Paper: NeoHorse-1, https://arxiv.org/html/2609.08183v1 (fetched and verified; all section numbers below are from that HTML).
Scope guard: training architecture (curriculum, on-policy distillation, routing tiers) deliberately NOT reproduced; only trajectory-state distinctions.

## 1. Paper-derived distinctions (for a deterministic binary settlement classifier)

### 1.1 Trajectory composition (Sec 3.1 "Data Composition")
- A trajectory is "a complete interaction executed by the deployment harness, preserving user requests, model responses, tool calls, environment observations, recovery attempts, and terminal outcomes" (Sec 3.1). This is the paper's canonical event vocabulary; v006 event schema should use the same six event kinds.
- Intermediate granularity: a "user turn" begins at a user request and ends at the next request or task termination; a "subscene" groups adjacent user turns sharing a local goal; "Each record remains linked to its parent trajectory and subscene" (Sec 3.1). Implication: every event record must carry a parent trajectory id; segmentation into turns is the natural feature window.
- Within a user turn, "the current request and its interleaved reasoning, tool calls, and observations are retained to preserve the reasoning-action-feedback chain" (Sec 3.1): order of reasoning -> action -> observation inside a turn is load-bearing.

### 1.2 Structural validation rule set (Sec 3.2 "Structural validation")
All rules are explicitly rule-based: "Because these properties are directly observable from the trajectory, they are evaluated using reproducible rules rather than model-based scores" (Sec 3.2). Rules:
- Reconstruct at turn level: requests, model responses, tool calls, tool observations, terminal events.
- Verify: payload readability; supported message structure; request and response presence; CAUSAL EVENT ORDER; closure of tool-call/result pairs "through identifiers and execution branches".
- Detect: missing responses; orphan observations; duplicated or conflicting tool-call identifiers; unresolved internal calls; ambiguous terminal branches.
- Three gate outcomes: internally complete (proceeds), partially recoverable ("contribute only causally closed sub-trajectories" — i.e., cut at the last closed pair), quarantined ("ambiguous event ownership or no recoverable supervision target").
- "Structural validity ... does not imply correct tool selection or task success" (Sec 3.2): structural features alone cannot be the label.

### 1.3 Six-dimensional semantic evaluation (Sec 3.2 "Semantic evaluation")
- Dimensions: goal attainment, instruction adherence, tool use, evidence consistency, error recovery, termination — evaluated on "a normalized semantic event stream".
- Split by mechanism: "High-certainty failures—such as a missing final response, an unresolved tool call, or an unrecovered terminal error—are detected deterministically. Cases that require task-level interpretation are evaluated by a semantic judge that is restricted to evidence explicitly present in the trajectory" (Sec 3.2). The judge is evidence-bounded; "Missing evidence or an interrupted judge call is never converted into a positive verdict".
- Segment-wise: "Long trajectories are evaluated in segments and subsequently aggregated at the turn level so that intermediate failures can be distinguished from successful later recovery" (Sec 3.2). Classifier corollary: features must be computed per segment/prefix, never only trajectory-globally, or early-failure-late-recovery collapses.
- Verdict scale per dimension: PASS / WARN / FAIL / NOT_EVALUATED, with evaluation coverage stored separately (Sec 3.2).
- Our v006 analog of the deterministic failure set: missing final response, unresolved tool call, unrecovered terminal error — all three are DERIVABLE features (see Sec 2 below).

### 1.4 Behavioral distinctions in trace analysis (Sec 5.1 "Agent Trace Analysis")
- Evidence acquisition before planning: untrained 4B "fails to inspect a manager's email containing an updated dependency constraint ... plans from outdated information, produces an invalid schedule"; trained 4B "retrieves the additional evidence, recognizes the updated dependency, recomputes and verifies the schedule" (Sec 5.1, QwenClawBench case). Observable proxy: whether new, content-bearing observations precede plan/artifact-write actions.
- Verification loop as repair input: 4B "stops after a single implementation attempt without establishing an effective testing and repair loop"; 9B "follows a complete edit-test-inspect-repair cycle and repeatedly incorporates execution feedback until the verifier passes" (Sec 5.1, WorkBuddy case). Key sentence: "It also concerns whether the model treats test outcomes as inputs to subsequent decisions and converts a failed attempt into evidence for further repair."
- Strategy adaptation vs repetition: after discovering pandas is unavailable, 4B "repeatedly attempts dependency installation, manual CSV parsing, and local script patching"; 9B "abandons repeated attempts to use the unavailable dependency, and switches to Python's standard csv and mathematical libraries" (Sec 5.1, PinchBench case). Observable proxy: post-error change of tool/command family vs recurrence of the same failing family.
- Interaction-budget efficiency: the adaptive 9B trajectory "reduces the number of model requests, execution time, and token usage by approximately 70.8%, 76.7%, and 83.6%" (Sec 5.1). Efficiency is framed against a budget, not against final length.
- Closing claim (Sec 5.1): the advantage is identifying "unproductive trajectories", revising strategy on environmental feedback, and allocating "a limited interaction budget to actions that directly contribute to task completion" — i.e., exactly stuck-loop, strategy-change, and verification-loop features.

### 1.5 Relevance note for corpus choice (Sec 5.2)
The paper's only head-to-head public-data comparison is against Toucan, "a public synthetic tool-agent dataset" (Sec 5.2, Table 3): routing-harness trajectories beat Toucan by +6.26 avg on five benchmarks. The paper does not claim Toucan carries outcome labels; it is used as matched-budget supervision. This supports, but does not by itself decide, the Toucan screening below.

## 2. Feature derivability table

Verdicts: DERIVABLE = deterministically computable from the event sequence available before the outcome is known. CONDITIONAL = only under a stated dataset/budget condition. NOT-DERIVABLE = needs post-outcome info or LLM judgment.

| # | Feature | Verdict | Extraction rule (one line for DERIVABLE) | Depends on |
|---|---------|---------|------------------------------------------|------------|
| 1 | tool calls / results counts | DERIVABLE | Count assistant tool_call invocations and matched observation events per trajectory. | typed action/observation events |
| 2 | unresolved tool calls | DERIVABLE | Tool-call ids (or expected alternation slots) with no subsequent matching observation, incl. at trajectory end. | tool_call_id pairing (swegym) or role alternation (nebius, agenttrove) |
| 3 | action/observation closure ratio | DERIVABLE | matched_pairs / total_actions from the pairing in #2. | same as #2 |
| 4 | tool diversity | DERIVABLE | distinct(tool name or command head) / total actions. | tool names or command text |
| 5 | tool switching rate | DERIVABLE | adjacent action pairs with different tool/command head / (n_actions - 1). | ordered actions |
| 6 | repeated identical actions | DERIVABLE | Count/max run of consecutive actions with identical normalized signature (tool + canonicalized args). | arg canonicalization |
| 7 | error count/rate | DERIVABLE | Observations matching a high-certainty error pattern library (traceback, nonzero exit, command-not-found, compiler/eval errors) / observations. | readable observation text; per-domain pattern calibration |
| 8 | repeated identical errors | DERIVABLE | Max run of observations with identical normalized error signature (from #7). | #7 signatures |
| 9 | recovery attempts | DERIVABLE | Action event that follows an error-flagged observation before the next error or terminal. | #7 |
| 10 | strategy change after failure | DERIVABLE | Post-error action whose tool/command family differs from the failing family within the next k actions (surface proxy of Sec 5.1 PinchBench). | #7; command-family taxonomy |
| 11 | recovery latency | DERIVABLE | Event count between an error observation and the next observation produced by a non-identical action. | #7, #6 |
| 12 | verification attempts | DERIVABLE | Actions matching test/check/lint/diff/build-verify regexes (pytest, npm test, make check, eslint, diff, ...). | command-bearing actions or verification-named tools |
| 13 | verification after modification | DERIVABLE | Modification-classified action (edit/write/patch) followed within k events by a verification action with no intervening modification (Sec 5.1 edit-test-inspect-repair). | #12, edit-action classifier (tool names/commands) |
| 14 | verification after recovery | DERIVABLE | Verification action occurring after an error observation plus a recovery action. | #9, #12 |
| 15 | evidence acquisition (new info per step) | CONDITIONAL | Only as lexical observation novelty (new distinct lines/content vs all previously seen observation payloads); the semantic sense of Sec 5.1 (retrieving the *relevant* email) is NOT-DERIVABLE without judgment. | readable observation text |
| 16 | interaction depth | DERIVABLE | Total event count (and action count) per trajectory/turn. | event stream |
| 17 | actions without new observations | DERIVABLE | Actions whose resulting observation is empty or exactly duplicates the prior observation payload. | normalized observation payloads |
| 18 | stuck loop length | DERIVABLE | Max k of consecutive identical (action signature -> same error signature) cycles (surface proxy of Sec 5.1 dependency-install repetition). | #6, #8 |
| 19 | prefix position (fraction of events consumed) | CONDITIONAL | Computable only against an exogenous interaction budget (fixed max events/tokens per Sec 5.1's budget framing); fraction of FINAL length is post-outcome info and leaks into the label at training time and is unavailable at live inference. | harness-recorded budget or fixed cap |

Counts: 17 DERIVABLE, 2 CONDITIONAL, 0 NOT-DERIVABLE as specified. Semantic-only variants that are NOT-DERIVABLE (out of the listed set's mechanical scope): semantic evidence relevance (#15), semantic strategy re-planning beyond surface family change (#10), "treats failed test as input to repair" as intent — only the mechanical loop (#13/#14) is observable.

## 3. Dataset screening

Six conditions: (a) parent trajectories identifiable; (b) causal event order recoverable; (c) actions/observations distinguishable; (d) defensible terminal success/settlement label; (e) label does not leak into features; (f) license permits use.

Revision SHAs confirmed via HF API on 2026-09-15 (all three match the values recorded for v005):
- SWE-Gym/OpenHands-Sampled-Trajectories: baf3a4e4bff514d48ddc08a93a2ade5c126212c7
- open-thoughts/AgentTrove: b395a4307a2bc9950a90dc899438f149e115fc60
- nebius/SWE-agent-trajectories: 68195a1450865274106246d0d0296a1d6807b88e

### 3.1 Screening table

| Dataset | Parent id | Causal order | Action/obs distinction | Terminal label | Leak risk | License | VERDICT |
|---|---|---|---|---|---|---|---|
| SWE-Gym/OpenHands-Sampled-Trajectories | instance_id + run_id (schema-verified; run_id disambiguates multiple runs per instance) | messages list ordered; assistant tool_calls[] -> tool-role replies with tool_call_id | role + tool_calls/tool_call_id structure | resolved (bool) cross-checkable against test_result.report.resolved, test_output, error_eval/empty_generation/failed_apply_patch/test_timeout | exclude resolved, test_result.*, git_patch, test_output from features | HF card declares NO license (README frontmatter verified — no license key); companion GitHub repo SWE-Gym/SWE-Gym is Apache-2.0 (LICENSE file verified via GitHub API). Dataset-level license formally UNDETERMINED; Apache-2.0 by inheritance is the defensible reading | ADMIT (existing v005 source); record license provenance in manifest |
| open-thoughts/AgentTrove | run_id (uuid, per row) + episode + original_source; task-level id (`task`) sometimes null (verified on sampled row) | conversations ordered; "New Terminal Output" observation marker verified present in sampled rows; terminus-2 JSON assistant payloads (analysis/plan/commands/task_complete) | assistant turns carry commands/keystrokes JSON; observations embedded in user turns after the marker (README: roles user/assistant/tool) | reward float (README: "Pass/fail outcome ... typically 1.0 or 0.0. Present in most but not all source datasets"); viewer schema also shows result/judgment/verifier_output/ground_truth/task_binary columns; sampled row had result=None | exclude reward/result/judgment/verifier_output/ground_truth; agent-declared `task_complete` inside assistant JSON is NOT a settlement signal | apache-2.0 (HF tags + card verified) | ADMIT (existing v005 source), CONDITIONAL on per-source label filter (keep only rows with non-null outcome field) |
| nebius/SWE-agent-trajectories | instance_id (+model_name separates runs) | verified sampled row: system -> user(issue) -> ai/user alternation, 93 events | role `ai` with mask=True = action; role `user` with mask=False = observation; deterministic, no text parsing needed | target (bool) + exit_status (e.g. "submitted (exit_context)") + eval_logs | exclude target, eval_logs, generated_patch, exit_status from features | cc-by-4.0 (HF tags + card verified) | ADMIT (existing v005 source) |
| Agent-Ark/Toucan-1.5M | uuid per instance (+ prompt_id/row_id in metadata); no parent-task replication | messages is a serialized STRING but parseable; roles system/user/assistant/tool in sample | tool_calls and tool-role messages distinguish actions/observations | NONE. No resolved/target/reward/exit field anywhere in schema (Kimi-K2, OSS, Qwen3, SFT configs all verified). Only question_quality_assessment and response_quality_assessment — LLM-judge annotations of style/completeness, not environment-verified outcomes. Sampled row: an unfinished trajectory (judge notes "has not yet returned any findings") still scored completeness=1 — annotations do not gate success; synthetic SFT assumes completion at synthesis time | response_quality_assessment would leak judge verdicts into features if naively joined | apache-2.0 (verified) | REJECT — condition (d) fails: no verified terminal outcome label; (e) also at risk |
| nvidia/Nemotron-SFT-SWE-v3 (optional candidate; listed in paper References as a HF dataset among public broadening data, Sec 3.1) | uuid per row | not inspected in depth (schema only) | messages list with roles (sampled: OpenHands system prompt) | NONE in released schema: features are exactly [messages, uuid, license] (datasets-server first-rows verified); 237,970 samples, OpenHands/SWE-agent/mini-SWE-agent harnesses per card | n/a | CC-BY-4.0 overall (card; per-row license column, mixed mit/bsd/apache sub-licenses) | REJECT for v006 — no outcome label; revisit only if NVIDIA releases a labeled variant |
| AgentBank (paper References: "50000+ interaction trajectories"; HF: Solaris99/AgentBank) | id per row only | not inspected (schema only) | ShareGPT from/value pairs | NONE in released schema: features are [id, conversations] per config (alfred, alfworld, ...) — no outcome field | n/a | apache-2.0 (HF tags verified) | REJECT for v006 — no outcome label in the public release |

### 3.2 Key evidence URLs inspected
- HF API dataset metadata (sha/tags/cardData/schema) for all six ids above, 2026-09-15.
- https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories/raw/main/README.md (frontmatter: dataset_info + configs only, no license key).
- https://api.github.com/repos/SWE-Gym/SWE-Gym/license (Apache-2.0 LICENSE file, 11,357 bytes).
- https://huggingface.co/datasets/open-thoughts/AgentTrove/raw/main/README.md (schema table incl. reward semantics; 219-source table) and datasets-server first-rows/rows samples (marker + result=null verification).
- datasets-server first-rows/rows samples for nebius/SWE-agent-trajectories, Agent-Ark/Toucan-1.5M (Kimi-K2), nvidia/Nemotron-SFT-SWE-v3.
- Toucan methodology cross-ref: https://arxiv.org/abs/2510.01179 (paper cited as [67] in NeoHorse Sec 5.2).

## 4. Recommended corpus schema implications for v006

Normalized event record (one per reconstructed event; mirrors Sec 3.1 composition and Sec 3.2 reconstruction):
- ids: trajectory_id (= dataset row id), parent_task_id, source (swegym|agenttrove|nebius), run_key.
- event fields: seq; event_type (action | observation | user_request | model_response | terminal); role; tool_name; action_signature (tool + canonicalized args/command); observation_ref (hash + length; full text kept out of feature surface); error_signature (nullable); closed_by (seq of matching observation, nullable — implements Sec 3.2 pair closure).
- label fields stored SEPARATELY from feature fields (Sec 3.2 keeps structural/semantic/routing metadata separate): terminal_label + label_evidence pointer (e.g., test_result.report, target+eval_logs, reward column) + label_source_version (dataset sha).
- validation gates per Sec 3.2, as deterministic quarantines: unreadable payload; missing request/response; out-of-order events; open tool-call/result pair; missing response; orphan observation; duplicate tool-call id; unresolved internal call; ambiguous terminal. Recoverable rows contribute only the causally closed prefix (cut at last closed pair).
- Per-source mapping:
  - swegym: closure via tool_call_id; action_signature from tool_calls[].function.{name,arguments}; parent = instance_id + run_id; label = resolved (+report flags as cross-check).
  - agenttrove: action_signature from assistant JSON commands[].keystrokes (parse; treat task_complete as agent-claim only); observations = user-turn content after "New Terminal Output"; parent = original_source + task + run_id; label = reward/result, rows with null outcome are label-less (usable only for unlabeled pretraining, excluded from classifier training).
  - nebius: action/observation by role ai/user + mask flag; action_signature from the SWE-agent command block in ai text; parent = instance_id + model_name; label = target, cross-check exit_status; eval_logs excluded from features.

## 5. Open questions

1. SWE-Gym dataset-level license is undeclared on HF; is Apache-2.0-by-inheritance (GitHub repo + ICLR paper) acceptable provenance for the v006 manifest, or should we seek confirmation from the authors?
2. AgentTrove: what fraction of rows has a non-null reward/result? Not scanned here (quick screen only); the admissibility threshold ("keep only labeled rows") needs that distribution before ingestion.
3. nebius: should exit_status variants (e.g., "submitted (exit_context)" on target=False rows) gate label admissibility, or is target authoritative in all cases?
4. Prefix-position features need an exogenous interaction budget (Sec 5.1 framing). None of the three datasets records harness budgets — do we fix a per-source cap (documented in HARNESS.md) instead?
5. Should Toucan-1.5M be kept as an unlabeled behavior corpus for future non-classifier work, or dropped entirely from v006 to keep the corpus contract clean?
