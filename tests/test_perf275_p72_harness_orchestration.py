"""Synthetic, non-physical P7.2 harness orchestration contract tests.

No interpreter is launched, no source worlds are evaluated, and neither D15
journals nor D16 observations are produced. Genuine mature parity is separate.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from benchmarks import perf275_p72_mature_runtime_ab as p72


class P72MatureOrchestrationContractTests(unittest.TestCase):
    def _execute(self, *, pypy_wall=5.0, corrupt=None, source_ok=True):
        calls = []

        def fake_native_step(exe, scratch, label, ordinal, prior, *, observe):
            calls.append((exe, label, ordinal, prior, observe))
            self.assertIn(exe, ("/fake/cpython", "/fake/pypy"))
            self.assertEqual(observe, label != "prefix")
            self.assertEqual(label == "prefix", exe == "/fake/pypy")

            if ordinal <= 4:
                selected = p72.GOLDEN_FIRST4[ordinal - 1]
            elif ordinal in p72.GOLDEN_MATURE:
                selected = p72.GOLDEN_MATURE[ordinal]
            else:
                selected = f"fixture-v7-{ordinal}"

            hashes = {
                "base.json": f"fixture-base-{ordinal}",
                **{
                    f"batch-{i:05d}.json": f"fixture-patch-{ordinal}-{i}"
                    for i in range(8)
                },
                "final.json": f"fixture-final-{ordinal}",
            }
            observer = f"fixture-observer-{ordinal}"
            if label == "pypy" and ordinal == 10 and corrupt == "journal":
                hashes["batch-00000.json"] = "bad-byte-payload"
            if label == "pypy" and ordinal == 10 and corrupt == "observer":
                observer = "bad-observer"

            fake = {
                "selected_v7": selected,
                "journal_bytes": 2048,
                "journal_payload_sha256": hashes,
                "observer_hash": observer,
                "native_wall_s": 10.0 if label == "cpython" else pypy_wall,
                "sampled_rss_bytes": 100 * 1024 * 1024,
                "retained_scratch_bytes": 4096,
            }
            return scratch / f"{label}-{ordinal:02d}.json", fake

        with TemporaryDirectory(prefix="p72-fake-control-only-") as td:
            target = Path(td) / "result.json"
            argv = [
                "p72", "--cpython", "/fake/cpython",
                "--pypy", "/fake/pypy", "--out", str(target),
            ]
            with (patch.object(p72, "git_source", return_value=(
                    p72.SOURCE if source_ok else "0" * 40)),
                  patch.object(p72, "native_step", side_effect=fake_native_step),
                  patch.object(sys, "argv", argv),
                  redirect_stdout(io.StringIO())):
                failure = None
                try:
                    p72.main()
                except AssertionError as exc:
                    failure = exc
            report = json.loads(target.read_text()) if target.exists() else None
        return calls, report, failure

    def test_same_predecessor_at_both_maturities_and_exact_22_steps(self):
        calls, report, failure = self._execute()
        self.assertIsNone(failure)
        self.assertEqual(len(calls), 22)
        self.assertEqual(
            [(label, ordinal) for _, label, ordinal, _, _ in calls],
            [( "prefix", i) for i in range(1, 10)]
            + [("cpython", 10), ("pypy", 10)]
            + [("prefix", i) for i in range(11, 20)]
            + [("cpython", 20), ("pypy", 20)],
        )
        self.assertIsNone(calls[0][3])
        self.assertEqual(calls[9][3], calls[10][3])
        self.assertEqual(calls[20][3], calls[21][3])
        self.assertEqual(calls[11][3], Path(calls[10][3]).with_name("pypy-10.json"))
        self.assertEqual(report["prefix_count"], 19)
        self.assertEqual(set(report["mature"]), {"10", "20"})
        self.assertEqual(report["combined_speed_ratio"], 2.0)
        self.assertEqual(report["status"], "PASS_MATURE_20_PYPY_RUNTIME_CANDIDATE_ONLY")
        self.assertFalse(report["original_seed16384_executed"])
        self.assertFalse(report["learning_claim"])

    def test_byte_mismatch_fails_closed_without_success_status(self):
        _, report, failure = self._execute(corrupt="journal")
        self.assertIsInstance(failure, AssertionError)
        self.assertIn("cross-runtime mismatch", str(failure))
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(report["mature"], {})

    def test_observer_mismatch_fails_closed_without_success_status(self):
        _, report, failure = self._execute(corrupt="observer")
        self.assertIsInstance(failure, AssertionError)
        self.assertIn("cross-runtime mismatch", str(failure))
        self.assertEqual(report["status"], "INCOMPLETE")

    def test_no_speedup_is_rejected_not_misreported_as_success(self):
        calls, report, failure = self._execute(pypy_wall=15.0)
        self.assertIsNone(failure)
        self.assertEqual(len(calls), 22)
        self.assertEqual(report["status"], "REJECT_OR_HOLD_MATURE_RUNTIME_GATE")
        self.assertLess(report["combined_speed_ratio"], 1.0)

    def test_wrong_source_fails_before_any_native_call(self):
        calls, report, failure = self._execute(source_ok=False)
        self.assertIsInstance(failure, AssertionError)
        self.assertIn("original source checkout changed", str(failure))
        self.assertEqual(calls, [])
        self.assertIsNone(report)


if __name__ == "__main__":
    unittest.main()
