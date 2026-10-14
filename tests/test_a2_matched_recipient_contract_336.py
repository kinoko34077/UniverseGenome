"""#336: synthetic STATIC witnesses, NOT an actual R2/rotate_copy physics run."""
from copy import deepcopy
import unittest

from core.physics import apply_latent_operator
from research.a2_matched_recipient_contract_336 import (
    CONTACT_KEY, FIELDS, NONTRACE_CONTEXT, SCHEMA,
    compare_native_contact_witnesses,
)


def fake_contact(*, trace=128, mask=0x11, epoch=0):
    after=apply_latent_operator("rotate_copy",1,1,mask,rotate_amount=4)
    return {
        "native_generation":14,
        "physical_address":300,
        "source_slot":2,"recipient_slot":4,
        "source_life_epoch":epoch,"recipient_life_epoch":0,
        "source_xy":[8,8],"recipient_xy":[8,8],
        "source_structure":1,"recipient_structure":1,
        "source_direction":0,"recipient_direction":4,
        "source_speed_code":1,"recipient_speed_code":1,
        "source_hp":200,"recipient_hp":200,
        "source_bond_strength":0,"recipient_bond_strength":0,
        "source_latent_before":1,"recipient_latent_before":1,
        "trace_bonus_shift":7,
        "source_trace_start":trace,"native_mask":mask,
        "recipient_latent_after":after,
        "native_operator":"rotate_copy","rotate_amount":4,
    }


class NativeRecipientSchemaOnly(unittest.TestCase):
    def test_true_native_source_pure_formula_and_mask_width_are_checked(self):
        b=fake_contact(trace=128,mask=0x11)
        h=fake_contact(trace=0,mask=0x01)
        result=compare_native_contact_witnesses([b],[h])
        self.assertEqual(result["schema"],SCHEMA)
        counts=result["counts"]
        self.assertEqual(counts["matched_selected_contacts"],1)
        self.assertEqual(counts["same_nontrace_context"],1)
        self.assertEqual(counts["trace_difference_with_equal_context"],1)
        self.assertEqual(counts["mask_difference_with_equal_context"],1)
        self.assertEqual(counts["recipient_difference_with_equal_context"],1)
        self.assertEqual(counts["trace_mask_recipient_difference_with_equal_context"],1)
        self.assertFalse(result["actual_alternate_physics_executed_here"])
        self.assertFalse(result["independent_confirmation"])
        self.assertFalse(result["teacher_specific_causal_learning_proven"])
        self.assertFalse(result["learning_claim"])
        self.assertEqual(b["recipient_latent_after"],16)
        self.assertEqual(h["recipient_latent_after"],0)
        self.assertEqual(len(FIELDS),len(set(FIELDS)))
        self.assertTrue(set(CONTACT_KEY).isdisjoint(NONTRACE_CONTEXT))

    def test_same_teacher_negative_sham_has_zero_actual_difference(self):
        b=fake_contact()
        result=compare_native_contact_witnesses([b],[deepcopy(b)])
        self.assertEqual(result["counts"]["matched_selected_contacts"],1)
        self.assertEqual(result["counts"]["recipient_difference_with_equal_context"],0)
        self.assertEqual(result["counts"]["trace_mask_recipient_difference_with_equal_context"],0)
        self.assertEqual(result["counts"]["unmatched_topology"],0)

    def test_life_epoch_reuse_does_not_count_as_matched(self):
        result=compare_native_contact_witnesses(
            [fake_contact()],[fake_contact(epoch=1)]
        )
        self.assertEqual(result["counts"]["matched_selected_contacts"],0)
        self.assertEqual(result["counts"]["unmatched_topology"],2)
        self.assertEqual(result["counts"]["recipient_difference_with_equal_context"],0)

    def test_nontrace_context_confounded_not_treated_as_teacher_read(self):
        b=fake_contact()
        h=fake_contact(trace=0,mask=0x01)
        h["recipient_hp"]=199
        result=compare_native_contact_witnesses([b],[h])
        self.assertEqual(result["counts"]["matched_selected_contacts"],1)
        self.assertEqual(result["counts"]["confounded_precontext"],1)
        self.assertEqual(result["counts"]["same_nontrace_context"],0)
        self.assertEqual(result["counts"]["recipient_difference_with_equal_context"],0)

    def test_reject_native_fabrication_incomplete_and_duplicate(self):
        b=fake_contact()
        for patch in (
            {"recipient_latent_after":7},
            {"native_mask":0},
            {"source_trace_start":-1},
            {"source_trace_start":False},
            {"native_operator":"masked_copy"},
            {"rotate_amount":5},
            {"source_slot":4},
            {"recipient_latent_before":65536},
            {"source_bond_strength":300},
            {"source_life_epoch":-1},
            {"source_xy":[-1,0]},
        ):
            with self.subTest(patch=patch):
                bad=deepcopy(b)
                bad.update(patch)
                with self.assertRaises(ValueError):
                    compare_native_contact_witnesses([bad],[bad])
        missing=deepcopy(b)
        del missing["source_hp"]
        with self.assertRaises(ValueError):
            compare_native_contact_witnesses([missing],[missing])
        with self.assertRaises(ValueError):
            compare_native_contact_witnesses([b,b],[])
        badmask=deepcopy(b)
        badmask["native_mask"]=0x12
        h=deepcopy(b)
        with self.assertRaises(ValueError):
            compare_native_contact_witnesses([badmask],[h])

    def test_static_classifier_does_not_mutate_event_inputs(self):
        b=fake_contact()
        h=fake_contact(trace=0,mask=1)
        a,c=deepcopy(b),deepcopy(h)
        compare_native_contact_witnesses([b],[h])
        self.assertEqual(b,a)
        self.assertEqual(h,c)


if __name__=="__main__":
    unittest.main()
