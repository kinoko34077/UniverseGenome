"""Only synthetic/dictionary tests of predeclared E2 report classification."""
from __future__ import annotations

from copy import deepcopy
import unittest

from research.a2_e2_outcome_scoring_336 import (
    COUNT_KEYS, INPUT_SCHEMA, CONTACT_SCHEMA,
    INVALID, NEGATIVE, UNRESOLVED, classify_report,
)


def fake_record(seed,role):
    return {
        "seed":seed, "role":role,
        "original_h0_sha256":"a"*64,
        "native_selected_events":10,
        "native_selected_event_sha256":"b"*64,
        "native_free_event_sha256":"c"*64,
        "checkpoints":{h:"d"*64 for h in ("0","1","10","100","250","500","1000")},
        "distribution":{"1000":{"active_cells":11,"distinct_latent_words":1}},
        "uninstrumented_full_state_parity":True,
    }


def synthetic_report():
    counts={key:0 for key in COUNT_KEYS}
    counts.update({
        "matched_selected_contacts":10,
        "same_nontrace_context":10,
        "trace_difference_with_equal_context":3,
        "mask_difference_with_equal_context":2,
    })
    return {
        "schema":INPUT_SCHEMA,
        "original_masked_copy_golden_parity":True,
        "negative_BH_full_equality":True,
        "positive_BB_sham_full_equality":True,
        "independent_confirmation":False,
        "learning_claim":False,
        "conditions":{
            "positive_exposed_seed":544, "negative_exposed_seed":545,
            "teacher_B_H":[66,8], "post_h0_native_steps":1000,
            "treatment_operator":"rotate_copy","baseline_operator":"masked_copy",
            "rotate_amount":4, "trace_decay_rate":256,
            "only_physical_config_delta":"latent_operator",
        },
        "environment":{"wall_seconds":6.5,"rss_mib":100.0},
        "data":{
            "544":{role:fake_record(544,role) for role in ("b","h","control")},
            "545":{role:fake_record(545,role) for role in ("b","h")},
        },
        "positive_native_paired_read_contrast":{"schema":CONTACT_SCHEMA,"counts":counts,
                                                  "b_native_source_event_count":10,
                                                  "h_native_source_event_count":10},
    }


class PreOutcomeStaticScoringTests(unittest.TestCase):
    def test_valid_zero_is_scoped_negative_not_learning(self):
        result=classify_report(synthetic_report())
        self.assertEqual(result["classification"],NEGATIVE)
        self.assertTrue(result["no_teacher_reference_used"])
        self.assertEqual(result["no_teacher_context"]["final_distinct_latent_words"],1)
        self.assertFalse(result["no_teacher_context"]["equality_is_causal_sham"])
        self.assertEqual(result["local_receiver_effect"],"NO_MATCHED_NATIVE_RECEIVER_DELTA")
        self.assertEqual(result["long_term_retention"],"NOT_ESTABLISHED")
        self.assertFalse(result["learning_claim"])

    def test_local_receiver_difference_cannot_claim_transient_or_persistent(self):
        report=synthetic_report()
        counts=report["positive_native_paired_read_contrast"]["counts"]
        counts["recipient_difference_with_equal_context"]=1
        counts["trace_mask_recipient_difference_with_equal_context"]=1
        result=classify_report(report)
        self.assertEqual(result["classification"],UNRESOLVED)
        self.assertEqual(result["local_receiver_effect"],"OBSERVED_MATCHED_NATIVE_RECEIVER_DELTA")
        self.assertEqual(result["long_term_retention"],"NOT_ESTABLISHED")
        self.assertFalse(result["learning_claim"])

    def test_no_teacher_is_own_h0_not_same_teacher_sham(self):
        report=synthetic_report()
        report["data"]["544"]["control"]["original_h0_sha256"]="f"*64
        self.assertEqual(classify_report(report)["classification"],NEGATIVE)

    def test_no_teacher_real_reference_is_required_and_noncausal(self):
        report=synthetic_report()
        report["data"]["544"]["control"]["distribution"]["1000"]["distinct_latent_words"]=12
        self.assertEqual(classify_report(report)["classification"],INVALID)
        report=synthetic_report()
        del report["data"]["544"]["control"]["distribution"]
        self.assertEqual(classify_report(report)["classification"],INVALID)

    def test_missing_source_distinct_control_is_not_evaluable(self):
        report=synthetic_report()
        del report["data"]["544"]["control"]
        self.assertEqual(classify_report(report)["classification"],INVALID)

    def test_zero_denominator_and_entirely_confounded_invalid(self):
        for matched,same,confounded in ((0,0,0),(4,0,4)):
            with self.subTest(matched=matched):
                report=synthetic_report()
                counts=report["positive_native_paired_read_contrast"]["counts"]
                counts.update({
                    "matched_selected_contacts":matched,
                    "same_nontrace_context":same,
                    "confounded_precontext":confounded,
                    "trace_difference_with_equal_context":0,
                    "mask_difference_with_equal_context":0,
                })
                self.assertEqual(classify_report(report)["classification"],INVALID)

    def test_event_count_consistency_and_missing_provenance_fail(self):
        report=synthetic_report()
        report["positive_native_paired_read_contrast"]["b_native_source_event_count"]=11
        self.assertEqual(classify_report(report)["classification"],INVALID)
        report=synthetic_report()
        del report["positive_native_paired_read_contrast"]["h_native_source_event_count"]
        self.assertEqual(classify_report(report)["classification"],INVALID)

    def test_failed_sentinel_controls_budget_and_unexplained_effect(self):
        modifications = (
            lambda d: d.update({"negative_BH_full_equality":False}),
            lambda d: d["data"]["545"]["h"]["checkpoints"].update({"1000":"f"*64}),
            lambda d: d["environment"].update({"wall_seconds":901}),
            lambda d: d["positive_native_paired_read_contrast"]["counts"].update(
                {"recipient_difference_with_equal_context":1}),
            lambda d: d["conditions"].update({"rotate_amount":5}),
            lambda d: d.update({"learning_claim":True}),
        )
        for mutate in modifications:
            report=synthetic_report()
            mutate(report)
            self.assertEqual(classify_report(report)["classification"],INVALID)


if __name__=="__main__":
    unittest.main()
