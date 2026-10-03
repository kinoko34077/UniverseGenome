from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from core import geometry
from core.physics import step
from core.runner import build_status, load_config
from core.state import DEFAULT_MAX_CELLS, HP_BITS, LATENT_BITS, STRUCTURE_BITS
from server.app import build_server


ROOT = Path(__file__).resolve().parents[1]


class Phase0ScaffoldTests(unittest.TestCase):
    def test_required_phase0_repository_structure(self):
        required = [
            "docs/SPECIFICATION.md",
            "docs/ROADMAP.md",
            "docs/spec/01_requirements.md",
            "docs/spec/03_behavior_spec.md",
            "docs/spec/06_implementation_spec.md",
            "docs/spec/07_test_spec.md",
            "core/runner.py",
            "search/genome.py",
            "persistence/snapshot.py",
            "server/app.py",
            "ui/index.html",
            "config/default.json",
        ]
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)
        adrs = list((ROOT / "docs" / "adr").glob("ADR-*.md"))
        self.assertEqual(len(adrs), 8)

    def test_geometry_contract(self):
        self.assertEqual(geometry.LOGICAL_SIZE, 32)
        self.assertEqual(geometry.SUBDIVISIONS_PER_TILE, 8)
        self.assertEqual(geometry.FIXED_POINT_SIZE, 256)
        self.assertEqual(geometry.tile_coordinate(255), 31)
        self.assertEqual(geometry.wrap_fixed(256), 0)
        self.assertEqual(geometry.spatial_address(31, 31), 1023)

    def test_state_widths_and_capacity(self):
        self.assertEqual(STRUCTURE_BITS, 16)
        self.assertEqual(LATENT_BITS, 16)
        self.assertEqual(HP_BITS, 8)
        self.assertEqual(DEFAULT_MAX_CELLS, 1024)

    def test_default_config_is_parseable_and_preserves_no_cell_id(self):
        config = load_config(ROOT / "config" / "default.json")
        self.assertEqual(config["world"]["logical_size"], 32)
        self.assertEqual(config["world"]["fixed_point_size"], 256)
        self.assertEqual(config["world"]["max_cells"], 1024)
        self.assertFalse(config["state"]["permanent_cell_id"])
        self.assertTrue(config["features"]["phase1_physics"])

    def test_experiment_config_is_explicitly_deferred(self):
        with (ROOT / "config" / "experiment_v0_1.json").open(encoding="utf-8") as handle:
            config = json.load(handle)
        self.assertEqual(config["task"], "A->B->NULL")
        self.assertEqual(config["status"], "implemented_phase4_learning_outcome_recorded")

    def test_runner_reports_phase1_physics(self):
        status = build_status(load_config(ROOT / "config" / "default.json"))
        self.assertFalse(status["phase0_scaffold"])
        self.assertTrue(status["phase1_physics_implemented"])
        self.assertTrue(status["phase2a_bond_physics_implemented"])

    def test_physics_entrypoint_runs_a_universe_step(self):
        from core.physics import create_universe

        state = create_universe(seed=0)
        metrics = step(state)
        self.assertEqual(metrics.generation, 1)

    def test_ui_scaffold_exists_and_declares_external_clock(self):
        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "ui" / "sim_view.js").read_text(encoding="utf-8")
        self.assertIn("Phase 3", html)
        self.assertIn("authoritative simulation clock is external", js)
        self.assertNotIn("updateGrid(", js)

    def test_static_server_can_bind_without_owning_simulation_clock(self):
        server = build_server(port=0)
        try:
            self.assertGreater(server.server_address[1], 0)
        finally:
            server.server_close()

    def test_headless_module_entrypoint(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "core.runner",
                "--config",
                str(ROOT / "config" / "default.json"),
                "--json",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        status = json.loads(proc.stdout)
        self.assertEqual(status["phase"], 5)
        self.assertTrue(status["phase1_physics_implemented"])


if __name__ == "__main__":
    unittest.main()
