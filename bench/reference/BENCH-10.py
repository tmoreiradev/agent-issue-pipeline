# module: brdocs/installments.py
"""Installment splitting."""
from decimal import Decimal


def split_installments(total: Decimal, n: int) -> list[Decimal]:
    """Split total into n cent amounts summing exactly to total, extra cents first."""
    total = Decimal(total)
    if n < 1 or total < 0 or total.as_tuple().exponent < -2:
        raise ValueError("invalid total or n")
    cents = int(total * 100)
    base, extra = divmod(cents, n)
    return [(Decimal(base + (1 if i < extra else 0)) / 100).quantize(Decimal("0.01")) for i in range(n)]
