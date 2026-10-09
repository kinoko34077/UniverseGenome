"""D11 #199: frozen native SelectionRecord pruning eligibility tests."""
import unittest

from core.population import CATEGORY_OPERATORS
from research import d11_native_prune_gate_199 as d11


class NativePruneGateTests(unittest.TestCase):
    def test_exact_frozen_native_cases(self):
        out=d11.evaluate()
        first=CATEGORY_OPERATORS[0]
        cases=out["native_selection_cases"]
        for category in CATEGORY_OPERATORS:
            self.assertEqual(cases["F0_flat_complete"][category]["pruned_indices"],[])
            self.assertEqual(cases["F1_flat_incomplete"][category]["pruned_indices"],[])
            self.assertEqual(cases["F0_flat_complete"][category]["four_window_evidence_count"],32)
            self.assertEqual(cases["F1_flat_incomplete"][category]["four_window_evidence_count"],0)
            self.assertEqual(len(cases["F0_flat_complete"][category]["protected_indices"]),4)
        self.assertEqual(cases["F2_skew_positive_median"][first]["pruned_indices"],[31])
        self.assertEqual(cases["F2_skew_positive_median"][first]["target_index"],31)
        self.assertEqual(cases["F2_skew_positive_median"][first]["parent_index"],0)
        self.assertEqual(cases["F2_skew_positive_median"][first]["medians_flagbit_count"],2)
        self.assertEqual(cases["F3_absolute_failure"][first]["pruned_indices"],[31])
        for category in CATEGORY_OPERATORS[1:]:
            self.assertEqual(cases["F2_skew_positive_median"][category]["pruned_indices"],[])
            self.assertEqual(cases["F3_absolute_failure"][category]["pruned_indices"],[])

    def test_deterministic_replay_and_separate_D9_causal_qualification(self):
        a,b=d11.evaluate(),d11.evaluate()
        self.assertEqual(a,b)
        self.assertEqual(a["digest"],b["digest"])
        self.assertEqual(a["classification"],"CONDITIONAL_ZERO_MEDIAN_PRUNE_GATE_CONFIRMED_D9_ACTUAL_CAUSE_NOT_IDENTIFIED")
        limits=a["limits"]
        self.assertTrue(limits["synthetic_fixtures_only"])
        for name in ("D9_actual_growth_windows_observed","D9_no_replacement_unique_cause_proven",
                     "actual_genetic_selection_pressure_observed_here","real_overfit_or_heldout_measured",
                     "learning_claim"):
            self.assertFalse(limits[name])

    def test_source_only_no_seed_or_policy_extension(self):
        self.assertEqual(len(CATEGORY_OPERATORS),4)
        self.assertEqual(d11.CATEGORY_SIZE,32)
        self.assertEqual(d11.GROUP_SIZE,4)
        self.assertEqual(set(d11.PREDECLARED["cases"]),{
            "F0_flat_complete","F1_flat_incomplete","F2_skew_positive_median","F3_absolute_failure"})
        with self.assertRaises(ValueError):
            d11._records("not_a_category","F0_flat_complete")
        with self.assertRaises(ValueError):
            d11._records(CATEGORY_OPERATORS[0],"new_posthoc_scenario")


if __name__=="__main__":
    unittest.main()
