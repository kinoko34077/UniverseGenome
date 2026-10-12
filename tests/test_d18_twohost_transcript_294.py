"""D18 data-only two-host immutable transcript fixtures; NEVER evaluates seed49152."""
from dataclasses import replace
import unittest

from research.d18_twohost_transcript_294 import (
    OriginalD18Transcript,SEED,FIRST_STAGE_END,
)

SOURCE="a"*40


def row(n,*,e1=0,e2=0,elapsed=None):
    return {
        "schema":"D18_NEW_SEED_NATIVE_JOURNAL_ADMISSION_V1",
        "source_sha":SOURCE,"seed":SEED,"ordinal":n,
        "job":1 if n<=20 else 2,
        "selected_post_v7_sha256":f"{n:064x}",
        "global_elapsed_ms":elapsed if elapsed is not None else n*20000,
        "journal_bytes":100000,
        "E1_count":e1,"E2_count":e2,
        "read_only":True,"learning_claim":False,
    }


def complete_stage1():
    state=OriginalD18Transcript.begin(SOURCE)
    for n in range(1,21):
        state=state.append(row(n))
    assert state.result=="HANDOFF_READY"
    return state


class D18TwoHostTranscriptTests(unittest.TestCase):
    def test_genuine_shape_exact_stage1_handoff_and_resume(self):
        state=complete_stage1()
        self.assertEqual(len(state.rows),20)
        manifest=state.stage1_manifest()
        self.assertEqual(manifest["selected_round"],FIRST_STAGE_END)
        self.assertEqual(manifest["seed"],SEED)
        with self.assertRaises(ValueError):
            state.append(row(21))
        second=state.accept_second_host(manifest,copied_rows=state.rows,
                                         current_global_elapsed_ms=400001)
        self.assertEqual(second.job,2)
        self.assertEqual(second.stage1_digest,manifest["manifest_sha256"])
        self.assertEqual(second.append(row(21)).selected_round,21)

    def test_real_e1_sooner_than_last_round_is_retained(self):
        state=complete_stage1()
        inbound=state.stage1_manifest()
        state=state.accept_second_host(inbound,copied_rows=state.rows,
                                       current_global_elapsed_ms=401000)
        for n in range(21,41):
            state=state.append(row(n,e1=1 if n==38 else 0))
        report=state.verdict()
        self.assertEqual(report["status"],"E2_NOT_OBSERVED_FINAL")
        self.assertTrue(report["E1_ever_observed"])
        self.assertFalse(report["E2_ever_observed"])
        self.assertEqual(report["E1_first_round"],38)
        self.assertIsNone(report["E2_first_round"])
        self.assertFalse(report["admission_rows_are_from_original_journal"])
        with self.assertRaises(ValueError):
            state.append(row(41))

    def test_actual_terminal_e2_requires_mature_round(self):
        state=complete_stage1()
        state=state.accept_second_host(state.stage1_manifest(),
                                       copied_rows=state.rows,
                                       current_global_elapsed_ms=400100)
        for n in range(21,38):
            state=state.append(row(n,e1=1 if n==37 else 0,
                                   e2=1 if n==37 else 0))
        report=state.verdict()
        self.assertEqual(report["status"],"OBSERVED_E2_FINAL")
        self.assertEqual(report["rounds"],37)
        self.assertEqual(report["E2_first_round"],37)

    def test_growth_e1_may_cover_up_to_native128_not_four_retirements(self):
        state=complete_stage1()
        state=state.accept_second_host(state.stage1_manifest(),
                                       copied_rows=state.rows,
                                       current_global_elapsed_ms=400100)
        for n in range(21,41):
            state=state.append(row(n,e1=128 if n==38 else 0))
        report=state.verdict()
        self.assertEqual(report["status"],"E2_NOT_OBSERVED_FINAL")
        self.assertTrue(report["E1_ever_observed"])
        self.assertEqual(report["E1_first_round"],38)
        with self.assertRaises(ValueError):
            OriginalD18Transcript.begin(SOURCE).append(row(1,e1=129))

    def test_historical_real_e2_before37_still_terminal_at37(self):
        state=complete_stage1()
        state=state.accept_second_host(state.stage1_manifest(),
                                       copied_rows=state.rows,
                                       current_global_elapsed_ms=400100)
        for n in range(21,38):
            state=state.append(row(n,e1=int(n==26),e2=int(n==26)))
        report=state.verdict()
        self.assertEqual(report["status"],"OBSERVED_E2_FINAL")
        self.assertEqual(report["rounds"],37)
        self.assertEqual(report["E2_first_round"],26)
        with self.assertRaises(ValueError):
            state.append(row(38))

    def test_tampered_handoff_wrong_copy_and_clock_fail(self):
        state=complete_stage1()
        manifest=state.stage1_manifest()
        fake={**manifest,"selected_v7_sha256":"b"*64}
        with self.assertRaises(ValueError):
            state.accept_second_host(fake,copied_rows=state.rows,
                                     current_global_elapsed_ms=400100)
        with self.assertRaises(ValueError):
            state.accept_second_host(manifest,copied_rows=state.rows[:-1],
                                     current_global_elapsed_ms=400100)
        with self.assertRaises(ValueError):
            state.accept_second_host(manifest,copied_rows=state.rows,
                                     current_global_elapsed_ms=399999)
        with self.assertRaises(ValueError):
            state.accept_second_host(manifest,copied_rows=state.rows,
                                     current_global_elapsed_ms=1800001)

    def test_failclosed_wrong_seed_source_job_ordinal_and_clock(self):
        state=OriginalD18Transcript.begin(SOURCE)
        bad=[]
        for change in (
            {"source_sha":"b"*40},{"seed":16384},{"job":2},{"ordinal":2},
            {"global_elapsed_ms":1800001},{"journal_bytes":134217729},
            {"learning_claim":True},{"E1_count":0,"E2_count":1},
            {"selected_post_v7_sha256":"incorrect"},
        ):
            bad.append({**row(1),**change})
        for candidate in bad:
            with self.subTest(candidate=candidate),self.assertRaises(ValueError):
                state.append(candidate)
        state=state.append(row(1))
        with self.assertRaises(ValueError):
            state.append(row(2,elapsed=19999))

    def test_incomplete_and_misused_stage_never_terminal(self):
        state=OriginalD18Transcript.begin(SOURCE)
        with self.assertRaises(ValueError):
            state.verdict()
        for n in range(1,20):
            state=state.append(row(n))
        with self.assertRaises(ValueError):
            state.stage1_manifest()
        with self.assertRaises(ValueError):
            state.append(row(20,e2=5))
        state=state.append(row(20))
        with self.assertRaises(ValueError):
            state.verdict()
        with self.assertRaises(ValueError):
            state.append(row(21))


if __name__=="__main__":
    unittest.main()
