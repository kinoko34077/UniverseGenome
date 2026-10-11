"""PERF230 P4.7 empty-state physics parity, native selected128 measured separately.

Original long science seed16384 is never exercised here.
"""
from __future__ import annotations

from dataclasses import fields
import unittest
from unittest.mock import patch

from core.physics import PhysicsConfig, StepMetrics, _spawn_noise, create_universe, step
from core.state import Lifecycle, UniverseState


class EmptyStepParityTests(unittest.TestCase):
    def test_empty_default_one_generation_no_unneeded_noise(self):
        config = PhysicsConfig()
        state = create_universe(seed=0, config=config)
        self.assertTrue(all(v == Lifecycle.FREE for v in state.lifecycle))
        before = state.to_snapshot()
        with patch("core.physics._spawn_noise", side_effect=AssertionError("unused noise path")):
            metrics = step(state)
        after = state.to_snapshot()
        self.assertEqual(after["generation"], before["generation"] + 1)
        self.assertEqual(after["arrays"], before["arrays"])
        self.assertEqual(metrics.generation, after["generation"])
        self.assertEqual(metrics.active_cells, 0)
        self.assertEqual(metrics.activity_cost, 0)
        for name in ("collision_count", "collision_pair_evaluations", "bond_contact_count",
                     "latent_transmission_count", "fusion_count", "fragmentation_count",
                     "noise_spawn_count"):
            self.assertEqual(getattr(metrics, name), 0)

    def test_empty_default_matches_original_slow_path(self):
        config = PhysicsConfig()
        candidate = create_universe(seed=7, config=config)
        reference = UniverseState.from_snapshot(candidate.to_snapshot(), config=config)
        # Disable the shortcut through a semantically inert reference route.
        with patch("core.physics._slow_trace_inert", return_value=False):
            original_metrics = step(reference)
        new_metrics = step(candidate)
        self.assertEqual(candidate.to_snapshot(), reference.to_snapshot())
        for field in fields(StepMetrics):
            if field.name != "generations_per_second":
                self.assertEqual(getattr(new_metrics, field.name),
                                 getattr(original_metrics, field.name))

    def test_excluded_states_keep_original_physics(self):
        configurations = (PhysicsConfig(), PhysicsConfig(noise_rate=1),
                          PhysicsConfig(trace_write_cap=1))
        for i, config in enumerate(configurations):
            with self.subTest(i=i):
                state = create_universe(seed=6, config=config)
                if i == 0:
                    state.spawn(x=8, y=16)
                with patch("core.physics._spawn_noise", wraps=_spawn_noise) as noise:
                    step(state)
                    noise.assert_called_once()

    def test_external_stimulus_on_empty_world_keeps_original_path(self):
        state = create_universe(seed=2, config=PhysicsConfig())
        with patch("core.physics._spawn_noise", wraps=_spawn_noise) as noise:
            step(state, stimulus_slots=(0,))
            noise.assert_called_once()

    def test_black_hole_keeps_original_path(self):
        state = create_universe(seed=2, config=PhysicsConfig())
        state.lifecycle[0] = int(Lifecycle.BLACK_HOLE)
        state.black_hole_timer[0] = 2
        with patch("core.physics._spawn_noise", wraps=_spawn_noise) as noise:
            step(state)
            noise.assert_called_once()

    def test_default_config_unchanged(self):
        config = PhysicsConfig()
        state = create_universe(seed=3, config=config)
        before = config.to_dict()
        step(state)
        self.assertEqual(config.to_dict(), before)


if __name__ == "__main__":
    unittest.main()
