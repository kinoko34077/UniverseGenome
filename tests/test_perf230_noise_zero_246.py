"""PERF230 P4.6 zero-rate noise source equivalence; D16 science is NOT run."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from core.physics import PhysicsConfig, _spawn_noise, create_universe


class ZeroNoiseFastpathTests(unittest.TestCase):
    def test_zero_noise_does_not_compute_unused_hash_or_mutate_state(self) -> None:
        config = PhysicsConfig(noise_rate=0)
        state = create_universe(seed=21, config=config)
        old = state.to_snapshot()
        # This is intentionally RED on the original implementation.
        with patch("core.physics.event_key", side_effect=AssertionError("unused chance hash")):
            self.assertEqual(_spawn_noise(state, config, state.generation), 0)
        self.assertEqual(old, state.to_snapshot())

    def test_positive_noise_preserves_unsigned_threshold_path(self) -> None:
        config = PhysicsConfig(noise_rate=1)
        state = create_universe(seed=21, config=config)
        old = state.to_snapshot()
        # The original positive-rate path must still compute a chance event.
        with patch("core.physics.event_u16", return_value=65535) as chance:
            self.assertEqual(_spawn_noise(state, config, state.generation), 0)
            chance.assert_called_once()
        self.assertEqual(old, state.to_snapshot())


if __name__ == "__main__":
    unittest.main()
