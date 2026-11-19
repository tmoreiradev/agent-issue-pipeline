---
id: BENCH-05
title: Format Brazilian money
state: Todo
labels: [task, ready-for-agent]
---
Add `format_brl(value: Decimal) -> str` in `brdocs/money.py`.

## Acceptance criteria
- `format_brl(Decimal("1234.5")) == "R$ 1.234,50"`; thousands separated by `.`, decimals by `,`.
- Negative values: `format_brl(Decimal("-1234.5")) == "-R$ 1.234,50"`.
- Rounds to 2 places with ROUND_HALF_UP: `format_brl(Decimal("0.125")) == "R$ 0,13"`.

## Evals
- Unit tests for zero, thousands, millions, negatives and the half-up case.
