"""D8 #190: real baseline and synthetic collapse/diversity role guard tests."""
import copy
import json
import unittest

from search.evolution import SteadyStateOptimizer
from search.genome import UniverseGenome
from core.population import CATEGORY_OPERATORS
from research import d8_genome_diversity_190 as d8


def rows(population_by_category):
    result=[]
    for cat in CATEGORY_OPERATORS:
        genomes=population_by_category[cat]
        assert len(genomes)==32
        for offset,g in enumerate(genomes):
            result.append({
                "index":len(result), "category":cat, "genome":g.to_dict(),
                "seed":offset,"allocation_reason":"synthetic","parent_genome_key":None,
            })
    return result


class DiversityAuditTests(unittest.TestCase):
    def setUp(self):
        self.genomes=UniverseGenome.initial_population()
        self.initial={cat:list(g for g in self.genomes for _ in range(4)) for cat in CATEGORY_OPERATORS}

    def test_initial_8_genomes_4_real_seeds_each(self):
        out=d8.report_rows(rows(self.initial),optimizer_generation=0)
        self.assertEqual(out["global_pooled_unique_genomes"],8)
        for v in out["strata"].values():
            self.assertEqual(v["occupied_slots"],32)
            self.assertEqual(v["unique_genomes"],8)
            self.assertEqual(v["genome_slot_frequencies"],[4]*8)
            self.assertEqual(v["dominant_genome_share"],0.125)
            self.assertEqual(v["shannon_effective_genomes"],8)
            self.assertEqual(v["inverse_simpson_effective_genomes"],8)
            self.assertEqual(v["distinct_real_seeds_per_genome"],[4]*8)
            self.assertEqual(v["seed_reused_within_genome_count"],0)
            self.assertGreater(v["mean_distinct_genome_field_mismatch"],0)

    def test_collapse_is_detected_but_not_autocalled_real(self):
        mono={cat:[self.genomes[0]]*32 for cat in CATEGORY_OPERATORS}
        out=d8.report_rows(rows(mono),optimizer_generation=1000)
        for v in out["strata"].values():
            self.assertEqual(v["unique_genomes"],1)
            self.assertEqual(v["dominant_genome_share"],1)
            self.assertEqual(v["shannon_effective_genomes"],1)
            self.assertEqual(v["inverse_simpson_effective_genomes"],1)
            self.assertIsNone(v["mean_distinct_genome_field_mismatch"])
            self.assertEqual(v["fixed_field_count"],len(d8.FIELDS))
            self.assertEqual(v["distinct_real_seeds_per_genome"],[32])
        self.assertFalse(out["limitations"]["genetic_diversity_collapse_proven"])
        self.assertFalse(out["limitations"]["overfitting_measured"])

    def test_nonuniform_concentration_and_category_isolation(self):
        p=copy.deepcopy(self.initial)
        p[CATEGORY_OPERATORS[0]]=[self.genomes[0]]*16+[self.genomes[1]]*8+[self.genomes[2]]*8
        out=d8.report_rows(rows(p),optimizer_generation=2)
        first=out["strata"][CATEGORY_OPERATORS[0]]
        second=out["strata"][CATEGORY_OPERATORS[1]]
        self.assertEqual(first["unique_genomes"],3)
        self.assertEqual(first["dominant_genome_share"],0.5)
        self.assertEqual(first["inverse_simpson_effective_genomes"],2.6666666667)
        self.assertEqual(second["dominant_genome_share"],0.125)
        self.assertEqual(second["unique_genomes"],8)
        self.assertEqual(out["global_pooled_unique_genomes"],8)
        self.assertEqual(out["total_authoritative_slots"],128)

    def test_guard_rejects_invalid_roster_and_identity(self):
        p=rows(self.initial)
        p[3]["index"]=2
        with self.assertRaises(ValueError):
            d8.report_rows(p,optimizer_generation=0)
        p=rows(self.initial)
        del p[3]["genome"]["noise_rate"]
        with self.assertRaises(ValueError):
            d8.report_rows(p,optimizer_generation=0)
        p=rows(self.initial)
        p[3]["seed"]=True
        with self.assertRaises(ValueError):
            d8.report_rows(p,optimizer_generation=0)

    def test_evidence_roles_disjoint_and_not_real_generalization(self):
        with self.assertRaisesRegex(ValueError,"leakage"):
            d8.enforce_cohort_roles({"training":[5,6],"heldout":[6,7]})
        with self.assertRaisesRegex(ValueError,"duplicate"):
            d8.enforce_cohort_roles({"training":[4,4]})
        v=d8.enforce_cohort_roles({"training":[4],"validation":[5],"heldout":[6]})
        self.assertTrue(v["heldout_evaluable"])
        self.assertIsNone(v["generalization_result"])
        self.assertFalse(d8.enforce_cohort_roles({})["heldout_evaluable"])

    def test_real_128_slot_baseline_nonmutating_repeat(self):
        opt=SteadyStateOptimizer.from_defaults(base_seed=0)
        before=d8.digest(opt.to_snapshot())
        a=d8.analyze(opt)
        b=d8.analyze(opt)
        self.assertEqual(before,d8.digest(opt.to_snapshot()))
        self.assertEqual(a,b)
        self.assertEqual(a["total_authoritative_slots"],128)
        self.assertEqual(a["global_pooled_unique_genomes"],8)
        for category in CATEGORY_OPERATORS:
            self.assertEqual(a["strata"][category]["unique_genomes"],8)
            self.assertEqual(a["strata"][category]["dominant_genome_share"],0.125)
        self.assertFalse(a["limitations"]["independent_heldout_tested"])
        self.assertFalse(a["learning_claim"])


if __name__=="__main__":
    unittest.main()
