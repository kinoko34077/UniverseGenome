"""D18.1 native E1/E2 observer tests: ORIGINAL exposed seed0, short fixture only."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d15_sparse_recovery_213 import JournalIntegrityError, SparseEvaluationJournal
from research.d18_native_journal_observer_294 import observe_completed_native_round
from search.evolution import SteadyStateOptimizer


class D18ActualSourceOnlyObserverTests(unittest.TestCase):
    def test_real_complete_short_selected128_journal_no_mutation_and_tamper(self):
        source = "a" * 40  # synthetic provenance marker, NEVER new science source
        with tempfile.TemporaryDirectory(prefix="d18-short-exposed-seed0-") as tmp:
            path = Path(tmp) / "journal"
            report = execute_selected_round(
                path,
                source_commit=source, base_seed=0,
                experiment=ExperimentConfig(evaluation_timeout_generations=2),
                base_config=PhysicsConfig(),
                evaluation_batch_size=16, memory_mib=1536, workers=1,
            )
            self.assertEqual(report["new_evaluations"], 128)
            self.assertEqual(report["checkpoint_writes"], 8)
            original_files = {
                p.name: p.read_bytes() for p in path.iterdir() if p.is_file()
            }
            d18 = observe_completed_native_round(path, source_commit=source)
            self.assertEqual(d18["schema"],
                             "D18_ORIGINAL_D15_ACTUAL_SELECTED_E1_E2_OBSERVER_V1")
            self.assertEqual(d18["source_commit"], source)
            self.assertEqual(d18["seed"], 0)
            self.assertEqual(d18["original_selected_round"], 1)
            self.assertEqual(d18["original_native_evaluated_worlds"], 128)
            self.assertEqual(d18["selected_post_v7_sha256"], report["final_digest"])
            self.assertEqual(len(d18["categories"]), 4)
            self.assertTrue(d18["read_only"])
            self.assertFalse(d18["learning_claim"])
            self.assertEqual(d18["E1_growth_only_candidate_count"], 0)
            self.assertEqual(d18["E2_actual_growth_pruned_count"], 0)
            self.assertEqual(
                original_files,
                {p.name: p.read_bytes() for p in path.iterdir() if p.is_file()},
            )
            with self.assertRaises(JournalIntegrityError):
                observe_completed_native_round(path, source_commit="b" * 40)
            bad_patch = path / "batch-00000.json"
            bad_patch.write_bytes(bad_patch.read_bytes() + b"tamper")
            with self.assertRaises(JournalIntegrityError):
                observe_completed_native_round(path, source_commit=source)

    def test_incomplete_short_existing_journal_refused(self):
        source = "a" * 40
        with tempfile.TemporaryDirectory(prefix="d18-incomplete-") as tmp:
            path = Path(tmp) / "journal"
            native = SteadyStateOptimizer.from_defaults(
                base_seed=0,
                experiment=ExperimentConfig(evaluation_timeout_generations=2),
                base_config=PhysicsConfig(),
            )
            SparseEvaluationJournal.create(
                path, base_snapshot=native.to_snapshot(), source_commit=source,
            )
            with self.assertRaises(JournalIntegrityError):
                observe_completed_native_round(path, source_commit=source)

    def test_invalid_source_commit_is_refused_before_read(self):
        with self.assertRaises(ValueError):
            observe_completed_native_round(Path("/none"), source_commit="invalid")


if __name__ == "__main__":
    unittest.main()
