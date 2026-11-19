"""Hidden acceptance test for BENCH-02: never shown to the agents."""
import unittest
from brdocs.cpf_format import format_cpf

class Hidden(unittest.TestCase):
    def test_format(self):
        self.assertEqual(format_cpf("52998224725"), "529.982.247-25")
        self.assertEqual(format_cpf("529.982.247-25"), "529.982.247-25")
    def test_errors(self):
        for v in ("123", "52998224724", "11111111111", ""):
            with self.assertRaises(ValueError):
                format_cpf(v)
