"""PERF230 test-only report validation; no default128 native execution in unit CI."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from benchmarks.perf230_default128 import compare_reports, _write_json


class Perf230ReportContract(unittest.TestCase):
    @staticmethod
    def _fixtures(root: Path) -> None:
        for workers in (1, 2, 4):
            _write_json(
                root / f"perf230-default128-{workers}.json",
                {
                    "study_status": "COMPLETE",
                    "source_sha": "a" * 40,
                    "final_digest": "b" * 64,
                    "evaluated_worlds": 128,
                    "native_selection_performed": True,
                    "actual_wall_seconds": float(100 // workers),
                    "config": {
                        "workers": workers,
                        "seed": 0,
                        "worlds": 128,
                        "batch": 16,
                        "memory_mib": 1536,
                        "experiment": {"original": "default"},
                        "physics": {"original": "default"},
                    },
                },
            )

    def test_valid_equal_full_selected_snapshots(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixtures(root)
            result = compare_reports(root, root / "comparison.json")
            self.assertEqual(result["identical_full_v7_digest"], "b" * 64)
            self.assertEqual(result["actual_wall_by_workers"], {
                1: 100.0, 2: 50.0, 4: 25.0
            })
            self.assertFalse(result["D16_seed16384_outcomes"])

    def test_reject_digest_drift(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixtures(root)
            target = root / "perf230-default128-4.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["final_digest"] = "c" * 64
            _write_json(target, record)
            with self.assertRaisesRegex(AssertionError, "final_digest"):
                compare_reports(root, root / "comparison.json")

    def test_reject_incomplete_run(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixtures(root)
            target = root / "perf230-default128-2.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["study_status"] = "INCOMPLETE"
            _write_json(target, record)
            with self.assertRaisesRegex(AssertionError, "did not finish"):
                compare_reports(root, root / "comparison.json")

    def test_reject_source_or_configuration_drift(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixtures(root)
            target = root / "perf230-default128-4.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["config"]["seed"] = 16384
            _write_json(target, record)
            with self.assertRaisesRegex(AssertionError, "condition diverges"):
                compare_reports(root, root / "comparison.json")


if __name__ == "__main__":
    unittest.main()
