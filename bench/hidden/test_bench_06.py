"""Hidden acceptance test for BENCH-06: never shown to the agents."""
import unittest
from datetime import date
from brdocs.dates import parse_br_date

class Hidden(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(parse_br_date("31/12/2025"), date(2025, 12, 31))
        self.assertEqual(parse_br_date("29/02/2024"), date(2024, 2, 29))
        self.assertEqual(parse_br_date("01/01/2000"), date(2000, 1, 1))
    def test_errors(self):
        for v in ("31/02/2025", "29/02/2025", "2025-12-31", "31-12-2025", "32/01/2025", ""):
            with self.assertRaises(ValueError):
                parse_br_date(v)
