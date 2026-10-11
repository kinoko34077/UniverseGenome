"""P5.3 source active-slot scan sampling must not alter science."""
import unittest
from benchmarks.perf230_p53_active_scan_distribution import (
    CATEGORY_REPRESENTATIVES,SEED,FROZEN_SLOT0,
)

class SourceNativeScanCoverage(unittest.TestCase):
    def test_existing_exposed_seed_and_all_native_category_representatives(self):
        self.assertEqual(SEED,0)
        self.assertEqual(CATEGORY_REPRESENTATIVES,(0,32,64,96))
        self.assertEqual(FROZEN_SLOT0,
            "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1")

if __name__=="__main__":
    unittest.main()
