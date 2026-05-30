from __future__ import annotations

from typing import Any

from godspeed_nav.metabolization import compute_metabolization
from godspeed_nav.metrics import compute_error, estimate_payment, rank_affordances, score_settlement
from godspeed_nav.reports import generate_developmental_report
from godspeed_nav.runtime import NavigationRuntime
from godspeed_nav.trajectory import update_trajectory


TOOL_NAMES = [
    "cybernetic_nav.compute_error",
    "cybernetic_nav.estimate_payment",
    "cybernetic_nav.score_settlement",
    "cybernetic_nav.update_trajectory",
    "cybernetic_nav.compute_metabolization",
    "cybernetic_nav.rank_affordances",
    "cybernetic_nav.runtime_snapshot",
    "cybernetic_nav.developmental_report",
]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
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
    if name == "cybernetic_nav.runtime_snapshot":
        return NavigationRuntime(arguments.get("storage_root", ".godspeed-harness")).snapshot()
    if name == "cybernetic_nav.developmental_report":
        return generate_developmental_report(arguments.get("storage_root", ".godspeed-harness"))
    raise ValueError(f"invalid_input: unknown tool {name}")
