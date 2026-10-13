"""Synthetic-only P7.3 orchestration contract tests.

These tests never launch CPython/PyPy children and never evaluate a native
world. Authentic complete37 evidence is produced only by the manual workflow.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from benchmarks import perf275_p73_two_host_complete37 as p73


def _fake_row(runtime: str, ordinal: int, previous: Path | None = None) -> tuple[Path, dict]:
    digest = f"v7-{ordinal:02d}"
    report = {
        "runtime_identity": {
            "implementation": "cpython" if runtime == "cpython" else "pypy",
            "python_version": [3, 12] if runtime == "cpython" else [3, 11],
            "executable": f"/fake/{runtime}",
            "version": "fixture",
        },
        "source_sha": p73.SOURCE,
        "seed": p73.SEED,
        "ordinal": ordinal,
        "selected_v7": digest,
        "observer_hash": f"observer-{ordinal:02d}",
        "journal_payload_sha256": {
            "base.json": f"base-{ordinal:02d}",
            **{f"batch-{i:05d}.json": f"batch-{ordinal:02d}-{i}" for i in range(8)},
            "final.json": f"final-{ordinal:02d}",
        },
        "journal_bytes": 1024,
        "default1024": True,
        "sampled_rss_bytes": 100 * 1024 * 1024,
        "retained_scratch_bytes": 4096,
        "native_wall_s": 20.0 if runtime == "cpython" else 10.0,
        "selected_snapshot": {"ordinal": ordinal},
    }
    path = Path(f"/fake/{runtime}-{ordinal:02d}.json")
    return path, report


class P73HarnessContractTests(unittest.TestCase):
    def test_manual_workflow_is_visible_and_not_automatic(self):
        workflow = Path(__file__).parents[1] / ".github/workflows/perf275-p73-two-host-complete37.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("\n  push:", text)
        self.assertNotIn("\n  pull_request:", text)
        self.assertIn(p73.SOURCE, text)
        self.assertIn("default: '0'", text)
        self.assertIn("host1_cpython", text)
        self.assertIn("host2_pypy", text)
        self.assertIn("16f9f56e82d1f4ec95a324c1a8cacfd78afc7f0656c0a809a18725ef4391453a", text)
        self.assertIn("1080s", text)
        self.assertIn("workflow_dispatch", text)

    def test_host_executes_exactly_37_source_bound_rounds(self):
        calls = []

        def fake_step(runtime, scratch, ordinal, prior, *, exe, deadline):
            self.assertGreater(deadline, 0)
            calls.append((runtime, ordinal, prior))
            return _fake_row(runtime, ordinal, prior)

        with TemporaryDirectory() as td:
            out = Path(td) / "host.json"
            with patch.object(p73, "git_source", return_value=p73.SOURCE), \
                 patch.object(p73, "preflight_runtime", return_value={
                     "implementation": "cpython", "python_version": [3, 12],
                     "executable": "/fake/cpython", "version": "fixture",
                 }), \
                 patch.object(p73, "native_step", side_effect=fake_step):
                report = p73.execute_host("cpython", "/fake/cpython", out)

        self.assertEqual(report["status"], "HOST_COMPLETE37")
        self.assertEqual(report["rounds_completed"], 37)
        self.assertEqual(len(report["rounds"]), 37)
        self.assertEqual([row[1] for row in calls], list(range(1, 38)))
        self.assertIsNone(calls[0][2])
        self.assertEqual(report["source_sha"], p73.SOURCE)
        self.assertEqual(report["seed"], 0)
        self.assertFalse(report["original_seed16384_executed"])
        self.assertFalse(report["original_seed49152_executed"])

    def test_host_source_mismatch_fails_before_native_round(self):
        with TemporaryDirectory() as td, patch.object(p73, "git_source", return_value="0" * 40), \
             patch.object(p73, "native_step") as step:
            with self.assertRaisesRegex(AssertionError, "original source"):
                p73.execute_host("cpython", "/fake/cpython", Path(td) / "host.json")
            step.assert_not_called()

    def test_host_runtime_identity_mismatch_fails_before_native_round(self):
        with TemporaryDirectory() as td, \
             patch.object(p73, "git_source", return_value=p73.SOURCE), \
             patch.object(p73, "preflight_runtime", side_effect=AssertionError("wrong runtime")), \
             patch.object(p73, "native_step") as step:
            with self.assertRaisesRegex(AssertionError, "wrong runtime"):
                p73.execute_host("pypy", "/fake/pypy", Path(td) / "host.json")
            step.assert_not_called()

    def test_compare_requires_exact_round_parity_and_writes_pass(self):
        def make_report(runtime: str, wall: float) -> dict:
            rows = []
            for ordinal in range(1, 38):
                _, row = _fake_row(runtime, ordinal)
                row["native_wall_s"] = wall
                row.pop("selected_snapshot")
                rows.append(row)
            report = {
                "kind": p73.REPORT_KIND,
                "source_sha": p73.SOURCE,
                "seed": 0,
                "runtime": runtime,
                "interpreter_identity": {
                    "implementation": "cpython" if runtime == "cpython" else "pypy",
                    "python_version": [3, 12] if runtime == "cpython" else [3, 11],
                    "executable": f"/fake/{runtime}",
                },
                "host_identity": {"hostname": "fixture", "cpu_count": 3},
                "interpreter_artifact": {"url": None, "sha256": None},
                "status": "HOST_COMPLETE37",
                "rounds_completed": 37,
                "rounds": rows,
                "original_seed16384_executed": False,
                "original_seed49152_executed": False,
                "learning_claim": False,
            }
            return report

        with TemporaryDirectory() as td:
            left = Path(td) / "cpython.json"
            right = Path(td) / "pypy.json"
            out = Path(td) / "verdict.json"
            left.write_text(json.dumps(make_report("cpython", 20.0)))
            right.write_text(json.dumps(make_report("pypy", 10.0)))
            verdict = p73.compare_reports(left, right, out)
            self.assertEqual(verdict["status"], "PASS_COMPLETE37_PYPY_RUNTIME_CANDIDATE_ONLY")
            self.assertEqual(verdict["rounds"], 37)
            self.assertEqual(verdict["speed_ratio"], 2.0)
            self.assertEqual(verdict["report_sha256"]["cpython"], hashlib.sha256(left.read_bytes()).hexdigest())
            self.assertTrue(out.is_file())

    def test_compare_fails_closed_on_one_round_digest_mismatch(self):
        def make_report(runtime: str) -> dict:
            rows = []
            for ordinal in range(1, 38):
                _, row = _fake_row(runtime, ordinal)
                row.pop("selected_snapshot")
                rows.append(row)
            return {
                "kind": p73.REPORT_KIND,
                "source_sha": p73.SOURCE,
                "seed": 0,
                "runtime": runtime,
                "interpreter_identity": {
                    "implementation": "cpython" if runtime == "cpython" else "pypy",
                    "python_version": [3, 12] if runtime == "cpython" else [3, 11],
                    "executable": f"/fake/{runtime}",
                },
                "host_identity": {"hostname": "fixture", "cpu_count": 3},
                "interpreter_artifact": {"url": None, "sha256": None},
                "status": "HOST_COMPLETE37",
                "rounds_completed": 37,
                "rounds": rows,
                "original_seed16384_executed": False,
                "original_seed49152_executed": False,
                "learning_claim": False,
            }

        with TemporaryDirectory() as td:
            left = Path(td) / "cpython.json"
            right = Path(td) / "pypy.json"
            out = Path(td) / "verdict.json"
            left.write_text(json.dumps(make_report("cpython")))
            bad = make_report("pypy")
            bad["rounds"][18]["observer_hash"] = "tampered"
            right.write_text(json.dumps(bad))
            with self.assertRaisesRegex(AssertionError, "parity"):
                p73.compare_reports(left, right, out)
            verdict = json.loads(out.read_text())
            self.assertEqual(verdict["status"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
