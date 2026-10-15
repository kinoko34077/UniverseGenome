"""#358: true source-native step on artificially constructed synthetic cells.

This is neither old R2 seed544/545 nor a new independent scientific cohort.
It verifies instrumented/uninstrumented actual native state parity and the
complete selected transmission field provenance; no teacher result is claimed.
"""
import copy
import os
import unittest
from unittest.mock import patch

import core.physics as physics
from core.state import SHAPE_SINGLE
from tests.support_r2_masked_xor_native_observer_358 import MaskedXorNativeObserver
from tests.support_r2_masked_xor_contact_354 import classify_purported_native_contacts


def artificial_native_contact(*, source_trace=128):
    config=physics.PhysicsConfig(
        max_cells=8,initial_density=0,hp_decay=0,noise_rate=0,
        fragmentation_enabled=False,fusion_enabled=False,
        latent_operator="masked_xor",rotate_amount=4,
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


class MaskedXorNativeActualSourceParity(unittest.TestCase):
    def test_source_native_step_matches_uninstrumented_complete_snapshot(self):
        s=artificial_native_contact()
        original=copy.deepcopy(s)
        old_mask=physics.transmission_mask
        old_transmit=physics._transmit_latent
        native_result=physics.step(original)
        ob=MaskedXorNativeObserver(s)
        with ob.attach():
            observed_result=physics.step(s)
        self.assertIs(physics.transmission_mask,old_mask)
        self.assertIs(physics._transmit_latent,old_transmit)
        self.assertEqual(s.to_snapshot(),original.to_snapshot())
        self.assertEqual(native_result.latent_transmission_count,1)
        self.assertEqual(observed_result.latent_transmission_count,1)
        self.assertEqual(len(ob.events),2)
        self.assertEqual(ob.schema,"UG_R2_MASKED_XOR_SOURCE_ONLY_CONTACT_WITNESS_V0_354")
        for e in ob.events:
            self.assertEqual(e["source_life_epoch"],0)
            self.assertEqual(e["recipient_life_epoch"],0)
            self.assertEqual(e["native_operator"],"masked_xor")
            self.assertEqual(e["source_latent_before"],1)
            self.assertEqual(e["recipient_latent_before"],1)
            self.assertEqual(e["native_generation"],0)
            self.assertEqual(e["source_bond_strength"],4)
        report=classify_purported_native_contacts(ob.events,copy.deepcopy(ob.events))
        self.assertEqual(report["counts"]["matched_contacts"],2)
        self.assertEqual(report["counts"]["recipient_after_different"],0)
        self.assertFalse(report["learning_claim"])

    def test_physical_step_source_trace_variation_not_teacher_causal_result(self):
        a=artificial_native_contact(source_trace=128)
        b=artificial_native_contact(source_trace=0)
        ap=MaskedXorNativeObserver(a)
        bp=MaskedXorNativeObserver(b)
        with ap.attach():
            physics.step(a)
        with bp.attach():
            physics.step(b)
        report=classify_purported_native_contacts(ap.events,bp.events)
        self.assertEqual(report["counts"]["matched_contacts"],2)
        self.assertEqual(report["counts"]["confounded_precontact"],0)
        self.assertEqual(report["counts"]["source_trace_different"],1)
        self.assertEqual(report["counts"]["native_mask_different"],1)
        self.assertFalse(report["native_source_provenance_verified_here"])
        self.assertFalse(report["learning_claim"])

    def test_life_epoch_changes_under_actual_native_free_and_spawn(self):
        s=artificial_native_contact()
        ob=MaskedXorNativeObserver(s)
        with ob.attach():
            s.free(0)
            self.assertEqual(s.lifecycle[0],0)
            i=s.spawn(x=0,y=0,structure=SHAPE_SINGLE,latent=1,hp=200)
            self.assertEqual(i,0)
            self.assertEqual(ob.prior.epochs[0],1)
        self.assertEqual(len(ob.events),0)

    def test_one_factor_and_gate_stay_nonexecuting_in_pull_request(self):
        from dataclasses import asdict
        from tests.l3_xor_exposed_pilot_358 import candidate_config, verify_study_gate
        reference, altered = candidate_config()
        changed = {k for k,v in asdict(reference).items() if asdict(altered)[k] != v}
        self.assertEqual(changed, {"latent_operator"})
        self.assertEqual(altered.rotate_amount, reference.rotate_amount)
        self.assertEqual(altered.rotate_amount, 4)
        # A negative PR gate test must not depend on the ambient Actions event.
        # The original one-shot marker exists on main; push jobs may use a
        # shallow checkout without HEAD^, which is not a PR-gate regression.
        with patch.dict(os.environ, {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_REF": "refs/pull/1/merge",
            "GITHUB_RUN_ATTEMPT": "1",
        }):
            with patch("subprocess.run", side_effect=AssertionError(
                "PR gate must reject before inspecting Git history"
            )):
                with self.assertRaises(PermissionError):
                    verify_study_gate("0" * 40)

    def test_fail_closed_wrong_mode_and_single_use(self):
        s=artificial_native_contact()
        observer=MaskedXorNativeObserver(s)
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
            MaskedXorNativeObserver(s)


if __name__=="__main__":
    unittest.main()
