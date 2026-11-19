`split_installments` is added in `brdocs/installments.py`, with tests in `tests/test_installments.py`. The full suite passes (63 tests), and the work is committed with no uncommitted changes.

It covers all three acceptance criteria. The tests cover an exact split, remainders, a total smaller than `n` cents and the error cases. I didn't run them against the old code to confirm they fail without the change, but the module didn't exist before, so every test depends on it.

I added two things you didn't ask for: a non-`Decimal` total and `NaN`/`Infinity` also raise `ValueError`. `n` is assumed to be an int and isn't type-checked.