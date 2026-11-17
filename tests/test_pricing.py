from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from qshift.engine.pricing import (
    format_inr,
    gst_by_slab,
    line_gst,
    money_for_quantity,
    quote_total,
)


def test_indian_grouping_and_sign() -> None:
    assert format_inr(85000000) == "₹8,50,000"
    assert format_inr(-170000000) == "-₹17,00,000"
    assert format_inr(123) == "₹1.23"


def test_half_up_to_paise() -> None:
    assert money_for_quantity(Decimal("0.5"), 1) == 1


def test_gst_is_rounded_half_up_and_added_to_quote_total() -> None:
    line = {"quantity": "1", "rate_paise": 101, "gst_bps": 1800}
    assert line_gst(line) == 18
    assert quote_total([line]) == 119
    assert gst_by_slab([line]) == {1800: 18}


def test_gst_rounds_once_per_slab_subtotal() -> None:
    lines = [{"quantity": "1", "rate_paise": 1, "gst_bps": 1800} for _ in range(3)]
    assert line_gst(lines[0]) == 0
    assert gst_by_slab(lines) == {1800: 1}
    assert quote_total(lines) == 4


@given(
    quantities=st.lists(
        st.decimals(
            min_value="0", max_value="1000", places=3, allow_nan=False, allow_infinity=False
        ),
        min_size=0,
        max_size=20,
    ),
    rate=st.integers(min_value=0, max_value=10_000_000),
)
def test_quote_total_equals_sum_of_line_totals(quantities: list[Decimal], rate: int) -> None:
    lines = [{"quantity": str(q), "rate_paise": rate} for q in quantities]
    assert quote_total(lines) == sum(money_for_quantity(q, rate) for q in quantities)


@given(
    qty=st.decimals(
        min_value="0", max_value="100", places=3, allow_nan=False, allow_infinity=False
    ),
    rate=st.integers(0, 1_000_000),
)
def test_recalculation_is_idempotent(qty: Decimal, rate: int) -> None:
    once = money_for_quantity(qty, rate)
    assert money_for_quantity(qty, rate) == once
