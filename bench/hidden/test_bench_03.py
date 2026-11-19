"""Hidden acceptance test for BENCH-03: never shown to the agents."""
import unittest
from brdocs.nfe import nfe_key_check_digit, is_valid_nfe_key

K1 = "3525110123456700018955001000000123100000123"
K2 = "4123120612345600019855002000000456123456789"

class Hidden(unittest.TestCase):
    def test_digit(self):
        self.assertEqual(nfe_key_check_digit(K1), 2)
        self.assertEqual(nfe_key_check_digit(K2), 0)
        for bad in ("123", K1 + "1", "x" * 43):
            with self.assertRaises(ValueError):
                nfe_key_check_digit(bad)
    def test_key(self):
        self.assertTrue(is_valid_nfe_key(K1 + "2"))
        self.assertTrue(is_valid_nfe_key(" ".join([(K1 + "2")[i:i + 4] for i in range(0, 44, 4)])))
        self.assertFalse(is_valid_nfe_key(K1 + "3"))
        self.assertFalse(is_valid_nfe_key(K1))
        self.assertFalse(is_valid_nfe_key("a" * 44))
