"""Hugging Face dataset streaming helpers for the calibration pipeline."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

try:
    from datasets import load_dataset
except ImportError:  # pragma: no cover - exercised by dependency tests if needed
    load_dataset = None  # type: ignore[assignment]


def require_datasets() -> None:
    """Raise if the ``datasets`` library is not installed."""
    if load_dataset is None:
        raise RuntimeError("datasets_dependency_required: install with uv sync")


def load_hf_stream(source_uri: str, split: str) -> Iterable[dict[str, Any]]:
    """Return a streaming iterator over a Hugging Face dataset split."""
    require_datasets()
    return load_dataset(source_uri, split=split, streaming=True)


def iter_limited(
    rows: Iterable[dict[str, Any]], limit: int | None
) -> Iterator[dict[str, Any]]:
    """Yield at most *limit* rows from *rows*."""
    for index, row in enumerate(rows):
        if limit is not None and index >= limit:
            return
        yield dict(row)
