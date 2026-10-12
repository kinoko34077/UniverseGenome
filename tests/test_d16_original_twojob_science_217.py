"""D16.11 original-science launch source guard: NO physical seed16384 steps."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.d16_original_twojob_science_217 import (
    ORIGINAL_SEED, STAGE1_END, MAX_ROUNDS, REPORT_SCHEMA,
    execute, check_inbound_rows, original_observation, isolated_handoff_folder,
)
from research.d16_twojob_run_control_217 import D16BoundaryError


class OriginalScienceProgramSourceGuards(unittest.TestCase):
    def test_reserved_study_contract_is_fixed_not_fixture(self):
        self.assertEqual(ORIGINAL_SEED,16384)
        self.assertEqual(STAGE1_END,20)
        self.assertEqual(MAX_ROUNDS,40)
        self.assertIn("ORIGINAL",REPORT_SCHEMA)

    def test_no_third_job_before_physics_or_host_action(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(D16BoundaryError):
                execute(job=3, out=Path(temp))
            with self.assertRaises(D16BoundaryError):
                execute(job=True, out=Path(temp))

    def test_job1_refuses_prior_and_job2_refuses_absent_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(D16BoundaryError):
                execute(job=1, out=Path(temp), inbound=Path(temp))
            with self.assertRaises(D16BoundaryError):
                execute(job=2, out=Path(temp), inbound=None)

    def test_first_host_partial_report_never_becomes_native_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(D16BoundaryError):
                check_inbound_rows(Path(temp), source="a"*40, report={
                    "schema":REPORT_SCHEMA, "seed":ORIGINAL_SEED,
                    "source_sha":"a"*40,"status":"HANDOFF_READY",
                    "rounds":[],  # no genuine original20 selected receipts
                })

    def test_source_entry_sha_failclosed_before_evaluation(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("research.d16_original_twojob_science_217.source_sha",
                       side_effect=D16BoundaryError("no pinned checkout")):
                with self.assertRaisesRegex(D16BoundaryError,"no pinned checkout"):
                    execute(job=1, out=Path(temp))

    def test_complete_host2_evidence_is_copied_without_mutating_inbound(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            inbound, out = parent/"inbound", parent/"out"
            inbound.mkdir()
            (inbound/"stage1-manifest.json").write_text('{"source_sha":"a"}')
            (inbound/"partial-report.json").write_text('{"rounds":[]}')
            (inbound/"selected-round-20.json").write_bytes(b"native-checkpoint")
            (inbound/"selected-receipt-20.json").write_bytes(b"immutable-receipt")
            before={p.name:p.read_bytes() for p in inbound.iterdir()}
            self.assertEqual(isolated_handoff_folder(inbound,out),out)
            (out/"selected-round-21.json").write_bytes(b"native-second-job")
            self.assertEqual({p.name:p.read_bytes() for p in inbound.iterdir()},before)
            self.assertTrue((out/"selected-round-20.json").is_file())
            self.assertTrue((out/"selected-receipt-20.json").is_file())
            self.assertTrue((out/"selected-round-21.json").is_file())
            self.assertFalse((inbound/"selected-round-21.json").exists())

    def test_host2_never_accepts_overlapping_evidence_or_nested_untracked_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            inbound=Path(temp)/"inbound"
            inbound.mkdir()
            (inbound/"stage1-manifest.json").write_text("{}")
            with self.assertRaises(D16BoundaryError):
                isolated_handoff_folder(inbound,inbound)
            (inbound/"nested").mkdir()
            with self.assertRaises(D16BoundaryError):
                isolated_handoff_folder(inbound,Path(temp)/"out")

    def test_scientific_observation_keeps_native_retirement_separate_from_learning(self):
        item={
            "ordinal":37,"source_sha":"a"*40,"seed":ORIGINAL_SEED,
            "selected_v7_sha256":"b"*64,
            "d15_journal_bytes":30,"rss_sampled_bytes":100,
            "global_wall_ms":420000,
            "d15_verified_observer":{
                "evaluated_native_worlds":128,
                "original_selected_once_proven_by_D15_final":True,
                "actual_native_replacement_count":1,
                "native_retirements":[{"category":"A","index":0}],
                "categories":{"A":{"complete_nonfailure_count":1,
                                   "native_replacement_count":1}},
                "before_diversity":{"A":{"distinct":8}},
                "after_diversity":{"A":{"distinct":7}},
            },
        }
        r=original_observation(item)
        self.assertEqual(r["original_actual_native_replacements"],1)
        self.assertEqual(r["before_diversity"]["A"]["distinct"],8)
        self.assertNotIn("learning_claim",r)


if __name__=="__main__":
    unittest.main()
