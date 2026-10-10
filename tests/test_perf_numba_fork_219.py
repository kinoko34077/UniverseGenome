"""#219 PERF5: real native slot ordering and typed-kernel proof smoke."""
import unittest

from benchmarks.perf_numba_fork_219 import (
    DEFAULT_INDICES, DEFAULT_SLOT_GOLDEN, SHORT_GOLDEN,
    _parallel, _reference, scan_kernel_trial,
)


class Perf5NativeBackendSmokeTests(unittest.TestCase):
    def test_predeclared_envelope(self):
        self.assertEqual(len(DEFAULT_INDICES), 16)
        self.assertEqual(DEFAULT_INDICES[:4], (0, 1, 2, 3))
        self.assertEqual(DEFAULT_INDICES[-4:], (96, 97, 98, 99))
        self.assertEqual(len(DEFAULT_SLOT_GOLDEN), 64)
        self.assertEqual(len(SHORT_GOLDEN), 64)

    def test_two_workers_return_same_authoritative_subset(self):
        indices = (0, 32, 64, 96)
        reference = _reference(indices, full_selection=False, short=True)
        trial = _parallel(indices, full_selection=False, short=True,
                          workers=2, batch_size=1)
        self.assertEqual(trial["sha256"], reference["sha256"])
        self.assertEqual(trial["results"], 4)
        self.assertEqual(trial["selection_commits"], 0)
        self.assertEqual(trial["generation"], 0)

    def test_typed_numba_scan_exact_lifecycle_indices(self):
        # NumPy/Numba belong only to the dedicated PERF5 optional-dependency
        # benchmark job. The normal core CI must remain dependency-free;
        # the pinned dedicated job runs this test rather than skipping it.
        try:
            import numpy  # noqa: F401
            import numba  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional benchmark-only numerical dependency absent: {exc.name}")
        trial = scan_kernel_trial(iterations=10)
        self.assertEqual(trial["status"], "ISOLATED_CLASSIFICATION_ONLY")
        self.assertEqual(len(trial["cases"]), 4)
        self.assertTrue(trial["no_physics_step_replacement"])


if __name__ == "__main__":
    unittest.main()
