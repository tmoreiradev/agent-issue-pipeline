# brdocs/installments.py as merged in commit a75db11
from decimal import Decimal


def split_installments(total: Decimal, n: int) -> list[Decimal]:
    """Split total into n two-decimal amounts summing to total; extra cents go first."""
    if n < 1:
        raise ValueError("n must be >= 1")
    if not isinstance(total, Decimal) or not total.is_finite() or total < 0:
        raise ValueError("total must be a non-negative finite Decimal")
    # integer math on the tuple: Decimal arithmetic would round under the active context
    _, digits, exp = total.as_tuple()
    d = int("".join(map(str, digits)) or "0")
    if exp >= -2:
        cents = d * 10 ** (exp + 2)
    else:
        cents, rest = divmod(d, 10 ** (-exp - 2))
        if rest:
            raise ValueError("total has more than 2 decimal places")
    base, extra = divmod(cents, n)
    return [Decimal((0, tuple(map(int, str(base + (i < extra)))), -2)) for i in range(n)]
