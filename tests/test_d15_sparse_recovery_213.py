"""D15 #213 — deterministic sparse journal, integrity and bounded RSS admission."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research.d15_sparse_recovery_213 import (
    ResourceBudget, CheckpointPolicy, SparseEvaluationJournal, JournalIntegrityError,
)


def fixture():
    return {
        "format_version": 7, "generation": 4,
        "slots": [{"index": i, "generation": 4, "state": {"generation": 56, "latent": i}}
                  for i in range(8)],
        "scheduler": {"evaluation_count": 512, "replacement_count": 0},
    }


class RecoveryTests(unittest.TestCase):
    def test_user_ram_budget_rejects_oversubscription_before_allocation(self):
        self.assertEqual(ResourceBudget(memory_mib=1536).limit_bytes,1536*1024*1024)
        self.assertEqual(ResourceBudget(memory_mib=2048).limit_bytes,2048*1024*1024)
        for value in (-1,0,False,2.5,2049):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ResourceBudget(memory_mib=value)
        b=ResourceBudget(memory_mib=1024)
        b.admit(estimated_additional_bytes=32*1024*1024,current_rss_bytes=128*1024*1024,
                available_host_bytes=512*1024*1024)
        with self.assertRaises(MemoryError):
            b.admit(estimated_additional_bytes=950*1024*1024,
                    current_rss_bytes=128*1024*1024,available_host_bytes=2048*1024*1024)
        with self.assertRaises(MemoryError):
            b.admit(estimated_additional_bytes=500*1024*1024,
                    current_rss_bytes=128*1024*1024,available_host_bytes=200*1024*1024)

    def test_adaptive_checkpoint_by_worlds_or_elapsed_seconds(self):
        policy=CheckpointPolicy(max_worlds_between_saves=16,
                                max_seconds_between_saves=120)
        self.assertFalse(policy.should_commit(pending_worlds=0,seconds_since_save=999))
        self.assertFalse(policy.should_commit(pending_worlds=1,seconds_since_save=10))
        self.assertTrue(policy.should_commit(pending_worlds=16,seconds_since_save=1))
        self.assertTrue(policy.should_commit(pending_worlds=1,seconds_since_save=121))
        for opts in (
            {"max_worlds_between_saves":0},
            {"max_worlds_between_saves":33},
            {"max_seconds_between_saves":0},
        ):
            with self.assertRaises(ValueError):
                CheckpointPolicy(**opts)

    def test_mid_round_crash_replays_only_unfinished_worlds(self):
        start=fixture()
        with TemporaryDirectory() as directory:
            root=Path(directory)
            j=SparseEvaluationJournal.create(root,base_snapshot=start,
                                               source_commit="baseline-sha",max_bytes=8*1024*1024)
            part=[{"index":i,"generation":5,"state":{"generation":70,"latent":i+1}} for i in range(3)]
            j.commit(part)
            restored=SparseEvaluationJournal.open(root,source_commit="baseline-sha")
            view=restored.recover()
            self.assertEqual(view.next_index,3)
            self.assertFalse(view.evaluation_complete)
            self.assertEqual(view.snapshot["slots"][2],part[2])
            self.assertEqual(view.snapshot["slots"][3],start["slots"][3])
            self.assertEqual(view.snapshot["scheduler"],start["scheduler"])
            rest=[{"index":i,"generation":5,"state":{"generation":70,"latent":i+1}}
                  for i in range(3,8)]
            restored.commit(rest)
            complete=SparseEvaluationJournal.open(root,source_commit="baseline-sha")
            v=complete.recover()
            self.assertEqual(v.next_index,8)
            self.assertTrue(v.evaluation_complete)
            final=copy.deepcopy(v.snapshot)
            final["generation"]=5
            final["scheduler"]["evaluation_count"]=520
            complete.commit_final(final)
            end=SparseEvaluationJournal.open(root,source_commit="baseline-sha").recover()
            self.assertEqual(end.final_snapshot,final)
            self.assertTrue(end.final_committed)
            self.assertEqual(end.next_index,8)

    def test_rejects_out_of_order_or_duplicate_patch_without_side_effect(self):
        with TemporaryDirectory() as directory:
            j=SparseEvaluationJournal.create(Path(directory),base_snapshot=fixture(),
                                               source_commit="abc")
            bad=[{"index":2,"state":{"generation":5}}]
            with self.assertRaises(ValueError):
                j.commit(bad)
            j.commit([{"index":0,"state":{"generation":5}}])
            with self.assertRaises(ValueError):
                j.commit([{"index":0,"state":{"generation":5}}])
            self.assertEqual(j.recover().next_index,1)
            with self.assertRaises(ValueError):
                j.commit_final(fixture())

    def test_real_native_four_world_training_checkpoint_and_resume_identity(self):
        # This exercises real slot-local physics and exact v7 snapshot restore.
        # It is not yet a native selected mid-round restart implementation.
        from core.experiment import ExperimentConfig
        from search.evolution import SteadyStateOptimizer
        from research.d8_genome_diversity_190 import digest

        opt=SteadyStateOptimizer.from_defaults(
            base_seed=0,experiment=ExperimentConfig(evaluation_timeout_generations=2))
        with TemporaryDirectory() as directory:
            j=SparseEvaluationJournal.create(
                Path(directory),base_snapshot=opt.to_snapshot(),
                source_commit="accepted-d13-native-128")
            for i in range(0,4,2):
                updated=[]
                for slot in opt.slots[i:i+2]:
                    opt._evaluate_slot(slot)
                    updated.append(slot.to_dict())
                j.commit(updated)
            reconstructed=SparseEvaluationJournal.open(
                Path(directory),source_commit="accepted-d13-native-128").recover()
            self.assertEqual(reconstructed.next_index,4)
            self.assertFalse(reconstructed.evaluation_complete)
            self.assertEqual(digest(reconstructed.snapshot),digest(opt.to_snapshot()))
            restored=SteadyStateOptimizer.from_snapshot(reconstructed.snapshot)
            self.assertEqual(digest(restored.to_snapshot()),digest(opt.to_snapshot()))
            # Recover and continue from the *first unfinished* physical world.
            opt._evaluate_slot(opt.slots[4])
            restored._evaluate_slot(restored.slots[4])
            self.assertEqual(digest(restored.to_snapshot()),digest(opt.to_snapshot()))

    def test_foreign_source_or_modified_base_is_rejected(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            SparseEvaluationJournal.create(root,base_snapshot=fixture(),source_commit="same")
            with self.assertRaises(JournalIntegrityError):
                SparseEvaluationJournal.open(root,source_commit="different")
            base=root/"base.json"
            base.write_bytes(base.read_bytes()+b" ")
            with self.assertRaises(JournalIntegrityError):
                SparseEvaluationJournal.open(root,source_commit="same")

    def test_corrupted_last_chunk_fails_closed_or_explicit_read_only_salvage(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            j=SparseEvaluationJournal.create(root,base_snapshot=fixture(),source_commit="same")
            j.commit([{"index":0,"state":{"generation":5}}])
            j.commit([{"index":1,"state":{"generation":5}}])
            files=sorted(root.glob("batch-*.json"))
            files[-1].write_bytes(b"broken")
            with self.assertRaises(JournalIntegrityError):
                SparseEvaluationJournal.open(root,source_commit="same")
            safe=SparseEvaluationJournal.open(root,source_commit="same",salvage_last=True)
            v=safe.recover()
            self.assertEqual(v.next_index,1)
            self.assertTrue(v.read_only)
            with self.assertRaises(JournalIntegrityError):
                safe.commit([{"index":1,"state":{"generation":5}}])

    def test_orphan_uncommitted_temp_is_ignored_and_no_full_copy_per_patch(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            j=SparseEvaluationJournal.create(root,base_snapshot=fixture(),source_commit="same")
            j.commit([{"index":0,"state":{"generation":5}}])
            (root/"batch-00002.json.tmp").write_bytes(b"partial power loss")
            again=SparseEvaluationJournal.open(root,source_commit="same")
            self.assertEqual(again.recover().next_index,1)
            self.assertEqual(len(list(root.glob("batch-*.json"))),1)
            payload=json.loads(next(root.glob("batch-*.json")).read_text())
            self.assertNotIn("base_snapshot",payload)
            self.assertEqual(len(payload["slots"]),1)
            self.assertLess(sum(p.stat().st_size for p in root.iterdir()),8*1024*1024)


if __name__=="__main__":
    unittest.main()
