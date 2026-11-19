---
id: BENCH-04
title: Normalize CEP
state: Todo
labels: [task, ready-for-agent]
---
Add `normalize_cep(value: str) -> str` in `brdocs/cep.py`.

## Acceptance criteria
- Removes `-`, `.` and spaces: `normalize_cep("01310-100") == "01310100"`.
- Raises `ValueError` unless the result is exactly 8 digits.

## Evals
- Unit tests for hyphen, dot, spaces, already-normalized input, too short and letters.
