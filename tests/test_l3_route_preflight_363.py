"""#363 frozen protocol / original genuine archive read-only validation; no physics."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from tests.l3_native_route_pilot_363 import (
    exact_marker_gate, original_report, trace_carrier_slots,
)


class SourceOnlyRoutePreflight(unittest.TestCase):
    def test_original_source_evidence_readonly_and_bh_equal_controls(self):
        report=original_report()
        self.assertEqual(report["source_sha"] if "source_sha" in report else report["runner_source_sha"],
                         "2a2cf845e12617583790c1838a4dfe5573a5ef45")
        self.assertTrue(report["original_masked_copy_golden_parity"])
        self.assertTrue(report["negative_BH_full_equality"])
        self.assertEqual(report["data"]["544"]["h"]["checkpoints"],
                         report["data"]["544"]["control"]["checkpoints"])
        self.assertEqual(report["positive_native_paired_read_contrast"]["counts"]["matched_contacts"],764)

    def test_exact_protocol_is_nonexecuting_before_marker(self):
        p=json.loads(Path("tests/l3_native_route_protocol_363.json").read_text())
        self.assertEqual(p["owner_issue"],363)
        self.assertEqual(p["scientific_role"],
                         "EXPLORATORY_EXPOSED_REPEATED_INPUTS_NOT_INDEPENDENT")
        self.assertEqual(p["experimental_controls"]["source_positive_seed"],544)
        self.assertEqual(p["experimental_controls"]["source_negative_seed"],545)
        self.assertEqual(p["experimental_controls"]["post_h0_operator"],"masked_xor")
        self.assertEqual(p["experimental_controls"]["rotate_amount_unchanged"],4)
        self.assertTrue(p["experimental_controls"]["no_data_driven_seed_or_event_selection"])
        self.assertFalse(p["actual_new_native_run_started"])
        self.assertFalse(p["approval_to_run"])
        self.assertFalse(p["learning_claim"])
        self.assertEqual(p["used_new_seeds"],[])
        self.assertFalse(Path("research/approvals/l3_route_e0_363.run").exists())
        with self.assertRaises(PermissionError):
            exact_marker_gate("0"*40)

    def test_trace_carrier_pair_extraction_exact_initial_h0_only(self):
        b={"arrays":{"slow_trace":[0,1,10,5]}}
        h={"arrays":{"slow_trace":[0,2,10,7]}}
        self.assertEqual(trace_carrier_slots(b,h),{1,3})
        self.assertEqual(trace_carrier_slots(b,b),set())


if __name__=="__main__":
    unittest.main()
