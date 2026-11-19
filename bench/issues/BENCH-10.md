---
id: BENCH-10
title: Split an amount into installments
state: Todo
labels: [task, ready-for-agent]
---
Add `split_installments(total: Decimal, n: int) -> list[Decimal]` in `brdocs/installments.py`.

## Acceptance criteria
- Returns `n` amounts with exactly 2 decimal places whose sum is exactly `total`.
- Amounts differ by at most one cent; the extra cents go to the first installments:
  `split_installments(Decimal("100.00"), 3) == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]`.
- Raises `ValueError` for `n < 1`, a negative total, or a total with more than 2 decimal places.

## Evals
- Unit tests for an exact split, remainders, a total smaller than `n` cents and the error cases.
