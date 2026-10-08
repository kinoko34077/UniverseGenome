"""#167 D2 pre-execution contract and fail-closed aggregation guards."""
import tempfile
from pathlib import Path
import unittest

from research.phase_g_decay_axis_159 import load_frozen_contract
from research.trace_fate_d2_167 import (
    D1_ACCEPTED_MAIN, RATES, RUN_HORIZON, aggregate, assignments,
    run_case, run_shard,
)


class TraceFateD2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = load_frozen_contract()

    def test_d2_matrix_exactly_reuses_adaptive_g0_not_heldout(self):
        rows = assignments(self.frozen)
        self.assertEqual(len(rows), 20)
        self.assertEqual(len(set(rows)), 20)
        self.assertEqual(rows[:16], [
            (seed, "search") for seed in self.frozen["search_cohort"]
        ])
        self.assertEqual(rows[16:], [
            (seed, "sentinel") for seed in self.frozen["search_negative_sentinels"]
        ])
        self.assertTrue(set(seed for seed, _ in rows).isdisjoint(
            self.frozen["heldout_validation_cohort"]
            + self.frozen["heldout_negative_sentinels"]
            + self.frozen["old_140_primary_seeds_excluded"]
        ))
        self.assertEqual(RATES, (0, 256))
        self.assertEqual(RUN_HORIZON, 1000)
        self.assertEqual(len(D1_ACCEPTED_MAIN), 40)

    def test_invalid_rate_shard_source_or_cohort_fails_before_running(self):
        with tempfile.TemporaryDirectory() as root:
            for rate, shard in ((1, 0), (256, -1), (256, 4)):
                with self.subTest(rate=rate, shard=shard):
                    with self.assertRaisesRegex(ValueError, "outside frozen"):
                        run_shard(
                            rate=rate, shard=shard, source_sha=D1_ACCEPTED_MAIN,
                            output_dir=Path(root),
                        )
        with self.assertRaisesRegex(ValueError, "outside predeclared"):
            run_case(seed=0, role="search", rate=256, source_sha=D1_ACCEPTED_MAIN)
        with self.assertRaisesRegex(ValueError, "source SHA"):
            run_case(
                seed=self.frozen["search_cohort"][0], role="search",
                rate=256, source_sha="invalid",
            )

    def test_missing_matrix_is_blocked(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "incomplete D2 matrix"):
                aggregate(Path(root), source_sha=D1_ACCEPTED_MAIN)


if __name__ == "__main__":
    unittest.main()
