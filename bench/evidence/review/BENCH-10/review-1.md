- MEDIUM — `brdocs/installments.py:11`: `Decimal("1.500")` is accepted despite having three decimal places, violating the explicit validation criterion. `test_trailing_zeros_ok` enforces this conflicting behavior. Reject totals whose `as_tuple().exponent < -2` and update that test to expect `ValueError`.

- MEDIUM — `brdocs/installments.py:11`: A valid total such as `Decimal("1E+28")` with `n=1` raises `decimal.InvalidOperation` because `quantize` exceeds the default context precision. This leaves the return-value criterion unmet for valid inputs. Convert to integer cents using the Decimal coefficient and exponent, and construct results without context-dependent rounding; add coverage for large totals and reduced precision.

VERDICT: REJECTED