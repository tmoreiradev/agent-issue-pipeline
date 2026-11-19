# brdocs

Small helpers for Brazilian documents, money and dates.

- Python 3.11+, standard library only. No third-party packages, no network access at runtime or in tests.
- One module per feature under `brdocs/`, with its tests in `tests/test_<module>.py` (unittest).
- Run the checks with `python -m unittest discover -s tests -q`.
- Public functions get a one-line docstring. Invalid input raises `ValueError` unless the issue says otherwise.
