from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.physics import (
    PhysicsConfig,
    create_universe,
    destination_footprint,
    relative_velocity,
    speed_code_for_magnitude,
    step,
)
from core.state import Lifecycle
from persistence.snapshot import load_snapshot, save_snapshot


ROOT = Path(__file__).resolve().parents[1]


class Phase1PhysicsTests(unittest.TestCase):
    def test_p1_001_deterministic_replay(self):
        config = PhysicsConfig(noise_rate=4096, noise_attempts=3, hp_decay=1)
        left = create_universe(seed=17, config=config)
        right = create_universe(seed=17, config=config)
        left.spawn(x=0, y=0, direction=2, speed_code=3, hp=200)
        right.spawn(x=0, y=0, direction=2, speed_code=3, hp=200)
        for _ in range(20):
            step(left, stimulus_slots=())
            step(right, stimulus_slots=())
        self.assertEqual(left.to_snapshot(), right.to_snapshot())

    def test_p1_002_toroidal_wrap(self):
        state = create_universe(seed=1)
        slot = state.spawn(x=255, y=0, direction=2, speed_code=speed_code_for_magnitude(1), hp=10)
        step(state)
        self.assertEqual((state.x[slot], state.y[slot]), (0, 0))

        cases = ((0, 0, 6, 1, 255, 0), (0, 255, 4, 1, 0, 0), (0, 0, 0, 1, 0, 255))
        for x, y, direction, speed_code, expected_x, expected_y in cases:
            wrapped = create_universe(seed=direction)
            cell = wrapped.spawn(x=x, y=y, direction=direction, speed_code=speed_code, hp=10)
            step(wrapped)
            self.assertEqual((wrapped.x[cell], wrapped.y[cell]), (expected_x, expected_y))

    def test_p1_003_all_supported_speeds(self):
        expected = [0, 1, 2, 4, 8, 16, 32, 64]
        for code, displacement in enumerate(expected):
            state = create_universe(seed=code)
            slot = state.spawn(x=0, y=8, direction=2, speed_code=code, hp=10)
            step(state)
            self.assertEqual(state.x[slot], displacement, code)

    def test_p1_004_destination_only_tunneling_and_footprint(self):
        config = PhysicsConfig(collision_threshold=0, collision_damage=100)
        tunneling = create_universe(seed=2, config=config)
        mover = tunneling.spawn(x=0, y=0, direction=2, speed_code=7, hp=100)
        middle = tunneling.spawn(x=32, y=0, direction=0, speed_code=0, hp=100)
        metrics = step(tunneling)
        self.assertEqual(metrics.collision_count, 0)
        self.assertEqual(tunneling.hp[middle], 100)
        self.assertEqual(destination_footprint(tunneling.structure[mover], tunneling.x[mover], tunneling.y[mover]), {(8, 0)})

        destination = create_universe(seed=2, config=config)
        destination.spawn(x=0, y=0, direction=2, speed_code=7, hp=100)
        target = destination.spawn(x=64, y=0, direction=0, speed_code=0, hp=100)
        metrics = step(destination)
        self.assertEqual(metrics.collision_count, 1)
        self.assertLess(destination.hp[target], 100)

    def test_p1_005_noise_is_deterministic(self):
        config = PhysicsConfig(noise_rate=65535, noise_attempts=4, hp_decay=0)
        left = create_universe(seed=99, config=config)
        right = create_universe(seed=99, config=config)
        self.assertEqual(step(left).noise_spawn_count, 4)
        self.assertEqual(step(right).noise_spawn_count, 4)
        self.assertEqual(left.to_snapshot(), right.to_snapshot())

    def test_p1_005_full_capacity_discards_noise_without_growth(self):
        config = PhysicsConfig(max_cells=1, noise_rate=65535, noise_attempts=4)
        state = create_universe(seed=100, config=config)
        state.spawn(x=0, y=0, hp=255)
        metrics = step(state)
        self.assertEqual(metrics.noise_spawn_count, 0)
        self.assertEqual(len(state.lifecycle), 1)

    def test_p1_006_three_or_more_arrivals_are_bounded(self):
        config = PhysicsConfig(collision_threshold=0, collision_damage=1)
        state = create_universe(seed=3, config=config)
        for x in (0, 1, 2):
            state.spawn(x=x, y=0, direction=2, speed_code=0, hp=100)
        metrics = step(state)
        self.assertEqual(metrics.collision_count, 1)
        self.assertEqual(metrics.collision_pair_evaluations, 1)

    def test_p1_007_black_hole_recovery_and_deletion(self):
        config = PhysicsConfig(hp_decay=1, black_hole_grace=2, recovery_hp=32)
        state = create_universe(seed=4, config=config)
        recoverable = state.spawn(x=0, y=0, direction=0, speed_code=0, hp=1)
        doomed = state.spawn(x=8, y=0, direction=0, speed_code=0, hp=1)
        step(state)
        self.assertEqual(state.lifecycle[recoverable], Lifecycle.BLACK_HOLE)
        self.assertEqual(state.lifecycle[doomed], Lifecycle.BLACK_HOLE)
        step(state, stimulus_slots=[recoverable])
        self.assertEqual(state.lifecycle[recoverable], Lifecycle.ACTIVE)
        self.assertEqual(state.hp[recoverable], 31)
        step(state)
        step(state)
        self.assertEqual(state.lifecycle[doomed], Lifecycle.FREE)
        reused = state.spawn(x=16, y=0, hp=10)
        self.assertEqual(reused, doomed)

    def test_p1_008_snapshot_roundtrip_continuation(self):
        config = PhysicsConfig(noise_rate=8192, noise_attempts=2, hp_decay=1)
        uninterrupted = create_universe(seed=8, config=config)
        uninterrupted.spawn(x=7, y=9, direction=3, speed_code=4, hp=200)
        for _ in range(4):
            step(uninterrupted)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phase1.json"
            save_snapshot(path, uninterrupted)
            resumed = load_snapshot(path)
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())
        for _ in range(8):
            step(uninterrupted)
            step(resumed)
        self.assertEqual(resumed.to_snapshot(), uninterrupted.to_snapshot())

    def test_p1_009_headless_runner(self):
        proc = subprocess.run(
            [sys.executable, "-m", "core.runner", "--config", "config/default.json", "--generations", "3", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        status = json.loads(proc.stdout)
        self.assertEqual(status["phase"], 5)
        self.assertEqual(status["generations"], 3)
        self.assertIn("active_cells", status["performance"])

    def test_p1_010_performance_counters_and_direction_aware_velocity(self):
        self.assertGreater(relative_velocity(2, 4, 6, 4), 0)
        self.assertEqual(relative_velocity(2, 4, 2, 4), 0)
        state = create_universe(seed=10)
        state.spawn(x=0, y=0, direction=2, speed_code=0, hp=10)
        metrics = step(state)
        self.assertIsNotNone(metrics.generations_per_second)
        self.assertGreaterEqual(metrics.active_cells, 0)


if __name__ == "__main__":
    unittest.main()
