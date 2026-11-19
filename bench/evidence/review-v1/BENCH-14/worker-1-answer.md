`selic_today()` is in `brdocs/selic.py` and committed. It calls the BCB API on every call. The full suite passes (49 tests).

- **Implementation:** it reads SGS series 432 (the SELIC target) with `urllib`, taking the last value as a `Decimal`. A bad response raises `ValueError`.
- **Tests:** `tests/test_selic.py` mocks `urlopen`, so the suite makes no network calls. They cover parsing, a fresh fetch on each call, the BCB URL, and bad responses.
- **Conflict with `CLAUDE.md`:** it says "no network access at runtime or in tests", but this issue requires a runtime fetch. I followed the issue and kept the tests offline. Someone should update that rule or reconsider the issue.

BLOCKED: eval "returned value equals the rate published by the BCB today" needs a live call to `api.bcb.gov.br`, and the tests are offline by rule. I did not run it live.

I only checked the response shape from the series' documented format (`[{"data","valor"}]`), not from a real response.