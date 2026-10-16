"""#379 E2 entirely source-only: frozen science boundary, no original native step."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import unittest

from research.a2_matched_recipient_contract_336 import CONTACT_KEY
from tests.support_l3_e2_retention_379 import (
    horizon_plan, classify_paired_native_edge, MECHANICAL_CONTEXT,
)

EXPECTED_E1_SHA = "3d7075a727c6bb1e2c08887cf7b1dc8313594d1f5f788ddc1b7915ddcd182164"


def event(*, source_latent: int, after: int) -> dict:
    # Entirely invented test fixture; NOT an original authentic selected event.
    x = {
        "native_generation": 51, "physical_address": 12,
        "source_slot": 22, "recipient_slot": 4,
        "source_life_epoch": 0, "recipient_life_epoch": 1,
        "source_latent_before": source_latent,
        "recipient_latent_before": 1,
        "recipient_latent_after": after,
        "native_mask": 1,
    }
    for k in MECHANICAL_CONTEXT:
        x[k] = [1, 2] if k in ("source_xy", "recipient_xy") else 1
    return x


class E2OriginalDownstreamSourceContract(unittest.TestCase):
    def test_provenance_and_nonexecuting_original_E1_evidence(self):
        p = json.loads(Path("tests/l3_e2_retention_protocol_379.json").read_text())
        self.assertEqual(p["owner_issue"], 379)
        self.assertEqual(p["parent_owner_issue"], 363)
        self.assertEqual(p["status"],
                         "SOURCE_ONLY_DESIGN_NOT_AUTHORIZED_TO_EXECUTE_NATIVE_E2")
        self.assertFalse(p["actual_e2_original_native_physics_started"])
        self.assertTrue(p["cohort"]["not_independent"])
        self.assertTrue(p["cohort"]["original_e0_e1_one_shots_consumed"])
        self.assertTrue(p["resources"]["no_retry"])
        self.assertTrue(p["resources"]["no_effectful_workflow_or_marker_in_this_design"])
        self.assertFalse(p["scientific_claims"]["learning_claim"])
        self.assertFalse(p["scientific_claims"]["original_carrier_turnover_retention_proven"])
        self.assertFalse(p["scientific_claims"]["natural_spontaneous_teacher_dependent_BH_causality_proven"])
        archive = Path(p["evidence"]["e1_raw_archive"]).read_text().strip()
        raw = base64.b64decode(archive, validate=True)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_E1_SHA)
        original = json.loads(raw)
        self.assertEqual(original["source_sha"],
                         "4e5b43bfab3515bc8945f6ffdc38fe9ca8027fcf")
        self.assertEqual(original["schema"],
                         "UG_L3_363_E1_AUTHENTIC_PRECONTACT_INTERVENTION_V1")
        selected = original["local_intervention"]["selected"]
        self.assertEqual(selected["native_key"], {
            k: p["evidence"]["selected"][k] for k in CONTACT_KEY
        })
        self.assertEqual(selected["baseline_B_source_trace"], 32)
        self.assertEqual(selected["intervention_H_source_trace"], 0)
        self.assertEqual(original["local_intervention"]["trace_only_mask_xor"], 1)
        self.assertEqual(original["local_intervention"]["trace_only_receiver_xor"], 1)
        self.assertFalse(original["independent_confirmation"])
        self.assertFalse(original["learning_claim"])

    def test_h0_and_post_selected_absolute_clocks_cannot_be_conflated(self):
        schedule = horizon_plan(2)  # invented sample h0 generation, NOT real 544.
        self.assertEqual(schedule["original_contact_pre_generation"], 49)
        self.assertEqual(schedule["original_contact_post_generation"], 50)
        self.assertEqual(schedule["post_h0"][-1]["absolute_snapshot_generation"], 1002)
        self.assertEqual(schedule["post_selected"][0]["absolute_snapshot_generation"], 50)
        self.assertEqual(schedule["post_selected"][-1]["absolute_snapshot_generation"], 1050)
        self.assertEqual(schedule["required_last_generation"], 1050)
        for invalid in (-1, 49, True, 0.5, "2"):
            with self.assertRaises(ValueError):
                horizon_plan(invalid)

    def test_native_masked_xor_candidate_is_not_confirmed_lineage(self):
        baseline = event(source_latent=0, after=1)
        intervention = event(source_latent=1, after=0)
        out = classify_paired_native_edge(
            baseline, intervention,
            affected_source_epochs=frozenset({(22, 0)}),
            living_recipient_epochs=frozenset({(4, 1)}),
        )
        self.assertEqual(out["native_source_masked_contribution_xor"], 1)
        self.assertEqual(out["recipient_after_xor"], 1)
        self.assertEqual(out["classification"],
                         "CANDIDATE_NATIVE_EDGE_REQUIRES_CHAIN_AND_TURNOVER_PROOF")
        self.assertFalse(out["event_provenance_verified_here"])
        self.assertFalse(out["physical_turnover_or_retention_proven_here"])
        self.assertFalse(out["learning_claim"])

    def test_native_lineage_fail_closed_on_missing_path_or_living_epoch(self):
        baseline = event(source_latent=0, after=1)
        intervention = event(source_latent=1, after=0)
        def verdict(sources, living):
            return classify_paired_native_edge(
                baseline, intervention,
                affected_source_epochs=frozenset(sources),
                living_recipient_epochs=frozenset(living),
            )["classification"]
        self.assertEqual(verdict([], [(4, 1)]),
                         "SOURCE_NOT_IN_VERIFIED_PERTURBATION_PATH")
        self.assertEqual(verdict([(22, 0)], [(4, 0)]),
                         "RECIPIENT_EPOCH_NOT_VERIFIED_LIVING")
        self.assertEqual(verdict([(22, 0)], [(4, 1)]),
                         "CANDIDATE_NATIVE_EDGE_REQUIRES_CHAIN_AND_TURNOVER_PROOF")

    def test_mechanical_and_native_event_divergence_are_not_local_causal_proof(self):
        a = event(source_latent=0, after=1)
        b = event(source_latent=1, after=0)
        kw = dict(affected_source_epochs=frozenset({(22, 0)}),
                  living_recipient_epochs=frozenset({(4, 1)}))
        b2 = dict(b, physical_address=13)
        self.assertEqual(
            classify_paired_native_edge(a, b2, **kw)["classification"],
            "NOT_COMPARABLE_DIFFERENT_NATIVE_SELECTED_CONTACT")
        b2 = dict(b, source_hp=2)
        self.assertEqual(
            classify_paired_native_edge(a, b2, **kw)["classification"],
            "POST_TREATMENT_MECHANICAL_CONTEXT_DIVERGENCE")

    def test_bad_xor_or_incomplete_native_event_rejects(self):
        a = event(source_latent=0, after=1)
        b = event(source_latent=1, after=0)
        kw = dict(affected_source_epochs=frozenset({(22, 0)}),
                  living_recipient_epochs=frozenset({(4, 1)}))
        with self.assertRaises(ValueError):
            classify_paired_native_edge(a, dict(b, recipient_latent_after=1), **kw)
        with self.assertRaises(ValueError):
            classify_paired_native_edge(a, {"native_generation":51}, **kw)
        with self.assertRaises(ValueError):
            classify_paired_native_edge(a, b, affected_source_epochs={(22,0)},
                                         living_recipient_epochs=frozenset({(4,1)}))
        with self.assertRaises(ValueError):
            classify_paired_native_edge(dict(a, source_life_epoch=-1), b, **kw)

    def test_no_source_mask_overlap_is_not_transmission(self):
        a = event(source_latent=0, after=1)
        b = event(source_latent=0, after=1)
        verdict = classify_paired_native_edge(
            a,b, affected_source_epochs=frozenset({(22,0)}),
            living_recipient_epochs=frozenset({(4,1)}))
        self.assertEqual(verdict["classification"],
                         "NO_NEW_NATIVE_MASKED_SOURCE_BIT_DELTA")


if __name__ == "__main__":
    unittest.main()
