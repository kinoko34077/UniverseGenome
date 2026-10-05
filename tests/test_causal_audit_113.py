"""Tests for the Issue #113 research-only causal audit harness."""

from __future__ import annotations

import unittest

from research.causal_audit_113 import (
    BRANCHES,
    CHECKPOINT_LABELS,
    compare_state_snapshots,
    run_case,
)


class CausalAuditPrimitiveTests(unittest.TestCase):
    def test_snapshot_comparison_reports_tracked_field_deltas(self):
        before = {
            "generation": 4,
            "arrays": {
                "hp": [1, 2],
                "latent": [3, 4],
                "x": [5, 6],
            },
        }
        after = {
            "generation": 5,
            "arrays": {
                "hp": [1, 9],
                "latent": [3, 4],
                "x": [5, 7],
            },
        }

        result = compare_state_snapshots(before, after)

        self.assertFalse(result["identical"])
        self.assertEqual(result["changed_fields"], ["hp", "x"])
        self.assertEqual(result["changed_slots"]["hp"], [1])
        self.assertEqual(result["changed_slots"]["x"], [1])

    def test_declarations_are_fixed_for_the_predeclared_audit(self):
        self.assertEqual(
            BRANCHES,
            ("control", "a_only", "ab", "ac"),
        )
        self.assertEqual(
            CHECKPOINT_LABELS,
            (
                "pre_stimulus",
                "teacher_byte",
                "teacher_sequence_complete",
                "plus_10",
                "plus_100",
                "plus_1000",
            ),
        )

    def test_one_case_uses_matched_branches_and_deterministic_replay(self):
        result = run_case(seed=0, density=4)

        self.assertEqual(set(result["branches"]), set(BRANCHES))
        self.assertTrue(result["replay_equal"])
        self.assertTrue(result["raw_instrumented_equal"])
        self.assertEqual(
            {record["source_digest"] for record in result["branches"].values()},
            {result["source_digest"]},
        )
        self.assertEqual(
            set(result["branches"]["ab"]["checkpoints"]),
            set(CHECKPOINT_LABELS),
        )
        self.assertEqual(result["branches"]["ab"]["generations"], 1124)
        self.assertEqual(
            set(result["causal"]["levels"]),
            {"L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"},
        )


if __name__ == "__main__":
    unittest.main()
