"""#172 R1 safety gates: local physics, parity, data-role and closed frozen mode."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import core.physics as physics
from core.state import UniverseState
from research.r1_causal_isolation_172 import (
    FACTORS, POOL, RATES, ResearchIntervention, h0_snapshots, load_frozen,
    qualification,
)


class R1CausalIsolation172Tests(unittest.TestCase):
    def config(self):
        return physics.PhysicsConfig(
            initial_density=0, trace_write_cap=32,
            trace_transfer_cap=8, trace_discharge_cap=16,
            trace_decay_rate=256, trace_bonus_shift=5,
        )

    def local_pair(self):
        config = self.config()
        state = UniverseState(max_cells=config.max_cells, seed=7, config=config)
        a = state.spawn(x=8, y=8)
        b = state.spawn(x=8, y=8)
        state.slow_trace[a] = 10
        state.slow_trace[b] = 3
        return state, a, b

    def test_pass_through_nonmutating_sham(self):
        config = self.config()
        left = physics.create_universe(seed=7, config=config)
        right = physics.create_universe(seed=7, config=config)
        physics.step(left)
        with ResearchIntervention("sham").attach():
            physics.step(right)
        self.assertEqual(left.to_snapshot(), right.to_snapshot())

    def test_local_free_trace_relay_without_ghost_free_cell(self):
        state, a, b = self.local_pair()
        with ResearchIntervention("free_local_relay").attach():
            state.free(a)
        self.assertEqual(state.slow_trace[a], 0)
        self.assertEqual(state.slow_trace[b], 13)
        self.assertEqual(state.lifecycle[a], 0)
        control, a2, b2 = self.local_pair()
        with ResearchIntervention("sham").attach():
            control.free(a2)
        self.assertEqual(control.slow_trace[b2], 3)

    def test_transfer_and_write_isolated_at_existing_operator(self):
        a, i, j = self.local_pair()
        b, _, _ = self.local_pair()
        with ResearchIntervention("transfer_off").attach():
            physics._transfer_slow_trace(a, a.config, ((i, j),))
        physics._transfer_slow_trace(b, b.config, ((i, j),))
        self.assertEqual([a.slow_trace[i], a.slow_trace[j]], [10, 3])
        self.assertNotEqual([b.slow_trace[i], b.slow_trace[j]], [10, 3])
        with ResearchIntervention("post_h0_write_off").attach():
            physics._apply_slow_trace_writes(a, a.config, {i: 32})
        self.assertEqual(a.slow_trace[i], 10)

    def test_read_ablation_targets_mask_not_latent_direct_write(self):
        state, a, b = self.local_pair()
        state.slow_trace[a] = 224
        state.bond_strength[a] = 128
        before = list(state.latent)
        physical = physics.transmission_mask(
            7, 1, 17, (a, b), 128, participant=state, source_trace=224
        )
        zero = physics.transmission_mask(
            7, 1, 17, (a, b), 128, participant=state, source_trace=0
        )
        self.assertNotEqual(physical, zero)
        with ResearchIntervention("read_bonus_off").attach():
            changed = physics.transmission_mask(
                7, 1, 17, (a, b), 128, participant=state, source_trace=224
            )
        self.assertEqual(changed, zero)
        self.assertEqual(state.latent, before)

    def test_seed_roles_frozen_and_h0_only(self):
        self.assertEqual(POOL[0], 160)
        self.assertEqual(POOL[-1], 543)
        self.assertEqual(RATES, (0, 256))
        self.assertEqual(len(FACTORS), 4)
        with self.assertRaises(ValueError):
            h0_snapshots(96)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                load_frozen(Path(tmp) / "absent.json")

    def test_qualification_has_no_long_horizon_fields(self):
        # This computes h0-only training input/teacher differences and nothing later.
        data = qualification()
        self.assertEqual(data["horizon_max"], 0)
        self.assertEqual(len(data["positive_seeds"]), 24)
        self.assertEqual(len(data["negative_seeds"]), 8)
        self.assertFalse(set(data["positive_seeds"]) & set(data["negative_seeds"]))
        self.assertTrue(all(160 <= seed <= 543
                            for seed in data["positive_seeds"] + data["negative_seeds"]))
        self.assertFalse(data["learning_claim"])


if __name__ == "__main__":
    unittest.main()
