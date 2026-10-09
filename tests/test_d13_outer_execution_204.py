"""D13 #204: bounded plan, actual small-world evaluation, and role invariants."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research import d13_outer_execution_204 as d13


class ResearchOuterTests(unittest.TestCase):
    def test_exact_legacy_config_contract_and_preflight(self):
        p=d13.OuterResearchPlan()
        self.assertEqual((p.mode,p.outer_steps,p.evaluated_worlds,p.worlds_per_batch),
                         ("native_selection",1,128,128))
        info=p.validate(physics=PhysicsConfig(),experiment=ExperimentConfig())
        self.assertEqual(info["resident_world_limit"],128)
        self.assertEqual(info["world_rounds"],128)
        self.assertEqual(info["physical_generations_per_world_round"],14)
        self.assertLessEqual(info["estimated_physics_work"],d13.MAX_WORK_UNITS)

    def test_bad_plans_fail_before_any_universe_is_built(self):
        bad=(
            d13.OuterResearchPlan(outer_steps=100),
            d13.OuterResearchPlan(evaluated_worlds=127),
            d13.OuterResearchPlan(worlds_per_batch=129),
            d13.OuterResearchPlan(mode="sampled_evaluation",evaluated_worlds=8,worlds_per_batch=9),
            d13.OuterResearchPlan(mode="sampled_evaluation",evaluated_worlds=8,worlds_per_batch=0),
            d13.OuterResearchPlan(mode="sampled_evaluation",outer_steps=64,evaluated_worlds=128,worlds_per_batch=16),
            d13.OuterResearchPlan(base_seed=-1),
            d13.OuterResearchPlan(outer_steps=True),
            d13.OuterResearchPlan(max_wall_seconds=0),
        )
        with patch.object(d13,"create_universe",side_effect=AssertionError("world constructed")):
            for plan in bad:
                with self.subTest(plan=plan):
                    with self.assertRaises(ValueError):
                        d13.execute(plan)

    def test_real_full_128_native_complete_round_atomic_resume_is_bit_identical(self):
        # One genuine full native step, not a simulated state or a partial cohort.
        proto=ExperimentConfig(evaluation_timeout_generations=2)
        with TemporaryDirectory() as directory:
            path=Path(directory)/"native-checkpoint.json"
            original=d13.execute(d13.OuterResearchPlan(outer_steps=1),
                                 experiment=proto,snapshot_out=path)
            self.assertTrue(path.is_file())
            resumed=d13.execute(d13.OuterResearchPlan(outer_steps=0),
                                experiment=proto,resume_snapshot=path)
            self.assertEqual(original["final_state_digest"],resumed["final_state_digest"])
            self.assertEqual(original["scheduler"],resumed["scheduler"])
            self.assertEqual(original["final_optimizer_generation"],1)
            self.assertEqual(resumed["start_optimizer_generation"],1)
            self.assertEqual(resumed["final_optimizer_generation"],1)
            self.assertFalse(resumed["genetic_selection_performed"])

    def test_large_resume_snapshot_is_rejected_before_read(self):
        # Sparse file forces admission rejection without allocating 256 MiB.
        with TemporaryDirectory() as directory:
            path=Path(directory)/"oversized.json"
            with path.open("wb") as stream:
                stream.truncate(256*1024*1024+1)
            with patch.object(Path,"read_text",
                              side_effect=AssertionError("oversized file was read")):
                with self.assertRaises(ValueError):
                    d13.execute(d13.OuterResearchPlan(outer_steps=0),
                                resume_snapshot=path)

    def test_stratified_world_ids_and_no_partial_selection(self):
        self.assertEqual(d13._sample_indices(1),(0,))
        self.assertEqual(d13._sample_indices(4),(0,32,64,96))
        self.assertEqual(d13._sample_indices(8),(0,32,64,96,1,33,65,97))
        self.assertEqual(sorted(d13._sample_indices(128)),list(range(128)))

    def test_real_single_disposable_world_is_deterministic_and_nonselecting(self):
        plan=d13.OuterResearchPlan(mode="sampled_evaluation",base_seed=16384,
                                   outer_steps=1,evaluated_worlds=1,worlds_per_batch=1)
        protocol=ExperimentConfig(evaluation_timeout_generations=2)
        first=d13.execute(plan,experiment=protocol)
        second=d13.execute(plan,experiment=protocol)
        self.assertEqual(first["digest"],second["digest"])
        self.assertEqual(first["evaluated_world_ids"],[0])
        self.assertFalse(first["genetic_selection_performed"])
        self.assertTrue(first["selection_not_applicable"])
        self.assertEqual(first["sampled_world_results"][0]["physical_generation"],14)
        self.assertFalse(first["learning_claim"])
        self.assertFalse(first["independent_heldout_tested"])

    def test_native_zero_round_does_not_claim_selection_or_replacement(self):
        result=d13.execute(d13.OuterResearchPlan(outer_steps=0))
        self.assertFalse(result["genetic_selection_performed"])
        self.assertFalse(result["native_selection_policy_invoked"])
        self.assertEqual(result["observed_genetic_replacements"],0)
        self.assertEqual(result["start_optimizer_generation"],0)
        self.assertEqual(result["final_optimizer_generation"],0)
        self.assertFalse(result["selection_not_exposed"])

    def test_sampled_outer_round_count_controls_real_physical_clock(self):
        plan=d13.OuterResearchPlan(mode="sampled_evaluation",base_seed=16384,
                                   outer_steps=3,evaluated_worlds=1,worlds_per_batch=1)
        value=d13.execute(plan,experiment=ExperimentConfig(evaluation_timeout_generations=2))
        self.assertEqual(value["sampled_world_results"][0]["physical_generation"],42)
        self.assertEqual(value["admission"]["world_rounds"],3)
        self.assertFalse(value["genetic_selection_performed"])

    def test_category_coverage_and_batch_boundary_same_results(self):
        proto=ExperimentConfig(evaluation_timeout_generations=2)
        a=d13.execute(d13.OuterResearchPlan(
            mode="sampled_evaluation",outer_steps=1,base_seed=16384,
            evaluated_worlds=4,worlds_per_batch=1),experiment=proto)
        b=d13.execute(d13.OuterResearchPlan(
            mode="sampled_evaluation",outer_steps=1,base_seed=16384,
            evaluated_worlds=4,worlds_per_batch=4),experiment=proto)
        self.assertEqual(a["sampled_world_results"],b["sampled_world_results"])
        self.assertEqual(len({x["category"] for x in a["sampled_world_results"]}),4)
        self.assertEqual([x["index"] for x in a["sampled_world_results"]],[0,32,64,96])


if __name__=="__main__":
    unittest.main()
