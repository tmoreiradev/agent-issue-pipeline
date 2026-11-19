---
id: BENCH-13
title: Format CEP both ways
state: Todo
labels: [task, ready-for-agent]
---
Add `format_cep(value: str) -> str` in `brdocs/cep_format.py`.

## Acceptance criteria
- Always returns the CEP with a hyphen: `format_cep("01310100") == "01310-100"`.
- Always returns only digits, for storage: `format_cep("01310100") == "01310100"`.

## Evals
- Both assertions above pass in the same test run.
