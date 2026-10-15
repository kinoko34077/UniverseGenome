"""#354 synthetic-only masked_xor native contact witness reference regressions."""
from __future__ import annotations

import unittest

from core.physics import apply_latent_operator
from research.a2_matched_recipient_contract_336 import CONTACT_KEY, FIELDS
from tests.support_r2_masked_xor_contact_354 import (
    classify_purported_native_contacts, _native_key,
)

class SourceOnlyContactContractTest(unittest.TestCase):
    def event(self, *, trace=0, mask=2, source=1, dest=1, recipient_slot=2):
        e = {
            "native_generation": 17, "physical_address": 1,
            "source_slot": 1, "recipient_slot": recipient_slot,
            "source_life_epoch": 3, "recipient_life_epoch": 5,
            "source_xy": [1, 1], "recipient_xy": [1, 2],
            "source_structure": 1, "recipient_structure": 1,
            "source_direction": 1, "recipient_direction": 1,
            "source_speed_code": 1, "recipient_speed_code": 1,
            "source_hp": 100, "recipient_hp": 100,
            "source_bond_strength": 0, "recipient_bond_strength": 0,
            "source_latent_before": source, "recipient_latent_before": dest,
            "trace_bonus_shift": 0, "source_trace_start": trace,
            "native_mask": mask, "recipient_latent_after": apply_latent_operator(
                "masked_xor", source, dest, mask, rotate_amount=0,
            ), "native_operator": "masked_xor", "rotate_amount": 0,
        }
        self.assertEqual(set(e), set(FIELDS))
        return e

    def test_source_only_positive_local_does_not_claim_retention(self):
        b = self.event(trace=0, mask=2)
        h = self.event(trace=1, mask=3)
        result = classify_purported_native_contacts([b], [h])
        self.assertEqual(result["classification"],
                         "LOCAL_RECEIVER_EFFECT_RETENTION_UNRESOLVED")
        self.assertEqual(result["counts"]["comparable_precontact"], 1)
        self.assertEqual(result["counts"]["source_trace_different"], 1)
        self.assertEqual(result["counts"]["native_mask_different"], 1)
        self.assertEqual(result["counts"]["mask_xor_source_support_nonzero"], 1)
        self.assertEqual(result["counts"]["recipient_after_different"], 1)
        self.assertFalse(result["native_source_provenance_verified_here"])
        self.assertFalse(result["actual_native_experiment_executed_here"])
        self.assertEqual(result["long_term_retention"], "NOT_ESTABLISHED")
        self.assertFalse(result["learning_claim"])

    def test_mask_diff_with_zero_source_overlap_is_true_scoped_negative(self):
        b, h = self.event(trace=0, mask=1), self.event(trace=1, mask=3)
        r = classify_purported_native_contacts([b], [h])
        self.assertEqual(r["classification"], "NEGATIVE_NO_MATCHED_RECIPIENT_EFFECT")
        self.assertEqual(r["counts"]["native_mask_different"], 1)
        self.assertEqual(r["counts"]["mask_xor_source_support_nonzero"], 0)
        self.assertEqual(r["counts"]["recipient_after_different"], 0)

    def test_confounded_or_unmatched_is_not_a_physical_negative(self):
        b = self.event()
        h = self.event(trace=1, mask=3, dest=2)
        r = classify_purported_native_contacts([b], [h])
        self.assertEqual(r["classification"], "NOT_EVALUABLE_NO_SEED_REPLACEMENT")
        self.assertEqual(r["counts"]["confounded_precontact"], 1)
        h2 = self.event(trace=1, mask=3, recipient_slot=4)
        r = classify_purported_native_contacts([b], [h2])
        self.assertEqual(r["classification"], "NOT_EVALUABLE_NO_SEED_REPLACEMENT")
        self.assertEqual(r["counts"]["unmatched_contacts"], 2)
        self.assertEqual(r["counts"]["comparable_precontact"], 0)

    def test_fail_closed_for_false_data_and_operator_mismatch(self):
        b = self.event(trace=0, mask=2)
        h = self.event(trace=1, mask=3)
        corrupted = dict(h, recipient_latent_after=65535)
        with self.assertRaisesRegex(ValueError, "recipient-after"):
            classify_purported_native_contacts([b], [corrupted])
        wrong = dict(h, native_operator="rotate_copy")
        with self.assertRaisesRegex(ValueError, "wrong physical operator"):
            classify_purported_native_contacts([b], [wrong])
        wrong = dict(h, native_mask=2)
        with self.assertRaisesRegex(ValueError, "mask width"):
            classify_purported_native_contacts([b], [wrong])
        wrong = dict(h, extra_field=9)
        with self.assertRaisesRegex(ValueError, "witness schema"):
            classify_purported_native_contacts([b], [wrong])
        wrong = dict(h, recipient_latent_after=True)
        with self.assertRaisesRegex(ValueError, "16-bit"):
            classify_purported_native_contacts([b], [wrong])

    def test_same_trace_different_mask_is_invalid_and_duplicate_rejected(self):
        b = self.event(trace=0, mask=1)
        h = self.event(trace=0, mask=2)
        with self.assertRaisesRegex(ValueError, "same trace"):
            classify_purported_native_contacts([b], [h])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            classify_purported_native_contacts([b, b], [h])
        with self.assertRaisesRegex(ValueError, "self-transfer"):
            _native_key(dict(b, recipient_slot=1))

    def test_empty_or_too_many_native_contacts_not_evaluable(self):
        r = classify_purported_native_contacts([], [])
        self.assertEqual(r["classification"], "NOT_EVALUABLE_NO_SEED_REPLACEMENT")
        from tests.support_r2_masked_xor_contact_354 import MAX_NATIVE_EVENTS
        with self.assertRaisesRegex(ValueError, "event bound exceeded"):
            classify_purported_native_contacts([{}] * (MAX_NATIVE_EVENTS+1), [])


if __name__ == "__main__":
    unittest.main()
