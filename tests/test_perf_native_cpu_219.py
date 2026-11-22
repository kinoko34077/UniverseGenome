"""Fast validation for #219 benchmark harness, without extended science."""
import unittest

from benchmarks.perf_native_cpu_219 import (
    SHORT_TIMEOUT, TEST_SEED, physics_case, profile_call,
)


class NativePerfPilotTests(unittest.TestCase):
    def test_fixed_test_only_envelope(self):
        self.assertEqual(TEST_SEED, 0)
        self.assertEqual(SHORT_TIMEOUT, 2)

    def test_profile_record_counts_real_calls(self):
        p, result = profile_call("simple", lambda: sum(range(10)))
        self.assertEqual(result, 45)
        self.assertGreater(p["function_calls"], 0)
        self.assertGreaterEqual(p["wall_seconds"], 0)
        self.assertTrue(p["top_cumulative"])

    def test_physics_test_case_has_stable_structural_bounds(self):
        p = physics_case(4, 2)
        self.assertEqual(p["physical_generations"], 2)
        self.assertEqual(p["final_generation"], 2)
        self.assertEqual(len(p["final_state_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
