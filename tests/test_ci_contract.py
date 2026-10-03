from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BrowserE2EWorkflowContractTests(unittest.TestCase):
    def test_ci_exposes_phase_validation_and_browser_e2e_lanes(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        self.assertIn("  phase5_validation:", workflow)
        self.assertNotIn("  scaffold:", workflow)
        self.assertIn("name: Browser E2E", workflow)
        self.assertIn("npx playwright test", workflow)

    def test_browser_e2e_tooling_is_declared(self):
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertIn("@playwright/test", package["devDependencies"])
        self.assertTrue((ROOT / "playwright.config.mjs").is_file())
        self.assertTrue((ROOT / "e2e" / "observer.spec.mjs").is_file())


if __name__ == "__main__":
    unittest.main()
