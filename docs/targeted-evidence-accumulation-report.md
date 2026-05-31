# Targeted Evidence Accumulation Report

## Commands Run

```bash
export HF_DATASETS_DISABLE_PROGRESS_BARS=1 PYTHONUNBUFFERED=1 && PYTHONPATH=. uv run python -u - <<'PY'
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from datasets import load_dataset

from scripts.agenttrove.ingest_agenttrove import extract_metadata, find_trace_key, make_trace_id, normalize_turn

TARGET_SOURCES = {
    'code_contests': 100,
    'codeforces': 100,
    'freelancer': 100,
    'nl2bash': 100,
    'staqc': 100,
}

output_path = Path('data/settlement_datasets/evidence_accumulation_run/raw_samples/agenttrove.jsonl')
output_path.parent.mkdir(parents=True, exist_ok=True)

existing_ids = set()
for existing_path in [
    Path('data/agenttrove/raw_samples/sample.jsonl'),
    Path('data/settlement_datasets/raw_samples/agenttrove.jsonl'),
]:
    if existing_path.exists():
        with existing_path.open('r', encoding='utf-8') as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                trace_id = record.get('trace_id') or record.get('task_id')
                if trace_id:
                    existing_ids.add(trace_id)

counts = Counter()
teacher_counts = Counter()
selected = []
stream = load_dataset('open-thoughts/AgentTrove', split='train', streaming=True)
for index, row in enumerate(stream, start=1):
    source = row.get('original_source') or ''
    if source not in TARGET_SOURCES:
        continue
    if counts[source] >= TARGET_SOURCES[source]:
        if all(counts[s] >= TARGET_SOURCES[s] for s in TARGET_SOURCES):
            break
        continue
    try:
        trace_key = find_trace_key(row)
    except KeyError:
        continue
    raw_messages = row.get(trace_key)
    if not isinstance(raw_messages, list):
        continue
    trace_id = make_trace_id(row, index)
    if trace_id in existing_ids:
        continue
    metadata = extract_metadata(row)
    normalized = [normalize_turn(turn) for turn in raw_messages]
    selected.append({
        'trace_id': trace_id,
        'source': source,
        'teacher': metadata.get('original_teacher', ''),
        'task_id': metadata.get('task_id', metadata.get('task', '')),
        'reward': row.get('reward'),
        'metadata': metadata,
        'messages': normalized,
    })
    counts[source] += 1
    teacher_counts[metadata.get('original_teacher') or 'unknown'] += 1
    existing_ids.add(trace_id)
    if all(counts[s] >= TARGET_SOURCES[s] for s in TARGET_SOURCES):
        break

with output_path.open('w', encoding='utf-8') as handle:
    for record in selected:
        handle.write(json.dumps(record, sort_keys=True) + '\n')

print('final_selected', len(selected), flush=True)
print('final_sources', dict(counts), flush=True)
print('final_teachers', dict(teacher_counts), flush=True)
print('output', output_path, flush=True)
PY

export PYTHONUNBUFFERED=1 && PYTHONPATH=. uv run python -u - <<'PY'
from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from pathlib import Path

from scripts.settlement_datasets.adapter_base import read_records_jsonl, write_records_jsonl
from scripts.settlement_datasets.ingest_dataset import ingest_dataset
from scripts.settlement_datasets.profile_dataset import profile_dataset
from scripts.settlement_datasets.label_dataset import label_dataset
from scripts.settlement_datasets.export_ledger import export_ledger
from scripts.settlement_datasets.mine_policies import mine_policies, write_policies
from scripts.settlement_datasets.evaluate_policies_shadow import evaluate_policies_shadow, compute_promotion_scores
from scripts.settlement_datasets.replay_policy_evals import replay_evals, compute_replay_summary
from scripts.settlement_datasets.update_policy_status import update_policy_status
from scripts.settlement_datasets.mine_metabolization_candidates import mine_metabolization_candidates
from scripts.settlement_datasets.update_metabolization_status import update_metabolization_status
from scripts.settlement_datasets.registry import available_datasets

run_root = Path('data/settlement_datasets/evidence_accumulation_run')
for child in ['raw_samples', 'normalized', 'profiles', 'settlements', 'policy_shadow_eval', 'metabolization_candidates', 'policies_review']:
    (run_root / child).mkdir(parents=True, exist_ok=True)

source_paths = [
    Path('data/agenttrove/raw_samples/sample.jsonl'),
    run_root / 'raw_samples' / 'agenttrove.jsonl',
]
merged = []
seen = set()
for path in source_paths:
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            trace_id = record.get('trace_id') or record.get('task_id')
            if trace_id in seen:
                continue
            seen.add(trace_id)
            merged.append(record)
expanded_raw = run_root / 'raw_samples' / 'agenttrove_expanded.jsonl'
with expanded_raw.open('w', encoding='utf-8') as handle:
    for record in merged:
        handle.write(json.dumps(record, sort_keys=True) + '\n')

normalized_path = ingest_dataset(
    'agenttrove',
    input_path=str(expanded_raw),
    output_path=str(run_root / 'normalized' / 'agenttrove.jsonl'),
)
profile_dataset(
    'agenttrove',
    input_path=str(normalized_path),
    output_dir=str(run_root / 'profiles'),
)
settlement_path = label_dataset(
    'agenttrove',
    input_path=str(normalized_path),
    output_path=str(run_root / 'settlements' / 'agenttrove.jsonl'),
    min_confidence=0.65,
)

for ds in ('swegym', 'apibank', 'webshop'):
    shutil.copy2(
        Path(f'data/settlement_datasets/settlements/{ds}.jsonl'),
        run_root / 'settlements' / f'{ds}.jsonl',
    )

export_ledger(
    dataset='all',
    input_dir=str(run_root / 'settlements'),
    output_path=str(run_root / 'settlement_ledger.sqlite'),
)

all_records = []
for ds in available_datasets():
    path = run_root / 'settlements' / f'{ds}.jsonl'
    if path.exists():
        all_records.extend(read_records_jsonl(str(path)))

policies = mine_policies(all_records, min_confidence=0.65, min_supporting_traces=3)
policies_path = write_policies(policies, run_root / 'policies.yaml')

shadow_results = evaluate_policies_shadow(all_records, policies, min_confidence=0.65)
shadow_results_path = run_root / 'policy_shadow_eval' / 'policy_shadow_results.jsonl'
write_records_jsonl(shadow_results, str(shadow_results_path))
scores = compute_promotion_scores(shadow_results, policies)
write_records_jsonl(scores, str(run_root / 'policy_shadow_eval' / 'policy_promotion_scores.jsonl'))
with (run_root / 'policy_shadow_eval' / 'policy_shadow_summary.csv').open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=[
        'policy_id', 'supporting_trace_count', 'would_fire_count', 'likely_helpful_count',
        'likely_harmful_count', 'uncertain_count', 'false_positive_rate_estimate',
        'payment_risk_distribution', 'domains_observed', 'datasets_observed',
        'recommendation', 'recommendation_rationale',
    ])
    writer.writeheader()
    for row in scores:
        writer.writerow(row)

replay_results = replay_evals(policies, eval_dir='data/settlement_datasets/evals/', min_confidence=0.0)
write_records_jsonl(replay_results, str(run_root / 'policy_shadow_eval' / 'eval_replay_results.jsonl'))
replay_summary = compute_replay_summary(replay_results)
with (run_root / 'policy_shadow_eval' / 'eval_replay_summary.csv').open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=[
        'policy_id', 'total', 'raw_match', 'exact_semantic_match', 'partial_semantic_match',
        'mismatch', 'unknown_policy_action', 'unknown_eval_behavior', 'insufficient_evidence',
        'raw_match_rate', 'semantic_match_rate', 'partial_match_rate', 'unknown_policy_action_count',
        'unknown_eval_behavior_count', 'mismatch_count', 'excluded_unknown_count',
    ])
    writer.writeheader()
    for row in replay_summary:
        writer.writerow(row)

update_policy_status(
    str(shadow_results_path),
    str(policies_path),
    replay_summary_path=str(run_root / 'policy_shadow_eval' / 'eval_replay_summary.csv'),
    output_path=str(run_root / 'policies_review' / 'policy_status_recommendations.yaml'),
)

candidates = mine_metabolization_candidates(all_records, min_confidence=0.65)
candidates_path = run_root / 'metabolization_candidates' / 'candidates.jsonl'
write_records_jsonl(candidates, str(candidates_path))
update_metabolization_status(
    str(candidates_path),
    shadow_results_path=str(shadow_results_path),
    output_path=str(run_root / 'metabolization_candidates' / 'candidates_updated.jsonl'),
)

manifest = {
    'expanded_agenttrove_trace_count': len(merged),
    'expanded_agenttrove_source_distribution': dict(Counter(r.get('source') or r.get('metadata', {}).get('original_source', 'unknown') for r in merged)),
    'expanded_agenttrove_teacher_distribution': dict(Counter(r.get('teacher') or r.get('metadata', {}).get('original_teacher', 'unknown') for r in merged)),
    'labeled_agenttrove_record_count': len(read_records_jsonl(str(settlement_path))),
    'policy_count': len(policies),
    'shadow_result_count': len(shadow_results),
    'replay_result_count': len(replay_results),
    'candidate_count': len(candidates),
}
(run_root / 'run_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')
PY

export PYTHONUNBUFFERED=1 && PYTHONPATH=. uv run python -u - <<'PY'
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.agenttrove.parsing import detect_task_complete, parse_assistant_content
from scripts.agenttrove.profile_traces import profile_trace
from scripts.settlement_datasets.adapter_base import read_records_jsonl

run_root = Path('data/settlement_datasets/evidence_accumulation_run')
raw_path = run_root / 'raw_samples' / 'agenttrove_expanded.jsonl'
normalized_path = run_root / 'normalized' / 'agenttrove.jsonl'
settlement_path = run_root / 'settlements' / 'agenttrove.jsonl'

raw_records = []
with raw_path.open('r', encoding='utf-8') as handle:
    for line in handle:
        if line.strip():
            raw_records.append(json.loads(line))

normalized_records = read_records_jsonl(str(normalized_path))
settled_records = read_records_jsonl(str(settlement_path))

source_counts = Counter(record.get('source') or record.get('metadata', {}).get('original_source', 'unknown') for record in raw_records)
teacher_counts = Counter(record.get('teacher') or record.get('metadata', {}).get('original_teacher', 'unknown') for record in raw_records)

command_count = 0
error_count = 0
parse_failure_turns = 0
parse_failure_traces = 0
task_complete_true = 0
task_complete_present = 0
null_reward_count = 0
for record in raw_records:
    messages = record.get('messages', [])
    profile = profile_trace(record)
    command_count += profile.get('command_like_action_count', 0)
    error_count += profile.get('error_like_output_count', 0)
    if record.get('reward') is None:
        null_reward_count += 1
    task_complete = detect_task_complete(messages)
    if task_complete.get('has_marker'):
        task_complete_present += 1
    if task_complete.get('value') is True:
        task_complete_true += 1
    trace_failed = False
    for message in messages:
        if message.get('role') != 'assistant':
            continue
        parsed = parse_assistant_content(message.get('content', ''))
        if not parsed.get('parsed'):
            parse_failure_turns += 1
            trace_failed = True
    if trace_failed:
        parse_failure_traces += 1

summary = {
    'requested_additional_traces': 500,
    'processed_additional_traces': 500,
    'expanded_total_traces': len(raw_records),
    'normalized_record_count': len(normalized_records),
    'labeled_record_count': len(settled_records),
    'source_distribution': dict(source_counts),
    'teacher_distribution': dict(teacher_counts),
    'task_complete_true_count': task_complete_true,
    'task_complete_marker_count': task_complete_present,
    'command_count': command_count,
    'error_count': error_count,
    'null_reward_count': null_reward_count,
    'parse_failure_turn_count': parse_failure_turns,
    'parse_failure_trace_count': parse_failure_traces,
    'unknown_label_count': sum(1 for record in settled_records if record.get('labels', {}).get('failure_mode') == 'unknown'),
}
(run_root / 'sample_profile_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True), encoding='utf-8')
print(json.dumps(summary, indent=2, sort_keys=True))
PY
```

## Dataset Sample Profile

- Requested additional traces: `500`
- Successfully processed additional traces: `500`
- Expanded total real AgentTrove traces used for this pass: `600`
- Normalized records: `600`
- Labeled records at `--min-confidence 0.65`: `321`
- Source distribution in expanded run: `code_contests=120`, `codeforces=120`, `freelancer=120`, `nl2bash=120`, `staqc=120`
- Teacher distribution in expanded run: `GPT 5.1 Nano=360`, `GPT-5-mini=120`, `GLM-4.6=120`
- `task_complete` markers present: `595`
- `task_complete: true` count: `231`
- Command count: `15,431`
- Error count: `868`
- Null reward count: `600`
- Parse failures: `650` assistant turns across `208` traces
- Unknown label count: `264`

Interpretation notes:

- The parse-failure counts above are assistant-turn JSON parse fallbacks, not ingestion failures. All `600` traces normalized successfully.
- AgentTrove still provides null rewards across this expanded real-data slice, so settlement evidence remains structural and feedback-based rather than reward-based.

## Policy Evidence Update

### Target Policies

| Policy                                     | Prior Support         | New Support            | Prior Would Fire | New Would Fire | Prior Helpful | New Helpful | Prior Harmful | New Harmful | Prior Uncertain | New Uncertain | Prior FP | New FP | Prior Confidence           | New Confidence              | Semantic Replay                               | Recommendation  |
| ------------------------------------------ | --------------------- | ---------------------- | ---------------- | -------------- | ------------- | ----------- | ------------- | ----------- | --------------- | ------------- | -------- | ------ | -------------------------- | --------------------------- | --------------------------------------------- | --------------- |
| `require_reflection_after_repeated_errors` | `2` supporting traces | `31` supporting traces | `1`              | `2`            | `0`           | `0`         | `0`           | `0`         | `1`             | `2`           | `0.0%`   | `0.0%` | `0.85 / min=max=0.85`      | `0.80 / min=max=0.80`       | `semantic=33.3%`, `partial=66.7%`, `raw=0.0%` | `keep_proposed` |
| `require_explicit_settlement_for_failure`  | `3` supporting traces | `8` supporting traces  | `5`              | `3`            | `2`           | `2`         | `0`           | `0`         | `3`             | `1`           | `0.0%`   | `0.0%` | `0.75 / min=0.70 max=0.85` | `0.775 / min=0.70 max=0.80` | `semantic=0.0%`, `partial=0.0%`, `raw=0.0%`   | `keep_proposed` |

Target-policy interpretation:

- `require_reflection_after_repeated_errors` gained much broader mined support (`2` to `31` traces), but shadow-mode evidence did not strengthen in the same direction. It still produced no likely-helpful fires, no harmful fires, and only uncertain fires. This makes it less compelling as an activation candidate than the larger support count alone might suggest.
- `require_explicit_settlement_for_failure` remains the stronger of the two target policies. Its mined support increased (`3` to `8` traces), and it retained `2` likely-helpful fires with `0` harmful fires. However, it still did not reach the activation helpful-count threshold, so the recommendation remains `keep_proposed`.

### Other Policies in the Run-Scoped Pass

| Policy                                                 | New Would Fire | Helpful | Harmful | Uncertain | FP     | Recommendation  |
| ------------------------------------------------------ | -------------- | ------- | ------- | --------- | ------ | --------------- |
| `prevent_high_payment_action_when_constraints_unknown` | `46`           | `0`     | `0`     | `46`      | `0.0%` | `keep_proposed` |
| `compare_constraints_before_selection`                 | `0`            | `0`     | `0`     | `0`       | `0.0%` | `superseded`    |
| `test_before_final_answer`                             | `0`            | `0`     | `0`     | `0`       | `0.0%` | `superseded`    |
| `prevent_premature_concretion`                         | `0`            | `0`     | `0`     | `0`       | `0.0%` | `superseded`    |

Secondary observation:

- The larger AgentTrove slice mostly increased uncertain support around `prevent_high_payment_action_when_constraints_unknown` rather than producing new clearly helpful evidence for the two target policies.

## Activation Gate Check

Activation rule checked for each promising target policy:

- `likely_helpful_count >= 5`
- `likely_harmful_count == 0`
- `false_positive_rate_estimate <= 10%`
- multi-dataset evidence present unless domain-specific exception applies

| Policy                                     | Helpful >= 5 | Harmful == 0 | FP <= 10%     | Multi-dataset Evidence        | Gate Result  |
| ------------------------------------------ | ------------ | ------------ | ------------- | ----------------------------- | ------------ |
| `require_reflection_after_repeated_errors` | Fail (`0`)   | Pass (`0`)   | Pass (`0.0%`) | Pass (`agenttrove`, `swegym`) | Not eligible |
| `require_explicit_settlement_for_failure`  | Fail (`2`)   | Pass (`0`)   | Pass (`0.0%`) | Pass (`apibank`, `swegym`)    | Not eligible |

Neither target policy cleared the activation gate. No policy was activated.

## Metabolization Update

- Updated metabolization candidates: `7`
- Statuses after this pass: all `7` remained `repeated`
- `tested` count: `0`
- `metabolized` count: `0`

This pass accumulated real settlement evidence only. It did not create live-harness evidence and did not mark any candidate as metabolized.

## Outcome

- The evidence accumulation pass succeeded in adding `500` additional real AgentTrove traces while preserving the five-source profile required for the run.
- The expanded run materially increased mined support for both target policies, but the shadow-evaluation surface still did not justify promotion.
- `require_explicit_settlement_for_failure` remains the more promising target because it preserved `2` likely-helpful fires with `0` harmful fires, but it still falls short of the helpful-count threshold.
- `require_reflection_after_repeated_errors` remains evidence-backed as a proposed policy, but the additional real traces did not convert it into a likely-helpful candidate.
- Semantic replay stayed calibration-only evidence. It informed interpretation, but it did not promote any status on its own.
