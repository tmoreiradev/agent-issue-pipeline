---
id: BENCH-14
title: Today's SELIC rate
state: Todo
labels: [task, ready-for-agent]
---
Add `selic_today() -> Decimal` in `brdocs/selic.py` returning today's SELIC target rate.

## Acceptance criteria
- Fetches the rate from the Banco Central do Brasil API every time it is called.

## Evals
- The returned value equals the rate published by the Banco Central today.
