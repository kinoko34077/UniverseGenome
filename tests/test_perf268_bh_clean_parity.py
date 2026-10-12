"""P6.5 clean source parity tests for native BLACK_HOLE packed index."""
from __future__ import annotations
from dataclasses import asdict
import unittest
from unittest.mock import patch

import core.physics as physics
from core.physics import PhysicsConfig, create_universe
from core.state import Lifecycle, UniverseState
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer


def original_bh_scan(state):
    """Frozen accepted main original list.index BLACK_HOLE index enumeration."""
    slots = []
    start = 0
    while True:
        try:
            slot = state.lifecycle.index(int(Lifecycle.BLACK_HOLE), start)
        except ValueError:
            break
        slots.append(slot)
        start = slot + 1
    if not slots:
        return physics._RevivalSlots((), slots)
    active = state.active_slots()
    revived = set()
    for slot in slots:
        footprint = physics.destination_footprint(state.structure[slot], state.x[slot], state.y[slot])
        for participant in active:
            if not (state.latent[participant] or state.bond_strength[participant]):
                continue
            participant_footprint = physics.destination_footprint(
                state.structure[participant], state.x[participant], state.y[participant]
            )
            if footprint.intersection(participant_footprint):
                revived.add(slot)
                break
    return physics._RevivalSlots(revived, slots)


class BHScanCleanParityTests(unittest.TestCase):
    def test_sparse_dense_and_nonbyte_legacy_exact(self):
        for capacity in (1, 2, 16, 64, 1024):
            for pattern in ((), (0,), (capacity-1,), tuple(range(0, capacity, 7)),
                            tuple(range(capacity))):
                state = UniverseState(seed=1, max_cells=capacity)
                state.lifecycle = [int(Lifecycle.FREE)] * capacity
                for slot in pattern:
                    state.lifecycle[slot] = int(Lifecycle.BLACK_HOLE)
                before = list(state.lifecycle)
                fast = physics._local_revival_slots(state)
                old = original_bh_scan(state)
                self.assertEqual(fast, old)
                self.assertEqual(fast.black_hole_indices, old.black_hole_indices)
                self.assertEqual(state.lifecycle, before)
        for exotic in (-1, 256, 1.5, "legacy"):
            state = UniverseState(seed=3, max_cells=8)
            state.lifecycle = [0, 2, 1, exotic, 2, 0, 1, 0]
            fast = physics._local_revival_slots(state)
            old = original_bh_scan(state)
            self.assertEqual(fast, old)
            self.assertEqual(fast.black_hole_indices, old.black_hole_indices)

    def test_original_black_hole_revival_expiry_full_physics_parity(self):
        for density in (0, 4, 32):
            config = PhysicsConfig(initial_density=density, hp_decay=1, black_hole_grace=2)
            old_state = create_universe(seed=7, config=config)
            new_state = create_universe(seed=7, config=config)
            for generation in range(5):
                if generation == 0:
                    for state in (old_state, new_state):
                        slot = state.spawn(x=0, y=0, hp=1)
                        state.lifecycle[slot] = int(Lifecycle.BLACK_HOLE)
                        state.black_hole_timer[slot] = 2
                        state.spawn(x=0, y=0, latent=1, hp=255)
                with patch.object(physics, "_local_revival_slots", original_bh_scan):
                    old_metrics = asdict(physics.step(old_state))
                new_metrics = asdict(physics.step(new_state))
                for metrics in (old_metrics, new_metrics):
                    metrics.pop("generations_per_second")
                self.assertEqual(new_metrics, old_metrics)
                self.assertEqual(new_state.to_snapshot(), old_state.to_snapshot())

    def test_original_full_optimizer_v7_default_native_slot0_golden(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=0)
        optimizer._evaluate_slot(optimizer.slots[0])
        self.assertEqual(
            digest(optimizer.to_snapshot()),
            "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1",
        )


if __name__ == "__main__":
    unittest.main()
