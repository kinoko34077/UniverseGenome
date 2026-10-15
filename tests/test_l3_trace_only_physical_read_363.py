"""#363 minimal physical trace-only controllability — synthetic cells, real native step.

This is NOT historical seed 544/545 physics, independent R3, or teacher learning.
It tests a single pre-selected, genuine native directed collision with an
unchanged source/recipient physical context and only source slow_trace varied.
"""
from __future__ import annotations

import copy
from dataclasses import replace
import unittest

import core.physics as physics
from tests.test_l3_xor_native_source_358 import artificial_native_contact
from tests.support_r2_masked_xor_native_observer_358 import MaskedXorNativeObserver
from tests.support_r2_masked_xor_contact_354 import classify_purported_native_contacts


class NativeTraceOnlyPhysicalReadTest(unittest.TestCase):
    def physical_step(self, trace: int, source_word: int):
        if trace not in (0, 32):
            raise ValueError("predeclared trace width boundary only")
        state = artificial_native_contact(source_trace=trace)
        state.config = replace(state.config, trace_bonus_shift=5)
        state.latent[0] = source_word
        # Exactly same native starting topology, RNG seed, bond, HP and
        # recipient before-word across the two branches except source trace.
        pristine = copy.deepcopy(state)
        before = state.to_snapshot()
        native_mask = physics.transmission_mask
        native_transmit = physics._transmit_latent
        observer = MaskedXorNativeObserver(state)
        with observer.attach():
            measured = physics.step(state)
        direct = physics.step(pristine)
        self.assertIs(physics.transmission_mask, native_mask)
        self.assertIs(physics._transmit_latent, native_transmit)
        self.assertEqual(state.to_snapshot(), pristine.to_snapshot())
        self.assertEqual(measured.latent_transmission_count, 1)
        self.assertEqual(direct.latent_transmission_count, 1)
        self.assertEqual(len(observer.events), 2)
        outgoing = [e for e in observer.events if
                    e["source_slot"] == 0 and e["recipient_slot"] == 1]
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0]["source_life_epoch"], 0)
        self.assertEqual(outgoing[0]["source_latent_before"], source_word)
        self.assertEqual(outgoing[0]["source_trace_start"], trace)
        self.assertEqual(outgoing[0]["trace_bonus_shift"], 5)
        return before, observer.events, outgoing[0], state.to_snapshot()

    def test_real_native_selected_trace_width_changes_actual_receiver(self):
        low = self.physical_step(0, 65535)
        high = self.physical_step(32, 65535)
        before_low, before_high = copy.deepcopy(low[0]), copy.deepcopy(high[0])
        # Source slow_trace is THE ONLY intentional initial physical delta.
        before_high["arrays"]["slow_trace"] = before_low["arrays"]["slow_trace"]
        self.assertEqual(before_high, before_low)
        self.assertEqual(low[2]["native_generation"], high[2]["native_generation"])
        self.assertEqual(low[2]["physical_address"], high[2]["physical_address"])
        self.assertEqual(low[2]["source_xy"], high[2]["source_xy"])
        self.assertEqual(low[2]["source_bond_strength"], high[2]["source_bond_strength"])
        self.assertEqual(low[2]["recipient_latent_before"], high[2]["recipient_latent_before"])
        self.assertEqual(low[2]["native_mask"].bit_count(), 1)
        self.assertEqual(high[2]["native_mask"].bit_count(), 2)
        mask_delta = low[2]["native_mask"] ^ high[2]["native_mask"]
        self.assertNotEqual(mask_delta, 0)
        self.assertEqual(
            low[2]["recipient_latent_after"] ^ high[2]["recipient_latent_after"],
            mask_delta,
        )
        matched = classify_purported_native_contacts(high[1], low[1])
        c = matched["counts"]
        self.assertEqual(c["matched_contacts"], 2)
        self.assertEqual(c["comparable_precontact"], 2)
        self.assertEqual(c["source_trace_different"], 1)
        self.assertEqual(c["native_mask_different"], 1)
        self.assertEqual(c["mask_xor_source_support_nonzero"], 1)
        self.assertEqual(c["recipient_after_different"], 1)
        self.assertEqual(matched["classification"],
                         "LOCAL_RECEIVER_EFFECT_RETENTION_UNRESOLVED")
        self.assertFalse(matched["native_source_provenance_verified_here"])
        self.assertFalse(matched["learning_claim"])

    def test_same_value_trace_sham_does_not_create_false_effect(self):
        a = self.physical_step(32, 65535)
        b = self.physical_step(32, 65535)
        self.assertEqual(a[0], b[0])
        self.assertEqual(a[3], b[3])
        result = classify_purported_native_contacts(a[1], b[1])
        self.assertEqual(result["counts"]["source_trace_different"], 0)
        self.assertEqual(result["counts"]["native_mask_different"], 0)
        self.assertEqual(result["counts"]["recipient_after_different"], 0)
        self.assertEqual(result["classification"],
                         "NEGATIVE_NO_MATCHED_RECIPIENT_EFFECT")

    def test_mask_change_without_source_bit_is_actual_zero_response(self):
        low = self.physical_step(0, 0)
        high = self.physical_step(32, 0)
        self.assertNotEqual(low[2]["native_mask"], high[2]["native_mask"])
        self.assertEqual(low[2]["recipient_latent_after"],
                         high[2]["recipient_latent_after"])
        result = classify_purported_native_contacts(high[1], low[1])
        self.assertEqual(result["counts"]["source_trace_different"], 1)
        self.assertEqual(result["counts"]["native_mask_different"], 1)
        self.assertEqual(result["counts"]["mask_xor_source_support_nonzero"], 0)
        self.assertEqual(result["counts"]["recipient_after_different"], 0)
        self.assertEqual(result["classification"],
                         "NEGATIVE_NO_MATCHED_RECIPIENT_EFFECT")


if __name__ == "__main__":
    unittest.main()
