`split_installments` is in `brdocs/installments.py` and committed as `feat(installments): add split_installments (BENCH-10)`. The full suite passes (50 tests) and the tree is clean.

- **Splitting:** it works in integer cents with `divmod`, so the sum is exact. The extra cents go to the first installments, and `split_installments(Decimal("100.00"), 3)` gives `[33.34, 33.33, 33.33]`.
- **Errors:** it raises `ValueError` for `n < 1`, a negative total, and a total with more than 2 decimal places.
- **Tests:** `tests/test_installments.py` covers an exact split, remainders, a total smaller than `n` cents, and the error cases.
- **Beyond the issue:** it also rejects NaN, infinity, a non-`Decimal` total, and a non-int or bool `n`. `Decimal("1.500")` is accepted because it is still a 2-decimal amount.

I didn't run the tests against the code without my change. The acceptance tests all import the new module, so they can't pass without it.