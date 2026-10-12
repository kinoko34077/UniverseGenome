"""D18 #290: synthetic source-native pruning truth table; no evaluated worlds."""
import unittest
from dataclasses import replace

from research.d8_genome_diversity_190 import digest
from research.d18_native_growth_gate_290 import (
    inspect_native_category,
    inspect_native_preselection_state,
)
from search.evolution import SteadyStateOptimizer
from search.outer_search import SelectionRecord

CATEGORY = "masked_copy"


def entries():
    return [
        SelectionRecord(
            index=i,
            group_key=(CATEGORY, f"synthetic-{i}"),
            objective_key=(i,),
            evidence_count=4,
            candidate_tie_key=(i,),
            growth_windows=(15, 15, 15, 15),
            evidence_mature=True,
        )
        for i in range(32)
    ]


class D18NativeReadOnlyGateTests(unittest.TestCase):
    def test_zero_threshold_original_shape_cannot_grow_prune(self):
        base = entries()
        for i in range(32):
            base[i] = replace(base[i], evidence_mature=False, growth_windows=())
        for i, windows in ((9, (0, 1, 0, 0)),
                           (19, (0, 1, 0, 1)),
                           (23, (1, 0, 1, 0))):
            base[i] = replace(base[i], evidence_mature=True, growth_windows=windows)
        result = inspect_native_category(base, category=CATEGORY)
        self.assertEqual(result["complete_nonfailure_count"], 3)
        self.assertEqual(result["median_growth_bitcounts"], [0, 1, 0, 0])
        self.assertEqual(result["native_half_median_thresholds"], [0, 0, 0, 0])
        self.assertEqual(result["growth_only_candidate_indices_E1"], [])
        self.assertEqual(result["native_predicted_target_index"], None)
        self.assertIsNone(result["actual_native_retirement_E2"])

    def test_positive_four_medians_make_synthetic_e1_reachable(self):
        base = entries()
        base[31] = replace(base[31], growth_windows=(0, 0, 0, 0))
        before = tuple(base)
        result = inspect_native_category(base, category=CATEGORY)
        self.assertEqual(result["median_growth_bitcounts"], [4, 4, 4, 4])
        self.assertEqual(result["native_half_median_thresholds"], [2, 2, 2, 2])
        self.assertEqual(result["growth_only_candidate_indices_E1"], [31])
        self.assertEqual(result["native_predicted_target_class"], "growth_only")
        self.assertIsNone(result["actual_native_retirement_E2"])
        self.assertFalse(result["physics_reachability_proven"])
        self.assertEqual(before, tuple(base))

    def test_native_protection_supresses_eligible_weakness(self):
        base = entries()
        base[0] = replace(base[0], growth_windows=(0, 0, 0, 0))
        result = inspect_native_category(base, category=CATEGORY)
        self.assertIn(0, result["protected_indices"])
        self.assertEqual(result["native_half_median_thresholds"], [2, 2, 2, 2])
        self.assertEqual(result["growth_only_candidate_indices_E1"], [])
        self.assertIsNone(result["native_predicted_target_index"])

    def test_source_rank_can_choose_absolute_failure_before_growth(self):
        base = entries()
        base[30] = replace(base[30], absolute_failure=True,
                           objective_key=(100,))
        base[31] = replace(base[31], growth_windows=(0, 0, 0, 0),
                           objective_key=(99,))
        result = inspect_native_category(base, category=CATEGORY)
        self.assertEqual(result["growth_only_candidate_indices_E1"], [31])
        self.assertIn(30, result["absolute_failure_indices"])
        self.assertEqual(result["native_predicted_target_index"], 30)
        self.assertEqual(result["native_predicted_target_class"], "absolute_failure")
        self.assertIsNone(result["actual_native_retirement_E2"])

    def test_growth_can_win_synthetic_rank_but_not_real_e2(self):
        base = entries()
        base[30] = replace(base[30], absolute_failure=True,
                           objective_key=(99,))
        base[31] = replace(base[31], growth_windows=(0, 0, 0, 0),
                           objective_key=(100,))
        result = inspect_native_category(base, category=CATEGORY)
        self.assertEqual(result["native_predicted_target_index"], 31)
        self.assertEqual(result["native_predicted_target_class"], "growth_only")
        self.assertIsNone(result["actual_native_retirement_E2"])

    def test_duplicate_or_wrong_category_rejected(self):
        base = entries()
        base[31] = replace(base[31], index=0)
        with self.assertRaises(ValueError):
            inspect_native_category(base, category=CATEGORY)
        base = entries()
        base[31] = replace(base[31], group_key=("masked_xor", "wrong"))
        with self.assertRaises(ValueError):
            inspect_native_category(base, category=CATEGORY)

    def test_real_native_initial_state_observed_without_stepping(self):
        original = SteadyStateOptimizer.from_defaults(base_seed=0)
        before = digest(original.to_snapshot())
        report = inspect_native_preselection_state(original)
        self.assertEqual(digest(original.to_snapshot()), before)
        self.assertEqual(report["original_selected_v7_sha256_before_after"], before)
        self.assertEqual(report["original_optimizer_generation"], 0)
        self.assertEqual(len(report["categories"]), 4)
        self.assertTrue(report["native_state_unchanged"])
        self.assertFalse(report["learning_claim"])
        for group in report["categories"].values():
            self.assertEqual(group["occupied"], 32)
            self.assertEqual(group["growth_only_candidate_indices_E1"], [])
            self.assertIsNone(group["actual_native_retirement_E2"])


if __name__ == "__main__":
    unittest.main()
