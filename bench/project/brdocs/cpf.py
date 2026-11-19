"""CPF (Brazilian individual taxpayer id) validation."""

import re


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _check_digit(numbers: str) -> int:
    weight = len(numbers) + 1
    total = sum(int(n) * (weight - i) for i, n in enumerate(numbers))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def is_valid_cpf(value: str) -> bool:
    """True for a CPF with valid check digits, formatted (`123.456.789-09`) or not."""
    d = _digits(value)
    if len(d) != 11 or d == d[0] * 11:
        return False
    first = _check_digit(d[:9])
    second = _check_digit(d[:9] + str(first))
    return d[9:] == f"{first}{second}"
