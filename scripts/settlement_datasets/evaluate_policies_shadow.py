from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)
from scripts.settlement_datasets.registry import available_datasets


def _check_trigger(
    trigger: dict[str, Any], record: dict[str, Any]
) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    payment = record.get("payment", {})
    labels = record.get("labels", {})
    outcome = record.get("outcome", {})
    actions = record.get("affordance_path", {}).get("actions", [])
    domain = record.get("domain", "")

    if "error_count_gte" in trigger:
        threshold = trigger["error_count_gte"]
        actual = payment.get("error_count", 0)
        if actual >= threshold:
            evidence.append(f"error_count={actual}>={threshold}")
        else:
            return False, []

    if "action_type" in trigger:
        at = trigger["action_type"]
        if at == "edit_or_api_call":
            has_edit = any(
                a.get("action_type") in ("command", "api_call") for a in actions
            )
            has_prior_search = any(
                a.get("action_type") in ("analysis", "search")
                for i, a in enumerate(actions)
                if any(
                    a2.get("action_type") in ("command", "api_call")
                    for a2 in actions[i + 1 :]
                )
            )
            if (
                has_edit
                and trigger.get("prior_search") is False
                and not has_prior_search
            ):
                evidence.append(f"has_{at}_without_prior_search")
            elif has_edit:
                return False, []
            else:
                return False, []

    if "selection_action" in trigger:
        has_selection = any(
            a.get("action_type") in ("buy", "selection") for a in actions
        )
        if has_selection and trigger.get("prior_comparison") is False:
            has_prior_compare = any(
                a.get("action_type") == "analysis"
                for a in actions[: max(1, len(actions) - 1)]
            )
            if not has_prior_compare:
                evidence.append("selection_without_prior_comparison")
            else:
                return False, []
        else:
            return False, []

    if "api_call" in trigger:
        has_api = any(a.get("action_type") == "api_call" for a in actions)
        if has_api and trigger.get("prior_schema_check") is False:
            has_prior_analysis = any(
                a.get("action_type") == "analysis"
                for a in actions[: max(1, len(actions) - 1)]
            )
            if not has_prior_analysis:
                evidence.append("api_call_without_prior_analysis")
            else:
                return False, []
        else:
            return False, []

    if "step_count_gte" in trigger:
        threshold = trigger["step_count_gte"]
        actual = payment.get("elapsed_steps", payment.get("turns", 0))
        if actual >= threshold:
            evidence.append(f"steps={actual}>={threshold}")
            if trigger.get("no_progress"):
                sq = outcome.get("settlement_quality", "")
                if sq in ("failure_with_signal", "failure_without_signal", "unknown"):
                    evidence.append("no_progress_indicated")
                else:
                    return False, []
        else:
            return False, []

    if "final_answer_action" in trigger:
        has_final = any(
            a.get("action_type") in ("buy", "submit", "final_answer")
            for a in actions[-2:]
        )
        if not has_final:
            has_final = outcome.get("settlement_quality") in (
                "clean_success",
                "brittle_success",
                "recovered_success",
            )
        if has_final and trigger.get("prior_verification") is False:
            has_verify = any(
                "test" in str(a.get("content", "")).lower()
                or a.get("action_type") == "verification"
                for a in actions[: max(1, len(actions) - 1)]
            )
            if not has_verify:
                evidence.append("final_answer_without_prior_verification")
            else:
                return False, []
        else:
            return False, []

    if "settlement_quality" in trigger:
        target_sq = trigger["settlement_quality"]
        actual_sq = outcome.get("settlement_quality", "")
        if actual_sq == target_sq:
            evidence.append(f"settlement_quality={actual_sq}")
        else:
            return False, []

    if "early_specific_action" in trigger:
        has_early = any(
            a.get("action_type") in ("command", "api_call", "buy")
            and a.get("turn_index", 99) < trigger.get("turn_index_lt", 3)
            for a in actions
        )
        if has_early:
            evidence.append("early_specific_action_before_analysis")
        else:
            return False, []

    if not evidence:
        return False, []

    return True, evidence


def _assess_counterfactual(
    policy: dict[str, Any],
    record: dict[str, Any],
    fired: bool,
) -> tuple[str, str, str, str]:
    if not fired:
        return "no_effect", "Policy trigger not met.", "low", "low"

    fm = record.get("labels", {}).get("failure_mode")
    sq = record.get("outcome", {}).get("settlement_quality", "")
    conf = record.get("outcome", {}).get("confidence", 0.0)
    payment = record.get("payment", {})
    error_count = payment.get("error_count", 0)
    policy_fms = policy.get("evidence", {}).get("observed_failure_patterns", [])

    payment_risk = "low"
    if error_count >= 3 or payment.get("turns", 0) >= 10:
        payment_risk = "medium"
    if error_count >= 5 or payment.get("turns", 0) >= 15:
        payment_risk = "high"

    fp_risk = "low"
    if sq in ("clean_success", "recovered_success") and fm is None:
        fp_risk = "high"
    elif sq in ("clean_success",) and fm is None:
        fp_risk = "medium"

    if sq in ("failure_with_signal", "failure_without_signal") and fm in policy_fms:
        return (
            "likely_helpful",
            f"Policy addresses observed failure mode '{fm}' in {sq} trace.",
            payment_risk,
            fp_risk,
        )

    if sq in ("clean_success", "recovered_success") and fm is None:
        return (
            "likely_harmful",
            f"Policy would fire on successful trace (quality={sq}) with no failure mode.",
            payment_risk,
            fp_risk,
        )

    if sq in ("partial_success", "unknown"):
        return (
            "uncertain",
            f"Policy fires on ambiguous trace (quality={sq}, fm={fm}).",
            payment_risk,
            fp_risk,
        )

    if fm and fm not in policy_fms:
        return (
            "uncertain",
            f"Policy fires but failure mode '{fm}' not in policy's target patterns {policy_fms}.",
            payment_risk,
            fp_risk,
        )

    return (
        "uncertain",
        f"Policy fires on trace with quality={sq}, fm={fm}.",
        payment_risk,
        fp_risk,
    )


def evaluate_policies_shadow(
    records: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    min_confidence: float = 0.65,
    dataset: str | None = None,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    results = []
    filtered = []
    for rec in records:
        if (
            min_confidence > 0
            and rec.get("outcome", {}).get("confidence", 0.0) < min_confidence
        ):
            continue
        if dataset and rec.get("dataset") != dataset:
            continue
        if domain and rec.get("domain") != domain:
            continue
        filtered.append(rec)

    for policy in policies:
        for record in filtered:
            trigger = policy.get("trigger", {})
            fired, trigger_evidence = _check_trigger(trigger, record)

            assessment, rationale, payment_risk, fp_risk = _assess_counterfactual(
                policy, record, fired
            )

            results.append(
                {
                    "policy_id": policy.get("id", ""),
                    "trace_id": record.get("task_id", ""),
                    "dataset": record.get("dataset", ""),
                    "domain": record.get("domain", ""),
                    "would_fire": fired,
                    "trigger_evidence": trigger_evidence,
                    "observed_failure_mode": record.get("labels", {}).get(
                        "failure_mode"
                    ),
                    "observed_settlement_quality": record.get("outcome", {}).get(
                        "settlement_quality", ""
                    ),
                    "observed_confidence": record.get("outcome", {}).get(
                        "confidence", 0.0
                    ),
                    "counterfactual_assessment": assessment,
                    "rationale": rationale,
                    "payment_risk": payment_risk,
                    "false_positive_risk": fp_risk,
                }
            )

    return results


def compute_promotion_scores(
    results: list[dict[str, Any]],
    policies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    policy_results: dict[str, list[dict]] = {}
    for r in results:
        pid = r["policy_id"]
        policy_results.setdefault(pid, []).append(r)

    scores = []
    for policy in policies:
        pid = policy.get("id", "")
        pr = policy_results.get(pid, [])

        fire_count = sum(1 for r in pr if r["would_fire"])
        helpful = sum(
            1
            for r in pr
            if r["would_fire"] and r["counterfactual_assessment"] == "likely_helpful"
        )
        harmful = sum(
            1
            for r in pr
            if r["would_fire"] and r["counterfactual_assessment"] == "likely_harmful"
        )
        uncertain = sum(
            1
            for r in pr
            if r["would_fire"] and r["counterfactual_assessment"] == "uncertain"
        )

        fire_events = [r for r in pr if r["would_fire"]]
        fp_rate = 0.0
        if fire_events:
            fp_events = sum(
                1 for r in fire_events if r["false_positive_risk"] in ("high", "medium")
            )
            fp_rate = round(fp_events / len(fire_events), 3)

        payment_dist: dict[str, int] = {}
        for r in fire_events:
            pr_key = r.get("payment_risk", "low")
            payment_dist[pr_key] = payment_dist.get(pr_key, 0) + 1

        domains = sorted(set(r["domain"] for r in fire_events)) if fire_events else []
        datasets = sorted(set(r["dataset"] for r in fire_events)) if fire_events else []

        recommendation = "keep_proposed"
        rec_rationale = ""

        if fire_count == 0:
            recommendation = "needs_more_evidence"
            rec_rationale = "Policy never fires on evaluated records."
        elif harmful > 0:
            recommendation = "reject" if harmful >= helpful else "refine"
            rec_rationale = f"Policy harms {harmful} successful traces."
        elif fp_rate > 0.5:
            recommendation = "refine"
            rec_rationale = f"False positive rate {fp_rate:.1%} is too high."
        elif helpful >= 5 and harmful == 0 and fp_rate <= 0.10:
            multi_source = len(datasets) >= 2 or len(domains) >= 2
            if multi_source or policy.get("_domain_specific"):
                recommendation = "candidate_for_activation"
                rec_rationale = f"Helpful on {helpful} traces across {len(datasets)} datasets, no harm, FP rate {fp_rate:.1%}."
            else:
                recommendation = "candidate_for_activation"
                rec_rationale = f"Helpful on {helpful} traces, no harm, FP rate {fp_rate:.1%}. Limited cross-dataset evidence ({len(datasets)} dataset)."
        elif helpful > 0 and harmful == 0:
            recommendation = "keep_proposed"
            rec_rationale = (
                f"Helpful on {helpful} traces but below activation threshold (need 5+)."
            )
        else:
            recommendation = "keep_proposed"
            rec_rationale = "Insufficient evidence for promotion."

        scores.append(
            {
                "policy_id": pid,
                "supporting_trace_count": len(pr),
                "would_fire_count": fire_count,
                "likely_helpful_count": helpful,
                "likely_harmful_count": harmful,
                "uncertain_count": uncertain,
                "false_positive_rate_estimate": fp_rate,
                "payment_risk_distribution": payment_dist,
                "domains_observed": domains,
                "datasets_observed": datasets,
                "recommendation": recommendation,
                "recommendation_rationale": rec_rationale,
            }
        )

    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate policies in shadow mode")
    parser.add_argument("--ledger", default=None, help="SQLite ledger path")
    parser.add_argument("--policies", default="data/settlement_datasets/policies.yaml")
    parser.add_argument(
        "--output", default="data/settlement_datasets/policy_shadow_eval"
    )
    parser.add_argument("--min-confidence", type=float, default=0.0)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--domain", default=None)

    args = parser.parse_args()

    with open(args.policies) as f:
        policy_data = yaml.safe_load(f)
    policies = policy_data.get("policies", [])

    all_records = []
    for ds in available_datasets():
        path = f"data/settlement_datasets/raw_samples/{ds}.jsonl"
        p = Path(path)
        if p.exists():
            all_records.extend(read_records_jsonl(str(p)))

    print(f"Loaded {len(policies)} policies, {len(all_records)} records")

    results = evaluate_policies_shadow(
        all_records,
        policies,
        min_confidence=args.min_confidence,
        dataset=args.dataset,
        domain=args.domain,
    )

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "policy_shadow_results.jsonl"
    write_records_jsonl(results, str(results_path))
    print(f"Wrote {len(results)} shadow results -> {results_path}")

    scores = compute_promotion_scores(results, policies)
    scores_path = output_dir / "policy_promotion_scores.jsonl"
    write_records_jsonl(scores, str(scores_path))

    summary_path = output_dir / "policy_shadow_summary.csv"
    with summary_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "policy_id",
                "supporting_trace_count",
                "would_fire_count",
                "likely_helpful_count",
                "likely_harmful_count",
                "uncertain_count",
                "false_positive_rate_estimate",
                "payment_risk_distribution",
                "domains_observed",
                "datasets_observed",
                "recommendation",
                "recommendation_rationale",
            ],
        )
        writer.writeheader()
        for s in scores:
            writer.writerow(s)
    print(f"Wrote promotion scores -> {summary_path}")

    for s in scores:
        print(
            f"  {s['policy_id']}: fires={s['would_fire_count']}, "
            f"helpful={s['likely_helpful_count']}, harmful={s['likely_harmful_count']}, "
            f"FP={s['false_positive_rate_estimate']:.1%}, rec={s['recommendation']}"
        )


if __name__ == "__main__":
    main()
