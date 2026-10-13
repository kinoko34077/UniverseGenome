"""#326: exact uniform occupancy theoretical-only contract and limits."""
from fractions import Fraction
import unittest

from research.a18_geometry_null_326 import (
    expected_complete_2x2_blocks,
    expected_complete_2x2_counts_for_marginals,
    conservative_uniform_null_upper_bound,
)


class GeometricNullContract(unittest.TestCase):
    def test_exact_toroidal_block_expected_value(self):
        self.assertEqual(expected_complete_2x2_blocks(0),Fraction(0,1))
        self.assertEqual(expected_complete_2x2_blocks(3),Fraction(0,1))
        self.assertEqual(expected_complete_2x2_blocks(1024),Fraction(1024,1))
        self.assertAlmostEqual(float(expected_complete_2x2_blocks(32)),
                               0.000808497447570073,places=15)
        self.assertAlmostEqual(float(expected_complete_2x2_blocks(27)),
                               0.00039458092894479376,places=15)
        self.assertAlmostEqual(float(expected_complete_2x2_blocks(22)),
                               0.00016446492850320034,places=15)
        self.assertAlmostEqual(float(expected_complete_2x2_blocks(11)),
                               0.000007419470458790993,places=16)
        self.assertEqual(expected_complete_2x2_blocks(4),
                         Fraction(1024,1) / 88584268800)

    def test_sum_and_conditional_per_step_upper(self):
        expected=(
            expected_complete_2x2_blocks(32)
            +expected_complete_2x2_blocks(27)
            +expected_complete_2x2_blocks(11)
        )
        self.assertEqual(expected_complete_2x2_counts_for_marginals((32,27,11)),expected)
        self.assertEqual(conservative_uniform_null_upper_bound(32,1000),
                         expected_complete_2x2_blocks(32)*1000)
        self.assertLess(float(conservative_uniform_null_upper_bound(32,1000)),1)
        self.assertEqual(conservative_uniform_null_upper_bound(32,0),0)

    def test_monotone_and_input_contract(self):
        last=Fraction(0,1)
        for n in range(1025):
            now=expected_complete_2x2_blocks(n)
            self.assertGreaterEqual(now,last)
            last=now
        for n in (-1,1025,1.5,True):
            with self.subTest(n=n),self.assertRaises(ValueError):
                expected_complete_2x2_blocks(n)
        for side in (0,1,2,3.5,True):
            with self.subTest(side=side),self.assertRaises(ValueError):
                expected_complete_2x2_blocks(4,side=side)
        for steps in (-1,1.5,True):
            with self.subTest(steps=steps),self.assertRaises(ValueError):
                conservative_uniform_null_upper_bound(32,steps)
        self.assertEqual(expected_complete_2x2_blocks(9,side=3),9)


if __name__=="__main__":
    unittest.main()
