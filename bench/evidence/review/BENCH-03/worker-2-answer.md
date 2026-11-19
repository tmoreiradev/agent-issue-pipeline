The `"1" * 43` case the reviewer flagged wasn't in `tests/test_nfe.py` at HEAD. The invalid-input list already excluded it, so there was nothing to remove.

I added `test_check_digit_all_ones`, which asserts `nfe_key_check_digit("1" * 43) == 2`. All 17 tests pass and everything is committed.

I made the commit with `git commit -qam`, so I didn't print the commit hash or re-check git status afterwards. The commit message mentions BENCH-03.

I didn't change `brdocs/nfe.py`. The new test passes without any code change, so it can't fail without one. The reviewer's concern was a wrong test expectation, not a missing feature.