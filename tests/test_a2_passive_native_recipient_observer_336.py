"""#336 E1a: AUTHENTIC native step on manually-constructed SYNTHETIC cells only.

This is neither old R2 seed544/545 nor a new independent scientific cohort.
It verifies instrumented/uninstrumented actual native state parity and the
complete selected transmission field provenance; no teacher result is claimed.
"""
import copy
import unittest

import core.physics as physics
from core.state import SHAPE_SINGLE
from research.a2_passive_native_recipient_observer_336 import (
    PassiveNativeRecipientObserver,
)
from research.a2_matched_recipient_contract_336 import (
    compare_native_contact_witnesses,
)


def artificial_native_contact(*, source_trace=128):
    config=physics.PhysicsConfig(
        max_cells=8,initial_density=0,hp_decay=0,noise_rate=0,
        fragmentation_enabled=False,fusion_enabled=False,
        latent_operator="rotate_copy",rotate_amount=4,
        trace_bonus_shift=7,
    )
    s=physics.create_universe(seed=0,config=config)
    first=s.spawn(x=0,y=0,structure=SHAPE_SINGLE,latent=1,
                  hp=200,direction=0,speed_code=0)
    second=s.spawn(x=0,y=0,structure=SHAPE_SINGLE,latent=1,
                   hp=200,direction=0,speed_code=0)
    s.slow_trace[first]=source_trace
    s.slow_trace[second]=0
    return s


class PassiveNativeActualSourceParity(unittest.TestCase):
    def test_source_native_step_matches_uninstrumented_complete_snapshot(self):
        s=artificial_native_contact()
        original=copy.deepcopy(s)
        old_mask=physics.transmission_mask
        old_transmit=physics._transmit_latent
        native_result=physics.step(original)
        ob=PassiveNativeRecipientObserver(s)
        with ob.attach():
            observed_result=physics.step(s)
        self.assertIs(physics.transmission_mask,old_mask)
        self.assertIs(physics._transmit_latent,old_transmit)
        self.assertEqual(s.to_snapshot(),original.to_snapshot())
        self.assertEqual(native_result.latent_transmission_count,1)
        self.assertEqual(observed_result.latent_transmission_count,1)
        self.assertEqual(len(ob.events),2)
        self.assertEqual(ob.schema,"UG_A2_MATCHED_NATIVE_RECIPIENT_CONTACTS_V1")
        for e in ob.events:
            self.assertEqual(e["source_life_epoch"],0)
            self.assertEqual(e["recipient_life_epoch"],0)
            self.assertEqual(e["native_operator"],"rotate_copy")
            self.assertEqual(e["source_latent_before"],1)
            self.assertEqual(e["recipient_latent_before"],1)
            self.assertEqual(e["native_generation"],0)
            self.assertEqual(e["source_bond_strength"],4)
        report=compare_native_contact_witnesses(ob.events,copy.deepcopy(ob.events))
        self.assertEqual(report["counts"]["matched_selected_contacts"],2)
        self.assertEqual(report["counts"]["recipient_difference_with_equal_context"],0)
        self.assertFalse(report["learning_claim"])

    def test_physical_step_source_trace_variation_not_teacher_causal_result(self):
        a=artificial_native_contact(source_trace=128)
        b=artificial_native_contact(source_trace=0)
        ap=PassiveNativeRecipientObserver(a)
        bp=PassiveNativeRecipientObserver(b)
        with ap.attach():
            physics.step(a)
        with bp.attach():
            physics.step(b)
        report=compare_native_contact_witnesses(ap.events,bp.events)
        self.assertEqual(report["counts"]["matched_selected_contacts"],2)
        self.assertEqual(report["counts"]["confounded_precontext"],0)
        self.assertEqual(report["counts"]["trace_difference_with_equal_context"],1)
        self.assertEqual(report["counts"]["mask_difference_with_equal_context"],1)
        self.assertFalse(report["teacher_specific_causal_learning_proven"])
        self.assertFalse(report["learning_claim"])

    def test_life_epoch_changes_under_actual_native_free_and_spawn(self):
        s=artificial_native_contact()
        ob=PassiveNativeRecipientObserver(s)
        with ob.attach():
            s.free(0)
            self.assertEqual(s.lifecycle[0],0)
            i=s.spawn(x=0,y=0,structure=SHAPE_SINGLE,latent=1,hp=200)
            self.assertEqual(i,0)
            self.assertEqual(ob.prior.epochs[0],1)
        self.assertEqual(len(ob.events),0)

    def test_fail_closed_wrong_mode_and_single_use(self):
        s=artificial_native_contact()
        observer=PassiveNativeRecipientObserver(s)
        with observer.attach():
            with self.assertRaises(ValueError):
                with observer.attach():
                    pass
        with self.assertRaises(ValueError):
            with observer.attach():
                pass
        s.config=physics.PhysicsConfig(max_cells=8,initial_density=0,
                                      latent_operator="masked_copy")
        with self.assertRaises(ValueError):
            PassiveNativeRecipientObserver(s)


if __name__=="__main__":
    unittest.main()
