"""D16.12 PR-only static launch safety; NEVER import/execute original seed16384."""
from __future__ import annotations

from pathlib import Path
import unittest

WORKFLOW = (Path(__file__).resolve().parent.parent
            / ".github/workflows/d16-original-science-one-shot-217.yml")


class SourceOnlyOriginalScienceLaunchContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_only_one_push_activated_native_seed16384_study(self):
        s = self.source
        self.assertIn("push:\n    branches: [main]", s)
        self.assertIn("paths:\n      - \".github/workflows/d16-original-science-one-shot-217.yml\"", s)
        self.assertIn("startsWith(github.event.head_commit.message, 'research(D16.12): launch original seed16384 bounded once')", s)
        self.assertIn("if: github.event_name == 'pull_request'", s)
        self.assertNotIn("workflow_dispatch:", s)
        self.assertNotIn("schedule:", s)

    def test_exactly_two_original_native_20_plus_20_hosted_jobs(self):
        s = self.source
        needle = "python -u -m research.d16_original_twojob_science_217 --job "
        self.assertEqual(s.count(needle), 2)
        self.assertIn(needle + "1 --out", s)
        self.assertIn(needle + "2 --inbound", s)
        self.assertIn("needs: original_seed16384_host1_rounds01_to20", s)
        self.assertEqual(s.count("timeout-minutes: 18"), 2)
        self.assertEqual(s.count("timeout -k 15s 960s"), 2)

    def test_source_frozen_public_readonly_and_partial_failures_preserved(self):
        s = self.source
        self.assertIn("permissions:\n  contents: read", s)
        self.assertEqual(s.count("persist-credentials: false"), 3)
        self.assertEqual(s.count("ref: ${{ github.sha }}"), 3)
        self.assertEqual(s.count('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"'), 2)
        self.assertEqual(s.count("if: always()"), 2)
        self.assertEqual(s.count("retention-days: 7"), 2)
        self.assertIn("cancel-in-progress: false", s)
        self.assertNotIn("secrets.", s)
        self.assertNotIn("contents: write", s)


if __name__ == "__main__":
    unittest.main()
