---
id: BENCH-11
title: Easter and movable holidays
state: Todo
labels: [task, ready-for-agent]
---
Add in `brdocs/holidays.py`:
- `easter(year: int) -> date` (Gregorian calendar);
- `movable_holidays(year: int) -> dict[str, date]` with exactly these keys: `carnaval_monday` (Easter - 48
  days), `carnaval_tuesday` (Easter - 47), `good_friday` (Easter - 2) and `corpus_christi` (Easter + 60).

## Acceptance criteria
- `easter(2025) == date(2025, 4, 20)`.
- `movable_holidays(2025)["corpus_christi"] == date(2025, 6, 19)`.
- Raises `ValueError` for years before 1583.

## Evals
- Unit tests for at least three different years and the error case.
