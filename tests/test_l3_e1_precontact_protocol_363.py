"""Non-executing E1 #363 source-only contract tests: no native world or step."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from research.a2_matched_recipient_contract_336 import CONTACT_KEY
from tests.support_l3_e1_precontact_363 import first_h0_carrier_trace_contrast


def fake_event(gen: int, source: int, epoch: int, trace: int, *,
               after: int | None = None):
    values = (gen, 17, source, 5, epoch, 0)
    e = dict(zip(CONTACT_KEY, values))
    e["source_trace_start"] = trace
    if after is not None:
        e["recipient_latent_after"] = after
    return e


class E1NonexecutingOriginalPrecontactProtocol(unittest.TestCase):
    def test_frozen_protocol_has_explicit_authority_and_authentic_capture_gates(self):
        p = json.loads(Path("tests/l3_e1_precontact_protocol_363.json").read_text())
        self.assertEqual(p["owner_issue"], 363)
        self.assertEqual(p["parent_issue"], 171)
        self.assertEqual(p["status"],
                         "SOURCE_ONLY_PREDECLARATION_NO_NEW_PHYSICS_AUTHORIZATION")
        self.assertEqual(p["frozen_provenance"]["exposed_seed"], 544)
        self.assertEqual(p["frozen_provenance"]["original_h0_carrier_slot"], 31)
        self.assertEqual(p["frozen_provenance"]["archived_raw_sha256"],
                         "08b1368a74729dfa5bee6da29069a7d757cc053fd5de493777e701196aa1368d")
        self.assertFalse(p["actual_e1_original_physics_started"])
        self.assertFalse(p["endpoints"]["learning_claim"])
        self.assertFalse(p["endpoints"]["independent_confirmation"])
        self.assertTrue(p["bounds"]["new_effectful_workflow_and_marker_require_separate_formal_review"])
        self.assertTrue(p["bounds"]["no_old_one_shot_action_relaunch"])
        self.assertEqual(p["predeclared_selection"]["not_found"],
                         "NOT_EVALUABLE_NO_QUALIFIED_ORIGINAL_H0_CONTACT")

    def test_first_original_carrier_contrast_ignores_after_and_input_order(self):
        # Fake records here do not prove native provenance or original 544 data.
        b = [fake_event(60, 31, 0, 12, after=0),
             fake_event(40, 31, 0, 17, after=65535),
             fake_event(30, 9, 0, 13, after=1)]
        h = [fake_event(30, 9, 0, 1, after=0),
             fake_event(40, 31, 0, 7, after=0),
             fake_event(60, 31, 0, 10, after=65535)]
        selected = first_h0_carrier_trace_contrast(b, h)
        self.assertEqual(selected["native_key"]["native_generation"], 40)
        self.assertEqual(selected["baseline_B_source_trace"], 17)
        self.assertEqual(selected["intervention_H_source_trace"], 7)
        self.assertFalse(selected["recipient_outcome_inspected"])
        self.assertFalse(selected["provenance_verified_here"])
        for item in (b, h):
            for event in item:
                event.pop("recipient_latent_after")
        self.assertEqual(first_h0_carrier_trace_contrast(b, h), selected)

    def test_no_eligible_carrier_is_none_without_fallback(self):
        self.assertIsNone(first_h0_carrier_trace_contrast(
            [fake_event(49, 31, 1, 12)], [fake_event(49, 31, 1, 1)]))
        self.assertIsNone(first_h0_carrier_trace_contrast(
            [fake_event(49, 31, 0, 12)], [fake_event(49, 31, 0, 12)]))
        self.assertIsNone(first_h0_carrier_trace_contrast(
            [fake_event(49, 31, 0, 12)], [fake_event(50, 31, 0, 1)]))

    def test_duplicate_or_invalid_native_record_fails_closed(self):
        e = fake_event(49, 31, 0, 12)
        with self.assertRaises(ValueError):
            first_h0_carrier_trace_contrast([e, dict(e)], [e])
        with self.assertRaises(ValueError):
            first_h0_carrier_trace_contrast([fake_event(49, 31, 0, 256)], [e])
        with self.assertRaises(ValueError):
            first_h0_carrier_trace_contrast([fake_event(49, -1, 0, 1)], [e])


if __name__ == "__main__":
    unittest.main()
