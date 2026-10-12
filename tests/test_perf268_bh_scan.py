"""P6.2 independent indexed source oracle for BLACK_HOLE scan; no D16 science."""
from __future__ import annotations

from dataclasses import asdict
import unittest
from unittest.mock import patch

import core.physics as physics
from core.physics import PhysicsConfig, create_universe
from core.state import Lifecycle, UniverseState
from benchmarks.perf268_bh_scan_ab import old_index_revival

BH = int(Lifecycle.BLACK_HOLE)
FREE = int(Lifecycle.FREE)
ACTIVE = int(Lifecycle.ACTIVE)


class Perf268PackedBlackHoleParity(unittest.TestCase):
    def test_native_zero_sparse_dense_and_mutating_blackholes(self):
        for capacity in (1, 2, 16, 64, 1024):
            patterns = [
                (), (0,), (capacity-1,), tuple(range(0,capacity,7)),
                tuple(range(capacity))
            ]
            for pattern in patterns:
                with self.subTest(capacity=capacity, pattern_len=len(pattern)):
                    state = UniverseState(seed=3, max_cells=capacity)
                    state.lifecycle = [FREE] * capacity
                    for idx in pattern:
                        state.lifecycle[idx] = BH
                    before = list(state.lifecycle)
                    actual = physics._local_revival_slots(state)
                    expected = old_index_revival(state)
                    self.assertEqual(tuple(actual.black_hole_indices), tuple(expected.black_hole_indices))
                    self.assertEqual(actual, expected)
                    self.assertEqual(state.lifecycle, before)
                    if capacity > 1:
                        state.lifecycle[capacity - 1] = Lifecycle.ACTIVE
                        again = physics._local_revival_slots(state)
                        self.assertEqual(tuple(again.black_hole_indices),
                                         tuple(old_index_revival(state).black_hole_indices))

    def test_original_index_semantics_for_nonbyte_lifecycle(self):
        for nonbyte in (-1, 256, 999, 1.5, "legacy"):
            with self.subTest(nonbyte=nonbyte):
                state = UniverseState(seed=0, max_cells=8)
                state.lifecycle = [FREE, BH, ACTIVE, FREE, nonbyte, BH, FREE, ACTIVE]
                fast = physics._local_revival_slots(state)
                legacy = old_index_revival(state)
                self.assertEqual(fast, legacy)
                self.assertEqual(tuple(fast.black_hole_indices), tuple(legacy.black_hole_indices))

    def test_original_physical_revival_and_grace_timeout(self):
        for density in (0, 4, 32):
            config = PhysicsConfig(initial_density=density, hp_decay=1, black_hole_grace=2)
            original = create_universe(seed=7, config=config)
            proposed = create_universe(seed=7, config=config)
            for generation in range(5):
                if generation == 0:
                    for state in (original, proposed):
                        slot = state.spawn(x=0, y=0, hp=1)
                        state.lifecycle[slot] = BH
                        state.black_hole_timer[slot] = 2
                        state.spawn(x=0, y=0, latent=1, hp=255)
                with patch.object(physics, "_local_revival_slots", old_index_revival):
                    previous = asdict(physics.step(original))
                current = asdict(physics.step(proposed))
                previous.pop("generations_per_second")
                current.pop("generations_per_second")
                self.assertEqual(current, previous)
                self.assertEqual(proposed.to_snapshot(), original.to_snapshot())


if __name__ == "__main__":
    unittest.main()
