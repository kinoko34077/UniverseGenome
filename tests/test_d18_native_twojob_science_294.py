"""D18 dormant original two-host runner safety tests (NO native seed49152 stepping)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import tempfile
import unittest
from unittest.mock import patch

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d16_twojob_run_control_217 import D16BoundaryError
from research.d18_native_journal_observer_294 import observe_completed_native_round
from research.d18_native_twojob_science_294 import (
    REPORT_KIND, SEARCH_SEED, MAX_ROUNDS,
    durable_json, load_json, total_bytes,
    validate_saved, authenticate_stage1, run_stage,
    archive_source_d15, extract_source_d15, D15_FILES,
)


class DormantD18RunnerTests(unittest.TestCase):
    def test_exact_source_original_role_does_not_launch_on_import(self):
        self.assertEqual(SEARCH_SEED, 49152)
        self.assertEqual(MAX_ROUNDS, 40)
        self.assertIn("E1_E2", REPORT_KIND)

    def test_durable_immutable_json_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"round.json"
            data={"ordinal":1,"learning_claim":False}
            durable_json(path,data)
            raw=path.read_bytes()
            self.assertEqual(load_json(path),data)
            self.assertEqual(total_bytes(Path(tmp)),len(raw))
            self.assertEqual(hashlib.sha256(raw).hexdigest(),
                             hashlib.sha256(path.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                durable_json(path,{"ordinal":2})
            self.assertEqual(path.read_bytes(),raw)
            self.assertFalse(any(x.suffix==".tmp" for x in Path(tmp).iterdir()))

    def test_incomplete_missing_round_never_authenticates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(D16BoundaryError):
                validate_saved(root,source="a"*40,ordinal=1,previous_sha="b"*64)
            with self.assertRaises(D16BoundaryError):
                authenticate_stage1(root,source="a"*40,current_global_elapsed_ms=50000)

    def test_invalid_host_or_stage_never_calls_native_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            # These fail before repo SHA probing or any physical evaluator.
            with patch("research.d18_native_twojob_science_294.single_original_round") as runner:
                for job,inbound in ((0,None),(3,None),(1,root),(2,None)):
                    with self.subTest(job=job,inbound=inbound):
                        with self.assertRaises(D16BoundaryError):
                            run_stage(job=job,out=root/"out",inbound=inbound)
                runner.assert_not_called()

    def test_genuine_source_bound_short_seed0_D15_journal_is_archived_replayable(self):
        # EXPOSED seed0 short two-generation test, never new actual seed49152.
        source = "a" * 40
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            journal = folder / "real-exposed-seed0-d15"
            report = execute_selected_round(
                journal, source_commit=source, base_seed=0,
                experiment=ExperimentConfig(evaluation_timeout_generations=2),
                base_config=PhysicsConfig(), workers=1,
                evaluation_batch_size=16,
            )
            self.assertEqual(report["new_evaluations"], 128)
            self.assertEqual(report["checkpoint_writes"], 8)
            before = observe_completed_native_round(journal, source_commit=source)
            archive = folder / "original-d15-round-01.zip"
            archive_sha, raw_size = archive_source_d15(journal, archive)
            self.assertEqual(len(archive_sha), 64)
            self.assertEqual(raw_size, sum((journal / name).stat().st_size
                                           for name in D15_FILES))
            with ZipFile(archive) as zf:
                self.assertEqual(tuple(zf.namelist()), D15_FILES)
            extracted = folder / "extracted"
            self.assertEqual(extract_source_d15(archive, extracted), raw_size)
            self.assertEqual(
                observe_completed_native_round(extracted, source_commit=source), before
            )
            with self.assertRaises(FileExistsError):
                archive_source_d15(journal, archive)
            self.assertEqual(
                observe_completed_native_round(extracted, source_commit=source), before
            )
            # Mutation after the zip means new artifact bytes are rejected.
            with archive.open("r+b") as file:
                file.seek(-25, 2)
                file.write(b"\0" * 8)
            with self.assertRaises(D16BoundaryError):
                extract_source_d15(archive, folder / "corrupt")

    def test_journal_archive_strict_flat_whitelist_no_zip_slip(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            root = folder / "fake"
            root.mkdir()
            for name in D15_FILES:
                (root / name).write_bytes(b"not-authentic-science")
            archive = folder / "fake.zip"
            digest_sha, raw_bytes = archive_source_d15(root, archive)
            self.assertEqual(len(digest_sha), 64)
            self.assertGreater(raw_bytes, 0)
            good = folder / "good"
            self.assertEqual(extract_source_d15(archive, good), raw_bytes)
            self.assertEqual((good / "final.json").read_bytes(),
                             b"not-authentic-science")
            missing = root / "final.json"
            missing.unlink()
            with self.assertRaises(D16BoundaryError):
                archive_source_d15(root, folder / "missing.zip")
            bad_zip = folder / "malicious.zip"
            with ZipFile(bad_zip, "w", compression=ZIP_DEFLATED) as zf:
                zf.writestr("../bad", "injection")
            with self.assertRaises(D16BoundaryError):
                extract_source_d15(bad_zip, folder / "escape")
            self.assertFalse((folder / "bad").exists())

    def test_invalid_or_unsafe_artifact_path_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            target=root/"actual.json"
            durable_json(target,{"source_sha":"a"*40})
            alias=root/"alias.json"
            alias.symlink_to(target)
            with self.assertRaises(D16BoundaryError):
                load_json(alias)
            self.assertEqual(load_json(target)["source_sha"],"a"*40)


if __name__ == "__main__":
    unittest.main()
