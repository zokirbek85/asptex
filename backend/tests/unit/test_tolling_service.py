"""
Tests for tolling distribution calculation logic.

Scenario:
  Lot: counterparty A = 300,000 kg, counterparty B = 250,000 kg
  A fee = 20%, B fee = 20%
  Daily FG = 13,000 kg

Expected:
  A gross = 7,090.909 kg | fee = 1,418.182 kg | net = 5,672.727 kg
  B gross = 5,909.091 kg | fee = 1,181.818 kg | net = 4,727.273 kg
  Processor = 2,600.000 kg
  Total check = 5,672.727 + 4,727.273 + 2,600.000 = 13,000.000
"""
from decimal import Decimal
import uuid

import pytest

from app.modules.tolling.service import _calculate_lines
from app.shared.enums import TollingLineType


class _FakeParticipant:
    """Minimal stand-in for TollingLotParticipant."""
    def __init__(self, counterparty_id, raw_kg_delivered, fee_pct):
        self.id = uuid.uuid4()
        self.counterparty_id = counterparty_id
        self.raw_kg_delivered = raw_kg_delivered
        self.fee_pct = fee_pct


def test_tolling_distribution_calculation():
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    participants = [
        _FakeParticipant(id_a, 300_000, Decimal("20.00")),
        _FakeParticipant(id_b, 250_000, Decimal("20.00")),
    ]
    daily_fg = Decimal("13000")
    cp_names = {id_a: "A", id_b: "B"}

    lines = _calculate_lines(participants, daily_fg, cp_names)

    assert len(lines) == 3

    line_a = next(l for l in lines if l["counterparty_id"] == id_a)
    line_b = next(l for l in lines if l["counterparty_id"] == id_b)
    line_proc = next(l for l in lines if l["line_type"] == TollingLineType.PROCESSOR_FEE)

    assert Decimal(str(line_a["gross_kg"])) == Decimal("7090.909")
    assert Decimal(str(line_a["fee_kg"])) == Decimal("1418.182")
    assert Decimal(str(line_a["net_kg"])) == Decimal("5672.727")

    assert Decimal(str(line_b["gross_kg"])) == Decimal("5909.091")
    assert Decimal(str(line_b["fee_kg"])) == Decimal("1181.818")
    assert Decimal(str(line_b["net_kg"])) == Decimal("4727.273")

    assert Decimal(str(line_proc["net_kg"])) == Decimal("2600.000")

    total_check = (
        Decimal(str(line_a["net_kg"]))
        + Decimal(str(line_b["net_kg"]))
        + Decimal(str(line_proc["net_kg"]))
    )
    assert total_check == Decimal("13000.000")


def test_tolling_calculate_lines_returns_decimal_not_float():
    """T3: _calculate_lines must never round-trip amounts through float()."""
    id_a = uuid.uuid4()
    participants = [_FakeParticipant(id_a, 100_000, Decimal("20.00"))]
    lines = _calculate_lines(participants, Decimal("13000"), {id_a: "A"})

    numeric_fields = ["gross_kg", "fee_kg", "net_kg", "ownership_share_pct", "fee_pct_applied"]
    for line in lines:
        for field in numeric_fields:
            assert isinstance(line[field], Decimal), (
                f"{field} is {type(line[field])}, expected Decimal (no float round-trip)"
            )


def test_tolling_largest_remainder_forces_exact_total():
    """T5b: 3 equal-share participants + an odd-cent total must still sum
    to exactly daily_fg_kg_total after per-participant _q3 rounding."""
    ids = [uuid.uuid4() for _ in range(3)]
    participants = [_FakeParticipant(i, 100_000, Decimal("10.00")) for i in ids]
    daily_fg = Decimal("10000.001")

    lines = _calculate_lines(participants, daily_fg, {i: "X" for i in ids})

    owner_lines = [l for l in lines if l["line_type"] == TollingLineType.OWNER_NET]
    fee_line = next(l for l in lines if l["line_type"] == TollingLineType.PROCESSOR_FEE)

    total_gross = sum(l["gross_kg"] for l in owner_lines)
    assert total_gross == daily_fg

    total_net_plus_fee = sum(l["net_kg"] for l in owner_lines) + fee_line["net_kg"]
    assert total_net_plus_fee == daily_fg


def test_tolling_zero_raw_raises():
    """When total raw is zero, calculation must raise BusinessRuleViolationError."""
    from app.core.exceptions import BusinessRuleViolationError

    participants = [_FakeParticipant(uuid.uuid4(), 0, Decimal("20.00"))]
    with pytest.raises(BusinessRuleViolationError):
        _calculate_lines(participants, Decimal("13000"), {})


def test_tolling_different_fee_pcts():
    """Asymmetric fee percentages should distribute processor fee correctly."""
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    participants = [
        _FakeParticipant(id_a, 100_000, Decimal("15.00")),
        _FakeParticipant(id_b, 100_000, Decimal("25.00")),
    ]
    daily_fg = Decimal("10000")
    cp_names = {id_a: "A", id_b: "B"}

    lines = _calculate_lines(participants, daily_fg, cp_names)

    line_a = next(l for l in lines if l["counterparty_id"] == id_a)
    line_b = next(l for l in lines if l["counterparty_id"] == id_b)
    line_proc = next(l for l in lines if l["line_type"] == TollingLineType.PROCESSOR_FEE)

    # Each has 50% share → gross = 5000 each
    assert Decimal(str(line_a["gross_kg"])) == Decimal("5000.000")
    assert Decimal(str(line_b["gross_kg"])) == Decimal("5000.000")

    # A fee 15%: 750, B fee 25%: 1250
    assert Decimal(str(line_a["fee_kg"])) == Decimal("750.000")
    assert Decimal(str(line_b["fee_kg"])) == Decimal("1250.000")

    # Processor total = 750 + 1250 = 2000
    assert Decimal(str(line_proc["net_kg"])) == Decimal("2000.000")

    total = (
        Decimal(str(line_a["net_kg"]))
        + Decimal(str(line_b["net_kg"]))
        + Decimal(str(line_proc["net_kg"]))
    )
    assert total == Decimal("10000.000")
