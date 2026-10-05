"""Semantic-world identity gate (CEP-0008 world_ref, convergence Stage 9).

A ``world_ref`` names exactly one resolved semantic-world revision:
``world:<name>@sha256:<64 lowercase hex>``. DomainForge defines it and SEA-Forge
recomputes its digest; GodSpeed-Agent checks SYNTAX and EQUALITY only and never
claims the digest was verified here. A mutable alias (``world:<name>``) or a
label is not an identity and is refused.
"""

from __future__ import annotations

import os
import re
from typing import Any

from godspeed_nav.schemas import DomainRuleError

#: Same pattern as the cep ``world_ref`` schema (name <= 64 chars).
WORLD_REF_RE = re.compile(
    r"^world:[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*@sha256:[0-9a-f]{64}$"
)
_NAME_MAX = 64

#: Environment variable pinning this deployment's world.
WORLD_REF_ENV = "GSA_WORLD_REF"


def verify_world_ref(value: Any) -> str:
    """Return ``value`` when it is a well-formed pinned world_ref; else raise."""
    if not isinstance(value, str) or not WORLD_REF_RE.match(value):
        raise DomainRuleError(
            "malformed_world_ref",
            "world_ref must be world:<name>@sha256:<64 lowercase hex>; an alias, "
            "label, or missing value is not a world identity",
        )
    name = value[len("world:") : value.index("@")]
    if len(name) > _NAME_MAX:
        raise DomainRuleError(
            "malformed_world_ref", "world_ref name exceeds 64 characters"
        )
    return value


def pinned_world_ref() -> str | None:
    """The deployment's pinned world_ref, or ``None`` when unset (never invented)."""
    raw = os.environ.get(WORLD_REF_ENV)
    return verify_world_ref(raw) if raw else None
