"""#326 A1.9: original 36-event one-step counterfactual, no new physics."""
import unittest

from core.physics import apply_latent_operator
from research.a19_exposed_operator_counterfactual_326 import (
    original_contact_counterfactual,
)


class ArchivedOriginalContactAlgebraTests(unittest.TestCase):
    def test_all_original_events_source_frozen_without_new_seed(self):
        result=original_contact_counterfactual()
        self.assertEqual(result["original_a14_source_pr_head_sha"],
                         "ad8384967cbe740729e636d1724ecfe0fa0a30e3")
        self.assertEqual(result["original_r2_source_sha"],
                         "af568ac1558f2f3f86e51341208f5b51557b7a39")
        self.assertEqual(result["positive_original_changed_mask_contacts"],36)
        self.assertEqual(result["negative_original_changed_mask_contacts"],0)
        self.assertEqual(result["original_actual_BH_recipient_contrast"],0)
        self.assertEqual(result["hypothetical_one_contact_BH_different_outputs"],{
            "masked_copy":0,"masked_and":0,"masked_xor":4,"rotate_copy":8,
        })
        self.assertEqual(result["changed_mask_difference_bit0"],4)
        self.assertEqual(result["changed_mask_difference_bit4"],4)
        self.assertEqual(result["changed_mask_difference_both_bits"],0)
        self.assertEqual(
            [r[0] for r in result["hypothetical_distinguishing_rows"]["masked_xor"]],
            [37,299,550,680],
        )
        self.assertEqual(
            len(result["hypothetical_distinguishing_rows"]["rotate_copy"]),8,
        )
        self.assertFalse(result["heldout_consumed"])
        self.assertFalse(result["new_physics_executed"])
        self.assertFalse(result["independent_confirmation"])
        self.assertFalse(result["learning_claim"])
        for op, rows in result["hypothetical_distinguishing_rows"].items():
            for row in rows:
                _,_,_,_,_,_,_,mask_b,mask_h,expected_b,expected_h=row
                self.assertNotEqual(expected_b,expected_h)
                self.assertEqual(expected_b,apply_latent_operator(
                    op,1,1,mask_b,rotate_amount=4))
                self.assertEqual(expected_h,apply_latent_operator(
                    op,1,1,mask_h,rotate_amount=4))
        self.assertEqual(
            result["hypothetical_distinguishing_rows"]["masked_copy"],[],
        )

    def test_masks_are_one_contact_local_not_causal_trajectory(self):
        self.assertEqual(apply_latent_operator("masked_copy",1,1,8193),1)
        self.assertEqual(apply_latent_operator("masked_copy",1,1,8192),1)
        self.assertEqual(apply_latent_operator("masked_xor",1,1,8193),0)
        self.assertEqual(apply_latent_operator("masked_xor",1,1,8192),1)
        self.assertEqual(apply_latent_operator("rotate_copy",1,1,8193),0)
        self.assertEqual(apply_latent_operator("rotate_copy",1,1,8192),1)


if __name__=="__main__":
    unittest.main()
