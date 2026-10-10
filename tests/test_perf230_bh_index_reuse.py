"""PERF230 P3.4 test-first: reuse the authoritative BH slot scan, no physics changes.

Both the accepted baseline and candidate must pass these behavioral tests.
The genuine full selected128 default run is verified by the separate A/B workflow.
"""
from __future__ import annotations

import unittest

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig, create_universe, step
from core.state import Lifecycle
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer


class BhIndexReuseBehavior(unittest.TestCase):
    def test_sparse_dense_and_bh_free_step_consistency(self) -> None:
        for density in (0, 4, 32, 128):
            with self.subTest(density=density):
                state = create_universe(
                    seed=0, config=PhysicsConfig(initial_density=density)
                )
                for generation in range(16):
                    metrics = step(state)
                    self.assertEqual(state.generation, generation + 1)
                    self.assertEqual(
                        metrics.active_cells, len(state.active_slots())
                    )

    def test_original_ordered_bh_expiry_and_direct_stimulus(self) -> None:
        state = create_universe(
            seed=0, config=PhysicsConfig(initial_density=0)
        )
        state.lifecycle[5] = int(Lifecycle.BLACK_HOLE)
        state.lifecycle[1] = int(Lifecycle.BLACK_HOLE)
        state.black_hole_timer[5] = 2
        state.black_hole_timer[1] = 1
        first = step(state)
        self.assertEqual(state.lifecycle[1], int(Lifecycle.FREE))
        self.assertEqual(state.lifecycle[5], int(Lifecycle.BLACK_HOLE))
        self.assertEqual(state.black_hole_timer[5], 1)
        self.assertEqual(first.active_cells, 0)
        second = step(state, stimulus_slots=(5,))
        self.assertEqual(state.lifecycle[5], int(Lifecycle.ACTIVE))
        self.assertEqual(state.black_hole_timer[5], 0)
        self.assertEqual(second.generation, 2)

    def test_default1024_original_single_slot_digest(self) -> None:
        opt = SteadyStateOptimizer.from_defaults(base_seed=0)
        opt._evaluate_slot(opt.slots[0])
        self.assertEqual(
            digest(opt.to_snapshot()),
            "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1",
        )

    def test_original_short_selected128_digest(self) -> None:
        opt = SteadyStateOptimizer.from_defaults(
            base_seed=0,
            experiment=ExperimentConfig(evaluation_timeout_generations=2),
        )
        record = opt.step(evaluation_batch_size=16)
        self.assertEqual(record["evaluated_slots"], 128)
        self.assertEqual(
            digest(opt.to_snapshot()),
            "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321",
        )


if __name__ == "__main__":
    unittest.main()
