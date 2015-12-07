import unittest
from ..models import Unit

class UnitTest(unittest.TestCase):

    def test_get_year_simple(self):
        self.assertEqual(Unit("COMP10120", "Name").get_year(), 1)
        self.assertEqual(Unit("COMP20120", "Name").get_year(), 2)

    def test_get_year_non_comp(self):
        self.assertEqual(Unit("BMAN30120", "Name").get_year(), 3)

if __name__ == '__main__':
    unittest.main()