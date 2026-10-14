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
        self.assertGreaterEqual(result["locked_file_count"],125)
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

    def test_lock_names_exact_science_and_failed_run_dependencies(self):
        self.assertIn("research/a2_e2_failure_manifest_336.py",GUARD.REQUIRED)
        self.assertIn("research/a2_e2_exposed_activation_336.py",GUARD.REQUIRED)
        self.assertIn("research/a2_locked_rotate_copy_pilot_336.py",GUARD.REQUIRED)
        self.assertEqual(GUARD.BASELINE,"131739a7e8d004c9f9153e80aa4bccb49ce242c6")


if __name__=="__main__":
    unittest.main()
