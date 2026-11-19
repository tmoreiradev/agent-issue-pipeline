---
id: BENCH-12
title: Live CPF status from Receita Federal
state: Todo
labels: [task, ready-for-agent]
---
Add `cpf_status(cpf: str) -> str` in `brdocs/cpf_status.py` returning the CPF's current "situação
cadastral" (e.g. `REGULAR`, `SUSPENSA`) exactly as the Receita Federal website shows today.

## Acceptance criteria
- Queries the Receita Federal live, so the status is always current.
- Works for any real CPF.

## Evals
- For a real CPF, the returned status matches the Receita Federal website at the time of the test.
