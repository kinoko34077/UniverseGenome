"""D18 one-shot Actions source-only audit; no original new research evaluation."""
from pathlib import Path
import unittest


WORKFLOW = Path(".github/workflows/d18-original-science-one-shot-294.yml")
RUNNER = Path("research/d18_native_twojob_science_294.py")
PREFIX = "research(D18.1): launch frozen new seed49152 original native two-host science once"


class D18OriginalOneShot294Tests(unittest.TestCase):
    def test_exact_source_and_launcher_modules_exist(self):
        self.assertTrue(WORKFLOW.is_file())
        self.assertTrue(RUNNER.is_file())

    def test_no_science_on_pr_or_unrelated_push(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("source_only_launch_contract:",text)
        self.assertIn("if: github.event_name == 'pull_request'",text)
        self.assertIn("github.event_name == 'push'",text)
        self.assertIn("github.ref == 'refs/heads/main'",text)
        self.assertIn("github.run_attempt == 1",text)
        self.assertIn(PREFIX,text)
        self.assertNotIn("workflow_dispatch:",text)
        self.assertNotIn("schedule:",text)
        self.assertNotIn("pypy",text.lower())
        self.assertNotIn("16384",text)
        self.assertIn("permissions:\n  contents: read",text)

    def test_two_hosts_exact_backend_rounds_and_global_timeout(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(text.count("    timeout-minutes: 18"),2)
        self.assertEqual(text.count("    timeout-minutes: 5"),1)
        self.assertEqual(text.count('          python-version: "3.12"'),3)
        self.assertEqual(text.count("timeout -k 15s 960s python -u -m research.d18_native_twojob_science_294"),2)
        self.assertIn("--job 1 --out reports/d18-native49152/host1",text)
        self.assertIn("--job 2 --inbound reports/d18-native49152/inbound --out reports/d18-native49152/host2",text)
        self.assertIn("needs: d18_newseed49152_host1_original_rounds01_to20",text)
        self.assertIn('          ref: ${{ github.sha }}',text)
        self.assertNotIn("mkdir -p reports/d18-native49152/host2",text)

    def test_full_firsthost_handoff_and_terminal_evidence_retained(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(text.count("          retention-days: 7"),2)
        self.assertEqual(text.count("        if: always()"),2)
        self.assertIn("d18-original-native49152-complete-first20",text)
        self.assertIn("d18-original-native49152-full-final-or-incomplete",text)
        self.assertIn("actions/download-artifact@v4",text)
        self.assertIn("actions/upload-artifact@v4",text)
        self.assertIn("cancel-in-progress: false",text)
        self.assertIn("persist-credentials: false",text)

    def test_runtime_is_dormant_and_requires_explicit_cli(self):
        runner=RUNNER.read_text(encoding="utf-8")
        self.assertIn("def run_stage(",runner)
        self.assertIn('if __name__ == "__main__":',runner)
        self.assertIn("sys.implementation.name == \"cpython\"",runner)
        self.assertIn("SteadyStateOptimizer.from_defaults(",runner)
        self.assertIn("execute_selected_round(",runner)
        self.assertIn("admit_completed_native_journal(",runner)
        self.assertIn("MAX_AGGREGATE_RSS",runner)
        self.assertIn("MAX_RETAINED_BYTES",runner)


if __name__ == "__main__":
    unittest.main()
