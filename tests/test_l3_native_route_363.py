"""#363 route aggregation has only synthetic records; never performs original physics."""
from __future__ import annotations
import copy
import unittest

from core.physics import apply_latent_operator
from tests.test_r2_masked_xor_contact_354 import SourceOnlyContactContractTest
from tests.support_l3_native_route_363 import classify_route


def fixture(**kwargs):
    return SourceOnlyContactContractTest().event(**kwargs)


class TraceContactStageClassifier(unittest.TestCase):
    def test_equal_context_trace_and_native_receiver_bit_delta(self):
        b, h = fixture(trace=0, mask=2), fixture(trace=1, mask=3)
        # Explicit synthetic pre-h0 survivor, unlike fixture default epoch 3.
        b["source_life_epoch"]=0
        h["source_life_epoch"]=0
        z=classify_route([b],[h],initial_trace_carrier_slots={1})
        self.assertEqual(z["classification"],"TRACE_REACHED_COMPARABLE_CONTACT")
        c=z["counts"]
        self.assertEqual(c["matched_contact_keys"],1)
        self.assertEqual(c["equal_nontrace_precontact"],1)
        self.assertEqual(c["partition_---"],1)
        self.assertEqual(c["source_trace_delta_comparable"],1)
        self.assertEqual(c["native_mask_delta_comparable"],1)
        self.assertEqual(c["effective_source_mask_overlap_comparable"],1)
        self.assertEqual(c["recipient_after_delta_comparable"],1)
        self.assertEqual(c["B_h0_trace_carrier_source_events"],1)
        self.assertEqual(z["first_native_generation"]["first_trace_delta"],17)
        self.assertFalse(z["learning_claim"])

    def test_confounded_fields_not_teacher_causality(self):
        b, h = fixture(trace=0,mask=2), fixture(trace=1,mask=3)
        h=dict(h,source_hp=89,source_latent_before=2)
        h["recipient_latent_after"]=apply_latent_operator(
            "masked_xor",h["source_latent_before"],h["recipient_latent_before"],
            h["native_mask"],rotate_amount=4)
        z=classify_route([b],[h],initial_trace_carrier_slots={1})
        c=z["counts"]
        self.assertEqual(z["classification"],
                         "TRACE_DIFFERENCE_ONLY_IN_CONFOUNDED_CONTACTS")
        self.assertEqual(c["confounded_nontrace_precontact"],1)
        self.assertEqual(c["partition_S-O"],1)
        self.assertEqual(c["source_trace_delta_confounded"],1)
        self.assertEqual(c["native_mask_delta_confounded"],1)
        self.assertEqual(c["field_diff_source_hp"],1)
        self.assertEqual(c["field_diff_source_latent_before"],1)
        self.assertEqual(c.get("recipient_after_delta_comparable",0),0)
        self.assertTrue(z["nontrace_confounded_receiver_delta_is_NOT_caused_by_trace"])

    def test_no_trace_reach_and_unmatched(self):
        b=fixture()
        h=copy.deepcopy(b)
        z=classify_route([b],[h],initial_trace_carrier_slots=set())
        self.assertEqual(z["classification"],
                         "NO_SOURCE_TRACE_CONTRAST_AT_MATCHED_CONTACTS")
        self.assertEqual(z["counts"]["matched_contact_keys"],1)
        self.assertEqual(z["counts"].get("source_trace_delta_all_matched",0),0)
        h["recipient_slot"]=4
        with self.assertRaisesRegex(ValueError,"invalid source-native witness schema"):
            classify_route([b],[{"missing":1}],initial_trace_carrier_slots={1})
        z=classify_route([b],[h],initial_trace_carrier_slots=set())
        self.assertEqual(z["classification"],"NOT_EVALUABLE_NO_MATCHED_CONTACT")
        self.assertEqual(z["counts"]["unmatched_contact_keys"],2)

    def test_reject_unsupported_inputs_and_native_errors(self):
        b=fixture()
        with self.assertRaisesRegex(ValueError,"duplicate"):
            classify_route([b,b],[b],initial_trace_carrier_slots={1})
        with self.assertRaisesRegex(ValueError,"carrier slot"):
            classify_route([],[],initial_trace_carrier_slots={True})
        with self.assertRaisesRegex(ValueError,"source selected contact budget|budget exceeded"):
            classify_route([b]*200001,[],initial_trace_carrier_slots=set())
        h=dict(b,native_mask=3)
        h["recipient_latent_after"]=apply_latent_operator(
            "masked_xor",h["source_latent_before"],h["recipient_latent_before"],
            h["native_mask"],rotate_amount=4)
        # Same trace cannot change the real selected native mask with same context.
        # Invalid mask width is caught before this downstream consistency assertion.
        with self.assertRaises(ValueError):
            classify_route([b],[h],initial_trace_carrier_slots=set())


if __name__=="__main__":
    unittest.main()
