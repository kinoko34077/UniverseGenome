"""#393 O3-A: synthetic cohort proposal checks ONLY — never native seed physics."""
from __future__ import annotations
from copy import deepcopy
import unittest
from unittest.mock import patch

from research.outer_l3_h0_cohort_393 import (
    STATUS, load_h0_source_contract, validate_h0_cohort_proposal,
)


def proposal():
    p = load_h0_source_contract()
    def rows(seeds):
        return [
            {
                "seed_id": seed,
                "h0_generation": 13,
                "h0_snapshot_sha256": ("%064x" % (seed + 1)),
                "h0_case_sha256": ("%064x" % (seed + 1000)),
                "source_sha": p["accepted_o2_source_main"],
            }
            for seed in seeds
        ]
    # Invented unit-test seed IDs and hashes, NOT materialized h0-qualified
    # native training or held-out cohorts, nor permitted real search.
    return {
        "training": rows((700, 701, 702, 703)),
        "validation": rows((800, 801, 802, 803)),
        "additional_exposed_seeds": [],
        "claimed_control_roles": list(p["control_roles"]),
        "claimed_qualification_phase": "H0_ONLY_BEFORE_CANDIDATE_OUTCOMES",
    }


class CohortSourceOnlyContract(unittest.TestCase):
    def test_no_real_manifest_or_seed_exposure_certified(self):
        p=load_h0_source_contract()
        self.assertEqual(p["mode"], "SOURCE_ONLY_UNPOPULATED_NO_SEED_APPROVAL")
        self.assertFalse(p["exclusions"]["exclusion_completeness_certified"])
        self.assertTrue(p["execution"]["manifest_unpopulated"])
        self.assertTrue(p["execution"]["requires_independent_attestation_in_o3b"])
        self.assertEqual(p["exclusions"]["reserved_closed_inclusive"],[[96,159]])
        self.assertEqual(p["exclusions"]["documented_exposed_seeds"],[544,545])
        self.assertFalse(p["scientific"]["winning_candidate_selected"])
        self.assertFalse(p["scientific"]["learning_claim"])

    def test_matched_disjoint_synthetic_h0_only_rows_never_authorize_Inner(self):
        with patch("core.physics.step",side_effect=AssertionError("no Inner native physics")):
            a=validate_h0_cohort_proposal(proposal())
        b=validate_h0_cohort_proposal(deepcopy(proposal()))
        self.assertEqual(a,b)
        self.assertEqual(a.status,STATUS)
        self.assertEqual(a.training_seed_ids,(700,701,702,703))
        self.assertEqual(a.validation_seed_ids,(800,801,802,803))
        self.assertEqual(len(a.proposal_sha256),64)
        self.assertFalse(a.source_provenance_verified)
        self.assertFalse(a.h0_only_eligibility_verified)
        self.assertFalse(a.exposure_ledger_complete)
        self.assertFalse(a.approved_for_outer_evaluation)
        self.assertFalse(a.actual_physics_executed)
        self.assertFalse(a.independent_validation)
        self.assertFalse(a.winning_candidate_selected)
        self.assertFalse(a.learning_claim)

    def test_exposed_reserved_overlapping_and_unsorted_seeds_reject(self):
        for seed in (0,96,159,544,545,702,801):
            # seed 0 is not inherently exposed, so only deliberately
            # test those in the known frozen exclusion or overlapping set.
            if seed == 0: continue
            case=proposal()
            case["training"][0]["seed_id"]=seed
            with self.subTest(seed=seed),self.assertRaises(ValueError):
                validate_h0_cohort_proposal(case)
        bad=proposal()
        bad["training"].reverse()
        with self.assertRaises(ValueError):
            validate_h0_cohort_proposal(bad)
        case=proposal()
        case["additional_exposed_seeds"]=[700]
        with self.assertRaises(ValueError):
            validate_h0_cohort_proposal(case)
        for extra in ([100,100],[101,100],[True],[-1]):
            case=proposal()
            case["additional_exposed_seeds"]=extra
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                validate_h0_cohort_proposal(case)

    def test_no_unreviewed_source_bad_digest_or_outcome_metadata(self):
        cases=[]
        a=proposal()
        a["training"][0]["source_sha"]="f"*40;cases.append(a)
        a=proposal()
        a["training"][0]["h0_snapshot_sha256"]="xyz";cases.append(a)
        a=proposal()
        a["training"][0]["h0_case_sha256"]="ABCDEF"*10;cases.append(a)
        a=proposal()
        a["training"][0]["h0_generation"]=True;cases.append(a)
        a=proposal()
        a["training"][0]["seed_id"]=True;cases.append(a)
        a=proposal()
        a["training"][0]["fitness"]=999;cases.append(a)
        a=proposal()
        a["teacher_loss_after_1000"]=0;cases.append(a)
        a=proposal()
        a["claimed_qualification_phase"]="POST_OUTCOME_PICKED";cases.append(a)
        a=proposal()
        a["claimed_control_roles"]=["teacher_B","teacher_H"];cases.append(a)
        for c in cases:
            with self.subTest(c=c),self.assertRaises(ValueError):
                validate_h0_cohort_proposal(c)

    def test_missing_or_short_cohorts_fail_without_fabricating_cases(self):
        a=proposal()
        a["training"]=[]
        with self.assertRaises(ValueError):
            validate_h0_cohort_proposal(a)
        a=proposal()
        a["validation"]=a["validation"][:3]
        with self.assertRaises(ValueError):
            validate_h0_cohort_proposal(a)
        a=proposal()
        a["validation"]=None
        with self.assertRaises(ValueError):
            validate_h0_cohort_proposal(a)
        a=proposal()
        a["training"][0]["h0_case_sha256"]=True
        with self.assertRaises(ValueError):
            validate_h0_cohort_proposal(a)


if __name__=="__main__":
    unittest.main()
