import unittest

from brdocs.cpf import is_valid_cpf


class TestCpf(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(is_valid_cpf("529.982.247-25"))
        self.assertTrue(is_valid_cpf("52998224725"))

    def test_invalid(self):
        self.assertFalse(is_valid_cpf("529.982.247-24"))
        self.assertFalse(is_valid_cpf("111.111.111-11"))
        self.assertFalse(is_valid_cpf("123"))
