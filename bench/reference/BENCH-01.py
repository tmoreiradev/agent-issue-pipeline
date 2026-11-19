# module: brdocs/cnpj.py
"""CNPJ validation."""
import re


def _dv(values):
    weights = (list(range(2, 10)) * 2)[: len(values)]
    total = sum(v * w for v, w in zip(reversed(values), weights, strict=True))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def is_valid_cnpj(value: str) -> bool:
    """True for a numeric CNPJ with valid check digits."""
    d = re.sub(r"[./-]", "", value or "")
    if not re.fullmatch(r"\d{14}", d) or d == d[0] * 14:
        return False
    nums = [int(c) for c in d]
    first = _dv(nums[:12])
    return nums[12] == first and nums[13] == _dv(nums[:12] + [first])
