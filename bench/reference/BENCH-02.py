# module: brdocs/cpf_format.py
"""CPF formatting."""
import re

from brdocs.cpf import is_valid_cpf


def format_cpf(value: str) -> str:
    """Format a valid CPF as 000.000.000-00."""
    d = re.sub(r"\D", "", value or "")
    if len(d) != 11 or not is_valid_cpf(d):
        raise ValueError(f"invalid CPF: {value!r}")
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
