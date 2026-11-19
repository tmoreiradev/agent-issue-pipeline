---
id: BENCH-01
title: CNPJ validation
state: Todo
labels: [task, ready-for-agent]
---
Add `is_valid_cnpj(value: str) -> bool` in `brdocs/cnpj.py`.

## Acceptance criteria
- Accepts formatted (`11.222.333/0001-81`) and unformatted (`11222333000181`) input.
- Validates both check digits with the official mod-11 weights.
- Returns `False` (never raises) for wrong length, wrong check digits or all-equal digits (`00000000000000`).

## Evals
- `is_valid_cnpj("11.222.333/0001-81")` is `True`; `is_valid_cnpj("11.222.333/0001-80")` is `False`.
- Unit tests cover valid, invalid digits, wrong length and repeated digits.
