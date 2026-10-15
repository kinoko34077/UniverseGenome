"""Strict source-only E1 runner guards + synthetic one-step native invariants.

No genuine h0 seed 544/545, no original E0 marker or full original native run.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tests.test_l3_xor_native_source_358 import artificial_native_contact
from tests.l3_e1_native_intervention_363 import (
    archived_e0, exact_gate, study, arm, evaluate_arms,
)
from research.a2_matched_recipient_contract_336 import CONTACT_KEY


class E1AuthenticSourceGuardTest(unittest.TestCase):
    def test_genuine_original_study_denied_without_private_gate_token(self):
        with self.assertRaises(PermissionError):
            study("0"*40)

    def test_pull_request_rejected_before_git_or_original_physics(self):
        with patch.dict(os.environ, {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_REF": "refs/pull/123/merge",
            "GITHUB_RUN_ATTEMPT": "1",
        }):
            with patch("subprocess.run", side_effect=AssertionError(
                "PR must not inspect or run actual source"
            )):
                with self.assertRaises(PermissionError):
                    exact_gate("0"*40)

    def test_archived_genuine_e0_raw_bytes_are_preserved(self):
        e0 = archived_e0()
        self.assertTrue(e0["controls_pass"])
        self.assertEqual(e0["classification"]["544"]["counts"]["matched_contact_keys"], 764)
        self.assertEqual(e0["classification"]["544"]["counts"]["equal_nontrace_precontact"], 668)
        self.assertEqual(e0["classification"]["544"]["counts"]["confounded_nontrace_precontact"], 96)
        p=json.loads(Path("tests/l3_e1_precontact_protocol_363.json").read_text())
        self.assertFalse(p["actual_e1_original_physics_started"])
        self.assertTrue(p["bounds"]["no_retry"])

    def test_synthetic_true_native_one_step_shams_and_bit_absence(self):
        import time
        state=artificial_native_contact(source_trace=0)
        state.config=replace(state.config, trace_bonus_shift=5)
        state.latent[0]=65535
        pre=state.to_snapshot()
        epochs=[0 if value else -1 for value in state.lifecycle]
        start=time.perf_counter()
        baseline=arm(pre,epochs,state.config,0,0,start)
        records=[e for e in baseline["events"] if e["source_slot"]==0 and e["recipient_slot"]==1]
        self.assertEqual(len(records),1)
        original=records[0]
        selection={"native_key":{field:original[field] for field in CONTACT_KEY},
                   "baseline_B_source_trace":0,"intervention_H_source_trace":32,
                   "selection_basis":"SYNTHETIC_FIXTURE_NO_REAL_ORIGINAL_CONTACT"}
        result=evaluate_arms(pre,epochs,state.config,selection,original,start)
        self.assertEqual(result["classification"],
                         "LOCAL_AUTHENTIC_CONTEXT_CONTROLLED_RECEIVER_EFFECT_RETENTION_UNRESOLVED")
        self.assertTrue(result["all_native_observer_parities"])
        self.assertTrue(result["same_value_sham_full_state_parity"])
        self.assertTrue(result["zero_source_bit_pair_negative"])
        self.assertNotEqual(result["trace_only_mask_xor"],0)
        self.assertEqual(result["trace_only_receiver_xor"],result["trace_only_mask_xor"])


if __name__=="__main__":
    unittest.main()
