from decimal import ROUND_HALF_UP, Decimal

from app.models.quote import QuoteItem
from app.schemas.quote import QuoteItemIn


TWO = Decimal("0.01")


def calc_line_total(qty: Decimal, unit_price: Decimal, discount_pct: Decimal) -> Decimal:
    return (qty * unit_price * (1 - discount_pct / 100)).quantize(TWO, ROUND_HALF_UP)


def calc_totals(items: list[QuoteItem]) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum((i.line_total for i in items), Decimal("0.00"))
    vat_total = sum(
        (i.line_total * i.vat_rate / 100).quantize(TWO, ROUND_HALF_UP) for i in items
    )
    return subtotal, vat_total, subtotal + vat_total


def build_item(item: QuoteItemIn, position: int) -> dict:
    """Berechnet line_total für eine einzelne Position."""
    line_total = calc_line_total(item.qty, item.unit_price, item.discount_pct)
    return {
        "position": item.position if item.position is not None else position,
        "description": item.description,
        "qty": item.qty,
        "unit": item.unit,
        "unit_price": item.unit_price,
        "discount_pct": item.discount_pct,
        "vat_rate": item.vat_rate,
        "line_total": line_total,
        "material_id": item.material_id,
    }


def build_items(raw: list[QuoteItemIn]) -> list[dict]:
    return [build_item(item, idx + 1) for idx, item in enumerate(raw)]
