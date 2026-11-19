---
id: BENCH-08
title: PIS/PASEP validation
state: Todo
labels: [task, ready-for-agent]
---
Add `is_valid_pis(value: str) -> bool` in `brdocs/pis.py`.

PIS/PASEP has 11 digits. The check digit uses weights 3,2,9,8,7,6,5,4,3,2 over the first 10 digits:
digit = 11 - (sum % 11), and becomes 0 when that result is 10 or 11.

## Acceptance criteria
- Accepts formatted (`120.12345.67-2`) and unformatted input.
- Returns `False` (never raises) for wrong length, wrong digit or non-digits.

## Evals
- `is_valid_pis("12012345672")` is `True`; `is_valid_pis("12012345673")` is `False`.
- Unit tests cover the digit-0 rule, formatted input and wrong length.
