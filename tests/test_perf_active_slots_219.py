"""#219 pure-CPU active slot indexing: exact legacy state/selection parity."""
from dataclasses import asdict
import unittest

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig, create_universe, step
from core.state import Lifecycle, UniverseState
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer


def legacy_active_slots(self):
    return [index for index, value in enumerate(self.lifecycle)
            if value == Lifecycle.ACTIVE]


class ActiveSlotsIndexEquivalenceTests(unittest.TestCase):
    def test_scan_matches_reference_across_free_active_blackhole_patterns(self):
        state = UniverseState(seed=0, max_cells=1024)
        patterns = (
            (), (0,), (1023,), (0, 1023), tuple(range(1024)),
            tuple(range(0, 1024, 3)), tuple(range(100, 400)),
        )
        for positions in patterns:
            with self.subTest(positions=len(positions)):
                state.lifecycle[:] = [int(Lifecycle.BLACK_HOLE) if i % 7 == 0
                                      else int(Lifecycle.FREE) for i in range(1024)]
                for i in positions:
                    state.lifecycle[i] = int(Lifecycle.ACTIVE)
                self.assertEqual(state.active_slots(), legacy_active_slots(state))
                self.assertEqual(state.active_slots(), sorted(positions))

    def test_physics_snapshot_and_counters_match_reference(self):
        original = UniverseState.active_slots
        for density in (4, 32, 128):
            with self.subTest(density=density):
                config = PhysicsConfig(initial_density=density)
                base = create_universe(seed=0, config=config)
                optimized = create_universe(seed=0, config=config)
                for _ in range(20):
                    try:
                        UniverseState.active_slots = legacy_active_slots
                        baseline_metrics = step(base)
                    finally:
                        UniverseState.active_slots = original
                    optimized_metrics = step(optimized)
                    self.assertEqual(base.to_snapshot(), optimized.to_snapshot())
                    baseline_counters = asdict(baseline_metrics)
                    opt_counters = asdict(optimized_metrics)
                    baseline_counters.pop("generations_per_second")
                    opt_counters.pop("generations_per_second")
                    self.assertEqual(baseline_counters, opt_counters)

    def test_original_pre_d14_native_selected128_golden(self):
        opt = SteadyStateOptimizer.from_defaults(
            base_seed=0,
            experiment=ExperimentConfig(evaluation_timeout_generations=2),
        )
        step_report = opt.step()
        self.assertEqual(step_report["evaluated_slots"], 128)
        self.assertFalse(step_report["cross_category_selection"])
        self.assertEqual(
            digest(opt.to_snapshot()),
            "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321",
        )


if __name__ == "__main__":
    unittest.main()
