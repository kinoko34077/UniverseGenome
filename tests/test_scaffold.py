from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from core import geometry
from core import latent_ops
from core.physics import PhysicsConfig, create_universe, step
from core.runner import build_status, load_config
from core.state import DEFAULT_MAX_CELLS, HP_BITS, LATENT_BITS, STRUCTURE_BITS
import core
import persistence
from server.app import build_server
import server


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
        self.assertEqual(config["phase"], 5)
        self.assertEqual(config["world"]["logical_size"], 32)
        self.assertEqual(config["world"]["fixed_point_size"], 256)
        self.assertEqual(config["world"]["max_cells"], 1024)
        self.assertFalse(config["state"]["permanent_cell_id"])
        self.assertTrue(config["features"]["phase1_physics"])
        self.assertEqual(config["physics"]["initial_latent"], 1)
        self.assertEqual(config["physics"]["initial_speed_code"], 1)
        self.assertEqual(config["physics"]["noise_latent"], 1)
        self.assertEqual(config["physics"]["noise_speed_code"], 1)

    def test_default_config_creates_a_deterministic_initial_substrate(self):
        config = load_config(ROOT / "config" / "default.json")
        state = create_universe(seed=17, config=PhysicsConfig.from_mapping(config))
        replay = create_universe(seed=17, config=PhysicsConfig.from_mapping(config))
        self.assertGreater(len(state.active_slots()), 0)
        self.assertEqual(state.to_snapshot(), replay.to_snapshot())

    def test_experiment_config_records_effective_protocol_and_outcome(self):
        with (ROOT / "config" / "experiment_v0_1.json").open(encoding="utf-8") as handle:
            config = json.load(handle)
        self.assertEqual(config["task"], "A->B->NULL")
        self.assertEqual(config["status"], "implemented_phase4_learning_outcome_recorded")
        self.assertEqual(config["teacher_delay_generations"], 4)
        self.assertEqual(config["teacher_repetitions"], 1)
        self.assertFalse(config["learning_claim"])

    def test_phase5_markers_and_audit_projections_are_current(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        runner = (ROOT / "core" / "runner.py").read_text(encoding="utf-8")
        server = (ROOT / "server" / "app.py").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        specification = (ROOT / "docs" / "SPECIFICATION.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
        changelog = (ROOT / "docs" / "spec" / "08_changelog.md").read_text(encoding="utf-8")
        handoff = (ROOT / "docs" / "PHASE6_HANDOFF.md").read_text(encoding="utf-8")

        self.assertIn("Headless Phase 5 smoke", ci)
        self.assertNotIn("Headless Phase 0 smoke", ci)
        self.assertIn("Phase 6.1", runner)
        self.assertIn("runtime API", server)
        self.assertIn("server-owned runtime", readme)
        self.assertNotIn("unchanged observer/UI scaffold", readme)
        self.assertIn("Phase 0 through Phase 5", specification)
        self.assertIn("PR #32", changelog)
        self.assertIn("PR #33", changelog)
        self.assertIn("PR #34", changelog)
        self.assertIn("02b07bb8dae7f649d543f8386d421064c6977a55", changelog)
        # Historical acceptance markers remain durable, while the handoff also
        # projects the current post-#59 readiness evidence.
        self.assertIn("02b07bb8dae7f649d543f8386d421064c6977a55", handoff)
        self.assertIn("84/84", handoff)
        self.assertIn("4fe87b2f32662d7445bc8084dc91d07e2a029d42", handoff)
        self.assertIn("5844e989706afce7988c4b8d50f94fc33afb1228", handoff)
        self.assertIn("130 tests / OK", handoff)
        self.assertIn("37137438184", handoff)
        self.assertIn("readiness audit #60", handoff)
        self.assertIn("Phase 5", roadmap)

    def test_current_state_separates_implementation_from_readiness(self):
        status = build_status(load_config(ROOT / "config" / "default.json"))

        self.assertTrue(status["phase5_optimizer_implemented"])
        self.assertTrue(status["phase6_capabilities_implemented"])
        self.assertTrue(status["phase6_multi_mapping_implemented"])
        self.assertEqual(status["acceptance_state"], "accepted")
        self.assertTrue(status["phase6_ready"])
        self.assertEqual(status["blocking_owners"], [])
        self.assertEqual(status["readiness_owner"], "#60")
        self.assertEqual(
            status["next_phase"],
            "Phase 6.2 temporal sequence discrimination (bounded child Issue required)",
        )

    def test_post_audit_documentation_routes_to_phase6_handoff(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        specification = (ROOT / "docs" / "SPECIFICATION.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
        handoff = (ROOT / "docs" / "PHASE6_HANDOFF.md").read_text(encoding="utf-8")
        overview = (ROOT / "docs" / "spec" / "00_overview.md").read_text(encoding="utf-8")
        functional = (ROOT / "docs" / "spec" / "02_functional_spec.md").read_text(encoding="utf-8")
        changelog = (ROOT / "docs" / "spec" / "08_changelog.md").read_text(encoding="utf-8")
        historical_plans = [
            (
                ROOT / "docs" / "superpowers" / "plans" / name
            ).read_text(encoding="utf-8")
            for name in (
                "2026-10-03-phase5-authoritative-slots.md",
                "2026-10-03-phase5-semantic-corrections.md",
                "2026-10-04-phase5-free-slot-evidence.md",
            )
        ]

        self.assertIn("P6.1 multiple independent byte mappings", readme)
        self.assertIn("readiness rerun #60 passed", readme)
        self.assertIn("GUI/search integration #63 is complete via PR #73", readme)
        self.assertIn("Phase 5 search-semantic remediation #65 is complete via PR #70", readme)
        self.assertIn("P6.2 temporal sequence discrimination", readme)
        self.assertIn("authoritative Phase 5", readme)
        self.assertIn("P6.1 multiple-mapping capability implemented", specification)
        self.assertIn("P6.2", specification)
        self.assertIn(
            "Phase 6+ — Capability ladder (#78)",
            roadmap,
        )
        self.assertIn(
            "Status: **P6.1 multiple independent byte mappings accepted; P6.2 is the next bounded capability frontier**",
            handoff,
        )
        self.assertIn("historical v0.1 physics/search contract", handoff)
        self.assertIn("Status is a single base term", overview)
        self.assertNotIn("Status: open / policy hook only", functional)
        self.assertNotIn("Status: accepted invariant", functional)
        self.assertIn("Phase 2D accepted (#16 / PR #17)", changelog)
        self.assertIn("REQ-083", changelog)
        for historical_plan in historical_plans:
            self.assertIn("Historical execution record; not Current State authority.", historical_plan)

    def test_phase5_metadata_and_implemented_defaults_are_current(self):
        functional = (ROOT / "docs" / "spec" / "02_functional_spec.md").read_text(encoding="utf-8")
        behavior = (ROOT / "docs" / "spec" / "03_behavior_spec.md").read_text(encoding="utf-8")
        implementation = (ROOT / "docs" / "spec" / "06_implementation_spec.md").read_text(encoding="utf-8")

        self.assertEqual(core.PHASE, 6)
        self.assertEqual(persistence.PHASE, 5)
        self.assertEqual(server.PHASE, 5)

        core_init = (ROOT / "core" / "__init__.py").read_text(encoding="utf-8")
        server_init = (ROOT / "server" / "__init__.py").read_text(encoding="utf-8")
        persistence_init = (ROOT / "persistence" / "__init__.py").read_text(encoding="utf-8")
        snapshot_module = (ROOT / "persistence" / "snapshot.py").read_text(encoding="utf-8")
        for package_metadata in (core_init, server_init, persistence_init):
            self.assertIn("implementation-level marker", package_metadata)
            self.assertNotIn("accepted Phase 5", package_metadata)
        self.assertIn("current UniverseState persistence contract", snapshot_module)
        self.assertNotIn("Phase 2D authoritative state", snapshot_module)
        self.assertNotIn("unable to read Phase 2D snapshot", snapshot_module)

        self.assertEqual(
            latent_ops.LATENT_OPERATOR_CATEGORIES,
            ("masked_copy", "masked_xor", "rotate_copy", "masked_and"),
        )
        self.assertIn("| IN0 | `(8, 12)` |", functional)
        self.assertIn("| OUT7 | `(24, 19)` |", functional)
        self.assertIn("OUT_NULL", functional)
        self.assertIn("`(24, 22)`", functional)
        self.assertIn("noise_attempts", behavior)
        self.assertIn("one deterministic noise-event decision", behavior)
        self.assertIn("black_hole_grace = 2", implementation)

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
        self.assertEqual(status["phase"], 6)
        self.assertTrue(status["phase1_physics_implemented"])


if __name__ == "__main__":
    unittest.main()
