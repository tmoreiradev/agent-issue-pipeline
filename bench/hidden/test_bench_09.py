"""Hidden acceptance test for BENCH-09: never shown to the agents."""
import unittest
from brdocs.cnpj_alnum import is_valid_cnpj_alnum

class Hidden(unittest.TestCase):
    def test_valid(self):
        for v in ("12.ABC.345/01DE-35", "12ABC34501DE35", "12abc34501de35", "11.222.333/0001-81"):
            self.assertTrue(is_valid_cnpj_alnum(v), v)
    def test_invalid(self):
        for v in ("12ABC34501DE36", "12ABC34501DEAB", "12ABC34501D35", "12ABC3450#DE35", "00000000000000",
                  "AAAAAAAAAAAAAA", ""):
            self.assertFalse(is_valid_cnpj_alnum(v), v)
