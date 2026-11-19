---
id: BENCH-09
title: Alphanumeric CNPJ (2026 format)
state: Todo
labels: [task, ready-for-agent]
---
From July 2026 the CNPJ can be alphanumeric: the first 12 characters may be digits or uppercase letters,
the last 2 (check digits) stay numeric. Each character's value is its ASCII code minus 48 (so `0`-`9`
keep their value and `A` is 17), and the check digits use the same mod-11 weights as the numeric CNPJ.

Add `is_valid_cnpj_alnum(value: str) -> bool` in `brdocs/cnpj_alnum.py`.

## Acceptance criteria
- `is_valid_cnpj_alnum("12.ABC.345/01DE-35")` is `True` (the Receita Federal example).
- Letters are case-insensitive; `.`, `/` and `-` are ignored.
- Purely numeric CNPJs keep working: `is_valid_cnpj_alnum("11.222.333/0001-81")` is `True`.
- Returns `False` (never raises) for letters in the check digits, wrong length, other symbols or all-equal characters.

## Evals
- Unit tests for the official example, a numeric CNPJ, lowercase input, a wrong check digit and letters in the check digits.
