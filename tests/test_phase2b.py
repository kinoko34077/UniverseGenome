from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.physics import (
    PhysicsConfig,
    apply_latent_operator,
    create_universe,
    step,
    transmission_mask,
)
from core.runner import build_status
from persistence.snapshot import load_snapshot, save_snapshot


ROOT = Path(__file__).resolve().parents[1]


class Phase2BLatentTests(unittest.TestCase):
    def test_p2b_001_all_operator_formulas_are_16_bit(self):
        source = 0x1234
        destination = 0xA5A5
        mask = 0x0F0F

        self.assertEqual(
            apply_latent_operator("masked_copy", source, destination, mask),
            (destination & ~mask) | (source & mask),
        )
        self.assertEqual(
            apply_latent_operator("masked_xor", source, destination, mask),
            destination ^ (source & mask),
        )
        rotated = ((source << 4) | (source >> 12)) & 0xFFFF
        self.assertEqual(
            apply_latent_operator("rotate_copy", source, destination, mask, rotate_amount=4),
            (destination & ~mask) | (rotated & mask),
        )
        self.assertEqual(
            apply_latent_operator("masked_and", source, destination, mask),
            destination & (source | (~mask & 0xFFFF)),
        )

    def test_p2b_002_mask_width_and_determinism(self):
        first = transmission_mask(seed=31, generation=4, address=9, pair=(2, 7), bond_strength=0)
        wide = transmission_mask(seed=31, generation=4, address=9, pair=(2, 7), bond_strength=255)
        again = transmission_mask(seed=31, generation=4, address=9, pair=(2, 7), bond_strength=255)
        self.assertEqual(first.bit_count(), 1)
        self.assertEqual(wide.bit_count(), 16)
        self.assertEqual(wide, 0xFFFF)
        self.assertEqual(wide, again)

    def test_p2f_transmission_event_key_does_not_use_storage_slot_pair(self):
        first = transmission_mask(seed=31, generation=4, address=9, pair=(2, 7), bond_strength=16)
        equivalent = transmission_mask(seed=31, generation=4, address=9, pair=(99, 101), bond_strength=16)
        self.assertEqual(first, equivalent)

    def test_p2b_003_contact_transmits_synchronously_and_recovers_hp(self):
        config = PhysicsConfig(
            hp_decay=0,
            recovery_hp=7,
            bond_gain=16,
            bond_decay=0,
            latent_operator="masked_copy",
        )
        state = create_universe(seed=32, config=config)
        source = state.spawn(x=0, y=0, direction=0, speed_code=0, hp=10, latent=0xFFFF)
        destination = state.spawn(x=1, y=0, direction=0, speed_code=0, hp=10, latent=0x0000)
        source_mask = transmission_mask(
            state.seed,
            state.generation,
            0,
            (source, destination),
            bond_strength=16,
            participant=state,
        )
        destination_mask = transmission_mask(
            state.seed,
            state.generation,
            0,
            (destination, source),
            bond_strength=16,
            participant=state,
        )

        metrics = step(state)

        self.assertEqual(metrics.latent_transmission_count, 1)
        self.assertEqual(state.latent[source], apply_latent_operator("masked_copy", 0x0000, 0xFFFF, destination_mask))
        self.assertEqual(state.latent[destination], apply_latent_operator("masked_copy", 0xFFFF, 0x0000, source_mask))
        self.assertEqual(state.hp[source], 17)
        self.assertEqual(state.hp[destination], 17)

    def test_p2b_004_snapshot_restores_operator_and_continuation(self):
        config = PhysicsConfig(
            hp_decay=0,
            bond_gain=16,
            bond_decay=0,
            latent_operator="rotate_copy",
            rotate_amount=12,
        )
        uninterrupted = create_universe(seed=33, config=config)
        uninterrupted.spawn(x=0, y=0, direction=0, speed_code=0, hp=255, latent=0x1234)
        uninterrupted.spawn(x=1, y=0, direction=0, speed_code=0, hp=255, latent=0x5678)
        step(uninterrupted)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phase2b.json"
            save_snapshot(path, uninterrupted)
            resumed = load_snapshot(path)
        self.assertEqual(resumed.config.to_dict(), config.to_dict())
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())
        for _ in range(3):
            step(uninterrupted)
            step(resumed)
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())

    def test_p2b_005_three_arrivals_keep_transmission_bounded(self):
        config = PhysicsConfig(hp_decay=0, bond_gain=1, bond_decay=0)
        state = create_universe(seed=34, config=config)
        for x in (0, 1, 2):
            state.spawn(x=x, y=0, direction=0, speed_code=0, hp=255, latent=x + 1)

        metrics = step(state)

        self.assertEqual(metrics.collision_pair_evaluations, 1)
        self.assertEqual(metrics.latent_transmission_count, 1)

    def test_p2b_006_status_and_headless_counter(self):
        raw = json.loads((ROOT / "config" / "default.json").read_text(encoding="utf-8"))
        status = build_status(raw)
        self.assertTrue(status["phase2b_latent_operators_implemented"])
        self.assertEqual(status["next_phase"], "Phase 6+ roadmap review (explicit next capability decision required)")

        proc = subprocess.run(
            [sys.executable, "-m", "core.runner", "--config", "config/default.json", "--generations", "2", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        output = json.loads(proc.stdout)
        self.assertIn("latent_transmission_count", output["performance"])


if __name__ == "__main__":
    unittest.main()
