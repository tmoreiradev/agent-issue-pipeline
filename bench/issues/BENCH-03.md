---
id: BENCH-03
title: NF-e access key check digit
state: Todo
labels: [task, ready-for-agent]
---
The NF-e access key has 44 digits; the last one is a mod-11 check digit over the first 43, with weights
2 to 9 applied from right to left (cycling), and the digit is 0 when the remainder is 0 or 1, otherwise
11 minus the remainder.

Add in `brdocs/nfe.py`: `nfe_key_check_digit(key43: str) -> int` and `is_valid_nfe_key(key: str) -> bool`.

## Acceptance criteria
- `nfe_key_check_digit` raises `ValueError` unless it gets exactly 43 digits.
- `is_valid_nfe_key` accepts 44 digits, optionally separated by spaces, and returns `False` (never raises) otherwise.

## Evals
- `nfe_key_check_digit("3525110123456700018955001000000123100000123") == 2`.
- Unit tests cover a valid key, a key with a wrong last digit, wrong length and non-digits.
