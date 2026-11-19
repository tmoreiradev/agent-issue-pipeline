`is_valid_pis` is added in `brdocs/pis.py`, with tests in `tests/test_pis.py`. The full suite passes (40 tests), and everything is committed as `feat(pis): add is_valid_pis (BENCH-08)`.

- **Accepted input:** formatted (`120.12345.67-2`) and unformatted values. Only `.` and `-` are stripped.
- **Invalid input:** wrong length, a wrong digit and non-digits all return `False`. Non-string input such as `None` or an int also returns `False`, and nothing raises.
- **Digit-0 rule:** tested with `12012345630` (remainder 1, so the result is 10 and becomes 0) and `12012345680` (remainder 0, so the result is 11 and becomes 0).
- **Evals:** `12012345672` is `True` and `12012345673` is `False`, both in the tests.

**Skipped:** I did not reject repeated-digit values like `00000000000`, since the issue doesn't ask for it. If the algorithm accepts one, it returns `True`.