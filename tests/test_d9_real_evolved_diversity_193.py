"""D9 #193 synthetic time-series guard tests; real steps run only in frozen Action."""
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from search.evolution import SteadyStateOptimizer
from core.population import CATEGORY_OPERATORS
from research.d8_genome_diversity_190 import digest
from research import d9_real_evolved_diversity_193 as d9


def series(*, replacements=0, concentrated=False, fixation=False):
    records=[]
    for i in range(5):
        share=0.125 if i==0 or not concentrated else 0.5
        u=8 if i==0 or not fixation else 1
        records.append({
            "generation":i,"replacement_count":0 if i==0 else replacements,
            "replacements":[] if i==0 else ([{"allocation_reason":"mutation_child"}]*replacements),
            "strata":{cat:{"unique_genomes":u,
                           "dominant_genome_share":1 if i>0 and fixation else share}
                      for cat in CATEGORY_OPERATORS},
        })
    return records


class TrajectoryTests(unittest.TestCase):
    def test_insufficient_selection_exposure_is_not_preservation(self):
        risk=d9.classify_trajectory(series())
        self.assertEqual(risk["classification"],"SELECTION_NOT_EXPOSED")
        self.assertFalse(risk["long_term_diversity_guaranteed"])
        self.assertFalse(risk["overfitting_measured"])

    def test_concentration_and_fixation_are_different(self):
        a=d9.classify_trajectory(series(replacements=1,concentrated=True))
        self.assertEqual(a["classification"],"CONCENTRATION_OBSERVED_IN_SHORT_RUN")
        self.assertEqual(a["observed_replacements"],4)
        b=d9.classify_trajectory(series(replacements=1,fixation=True))
        self.assertEqual(b["classification"],"FIXATION_OBSERVED_IN_SHORT_RUN")
        self.assertEqual(len(b["genotype_fixation_windows"]),16)
        self.assertFalse(b["independent_heldout_tested"])

    def test_replay_or_missing_step_fails(self):
        broken=series()
        broken[-1]["generation"]=5
        with self.assertRaises(ValueError):
            d9.classify_trajectory(broken)

    def test_real_initial_checkpoint_is_read_only(self):
        opt=SteadyStateOptimizer.from_defaults(base_seed=16384)
        before=digest(opt.to_snapshot())
        record=d9._checkpoint(opt,step_data=None,previous=None)
        self.assertEqual(before,digest(opt.to_snapshot()))
        self.assertEqual(record["generation"],0)
        self.assertEqual(record["replacement_count"],0)
        for cat in CATEGORY_OPERATORS:
            self.assertEqual(record["strata"][cat]["unique_genomes"],8)

    def test_no_future_cohort_and_no_generalization_claim(self):
        self.assertEqual(d9.START_SEEDS,(16384,32768))
        self.assertEqual(d9.STEPS,4)
        self.assertEqual(d9.PROTOCOL["learning_claim"],False)
        self.assertEqual(d9.PROTOCOL["heldout_generalization_measured"],False)
        with self.assertRaises(ValueError):
            d9.trajectory(2048)

    def test_missing_aggregate_fails_closed(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                d9.aggregate(Path(tmp),"a"*40)


if __name__=="__main__":
    unittest.main()
