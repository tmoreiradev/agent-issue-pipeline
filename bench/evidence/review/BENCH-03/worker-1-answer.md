BENCH-03 is done and committed: `nfe_key_check_digit` and `is_valid_nfe_key` are in `brdocs/nfe.py`. The full suite passes (16 tests), including the eval `nfe_key_check_digit("3525110123456700018955001000000123100000123") == 2`. I didn't re-run the new tests against the pre-change code to confirm they fail without it. The new module and test file don't exist before this commit, so the tests can't pass there.

Tests are in `tests/test_nfe.py`. They cover a valid key, a valid key with spaces, a wrong last digit, wrong length and non-digits.

Only the ASCII digits 0-9 count as digits, so full-width digits like `１` are rejected. `is_valid_nfe_key` also returns `False` for non-string input.

Not checked: the check-digit rule against any key other than the eval one. Only spaces are accepted as separators. Dots and dashes make a key invalid.