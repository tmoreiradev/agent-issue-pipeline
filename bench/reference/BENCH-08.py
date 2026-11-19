# module: brdocs/pis.py
"""PIS/PASEP validation."""
import re


def is_valid_pis(value: str) -> bool:
    """True for a PIS/PASEP with a valid check digit."""
    d = re.sub(r"[./-]", "", value or "")
    if not re.fullmatch(r"\d{11}", d):
        return False
    total = sum(int(c) * w for c, w in zip(d[:10], (3, 2, 9, 8, 7, 6, 5, 4, 3, 2), strict=True))
    digit = 11 - total % 11
    return int(d[10]) == (0 if digit >= 10 else digit)
