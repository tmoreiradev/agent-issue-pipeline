# module: brdocs/money.py
"""Brazilian money formatting."""
from decimal import ROUND_HALF_UP, Decimal


def format_brl(value: Decimal) -> str:
    """Format as R$ 1.234,50 (negative: -R$ 1.234,50), rounding half up."""
    q = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    text = f"{abs(q):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}R$ {text}"
