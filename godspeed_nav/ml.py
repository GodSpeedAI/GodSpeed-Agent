from __future__ import annotations


def ensure_ml_allowed(settlement_event_count: int, threshold: int = 200) -> bool:
    if settlement_event_count < threshold:
        raise RuntimeError(
            f"insufficient_settlement_history: {settlement_event_count} events available, {threshold} required"
        )
    return True
