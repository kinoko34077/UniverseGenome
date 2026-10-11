"""D16.9 dormant 2-job incremental stage tests: synthetic metadata only."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.d16_complete_round_checkpoint_217 import KIND
from research.d16_incremental_stage_217 import run_dormant_stage
from research.d16_twojob_run_control_217 import D16BoundaryError
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

SRC="f"*40
START=1780000000000


class IncrementalTwoJobStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="d16-incremental-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.seed=0
        self.genesis=SteadyStateOptimizer.from_defaults(base_seed=0).to_snapshot()
        self.now=START
        self.local=0
        self.evaluated=[]

    def executor(self,ordinal,previous,_clock):
        self.evaluated.append(ordinal)
        self.now+=1000
        self.local+=1000
        optimizer=SteadyStateOptimizer.from_snapshot(previous)
        optimizer.generation=ordinal  # metadata ONLY, no original native physics
        snapshot=optimizer.to_snapshot()
        names=sorted(set(s.category for s in optimizer.slots))
        return {
            "kind":KIND,"source_sha":SRC,"seed":self.seed,
            "ordinal":ordinal,"selected_snapshot":snapshot,
            "selected_v7_sha256":digest(snapshot),
            "global_wall_ms":self.now-START-1,"learning_claim":False,
            "d15_verified_observer":{
                "source_commit":SRC,"base_seed":self.seed,
                "before_optimizer_generation":ordinal-1,
                "selected_optimizer_generation":ordinal,
                "selected_post_v7_sha256":digest(snapshot),
                "evaluated_native_worlds":128,"selected_native_worlds":128,
                "d15_journal_chain_verified":True,
                "original_selected_once_proven_by_D15_final":True,
                "actual_native_replacement_count":0,
                "categories":{c:{"complete_nonfailure_count":0,
                                 "native_replacement_count":0}
                              for c in names},
            },
        }

    def run_job(self,job,manifest=None,max_new=None,executor=None):
        return run_dormant_stage(
            root=self.root,source_sha=SRC,seed=self.seed,
            original_genesis=self.genesis,study_started_unix_ms=START,
            job=job,now_unix_ms=lambda:self.now,
            local_elapsed_ms=lambda:self.local,
            native_completed_evaluator=executor or self.executor,
            source_bound_inbound_manifest=manifest,
            max_new_rounds=max_new,
        )

    def test_seed0_two_hosted_stage_shape_and_no_science_outcome(self):
        one=self.run_job(1)
        self.assertEqual(one["stage_result"],"HANDOFF_READY")
        self.assertEqual(one["new_complete_selections"],1)
        path=self.root/"original-job1-selected-transfer.json"
        self.assertTrue(path.exists())
        self.now+=1000
        self.local=0
        two=self.run_job(2,manifest=json.loads(path.read_bytes()))
        self.assertEqual(two["stage_result"],"FIXTURE_COMPLETE_NO_SCIENCE")
        self.assertEqual(two["last_completed_round"],2)
        self.assertEqual(self.evaluated,[1,2])
        self.assertFalse(two["original_science_outcome_claimed"])
        self.assertTrue((self.root/"terminal-verdict.json").exists())
        with self.assertRaises(D16BoundaryError):
            self.run_job(2,manifest=json.loads(path.read_bytes()))
        self.assertEqual(self.evaluated,[1,2])

    def test_same_host_restart_only_replays_complete_original_prefix(self):
        self.seed=16384
        self.genesis=SteadyStateOptimizer.from_defaults(base_seed=16384).to_snapshot()
        a=self.run_job(1,max_new=1)
        self.assertEqual(a["last_completed_round"],1)
        self.assertEqual(a["stage_result"],"IN_PROGRESS")
        b=self.run_job(1,max_new=1)
        self.assertEqual(b["last_completed_round"],2)
        self.assertEqual(self.evaluated,[1,2])
        self.assertFalse((self.root/"original-job1-selected-transfer.json").exists())

    def test_orphan_selected_without_receipt_never_auto_replays_or_reexecutes(self):
        with patch("research.d16_incremental_stage_217.immutable_receipt",
                   side_effect=RuntimeError("crash after full selected commit")):
            with self.assertRaises(RuntimeError):
                self.run_job(1)
        self.assertTrue((self.root/"selected-round-01.json").exists())
        self.assertFalse((self.root/"selected-receipt-01.json").exists())
        with self.assertRaises(D16BoundaryError):
            self.run_job(1)
        self.assertEqual(self.evaluated,[1])

    def test_missing_or_corrupted_second_host_manifest_rejected(self):
        self.run_job(1)
        self.now+=1000
        self.local=0
        with self.assertRaises(D16BoundaryError):
            self.run_job(2)
        manifest=json.loads((self.root/"original-job1-selected-transfer.json").read_bytes())
        with self.assertRaises(D16BoundaryError):
            self.run_job(2,manifest={**manifest,"observer_ledger_sha256":"0"*64})
        self.assertEqual(self.evaluated,[1])

    def test_native_evaluator_error_has_no_fabricated_completed_progress(self):
        def broken(_n,_p,_c):
            raise RuntimeError("native evaluator interrupted")
        with self.assertRaises(RuntimeError):
            self.run_job(1,executor=broken)
        self.assertEqual(list(self.root.glob("selected-round-*.json")),[])
        self.assertEqual(self.run_job(1)["last_completed_round"],1)
        self.assertEqual(self.evaluated,[1])


if __name__=="__main__":
    unittest.main()
