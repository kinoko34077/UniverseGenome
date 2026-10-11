"""D16 native journal observer on previously exposed seed0 short fixture only."""
from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d15_sparse_recovery_213 import JournalIntegrityError, SparseEvaluationJournal
from research.d16_native_journal_observer_217 import observe_committed_round
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer


class OriginalSourceD15ObserverTests(unittest.TestCase):
    def test_authentic_completed_journal_readonly_and_tamper_failclosed(self):
        source = "a" * 40
        protocol = ExperimentConfig(evaluation_timeout_generations=2)
        physics = PhysicsConfig()
        with tempfile.TemporaryDirectory(prefix="d16-readonly-seed0-") as temp:
            root = Path(temp) / "original_selected128"
            result = execute_selected_round(
                root,
                source_commit=source,
                base_seed=0,
                experiment=protocol,
                base_config=physics,
                evaluation_batch_size=16,
                memory_mib=1536,
                workers=1,
            )
            self.assertTrue(result["final_committed"])
            self.assertEqual(result["new_evaluations"], 128)
            self.assertEqual(
                result["final_digest"],
                "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321",
            )
            original_bytes = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
            report = observe_committed_round(root, source_commit=source)
            self.assertEqual(report["evaluated_native_worlds"], 128)
            self.assertEqual(report["selected_native_worlds"], 128)
            self.assertEqual(report["before_optimizer_generation"], 0)
            self.assertEqual(report["selected_optimizer_generation"], 1)
            self.assertEqual(report["selected_post_v7_sha256"], result["final_digest"])
            self.assertEqual(len(report["categories"]), 4)
            self.assertTrue(all(
                data["native_replacement_count"] <= 1
                for data in report["categories"].values()
            ))
            self.assertFalse(report["learning_claim"])
            self.assertTrue(report["read_only"])
            self.assertEqual(
                original_bytes,
                {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()},
            )
            with self.assertRaises(JournalIntegrityError):
                observe_committed_round(root, source_commit="b" * 40)
            batch = root / "batch-00000.json"
            batch.write_bytes(batch.read_bytes() + b"tampered")
            with self.assertRaises(JournalIntegrityError):
                observe_committed_round(root, source_commit=source)

    def test_incomplete_native_journal_never_reports_selected_evidence(self):
        source = "a" * 40
        with tempfile.TemporaryDirectory(prefix="d16-incomplete-") as temp:
            root = Path(temp) / "original_incomplete"
            native = SteadyStateOptimizer.from_defaults(
                base_seed=0, experiment=ExperimentConfig(evaluation_timeout_generations=2),
                base_config=PhysicsConfig(),
            )
            SparseEvaluationJournal.create(
                root, base_snapshot=native.to_snapshot(), source_commit=source,
            )
            with self.assertRaises(JournalIntegrityError):
                observe_committed_round(root, source_commit=source)

    def test_requires_complete_exact_source_sha(self):
        with self.assertRaises(ValueError):
            observe_committed_round(Path("/unused"), source_commit="short")


if __name__ == "__main__":
    unittest.main()
