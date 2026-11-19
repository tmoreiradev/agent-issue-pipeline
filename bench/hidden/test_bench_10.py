"""Hidden acceptance test for BENCH-10: never shown to the agents."""
import unittest
from decimal import Decimal
from brdocs.installments import split_installments

def two_places(amounts):
    return all(x.as_tuple().exponent == -2 for x in amounts)


class Hidden(unittest.TestCase):
    def test_exactly_two_decimal_places(self):
        for total, n in (("100.00", 3), ("0.05", 3), ("0.02", 4), ("1234.57", 7), ("10", 1), ("0", 2)):
            self.assertTrue(two_places(split_installments(Decimal(total), n)), (total, n))

    def test_split(self):
        self.assertEqual(split_installments(Decimal("100.00"), 3),
                         [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])
        self.assertEqual(split_installments(Decimal("0.05"), 3), [Decimal("0.02"), Decimal("0.02"), Decimal("0.01")])
        self.assertEqual(split_installments(Decimal("0.02"), 4),
                         [Decimal("0.01"), Decimal("0.01"), Decimal("0.00"), Decimal("0.00")])
        r = split_installments(Decimal("1234.57"), 7)
        self.assertEqual(sum(r), Decimal("1234.57"))
        self.assertTrue(all(x.as_tuple().exponent == -2 for x in r))
        self.assertLessEqual(max(r) - min(r), Decimal("0.01"))
        self.assertEqual(split_installments(Decimal("10"), 1), [Decimal("10.00")])
    def test_errors(self):
        for total, n in ((Decimal("10"), 0), (Decimal("-1"), 2), (Decimal("1.001"), 2), (Decimal("1.500"), 2)):
            with self.assertRaises(ValueError):
                split_installments(total, n)
