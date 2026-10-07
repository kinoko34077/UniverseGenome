from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from core.physics import PhysicsConfig, create_universe
from research.slow_trace_persistence_140 import (
    PROFILE,
    PRIMARY_DENSITY32_SEEDS,
    build_active_config,
    run_case,
    snapshot_diff,
)


ROOT = Path(__file__).resolve().parents[1]


class SlowTracePersistence140Tests(unittest.TestCase):
    def config_payload(self) -> dict:
        return json.loads(
            (ROOT / "config" / "default.json").read_text(encoding="utf-8")
        )

    def experiment_payload(self) -> dict:
        return json.loads(
            (ROOT / "config" / "experiment_v0_1.json").read_text(encoding="utf-8")
        )

    def test_profile_is_exact_and_in_memory_only(self):
        payload = self.config_payload()
        before = copy.deepcopy(payload)
        config = build_active_config(payload, density=32)
        self.assertEqual(payload, before)
        self.assertEqual(config.initial_density, 32)
        for key, value in PROFILE.items():
            self.assertEqual(getattr(config, key), value)

        default = PhysicsConfig.from_mapping(payload)
        self.assertEqual(default.trace_write_cap, 0)
        self.assertEqual(default.trace_transfer_cap, 0)
        self.assertEqual(default.trace_discharge_cap, 0)
        self.assertEqual(default.trace_decay_rate, 0)
        self.assertEqual(default.trace_bonus_shift, 8)

    def test_snapshot_diff_includes_slow_trace(self):
        config = build_active_config(self.config_payload(), density=32)
        first = create_universe(seed=900, config=config)
        slot = first.active_slots()[0]
        second = create_universe(seed=900, config=config)
        second.slow_trace[slot] = 1
        diff = snapshot_diff(first.to_snapshot(), second.to_snapshot())
        self.assertTrue(diff["different"])
        self.assertEqual(diff["fields"]["slow_trace"]["slot_ids"], [slot])

    def test_short_primary_replay_and_raw_equivalence(self):
        case = run_case(
            seed=PRIMARY_DENSITY32_SEEDS[0],
            role="density32_primary",
            config_payload=self.config_payload(),
            experiment_payload=self.experiment_payload(),
            verify=True,
            max_horizon=1,
        )
        self.assertTrue(case["replay_match"])
        self.assertTrue(case["raw_instrumented_match"])
        self.assertEqual(case["profile"], PROFILE)
        self.assertIn("slow_trace", case["checkpoints"]["0"]["comparisons"]["b_vs_h"]["fields"])


if __name__ == "__main__":
    unittest.main()
