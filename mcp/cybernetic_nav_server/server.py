from __future__ import annotations

import json
import sys
from typing import Any

from godspeed_nav.absorption import review_absorbability
from godspeed_nav.config import load_config, resolve_storage_root, runtime_policy
from godspeed_nav.disintegration import review_positive_disintegration
from godspeed_nav.metabolization import compute_metabolization
from godspeed_nav.metrics import (
    compute_error,
    estimate_payment,
    rank_affordances,
    review_representational_transition,
    score_settlement,
)
from godspeed_nav.ml import run_predictive_extensions
from godspeed_nav.reports import generate_developmental_report
from godspeed_nav.runtime import NavigationRuntime
from godspeed_nav.schemas import DomainRuleError
from godspeed_nav.storage import LedgerStore
from godspeed_nav.trajectory import detect_circular_motion, update_trajectory
from godspeed_nav.validation import validate_enterprise_readiness

TOOL_NAMES = [
    "cybernetic_nav.compute_error",
    "cybernetic_nav.estimate_payment",
    "cybernetic_nav.score_settlement",
    "cybernetic_nav.update_trajectory",
    "cybernetic_nav.compute_metabolization",
    "cybernetic_nav.rank_affordances",
    "cybernetic_nav.review_representational_transition",
    "cybernetic_nav.detect_circular_motion",
    "cybernetic_nav.review_absorbability",
    "cybernetic_nav.review_positive_disintegration",
    "cybernetic_nav.write_ledger_event",
    "cybernetic_nav.read_developmental_memory",
    "cybernetic_nav.search_developmental_memory",
    "cybernetic_nav.start_direction",
    "cybernetic_nav.review_horizon",
    "cybernetic_nav.record_settlement",
    "cybernetic_nav.runtime_snapshot",
    "cybernetic_nav.cognitive_surfaces",
    "cybernetic_nav.developmental_report",
    "cybernetic_nav.predictive_extensions",
    "cybernetic_nav.validate_enterprise_readiness",
]


def _runtime(arguments: dict[str, Any]) -> NavigationRuntime:
    workspace_root = arguments.get("workspace_root", ".")
    config = load_config(workspace_root)
    return NavigationRuntime(
        resolve_storage_root(workspace_root, arguments.get("storage_root")),
        policy=runtime_policy(config),
    )


def _store(arguments: dict[str, Any]) -> LedgerStore:
    workspace_root = arguments.get("workspace_root", ".")
    return LedgerStore(
        resolve_storage_root(workspace_root, arguments.get("storage_root"))
    )


def _policy(arguments: dict[str, Any]) -> dict[str, Any]:
    return runtime_policy(load_config(arguments.get("workspace_root", ".")))


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "cybernetic_nav.compute_error":
            return compute_error(**arguments)
        if name == "cybernetic_nav.estimate_payment":
            return estimate_payment(**arguments)
        if name == "cybernetic_nav.score_settlement":
            return score_settlement(**arguments)
        if name == "cybernetic_nav.update_trajectory":
            return update_trajectory(**arguments)
        if name == "cybernetic_nav.compute_metabolization":
            return compute_metabolization(**arguments)
        if name == "cybernetic_nav.rank_affordances":
            return rank_affordances(**arguments)
        if name == "cybernetic_nav.review_representational_transition":
            return _runtime(arguments).review_representational_transition(
                current_state=arguments["current_state"],
                target_state=arguments["target_state"],
                capacity=float(arguments["capacity"]),
                metabolized_shortcuts=arguments.get("metabolized_shortcuts"),
            )
        if name == "cybernetic_nav.detect_circular_motion":
            return detect_circular_motion(**arguments)
        if name == "cybernetic_nav.review_absorbability":
            return review_absorbability(
                root_project_state=arguments["root_project_state"],
                external_project_state=arguments["external_project_state"],
                desired_direction=arguments["desired_direction"],
                capability_delta=arguments["capability_delta"],
                license_summary=arguments["license_summary"],
                pathway=arguments.get("pathway"),
                policy=_policy(arguments),
            )
        if name == "cybernetic_nav.review_positive_disintegration":
            return review_positive_disintegration(
                structures=arguments["structures"],
                require_human_review=arguments.get(
                    "require_human_review",
                    _policy(arguments)["require_human_review_for_disintegration"],
                ),
            )
        if name == "cybernetic_nav.write_ledger_event":
            envelope = _store(arguments).append_event(
                arguments["ledger_name"], arguments["record"]
            )
            return {"recorded": True, "event": envelope}
        if name == "cybernetic_nav.read_developmental_memory":
            ledger_name = arguments.get("ledger_name")
            if ledger_name:
                return {
                    "ledger": ledger_name,
                    "records": _store(arguments).read(ledger_name),
                }
            if arguments.get("query") == "lineage":
                return _runtime(arguments).read_developmental_memory()
            return {
                "ledgers": {
                    ledger: _store(arguments).read(ledger)
                    for ledger in [
                        "desired_directions",
                        "horizons",
                        "affordances",
                        "payments",
                        "settlements",
                        "trajectories",
                    ]
                },
                "lineage": _runtime(arguments).read_developmental_memory(),
            }
        if name == "cybernetic_nav.search_developmental_memory":
            return _store(arguments).search_developmental_memory(
                arguments["query"],
                limit=int(arguments.get("limit", 5)),
            )
        if name == "cybernetic_nav.start_direction":
            return _runtime(arguments).start_direction(
                label=arguments["label"],
                statement=arguments["statement"],
                kind=arguments.get("kind", "goal"),
                source=arguments.get("source"),
            )
        if name == "cybernetic_nav.review_horizon":
            return _runtime(arguments).review_horizon(
                direction_id=arguments["direction_id"],
                candidates=arguments["candidates"],
            )
        if name == "cybernetic_nav.record_settlement":
            return _runtime(arguments).record_settlement(
                affordance_id=arguments["affordance_id"],
                before_state=arguments["before_state"],
                after_state=arguments["after_state"],
                payment_actual=arguments["payment_actual"],
                evidence=arguments["evidence"],
                horizon_delta=float(arguments["horizon_delta"]),
            )
        if name == "cybernetic_nav.runtime_snapshot":
            return _runtime(arguments).snapshot()
        if name == "cybernetic_nav.cognitive_surfaces":
            return _runtime(arguments).cognitive_surfaces()
        if name == "cybernetic_nav.developmental_report":
            return generate_developmental_report(
                arguments.get("storage_root", ".godspeed-harness")
            )
        if name == "cybernetic_nav.predictive_extensions":
            return run_predictive_extensions(
                workspace_root=arguments.get("workspace_root", "."),
                storage_root=arguments.get("storage_root", ".godspeed-harness"),
                candidates=arguments.get("candidates", []),
                provider_name=arguments.get("provider"),
            )
        if name == "cybernetic_nav.validate_enterprise_readiness":
            return validate_enterprise_readiness(
                workspace_root=arguments.get("workspace_root", "."),
                storage_root=str(_store(arguments).root),
            )
    except KeyError as exc:
        raise ValueError(
            f"invalid_input: missing required argument {exc.args[0]}"
        ) from exc
    except TypeError as exc:
        raise ValueError(f"invalid_input: {exc}") from exc
    raise ValueError(f"invalid_input: unknown tool {name}")


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"tools": TOOL_NAMES}, sort_keys=True))
        return 0

    request = json.loads(raw)
    if not isinstance(request, dict):
        raise SystemExit("invalid_input: MCP request must be a JSON object")
    try:
        result = call_tool(request["name"], request.get("arguments", {}))
    except DomainRuleError as error:
        sys.stderr.write(
            json.dumps({"code": error.code, "message": str(error)}, sort_keys=True)
            + "\n"
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
