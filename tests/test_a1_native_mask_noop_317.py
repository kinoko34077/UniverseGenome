"""Source-native masked_copy bitwise no-op A1.3 contract tests."""
import unittest
from core.physics import apply_latent_operator
from research.a1_native_mask_noop_317 import classify, mask_effect


class MaskNoopTests(unittest.TestCase):
    def event(self, *, mask=1, src=0, dst=0, trace=0, gen=9):
        return {
            "native_generation": gen, "address": 19,
            "source_slot": 1, "recipient_slot": 2,
            "source_epoch": 0, "recipient_epoch": 0,
            "source_xy": [1,2], "bond_strength": 0, "shift": 5,
            "source_latent_before": src, "recipient_latent_before": dst,
            "source_trace_start": trace, "native_mask": mask,
            "recipient_latent_after": apply_latent_operator("masked_copy", src, dst, mask),
        }

    def test_exact_original_masked_copy_math_and_noop_bits(self):
        self.assertEqual(mask_effect(source=0, recipient=0, mask_b=1, mask_h=3), 0)
        self.assertEqual(mask_effect(source=3, recipient=0, mask_b=1, mask_h=3), 2)
        with self.assertRaises(ValueError):
            mask_effect(source=-1, recipient=0, mask_b=1, mask_h=2)

    def test_different_mask_without_latent_effect_is_not_learning(self):
        result=classify([self.event(mask=1,trace=31,src=0,dst=0)],
                        [self.event(mask=3,trace=32,src=0,dst=0)])
        self.assertEqual(result["counts"]["different_mask"],1)
        self.assertEqual(result["counts"]["different_mask_algebraic_inert"],1)
        self.assertEqual(result["counts"]["different_mask_native_output_different"],0)
        self.assertFalse(result["causal_readout_claim"])

    def test_different_mask_with_genuine_latent_effect_is_detected(self):
        result=classify([self.event(mask=1,trace=31,src=3,dst=0)],
                        [self.event(mask=3,trace=32,src=3,dst=0)])
        self.assertEqual(result["counts"]["different_mask_potential_latent_effect"],1)
        self.assertEqual(result["counts"]["different_mask_native_output_different"],1)

    def test_fails_closed_on_wrong_recipient_or_confounded_state(self):
        original=self.event(mask=1,trace=31,src=3,dst=0)
        wrong=dict(original,recipient_latent_after=55)
        with self.assertRaises(ValueError):
            classify([wrong],[self.event(mask=3,trace=32,src=3,dst=0)])
        changed=dict(self.event(mask=3,trace=32,src=0,dst=0),source_xy=[2,2])
        result=classify([self.event(mask=1,trace=31,src=0,dst=0)],[changed])
        self.assertEqual(result["counts"]["confounded_nontrace"],1)
        self.assertEqual(result["counts"]["different_mask"],0)
        with self.assertRaises(ValueError):
            classify([original,original],[])


if __name__=="__main__":
    unittest.main()
