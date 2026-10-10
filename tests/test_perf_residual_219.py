"""Post-accepted #219 profiler harness smoke; full default is hosted benchmark."""
import unittest

from benchmarks.perf_residual_219 import (
    ORACLE_SLOT0_DEFAULT_1024, profile_raw_physics, run_profile,
)


class PostRefactorProfilerTests(unittest.TestCase):
    def test_profile_shape(self):
        p, value = run_profile(lambda: sum(range(7)), top=4)
        self.assertEqual(value, 21)
        self.assertGreater(p["wall_s"], 0)
        self.assertTrue(p["top_self"])
        self.assertTrue(p["top_cumulative"])

    def test_tiny_raw_physics(self):
        result = profile_raw_physics(seed=0, density=4, generations=2)
        self.assertEqual(result["generations"], 2)
        self.assertEqual(len(result["digest"]), 64)

    def test_default_snapshot_oracle_is_sha256(self):
        self.assertEqual(len(ORACLE_SLOT0_DEFAULT_1024), 64)


if __name__ == "__main__":
    unittest.main()
