from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from scripts.settlement_datasets.adapter_base import read_records_jsonl, write_records_jsonl
from scripts.settlement_datasets.evaluate_policies_shadow import (
    compute_promotion_scores,
    evaluate_policies_shadow,
)
from scripts.settlement_datasets.export_ledger import export_ledger
from scripts.settlement_datasets.ingest_dataset import ingest_dataset
from scripts.settlement_datasets.label_dataset import label_dataset
from scripts.settlement_datasets.live_shadow_policy_eval import replay_records_to_live_shadow
from scripts.settlement_datasets.mine_metabolization_candidates import (
    mine_metabolization_candidates,
)
from scripts.settlement_datasets.mine_policies import mine_policies, write_policies
from scripts.settlement_datasets.profile_dataset import profile_dataset
from scripts.settlement_datasets.replay_policy_evals import (
    compute_replay_summary,
    replay_evals,
)
from scripts.settlement_datasets.run_scoped_paths import (
    add_run_scope_arguments,
    ensure_run_surface,
    load_target_profile,
    utc_now_iso,
    write_run_manifest,
    write_summary_files,
)
from scripts.settlement_datasets.target_profile_filtering import apply_target_profile
from scripts.settlement_datasets.update_metabolization_status import (
    update_metabolization_status,
)
from scripts.settlement_datasets.update_policy_status import update_policy_status


STAGE_ORDER = [
    "ingest",
    "profile",
    "label",
    "export-ledger",
    "mine-policies",
    "shadow-eval",
    "replay",
    "policy-status",
    "metabolization-candidates",
    "metabolization-status",
    "live-shadow",
    "summary",
]


def _should_run(stage: str, start_stage: str, end_stage: str) -> bool:
    return STAGE_ORDER.index(start_stage) <= STAGE_ORDER.index(stage) <= STAGE_ORDER.index(end_stage)


def _confidence_distribution(records: list[dict[str, Any]]) -> dict[str, int]:
    distribution = {"gte_0_8": 0, "gte_0_65": 0, "lt_0_65": 0}
    for record in records:
        confidence = float(record.get("outcome", {}).get("confidence", 0.0) or 0.0)
        if confidence >= 0.8:
            distribution["gte_0_8"] += 1
        elif confidence >= 0.65:
            distribution["gte_0_65"] += 1
        else:
            distribution["lt_0_65"] += 1
    return distribution


def _policy_counts(policies: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(policy.get("status", "unknown") for policy in policies)
    counts["total"] = len(policies)
    return dict(counts)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _target_policy_evidence(
    shadow_results: list[dict[str, Any]],
    target_profile_name: str | None,
) -> dict[str, Any]:
    by_policy = Counter(
        result.get("policy_id", "unknown")
        for result in shadow_results
        if result.get("would_fire")
    )
    return {
        "target_profile": target_profile_name,
        "policy_fire_counts": dict(by_policy),
    }


def _recommended_next_move(summary: dict[str, Any]) -> str:
    harmful = summary["policy_fire_counts"].get("likely_harmful", 0)
    uncertain = summary["policy_fire_counts"].get("uncertain", 0)
    live_shadow = summary["live_shadow_fire_counts"].get("total", 0)
    if harmful:
        return "Review harmful shadow fires before refining trigger conditions or rerunning adjudication."
    if uncertain:
        return "Inspect uncertain shadow results and replay summaries to tighten evidence thresholds without changing policy status."
    if live_shadow:
        return "Inspect live-shadow fire traces to decide whether a narrower target profile is worth the next evidence run."
    return "Populate the run with real traces or rerun from a later stage using --input-run-dir once new evidence is available."


def _target_policy_status(results: list[dict[str, Any]], policy_id: str) -> str:
    fires = [result for result in results if result.get("policy_id") == policy_id and result.get("would_fire")]
    if not fires:
        return "needs_more_evidence"

    harmful = sum(1 for result in fires if result.get("counterfactual_assessment") == "likely_harmful")
    helpful = sum(1 for result in fires if result.get("counterfactual_assessment") == "likely_helpful")
    pre_settlement_with_recovery = sum(
        1
        for result in fires
        if result.get("recovery_opportunity")
        and result.get("fire_timing") in {"early", "middle", "late"}
    )

    if harmful > 0 and helpful == 0:
        return "refine"
    if harmful > 0:
        return "keep_proposed"
    if pre_settlement_with_recovery >= 5:
        return "candidate_for_guarded_experiment"
    if helpful > 0:
        return "keep_proposed"
    return "needs_more_evidence"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run_evidence_pipeline(
    *,
    run_id: str | None,
    dataset: str,
    limit: int | None,
    min_confidence: float,
    input_path: str | None = None,
    run_dir: str | Path | None = None,
    input_run_dir: str | Path | None = None,
    output_run_dir: str | Path | None = None,
    target_profile: str | None = None,
    target_profile_config: str | Path = "configs/settlement_datasets/targeted_trace_queries.yaml",
    start_stage: str = "ingest",
    end_stage: str = "summary",
    eval_dir: str = "data/settlement_datasets/evals/",
    dry_run: bool = False,
    include_live_shadow: bool = True,
) -> dict[str, Path]:
    scope = ensure_run_surface(
        run_id=run_id,
        run_dir=run_dir,
        input_run_dir=input_run_dir,
        output_run_dir=output_run_dir,
    )
    created_at = utc_now_iso()
    target_profile_data = (
        load_target_profile(target_profile, config_path=target_profile_config)
        if target_profile
        else None
    )

    normalized_path = scope.dataset_jsonl_path(
        "normalized",
        dataset,
        input_surface=not _should_run("ingest", start_stage, end_stage),
    )
    settlement_path = scope.dataset_jsonl_path(
        "settlements",
        dataset,
        input_surface=not _should_run("label", start_stage, end_stage),
    )
    policies_path = scope.named_path(
        "policies",
        "policies.yaml",
        input_surface=not _should_run("mine-policies", start_stage, end_stage),
    )
    shadow_dir = scope.stage_dir(
        "shadow",
        input_surface=not _should_run("shadow-eval", start_stage, end_stage),
    )
    replay_dir = scope.stage_dir(
        "replay",
        input_surface=not _should_run("replay", start_stage, end_stage),
    )
    metabolization_dir = scope.stage_dir(
        "metabolization",
        input_surface=not _should_run("metabolization-candidates", start_stage, end_stage),
    )

    commands = [
        {
            "stage": stage,
            "planned": _should_run(stage, start_stage, end_stage),
            "executed": False,
        }
        for stage in STAGE_ORDER
        if stage != "summary"
    ]
    input_paths = {
        "input": input_path,
        "input_run_dir": str(scope.input_root),
        "eval_dir": eval_dir,
    }
    output_paths = {
        "run_dir": str(scope.root),
        "raw": str(scope.dataset_jsonl_path("raw", dataset)),
        "normalized": str(scope.dataset_jsonl_path("normalized", dataset)),
        "profile": str(scope.profile_path(dataset)),
        "settlements": str(scope.dataset_jsonl_path("settlements", dataset)),
        "ledger": str(scope.named_path("ledger", "settlement_ledger.sqlite")),
        "policies": str(scope.named_path("policies", "policies.yaml")),
        "shadow_dir": str(scope.shadow_dir),
        "replay_dir": str(scope.replay_dir),
        "policy_status": str(scope.named_path("adjudication", "policy_status_recommendations.yaml")),
        "candidates": str(scope.named_path("metabolization", "candidates.jsonl")),
        "candidates_updated": str(scope.named_path("metabolization", "candidates_updated.jsonl")),
    }

    artifact_counts = {
        "raw_records": 0,
        "normalized_records": 0,
        "labeled_records": 0,
        "policy_fires": 0,
        "replay_results": 0,
        "live_shadow_fires": 0,
        "metabolization_candidates": 0,
    }
    policy_counts: dict[str, int] = {"total": 0}
    eval_counts = {"shadow_results": 0, "replay_results": 0, "live_shadow_fires": 0}
    target_match_counts: dict[str, Any] = {
        "sampled_count": 0,
        "matched_count": 0,
        "high_confidence_count": 0,
        "signal_counts": {},
        "exclude_reason_counts": {},
    }

    normalized_records: list[dict[str, Any]] = []
    labeled_records: list[dict[str, Any]] = []
    policies: list[dict[str, Any]] = []
    shadow_results: list[dict[str, Any]] = []
    replay_results: list[dict[str, Any]] = []
    replay_summary: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    updated_candidates: list[dict[str, Any]] = []
    live_shadow_fires: list[dict[str, Any]] = []
    target_analysis_artifact: Path | None = None

    if not dry_run:
        if _should_run("ingest", start_stage, end_stage):
            ingest_dataset(
                dataset,
                limit=limit,
                input_path=input_path,
                output_path=str(scope.dataset_jsonl_path("normalized", dataset)),
                raw_output_path=str(scope.dataset_jsonl_path("raw", dataset)),
            )
            for command in commands:
                if command["stage"] == "ingest":
                    command["executed"] = True
                    break

        if normalized_path.exists():
            normalized_records = read_records_jsonl(str(normalized_path))
        target_match_counts["sampled_count"] = len(normalized_records)
        raw_path = scope.dataset_jsonl_path("raw", dataset)
        if raw_path.exists():
            artifact_counts["raw_records"] = len(read_records_jsonl(str(raw_path)))

        if target_profile and normalized_records:
            filtered_records, target_diagnostics = apply_target_profile(
                normalized_records,
                profile_name=target_profile,
                profile=target_profile_data or {},
                min_confidence=min_confidence,
            )
            normalized_records = filtered_records
            write_records_jsonl(normalized_records, str(normalized_path))
            target_analysis_artifact = _write_json(
                scope.named_path("summaries", "target_profile_analysis.json"),
                target_diagnostics,
            )
            target_match_counts = {
                "sampled_count": target_diagnostics["sampled_count"],
                "matched_count": target_diagnostics["matched_count"],
                "high_confidence_count": target_diagnostics["high_confidence_count"],
                "signal_counts": target_diagnostics["signal_counts"],
                "exclude_reason_counts": target_diagnostics["exclude_reason_counts"],
                "qualifying_examples": target_diagnostics["qualifying_examples"],
                "rejected_examples": target_diagnostics["rejected_examples"],
                "targeting_mode": target_diagnostics["targeting_mode"],
                "notes": target_diagnostics["notes"],
            }

        artifact_counts["normalized_records"] = len(normalized_records)

        if _should_run("profile", start_stage, end_stage):
            profile_dataset(dataset, input_path=str(normalized_path), output_dir=str(scope.profiles_dir))
            for command in commands:
                if command["stage"] == "profile":
                    command["executed"] = True
                    break

        if _should_run("label", start_stage, end_stage):
            label_dataset(
                dataset,
                input_path=str(normalized_path),
                output_path=str(scope.dataset_jsonl_path("settlements", dataset)),
                min_confidence=min_confidence,
            )
            for command in commands:
                if command["stage"] == "label":
                    command["executed"] = True
                    break

        if settlement_path.exists():
            labeled_records = read_records_jsonl(str(settlement_path))
        artifact_counts["labeled_records"] = len(labeled_records)

        if _should_run("export-ledger", start_stage, end_stage):
            export_ledger(
                dataset=dataset,
                input_dir=str(scope.settlements_dir),
                output_path=str(scope.named_path("ledger", "settlement_ledger.sqlite")),
            )
            for command in commands:
                if command["stage"] == "export-ledger":
                    command["executed"] = True
                    break

        if _should_run("mine-policies", start_stage, end_stage):
            policies = mine_policies(
                labeled_records,
                min_confidence=min_confidence,
                min_supporting_traces=3,
            )
            write_policies(policies, scope.named_path("policies", "policies.yaml"))
            for command in commands:
                if command["stage"] == "mine-policies":
                    command["executed"] = True
                    break
        elif policies_path.exists():
            with policies_path.open(encoding="utf-8") as handle:
                policies = (yaml.safe_load(handle) or {}).get("policies", [])

        policy_counts = _policy_counts(policies)

        if _should_run("shadow-eval", start_stage, end_stage):
            shadow_results = evaluate_policies_shadow(
                normalized_records,
                policies,
                min_confidence=min_confidence,
                dataset=dataset,
            )
            write_records_jsonl(shadow_results, str(scope.named_path("shadow", "policy_shadow_results.jsonl")))
            scores = compute_promotion_scores(shadow_results, policies)
            write_records_jsonl(scores, str(scope.named_path("shadow", "policy_promotion_scores.jsonl")))
            _write_csv(
                scope.named_path("shadow", "policy_shadow_summary.csv"),
                scores,
                [
                    "policy_id",
                    "supporting_trace_count",
                    "would_fire_count",
                    "likely_helpful_count",
                    "likely_harmful_count",
                    "uncertain_count",
                    "false_positive_rate_estimate",
                    "uncertainty_reason_distribution",
                    "fire_timing_distribution",
                    "recovery_opportunity_count",
                    "helpful_with_recovery_opportunity_count",
                    "uncertain_with_recovery_opportunity_count",
                    "fires_after_failure_settled_count",
                    "payment_risk_distribution",
                    "domains_observed",
                    "datasets_observed",
                    "recommendation",
                    "recommendation_rationale",
                ],
            )
            for command in commands:
                if command["stage"] == "shadow-eval":
                    command["executed"] = True
                    break
        else:
            shadow_results_path = shadow_dir / "policy_shadow_results.jsonl"
            if shadow_results_path.exists():
                shadow_results = read_records_jsonl(str(shadow_results_path))

        artifact_counts["policy_fires"] = sum(1 for result in shadow_results if result.get("would_fire"))
        eval_counts["shadow_results"] = len(shadow_results)

        if _should_run("replay", start_stage, end_stage):
            replay_results = replay_evals(
                policies,
                eval_dir=eval_dir,
                min_confidence=min_confidence,
            )
            write_records_jsonl(replay_results, str(scope.named_path("replay", "eval_replay_results.jsonl")))
            replay_summary = compute_replay_summary(replay_results)
            _write_csv(
                scope.named_path("replay", "eval_replay_summary.csv"),
                replay_summary,
                [
                    "policy_id",
                    "total",
                    "raw_match",
                    "exact_semantic_match",
                    "partial_semantic_match",
                    "mismatch",
                    "unknown_policy_action",
                    "unknown_eval_behavior",
                    "insufficient_evidence",
                    "raw_match_rate",
                    "semantic_match_rate",
                    "partial_match_rate",
                    "unknown_policy_action_count",
                    "unknown_eval_behavior_count",
                    "mismatch_count",
                    "excluded_unknown_count",
                ],
            )
            for command in commands:
                if command["stage"] == "replay":
                    command["executed"] = True
                    break
        else:
            replay_results_path = replay_dir / "eval_replay_results.jsonl"
            if replay_results_path.exists():
                replay_results = read_records_jsonl(str(replay_results_path))

        artifact_counts["replay_results"] = len(replay_results)
        eval_counts["replay_results"] = len(replay_results)

        if _should_run("policy-status", start_stage, end_stage):
            update_policy_status(
                str(scope.named_path("shadow", "policy_shadow_results.jsonl")),
                str(scope.named_path("policies", "policies.yaml")),
                replay_summary_path=str(scope.named_path("replay", "eval_replay_summary.csv")),
                output_path=str(scope.named_path("adjudication", "policy_status_recommendations.yaml")),
            )
            for command in commands:
                if command["stage"] == "policy-status":
                    command["executed"] = True
                    break

        if _should_run("metabolization-candidates", start_stage, end_stage):
            candidates = mine_metabolization_candidates(
                labeled_records,
                min_confidence=min_confidence,
            )
            write_records_jsonl(candidates, str(scope.named_path("metabolization", "candidates.jsonl")))
            for command in commands:
                if command["stage"] == "metabolization-candidates":
                    command["executed"] = True
                    break
        else:
            candidates_path = metabolization_dir / "candidates.jsonl"
            if candidates_path.exists():
                candidates = read_records_jsonl(str(candidates_path))

        artifact_counts["metabolization_candidates"] = len(candidates)

        if _should_run("metabolization-status", start_stage, end_stage):
            updated_path = update_metabolization_status(
                str(scope.named_path("metabolization", "candidates.jsonl")),
                shadow_results_path=str(scope.named_path("shadow", "policy_shadow_results.jsonl")),
                output_path=str(scope.named_path("metabolization", "candidates_updated.jsonl")),
            )
            updated_candidates = read_records_jsonl(str(updated_path))
            for command in commands:
                if command["stage"] == "metabolization-status":
                    command["executed"] = True
                    break
        else:
            updated_candidates_path = metabolization_dir / "candidates_updated.jsonl"
            if updated_candidates_path.exists():
                updated_candidates = read_records_jsonl(str(updated_candidates_path))

        if include_live_shadow and _should_run("live-shadow", start_stage, end_stage):
            live_outputs = replay_records_to_live_shadow(
                labeled_records,
                output_dir=scope.shadow_dir / "live_shadow",
                enabled=True,
            )
            live_shadow_fires = read_records_jsonl(str(live_outputs["policy_fires"]))
            for command in commands:
                if command["stage"] == "live-shadow":
                    command["executed"] = True
                    break
        elif include_live_shadow:
            live_fires_path = scope.shadow_dir / "live_shadow" / "policy_fires.jsonl"
            if live_fires_path.exists():
                live_shadow_fires = read_records_jsonl(str(live_fires_path))

        artifact_counts["live_shadow_fires"] = len(live_shadow_fires)
        eval_counts["live_shadow_fires"] = len(live_shadow_fires)

    updated_candidate_records = updated_candidates or candidates
    harmful_count = sum(1 for result in shadow_results if result.get("counterfactual_assessment") == "likely_harmful")
    uncertain_count = sum(1 for result in shadow_results if result.get("counterfactual_assessment") == "uncertain")
    helpful_count = sum(1 for result in shadow_results if result.get("counterfactual_assessment") == "likely_helpful")
    live_shadow_by_policy = Counter(fire.get("policy_id", "unknown") for fire in live_shadow_fires)
    candidate_status_counts = Counter(
        record.get("metabolization_status", "candidate") for record in updated_candidate_records
    )
    reflection_policy_id = "require_reflection_before_continuing_after_second_unresolved_error"
    reflection_results = [
        result
        for result in shadow_results
        if result.get("policy_id") == reflection_policy_id
    ]
    reflection_fires = [result for result in reflection_results if result.get("would_fire")]

    summary = {
        "run_id": scope.run_id,
        "created_at": created_at,
        "dataset": dataset,
        "min_confidence": min_confidence,
        "target_profile": target_profile,
        "target_profile_metadata": target_profile_data,
        "trace_counts": {
            "ingested": artifact_counts["raw_records"],
            "normalized": artifact_counts["normalized_records"],
            "labeled": artifact_counts["labeled_records"],
        },
        "target_profile_match_counts": target_match_counts,
        "confidence_distribution": _confidence_distribution(labeled_records or normalized_records),
        "policy_fire_counts": {
            "total": artifact_counts["policy_fires"],
            "likely_helpful": helpful_count,
            "likely_harmful": harmful_count,
            "uncertain": uncertain_count,
        },
        "target_policy_evidence": _target_policy_evidence(shadow_results, target_profile),
        "reflection_policy_evidence": {
            "policy_id": reflection_policy_id,
            "would_fire_count": len(reflection_fires),
            "fire_timing_distribution": dict(Counter(result.get("fire_timing", "unknown") for result in reflection_fires)),
            "recovery_opportunity_count": sum(1 for result in reflection_fires if result.get("recovery_opportunity")),
            "assessment_distribution": dict(Counter(result.get("counterfactual_assessment", "unknown") for result in reflection_fires)),
            "pre_settlement_fire_count": sum(1 for result in reflection_fires if result.get("fire_timing") in {"early", "middle", "late"}),
            "status_recommendation": _target_policy_status(shadow_results, reflection_policy_id),
        },
        "false_positive_count": harmful_count,
        "harmful_count": harmful_count,
        "uncertain_count": uncertain_count,
        "live_shadow_fire_counts": {
            "total": len(live_shadow_fires),
            "by_policy": dict(live_shadow_by_policy),
        },
        "metabolization_candidate_status_counts": dict(candidate_status_counts),
        "policy_activation_count": 0,
        "recommended_next_move": "Populate the run with real traces or rerun from a later stage using --input-run-dir once new evidence is available."
        if dry_run
        else _recommended_next_move(
            {
                "policy_fire_counts": {
                    "likely_harmful": harmful_count,
                    "uncertain": uncertain_count,
                },
                "live_shadow_fire_counts": {"total": len(live_shadow_fires)},
            }
        ),
    }

    manifest = {
        "run_id": scope.run_id,
        "created_at": created_at,
        "commands": commands,
        "datasets": [dataset],
        "limits": {"limit": limit, "start_stage": start_stage, "end_stage": end_stage},
        "min_confidence": min_confidence,
        "input_paths": input_paths,
        "output_paths": output_paths,
        "artifact_counts": artifact_counts,
        "policy_counts": policy_counts,
        "eval_counts": eval_counts,
        "target_profile": target_profile,
        "target_profile_analysis": str(target_analysis_artifact) if target_analysis_artifact is not None else None,
        "test_status": None,
    }

    manifest_path = write_run_manifest(scope, manifest)
    summary_paths = write_summary_files(scope, summary)
    return {
        "manifest": manifest_path,
        **summary_paths,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the settlement dataset evidence workflow into a run-scoped surface")
    parser.add_argument("--dataset", required=True, choices=["agenttrove", "swegym", "apibank", "webshop"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--input", default=None)
    parser.add_argument("--min-confidence", type=float, default=0.65)
    parser.add_argument("--start-stage", choices=STAGE_ORDER[:-1], default="ingest")
    parser.add_argument("--end-stage", choices=STAGE_ORDER, default="summary")
    parser.add_argument("--eval-dir", default="data/settlement_datasets/evals/")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-live-shadow", action="store_true")
    parser.add_argument(
        "--enable-live-shadow-replay",
        action="store_true",
        help="Explicitly enable live shadow replay. This is already the default unless --skip-live-shadow is set.",
    )
    add_run_scope_arguments(parser, include_target_profile=True)
    args = parser.parse_args()

    results = run_evidence_pipeline(
        run_id=args.run_id,
        dataset=args.dataset,
        limit=args.limit,
        min_confidence=args.min_confidence,
        input_path=args.input,
        run_dir=args.run_dir,
        input_run_dir=args.input_run_dir,
        output_run_dir=args.output_run_dir,
        target_profile=args.target_profile,
        target_profile_config=args.target_profile_config,
        start_stage=args.start_stage,
        end_stage=args.end_stage,
        eval_dir=args.eval_dir,
        dry_run=args.dry_run,
        include_live_shadow=args.enable_live_shadow_replay or not args.skip_live_shadow,
    )

    print(f"Wrote run manifest -> {results['manifest']}")
    print(f"Wrote run summary -> {results['summary_json']}")
    print(f"Wrote markdown summary -> {results['summary_md']}")


if __name__ == "__main__":
    main()
