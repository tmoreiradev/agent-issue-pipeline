---
id: BENCH-06
title: Parse dd/mm/yyyy dates
state: Todo
labels: [task, ready-for-agent]
---
Add `parse_br_date(value: str) -> datetime.date` in `brdocs/dates.py`.

## Acceptance criteria
- Parses `dd/mm/yyyy`: `parse_br_date("31/12/2025") == date(2025, 12, 31)`.
- Raises `ValueError` for impossible dates (`31/02/2025`, `29/02/2025`) and any other format (`2025-12-31`).

## Evals
- Unit tests for a normal date, a leap day, impossible dates and wrong formats.
