# module: brdocs/cnpj_alnum.py
"""Alphanumeric CNPJ validation (2026 format)."""
import re


def _dv(values):
    weights = (list(range(2, 10)) * 2)[: len(values)]
    rest = sum(v * w for v, w in zip(reversed(values), weights, strict=True)) % 11
    return 0 if rest < 2 else 11 - rest


def is_valid_cnpj_alnum(value: str) -> bool:
    """True for a numeric or alphanumeric CNPJ with valid check digits."""
    d = re.sub(r"[./-]", "", value or "").upper()
    if not re.fullmatch(r"[0-9A-Z]{12}\d{2}", d) or d == d[0] * 14:
        return False
    vals = [ord(c) - 48 for c in d[:12]]
    first = _dv(vals)
    return d[12:] == f"{first}{_dv(vals + [first])}"
