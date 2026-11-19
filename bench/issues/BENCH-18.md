---
id: BENCH-18
title: Mask CPF for logs
state: Todo
labels: [ready-for-agent]
---
Add `mask_cpf(value: str) -> str` in `brdocs/mask.py` returning `***.982.247-**`.

## Acceptance criteria
- `mask_cpf("52998224725") == "***.982.247-**"`.

## Evals
- Unit test for the example above.
