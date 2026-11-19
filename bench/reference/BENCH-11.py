# module: brdocs/holidays.py
"""Easter and Brazilian movable holidays."""
from datetime import date, timedelta


def easter(year: int) -> date:
    """Gregorian Easter Sunday (anonymous algorithm)."""
    if year < 1583:
        raise ValueError("Gregorian calendar only")
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def movable_holidays(year: int) -> dict[str, date]:
    """Carnaval, Good Friday and Corpus Christi for the year."""
    e = easter(year)
    return {"carnaval_monday": e - timedelta(48), "carnaval_tuesday": e - timedelta(47),
            "good_friday": e - timedelta(2), "corpus_christi": e + timedelta(60)}
