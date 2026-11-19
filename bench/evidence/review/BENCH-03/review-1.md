- **HIGH — `tests/test_nfe.py:13`**: The invalid-input cases include `"1" * 43`, which satisfies the required input format. `nfe_key_check_digit` correctly returns `2`, so `assertRaises(ValueError)` fails. Remove this case from the invalid-input list and assert that it returns `2` instead. The supplied checks report success, but that result is inconsistent with this diff.

VERDICT: REJECTED