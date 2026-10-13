"""A1.7 original previously exposed fusion gate read-only protocol smoke tests."""
import unittest

from research.a17_original_fusion_funnel_329 import (
    PERIODS, STAGES, SEEDS, EXPECTED, empty_count_record,
    count_one, period_of, run_original_branch, report,
)
from research.a16_fusion_eligibility_funnel_326 import native_fusion_eligibility_funnel
from research.r2_write_rules_175 import load_frozen
from tests.test_a16_native_latent_diversity_feasibility_326 import (
    NativeLatentDiversityFeasibility,
)
from tests.test_a16_fusion_eligibility_funnel_326 import occupancy_of


class A17OldR2SourceContract(unittest.TestCase):
    def test_stage_accounting_is_explicit_and_unchanged(self):
        a=NativeLatentDiversityFeasibility._four_single_cover(bonds=33)
        candidate=native_fusion_eligibility_funnel(
            a,occupancy_of(a),a.config,
        )
        record=empty_count_record()
        count_one(record,candidate)
        count_one(record,candidate)
        self.assertEqual(record["native_steps"],2)
        self.assertEqual(record["candidate_groups"],2)
        self.assertEqual(record["gate_counts"]["compatible_velocity"],2)
        self.assertEqual(record["steps_any_gate"]["compatible_velocity"],2)
        self.assertEqual(tuple(record["gate_counts"]),STAGES)
        self.assertEqual(record["actual_fusions"],0)
        self.assertEqual(record["steps_any_gate"]["exact_cover"],2)

    def test_original_genuine_negative_geometry_is_counted_no_fusion(self):
        a=NativeLatentDiversityFeasibility._four_single_cover(missing=True)
        result=native_fusion_eligibility_funnel(a,occupancy_of(a),a.config)
        record=empty_count_record()
        count_one(record,result)
        self.assertEqual(record["native_steps"],1)
        self.assertEqual(record["gate_counts"]["exact_cover"],0)
        self.assertEqual(record["candidate_groups"],0)

    def test_period_and_seed_guards_no_new_prospective_study(self):
        self.assertEqual(SEEDS,(544,545))
        self.assertEqual(EXPECTED,{544:(764,95,36),545:(966,0,0)})
        self.assertEqual(PERIODS,((1,100),(101,250),(251,500),(501,1000)))
        self.assertEqual(
            [period_of(k) for k in (1,100,101,250,251,500,501,1000)],
            ["1-100","1-100","101-250","101-250",
             "251-500","251-500","501-1000","501-1000"],
        )
        for k in (0,1001):
            with self.assertRaises(ValueError):
                period_of(k)
        with self.assertRaises(ValueError):
            run_original_branch(16384,"b",{},0.0)
        with self.assertRaises(ValueError):
            run_original_branch(544,"control",{},0.0)
        with self.assertRaises(ValueError):
            report(source_sha="not-a-sha")

    def test_original_manifest_and_exact_native_conditions(self):
        f=load_frozen()
        self.assertEqual(f["digest"],
            "3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543")
        self.assertIn(544,f["positive_seeds"])
        self.assertIn(545,f["negative_seeds"])


if __name__=="__main__":
    unittest.main()
