"""WP-3 (F-02) end-to-end: a GSA SettlementRecorded reaches the ledger's
`event_log.agent_events` through NATS, and a malformed event on a fail-closed
subject lands on `sea.ledger.deadletter`.

Topology (provided by tests/e2e/docker-compose.yml):
    GSA publisher → NATS (sea.agent.event.godspeed-agent.<slug>)
                       → ledger bridge (sea_nats_bridge.py) → Postgres
                       → DLQ (sea.ledger.deadletter) on fail-closed rejection

The bridge runs as a subprocess from the sibling hassos-addon-agent-memory-ledger
repo (it needs that repo's venv with psycopg/nats). This test is SKIPPED unless
both services are reachable, so it never fails in environments without docker.

Plan-vs-reality note: the bridge marks `sea.agent.event` as fail-open
(warnings only), so a malformed *agent* event is ingested, NOT dead-lettered.
The DLQ path only triggers on fail-closed subjects (governance/memory). The
DLQ assertion here uses a fail-closed subject — exercising the real fail-closed
path rather than the plan's (incorrect) assumption that an agent event would
DLQ.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GSA_VENV = REPO_ROOT / ".venv" / "bin" / "python"
LEDGER_ROOT = REPO_ROOT.parent / "hassos-addon-agent-memory-ledger"
BRIDGE_PATH = LEDGER_ROOT / "agent_memory_ledger" / "rootfs" / "usr" / "bin" / "sea_nats_bridge.py"

NATS_URL = os.getenv("E2E_NATS_URL", "nats://127.0.0.1:4222")
PG_DSN = os.getenv(
    "E2E_PG_DSN", "postgresql://bridge_worker:bridge_e2e_pw@127.0.0.1:5432/agent_memory"
)


def _reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not (_reachable("127.0.0.1", 4222) and _reachable("127.0.0.1", 5432)),
    reason="e2e services not up (run: docker compose -f tests/e2e/docker-compose.yml up -d)",
)


def _wait_for_postgres(timeout: int = 30) -> None:
    """Wait for Postgres to accept a real query, not just a TCP connection.

    The container opens port 5432 while init scripts are still applying the
    ledger schema. Starting the bridge during that window makes it exit before
    creating the JetStream stream, and the test later fails as "no stream".
    """
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with psycopg.connect(PG_DSN, connect_timeout=2) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                    return
        except Exception as exc:  # noqa: BLE001 - readiness probe
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"postgres did not become query-ready: {last_error}")


@pytest.fixture(scope="module")
def bridge_process():
    """Start the ledger bridge pointed at the e2e NATS + Postgres."""
    _wait_for_postgres()
    env = {
        **os.environ,
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "5432",
        "DB_NAME": "agent_memory",
        "DB_USER": "bridge_worker",
        "DB_PASSWORD": "bridge_e2e_pw",
        "NATS_URL": NATS_URL,
        "JS_ENABLED": "true",
        "JS_STREAM_NAME": "SEA_LEDGER",
        "INBOUND_ENABLED": "true",
        "OUTBOUND_ENABLED": "false",  # no outbox rows in this test
        "DEAD_LETTER_ENABLED": "true",
        "FAIL_CLOSED": "true",
        "HEALTH_ENABLED": "false",  # avoid port bind issues in CI
        "PYTHONUNBUFFERED": "1",
    }
    proc = subprocess.Popen(
        [str(GSA_VENV), str(BRIDGE_PATH)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(LEDGER_ROOT),
    )
    try:
        # Give the bridge time to connect + create the stream/consumer.
        time.sleep(6)
        if proc.poll() is not None:
            output = ""
            if proc.stdout is not None:
                output = proc.stdout.read().decode(errors="replace")
            pytest.fail(f"ledger bridge exited during startup:\n{output}")
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _purge_stream():
    """No-op retained for compatibility; the bridge owns the SEA_LEDGER stream
    and recreates it on startup, so tests must not delete it mid-run. The
    agent_events UNIQUE(source_agent, idempotency_key) constraint + the bridge's
    inbox dedup make re-runs idempotent without purging."""
    return


def test_settlement_reaches_agent_events(bridge_process):
    # Import GSA's publisher (this repo) and emit a valid v1 settlement.
    sys.path.insert(0, str(REPO_ROOT))
    from agentic_capability_loop.adapters import emit_settlement_recorded
    from agentic_capability_loop.publisher import SettlementPublisher

    settlement = emit_settlement_recorded("wr-e2e", "pr-e2e", "ev-e2e", "usable", "e2e match")
    marker = settlement["idempotency_key"]

    pub = SettlementPublisher(nats_url=NATS_URL, enabled=True)
    asyncio.run(_publish_and_close(pub, settlement))

    # Poll Postgres for the row.
    row = _poll_row(marker, timeout=15)
    assert row is not None, "settlement never landed in event_log.agent_events"
    assert row["source_agent"] == "godspeed-agent"
    assert row["event_type"] == "SettlementRecorded"
    payload = row["payload"]
    assert payload["work_request_id"] == "wr-e2e"
    assert payload["outcome"] == "usable"


def test_malformed_fail_closed_event_reaches_dlq(bridge_process):
    import nats

    dlq_messages: list[bytes] = []
    ready = asyncio.Event()

    async def _on_msg(msg):
        dlq_messages.append(msg.data)

    async def _run():
        nc = await nats.connect(NATS_URL, connect_timeout=3)
        # Core subscription on the DLQ subject (the bridge falls back to a core
        # publish when the JetStream publish to a non-stream subject fails).
        await nc.subscribe("sea.ledger.deadletter", cb=_on_msg)
        ready.set()
        await asyncio.sleep(0.5)  # let the subscription propagate
        js = nc.jetstream()
        # A malformed envelope on a FAIL-CLOSED subject (missing schema_version
        # → validate_contract fails → fail-closed rejection → DLQ).
        bad = {
            "event_id": str(uuid.uuid4()),
            "source_agent": "e2e-malformed",
            "occurred_at": "2026-07-01T00:00:00Z",
            "payload": {"requested_action_type": "tool_call"},
        }
        # Intentionally NO schema_version → contract validation fails.
        await js.publish(
            "sea.governance.request.tool_call",
            json.dumps(bad).encode(),
            headers={"Nats-Msg-Id": f"e2e-bad-{uuid.uuid4()}"},
        )
        # Wait for the bridge to dead-letter it.
        for _ in range(30):
            if dlq_messages:
                break
            await asyncio.sleep(1)
        await nc.close()

    asyncio.run(_run())
    assert dlq_messages, "malformed fail-closed event never reached the DLQ"
    dlq = json.loads(dlq_messages[0])
    assert "dead_lettered_at" in dlq
    assert "validation" in str(dlq.get("reason", "")).lower()


async def _publish_and_close(pub, envelope):
    await pub.publish(envelope)
    await pub.close()


def _poll_row(idempotency_key: str, timeout: int):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with psycopg.connect(PG_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT source_agent, event_type, payload FROM event_log.agent_events "
                    "WHERE idempotency_key = %s",
                    (idempotency_key,),
                )
                row = cur.fetchone()
                if row is not None:
                    return {
                        "source_agent": row[0],
                        "event_type": row[1],
                        "payload": row[2],
                    }
        time.sleep(0.5)
    return None
