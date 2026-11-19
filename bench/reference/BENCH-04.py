# module: brdocs/cep.py
"""CEP normalization."""
import re


def normalize_cep(value: str) -> str:
    """Strip separators and return the 8-digit CEP."""
    d = re.sub(r"[-.\s]", "", value or "")
    if not re.fullmatch(r"\d{8}", d):
        raise ValueError(f"invalid CEP: {value!r}")
    return d
