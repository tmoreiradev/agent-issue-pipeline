Fixed the review finding. `split_installments(Decimal("1E+4300"), 1)` now returns a result instead of raising `ValueError`. All 53 tests pass, and the work is committed as `b3ef22a` with nothing left uncommitted.

- **Cause:** the old code turned the digit tuple into a string and an int, and later turned `base` into a string, all of which hit Python's 4,300-digit limit.
- **Cents:** they are now built from the digit tuple with `reduce`, with no string step.
- **Results:** each amount is `Decimal(int).scaleb(-2)` using a local `Context`. That context's precision is `len(digits) + max(exp, 0) + 4`, so it is exact and ignores the caller's precision.
- **Test:** I added `test_huge_total_beyond_int_str_limit`, which covers `1E+4300` split in 1 and `1E+5000` split in 3. The old code raised `ValueError` on the first case, so it fails without the fix. I didn't run it against the old code.

My first attempt set the precision from the coefficient length only. That silently truncated `1E+5000`, and the new test caught it, so the exponent is now included.

Very large totals are slow: the digit-to-int step is O(n²), which I accepted for inputs this rare.