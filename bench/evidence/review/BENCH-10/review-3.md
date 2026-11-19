- HIGH — `brdocs/installments.py:18–19`: `split_installments(Decimal("1E+1000000"), 1)` raises `decimal.Overflow`: the new `Context` increases precision but retains the default `Emax=999999`. This valid total therefore fails the return-value acceptance criterion. Construct each result directly from a Decimal tuple with exponent `-2`, avoiding context-dependent scaling, and add regression coverage.

The previous integer-to-string limit finding is fixed. Recorded checks pass: 53 tests.

VERDICT: REJECTED