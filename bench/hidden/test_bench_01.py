"""Hidden acceptance test for BENCH-01: never shown to the agents."""
import unittest
from brdocs.cnpj import is_valid_cnpj

class Hidden(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(is_valid_cnpj("11.222.333/0001-81"))
        self.assertTrue(is_valid_cnpj("11222333000181"))
    def test_invalid(self):
        for v in ("11.222.333/0001-80", "11222333000182", "00000000000000", "1122233300018", "", "abc"):
            self.assertFalse(is_valid_cnpj(v), v)
