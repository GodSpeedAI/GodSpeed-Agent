# v008 Fourth-Source Research (V1b, plan godspeed-agent-v008-r1-transfer)

Date: 2026-09-16. Bounded effort (~30 min of querying). Goal: a FOURTH public
agent-trajectory dataset admissible for the R1 transfer experiment, applying
the SAME six conditions as v007 (`.agents/reports/v007-dataset-research.md`):

1. stable parent identity;
2. real execution trajectory (ordered actions + observations with role semantics);
3. genuine failure/recovery events observable MID-trajectory;
4. defensible terminal outcome (execution-derived, not judge/synthesis);
5. compatible license;
6. causally reconstructable R1 state.

Already REJECTED in v007/v006 (not re-screened): Toucan-1.5M, AgentTrove,
SWE-Gym/SWE-Gym, R2E-Gym SFT + Verifier sets, Nemotron-SFT-SWE-v3, AgentBank.
Already ADMITTED (not candidates): SWE-Gym/OpenHands-Sampled-Trajectories,
nebius/SWE-agent-trajectories, SWE-bench/SWE-smith-trajectories.

Method: HF API org listings (`/api/datasets?author=...` for SWE-bench,
SWE-Gym, openhands, nebius), dataset metadata (`/api/datasets/<id>`), README
frontmatter/cards, datasets-server `/first-rows`, `/rows` (≤20 rows per call),
`/splits`. No large streaming.

## Org-scan breadth (not separately screened — no trajectory content or subsumed)

- `SWE-bench` org: SWE-bench_Verified/Lite/Multimodal/Multilingual, SWE-bench,
  SWE-bench_Not_Verified, SWE-prime, and SWE-smith-{py,go,php,java,js,rs,ts,cpp}
  — task-instance sets (instance + patch + test metadata), not trajectory
  sets. SWE-bench/SWE-smith-trajectories (admitted v007) is the only
  trajectory set in the org.
- `nebius` org: SWE-rebench, SWE-rebench-V2, SWE-rebench-V2-PRs,
  SWE-rebench-leaderboard, SWE-bench-extra — instance/leaderboard sets;
  SWE-agent-trajectories (admitted v007).
- `SWE-Gym` org: OpenHands-Sampled-Trajectories (admitted v006);
  SWE-Gym-Lite/Raw/Codebase-Index-Lite — instance sets; the remaining three
  trajectory sets screened below.
- `openhands` org: no datasets listed via the API.

## Screening table

| # | Candidate | Revision | License | Outcome field | Failure/recovery mid-trajectory | Verdict (one-line evidence) |
|---|---|---|---|---|---|---|
| 1 | **nebius/SWE-rebench-openhands-trajectories** | `35455389ab51bf5e2306bfd436ef72d0f98bf882` (API) | **cc-by-4.0** (README frontmatter line 1; API cardData) | `resolved` int64 0/1 + `exit_status` str; 67,074 rows; sample of 20: 7×0 / 13×1 | YES: first `resolved=0` row (185 msgs) has 32 tool-role keyword hits, each followed by assistant+tool continuation | **ADMIT** (conditional — see caveats) |
| 2 | Kwai-Klear/SWE-smith-mini_swe_agent_plus-trajectories-66k | `750b2c11239fd5e32f97e6cfb9bf80fb9a9a2983` | mit | **NONE**: first-rows features = `instance_id`, `messages` only | n/a — no outcome to condition on | **REJECT**: no outcome field in schema (condition 4 fails) AND success-only by construction — nebius rebench card Table 1 reports Successful 65,994 / Total 65,994 |
| 3 | SWE-Gym/MoatlessTools-Sampled-Trajectories | `51ba9a7f38fed087bcb1a11b3d51972ed72a8317` | **absent** (API null, no card tags) | none queryable | n/a | **REJECT**: data shipped as raw `.zip` fp8 experiment archives (siblings listing), no documented row schema, no license |
| 4 | SWE-Gym/OpenHands-SFT-Trajectories | `4aaa5a4a4b5861f4799d2336908760c190ac3b17` | mit | **NONE**: first-rows (config `default`, split `train.success.oss`) = `messages` only, 491 rows | n/a — success-filtered by construction (split literally named `train.success.oss`; 491 = the success count of OpenHands-Sampled-Trajectories per nebius Table 1) | **REJECT**: degenerate labels; no instance/outcome IDs; subsumed by an already-admitted source |
| 5 | SWE-Gym/OpenHands-Verifier-Trajectories | `d47f6cab996d3a5f7ba517c0be57595f4f6201ce` | **absent** | `resolved` bool on judge conversations | n/a | **REJECT**: first-rows message[0] = "You are an expert judge evaluating AI assistant interactions..." — verifier/teacher-forcing pattern, not an agent trajectory (same ground as R2E-Gym Verifier REJECT in v007) |

## Candidate 1 — nebius/SWE-rebench-openhands-trajectories: ADMIT (conditional)

### Six-condition check

| Condition | Evidence |
|---|---|
| 1. Stable parent identity | `trajectory_id` (documented "identifier unique for each collected trajectory"), plus `instance_id` (GitHub issue id, joinable to nebius/SWE-rebench Docker images) and `repo`. Card field table ("Dataset Structure"). |
| 2. Real execution trajectory | Complete OpenHands v0.54.0 conversation with roles `system`/`assistant` (with `tool_calls`)/`user`/`tool` (environment observations) — card "Dataset Summary" + first-rows role sequence `system, user, assistant, tool, assistant, tool, ...` (185 msgs in the inspected row). |
| 3. Genuine failure/recovery mid-trajectory | First `resolved=0` row: 32 tool-role keyword hits (`error|fail|traceback|exception|assertionerror`) each followed by assistant + tool messages; 34,913 of 67,074 trajectories are `resolved=0` per card statistics (32,161 successful / 67,074 total). Sample of 20 rows: 7 unresolved / 13 resolved across 20 distinct instance_ids. |
| 4. Defensible terminal outcome | `resolved` = "Binary indicator of task success: 1 if the agent solved the issue, 0 otherwise" (card field table). Base dataset nebius/SWE-rebench carries `FAIL_TO_PASS`/`PASS_TO_PASS`/`test_cmd` per instance and is "validated for correctness through automated environment setup and test execution" (SWE-rebench card; paper arXiv 2505.20411, SWE-bench-style execution eval). `exit_status` distinguishes submit vs agent error. `model_patch`/`gen_tests_correct`/`pred_passes_gen_tests` are label-side only. |
| 5. Compatible license | cc-by-4.0 (README frontmatter + API tags) — same as the admitted nebius source. |
| 6. Causally reconstructable R1 state | Ordered role-tagged message list with tool_call structure and a `tools` manifest; deterministic adapter mapping is the same shape as the existing OpenHands-family adapter. |

### Caveats (ingestion-time obligations; none lowering the bar)

- **Label mechanism re-verify**: the trajectories card states WHAT `resolved`
  means but not HOW it was computed; the execution derivation is documented on
  the base SWE-rebench card/paper. At ingestion, spot-verify `resolved`
  against `exit_status` and against the SWE-rebench eval description; record
  provenance in the corpus manifest like v007 did. UNDETERMINED until done.
- **Role semantics repeat the Part-1 findings** (`.agents/reports/v008-adapter-semantics.md`):
  (a) the card says observations arrive in BOTH `user` and `tool` roles —
  check for a leading user-role task/issue message (the nebius-source F3
  failure mode) and decide context vs observation before building episodes;
  (b) render `tool_calls[].function.{name,arguments}` into action content
  (swegym-source F2 lesson) or `cmd_family`/`mentions_bash` will be
  prose-only; note the card's warning that `arguments` is string-serialized;
  (c) `tools` manifest is present → `tool_names_manifest` populated, which
  actually makes `tool_diversity_count` comparable with swegym (both OpenHands
  harnesses), not with nebius/swe_smith.
- Single scaffolding (OpenHands v0.54.0) and single model (Qwen3-Coder-480B-A35B-Instruct)
  — fine for transfer (cohort is also near-single-model) but record it.
- Real-world GitHub issues (1,823 repos per card) vs swe_smith's synthetic
  faults and swegym's 11 repos: domain-provenance column required (v007-dsr
  caveat tradition).
- Revision pin: `35455389ab51bf5e2306bfd436ef72d0f98bf882` at screen time.

## Verdict

**One admissible fourth source exists: `nebius/SWE-rebench-openhands-trajectories`**
(cc-by-4.0, 67,074 trajectories, 48% resolved, execution-derived labels,
complete ordered OpenAI-format trajectories with tool manifest). The other
four screened candidates fail on outcome structure (2), deliverability (3),
label degeneracy (4), or trajectory-ness (5). No standards were lowered; the
single conditional obligation is the ingestion-time re-verification of the
`resolved` mechanism plus the two adapter-semantics precautions carried over
from the Part-1 audit.
