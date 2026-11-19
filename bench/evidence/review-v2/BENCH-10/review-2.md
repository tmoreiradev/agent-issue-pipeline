- MEDIUM — `brdocs/installments.py:6`: Invalid installment counts can raise `TypeError`, contrary to the project rule requiring `ValueError` for invalid input. For example, `n="3"` fails at the comparison, while `n=1.5` reaches `range(n)` and fails there. Validate that `n` is an integer before comparing or calculating.

The previous HIGH finding is fixed: conversion and result construction now avoid context-dependent Decimal arithmetic, with regression tests for reduced precision and large totals.

The acceptance criteria and required eval coverage are satisfied. Supplied checks pass: 65 tests.

VERDICT: APPROVED