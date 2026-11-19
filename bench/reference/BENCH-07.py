# module: brdocs/business_days.py
"""Business day arithmetic."""
from datetime import date, timedelta


def add_business_days(start: date, n: int, holidays=frozenset()) -> date:
    """Move forward n business days, skipping weekends and holidays."""
    if n < 0:
        raise ValueError("n must be >= 0")
    day = start
    while n:
        day += timedelta(days=1)
        if day.weekday() < 5 and day not in holidays:
            n -= 1
    return day
