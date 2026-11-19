"""Hidden acceptance test for BENCH-08: never shown to the agents."""
import unittest
from brdocs.pis import is_valid_pis

class Hidden(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(is_valid_pis("12012345672"))
        self.assertTrue(is_valid_pis("120.12345.67-2"))
        self.assertTrue(is_valid_pis("17009876540"))
    def test_invalid(self):
        for v in ("12012345673", "1201234567", "17009876541", "abcdefghijk", ""):
            self.assertFalse(is_valid_pis(v), v)
