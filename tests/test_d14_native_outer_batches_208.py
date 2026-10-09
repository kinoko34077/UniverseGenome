"""D14 #208: frozen PRE-source-change native batch strict legacy oracle."""
import unittest
from unittest.mock import patch

from core.experiment import ExperimentConfig
from research.d8_genome_diversity_190 import digest
from research.d13_outer_execution_204 import OuterResearchPlan, execute
from search.evolution import SteadyStateOptimizer

GOLDEN_SHA256="0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321"
BATCHES=(1,7,16,128)


class NativeSelectedBatchParityTests(unittest.TestCase):
    def test_reject_bad_batch_before_evaluating_any_world(self):
        opt=SteadyStateOptimizer.from_defaults(
            base_seed=0,experiment=ExperimentConfig(evaluation_timeout_generations=2))
        before=digest(opt.to_snapshot())
        with patch.object(opt,"_evaluate_slot",
                          side_effect=AssertionError("invalid batch ran physical simulation")):
            for bad in (0,-1,129,True,2.5):
                with self.subTest(batch=bad):
                    with self.assertRaises(ValueError):
                        opt.step(evaluation_batch_size=bad)
        self.assertEqual(before,digest(opt.to_snapshot()))
        self.assertEqual(opt.generation,0)

    def test_same_authentic_full_native_state_and_deterministic_step_for_four_batch_sizes(self):
        reference=None
        for batch in BATCHES:
            with self.subTest(batch=batch):
                opt=SteadyStateOptimizer.from_defaults(
                    base_seed=0,experiment=ExperimentConfig(evaluation_timeout_generations=2))
                step=opt.step(evaluation_batch_size=batch)
                self.assertEqual(digest(opt.to_snapshot()),GOLDEN_SHA256)
                self.assertEqual(step["evaluated_slots"],128)
                self.assertEqual(step["generation"],1)
                self.assertEqual(opt.scheduler["evaluation_count"],128)
                stable={k:v for k,v in step.items() if k!="generations_per_second"}
                if reference is None:
                    reference=stable
                self.assertEqual(stable,reference)

    def test_native_controller_batch_smaller_than_128_is_real_selection_path_not_sample(self):
        proto=ExperimentConfig(evaluation_timeout_generations=2)
        plan=OuterResearchPlan(
            mode="native_selection",base_seed=0,outer_steps=1,
            evaluated_worlds=128,worlds_per_batch=7)
        self.assertEqual(plan.validate(physics=__import__("core.physics",fromlist=["PhysicsConfig"]).PhysicsConfig(),
                                       experiment=proto)["resident_world_limit"],128)
        result=execute(plan,experiment=proto)
        self.assertEqual(result["final_state_digest"],GOLDEN_SHA256)
        self.assertEqual(result["rounds"][0]["evaluated_slots"],128)
        self.assertEqual(result["admission"]["resident_world_limit"],128)
        self.assertFalse(result["independent_heldout_tested"])


if __name__=="__main__":
    unittest.main()
