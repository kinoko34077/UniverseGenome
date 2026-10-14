"""#336: only an exact reviewed main-branch activation marker can start E2.

This is static workflow inspection. It never triggers GitHub Actions, creates
an original seed, imports the study runner or writes an activation marker.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
from unittest import TestCase


WORKFLOW=Path(".github/workflows/a2-e2-original-exposed-336.yml")
MARKER=Path("research/approvals/a2_e2_336.run")


class OneActivationCommitOnly(TestCase):
    def test_activation_marker_exact_if_present(self):
        self.assertTrue(WORKFLOW.is_file())
        if MARKER.exists():
            self.assertEqual(
                MARKER.read_bytes(),
                b"A2-E2-336-EXPOSED-544-545-ROTATE4-ONCE\n",
            )


    def test_real_git_first_add_then_delete_readd_is_not_one_shot(self):
        # Exercise the actual Git-history predicate, not only YAML text.
        with TemporaryDirectory() as work:
            root=Path(work)
            def git(*args):
                return subprocess.run(
                    ["git",*args],cwd=root,check=True,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    text=True,
                ).stdout.strip()
            git("init")
            git("config","user.name","E2 Synthetic Test")
            git("config","user.email","e2-test@example.invalid")
            marker=root/"research"/"approvals"/"a2_e2_336.run"
            marker.parent.mkdir(parents=True)
            def commit(message):
                git("add","--all")
                git("commit","-m",message)
            def counts():
                path="research/approvals/a2_e2_336.run"
                return tuple(len(git("log","--full-history","--format=%H",
                    f"--diff-filter={kind}","HEAD","--",path).splitlines())
                    for kind in ("A","D"))
            marker.write_text("A2-E2-336-EXPOSED-544-545-ROTATE4-ONCE\\n")
            commit("first marker introduction")
            self.assertEqual(counts(),(1,0))
            marker.unlink()
            commit("marker removal")
            self.assertEqual(counts(),(1,1))
            marker.write_text("A2-E2-336-EXPOSED-544-545-ROTATE4-ONCE\\n")
            commit("marker reintroduction")
            self.assertEqual(counts(),(2,1))


    def test_failure_metadata_wired_without_turning_failure_into_success(self):
        workflow=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("id: source_gate", workflow)
        self.assertIn("id: native_physics", workflow)
        self.assertIn("if: failure()", workflow)
        self.assertIn("id: failure_metadata", workflow)
        self.assertIn("research.a2_e2_failure_manifest_336", workflow)
        self.assertIn("--stage \"$stage\" --reason \"$reason\"", workflow)
        self.assertIn("--run-id \"$ORIGINAL_RUN_ID\" --attempt \"$ORIGINAL_RUN_ATTEMPT\"", workflow)
        self.assertIn("reason=UNKNOWN", workflow)
        self.assertIn("reason=VALIDATION_FAILED", workflow)
        self.assertIn("if: failure() && steps.failure_metadata.outcome == 'success'", workflow)
        self.assertIn("name: a2-e2-336-original-exposed-failure", workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertIn("if: success()", workflow)
        self.assertNotIn("continue-on-error:", workflow)
        self.assertNotIn("retry", workflow.lower())

    def test_no_dispatch_schedule_or_pr_experiment(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('branches: [main]',text)
        self.assertIn('github.run_attempt == 1',text)
        self.assertIn("fetch-depth: 0",text)
        self.assertIn("git log --full-history",text)
        self.assertIn("--diff-filter=A HEAD",text)
        self.assertIn("--diff-filter=D HEAD",text)
        self.assertIn('test "$additions" = "1"',text)
        self.assertIn('test "$deletions" = "0"',text)
        self.assertIn('paths:',text)
        self.assertIn('"research/approvals/a2_e2_336.run"',text)
        self.assertNotIn('workflow_dispatch:',text)
        self.assertNotIn('pull_request:',text)
        self.assertNotIn('schedule:',text)
        self.assertIn('permissions:\n  contents: read',text)
        self.assertIn('persist-credentials: false',text)
        self.assertIn('git diff --name-only HEAD^ HEAD',text)
        self.assertIn('git cat-file -e HEAD^:research/approvals/a2_e2_336.run',text)
        self.assertIn('test "$(git diff --name-only HEAD^ HEAD)" = "research/approvals/a2_e2_336.run"',text)
        self.assertIn('timeout --signal=TERM --kill-after=10s 900s',text)
        self.assertIn('--execute --e2-exposed-only',text)
        self.assertIn('retention-days: 5',text)
        self.assertIn('actions/upload-artifact@v4',text)
        self.assertNotIn('contents: write',text)
        self.assertNotIn('git push',text)
        self.assertNotIn('GITHUB_TOKEN',text)
