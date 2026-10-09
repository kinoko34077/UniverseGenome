"""R1 decision statistics, bounded shard assignment and frozen-mode safety."""
from __future__ import annotations

import unittest

from research.r1_causal_analysis_172 import _mcnemar_one_sided, _holm, shard_cases


class R1CausalAnalysisTests(unittest.TestCase):
    def test_exact_one_sided_paired_sign_test(self):
        self.assertEqual(_mcnemar_one_sided(0,0),1.0)
        self.assertEqual(_mcnemar_one_sided(8,0),1/256)
        self.assertEqual(_mcnemar_one_sided(0,8),1.0)
        self.assertGreater(_mcnemar_one_sided(8,2),0.05)

    def test_holm_controls_three_competing_loss_hypotheses(self):
        adjusted=_holm({"free":0.012,"write":0.01,"transfer":0.049})
        self.assertAlmostEqual(adjusted["write"],0.03)
        self.assertAlmostEqual(adjusted["free"],0.03)
        self.assertAlmostEqual(adjusted["transfer"],0.049)

    def test_shards_disjoint_complete_and_no_reuse(self):
        frozen={"positive_seeds":list(range(160,184)),
                "negative_seeds":list(range(184,192))}
        groups=[shard_cases(frozen,k) for k in range(8)]
        self.assertEqual([len(k) for k in groups],[4]*8)
        self.assertEqual(sorted(s for g in groups for s in g),list(range(160,192)))
        with self.assertRaises(ValueError):
            shard_cases(frozen,8)


if __name__=="__main__":
    unittest.main()
