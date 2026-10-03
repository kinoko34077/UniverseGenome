from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.physics import PhysicsConfig, create_universe, step
from core.runner import build_status
from persistence.snapshot import load_snapshot, save_snapshot


ROOT = Path(__file__).resolve().parents[1]


class Phase2ABondTests(unittest.TestCase):
    def test_p2a_001_compatible_contact_saturates_bond_gain(self):
        config = PhysicsConfig(
            hp_decay=0,
            bond_gain=10,
            bond_decay=3,
            bond_velocity_threshold=8,
        )
        state = create_universe(seed=21, config=config)
        first = state.spawn(x=0, y=0, direction=2, speed_code=0, hp=255)
        second = state.spawn(x=1, y=0, direction=2, speed_code=0, hp=255)
        state.bond_strength[first] = 250
        state.bond_strength[second] = 1

        metrics = step(state)

        self.assertEqual(metrics.bond_contact_count, 1)
        self.assertEqual(state.bond_strength[first], 255)
        self.assertEqual(state.bond_strength[second], 11)

    def test_p2a_002_non_contact_and_incompatible_contact_decay(self):
        config = PhysicsConfig(
            hp_decay=0,
            bond_gain=10,
            bond_decay=3,
            bond_velocity_threshold=8,
            collision_threshold=100,
        )
        state = create_universe(seed=22, config=config)
        non_contact = state.spawn(x=0, y=0, direction=0, speed_code=0, hp=255)
        fast_first = state.spawn(x=0, y=8, direction=2, speed_code=3, hp=255)
        fast_second = state.spawn(x=16, y=8, direction=6, speed_code=3, hp=255)
        state.bond_strength[non_contact] = 2
        state.bond_strength[fast_first] = 20
        state.bond_strength[fast_second] = 1

        metrics = step(state)

        self.assertEqual(metrics.bond_contact_count, 0)
        self.assertEqual(state.bond_strength[non_contact], 0)
        self.assertEqual(state.bond_strength[fast_first], 17)
        self.assertEqual(state.bond_strength[fast_second], 0)

    def test_p2a_003_three_arrivals_keep_bond_work_bounded(self):
        config = PhysicsConfig(hp_decay=0, bond_gain=1, bond_decay=1)
        state = create_universe(seed=23, config=config)
        for x in (0, 1, 2):
            state.spawn(x=x, y=0, direction=0, speed_code=0, hp=255)

        metrics = step(state)

        self.assertEqual(metrics.collision_pair_evaluations, 1)
        self.assertEqual(metrics.bond_contact_count, 1)
        self.assertEqual(sum(value > 0 for value in state.bond_strength), 2)

    def test_p2a_004_snapshot_restores_bond_config_and_continuation(self):
        config = PhysicsConfig(hp_decay=0, bond_gain=7, bond_decay=2)
        uninterrupted = create_universe(seed=24, config=config)
        uninterrupted.spawn(x=0, y=0, direction=0, speed_code=0, hp=255)
        uninterrupted.spawn(x=1, y=0, direction=0, speed_code=0, hp=255)
        for _ in range(2):
            step(uninterrupted)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phase2a.json"
            save_snapshot(path, uninterrupted)
            resumed = load_snapshot(path)

        self.assertEqual(resumed.config.to_dict(), config.to_dict())
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())
        for _ in range(3):
            step(uninterrupted)
            step(resumed)
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())

    def test_p2a_005_status_and_headless_counter(self):
        raw = json.loads((ROOT / "config" / "default.json").read_text(encoding="utf-8"))
        status = build_status(raw)
        self.assertTrue(status["phase2a_bond_physics_implemented"])
        self.assertTrue(status["phase2a_bond_physics_implemented"])

        proc = subprocess.run(
            [sys.executable, "-m", "core.runner", "--config", "config/default.json", "--generations", "2", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        output = json.loads(proc.stdout)
        self.assertIn("bond_contact_count", output["performance"])


if __name__ == "__main__":
    unittest.main()
