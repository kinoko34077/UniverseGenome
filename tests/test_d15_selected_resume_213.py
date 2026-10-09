"""#213 D15.5: predeclared genuine native selected128 hard interruption contract.

The fixed SHA comes from PRE-D14 native selected 128 worlds, not from these tests.
No independence/learning/heldout result is asserted.
"""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from core.experiment import ExperimentConfig
from research.d8_genome_diversity_190 import digest
from research.d15_sparse_recovery_213 import JournalIntegrityError, SparseEvaluationJournal
from search.evolution import SteadyStateOptimizer
from research.d15_selected_resume_213 import execute_selected_round

GOLDEN = "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321"
SOURCE = "frozen-integrated-D15.5-test-source"


def experiment():
    return ExperimentConfig(evaluation_timeout_generations=2)


class Selected128InterruptedRecoveryTests(unittest.TestCase):
    def _execute(self, root, **kwargs):
        return execute_selected_round(
            Path(root), base_seed=0, experiment=experiment(),
            source_commit=SOURCE, memory_mib=1536, evaluation_batch_size=16,
            **kwargs,
        )

    def _crash_process(self, root, *, where):
        hook = (
            "on_checkpoint=lambda n: os._exit(86) if n == 32 else None"
            if where == "after32" else
            ("on_stage=lambda stage: os._exit(87) if stage == 'before_final_commit' else None"
             if where == "before_final" else
             "on_stage=lambda stage: os._exit(88) if stage == 'after_final_commit' else None")
        )
        program = (
            "import os\n"
            "from pathlib import Path\n"
            "from core.experiment import ExperimentConfig\n"
            "from research.d15_selected_resume_213 import execute_selected_round\n"
            f"execute_selected_round(Path({str(root)!r}), base_seed=0, "
            "experiment=ExperimentConfig(evaluation_timeout_generations=2), "
            f"source_commit={SOURCE!r}, memory_mib=1536, evaluation_batch_size=16, {hook})\n"
        )
        process = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True, timeout=180)
        return process

    def test_full_authentic_selected_one_step_matches_frozen_pre_d14_golden(self):
        legacy = SteadyStateOptimizer.from_defaults(base_seed=0, experiment=experiment())
        original_step = legacy.step()
        original_snapshot = legacy.to_snapshot()
        self.assertEqual(digest(original_snapshot), GOLDEN)
        with TemporaryDirectory() as temp:
            result = self._execute(Path(temp) / "journal")
            self.assertEqual(result["final_digest"], GOLDEN)
            self.assertEqual(result["final_snapshot"], original_snapshot)
            self.assertEqual(result["new_evaluations"], 128)
            self.assertTrue(result["finalization_performed"])
            self.assertTrue(result["final_committed"])
            self.assertEqual(result["final_snapshot"]["scheduler"], original_snapshot["scheduler"])
            self.assertEqual(result["final_snapshot"]["prune_history"], original_snapshot["prune_history"])
            self.assertEqual(result["selected_step"]["replacements"], original_step["replacements"])
            self.assertEqual(result["selected_step"]["evaluated_slots"], 128)

    def test_actual_process_crash_after_two_real_16_world_patches_resumes_only_96(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "journal"
            failure = self._crash_process(root, where="after32")
            self.assertEqual(failure.returncode, 86, failure.stderr)
            view = SparseEvaluationJournal.open(root, source_commit=SOURCE).recover()
            self.assertEqual(view.next_index, 32)
            self.assertFalse(view.final_committed)
            resumed = self._execute(root)
            self.assertEqual(resumed["resumed_from"], 32)
            self.assertEqual(resumed["new_evaluations"], 96)
            self.assertTrue(resumed["finalization_performed"])
            self.assertEqual(resumed["final_digest"], GOLDEN)
            # A second fresh call MUST NOT re-evaluate or re-select.
            again = self._execute(root)
            self.assertEqual(again["new_evaluations"], 0)
            self.assertFalse(again["finalization_performed"])
            self.assertEqual(again["final_snapshot"], resumed["final_snapshot"])

    def test_crash_after_all_evaluated_precommit_and_after_atomic_final(self):
        for where,code in (("before_final",87),("after_final",88)):
            with self.subTest(where=where), TemporaryDirectory() as temp:
                root = Path(temp) / "journal"
                failure = self._crash_process(root, where=where)
                self.assertEqual(failure.returncode, code, failure.stderr)
                view = SparseEvaluationJournal.open(root, source_commit=SOURCE).recover()
                self.assertEqual(view.next_index, 128)
                self.assertEqual(view.final_committed, where == "after_final")
                recovered = self._execute(root)
                self.assertEqual(recovered["new_evaluations"], 0)
                self.assertEqual(recovered["finalization_performed"], where == "before_final")
                self.assertEqual(recovered["final_digest"], GOLDEN)
                self.assertEqual(self._execute(root)["final_digest"], GOLDEN)
                self.assertFalse(self._execute(root)["finalization_performed"])

    def test_incomplete_corrupt_source_and_protocol_resume_fail_closed(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)/"journal"
            failure=self._crash_process(root,where="after32")
            self.assertEqual(failure.returncode,86,failure.stderr)
            with self.assertRaises((JournalIntegrityError,ValueError)):
                execute_selected_round(root, base_seed=0, experiment=experiment(),
                                       source_commit="foreign-code-SHA", memory_mib=1536,
                                       evaluation_batch_size=16)
            with self.assertRaises((JournalIntegrityError,ValueError)):
                execute_selected_round(root, base_seed=1, experiment=experiment(),
                                       source_commit=SOURCE, memory_mib=1536,
                                       evaluation_batch_size=16)
            with self.assertRaises((JournalIntegrityError,ValueError)):
                execute_selected_round(root, base_seed=0,
                                       experiment=ExperimentConfig(evaluation_timeout_generations=3),
                                       source_commit=SOURCE, memory_mib=1536,
                                       evaluation_batch_size=16)
            last=sorted(root.glob("batch-*.json"))[-1]
            last.write_bytes(last.read_bytes()+b"CORRUPTION")
            with self.assertRaises(JournalIntegrityError):
                self._execute(root)


    def test_consecutive_authentic_selected_generations_from_durable_completed_round(self):
        legacy=SteadyStateOptimizer.from_defaults(base_seed=0,experiment=experiment())
        legacy.step()
        expected_first=legacy.to_snapshot()
        self.assertEqual(digest(expected_first),GOLDEN)
        legacy.step()
        expected_second=legacy.to_snapshot()
        with TemporaryDirectory() as temp:
            first=self._execute(Path(temp)/"round0")
            self.assertEqual(first["final_snapshot"],expected_first)
            second=self._execute(Path(temp)/"round1",
                                 base_snapshot=first["final_snapshot"])
            self.assertEqual(second["final_snapshot"],expected_second)
            self.assertEqual(second["final_snapshot"]["scheduler"],expected_second["scheduler"])
            self.assertEqual(second["final_snapshot"]["prune_history"],expected_second["prune_history"])
            self.assertEqual(second["final_snapshot"]["generation"],2)
            again=self._execute(Path(temp)/"round1",
                                base_snapshot=first["final_snapshot"])
            self.assertEqual(again["final_snapshot"],expected_second)
            self.assertFalse(again["finalization_performed"])
            with self.assertRaises((JournalIntegrityError,ValueError)):
                self._execute(Path(temp)/"round1",
                              base_snapshot=expected_second)

    def test_real_selected_rss_journal_write_count_and_single_writer_admission(self):
        import fcntl
        with TemporaryDirectory() as temp:
            root=Path(temp)/"journal"
            lock_path=root.with_name(root.name+".writer.lock")
            with lock_path.open("a+b") as stream:
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                program=(
                    "from pathlib import Path\n"
                    "from core.experiment import ExperimentConfig\n"
                    "from research.d15_selected_resume_213 import execute_selected_round\n"
                    f"execute_selected_round(Path({str(root)!r}),source_commit={SOURCE!r},"
                    "base_seed=0,experiment=ExperimentConfig(evaluation_timeout_generations=2))\n"
                )
                other=subprocess.run([sys.executable,"-c",program],
                                     capture_output=True,text=True,timeout=30)
                self.assertNotEqual(other.returncode,0)
                self.assertIn("active writer",other.stderr)
                self.assertFalse((root/"manifest.json").exists())
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
            complete=self._execute(root)
            self.assertEqual(complete["final_digest"],GOLDEN)
            self.assertGreater(complete["journal_bytes"],0)
            self.assertGreater(complete["peak_rss_bytes"],0)
            self.assertLess(complete["peak_rss_bytes"],1536*1024*1024)
            self.assertEqual(complete["checkpoint_writes"],8)
            initial_full_bytes=(root/"base.json").stat().st_size
            comparison_initial_full_every_checkpoint=initial_full_bytes*9
            self.assertLess(complete["journal_bytes"],comparison_initial_full_every_checkpoint)


if __name__=="__main__":
    unittest.main()
