"""A1.6 #326: source-only pure algebraic contact-readout eligibility checks.

No UniverseState, IOExperiment, seed or native physics step; no R3/Phase H.
Synthetic words and masks are NOT observations or acceptance evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from core.physics import apply_latent_operator

MANIFEST = Path("docs/research/a1_6_effective_contact_readout_design_326.json")
WORDS = (0, 1, 16, 17, 0x1234, 0x8000, 0xFFFF)
MASKS = (0, 1, 16, 17, 0x1234, 0xAAAA, 0xFFFF)
OPS = ("masked_copy", "masked_xor", "rotate_copy", "masked_and")
BITS = 0xFFFF


def expected_pair_delta(operator: str, source: int, destination: int,
                        mask_b: int, mask_h: int) -> int:
    """Pure 16-bit conditional identity; inputs never come from a new run."""
    delta = (mask_b ^ mask_h) & BITS
    if operator == "masked_copy":
        support = source ^ destination
    elif operator == "masked_xor":
        support = source
    elif operator == "rotate_copy":
        rotated = ((source << 4) | (source >> 12)) & BITS
        support = rotated ^ destination
    elif operator == "masked_and":
        support = destination & (~source & BITS)
    else:
        raise ValueError("operator absent from source-only model")
    return delta & support & BITS


class ContactEligibilitySourceOnlyTest(unittest.TestCase):
    def test_prospective_manifest_cannot_dispatch_or_consume_seeds(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "UG_A1_6_SOURCE_ONLY_CONTACT_READOUT_DESIGN_V1")
        self.assertEqual(manifest["owner_issue"], 326)
        self.assertEqual(manifest["parent_plan_issue"], 171)
        self.assertEqual(manifest["prior_completed_native_owner"], 336)
        self.assertEqual(manifest["status"], "DESIGN_ONLY_NOT_A_RUN_APPROVAL")
        self.assertEqual(manifest["analysis_base_main_sha"],
                         "d482f2f9e3a74adb1598d81dfe5fd51524aa8a06")
        self.assertFalse(manifest["learning_claim"])
        self.assertFalse(manifest["independent_confirmation"])
        proposed = manifest["proposed_single_future_exploratory_operator"]
        self.assertEqual(proposed["name"], "masked_xor")
        self.assertEqual(proposed["selection_status"],
                         "MECHANISM_FIRST_DESIGN_CANDIDATE_ONLY")
        self.assertFalse(proposed["native_physics_change_allowed_now"])
        self.assertTrue(proposed["teacher_content_in_operator_forbidden"])
        cohort = manifest["cohort_constraints"]
        self.assertEqual(cohort["new_seed_ids"], [])
        self.assertTrue(cohort["no_seed_qualification_or_execution"])
        self.assertEqual(cohort["previously_outcome_exposed"], [544, 545])
        self.assertEqual(cohort["independent_seed_start"], 1024)
        self.assertEqual(cohort["old_phase_h_reserved_inclusive"], [96, 159])
        self.assertTrue(cohort["future_cohort_disjointness_must_be_reviewed"])
        permission = manifest["authorization"]
        self.assertFalse(permission["can_run_actions"])
        self.assertFalse(permission["real_native_run_performed_by_this_design"])
        self.assertTrue(permission["separate_future_owner_required"])
        self.assertTrue(permission["explicit_new_trial_scope_and_approval_required"])
        self.assertEqual(manifest["resource_caps"]["max_wall_seconds_per_host"], 900)
        self.assertEqual(manifest["resource_caps"]["max_rss_mib_per_host"], 1536)
        self.assertEqual(manifest["resource_caps"]["max_selected_native_events_per_branch"], 200000)
        self.assertEqual(manifest["resource_caps"]["max_raw_result_bytes"], 131072)
        for value in manifest["immutability"].values():
            self.assertIs(value, True)
        self.assertEqual(
            len(manifest["conditional_equal_precontact_bit_identities"]), 4
        )
        self.assertIn("actual_after_latent_different_equal_context",
                      manifest["denominators"])

    def test_all_existing_operator_pairwise_support_identities(self):
        # 4 * 7 * 7 * 7 * 7 = 9604 source-only direct algebra comparisons.
        for operator in OPS:
            for source in WORDS:
                for recipient in WORDS:
                    for mask_b in MASKS:
                        for mask_h in MASKS:
                            actual_b = apply_latent_operator(
                                operator, source, recipient, mask_b,
                                rotate_amount=4
                            )
                            actual_h = apply_latent_operator(
                                operator, source, recipient, mask_h,
                                rotate_amount=4
                            )
                            self.assertEqual(
                                actual_b ^ actual_h,
                                expected_pair_delta(operator, source, recipient,
                                                    mask_b, mask_h),
                                (operator, source, recipient, mask_b, mask_h),
                            )

    def test_homogeneous_one_effect_is_a_synthetic_eligibility_example(self):
        # The actual historical 544/545 treatment is NOT being rerun.
        self.assertEqual(expected_pair_delta("masked_copy", 1, 1, 0, 1), 0)
        self.assertEqual(expected_pair_delta("masked_xor", 1, 1, 0, 1), 1)
        self.assertEqual(expected_pair_delta("masked_xor", 1, 1, 0, 16), 0)
        self.assertEqual(expected_pair_delta("rotate_copy", 1, 1, 0, 16), 16)
        self.assertEqual(expected_pair_delta("masked_and", 1, 1, 0, 1), 0)

    def test_mask_differences_are_not_native_teacher_effects(self):
        # Even a nonzero algebraic effect on a synthetic contact would not
        # validate native mask reachability, source trace causality or memory.
        for op in OPS:
            for word in WORDS:
                self.assertEqual(expected_pair_delta(op, word, word, 1, 1), 0)


if __name__ == "__main__":
    unittest.main()
