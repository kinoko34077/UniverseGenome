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
    create_universe,
    fragmentation_split_mask,
    step,
)
from core.rng import event_key, event_u16
from core.geometry import tile_coordinate
from core.runner import build_status
from core.state import Lifecycle, SHAPE_HORIZONTAL, SHAPE_SINGLE, structure_level, structure_shape
from persistence.snapshot import load_snapshot, save_snapshot


ROOT = Path(__file__).resolve().parents[1]


def fragmentation_config(**overrides):
    values = {
        "hp_decay": 0,
        "bond_gain": 0,
        "bond_decay": 0,
        "fragmentation_enabled": True,
        "fragmentation_rate": 0xFFFF,
    }
    values.update(overrides)
    return PhysicsConfig(**values)


class Phase2DFragmentationTests(unittest.TestCase):
    def test_p2d_001_splits_core_and_reuses_a_slot(self):
        config = fragmentation_config()
        state = create_universe(seed=51, config=config)
        core = state.spawn(
            x=0,
            y=0,
            structure=SHAPE_SINGLE << 2,
            latent=0xFFFF,
            hp=101,
            direction=2,
            speed_code=1,
        )
        state.age[core] = 9
        metrics = step(state)

        spatial_address = (tile_coordinate(state.y[core]) << 5) | tile_coordinate(state.x[core])
        local_index = ((state.x[core] & 0xFF) << 8) | (state.y[core] & 0xFF)
        split_mask = fragmentation_split_mask(state.seed, state.generation - 1, spatial_address, local_index)

        self.assertEqual(metrics.fragmentation_count, 1)
        self.assertEqual(state.lifecycle[core], Lifecycle.ACTIVE)
        self.assertEqual(structure_level(state.structure[core]), 1)
        self.assertEqual(state.hp[core], 51)
        self.assertEqual(state.age[core], 4)
        self.assertEqual(state.latent[core], 0xFFFF & ~split_mask)

        fragment = 1
        self.assertEqual(state.lifecycle[fragment], Lifecycle.ACTIVE)
        self.assertEqual(structure_level(state.structure[fragment]), 0)
        self.assertEqual(structure_shape(state.structure[fragment]), SHAPE_SINGLE)
        self.assertEqual(state.hp[fragment], 50)
        self.assertEqual(state.age[fragment], 0)
        self.assertEqual(state.direction[fragment], 6)
        self.assertEqual(state.speed_code[fragment], 1)
        self.assertEqual(state.latent[fragment], 0xFFFF & split_mask)
        self.assertEqual(state.bond_strength[fragment], 0)

        reused = state.spawn(x=16, y=16, hp=10)
        self.assertEqual(reused, 2)

    def test_p2d_002_level_zero_collapse_and_delete_paths(self):
        compound = create_universe(seed=52, config=fragmentation_config())
        compound_slot = compound.spawn(x=0, y=0, structure=SHAPE_HORIZONTAL, hp=100)
        self.assertEqual(step(compound).fragmentation_count, 1)
        self.assertEqual(compound.lifecycle[compound_slot], Lifecycle.ACTIVE)
        self.assertEqual(compound.structure[compound_slot], SHAPE_SINGLE)

        single = create_universe(seed=53, config=fragmentation_config())
        single_slot = single.spawn(x=0, y=0, structure=SHAPE_SINGLE, hp=100)
        self.assertEqual(step(single).fragmentation_count, 1)
        self.assertEqual(single.lifecycle[single_slot], Lifecycle.FREE)

    def test_p2d_003_probability_zero_and_capacity_full_are_noops(self):
        disabled = create_universe(seed=54, config=fragmentation_config(fragmentation_rate=0))
        disabled_slot = disabled.spawn(x=0, y=0, structure=SHAPE_SINGLE << 2, hp=100)
        before = disabled.to_snapshot()
        self.assertEqual(step(disabled).fragmentation_count, 0)
        self.assertEqual(disabled.to_snapshot()["arrays"]["structure"][disabled_slot], before["arrays"]["structure"][disabled_slot])

        full = create_universe(seed=55, config=fragmentation_config(max_cells=2))
        full_slot = full.spawn(x=0, y=0, structure=SHAPE_SINGLE << 2, hp=100)
        other = full.spawn(x=64, y=64, hp=100)
        full.lifecycle[other] = Lifecycle.BLACK_HOLE
        full.black_hole_timer[other] = 2
        self.assertEqual(step(full).fragmentation_count, 0)
        self.assertEqual(full.lifecycle[full_slot], Lifecycle.ACTIVE)

    def test_p2d_004_snapshot_replays_fragmentation(self):
        config = fragmentation_config()
        uninterrupted = create_universe(seed=56, config=config)
        uninterrupted.spawn(x=0, y=0, structure=SHAPE_SINGLE << 2, hp=101, latent=0x1234)
        step(uninterrupted)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phase2d.json"
            save_snapshot(path, uninterrupted)
            resumed = load_snapshot(path)
        self.assertEqual(resumed.config.to_dict(), config.to_dict())
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())
        step(uninterrupted)
        step(resumed)
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())


    def test_p2d_006_fragmentation_chance_is_independent_of_reusable_storage_slot(self):
        seed = next(
            candidate
            for candidate in range(1024)
            if event_u16(event_key(candidate, 0, 0, EVENT_FRAGMENTATION, 0))
            != event_u16(event_key(candidate, 0, 0, EVENT_FRAGMENTATION, 1))
        )
        legacy_a = event_u16(event_key(seed, 0, 0, EVENT_FRAGMENTATION, 0))
        legacy_b = event_u16(event_key(seed, 0, 0, EVENT_FRAGMENTATION, 1))
        rate = (legacy_a + legacy_b) // 2
        if rate <= min(legacy_a, legacy_b):
            rate = min(legacy_a, legacy_b) + 1

        config = fragmentation_config(fragmentation_rate=rate, max_cells=4)

        slot_zero = create_universe(seed=seed, config=config)
        slot_zero.spawn(
            x=40,
            y=56,
            structure=SHAPE_SINGLE,
            hp=100,
            direction=0,
            speed_code=0,
        )

        slot_one = create_universe(seed=seed, config=config)
        dummy = slot_one.spawn(x=200, y=200, hp=100, speed_code=0)
        target = slot_one.spawn(
            x=40,
            y=56,
            structure=SHAPE_SINGLE,
            hp=100,
            direction=0,
            speed_code=0,
        )
        self.assertEqual(target, 1)
        slot_one.free(dummy)

        result_zero = step(slot_zero)
        result_one = step(slot_one)

        self.assertEqual(
            result_zero.fragmentation_count,
            result_one.fragmentation_count,
        )
        self.assertEqual(
            bool(slot_zero.active_slots()),
            bool(slot_one.active_slots()),
        )

    def test_p2d_005_status_and_headless_counter(self):
        raw = json.loads((ROOT / "config" / "default.json").read_text(encoding="utf-8"))
        status = build_status(raw)
        self.assertTrue(status["phase2d_fragmentation_implemented"])
        self.assertEqual(status["next_phase"], "Readiness rerun (#60; Phase 6+ blocked)")
        self.assertTrue(raw["features"]["aging"])

        proc = subprocess.run(
            [sys.executable, "-m", "core.runner", "--config", "config/default.json", "--generations", "2", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        output = json.loads(proc.stdout)
        self.assertIn("fragmentation_count", output["performance"])


if __name__ == "__main__":
    unittest.main()
