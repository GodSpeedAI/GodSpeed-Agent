import json
from pathlib import Path

import pytest

from godspeed_nav.schemas import (
    Affordance,
    Capability,
    DesiredDirection,
    DomainRuleError,
    PaymentEstimate,
    Possibility,
    Potential,
    SettlementEvent,
    Substrate,
)
from godspeed_nav.storage import LedgerStore


def test_potential_cannot_be_executed_as_affordance():
    potential = Potential(
        id="pot-1",
        statement="Replace the whole operating model",
        required_capabilities=["validated migration path"],
        missing_pathway_reason="No receiving pathway has been proven",
    )

    with pytest.raises(DomainRuleError) as error:
        potential.to_affordance()

    assert error.value.code == "potential_cannot_execute"


def test_possibility_cannot_be_metabolized():
    possibility = Possibility(
        id="pos-1",
        statement="Maybe automate settlement review",
        candidate_pathway="Try a local script",
        unknowns=["No repeated settlement history"],
    )

    with pytest.raises(DomainRuleError) as error:
        possibility.to_substrate()

    assert error.value.code == "possibility_cannot_metabolize"


def test_affordance_requires_pathway_and_payment_estimate():
    with pytest.raises(DomainRuleError) as error:
        Affordance(
            id="aff-1",
            statement="Run a migration",
            pathway="",
            payment_estimate=None,
            expected_horizon_delta=2.0,
        )

    assert error.value.code == "affordance_requires_pathway_and_payment"


def test_capability_requires_repeated_successful_settlement():
    payment = PaymentEstimate(id="pay-1", affordance_id="aff-1", dimensions={"time": 1}, burden=1)
    one_settlement = [
        SettlementEvent(
            id="set-1",
            affordance_id="aff-1",
            before_state={"tests": 0},
            after_state={"tests": 3},
            payment_actual={"time": 1},
            score=0.9,
            status="success",
            evidence=["pytest passed"],
        )
    ]

    with pytest.raises(DomainRuleError) as error:
        Capability.from_settlements(
            id="cap-1",
            label="Plugin validation",
            settlement_events=one_settlement,
            payment_estimate=payment,
        )

    assert error.value.code == "capability_requires_repeated_settlement"


def test_substrate_requires_metabolization_evidence():
    capability = Capability(
        id="cap-1",
        label="Plugin validation",
        settlement_event_ids=["set-1", "set-2"],
        status="capability",
    )

    with pytest.raises(DomainRuleError) as error:
        Substrate.from_capability(capability, metabolization_score=0.4, evidence=["reused once"])

    assert error.value.code == "substrate_requires_metabolization"


def test_desired_direction_can_die_and_request_affordance_review():
    direction = DesiredDirection(
        id="dir-1",
        label="Ship a static goal",
        kind="goal",
        statement="Complete the original task",
        source="user",
        horizon_id="hor-1",
    )

    dead = direction.die("No longer produces useful pressure")

    assert dead.status == "dead"
    assert dead.needs_affordance_review is True
    assert "No longer" in dead.pressure_notes


def test_json_schemas_exist_for_required_domain_entities():
    schema_root = Path(__file__).resolve().parents[1] / "schemas"
    for name in [
        "desired_direction",
        "horizon",
        "affordance",
        "payment",
        "settlement",
        "capability",
        "substrate",
        "trajectory",
    ]:
        schema = json.loads((schema_root / f"{name}.schema.json").read_text(encoding="utf-8"))
        assert schema["title"]
        assert schema["type"] == "object"


def test_ledger_store_appends_reads_and_redacts_secrets(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness", redact_secrets=True)

    store.append("settlements", {"id": "set-1", "api_key": "sk-test", "nested": {"token": "abc"}})

    records = store.read("settlements")

    assert records == [{"id": "set-1", "api_key": "[REDACTED]", "nested": {"token": "[REDACTED]"}}]


def test_corrupt_ledger_records_are_quarantined(tmp_path: Path):
    store = LedgerStore(tmp_path / ".godspeed-harness")
    ledger = store.ledger_path("payments")
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text('{"id": "pay-1"}\nnot-json\n{"id": "pay-2"}\n', encoding="utf-8")

    records = store.read("payments")

    assert records == [{"id": "pay-1"}, {"id": "pay-2"}]
    quarantine = store.root / "cache" / "quarantine" / "payments.corrupt.jsonl"
    assert "not-json" in quarantine.read_text(encoding="utf-8")
