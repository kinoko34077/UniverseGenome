"""PERF230 P3.3: active-cell metric must equal authoritative lifecycle count.

Pre-frozen performance-only refactor: these invariants hold in the original
source as well as the proposed count-based reporting implementation.
"""
from __future__ import annotations

import unittest

from core.physics import PhysicsConfig, create_universe, step
from core.state import Lifecycle
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer


class ActiveMetricCountParity(unittest.TestCase):
    def test_density_and_active_scan_parity(self) -> None:
        for density in (0, 4, 32, 128):
            with self.subTest(density=density):
                state = create_universe(
                    seed=0, config=PhysicsConfig(initial_density=density)
                )
                for generation in range(16):
                    metrics = step(state)
                    expected = state.lifecycle.count(int(Lifecycle.ACTIVE))
                    self.assertEqual(metrics.active_cells, expected)
                    self.assertEqual(expected, len(state.active_slots()))
                    self.assertEqual(metrics.generation, generation + 1)

    def test_black_hole_expiry_and_direct_stimulus(self) -> None:
        state = create_universe(
            seed=0, config=PhysicsConfig(initial_density=0)
        )
        state.lifecycle[0] = int(Lifecycle.BLACK_HOLE)
        state.black_hole_timer[0] = 2
        for stimulus in ((), (0,), ()):
            metrics = step(state, stimulus_slots=stimulus)
            self.assertEqual(
                metrics.active_cells,
                state.lifecycle.count(int(Lifecycle.ACTIVE)),
            )
            self.assertEqual(metrics.active_cells, len(state.active_slots()))

    def test_existing_default_native_slot_golden(self) -> None:
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=0)
        optimizer._evaluate_slot(optimizer.slots[0])
        self.assertEqual(
            digest(optimizer.to_snapshot()),
            "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1",
        )


if __name__ == "__main__":
    unittest.main()
