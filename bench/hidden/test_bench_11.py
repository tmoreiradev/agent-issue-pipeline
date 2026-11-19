"""Hidden acceptance test for BENCH-11: never shown to the agents."""
import unittest
from datetime import date
from brdocs.holidays import easter, movable_holidays

class Hidden(unittest.TestCase):
    def test_easter(self):
        for y, d in ((2019, date(2019, 4, 21)), (2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)),
                     (2026, date(2026, 4, 5)), (2038, date(2038, 4, 25))):
            self.assertEqual(easter(y), d)
    def test_movable(self):
        self.assertEqual(movable_holidays(2026), {
            "carnaval_monday": date(2026, 2, 16), "carnaval_tuesday": date(2026, 2, 17),
            "good_friday": date(2026, 4, 3), "corpus_christi": date(2026, 6, 4)})
        self.assertEqual(movable_holidays(2019)["carnaval_monday"], date(2019, 3, 4))
    def test_error(self):
        with self.assertRaises(ValueError):
            easter(1500)
