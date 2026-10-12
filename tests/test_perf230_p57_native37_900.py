"""PERF230 P5.7 immutable two-job original selected128 performance fixture guards."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from benchmarks.perf230_p57_postpacked_native37_900 import (
    SEED, SPLIT, FINAL_ROUND, execute, main,
)
from research.d16_twojob_run_control_217 import D16BoundaryError


class P57RealSeed0NativeSourceBoundary(unittest.TestCase):
    def test_exact_benchmark_not_reserved_science(self):
        self.assertEqual(SEED,0)
        self.assertEqual(SPLIT,20)
        self.assertEqual(FINAL_ROUND,37)

    def test_stage2_without_complete_20_round_ledger_rejected_before_any_native_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(FileNotFoundError):
                execute(stage=2,out=root/"out",incoming=root/"missing")
            self.assertFalse((root/"out").exists())

    def test_stage1_cannot_override_seed_or_receive_prior_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(D16BoundaryError):
                execute(stage=1,out=root/"out",incoming=root/"not-allowed")
            self.assertFalse((root/"out").exists())
        with patch("sys.argv",["perf_fixture","--stage","1","--out","unused",
                                "--seed","16384"]):
            with self.assertRaises(SystemExit) as raised:
                main()
        self.assertEqual(raised.exception.code,2)


if __name__=="__main__":
    unittest.main()
