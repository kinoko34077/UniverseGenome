from __future__ import annotations

import json
from pathlib import Path
import unittest

from core.runner import load_config
from research.memory_coupling_audit_122 import (
    CHECKPOINT_GENERATIONS,
    NO_WRITE_DENSITY32_SEEDS,
    PRIMARY_DENSITY32_SEEDS,
    TEACHER_B,
    TEACHER_H,
    run_case,
)


class MemoryCouplingAudit122Tests(unittest.TestCase):
    def test_protocol_freeze_matches_issue_122(self) -> None:
        self.assertEqual((TEACHER_B, TEACHER_H), (66, 8))
        self.assertEqual(CHECKPOINT_GENERATIONS, (0, 1, 10, 100, 1000))
        self.assertEqual(
            PRIMARY_DENSITY32_SEEDS,
            (0, 5, 8, 9, 12, 14, 18, 19, 20, 22, 24, 29),
        )
        self.assertEqual(len(NO_WRITE_DENSITY32_SEEDS), 20)
        self.assertTrue(
            set(PRIMARY_DENSITY32_SEEDS).isdisjoint(NO_WRITE_DENSITY32_SEEDS)
        )
        self.assertEqual(
            set(PRIMARY_DENSITY32_SEEDS) | set(NO_WRITE_DENSITY32_SEEDS),
            set(range(32)),
        )

    def test_primary_case_reconfirms_t0_without_asserting_persistence_outcome(self) -> None:
        config_payload = load_config(Path("config/default.json"))
        experiment_payload = json.loads(
            Path("config/experiment_v0_1.json").read_text(encoding="utf-8")
        )
        case = run_case(
            seed=0,
            density=32,
            config_payload=config_payload,
            experiment_payload=experiment_payload,
            checkpoint_generations=(0, 1, 10),
        )
        self.assertTrue(case["replay_match"])
        self.assertTrue(case["raw_instrumented_match"])
        self.assertTrue(case["cohort"]["expected_primary_density32"])
        self.assertTrue(case["checkpoints"]["t0"]["b_vs_h"]["different"])
        for key in ("t0", "plus_1", "plus_10"):
            self.assertFalse(
                case["checkpoints"][key]["control_vs_control_repeat"]["different"]
            )

    def test_no_write_control_remains_identical_over_bounded_smoke(self) -> None:
        config_payload = load_config(Path("config/default.json"))
        experiment_payload = json.loads(
            Path("config/experiment_v0_1.json").read_text(encoding="utf-8")
        )
        case = run_case(
            seed=1,
            density=32,
            config_payload=config_payload,
            experiment_payload=experiment_payload,
            checkpoint_generations=(0, 1, 10),
        )
        self.assertTrue(case["replay_match"])
        self.assertTrue(case["raw_instrumented_match"])
        self.assertTrue(case["cohort"]["expected_no_write_density32"])
        for key in ("t0", "plus_1", "plus_10"):
            self.assertFalse(case["checkpoints"][key]["b_vs_h"]["different"])


if __name__ == "__main__":
    unittest.main()
