"""D12 #202: read-only native pruning telemetry and frozen D9 parity guards."""
import unittest

from core.population import CATEGORY_OPERATORS
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer
from research import d12_real_prune_eligibility_202 as d12


class D12ReadOnlySelectionTests(unittest.TestCase):
    def test_gen0_readonly_real_128_slot_native_probe(self):
        opt=SteadyStateOptimizer.from_defaults(base_seed=16384)
        before=digest(opt.to_snapshot())
        result=d12.eligibility_snapshot(opt)
        self.assertEqual(before,digest(opt.to_snapshot()))
        self.assertEqual(result["state_digest"],before)
        self.assertEqual(result["generation"],0)
        self.assertEqual(set(result["strata"]),set(CATEGORY_OPERATORS))
        for cat in CATEGORY_OPERATORS:
            v=result["strata"][cat]
            self.assertEqual(v["occupied"],32)
            self.assertEqual(v["native_pruned_indices"],[])
            self.assertEqual(v["gate"],"GROWTH_HISTORY_INCOMPLETE")
            self.assertEqual(v["complete_nonfailure_count"],0)
            self.assertEqual(v["growth_window_length_histogram"],{0:32})
            self.assertEqual(len(v["native_protected_indices"]),4)

    def test_native_gate_classification_distinguishes_missing_median_and_absolute_failure(self):
        base={"pruned_indices":[],"absolute_failure_count":0,
              "complete_nonfailure_count":0,"median_thresholds":[]}
        self.assertEqual(d12.classify_category(base),"GROWTH_HISTORY_INCOMPLETE")
        value={**base,"complete_nonfailure_count":32,"median_thresholds":[0,0,0,0]}
        self.assertEqual(d12.classify_category(value),"ZERO_MEDIAN_OR_TOO_SMALL_THRESHOLD")
        self.assertEqual(d12.classify_category({**value,"median_thresholds":[1,1,1,1]}),
                         "NO_WEAK_CANDIDATE_DESPITE_NONZERO_THRESHOLD")
        self.assertEqual(d12.classify_category({**value,"pruned_indices":[31]}),
                         "ELIGIBLE_AT_CHECKPOINT")
        self.assertEqual(d12.classify_category({**base,"absolute_failure_count":1}),
                         "ABSOLUTE_FAILURE_WITHOUT_NATIVE_PRUNE_UNEXPECTED")

    def test_fixed_D9_manifest_not_a_new_heldout_or_seed_sweep(self):
        self.assertEqual(d12.FROZEN_BASE_SEED,16384)
        self.assertEqual(d12.FROZEN_STEPS,4)
        self.assertEqual(d12.D9_SOURCE_SHA,
                         "6c51b7006b673e7d38facfde82f6ce9e9363d28e")
        self.assertEqual(d12.D9_CASE_SHA256,
                         "3e6162f8af56d0c802b02fa7e73df567dd7365bafc09fb42917ceb1815caf721")
        self.assertFalse(d12.PROTOCOL["independent_heldout_or_new_seeds"])
        self.assertFalse(d12.PROTOCOL["learning_claim"])


if __name__=="__main__":
    unittest.main()
