from __future__ import annotations

from collections import Counter
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from core.physics import PhysicsConfig, step
from core.population import (
    CATEGORY_OPERATORS,
    Population,
    load_population,
    run_population_headless,
    save_population,
)
from core.runner import build_status, load_config
from server.runtime import PopulationRuntime


ROOT = Path(__file__).resolve().parents[1]


def population_config(**overrides):
    values = {
        "max_cells": 4,
        "hp_decay": 0,
        "bond_gain": 0,
        "bond_decay": 0,
    }
    values.update(overrides)
    return PhysicsConfig(**values)


class Phase3PopulationTests(unittest.TestCase):
    def test_p3_001_has_four_categories_and_128_slots(self):
        population = Population.from_defaults(base_seed=71, config=population_config())

        self.assertEqual(len(population.slots), 128)
        self.assertEqual(Counter(slot.category for slot in population.slots), {name: 32 for name in CATEGORY_OPERATORS})
        pairs = [
            (slot.genome_id, slot.seed)
            for slot in population.slots
            if slot.category == CATEGORY_OPERATORS[0]
        ]
        self.assertEqual(len(set(pairs)), 32)
        for category in CATEGORY_OPERATORS[1:]:
            self.assertEqual(
                pairs,
                [(slot.genome_id, slot.seed) for slot in population.slots if slot.category == category],
            )

    def test_p3_002_slots_are_independent_and_replayable(self):
        first = Population.from_defaults(base_seed=72, config=population_config())
        second = Population.from_defaults(base_seed=72, config=population_config())
        first.slots[0].state.spawn(x=0, y=0, hp=100)
        second.slots[0].state.spawn(x=0, y=0, hp=100)

        self.assertIsNot(first.slots[0].state, first.slots[1].state)
        first.step()
        second.step()
        self.assertEqual(first.to_snapshot(), second.to_snapshot())
        self.assertEqual(first.slots[1].state.active_slots(), [])
        self.assertEqual(first.slots[0].state.to_snapshot(), second.slots[0].state.to_snapshot())

    def test_p3_003_history_is_bounded_and_rewind_restores_state(self):
        population = Population.from_defaults(base_seed=73, config=population_config(), history_length=128)
        population.slots[0].state.spawn(x=0, y=0, hp=100)
        population.run(3)

        self.assertLessEqual(population.history_size, 128)
        population.rewind(2)
        self.assertEqual(population.generation, 1)
        with self.assertRaises(ValueError):
            population.rewind(129)
        with self.assertRaises(ValueError):
            Population.from_defaults(base_seed=73, config=population_config(), history_length=127)

    def test_p3_004_clone_observation_does_not_mutate_authoritative_slot(self):
        population = Population.from_defaults(base_seed=74, config=population_config())
        population.slots[0].state.spawn(x=0, y=0, hp=100)
        before = population.slots[0].state.to_snapshot()

        clone = population.clone_for_observation(0)
        step(clone.state)

        self.assertEqual(clone.category, population.slots[0].category)
        self.assertEqual(clone.genome_id, population.slots[0].genome_id)
        self.assertEqual(population.slots[0].state.to_snapshot(), before)
        self.assertIsNot(clone.state, population.slots[0].state)

    def test_p3_005_population_snapshot_and_headless_summary(self):
        population = Population.from_defaults(base_seed=75, config=population_config())
        population.run(2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "population.json"
            save_population(path, population)
            resumed = load_population(path)
        self.assertEqual(resumed.to_snapshot(), population.to_snapshot())
        summary = run_population_headless(seed=75, generations=2, config=population_config())
        self.assertEqual(summary["slot_count"], 128)
        self.assertEqual(summary["generation"], 2)
        self.assertEqual(summary["generation_count"], 2)
        self.assertEqual(summary["slot_steps"], 256)
        self.assertGreaterEqual(summary["generations_per_second"], 0.0)
        self.assertEqual(summary["category_counts"], {name: 32 for name in CATEGORY_OPERATORS})

    def test_p2g_rewind_history_reports_bounded_memory_evidence(self):
        summaries = []
        for history_length in (128, 256, 512):
            population = Population.from_defaults(
                base_seed=76,
                config=population_config(),
                history_length=history_length,
            )
            population.run(4)
            summary = population.summary()
            self.assertLessEqual(summary["history_size"], history_length + 1)
            self.assertEqual(summary["history_entry_count"], summary["history_size"])
            self.assertGreater(summary["history_memory_bytes"], 0)
            self.assertLessEqual(summary["history_memory_bytes"], summary["history_memory_budget_bytes"])
            self.assertTrue(summary["history_memory_within_budget"])
            summaries.append(summary)
        self.assertLessEqual(summaries[-1]["history_memory_bytes"], summaries[0]["history_memory_budget_bytes"])

    def test_p3_006_status_config_and_ui_surface(self):
        raw = load_config(ROOT / "config" / "default.json")
        status = build_status(raw)
        self.assertTrue(status["phase3_runtime_implemented"])
        self.assertEqual(status["next_phase"], "Phase 6+ capability ladder (handoff only)")
        self.assertTrue(raw["features"]["multi_universe_runtime"])
        self.assertTrue(raw["features"]["io_learning"])
        self.assertTrue(raw["features"]["evolution"])

        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "ui" / "sim_view.js").read_text(encoding="utf-8")
        for control in ("Run", "Pause", "1 Step", "Reset", "Select Universe", "Clone for Observation", "Rewind", "Save Snapshot", "Load Snapshot"):
            self.assertIn(control, html)
        self.assertIn("16×8", html)
        self.assertIn("authoritative simulation clock is external", js)
        controls = (ROOT / "ui" / "controls.js").read_text(encoding="utf-8")
        self.assertIn("/api/state", js)
        self.assertIn("/api/control", js)
        self.assertIn("fetch(", js)
        self.assertIn("universeGenomeControl", controls)
        self.assertIn("--surface", html)

    def test_p3f_visual_observer_contract_is_authoritative_and_bounded(self):
        runtime = PopulationRuntime(history_length=512, config=population_config(initial_density=4))
        initial = runtime.state()

        self.assertEqual(initial["history_length"], 512)
        self.assertEqual(len(initial["summaries"][0]["overview"]), 64)
        self.assertTrue({"activity", "hierarchy", "occupied"} <= set(initial["summaries"][0]["overview"][0]))
        self.assertTrue({"activity", "hierarchy", "latent", "hp", "bond"} <= set(initial["selected"]["cells"][0]))

        clone = runtime.control("clone")
        self.assertEqual(clone["observation_target"], "clone")
        clone_generation = clone["selected"]["generation"]
        runtime.control("step")
        observed = runtime.state()
        self.assertEqual(observed["observation_target"], "clone")
        self.assertEqual(observed["selected"]["generation"], clone_generation)

        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "ui" / "sim_view.js").read_text(encoding="utf-8")
        self.assertIn("8×8", html)
        self.assertIn("mode-lock", html)
        self.assertIn("125", js)
        self.assertIn("500", js)
        self.assertIn("observation_target", js)

    def test_p3f_view_model_modes_and_visual_values_are_executable(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is required for the browser view-model contract")
        script = """
import { DETAIL_MODES, modeValue, hierarchyLevel } from './ui/view_model.mjs';
if (DETAIL_MODES.length !== 20) throw new Error('detail mode count');
if (modeValue({ latent: 8 }, 'latent bit 3') !== 1) throw new Error('latent bit mode');
if (modeValue({ structure: 1 << 6 }, 'hierarchy') !== 3) throw new Error('hierarchy mode');
if (modeValue({ activity: 77 }, 'activity') !== 77) throw new Error('activity mode');
if (hierarchyLevel(1 << 14) !== 7) throw new Error('hierarchy level');
"""
        result = subprocess.run(
            [node, "--input-type=module", "-e", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
