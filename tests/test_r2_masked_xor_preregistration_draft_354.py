"""#354 source-only preregistration guard tests. Do not instantiate or step any universe."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

from core.physics import apply_latent_operator
from research.a2_matched_recipient_contract_336 import CONTACT_KEY

DRAFT = Path("docs/research/r2_masked_xor_preregistration_draft_354.json")


class MaskedXorDraftPreflightTest(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(DRAFT.read_text(encoding="utf-8"))

    def test_historical_protection_and_proposed_band_disjointness(self):
        bands = self.spec["role_bands_proposed_not_validated"]
        historical = bands["historical_exposed"]
        independent = bands["future_independent_reserve"]
        exploratory = bands["future_exploratory_proposal"]
        phase_h = bands["historical_phase_h_holdout"]
        self.assertEqual((historical["start"], historical["end"]), (0, 1023))
        self.assertEqual((phase_h["start"], phase_h["end"]), (96, 159))
        self.assertTrue(historical["start"] <= phase_h["start"] <= phase_h["end"] <= historical["end"])
        self.assertLess(historical["end"], independent["start"])
        self.assertLess(independent["end"], exploratory["start"])
        self.assertLess(exploratory["end"], bands["unassigned_from"])
        for band in (historical, phase_h):
            self.assertFalse(band["post_h0_execution_allowed"])
        self.assertFalse(independent["qualification_allowed_now"])
        self.assertFalse(exploratory["qualification_allowed_now"])

    def test_no_implicit_physics_authorization(self):
        self.assertEqual(self.spec["owner_issue"], 354)
        self.assertEqual(self.spec["state"], "SOURCE_ONLY_DESIGN_NO_NATIVE_EXECUTION")
        self.assertEqual(self.spec["candidate"]["operator"], "masked_xor")
        self.assertTrue(self.spec["candidate"]["single_candidate"])
        self.assertTrue(self.spec["candidate"]["production_config_unchanged"])
        selection = self.spec["seed_freeze"]
        self.assertEqual(selection["selected_seeds"], [])
        for flag in ("cohort_collision_audit_complete","h0_qualification_executed",
                     "qualification_rule_frozen","stopping_rule_frozen"):
            self.assertFalse(selection[flag])
        for key, value in self.spec["authorization"].items():
            self.assertIs(value, False, key)
        self.assertTrue(self.spec["limits"]["no_retry"])
        self.assertFalse(self.spec["native_witness"]["long_term_retention_claim_allowed"])
        self.assertFalse(self.spec["native_witness"]["independent_learning_claim_allowed"])

    def test_source_native_witness_contract_and_counters(self):
        w = self.spec["native_witness"]
        self.assertEqual(tuple(w["match_keys"]), CONTACT_KEY)
        self.assertEqual(w["classify_invalid_as"], "NOT_EVALUABLE_NO_SEED_REPLACEMENT")
        counts = w["required_counters"]
        self.assertEqual(len(counts), len(set(counts)))
        for field in ("matched_contacts","confounded_precontact","comparable_precontact",
                      "native_mask_different","mask_xor_source_support_nonzero",
                      "recipient_after_different"):
            self.assertIn(field, counts)
        self.assertIn("INSTRUMENTATION_PARITY", w["decision_order"])
        self.assertIn("SOURCE_NATIVE_CONTACT_PROVENANCE", w["decision_order"])

    def test_single_operator_pure_algebra(self):
        # Synthetic one-contact calculations only; no seed, RNG, h0 or native step.
        words=(0,1,16,17,0x1234,0xFFFF)
        masks=(0,1,16,17,0x00FF,0xFFFF)
        for source in words:
            for recipient in words:
                for mask_b in masks:
                    for mask_h in masks:
                        actual=(apply_latent_operator("masked_xor",source,recipient,mask_b)
                                ^apply_latent_operator("masked_xor",source,recipient,mask_h))
                        self.assertEqual(actual, source & (mask_b ^ mask_h),
                                         (source,recipient,mask_b,mask_h))


if __name__ == "__main__":
    unittest.main()
