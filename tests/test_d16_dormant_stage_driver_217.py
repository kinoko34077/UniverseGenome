"""D16.8 dormant stage driver: synthetic metadata only, no original physical steps."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.d16_complete_round_checkpoint_217 import (
    KIND, read_completed, write_completed_atomic,
)
from research.d16_dormant_stage_driver_217 import (
    advance_one_verified_complete_round,
)
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, make_transfer, hash_of,
)
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

SOURCE="a"*40
START=1780000000000


class DormantNativeSelectedStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="d16-stage-driver-")
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.genesis=SteadyStateOptimizer.from_defaults(base_seed=0).to_snapshot()
        self.now=START+1000
        self.local=1000
        self.evaluations=[]

    def evaluator(self, ordinal, predecessor, _clock):
        self.evaluations.append(ordinal)
        opt=SteadyStateOptimizer.from_snapshot(predecessor or self.genesis)
        opt.generation=ordinal  # synthetic metadata, NO D15 selected evolution
        snap=opt.to_snapshot()
        names=sorted({s.category for s in opt.slots})
        observer={
            "source_commit":SOURCE,"base_seed":0,
            "before_optimizer_generation":ordinal-1,
            "selected_optimizer_generation":ordinal,
            "selected_post_v7_sha256":digest(snap),
            "evaluated_native_worlds":128,"selected_native_worlds":128,
            "d15_journal_chain_verified":True,
            "original_selected_once_proven_by_D15_final":True,
            "actual_native_replacement_count":0,
            "categories":{
                name:{"complete_nonfailure_count":0,
                      "native_replacement_count":0} for name in names
            },
        }
        return {
            "kind":KIND,"source_sha":SOURCE,"seed":0,"ordinal":ordinal,
            "selected_snapshot":snap,"selected_v7_sha256":digest(snap),
            "d15_verified_observer":observer,
            "global_wall_ms":self.now-START-100,"learning_claim":False,
        }

    def run(self,job=1,manifest=None,evaluator=None):
        return advance_one_verified_complete_round(
            folder=self.folder,source_sha=SOURCE,seed=0,
            original_genesis=self.genesis,study_started_unix_ms=START,
            job=job,now_unix_ms=lambda:self.now,
            local_elapsed_ms=lambda:self.local,
            native_completed_evaluator=evaluator or self.evaluator,
            source_bound_inbound_manifest=manifest,
        )

    def transfer(self):
        complete=read_completed(
            self.folder/"selected-round-01.json",
            source_sha=SOURCE,seed=0,ordinal=1,
        )
        return make_transfer(
            source_sha=SOURCE,selected_snapshot=complete["selected_snapshot"],
            seed=0,selected_round=1,clock=GlobalClock(START),
            now_unix_ms=START+1200,local_elapsed_ms=1200,
            observer_selected_digest=complete["selected_v7_sha256"],
            ledger_sha=hash_of(complete["d15_verified_observer"]),
        )

    def test_true_shape_two_stage_only_1_plus_1_fixture(self):
        first=self.run()
        self.assertEqual(first.stage.result,"HANDOFF_READY")
        self.assertTrue(first.selected_file.exists())
        self.assertTrue(first.receipt_file.exists())
        self.now=START+3000
        self.local=1000
        second=self.run(job=2,manifest=self.transfer())
        self.assertEqual(second.stage.result,"FIXTURE_COMPLETE_NO_SCIENCE")
        self.assertEqual(second.stage.selected_round,2)
        self.assertEqual(self.evaluations,[1,2])
        with self.assertRaises(D16BoundaryError):
            self.run(job=2,manifest=self.transfer())
        self.assertEqual(self.evaluations,[1,2])

    def test_executor_failure_before_selected_commit_allows_same_stage_retry(self):
        def crash(_n,_p,_c):
            raise RuntimeError("simulated interrupted native D15 source")
        with self.assertRaises(RuntimeError):
            self.run(evaluator=crash)
        self.assertFalse((self.folder/"selected-round-01.json").exists())
        recovered=self.run()
        self.assertEqual(recovered.stage.result,"HANDOFF_READY")
        self.assertEqual(self.evaluations,[1])

    def test_crash_between_completed_selection_and_receipt_fails_closed(self):
        with patch("research.d16_dormant_stage_driver_217.immutable_receipt",
                   side_effect=RuntimeError("interrupted after full selected")):
            with self.assertRaises(RuntimeError):
                self.run()
        self.assertTrue((self.folder/"selected-round-01.json").exists())
        self.assertFalse((self.folder/"selected-receipt-01.json").exists())
        with self.assertRaises(D16BoundaryError):
            self.run()
        self.assertEqual(self.evaluations,[1])  # no double original re-evaluation

    def test_second_job_manifest_is_mandatory_and_bound_to_actual_ledger(self):
        self.run()
        self.now=START+3000
        self.local=1000
        with self.assertRaises(D16BoundaryError):
            self.run(job=2)
        bad={**self.transfer(),"observer_ledger_sha256":"f"*64}
        with self.assertRaises(D16BoundaryError):
            self.run(job=2,manifest=bad)
        self.assertEqual(self.evaluations,[1])

    def test_first_job_rejects_injected_stage2_manifest(self):
        with self.assertRaises(D16BoundaryError):
            self.run(job=1,manifest={"ignored":"untrusted"})
        self.assertEqual(self.evaluations,[])


if __name__=="__main__":
    unittest.main()
