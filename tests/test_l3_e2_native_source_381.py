"""#381 E2 original native long-horizon runner acceptance, PR tests are inert."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from tests.l3_e2_original_native_381 import (
    actual_e1_archive, exact_gate, study, trajectory_arm,
    downstream_candidate_graph,
)
from tests.test_l3_e2_retention_protocol_379 import event


class E2OriginalRunnerNonexecutingGates(unittest.TestCase):
    def test_original_physics_study_refuses_without_reviewed_private_token(self):
        with self.assertRaises(PermissionError):
            study("0"*40)

    def test_original_native_arm_refuses_before_any_cloning_or_physics(self):
        with self.assertRaises(PermissionError):
            trajectory_arm({}, [], None, source_slot=31, source_trace=32,
                           zero_source_latent=False, absolute_targets={50}, start=0)

    def test_pull_request_refuses_before_git_even_with_original_marker_present(self):
        with patch.dict(os.environ, {
            "GITHUB_EVENT_NAME":"pull_request",
            "GITHUB_REF":"refs/pull/381/merge",
            "GITHUB_RUN_ATTEMPT":"1",
        }):
            with patch("subprocess.run", side_effect=AssertionError(
                "No Git history or physics may run in an E2 PR"
            )):
                with self.assertRaises(PermissionError):
                    exact_gate("0"*40)

    def test_read_archived_E1_source_bytes_without_world_construction(self):
        e1 = actual_e1_archive()
        key = e1["local_intervention"]["selected"]["native_key"]
        self.assertEqual((key["native_generation"],key["physical_address"],
                          key["source_slot"],key["recipient_slot"],
                          key["source_life_epoch"],key["recipient_life_epoch"]),
                         (49,500,31,22,0,0))
        self.assertEqual(e1["local_intervention"]["trace_only_receiver_xor"],1)
        self.assertFalse(e1["learning_claim"])

    def test_synthetic_event_graph_never_proves_epoch_turnover(self):
        baseline=event(source_latent=0,after=1)
        treated=event(source_latent=1,after=0)
        def arm(e, after):
            lat=[0]*32
            lat[4]=after
            return {
                "events":[e],
                "terminal_living_epochs":{(4,1)},
                "final_snapshot":{"arrays":{"latent":lat}},
                "free_events":[],
            }
        result=downstream_candidate_graph(
            arm(baseline,1),arm(treated,0),selected_contact_post=50
        )
        self.assertEqual(
            result["native_epoch_candidate_counts"]["CANDIDATE_NATIVE_EDGE_REQUIRES_CHAIN_AND_TURNOVER_PROOF"],
            1,
        )
        self.assertEqual(result["candidate_living_distinct_epoch_count"],1)
        self.assertFalse(result["original_donor_or_receiver_freed_both_arms"])
        self.assertFalse(result["candidate_turnover_path_not_independently_confirmed"])
        self.assertFalse(result["causal_cross_life_epoch_turnover_proven"])


if __name__=="__main__":
    unittest.main()
