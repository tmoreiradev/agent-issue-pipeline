Fixed both review findings and committed. 52 tests pass, tree clean.

- **Three-decimal totals:** `Decimal("1.500")` now raises `ValueError`. The check is `exponent < -2`, and `test_trailing_zeros_ok` is now a rejection test.
- **Large totals:** `Decimal("1E+28")` with `n=1` no longer raises `InvalidOperation`. The split now uses integer cents taken from the Decimal digits and exponent, and builds results as `Decimal(f"{cents}E-2")`. Neither step rounds in the Decimal context. New tests cover `1E+28`, `1E+30` and a context with `prec=5`.

I haven't confirmed the new tests fail on the old code. The `1E+30` sum check is done in integer cents, because summing Decimals rounds at 28 digits.

The `1E+30` test's integer-cents expression is clumsy. I left it as is.