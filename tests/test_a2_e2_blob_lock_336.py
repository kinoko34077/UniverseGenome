"""#336 review/source integrity: static Git tree only, no native physics."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(".github/scripts/a2_e2_source_identity_336.py")
SPEC=importlib.util.spec_from_file_location("e2_source_guard",SCRIPT)
GUARD=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class SourceBlobLockTests(unittest.TestCase):
    def test_pr_effective_tree_is_frozen(self):
        result=GUARD.verify_locked_tree("HEAD")
        self.assertEqual(result["status"],"SOURCE_BLOB_LOCK_MATCH")
        self.assertEqual(result["locked_file_count"],141)  # 140 previously reviewed + 1 O2-3 research-only eligibility blob
        self.assertFalse(result["scientific_experiment_executed"])

    def test_outer_research_added_blobs_are_also_strictly_reviewed(self):
        lock=__import__("json").loads(GUARD.LOCK.read_text(encoding="utf-8"))
        new={
            "research/outer_l3_memory_search_386.py":
                "75d265f353c632814c0b50832c8ee6c0dd794c9a",
            "research/outer_l3_search_protocol_386.json":
                "abd28cd928d57c9d5028fc3a43481a3b694eae36",
        }
        new["research/outer_l3_inner_adapter_388.py"] = (
            "86a2cdd41435573cfa394ccce2d631fd0dfb50d7"
        )
        new["research/outer_l3_native_evidence_388.py"] = (
            "281e7b52894de0a8a82a61c41efc49821e994f82"
        )
        new["research/outer_l3_eligible_selection_388.py"] = (
            "41bc5da2c70b4caa6f6b9c1964d88d2089ddaa94"
        )
        for path,sha in new.items():
            self.assertEqual(lock["blobs"][path],sha)
        actual=GUARD.tracked_source_blobs("HEAD")
        self.assertEqual(set(actual),set(lock["blobs"]))
        for path,sha in new.items():
            altered=dict(actual)
            altered[path]="0"*40
            with self.assertRaisesRegex(ValueError,"unreviewed scientific source divergence"):
                GUARD.compare_locked_sources(lock["blobs"],altered)

    def test_effectful_entry_still_requires_verified_full_ancestry(self):
        import inspect
        gate=inspect.getsource(GUARD.verify_source_lock)
        self.assertIn("verify_locked_tree(ref)",gate)
        self.assertIn('"merge-base", "--is-ancestor"',gate)

    def test_changed_deleted_added_and_malformed_sources_fail(self):
        fixed={key:"a"*40 for key in GUARD.REQUIRED}
        GUARD.compare_locked_sources(fixed,dict(fixed))
        changes=[
            {k:v for k,v in fixed.items() if k!="core/physics.py"},
            {**fixed,"core/physics.py":"b"*40},
            {**fixed,"research/undocumented.py":"a"*40},
        ]
        for observed in changes:
            with self.subTest(observed=observed):
                with self.assertRaises(ValueError):
                    GUARD.compare_locked_sources(fixed,observed)
        with self.assertRaises(ValueError):
            GUARD.compare_locked_sources({**fixed,"core/physics.py":"NOT_A_SHA"},fixed)

    def test_action_and_attester_are_both_hash_bound(self):
        import json
        frozen=json.loads(GUARD.LOCK.read_text(encoding="utf-8"))
        self.assertEqual(frozen["source_actions"],list(GUARD.ACTION_FILES))
        for path in GUARD.ACTION_FILES:
            self.assertIn(path,GUARD.REQUIRED)
            self.assertIn(path,frozen["blobs"])
        corrupted=dict(frozen["blobs"])
        corrupted[GUARD.ACTION_FILES[0]]="0"*40
        with self.assertRaises(ValueError):
            GUARD.compare_locked_sources(corrupted,GUARD.tracked_source_blobs("HEAD"))

    def test_scorer_drift_rejected_before_exposed_marker(self):
        import json
        lock = json.loads(GUARD.LOCK.read_text(encoding="utf-8"))
        name = "research/a2_e2_outcome_scoring_336.py"
        self.assertIn(name, lock["blobs"])
        expected = dict(lock["blobs"])
        unexpected = dict(expected)
        unexpected[name] = "0" * 40
        with self.assertRaisesRegex(ValueError, "unreviewed scientific source divergence"):
            GUARD.compare_locked_sources(expected, unexpected)

    def test_lock_names_exact_science_and_failed_run_dependencies(self):
        self.assertIn("research/a2_e2_failure_manifest_336.py",GUARD.REQUIRED)
        self.assertIn("research/a2_e2_outcome_scoring_336.py",GUARD.REQUIRED)
        self.assertIn("research/a2_e2_exposed_activation_336.py",GUARD.REQUIRED)
        self.assertIn("research/a2_locked_rotate_copy_pilot_336.py",GUARD.REQUIRED)
        self.assertEqual(GUARD.BASELINE,"3ffc3900c599be86af83565730553088d6f09580")


if __name__=="__main__":
    unittest.main()
