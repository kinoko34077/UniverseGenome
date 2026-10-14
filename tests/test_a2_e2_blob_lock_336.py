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
        self.assertEqual(result["locked_file_count"],136)
        self.assertFalse(result["scientific_experiment_executed"])

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
        self.assertEqual(GUARD.BASELINE,"d8e863f6b3e213163455c2ad0ebaa691371aa4a2")


if __name__=="__main__":
    unittest.main()
