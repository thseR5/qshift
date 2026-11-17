"""Financial calculations use Decimal input and integer paise output only."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def money_for_quantity(quantity: str | Decimal, rate_paise: int) -> int:
    qty = quantity if isinstance(quantity, Decimal) else Decimal(quantity)
    if not qty.is_finite() or qty < 0 or rate_paise < 0:
        raise ValueError("Quantity and rate must be finite and non-negative")
    return int((qty * Decimal(rate_paise)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def line_total(line: dict[str, Any]) -> int:
    return money_for_quantity(str(line["quantity"]), int(line["rate_paise"]))


def line_gst(line: dict[str, Any]) -> int:
    basis_points = int(line.get("gst_bps", 0))
    if basis_points < 0:
        raise ValueError("GST basis points must be non-negative")
    gst = Decimal(line_total(line)) * Decimal(basis_points) / Decimal(10_000)
    return int(gst.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def line_total_with_tax(line: dict[str, Any]) -> int:
    return line_total(line) + line_gst(line)


def quote_total(lines: list[dict[str, Any]]) -> int:
    subtotal = sum(line_total(line) for line in lines)
    return subtotal + sum(gst_by_slab(lines).values())


def gst_by_slab(lines: list[dict[str, Any]]) -> dict[int, int]:
    subtotals: dict[int, int] = {}
    for line in lines:
        slab = int(line.get("gst_bps", 0))
        subtotals[slab] = subtotals.get(slab, 0) + line_total(line)
    return {
        slab: int(
            (Decimal(subtotal) * Decimal(slab) / Decimal(10_000)).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        for slab, subtotal in subtotals.items()
    }


def format_inr(paise: int) -> str:
    rupees, cents = divmod(abs(paise), 100)
    digits = str(rupees)
    if len(digits) > 3:
        tail, prefix = digits[-3:], digits[:-3]
        groups: list[str] = []
        while prefix:
            groups.insert(0, prefix[-2:])
            prefix = prefix[:-2]
        digits = ",".join(groups + [tail])
    sign = "-" if paise < 0 else ""
    return f"{sign}₹{digits}" + (f".{cents:02d}" if cents else "")
