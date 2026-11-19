- HIGH — `brdocs/installments.py:10`: `Decimal.scaleb()` uses the active decimal context and can round before validation. With context precision 2, `split_installments(Decimal("1.01"), 1)` produces `Decimal("1.0")`, losing one cent and returning only one decimal place. Large totals can also round under the default context. Convert to integer cents and construct results using context-independent Decimal tuple operations; add regression coverage for reduced precision and large totals.

The supplied checks pass: 63 tests. The required basic test cases are present, but exactness remains unmet.

VERDICT: REJECTED