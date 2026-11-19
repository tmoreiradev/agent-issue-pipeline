Fixed the review finding. All 65 tests pass and the tree is clean. There are two commits: the fix, then a correction to my own large-total test.

`split_installments` no longer uses `scaleb`. It now takes the digits and exponent from `total.as_tuple()` and does the arithmetic in integers. A non-zero remainder past 2 decimal places raises `ValueError`. Results are built from Decimal tuples with exponent -2, so the active decimal context can't round anything.

I added two regression tests in `tests/test_installments.py`:
- **Reduced precision:** with context precision 2, `split_installments(D("1.01"), 1)` gives `"1.01"`. The 100/3 split is unchanged, and `1.001` still raises.
- **Large total:** `123456789012345678901234567890.12` split 7 ways has parts that sum exactly to the total in cents, and each part has exactly 2 decimal places.

I didn't run the new tests against the old `scaleb` code to confirm they fail there.

Not handled: a total with a huge exponent, like `Decimal("1E+999999999")`, would build an enormous integer. I left it as a known limit.