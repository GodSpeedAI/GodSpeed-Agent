from __future__ import annotations

from typing import Any

_REGISTRY: dict[str, type] = {}


def register_adapter(name: str, adapter_cls: type) -> None:
    _REGISTRY[name] = adapter_cls


def get_adapter(name: str) -> Any:
    if name not in _REGISTRY:
        _lazy_load()
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown adapter: {name}. Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]()


def get_all_adapters() -> dict[str, Any]:
    _lazy_load()
    return {name: cls() for name, cls in _REGISTRY.items()}


def available_datasets() -> list[str]:
    _lazy_load()
    return sorted(_REGISTRY.keys())


_LOADED = False


def _lazy_load() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    from scripts.settlement_datasets.agenttrove_adapter import AgentTroveAdapter
    from scripts.settlement_datasets.swegym_adapter import SWEGymAdapter
    from scripts.settlement_datasets.swegym_openhands_adapter import (
        SWEGymOpenHandsAdapter,
    )
    from scripts.settlement_datasets.nebius_swe_agent_adapter import (
        NebiusSWEAgentAdapter,
    )
    from scripts.settlement_datasets.swe_smith_adapter import SWESmithAdapter
    from scripts.settlement_datasets.apibank_adapter import APIBankAdapter
    from scripts.settlement_datasets.webshop_adapter import WebShopAdapter

    register_adapter("agenttrove", AgentTroveAdapter)
    register_adapter("swegym", SWEGymAdapter)
    register_adapter("swegym_openhands", SWEGymOpenHandsAdapter)
    register_adapter("nebius_swe_agent", NebiusSWEAgentAdapter)
    register_adapter("swe_smith", SWESmithAdapter)
    register_adapter("apibank", APIBankAdapter)
    register_adapter("webshop", WebShopAdapter)
