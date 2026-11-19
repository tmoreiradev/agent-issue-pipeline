"""Hidden acceptance test for BENCH-05: never shown to the agents."""
import unittest
from decimal import Decimal
from brdocs.money import format_brl

class Hidden(unittest.TestCase):
    def test_format(self):
        self.assertEqual(format_brl(Decimal("1234.5")), "R$ 1.234,50")
        self.assertEqual(format_brl(Decimal("0")), "R$ 0,00")
        self.assertEqual(format_brl(Decimal("1234567.891")), "R$ 1.234.567,89")
        self.assertEqual(format_brl(Decimal("999.999")), "R$ 1.000,00")
        self.assertEqual(format_brl(Decimal("-1234.5")), "-R$ 1.234,50")
    def test_half_up(self):
        self.assertEqual(format_brl(Decimal("0.125")), "R$ 0,13")
        self.assertEqual(format_brl(Decimal("2.675")), "R$ 2,68")
