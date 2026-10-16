"""#388 O2-2 pure source-native evidence arithmetic tests, no Universe step."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from core.physics import LATENT_OPERATORS, apply_latent_operator
from research.a2_matched_recipient_contract_336 import NONTRACE_CONTEXT
from research.outer_l3_native_evidence_388 import (
    NativeReadCheck, check_native_operator_event,
    compare_native_operator_contacts, validate_native_operator_events,
)


def fixture(*, operator="masked_xor", source=1, recipient=0, mask=1,
            trace=32, rotate=4, source_epoch=0, recipient_epoch=1):
    # Totally SYNTHETIC contact row. Not an actual selected native event.
    e = {
        "native_generation":49, "physical_address":500,
        "source_slot":31, "recipient_slot":22,
        "source_life_epoch":source_epoch,
        "recipient_life_epoch":recipient_epoch,
        "native_operator":operator, "rotate_amount":rotate,
        "source_latent_before":source, "recipient_latent_before":recipient,
        "source_trace_start":trace, "native_mask":mask,
        "recipient_latent_after":apply_latent_operator(
            operator,source,recipient,mask,rotate_amount=rotate),
    }
    for name in NONTRACE_CONTEXT:
        if name not in e:
            e[name] = [2,3] if name.endswith("_xy") else 1
    e["trace_bonus_shift"]=5
    return e


class FourOperatorOriginalNativeEvidence(unittest.TestCase):
    def test_all_current_actual_physics_operators_and_epoch_keys(self):
        self.assertEqual(
            set(LATENT_OPERATORS),
            {"masked_copy", "masked_xor", "rotate_copy", "masked_and"},
        )
        outcomes=[]
        for op in sorted(LATENT_OPERATORS):
            e=fixture(operator=op,source=0x0103,recipient=0x000A,
                      mask=0x0F0F,rotate=4)
            x=check_native_operator_event(e)
            self.assertEqual(x.operator,op)
            self.assertEqual(x.native_key,(49,500,31,22,0,1))
            self.assertTrue(x.native_operator_identity_valid)
            self.assertFalse(x.actual_source_provenance_verified)
            self.assertFalse(x.causal_intervention_proven)
            self.assertFalse(x.cross_epoch_lineage_proven)
            self.assertFalse(x.independent_confirmation)
            self.assertFalse(x.learning_claim)
            outcomes.append(x.actual_receiver_after)
        self.assertEqual(len(outcomes),4)

    def test_missing_invalid_or_forged_after_fails_closed(self):
        e=fixture()
        for broken in [
            dict(e, recipient_latent_after=65535),
            dict(e, native_operator="fictional"),
            dict(e, rotate_amount=16),
            dict(e, source_trace_start=True),
            dict(e, native_mask=-1),
            dict(e, trace_bonus_shift=9),
            dict(e, source_life_epoch=-1),
            dict(e, source_slot=22),
            dict(e, source_xy=[-1,2]),
            dict(e, source_latent_before=65536),
            {k:v for k,v in e.items() if k!="native_mask"},
            dict(e, injected_teacher_label="B"),
        ]:
            with self.subTest(broken=broken):
                with self.assertRaises(ValueError):
                    check_native_operator_event(broken)

    def test_complete_batch_rejects_reused_same_generation_epoch_key(self):
        e=fixture()
        self.assertEqual(len(validate_native_operator_events([e])),1)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            validate_native_operator_events([e,dict(e)])
        with self.assertRaises(ValueError):
            validate_native_operator_events([])
        with self.assertRaises(ValueError):
            validate_native_operator_events({"bad":"mapping"})

    def test_structural_trace_association_is_not_a_causal_proof(self):
        baseline=fixture(mask=1,trace=32)
        treatment=fixture(mask=0,trace=0)
        result=compare_native_operator_contacts(baseline,treatment)
        self.assertEqual(
            result.classification,
            "STRUCTURALLY_ELIGIBLE_LOCAL_TRACE_READER_NOT_CAUSALLY_PROVEN",
        )
        self.assertTrue(result.matched_source_context)
        self.assertFalse(result.native_source_provenance_verified)
        self.assertFalse(result.controlled_causal_trace_read_proven)
        self.assertFalse(result.turnover_proven)
        self.assertFalse(result.independent_learning_proven)

    def test_context_or_effect_mismatch_is_not_unconfounded_causality(self):
        baseline=fixture(mask=1,trace=32)
        cases=[
            (dict(fixture(mask=0,trace=0),native_generation=50),
             "DIFFERENT_ACTUAL_SELECTED_CONTACT"),
            (fixture(operator="rotate_copy",mask=0,trace=0),
             "OPERATOR_CHANGED_NOT_COMPARABLE"),
            (dict(fixture(mask=0,trace=0),source_hp=2),
             "POST_TREATMENT_NONTRACE_CONTEXT_DIVERGENCE"),
            (fixture(mask=1,trace=32),
             "EQUAL_SOURCE_TRACE_NO_LOCAL_TRACE_TREATMENT"),
            (fixture(mask=1,trace=0),
             "TRACE_DIFFERENT_BUT_NATIVE_MASK_EQUAL"),
            (fixture(source=0,mask=0,trace=0),
             "POST_TREATMENT_NONTRACE_CONTEXT_DIVERGENCE"),
        ]
        for other,label in cases:
            with self.subTest(label=label):
                self.assertEqual(
                    compare_native_operator_contacts(baseline,other).classification,
                    label,
                )

    def test_no_world_construction_or_genuine_original_seed_execution(self):
        with patch("core.physics.step",side_effect=AssertionError("no Inner step")):
            self.assertEqual(
                len(validate_native_operator_events([fixture()])),1)
            self.assertFalse(
                compare_native_operator_contacts(
                    fixture(),fixture(mask=0,trace=0)
                ).independent_learning_proven
            )


if __name__=="__main__":
    unittest.main()
