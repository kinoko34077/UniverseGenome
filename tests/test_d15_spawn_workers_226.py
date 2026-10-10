"""#226 P1 opt-in Linux spawn vs original D15 serial journal RED/GREEN safety.

Retains source-bound seed0/timeout2 original 128 authoritative slots. No D16
16384/37-step study, no learning/generalization or default backend switch.
"""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
import unittest

from core.experiment import ExperimentConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d15_sparse_recovery_213 import (
    JournalIntegrityError, SparseEvaluationJournal,
)
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

SOURCE = "perf226-spawn-worker-source-bound"
GOLDEN = "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321"


def _protocol():
    return ExperimentConfig(evaluation_timeout_generations=2)


@unittest.skipUnless(sys.platform == "linux", "D15 Linux POSIX source-only workers")
class NativeSpawnD15Tests(unittest.TestCase):
    def _execute(self, root, *, workers=1, **kwargs):
        return execute_selected_round(
            Path(root), source_commit=SOURCE, base_seed=0,
            experiment=_protocol(), evaluation_batch_size=16,
            memory_mib=1536, workers=workers, **kwargs,
        )

    def test_workers2_and_workers4_match_complete_original_selected128(self):
        opt = SteadyStateOptimizer.from_defaults(base_seed=0, experiment=_protocol())
        original_step = opt.step()
        original = opt.to_snapshot()
        self.assertEqual(digest(original), GOLDEN)
        for workers in (2, 4):
            with self.subTest(workers=workers), TemporaryDirectory() as d:
                path = Path(d) / "journal"
                result = self._execute(path, workers=workers)
                self.assertEqual(result["final_digest"], GOLDEN)
                self.assertEqual(result["final_snapshot"], original)
                self.assertEqual(result["selected_step"]["replacements"], original_step["replacements"])
                self.assertEqual(result["checkpoint_writes"], 8)
                replay = self._execute(path, workers=workers)
                self.assertEqual(replay["new_evaluations"], 0)
                self.assertFalse(replay["finalization_performed"])

    def test_actual_parent_exit_after_two_patches_resume_only_96(self):
        with TemporaryDirectory() as d:
            root = Path(d) / "journal"
            children_at_crash = Path(d) / "spawn-child-pids.txt"
            program = (
                "import os\nfrom pathlib import Path\n"
                "from core.experiment import ExperimentConfig\n"
                "from research.d15_selected_resume_213 import execute_selected_round\n"
                f"child_file = Path({str(children_at_crash)!r})\n"
                "def kill_after_two_patches(index):\n"
                "    if index == 32:\n"
                "        child_file.write_text("
                "Path(f'/proc/self/task/{os.getpid()}/children').read_text())\n"
                "        os._exit(86)\n"
                f"execute_selected_round(Path({str(root)!r}),"
                f"source_commit={SOURCE!r},base_seed=0,"
                "experiment=ExperimentConfig(evaluation_timeout_generations=2),"
                "evaluation_batch_size=16,memory_mib=1536,workers=2,"
                "on_checkpoint=kill_after_two_patches)\n"
            )
            failed = subprocess.run([sys.executable,"-c",program],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE,
                                    text=True,timeout=120)
            self.assertEqual(failed.returncode, 86, failed.stderr)
            # At the crash point the parent still had two worker children
            # (and possibly Python's resource_tracker). They must not remain
            # RUNNING after the parent's abrupt death. Zombies count as dead.
            listed = [int(pid) for pid in children_at_crash.read_text().split()]
            self.assertGreaterEqual(len(listed), 2)
            deadline = time.monotonic() + 8
            while True:
                running = []
                for pid in listed:
                    stat = Path(f"/proc/{pid}/stat")
                    try:
                        state = stat.read_text().rsplit(")", 1)[1].split()[0]
                    except FileNotFoundError:
                        continue
                    if state not in ("Z", "X", "x"):
                        running.append((pid, state))
                if not running or time.monotonic() >= deadline:
                    break
                time.sleep(0.05)
            self.assertFalse(running, f"orphaned D15 child processes after parent exit: {running}")
            # Neither the parent nor spawned children can retain D15 writer
            # flock after the parent dies.
            lock = root.with_name(root.name+".writer.lock")
            with lock.open("a+b") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            view = SparseEvaluationJournal.open(root,source_commit=SOURCE).recover()
            self.assertEqual(view.next_index,32)
            result = self._execute(root,workers=4)
            self.assertEqual(result["resumed_from"],32)
            self.assertEqual(result["new_evaluations"],96)
            self.assertEqual(result["final_digest"],GOLDEN)
            with self.assertRaises(JournalIntegrityError):
                self._execute(root,workers=2,base_snapshot={
                    "untrusted":True,
                })

    def test_two_real_native_selected_generations_and_no_duplicate_finalization(self):
        serial = SteadyStateOptimizer.from_defaults(base_seed=0,experiment=_protocol())
        serial.step()
        first = serial.to_snapshot()
        serial.step()
        second = serial.to_snapshot()
        with TemporaryDirectory() as d:
            round0 = self._execute(Path(d)/"round0",workers=2)
            round1 = self._execute(Path(d)/"round1",workers=4,
                                   base_snapshot=round0["final_snapshot"])
            self.assertEqual(round0["final_snapshot"], first)
            self.assertEqual(round1["final_snapshot"], second)
            self.assertEqual(round1["final_snapshot"]["generation"],2)
            replay = self._execute(Path(d)/"round1",workers=2,
                                   base_snapshot=round0["final_snapshot"])
            self.assertFalse(replay["finalization_performed"])
            self.assertEqual(replay["final_snapshot"],second)

    def test_worker_sigkill_aborts_without_committing_any_journal_patch(self):
        from research.d15_spawn_workers_226 import SpawnEvaluator
        from research.d15_sparse_recovery_213 import ResourceBudget
        opt = SteadyStateOptimizer.from_defaults(base_seed=0,experiment=_protocol())
        with TemporaryDirectory() as d:
            lock = Path(d)/"no-journal.writer.lock"
            with SpawnEvaluator(opt.to_snapshot(),workers=2,
                                budget=ResourceBudget(1536),lock_path=lock) as pool:
                pool.processes[0].kill()
                pool.processes[0].join(timeout=3)
                with self.assertRaises((OSError,JournalIntegrityError)):
                    pool.evaluate((0,1))
            self.assertFalse(lock.exists())
            self.assertFalse((Path(d)/"journal").exists())

    def test_crash_before_and_after_atomic_final_preserves_original_single_selection(self):
        for stage,exit_code,expect_final in (
            ("before_final_commit",87,False),("after_final_commit",88,True),
        ):
            with self.subTest(stage=stage),TemporaryDirectory() as d:
                root=Path(d)/"journal"
                program=(
                    "import os\nfrom pathlib import Path\n"
                    "from core.experiment import ExperimentConfig\n"
                    "from research.d15_selected_resume_213 import execute_selected_round\n"
                    f"execute_selected_round(Path({str(root)!r}),"
                    f"source_commit={SOURCE!r},base_seed=0,"
                    "experiment=ExperimentConfig(evaluation_timeout_generations=2),"
                    "evaluation_batch_size=16,memory_mib=1536,workers=2,"
                    f"on_stage=lambda st: os._exit({exit_code}) if st=={stage!r} else None)\n"
                )
                crashed=subprocess.run([sys.executable,"-c",program],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.PIPE,
                                       text=True,timeout=120)
                self.assertEqual(crashed.returncode,exit_code,crashed.stderr)
                view=SparseEvaluationJournal.open(root,source_commit=SOURCE).recover()
                self.assertEqual(view.next_index,128)
                self.assertEqual(view.final_committed,expect_final)
                recovered=self._execute(root,workers=4)
                self.assertEqual(recovered["new_evaluations"],0)
                self.assertEqual(recovered["finalization_performed"],not expect_final)
                self.assertEqual(recovered["final_digest"],GOLDEN)
                self.assertFalse(self._execute(root,workers=2)["finalization_performed"])

    def test_optin_from_short_lived_thread_fails_before_journal_exists(self):
        from threading import Thread
        with TemporaryDirectory() as d:
            target = Path(d) / "journal"
            failures = []

            def attempt():
                try:
                    self._execute(target, workers=2)
                except BaseException as exc:
                    failures.append(exc)

            thread = Thread(target=attempt)
            thread.start()
            thread.join(timeout=8)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(failures), 1)
            self.assertIsInstance(failures[0], ValueError)
            self.assertIn("main thread", str(failures[0]))
            self.assertFalse(target.exists())

    def test_optin_args_reject_wrong_worker_count_before_filesystem(self):
        with TemporaryDirectory() as d:
            for workers in (0,3,5,False,2.0):
                with self.subTest(workers=workers),self.assertRaises(ValueError):
                    self._execute(Path(d)/"invalid",workers=workers)
            self.assertFalse((Path(d)/"invalid").exists())


if __name__ == "__main__":
    unittest.main()
