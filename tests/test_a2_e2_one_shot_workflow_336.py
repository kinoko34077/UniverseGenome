"""#336: only an exact reviewed main-branch activation marker can start E2.

This is static workflow inspection. It never triggers GitHub Actions, creates
an original seed, imports the study runner or writes an activation marker.
"""
from pathlib import Path
from unittest import TestCase


WORKFLOW=Path(".github/workflows/a2-e2-original-exposed-336.yml")
MARKER=Path("research/approvals/a2_e2_336.run")


class OneActivationCommitOnly(TestCase):
    def test_no_marker_in_source_only_preparation(self):
        self.assertFalse(MARKER.exists())
        self.assertTrue(WORKFLOW.is_file())

    def test_no_dispatch_schedule_or_pr_experiment(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('branches: [main]',text)
        self.assertIn('paths:',text)
        self.assertIn('"research/approvals/a2_e2_336.run"',text)
        self.assertNotIn('workflow_dispatch:',text)
        self.assertNotIn('pull_request:',text)
        self.assertNotIn('schedule:',text)
        self.assertIn('permissions:\n  contents: read',text)
        self.assertIn('persist-credentials: false',text)
        self.assertIn('git diff --name-only HEAD^ HEAD',text)
        self.assertIn('test "$(git diff --name-only HEAD^ HEAD)" = "research/approvals/a2_e2_336.run"',text)
        self.assertIn('timeout --signal=TERM --kill-after=10s 900s',text)
        self.assertIn('--execute --e2-exposed-only',text)
        self.assertIn('retention-days: 5',text)
        self.assertIn('actions/upload-artifact@v4',text)
        self.assertNotIn('contents: write',text)
        self.assertNotIn('git push',text)
        self.assertNotIn('GITHUB_TOKEN',text)
