# module: brdocs/nfe.py
"""NF-e access key check digit."""
import re


def nfe_key_check_digit(key43: str) -> int:
    """Mod-11 check digit of the first 43 digits of an NF-e key."""
    if not re.fullmatch(r"\d{43}", key43 or ""):
        raise ValueError("expected 43 digits")
    weights = list(range(2, 10)) * 6
    total = sum(int(c) * weights[i] for i, c in enumerate(reversed(key43)))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def is_valid_nfe_key(key: str) -> bool:
    """True for a 44-digit NF-e key (spaces allowed) with a valid check digit."""
    d = (key or "").replace(" ", "")
    if not re.fullmatch(r"\d{44}", d):
        return False
    return nfe_key_check_digit(d[:43]) == int(d[43])
