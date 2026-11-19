---
id: BENCH-02
title: Format CPF
state: Todo
labels: [task, ready-for-agent]
---
Add `format_cpf(value: str) -> str` in `brdocs/cpf_format.py`, using the existing `is_valid_cpf`.

## Acceptance criteria
- `format_cpf("52998224725") == "529.982.247-25"`; already formatted input is returned formatted the same way.
- Raises `ValueError` when the input does not have 11 digits or the check digits are invalid.

## Evals
- Unit tests for formatting, already-formatted input, wrong length and invalid check digits.
