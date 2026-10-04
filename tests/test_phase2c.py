from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.physics import PhysicsConfig, create_universe, mix_fusion_latent, step
from core.runner import build_status
from core.state import Lifecycle, SHAPE_HORIZONTAL, SHAPE_SINGLE, structure_level, structure_shape
from persistence.snapshot import load_snapshot, save_snapshot


ROOT = Path(__file__).resolve().parents[1]


def spawn_square(state, *, hp=(100, 200, 200, 50), directions=(2, 2, 2, 2), speeds=(1, 2, 3, 1)):
    slots = []
    for (x, y), cell_hp, direction, speed in zip(
        ((0, 0), (8, 0), (0, 8), (8, 8)), hp, directions, speeds
    ):
        slot = state.spawn(
            x=x,
            y=y,
            structure=SHAPE_SINGLE,
            hp=cell_hp,
            direction=direction,
            speed_code=speed,
            latent=0,
        )
        state.bond_strength[slot] = 32
        slots.append(slot)
    return slots


class Phase2CFusionTests(unittest.TestCase):
    def test_p2c_001_square_fuses_to_upper_core(self):
        config = PhysicsConfig(
            hp_decay=0,
            bond_gain=0,
            bond_decay=0,
            fusion_enabled=True,
            fusion_velocity_threshold=8,
            fusion_bond_threshold=32,
        )
        state = create_universe(seed=41, config=config)
        slots = spawn_square(state)
        for slot, value in zip(slots, (0x0001, 0x0010, 0x0100, 0x1000)):
            state.latent[slot] = value

        metrics = step(state)

        self.assertEqual(metrics.fusion_count, 1)
        target = slots[0]
        self.assertEqual(state.lifecycle[target], Lifecycle.ACTIVE)
        self.assertEqual(structure_level(state.structure[target]), 1)
        self.assertEqual(structure_shape(state.structure[target]), SHAPE_SINGLE)
        self.assertEqual(state.age[target], 0)
        self.assertEqual(state.bond_strength[target], 0)
        self.assertEqual(state.hp[target], 255)
        self.assertEqual(state.direction[target], 2)
        self.assertEqual(state.speed_code[target], 1)
        self.assertEqual(state.latent[target], mix_fusion_latent([0x0001, 0x0010, 0x0100, 0x1000]))
        self.assertEqual(sum(state.lifecycle[slot] == Lifecycle.FREE for slot in slots[1:]), 3)

        reused = state.spawn(x=16, y=16, hp=10)
        self.assertEqual(reused, slots[1])

    def test_p2c_002_ineligible_square_does_not_fuse(self):
        config = PhysicsConfig(
            hp_decay=0,
            bond_gain=0,
            bond_decay=0,
            fusion_enabled=True,
            fusion_velocity_threshold=8,
            fusion_bond_threshold=32,
        )
        state = create_universe(seed=42, config=config)
        slots = spawn_square(state)
        state.bond_strength[slots[-1]] = 31

        metrics = step(state)

        self.assertEqual(metrics.fusion_count, 0)
        self.assertTrue(all(state.lifecycle[slot] == Lifecycle.ACTIVE for slot in slots))

    def test_p2c_003_velocity_and_level_constraints_are_parameterized(self):
        velocity_config = PhysicsConfig(
            hp_decay=0,
            bond_gain=0,
            bond_decay=0,
            fusion_enabled=True,
            fusion_velocity_threshold=0,
            fusion_bond_threshold=32,
        )
        velocity_state = create_universe(seed=43, config=velocity_config)
        velocity_slots = spawn_square(velocity_state, speeds=(1, 0, 0, 0))
        self.assertEqual(step(velocity_state).fusion_count, 0)

        level_state = create_universe(seed=44, config=velocity_config)
        level_slots = spawn_square(level_state)
        level_state.structure[level_slots[-1]] = SHAPE_SINGLE << 2
        self.assertEqual(step(level_state).fusion_count, 0)

        overlap_state = create_universe(seed=46, config=velocity_config)
        overlap_slots = spawn_square(overlap_state)
        overlap_state.structure[overlap_slots[0]] = SHAPE_HORIZONTAL
        self.assertEqual(step(overlap_state).fusion_count, 0)

    def test_p2c_004_snapshot_replays_fusion(self):
        config = PhysicsConfig(hp_decay=0, bond_gain=0, bond_decay=0, fusion_enabled=True, fusion_bond_threshold=1)
        uninterrupted = create_universe(seed=45, config=config)
        spawn_square(uninterrupted)
        step(uninterrupted)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phase2c.json"
            save_snapshot(path, uninterrupted)
            resumed = load_snapshot(path)
        self.assertEqual(resumed.config.to_dict(), config.to_dict())
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())
        step(uninterrupted)
        step(resumed)
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())

    def test_p2c_005_status_and_headless_counter(self):
        raw = json.loads((ROOT / "config" / "default.json").read_text(encoding="utf-8"))
        status = build_status(raw)
        self.assertTrue(status["phase2c_fusion_implemented"])
        self.assertEqual(status["next_phase"], "Readiness rerun (#60; Phase 6+ blocked)")

        proc = subprocess.run(
            [sys.executable, "-m", "core.runner", "--config", "config/default.json", "--generations", "2", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        output = json.loads(proc.stdout)
        self.assertIn("fusion_count", output["performance"])


if __name__ == "__main__":
    unittest.main()
