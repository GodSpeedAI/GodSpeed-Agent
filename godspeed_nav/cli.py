from __future__ import annotations

import argparse
import json
from typing import Any

from godspeed_nav.metrics import compute_error, estimate_payment


def _json_arg(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("value must be a JSON object")
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
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "compute-error":
        return compute_error(args.desired, args.observed, args.weights)
    if args.command == "estimate-payment":
        return estimate_payment(args.costs, args.weights, args.capacities)
    raise SystemExit(f"Unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

