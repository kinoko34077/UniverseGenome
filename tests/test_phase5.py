from __future__ import annotations

import json
from pathlib import Path
import unittest

from core.experiment import ExperimentConfig
from core.population import run_population_headless
from core.physics import PhysicsConfig, create_universe
from core.runner import build_status, load_config
from search.evolution import (
    CandidateSlot,
    SteadyStateOptimizer,
    evaluate_candidate,
    optimizer_snapshot,
    restore_optimizer_snapshot,
    run_optimizer_headless,
    seed_escalation,
)
from search.fitness import Fitness, compare_fitness
from search.genome import UniverseGenome
from search.pruning import GrowthHistory, growth_flags, prune_candidates, protected_indices


ROOT = Path(__file__).resolve().parents[1]


class Phase5OptimizerTests(unittest.TestCase):
    def test_p5_001_genome_excludes_seed_and_mutates_one_binary_step(self):
        genome = UniverseGenome.default()
        mutated = genome.mutate("hp_decay", direction=1)
        self.assertNotIn("seed", genome.to_dict())
        changed = [key for key in genome.to_dict() if genome.to_dict()[key] != mutated.to_dict()[key]]
        self.assertEqual(changed, ["hp_decay"])
        self.assertEqual(mutated.hp_decay, 2)
        with self.assertRaises(ValueError):
            genome.mutate("seed", direction=1)

    def test_p5_002_fitness_is_lexicographic_and_not_complexity(self):
        winner = Fitness(success=1, wrong_outputs=9, timeouts=9, response_latency=99, activity_cost=999)
        loser = Fitness(success=0, wrong_outputs=0, timeouts=0, response_latency=0, activity_cost=0)
        self.assertEqual(compare_fitness(winner, loser), 1)
        self.assertEqual(compare_fitness(winner, winner), 0)
        self.assertLess(Fitness(1, 0, 0, 1, 1).sort_key(), Fitness(1, 0, 0, 2, 1).sort_key())

    def test_p5_003_growth_flags_and_history_are_bounded(self):
        before = Fitness(0, 4, 3, 8, 10)
        after = Fitness(1, 3, 2, 7, 9)
        flags = growth_flags(before, after)
        self.assertEqual(flags & 0b11111, 0b11111)
        history = GrowthHistory()
        for _ in range(5):
            history.push(flags)
        self.assertEqual(history.window_count, 4)
        self.assertLessEqual(history.value, 0xFFFFFFFF)
        self.assertEqual(history.score, 20)

    def test_p5_004_pruning_protects_absolute_top_eighth(self):
        records = [
            CandidateSlot(index=index, category="masked_copy", genome=UniverseGenome.default(), seed=index, fitness=Fitness(1 if index == 0 else 0, 0, 0, index, index), growth_windows=((4, 4, 4, 4) if index in (0, 4, 5, 6) else (0, 0, 0, 0)))
            for index in range(8)
        ]
        self.assertIn(0, protected_indices(records))
        self.assertNotIn(0, prune_candidates(records))
        self.assertIn(1, prune_candidates(records))

    def test_p5_005_seed_escalation_and_replacement_are_deterministic(self):
        self.assertEqual([seed_escalation(value) for value in (4, 8, 16, 32, 64)], [8, 16, 32, 32, 32])
        parent = CandidateSlot(index=0, category="masked_copy", genome=UniverseGenome.default(), seed=41, fitness=Fitness(0, 0, 0, 0, 0), growth_windows=(1,))
        optimizer = SteadyStateOptimizer()
        replacement = optimizer.replace_free_slot(free_index=12, parent=parent, direction=1)
        self.assertEqual(replacement.index, 12)
        self.assertEqual(replacement.category, parent.category)
        self.assertEqual(replacement.seed, 42)
        self.assertNotIn("seed", replacement.genome.to_dict())

    def test_p5_006_status_and_flags(self):
        raw = load_config(ROOT / "config" / "default.json")
        status = build_status(raw)
        self.assertTrue(status["phase5_optimizer_implemented"])
        self.assertEqual(status["next_phase"], "Phase 6+ capability ladder (handoff only)")
        self.assertTrue(raw["features"]["multi_universe_search"])
        self.assertTrue(raw["features"]["evolution"])
        self.assertFalse(raw["features"]["phase6_capabilities"])
        with (ROOT / "config" / "experiment_v0_1.json").open(encoding="utf-8") as handle:
            experiment = json.load(handle)
        self.assertEqual(experiment["learning_claim"], False)
        handoff = (ROOT / "docs" / "PHASE6_HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("No Phase 6+ capability has been implemented", handoff)

    def test_p5_007_genome_maps_every_field_to_effective_physics(self):
        genome = UniverseGenome(
            initial_density=2,
            hp_decay=3,
            hp_gain=5,
            noise_rate=7,
            bond_gain=11,
            bond_decay=13,
            collision_threshold=17,
            fusion_threshold=19,
            fragmentation_base_probability=23,
            black_hole_grace=29,
            rotate_amount=15,
        )
        base = PhysicsConfig(max_cells=8)
        effective = genome.to_physics_config(base)

        self.assertEqual(effective.initial_density, 2)
        self.assertEqual(effective.hp_decay, 3)
        self.assertEqual(effective.recovery_hp, 5)
        self.assertEqual(effective.noise_rate, 7)
        self.assertEqual(effective.bond_gain, 11)
        self.assertEqual(effective.bond_decay, 13)
        self.assertEqual(effective.collision_threshold, 17)
        self.assertEqual(effective.fusion_velocity_threshold, 19)
        self.assertEqual(effective.fragmentation_rate, 23)
        self.assertEqual(effective.black_hole_grace, 29)
        self.assertEqual(effective.rotate_amount, 15)
        self.assertEqual(len(create_universe(seed=3, config=effective).active_slots()), 2)

        with self.assertRaises(ValueError):
            UniverseGenome(initial_density=9).to_physics_config(base)

    def test_p5_008_candidate_evaluation_uses_phase4_measurement(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        measurement = evaluate_candidate(
            genome=UniverseGenome.default(),
            seeds=(3, 4),
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        self.assertEqual(measurement.seed_count, 2)
        self.assertEqual(measurement.baseline_successes, 0)
        self.assertEqual(measurement.trained_successes, 0)
        self.assertFalse(measurement.learning_claim)
        self.assertEqual(len(measurement.per_seed), 2)

    def test_p5_009_replacement_escalates_evaluation_seed_count(self):
        parent = CandidateSlot(
            index=0,
            category="masked_copy",
            genome=UniverseGenome.default(),
            seed=41,
            seed_count=4,
            fitness=Fitness(0, 0, 0, 0, 0),
            growth_windows=(1,),
        )
        optimizer = SteadyStateOptimizer()
        replacement = parent
        for expected_count in (8, 16, 32, 32):
            replacement = optimizer.replace_free_slot(free_index=12, parent=replacement, direction=1)
            self.assertEqual(replacement.seed_count, expected_count)

    def test_p5_010_headless_output_contains_real_measurement_and_replacement_trace(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        result = run_optimizer_headless(
            seeds=(3, 4),
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        self.assertEqual(result["candidate_measurement"]["seed_count"], 2)
        self.assertFalse(result["phase4_learning_claim"])
        self.assertEqual(result["replacement_seed_counts"], [8, 16, 32, 32])

    def test_p2g_optimizer_snapshot_roundtrip_preserves_bounded_state(self):
        parent = CandidateSlot(
            index=2,
            category="masked_xor",
            genome=UniverseGenome.default(),
            seed=12,
            fitness=Fitness(1, 2, 3, 4, 5, 6, 7),
            growth_windows=(1, 3, 7, 15),
            seed_count=16,
            parent_index=1,
        )
        payload = optimizer_snapshot((parent,), generation=128)
        generation, restored = restore_optimizer_snapshot(payload)
        self.assertEqual(generation, 128)
        self.assertEqual(restored, (parent,))
        self.assertEqual(optimizer_snapshot(restored, generation=generation), payload)

    def test_p2g_growth_flags_include_retention_and_noise_robustness(self):
        before = Fitness(0, 4, 3, 8, 10, 0, 0)
        after = Fitness(1, 3, 2, 7, 9, 1, 1)
        self.assertEqual(growth_flags(before, after) & 0b1111111, 0b1111111)

    def test_p2g_pruning_uses_growth_bit_count_not_numeric_byte_sum(self):
        records = [
            CandidateSlot(
                index=index,
                category="masked_copy",
                genome=UniverseGenome.default(),
                seed=index,
                fitness=Fitness(1 if index == 0 else 0),
                growth_windows=(0xFF, 0xFF, 0xFF, 0xFF)
                if index == 0
                else (0x0F, 0x0F, 0x0F, 0x0F)
                if index < 7
                else (0x80, 0x80, 0x80, 0x80),
            )
            for index in range(8)
        ]
        self.assertIn(7, prune_candidates(records))

    def test_p2g_population_headless_reports_bounded_performance_counts(self):
        summary = run_population_headless(
            seed=75,
            generations=2,
            config=PhysicsConfig(max_cells=4, hp_decay=0, bond_gain=0, bond_decay=0),
        )
        self.assertEqual(summary["generation_count"], 2)
        self.assertEqual(summary["slot_steps"], 256)
        self.assertGreaterEqual(summary["generations_per_second"], 0.0)

    def test_p2g_pruning_protection_is_category_local(self):
        records = [
            CandidateSlot(
                index=index,
                category="masked_copy" if index < 8 else "masked_xor",
                genome=UniverseGenome.default(),
                seed=index,
                fitness=Fitness(1 if index in (0, 1) else 0, response_latency=index),
                growth_windows=(0xFF, 0xFF, 0xFF, 0xFF)
                if index in (0, 8)
                else (0, 0, 0, 0),
            )
            for index in range(16)
        ]
        protected = protected_indices(records)
        self.assertIn(0, protected)
        self.assertIn(8, protected)

    def test_p5_011_integrated_optimizer_evaluates_128_and_replaces_locally(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=101,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        self.assertEqual(len(optimizer.candidates), 128)
        self.assertEqual({category: sum(slot.category == category for slot in optimizer.candidates)
                          for category in ("masked_copy", "masked_xor", "rotate_copy", "masked_and")},
                         {"masked_copy": 32, "masked_xor": 32, "rotate_copy": 32, "masked_and": 32})
        for category in ("masked_copy", "masked_xor", "rotate_copy", "masked_and"):
            slot = next(candidate for candidate in optimizer.candidates if candidate.category == category)
            self.assertEqual(slot.universe_snapshot["config"]["latent_operator"], category)

        summary = optimizer.step()

        self.assertEqual(summary["evaluated_slots"], 128)
        self.assertEqual(summary["category_counts"], {
            "masked_copy": 32,
            "masked_xor": 32,
            "rotate_copy": 32,
            "masked_and": 32,
        })
        self.assertEqual(summary["cross_category_selection"], False)
        self.assertGreaterEqual(summary["replacement_count"], 4)
        self.assertGreaterEqual(len({slot.last_mutation_field for slot in optimizer.candidates if slot.last_mutation_field}), 2)
        self.assertTrue(all(slot.universe_snapshot is not None for slot in optimizer.candidates))

    def test_p5_012_integrated_snapshot_restores_deterministic_continuation(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        first = SteadyStateOptimizer.from_defaults(
            base_seed=102,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        first.step()
        restored = SteadyStateOptimizer.from_snapshot(first.to_snapshot())
        first.step()
        restored.step()
        self.assertEqual(first.to_snapshot(), restored.to_snapshot())

        payload = restored.to_snapshot()
        self.assertIn("base_config", payload)
        self.assertIn("experiment", payload)
        self.assertIn("scheduler", payload)
        self.assertEqual(len(payload["candidates"]), 128)
        self.assertTrue(all("universe_snapshot" in candidate for candidate in payload["candidates"]))

    def test_p5_013_headless_reports_integrated_multi_field_search(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        result = run_optimizer_headless(
            seeds=(3, 4),
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
            iterations=3,
        )
        self.assertEqual(result["population_size"], 128)
        self.assertEqual(result["optimizer_iterations"], 3)
        self.assertEqual(result["category_counts"], {
            "masked_copy": 32,
            "masked_xor": 32,
            "rotate_copy": 32,
            "masked_and": 32,
        })
        self.assertGreaterEqual(result["replacement_count"], 4)
        self.assertGreaterEqual(len(result["mutation_fields"]), 2)
        self.assertEqual(result["seed_escalation"], [8, 16, 32, 32])
        self.assertEqual(result["integrated_seed_counts"], [8] * 4 + [16] * 4 + [32] * 4)

    def test_p5_014_integrated_loop_reaches_growth_pruning(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=103,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        summary = optimizer.run(iterations=5)
        self.assertGreater(summary["pruned_count"], 0)
        self.assertTrue(any(item["reason"] == "growth_pruned" for item in summary["replacements"]))


if __name__ == "__main__":
    unittest.main()
