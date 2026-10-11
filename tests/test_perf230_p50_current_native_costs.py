"""PERF230 P5.0 safety invariants for single exposed seed0 cost profiler."""
import inspect
import unittest

from benchmarks import perf230_p50_current_native_costs as subject


class P50CostProbeGuardTests(unittest.TestCase):
    def test_never_executes_reserved_study_seed(self):
        self.assertEqual(subject.ORIGINAL_BENCHMARK_SEED,0)
        self.assertEqual(len(subject.FROZEN_SELECTED128_FIRST),64)
        src=inspect.getsource(subject.main)
        self.assertNotIn("--seed",src)

    def test_same_full_selected128_original_authoritative_frozen_digest(self):
        self.assertEqual(subject.FROZEN_SELECTED128_FIRST,
                         "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63")

if __name__=="__main__":
    unittest.main()
