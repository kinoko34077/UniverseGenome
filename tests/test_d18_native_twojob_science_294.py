"""D18 dormant original two-host runner safety tests (NO native seed49152 stepping)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.d16_twojob_run_control_217 import D16BoundaryError
from research.d18_native_twojob_science_294 import (
    REPORT_KIND, SEARCH_SEED, MAX_ROUNDS,
    durable_json, load_json, total_bytes,
    validate_saved, authenticate_stage1, run_stage,
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
