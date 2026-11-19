---
id: BENCH-07
title: Add business days
state: Todo
labels: [task, ready-for-agent]
---
Add `add_business_days(start: date, n: int, holidays: set[date] | frozenset[date] = frozenset()) -> date`
in `brdocs/business_days.py`.

## Acceptance criteria
- Moves forward `n` business days, skipping Saturdays, Sundays and dates in `holidays`.
- `n == 0` returns `start` unchanged; negative `n` raises `ValueError`.
- `add_business_days(date(2025, 11, 14), 1) == date(2025, 11, 17)` (Friday to Monday).

## Evals
- Unit tests for weekends, a holiday in the way, `n == 0`, starting on a weekend and negative `n`.
