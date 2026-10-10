"""PERF230 BH-free full-scan fastpath must preserve original native semantics."""
from __future__ import annotations

import unittest

from core.physics import PhysicsConfig, create_universe, step
from core.state import Lifecycle
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

HISTORIC_DEFAULT_SLOT0_V7 = (
    "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"
)


class NoBlackHoleFastpathRegressions(unittest.TestCase):
    def test_no_bh_physical_metrics_match_final_active_lifecycle(self) -> None:
        state = create_universe(seed=0, config=PhysicsConfig(initial_density=8))
        for _ in range(20):
            metrics = step(state)
            self.assertEqual(metrics.active_cells,
                             state.lifecycle.count(int(Lifecycle.ACTIVE)))

    def test_existing_black_hole_grace_expiry_keeps_original_path(self) -> None:
        state = create_universe(seed=0, config=PhysicsConfig(initial_density=0))
        state.lifecycle[0] = int(Lifecycle.BLACK_HOLE)
        state.black_hole_timer[0] = 2
        step(state)
        self.assertEqual(state.lifecycle[0], int(Lifecycle.BLACK_HOLE))
        self.assertEqual(state.black_hole_timer[0], 1)
        step(state)
        self.assertEqual(state.lifecycle[0], int(Lifecycle.FREE))

    def test_original_stimulus_revives_black_hole_without_new_branch_effect(self) -> None:
        state = create_universe(seed=0, config=PhysicsConfig(initial_density=0))
        state.lifecycle[0] = int(Lifecycle.BLACK_HOLE)
        state.black_hole_timer[0] = 2
        step(state, stimulus_slots=(0,))
        self.assertEqual(state.lifecycle[0], int(Lifecycle.ACTIVE))
        self.assertEqual(state.black_hole_timer[0], 0)

    def test_complete_original_default_slot0_optimizer_snapshot_golden(self) -> None:
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=0)
        optimizer._evaluate_slot(optimizer.slots[0])
        self.assertEqual(digest(optimizer.to_snapshot()),
                         HISTORIC_DEFAULT_SLOT0_V7)


if __name__ == "__main__":
    unittest.main()
