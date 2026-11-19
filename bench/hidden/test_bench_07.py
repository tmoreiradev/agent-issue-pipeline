"""Hidden acceptance test for BENCH-07: never shown to the agents."""
import unittest
from datetime import date
from brdocs.business_days import add_business_days

class Hidden(unittest.TestCase):
    def test_days(self):
        self.assertEqual(add_business_days(date(2025, 11, 14), 1), date(2025, 11, 17))
        self.assertEqual(add_business_days(date(2025, 11, 14), 1, {date(2025, 11, 17)}), date(2025, 11, 18))
        self.assertEqual(add_business_days(date(2025, 11, 15), 1), date(2025, 11, 17))
        self.assertEqual(add_business_days(date(2025, 11, 10), 5), date(2025, 11, 17))
        self.assertEqual(add_business_days(date(2025, 11, 14), 0), date(2025, 11, 14))
    def test_negative(self):
        with self.assertRaises(ValueError):
            add_business_days(date(2025, 11, 14), -1)
