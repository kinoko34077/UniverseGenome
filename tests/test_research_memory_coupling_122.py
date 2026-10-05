from __future__ import annotations

import json
from pathlib import Path
import unittest

from core.runner import load_config
from research.memory_coupling_audit_122 import (
    DENSITY4_NEGATIVE_SENTINELS,
    DENSITY4_SEEDS,
    DENSITY4_WRITE_POSITIVE_SEEDS,
    HORIZONS,
    NEGATIVE_DENSITY32_SEEDS,
    NEGATIVE_DENSITY32_SENTINELS,
    PRIMARY_DENSITY32_SEEDS,
    ROUTE_RECALL_REQUIRED_PRIMARY_PERSISTENT,
    case_plan,
    classify_diff,
    run_case,
)


class MemoryCouplingAudit122Tests(unittest.TestCase):
    def test_protocol_freeze_constants(self) -> None:
        self.assertEqual(HORIZONS, (0, 1, 10, 100, 1000))
        self.assertEqual(
            PRIMARY_DENSITY32_SEEDS,
            (0, 5, 8, 9, 12, 14, 18, 19, 20, 22, 24, 29),
        )
        self.assertEqual(
            set(PRIMARY_DENSITY32_SEEDS).intersection(
                NEGATIVE_DENSITY32_SEEDS
            ),
            set(),
        )
        self.assertEqual(
            set(PRIMARY_DENSITY32_SEEDS).union(NEGATIVE_DENSITY32_SEEDS),
            set(range(32)),
        )
        self.assertEqual(NEGATIVE_DENSITY32_SENTINELS, (1, 2, 3, 4))
        self.assertEqual(DENSITY4_SEEDS, tuple(range(32)))
        self.assertEqual(DENSITY4_WRITE_POSITIVE_SEEDS, (9,))
        self.assertEqual(DENSITY4_NEGATIVE_SENTINELS, (0, 1, 2, 3))
        self.assertEqual(ROUTE_RECALL_REQUIRED_PRIMARY_PERSISTENT, 8)

        plan = case_plan()
        self.assertEqual(len(plan), 64)
        self.assertEqual(sum(item["long_horizon"] for item in plan), 21)
        self.assertEqual(sum(item["verify"] for item in plan), 13)

    def test_classification_is_field_based(self) -> None:
        fields = {
            name: {"changed_slots": 0, "slot_ids": [], "absolute_delta_sum": 0}
            for name in (
                "lifecycle", "x", "y", "structure", "latent", "hp",
                "bond_strength", "direction", "speed_code", "age",
                "black_hole_timer",
            )
        }
        base = {
            "different": False,
            "changed_slots": [],
            "changed_slot_fields_total": 0,
            "fields": fields,
        }
        self.assertEqual(classify_diff(base), "RECONVERGED")

        hp = json.loads(json.dumps(base))
        hp["different"] = True
        hp["changed_slots"] = [1]
        hp["fields"]["hp"]["changed_slots"] = 1
        self.assertEqual(classify_diff(hp), "HP_ONLY")

        lifecycle = json.loads(json.dumps(hp))
        lifecycle["fields"]["lifecycle"]["changed_slots"] = 1
        self.assertEqual(classify_diff(lifecycle), "LIFECYCLE_KINEMATIC")

        network = json.loads(json.dumps(hp))
        network["fields"]["latent"]["changed_slots"] = 1
        self.assertEqual(classify_diff(network), "NETWORK_COUPLED")

    def test_h0_reproduces_accepted_primary_and_negative_cases(self) -> None:
        config_payload = load_config(Path("config/default.json"))
        experiment_payload = json.loads(
            Path("config/experiment_v0_1.json").read_text(encoding="utf-8")
        )
        primary = run_case(
            seed=0,
            density=32,
            role="density32_primary_write_positive",
            long_horizon=False,
            verify=True,
            config_payload=config_payload,
            experiment_payload=experiment_payload,
        )
        negative = run_case(
            seed=1,
            density=32,
            role="density32_immediate_no_write",
            long_horizon=False,
            verify=False,
            config_payload=config_payload,
            experiment_payload=experiment_payload,
        )
        self.assertTrue(
            primary["horizons"]["0"]["comparisons"]["b_vs_h"]["different"]
        )
        self.assertEqual(
            classify_diff(
                primary["horizons"]["0"]["comparisons"]["b_vs_h"]
            ),
            "HP_ONLY",
        )
        self.assertFalse(
            negative["horizons"]["0"]["comparisons"]["b_vs_h"]["different"]
        )
        self.assertTrue(primary["replay_match"])
        self.assertTrue(primary["raw_instrumented_match"])
        self.assertFalse(
            primary["horizons"]["0"]["comparisons"][
                "control_vs_control_repeat"
            ]["different"]
        )


if __name__ == "__main__":
    unittest.main()
