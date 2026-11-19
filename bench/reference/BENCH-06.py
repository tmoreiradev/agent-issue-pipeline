# module: brdocs/dates.py
"""Brazilian date parsing."""
import datetime as dt
import re


def parse_br_date(value: str) -> dt.date:
    """Parse dd/mm/yyyy."""
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value or ""):
        raise ValueError(f"expected dd/mm/yyyy: {value!r}")
    d, m, y = (int(x) for x in value.split("/"))
    return dt.date(y, m, d)
