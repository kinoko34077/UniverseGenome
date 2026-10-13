"""A1.4 #317: frozen native mask/latent support classification tests."""
import unittest
from core.physics import apply_latent_operator
from research.a1_native_bit_support_317 import classify, period_for, PERIODS, EXPECTED_SELECTED

def event(*, source, recipient, mask, trace, generation=40, address=19,
          recipient_slot=2, source_epoch=0):
    return {
        "native_generation":generation, "address":address,
        "source_slot":1, "recipient_slot":recipient_slot,
        "source_epoch":source_epoch, "recipient_epoch":0,
        "source_xy":[1,2], "bond_strength":0, "shift":5,
        "source_latent_before":source, "recipient_latent_before":recipient,
        "source_trace_start":trace, "native_mask":mask,
        "recipient_latent_after":apply_latent_operator("masked_copy",source,recipient,mask),
    }

class BitSupportTests(unittest.TestCase):
    def compare(self, source, recipient, mask_b=1, mask_h=3, generation=40):
        return classify(
            [event(source=source,recipient=recipient,mask=mask_b,trace=31,generation=generation)],
            [event(source=source,recipient=recipient,mask=mask_h,trace=32,generation=generation)],
            h0_generation=1,
        )

    def test_all_three_mutually_exclusive_physical_classifications(self):
        equal=self.compare(3,3)
        self.assertEqual(equal["counts"]["H1_equal_source_recipient_latent"],1)
        self.assertEqual(equal["counts"].get("H2_differing_latent_bits_unselected",0),0)
        missed=self.compare(4,0)
        self.assertEqual(missed["counts"]["H2_differing_latent_bits_unselected"],1)
        changed=self.compare(3,0)
        self.assertEqual(changed["counts"]["H3_nonzero_overlap_real_native_effect"],1)
        self.assertEqual(changed["all_changed_mask_original_events"][0]["delta_mask_overlap"],2)
        self.assertFalse(changed["learning_claim"])

    def test_periods_are_fixed_and_relative_to_h0_generation(self):
        self.assertEqual(PERIODS,((1,100),(101,250),(251,500),(501,1000)))
        self.assertEqual([period_for(n) for n in (1,100,101,250,251,500,501,1000)],
                         ["1-100","1-100","101-250","101-250",
                          "251-500","251-500","501-1000","501-1000"])
        for n in (0,1001):
            with self.assertRaises(ValueError):period_for(n)
        one=self.compare(0,0,generation=501)
        self.assertEqual(one["by_frozen_relative_period"]["501-1000"]["changed_mask"],1)
        self.assertEqual(EXPECTED_SELECTED,{544:(764,95,36),545:(966,0,0)})

    def test_quantization_and_physical_pair_denominators(self):
        b=event(source=1,recipient=0,mask=1,trace=31)
        h=event(source=1,recipient=0,mask=1,trace=32)
        result=classify([b],[h],h0_generation=1)
        self.assertEqual(result["counts"]["matched"],1)
        self.assertEqual(result["counts"]["quantized_identical_mask"],1)
        self.assertEqual(result["counts"].get("changed_mask",0),0)
        self.assertEqual(result["all_changed_mask_original_events"],[])
        no_match=classify([b],[{**h,"recipient_slot":3}],h0_generation=1)
        self.assertEqual(no_match["counts"]["unmatched_topology"],2)

    def test_invalid_or_confounded_original_recipient_is_not_positive_evidence(self):
        b=event(source=3,recipient=0,mask=1,trace=31)
        h=event(source=3,recipient=0,mask=3,trace=32)
        wrong={**h,"recipient_latent_after":0}
        with self.assertRaises(ValueError):classify([b],[wrong],h0_generation=1)
        drift={**h,"source_xy":[9,9]}
        report=classify([b],[drift],h0_generation=1)
        self.assertEqual(report["counts"]["confounded_nontrace"],1)
        self.assertEqual(report["counts"].get("changed_mask",0),0)
        with self.assertRaises(ValueError):classify([b,b],[h],h0_generation=1)
        incomplete={**h}
        del incomplete["native_mask"]
        with self.assertRaises(ValueError):classify([b],[incomplete],h0_generation=1)

if __name__=="__main__":unittest.main()
