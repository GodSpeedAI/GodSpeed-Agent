from __future__ import annotations

import argparse
import json
from typing import Any

from godspeed_nav.absorption import review_absorbability
from godspeed_nav.metabolization import compute_metabolization
from godspeed_nav.metrics import compute_error, estimate_payment
from godspeed_nav.metrics import rank_affordances, score_settlement
from godspeed_nav.reports import generate_developmental_report
from godspeed_nav.runtime import NavigationRuntime


def _json_arg(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("value must be a JSON object")
    return parsed


def _json_list_arg(value: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise argparse.ArgumentTypeError("value must be a JSON array")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="godspeed-nav")
    subcommands = parser.add_subparsers(dest="command", required=True)

    error_parser = subcommands.add_parser("compute-error")
    error_parser.add_argument("--desired", type=_json_arg, required=True)
    error_parser.add_argument("--observed", type=_json_arg, required=True)
    error_parser.add_argument("--weights", type=_json_arg, default={})

    payment_parser = subcommands.add_parser("estimate-payment")
    payment_parser.add_argument("--costs", type=_json_arg, required=True)
    payment_parser.add_argument("--weights", type=_json_arg, default={})
    payment_parser.add_argument("--capacities", type=_json_arg, default={})

    rank_parser = subcommands.add_parser("rank-affordances")
    rank_parser.add_argument("--candidates", type=_json_list_arg, required=True)
    rank_parser.add_argument("--payments", type=_json_arg, required=True)

    settlement_parser = subcommands.add_parser("score-settlement")
    settlement_parser.add_argument("--before", type=_json_arg, required=True)
    settlement_parser.add_argument("--after", type=_json_arg, required=True)
    settlement_parser.add_argument("--desired", type=_json_arg, required=True)
    settlement_parser.add_argument("--payment", type=_json_arg, required=True)
    settlement_parser.add_argument("--evidence", type=_json_list_arg, default=[])

    metabolization_parser = subcommands.add_parser("metabolization")
    metabolization_parser.add_argument("--capability-id", required=True)
    metabolization_parser.add_argument("--settlements", type=_json_list_arg, required=True)
    metabolization_parser.add_argument("--reuse-frequency", type=int, required=True)
    metabolization_parser.add_argument("--context-diversity", type=int, required=True)
    metabolization_parser.add_argument("--stability", type=float, required=True)
    metabolization_parser.add_argument("--maintenance-burden", type=float, required=True)
    metabolization_parser.add_argument("--attention-burden", type=float, required=True)

    absorption_parser = subcommands.add_parser("absorbability")
    absorption_parser.add_argument("--root-state", type=_json_arg, required=True)
    absorption_parser.add_argument("--external-state", type=_json_arg, required=True)
    absorption_parser.add_argument("--desired", type=_json_arg, required=True)
    absorption_parser.add_argument("--capability-delta", type=_json_list_arg, required=True)
    absorption_parser.add_argument("--license", type=_json_arg, required=True)
    absorption_parser.add_argument("--pathway", default=None)

    runtime_snapshot_parser = subcommands.add_parser("runtime-snapshot")
    runtime_snapshot_parser.add_argument("--storage-root", default=".godspeed-harness")

    start_direction_parser = subcommands.add_parser("start-direction")
    start_direction_parser.add_argument("--storage-root", default=".godspeed-harness")
    start_direction_parser.add_argument("--label", required=True)
    start_direction_parser.add_argument("--statement", required=True)
    start_direction_parser.add_argument("--kind", default="goal")
    start_direction_parser.add_argument("--source", default="cli")

    review_horizon_parser = subcommands.add_parser("review-horizon")
    review_horizon_parser.add_argument("--storage-root", default=".godspeed-harness")
    review_horizon_parser.add_argument("--direction-id", required=True)
    review_horizon_parser.add_argument("--candidates", type=_json_list_arg, required=True)

    record_settlement_parser = subcommands.add_parser("record-settlement")
    record_settlement_parser.add_argument("--storage-root", default=".godspeed-harness")
    record_settlement_parser.add_argument("--affordance-id", required=True)
    record_settlement_parser.add_argument("--before", type=_json_arg, required=True)
    record_settlement_parser.add_argument("--after", type=_json_arg, required=True)
    record_settlement_parser.add_argument("--payment", type=_json_arg, required=True)
    record_settlement_parser.add_argument("--evidence", type=_json_list_arg, required=True)
    record_settlement_parser.add_argument("--horizon-delta", type=float, required=True)

    developmental_report_parser = subcommands.add_parser("developmental-report")
    developmental_report_parser.add_argument("--storage-root", default=".godspeed-harness")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "compute-error":
        return compute_error(args.desired, args.observed, args.weights)
    if args.command == "estimate-payment":
        return estimate_payment(args.costs, args.weights, args.capacities)
    if args.command == "rank-affordances":
        return rank_affordances(args.candidates, args.payments)
    if args.command == "score-settlement":
        return score_settlement(
            args.before,
            args.after,
            args.desired,
            args.payment,
            {"evidence": args.evidence},
        )
    if args.command == "metabolization":
        return compute_metabolization(
            capability_id=args.capability_id,
            settlement_events=args.settlements,
            reuse_frequency=args.reuse_frequency,
            context_diversity=args.context_diversity,
            stability=args.stability,
            maintenance_burden=args.maintenance_burden,
            attention_burden=args.attention_burden,
        )
    if args.command == "absorbability":
        return review_absorbability(
            root_project_state=args.root_state,
            external_project_state=args.external_state,
            desired_direction=args.desired,
            capability_delta=args.capability_delta,
            license_summary=args.license,
            pathway=args.pathway,
        )
    if args.command == "runtime-snapshot":
        return NavigationRuntime(args.storage_root).snapshot()
    if args.command == "start-direction":
        return NavigationRuntime(args.storage_root).start_direction(
            label=args.label,
            statement=args.statement,
            kind=args.kind,
            source=args.source,
        )
    if args.command == "review-horizon":
        return NavigationRuntime(args.storage_root).review_horizon(
            direction_id=args.direction_id,
            candidates=args.candidates,
        )
    if args.command == "record-settlement":
        return NavigationRuntime(args.storage_root).record_settlement(
            affordance_id=args.affordance_id,
            before_state=args.before,
            after_state=args.after,
            payment_actual=args.payment,
            evidence=args.evidence,
            horizon_delta=args.horizon_delta,
        )
    if args.command == "developmental-report":
        return generate_developmental_report(args.storage_root)
    raise SystemExit(f"Unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
