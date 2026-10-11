"""D16 offline crash-prefix replay tests: synthetic optimizer metadata only."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from research.d16_complete_prefix_recovery_217 import (
    immutable_receipt, replay_completed_prefix,
)
from research.d16_complete_round_checkpoint_217 import (
    KIND, write_completed_atomic,
)
from research.d16_twojob_run_control_217 import D16BoundaryError, GlobalClock
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

SOURCE="b"*40
START=1780000000000


def synthetic_state(initial, number):
    opt=SteadyStateOptimizer.from_snapshot(initial)
    opt.generation=number  # no original physical evaluations in this test
    snapshot=opt.to_snapshot()
    cat={name:{
        "complete_nonfailure_count":0,
        "native_replacement_count":0,
    } for name in sorted(set(slot.category for slot in opt.slots))}
    return {
        "kind":KIND,"source_sha":SOURCE,"seed":0,"ordinal":number,
        "selected_snapshot":snapshot,"selected_v7_sha256":digest(snapshot),
        "global_wall_ms":number*1000-100,
        "learning_claim":False,
        "d15_verified_observer":{
            "source_commit":SOURCE,"base_seed":0,
            "before_optimizer_generation":number-1,
            "selected_optimizer_generation":number,
            "selected_post_v7_sha256":digest(snapshot),
            "evaluated_native_worlds":128,"selected_native_worlds":128,
            "d15_journal_chain_verified":True,
            "original_selected_once_proven_by_D15_final":True,
            "categories":cat,"actual_native_replacement_count":0,
        },
    }


class CompletePrefixReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="d16-prefix-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.genesis=SteadyStateOptimizer.from_defaults(base_seed=0).to_snapshot()

    def write(self,n,*,elapsed=None,local=None):
        checkpoint=synthetic_state(self.genesis,n)
        write_completed_atomic(self.root,checkpoint)
        return immutable_receipt(
            self.root,source_sha=SOURCE,seed=0,ordinal=n,
            job=1 if n==1 else 2,
            clock=GlobalClock(START,1000 if n==2 else 0),
            now_unix_ms=START+(elapsed if elapsed is not None else n*1000),
            local_elapsed_ms=local if local is not None else 1000,
        )

    def replay(self):
        return replay_completed_prefix(
            self.root,source_sha=SOURCE,seed=0,
            original_genesis=self.genesis,study_started_unix_ms=START,
        )

    def test_empty_prefix_is_safe_not_science(self):
        state=self.replay()
        self.assertEqual(state.count,0)
        self.assertEqual(state.next_selected_round,1)
        self.assertEqual(state.stage.result,"IN_PROGRESS")
        self.assertFalse(state.provenance_authenticated)

    def test_genuine_shape_complete_prefix_1_plus_1_test_only(self):
        self.write(1)
        first=self.replay()
        self.assertEqual(first.stage.result,"HANDOFF_READY")
        self.assertEqual(first.next_selected_round,2)
        self.write(2)
        second=self.replay()
        self.assertEqual(second.stage.result,"FIXTURE_COMPLETE_NO_SCIENCE")
        self.assertEqual(second.next_selected_round,3)
        self.assertFalse(second.provenance_authenticated)

    def test_orphan_completed_round_without_time_receipt_rejected(self):
        write_completed_atomic(self.root,synthetic_state(self.genesis,1))
        with self.assertRaises(D16BoundaryError):
            self.replay()

    def test_prefix_hole_missing_first_round_rejected(self):
        self.write(2)
        with self.assertRaises(D16BoundaryError):
            self.replay()

    def test_tampered_receipt_and_completed_state_rejected(self):
        receipt=self.write(1)
        original=receipt.read_bytes()
        data=json.loads(original)
        data["selected_file_sha256"]="0"*64
        receipt.write_text(json.dumps(data))
        with self.assertRaises(D16BoundaryError):
            self.replay()
        receipt.write_bytes(original)
        completed=self.root/"selected-round-01.json"
        completed.write_bytes(completed.read_bytes()+b"tamper")
        with self.assertRaises(D16BoundaryError):
            self.replay()

    def test_receipt_immutable_and_absolute_clock_bounded(self):
        self.write(1)
        with self.assertRaises(FileExistsError):
            immutable_receipt(
                self.root,source_sha=SOURCE,seed=0,ordinal=1,job=1,
                clock=GlobalClock(START),now_unix_ms=START+1100,
                local_elapsed_ms=1100,
            )
        with self.assertRaises(D16BoundaryError):
            immutable_receipt(
                self.root,source_sha=SOURCE,seed=0,ordinal=1,job=1,
                clock=GlobalClock(START),now_unix_ms=START+1800001,
                local_elapsed_ms=1000,
            )

    def test_wrong_source_and_expired_second_job_cannot_replay(self):
        self.write(1)
        with self.assertRaises(D16BoundaryError):
            replay_completed_prefix(
                self.root,source_sha="a"*40,seed=0,
                original_genesis=self.genesis,study_started_unix_ms=START,
            )
        with self.assertRaises(D16BoundaryError):
            replay_completed_prefix(
                self.root,source_sha=SOURCE,seed=0,
                original_genesis=self.genesis,
                study_started_unix_ms=START-1000,
            )


if __name__ == "__main__":
    unittest.main()
