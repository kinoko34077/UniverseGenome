"""PERF230 bounded representative slot profiler contract; no heavy evaluation in CI."""
import unittest

from benchmarks.perf230_category_phases import INDICES, run


class NativeProfileContract(unittest.TestCase):
    def test_only_one_identity_per_original_category_stratum(self) -> None:
        self.assertEqual(INDICES, (0, 32, 64, 96))

    def test_unapproved_or_nonrepresentative_sample_fails_before_execution(self) -> None:
        with self.assertRaisesRegex(ValueError, "frozen"):
            run((0, 32, 64, 95))


if __name__ == "__main__":
    unittest.main()
