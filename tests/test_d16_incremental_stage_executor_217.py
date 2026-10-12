"""D16.9 dormant incremental FSM composition: synthetic metadata, seed0 ONLY."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.d16_complete_round_checkpoint_217 import KIND
from research.d16_complete_prefix_recovery_217 import replay_completed_prefix
from research.d16_incremental_stage_executor_217 import DormantIncrementalStage
from research.d16_twojob_run_control_217 import D16BoundaryError
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

SOURCE = "b" * 40
START = 1780000000000


class IncrementalNativeStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="d16-incremental-")
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.genesis = SteadyStateOptimizer.from_defaults(base_seed=0).to_snapshot()
        self.now = START + 1000
        self.local = 1000
        self.calls = []

    def native_fixture(self, ordinal, previous, _clock):
        self.calls.append(ordinal)
        opt = SteadyStateOptimizer.from_snapshot(previous)
        opt.generation = ordinal  # metadata-only; never evolve physical seed16384
        snapshot = opt.to_snapshot()
        names = sorted({s.category for s in opt.slots})
        observer = {
            "source_commit": SOURCE, "base_seed": 0,
            "before_optimizer_generation": ordinal - 1,
            "selected_optimizer_generation": ordinal,
            "selected_post_v7_sha256": digest(snapshot),
            "evaluated_native_worlds": 128,
            "selected_native_worlds": 128,
            "d15_journal_chain_verified": True,
            "original_selected_once_proven_by_D15_final": True,
            "actual_native_replacement_count": 0,
            "categories": {
                name: {"complete_nonfailure_count": 0,
                       "native_replacement_count": 0} for name in names
            },
        }
        return {
            "kind": KIND, "source_sha": SOURCE, "seed": 0,
            "ordinal": ordinal, "selected_snapshot": snapshot,
            "selected_v7_sha256": digest(snapshot),
            "d15_verified_observer": observer,
            "global_wall_ms": self.now - START - 100,
            "learning_claim": False,
        }

    def open(self, *, job=1, manifest=None, evaluator=None):
        return DormantIncrementalStage.open(
            folder=self.folder, source_sha=SOURCE, seed=0, job=job,
            original_genesis=self.genesis, study_started_unix_ms=START,
            now_unix_ms=lambda: self.now,
            local_elapsed_ms=lambda: self.local,
            native_completed_evaluator=evaluator or self.native_fixture,
            source_bound_inbound_manifest=manifest,
        )

    def test_original_fixture_two_hosted_stages_and_one_replay_each(self):
        with patch("research.d16_dormant_stage_driver_217.replay_completed_prefix",
                   wraps=replay_completed_prefix) as replay:
            first = self.open()
            self.assertEqual(first.reopened_completed_count, 0)
            self.assertEqual(first.run_to_stage_end().result, "HANDOFF_READY")
            manifest = first.verified_handoff()
            self.assertEqual(replay.call_count, 1)
            self.now = START + 3000
            self.local = 1000  # different hosted job monotonic clock
            second = self.open(job=2, manifest=manifest)
            self.assertEqual(second.reopened_completed_count, 1)
            self.assertEqual(second.run_to_stage_end().result,
                             "FIXTURE_COMPLETE_NO_SCIENCE")
            self.assertEqual(replay.call_count, 2)  # not per selected round
            self.assertEqual(self.calls, [1, 2])
            with self.assertRaises(D16BoundaryError):
                second.advance()
        self.assertEqual(self.calls, [1, 2])

    def test_stage2_requires_exact_authenticated_original_handoff(self):
        with self.assertRaises(D16BoundaryError):
            self.open(job=2)
        first = self.open()
        first.advance()
        self.now = START + 3000
        wrong = {**first.verified_handoff(), "observer_ledger_sha256": "f" * 64}
        with self.assertRaises(D16BoundaryError):
            self.open(job=2, manifest=wrong)
        self.assertEqual(self.calls, [1])

    def test_crash_before_selected_commit_does_not_publish(self):
        def fail(_ordinal, _previous, _clock):
            raise RuntimeError("injected native failure")
        first = self.open(evaluator=fail)
        with self.assertRaisesRegex(RuntimeError, "native failure"):
            first.advance()
        self.assertEqual(list(self.folder.glob("selected-*")), [])
        recovered = self.open()
        self.assertEqual(recovered.advance().stage.result, "HANDOFF_READY")
        self.assertEqual(self.calls, [1])

    def test_orphan_after_selected_before_receipt_blocks_replay(self):
        first = self.open()
        with patch("research.d16_incremental_stage_executor_217.immutable_receipt",
                   side_effect=RuntimeError("process died")):
            with self.assertRaisesRegex(RuntimeError, "process died"):
                first.advance()
        self.assertTrue((self.folder / "selected-round-01.json").exists())
        self.assertFalse((self.folder / "selected-receipt-01.json").exists())
        with self.assertRaises(D16BoundaryError):
            self.open()
        self.assertEqual(self.calls, [1])

    def test_retained_limit_fails_before_native_execution(self):
        first = self.open()
        with patch("research.d16_incremental_stage_executor_217.MAX_RETAINED_STUDY_BYTES",
                   100):
            with self.assertRaises(D16BoundaryError):
                first.advance()
        self.assertEqual(self.calls, [])

    def test_clock_overrun_fails_before_native_execution(self):
        first = self.open()
        self.local = 1080001
        with self.assertRaises(D16BoundaryError):
            first.advance()
        self.assertEqual(self.calls, [])

    def test_mutated_selection_is_not_accepted(self):
        first = self.open()
        def tamper(ordinal, previous, clock):
            d = self.native_fixture(ordinal, previous, clock)
            d["selected_v7_sha256"] = "f" * 64
            return d
        first.native_completed_evaluator = tamper
        with self.assertRaises(D16BoundaryError):
            first.advance()
        self.assertEqual(list(self.folder.glob("selected-*")), [])


if __name__ == "__main__":
    unittest.main()
