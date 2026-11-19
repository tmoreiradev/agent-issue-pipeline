"""Hidden acceptance test for BENCH-04: never shown to the agents."""
import unittest
from brdocs.cep import normalize_cep

class Hidden(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(normalize_cep("01310-100"), "01310100")
        self.assertEqual(normalize_cep("01.310-100"), "01310100")
        self.assertEqual(normalize_cep(" 01310 100 "), "01310100")
        self.assertEqual(normalize_cep("01310100"), "01310100")
    def test_errors(self):
        for v in ("1310-100", "013101000", "abcde-fgh", ""):
            with self.assertRaises(ValueError):
                normalize_cep(v)
