from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.physics import (
    EVENT_FRAGMENTATION,
    PhysicsConfig,
    age_class,
    age_scaled_fragmentation_rate,
    create_universe,
    step,
)
from core.rng import event_key, event_u16
from core.runner import build_status
from core.state import Lifecycle, SHAPE_SINGLE
from persistence.snapshot import load_snapshot, save_snapshot


ROOT = Path(__file__).resolve().parents[1]


def aging_config(**overrides):
    values = {
        "hp_decay": 0,
        "bond_gain": 0,
        "bond_decay": 0,
        "fragmentation_enabled": True,
        "fragmentation_rate": 100,
        "aging_enabled": True,
    }
    values.update(overrides)
    return PhysicsConfig(**values)


class Phase2EAgingTests(unittest.TestCase):
    def test_p2e_001_age_class_boundaries_are_safe_and_exact(self):
        expected = {
            0: 0,
            1: 0,
            2: 1,
            3: 1,
            4: 2,
            7: 2,
            8: 3,
            15: 3,
            16: 4,
        }
        for age, expected_class in expected.items():
            self.assertEqual(age_class(age), expected_class, age)

    def test_p2e_002_age_pressure_scales_and_saturates(self):
        self.assertEqual(age_scaled_fragmentation_rate(100, 0), 100)
        self.assertEqual(age_scaled_fragmentation_rate(100, 1), 100)
        self.assertEqual(age_scaled_fragmentation_rate(100, 2), 200)
        self.assertEqual(age_scaled_fragmentation_rate(100, 4), 400)
        self.assertEqual(age_scaled_fragmentation_rate(0xFFFF, 8), 0xFFFF)
        self.assertEqual(age_scaled_fragmentation_rate(100, 8, aging_enabled=False), 100)

    def test_p2e_003_old_structure_has_higher_deterministic_pressure(self):
        seed = next(
            candidate
            for candidate in range(10000)
            if 100
            <= event_u16(
                event_key(
                    candidate,
                    0,
                    0,
                    EVENT_FRAGMENTATION,
                    0x10000,
                )
            )
            < 400
        )
        young = create_universe(seed=seed, config=aging_config())
        old = create_universe(seed=seed, config=aging_config())
        young.spawn(x=0, y=0, structure=SHAPE_SINGLE << 2, hp=100)
        old_slot = old.spawn(x=0, y=0, structure=SHAPE_SINGLE << 2, hp=100)
        old.age[old_slot] = 4

        self.assertEqual(step(young).fragmentation_count, 0)
        self.assertEqual(step(old).fragmentation_count, 1)

    def test_p2e_004_snapshot_replays_age_pressure(self):
        config = aging_config(fragmentation_rate=0xFFFF)
        uninterrupted = create_universe(seed=61, config=config)
        slot = uninterrupted.spawn(x=0, y=0, structure=SHAPE_SINGLE << 2, hp=101)
        uninterrupted.age[slot] = 8
        step(uninterrupted)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phase2e.json"
            save_snapshot(path, uninterrupted)
            resumed = load_snapshot(path)
        self.assertEqual(resumed.config.to_dict(), config.to_dict())
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())
        for _ in range(3):
            step(uninterrupted)
            step(resumed)
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())

    def test_p2e_005_status_and_headless_runner(self):
        raw = json.loads((ROOT / "config" / "default.json").read_text(encoding="utf-8"))
        status = build_status(raw)
        self.assertTrue(status["phase2e_aging_implemented"])
        self.assertEqual(status["next_phase"], "Phase 6.5 noise robustness (bounded child Issue required)")
        self.assertTrue(raw["features"]["aging"])
        self.assertTrue(raw["features"]["multi_universe_search"])

        proc = subprocess.run(
            [sys.executable, "-m", "core.runner", "--config", "config/default.json", "--generations", "2", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        output = json.loads(proc.stdout)
        self.assertIn("fragmentation_count", output["performance"])
        self.assertEqual(output["performance"]["generations"], 2)


if __name__ == "__main__":
    unittest.main()
