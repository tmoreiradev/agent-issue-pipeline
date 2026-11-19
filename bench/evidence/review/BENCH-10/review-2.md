- MEDIUM — `brdocs/installments.py:17`: Valid input `split_installments(Decimal("1E+4300"), 1)` raises `ValueError` under Python’s default 4,300-digit integer-to-string limit when formatting `base`. Line 15 similarly fails for coefficients exceeding that limit. This leaves the return-value acceptance criterion unmet. Build integer cents directly from digits and construct results with Decimal tuples, avoiding large integer/string conversions; add regression coverage.

Both previous findings were fixed for their reported cases. Recorded checks pass: 52 tests.

VERDICT: REJECTED