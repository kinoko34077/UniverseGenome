from __future__ import annotations

import json
from pathlib import Path
import unittest

from core.runner import load_config
from research.transduction_audit_120 import (
    TEACHER_H,
    geometry_analysis,
    run_case,
)


class TransductionAudit120Tests(unittest.TestCase):
    def test_geometry_freeze_matches_predeclared_issue_values(self) -> None:
        result = geometry_analysis()
        self.assertEqual(result["distinct_idealized_regions"], 55)
        self.assertEqual(result["exact_alias_unordered_pairs"], 3393)
        self.assertEqual(result["largest_equivalence_class_size"], 68)
        self.assertEqual(result["b_alias_values"], [66, 194])
        self.assertEqual(result["b_region_size"], 27)
        self.assertEqual(result["c_region_size"], 30)
        self.assertEqual(result["b_c_symmetric_difference"], 3)
        self.assertEqual(result["maximum_distance_from_b"], 21)
        self.assertEqual(result["maximum_distance_candidates"], [8, 16])
        self.assertEqual(result["selected_high_contrast_byte"], TEACHER_H)
        self.assertTrue(result["selection_matches_predeclared"])
        self.assertEqual(result["b_h_symmetric_difference"], 21)
        self.assertEqual(
            result["distance_distribution_from_b"],
            {"0": 1, "3": 8, "6": 51, "9": 108, "12": 50, "15": 26, "18": 9, "21": 2},
        )

    def test_one_matched_case_replays_and_is_instrumentation_equivalent(self) -> None:
        config_payload = load_config(Path("config/default.json"))
        experiment_payload = json.loads(
            Path("config/experiment_v0_1.json").read_text(encoding="utf-8")
        )
        case = run_case(
            seed=23,
            density=32,
            config_payload=config_payload,
            experiment_payload=experiment_payload,
        )
        self.assertTrue(case["replay_match"])
        self.assertTrue(case["raw_instrumented_match"])
        self.assertGreaterEqual(case["hit_capacity"]["distinct_hit_pattern_count"], 1)


if __name__ == "__main__":
    unittest.main()
