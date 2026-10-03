from __future__ import annotations

import json
from pathlib import Path
import unittest

from core.experiment import (
    EvaluationResult,
    ExperimentConfig,
    LearningMeasurement,
    SeedMeasurement,
)
from core.io_bus import OutputEvent
from core.population import run_population_headless
from core.physics import PhysicsConfig, create_universe
from core.runner import build_status, load_config
from core.state import UniverseState
from search import evolution as evolution_module
from search.evolution import (
    SteadyStateOptimizer,
    UniverseSlot,
    evaluate_candidate,
    run_optimizer_headless,
    seed_escalation,
)
from search.fitness import Fitness, compare_fitness
from search.genome import UniverseGenome
from search.pruning import GrowthHistory, growth_flags, prune_candidates, protected_indices


ROOT = Path(__file__).resolve().parents[1]


def make_slot(
    *,
    index: int,
    category: str = "masked_copy",
    seed: int = 0,
    genome: UniverseGenome | None = None,
    fitness: Fitness | None = None,
    growth_windows: tuple[int, ...] = (),
    generation: int = 0,
    parent_index: int | None = None,
) -> UniverseSlot:
    config = PhysicsConfig(max_cells=8)
    state = create_universe(seed=seed, config=config)
    state.generation = generation
    return UniverseSlot(
        index=index,
        category=category,
        genome=genome or UniverseGenome.default(),
        seed=seed,
        state=state,
        fitness=fitness or Fitness(),
        growth_windows=growth_windows,
        parent_index=parent_index,
    )


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

    def test_p5_015_fitness_is_invariant_to_equivalent_seed_counts(self):
        expected = (OutputEvent.byte(66), OutputEvent.null())
        result = EvaluationResult(
            expected_events=expected,
            autonomous_events=expected,
            success=True,
            clone_generation=99,
            event_generations=(4, 6),
            evaluation_generations=12,
            activity_cost=8,
            timed_out=False,
        )

        def measurement(repetitions):
            per_seed = tuple(
                SeedMeasurement(
                    seed=index,
                    baseline=result,
                    trained=result,
                    baseline_no_input=result,
                    trained_no_input=result,
                    baseline_alternate=result,
                    trained_alternate=result,
                )
                for index in range(repetitions)
            )
            return LearningMeasurement(
                seed_count=repetitions,
                baseline_successes=repetitions,
                trained_successes=repetitions,
                baseline_no_input_clean=repetitions,
                trained_no_input_clean=repetitions,
                baseline_alternate_input_clean=repetitions,
                trained_alternate_input_clean=repetitions,
                criterion="test",
                learning_claim=False,
                per_seed=per_seed,
            )

        self.assertEqual(
            SteadyStateOptimizer._fitness_from_measurement(measurement(4)),
            SteadyStateOptimizer._fitness_from_measurement(measurement(8)),
        )

    def test_p5_016_fitness_uses_named_event_metrics_and_five_field_order(self):
        result = EvaluationResult(
            expected_events=(OutputEvent.byte(66), OutputEvent.null()),
            autonomous_events=(OutputEvent.byte(65), OutputEvent.byte(64), OutputEvent.byte(66)),
            success=False,
            clone_generation=99,
            event_generations=(2, 4, 5),
            evaluation_generations=12,
            activity_cost=17,
            timed_out=True,
        )
        measurement = LearningMeasurement(
            seed_count=1,
            baseline_successes=0,
            trained_successes=0,
            baseline_no_input_clean=0,
            trained_no_input_clean=1,
            baseline_alternate_input_clean=0,
            trained_alternate_input_clean=1,
            criterion="test",
            learning_claim=False,
            per_seed=(SeedMeasurement(
                seed=1,
                baseline=result,
                trained=result,
                baseline_no_input=result,
                trained_no_input=result,
                baseline_alternate=result,
                trained_alternate=result,
            ),),
        )

        fitness = SteadyStateOptimizer._fitness_from_measurement(measurement)
        self.assertEqual(fitness.wrong_outputs, 2.0)
        self.assertEqual(fitness.timeouts, 1.0)
        self.assertEqual(fitness.response_latency, 5.0)
        self.assertEqual(fitness.activity_cost, 17.0)
        self.assertEqual(
            Fitness(success=1, retention=0, noise_robustness=0).sort_key(),
            Fitness(success=1, retention=1, noise_robustness=1).sort_key(),
        )

    def test_p5_017_initial_population_has_eight_matched_parameter_genomes(self):
        genomes = UniverseGenome.initial_population()
        self.assertEqual(len(genomes), 8)
        self.assertEqual(len({tuple(genome.to_dict().items()) for genome in genomes}), 8)

        optimizer = SteadyStateOptimizer.from_defaults(base_seed=101)
        first_category = [
            slot.genome
            for slot in optimizer.candidates
            if slot.category == "masked_copy"
        ]
        self.assertEqual(len(first_category), 32)
        for category in ("masked_xor", "rotate_copy", "masked_and"):
            self.assertEqual(
                first_category,
                [slot.genome for slot in optimizer.candidates if slot.category == category],
            )
        self.assertEqual(len({slot.seed for slot in optimizer.slots}), 32)
        for genome_index in range(8):
            expected = {
                slot.seed
                for slot in optimizer.slots
                if slot.category == "masked_copy"
                and slot.genome == UniverseGenome.initial_population()[genome_index]
            }
            self.assertEqual(len(expected), 4)
            for category in ("masked_xor", "rotate_copy", "masked_and"):
                actual = {
                    slot.seed
                    for slot in optimizer.slots
                    if slot.category == category
                    and slot.genome == UniverseGenome.initial_population()[genome_index]
                }
                self.assertEqual(actual, expected)

    def test_p5_018_seed_evidence_allocates_a_fresh_same_genome_slot(self):
        parent = make_slot(index=0, seed=41)
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=100)
        expanded = optimizer.allocate_seed_slot(free_index=12, parent=parent)

        self.assertEqual(expanded.index, 12)
        self.assertEqual(expanded.category, parent.category)
        self.assertEqual(expanded.genome, parent.genome)
        self.assertNotEqual(expanded.seed, parent.seed)
        self.assertEqual(expanded.state.generation, 0)
        self.assertEqual(expanded.allocation_reason, "seed_evidence")

    def test_p5_019_mutation_child_is_separate_from_seed_escalation(self):
        parent = make_slot(index=0, seed=41)
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=100)
        child = optimizer.replace_free_slot(
            free_index=12,
            parent=parent,
            direction=1,
            field="hp_decay",
        )

        self.assertNotEqual(child.genome, parent.genome)
        self.assertNotEqual(child.seed, parent.seed)
        self.assertEqual(child.state.generation, 0)
        self.assertEqual(child.last_mutation_field, "hp_decay")
        self.assertEqual(child.allocation_reason, "mutation_child")

    def test_p5_020_integrated_loop_does_not_replace_live_slot_without_free_slot(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=104,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        identities = {slot.index: id(slot.state) for slot in optimizer.slots}

        first = optimizer.step()
        second = optimizer.step()

        self.assertEqual(first["evaluated_slots"], 128)
        self.assertEqual(second["evaluated_slots"], 128)
        self.assertEqual(first["replacement_count"], 0)
        self.assertEqual(second["replacement_count"], 0)
        self.assertEqual(first["replacements"], [])
        self.assertEqual(second["replacements"], [])
        self.assertTrue(all(id(slot.state) == identities[slot.index] for slot in optimizer.slots))
        self.assertTrue(all(slot.state.generation > 0 for slot in optimizer.slots))

    def test_p5_021_growth_windows_follow_128_physical_generations(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=256,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer(
            experiment=protocol,
            base_config=PhysicsConfig(max_cells=8),
        )
        candidate = make_slot(index=0, seed=0, generation=0)
        optimizer._evaluate_slot(candidate)
        self.assertEqual(candidate.physical_generations, 512)
        self.assertEqual(len(candidate.growth_windows), 4)
        self.assertIsNotNone(candidate.growth_reference)

    def test_p5_022_zero_median_growth_does_not_prune(self):
        records = [
            make_slot(
                index=index,
                seed=index,
                fitness=Fitness(),
                growth_windows=(0, 0, 0, 0),
            )
            for index in range(8)
        ]
        self.assertEqual(prune_candidates(records), set())

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
            make_slot(index=index, seed=index,
                      fitness=Fitness(1 if index == 0 else 0, 0, 0, index, index),
                      growth_windows=((0x0F, 0x0F, 0x0F, 0x0F)
                                      if index in (0, 4, 5, 6) else (0, 0, 0, 0)))
            for index in range(8)
        ]
        self.assertIn(0, protected_indices(records))
        self.assertNotIn(0, prune_candidates(records))
        self.assertIn(1, prune_candidates(records))

    def test_p5_005_real_slot_replacement_is_deterministic(self):
        self.assertEqual([seed_escalation(value) for value in (4, 8, 16, 32, 64)], [8, 16, 32, 32, 32])
        parent = make_slot(index=0, seed=41, growth_windows=(1,))
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=100)
        replacement = optimizer.replace_free_slot(free_index=12, parent=parent, direction=1)
        self.assertEqual(replacement.index, 12)
        self.assertEqual(replacement.category, parent.category)
        self.assertNotEqual(replacement.seed, parent.seed)
        self.assertEqual(replacement.state.generation, 0)
        self.assertEqual(replacement.allocation_reason, "mutation_child")
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

    def test_p5_009_repeated_evidence_uses_distinct_real_slots(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=100)
        parent = optimizer.slots[0]
        evidence = [optimizer.allocate_seed_slot(free_index=index, parent=parent)
                    for index in (8, 9, 10, 11)]
        self.assertEqual(len({slot.seed for slot in evidence}), 4)
        self.assertTrue(all(slot.genome == parent.genome for slot in evidence))
        self.assertTrue(all(slot.state.generation == 0 for slot in evidence))

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
        self.assertEqual(result["authoritative_slot_count"], 128)
        self.assertEqual(result["category_counts"], {
            "masked_copy": 32,
            "masked_xor": 32,
            "rotate_copy": 32,
            "masked_and": 32,
        })

    def test_p2g_optimizer_snapshot_roundtrip_preserves_bounded_state(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=100)
        optimizer.generation = 128
        payload = optimizer.to_snapshot()
        restored = SteadyStateOptimizer.from_snapshot(payload)
        self.assertEqual(restored.to_snapshot(), payload)
        self.assertEqual(payload["format_version"], 4)
        self.assertEqual(len(payload["slots"]), 128)
        self.assertTrue(all("state" in slot for slot in payload["slots"]))

    def test_p2g_growth_flags_include_retention_and_noise_robustness(self):
        before = Fitness(0, 4, 3, 8, 10, 0, 0)
        after = Fitness(1, 3, 2, 7, 9, 1, 1)
        self.assertEqual(growth_flags(before, after) & 0b1111111, 0b1111111)

    def test_p2g_pruning_uses_growth_bit_count_not_numeric_byte_sum(self):
        records = [
            make_slot(
                index=index,
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
            make_slot(
                index=index,
                category="masked_copy" if index < 8 else "masked_xor",
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

    def test_p5_011_integrated_optimizer_evaluates_128_without_forced_replacement(self):
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
            self.assertEqual(
                SteadyStateOptimizer._effective_config(
                    slot.genome,
                    category,
                    optimizer.base_config,
                ).latent_operator,
                category,
            )

        summary = optimizer.step()

        self.assertEqual(summary["evaluated_slots"], 128)
        self.assertEqual(summary["category_counts"], {
            "masked_copy": 32,
            "masked_xor": 32,
            "rotate_copy": 32,
            "masked_and": 32,
        })
        self.assertEqual(summary["cross_category_selection"], False)
        self.assertEqual(summary["replacement_count"], 0)
        self.assertFalse(any(slot.last_mutation_field for slot in optimizer.candidates))

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
        self.assertEqual(len(payload["slots"]), 128)
        self.assertEqual(payload["format_version"], 4)
        self.assertTrue(all("state" in slot for slot in payload["slots"]))
        self.assertTrue(all("training_states" not in slot for slot in payload["slots"]))

    def test_p5_023_headless_evidence_exposes_authoritative_metrics(self):
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
            iterations=4,
        )
        self.assertEqual(result["authoritative_slot_count"], 128)
        per_seed = result["candidate_measurement"]["per_seed"]
        self.assertTrue(per_seed)
        self.assertTrue({
            "wrong_output_count",
            "timed_out",
            "response_latency",
            "activity_cost",
        } <= set(per_seed[0]))

    def test_p5_013_headless_reports_integrated_search_without_forced_replacement(self):
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
            iterations=4,
        )
        self.assertEqual(result["population_size"], 128)
        self.assertEqual(result["optimizer_iterations"], 4)
        self.assertEqual(result["category_counts"], {
            "masked_copy": 32,
            "masked_xor": 32,
            "rotate_copy": 32,
            "masked_and": 32,
        })
        self.assertEqual(result["replacement_count"], 0)
        self.assertEqual(result["mutation_fields"], [])
        self.assertEqual(result["authoritative_slot_count"], 128)
        self.assertTrue(result["group_counts"])

    def test_p5_014_integrated_loop_does_not_prune_before_physical_window(self):
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
        self.assertEqual(summary["pruned_count"], 0)
        self.assertFalse(any(item["reason"] == "growth_pruned" for item in summary["replacements"]))
        self.assertTrue(all(not slot.growth_windows for slot in optimizer.candidates))

    def test_p5_024_initial_population_has_128_authoritative_universe_slots(self):
        self.assertTrue(hasattr(evolution_module, "UniverseSlot"))
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=105)
        slots = optimizer.slots

        self.assertEqual(len(slots), 128)
        self.assertTrue(all(isinstance(slot.state, UniverseState) for slot in slots))
        self.assertEqual(len({id(slot.state) for slot in slots}), 128)
        self.assertEqual({slot.state.generation for slot in slots}, {0})
        self.assertFalse(any(hasattr(slot, "training_states") for slot in slots))

    def test_p5_025_optimizer_steps_continue_authoritative_slot_state(self):
        self.assertTrue(hasattr(evolution_module, "UniverseSlot"))
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=8,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=106,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        identities = {slot.index: id(slot.state) for slot in optimizer.slots}
        summary = optimizer.step()
        replaced = {item["index"] for item in summary["replacements"]}

        self.assertTrue(all(
            id(slot.state) == identities[slot.index]
            for slot in optimizer.slots
            if slot.index not in replaced
        ))
        self.assertTrue(all(
            slot.state.generation > 0
            for slot in optimizer.slots
            if slot.index not in replaced
        ))
        self.assertTrue(all(slot.physical_generations == slot.state.generation for slot in optimizer.slots))

    def test_p5_026_same_genome_evidence_allocates_a_fresh_universe_slot(self):
        self.assertTrue(hasattr(SteadyStateOptimizer, "allocate_seed_slot"))
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=107)
        parent = next(slot for slot in optimizer.slots if slot.category == "masked_copy")
        allocated = optimizer.allocate_seed_slot(free_index=31, parent=parent)

        self.assertEqual(allocated.category, parent.category)
        self.assertEqual(allocated.genome, parent.genome)
        self.assertNotEqual(allocated.seed, parent.seed)
        self.assertEqual(allocated.state.generation, 0)
        self.assertIsNot(allocated.state, parent.state)
        self.assertEqual(allocated.allocation_reason, "seed_evidence")

    def test_p5_027_snapshot_contains_one_authoritative_state_per_slot(self):
        self.assertTrue(hasattr(SteadyStateOptimizer, "from_snapshot"))
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=108)
        payload = optimizer.to_snapshot()

        self.assertEqual(payload["format_version"], 4)
        self.assertEqual(len(payload["slots"]), 128)
        self.assertTrue(all("state" in record for record in payload["slots"]))
        self.assertTrue(all("training_states" not in record for record in payload["slots"]))

    def test_p5_028_promising_policy_is_not_fixed_without_approval(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=109)
        self.assertIsNone(optimizer.promising_policy)

    def test_p5_029_group_fitness_uses_all_real_seed_slots_for_parent_selection(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=110)
        local = [slot for slot in optimizer.slots if slot.category == "masked_copy"]
        genome_a = UniverseGenome.initial_population()[0]
        genome_b = UniverseGenome.initial_population()[1]
        group_a = [slot for slot in local if slot.genome == genome_a]
        group_b = [slot for slot in local if slot.genome == genome_b]
        group_a[0].fitness = Fitness(success=1)
        for slot in group_a[1:]:
            slot.fitness = Fitness()
        for slot in group_b:
            slot.fitness = Fitness(success=0.5)

        aggregate = optimizer.group_fitnesses()
        self.assertEqual(aggregate[group_a[0].evidence_group].success, 0.25)
        self.assertEqual(aggregate[group_b[0].evidence_group].success, 0.5)
        parent = optimizer._select_parent(local, excluded_index=31)
        self.assertEqual(parent.genome, genome_b)

        parent = local[0]
        allocated = optimizer.allocate_seed_slot(free_index=31, parent=parent)
        optimizer.slots[31] = allocated
        group_key = f"{parent.category}:{parent.genome_key}"
        self.assertEqual(optimizer.group_counts()[group_key], 5)
        restored = SteadyStateOptimizer.from_snapshot(optimizer.to_snapshot())
        self.assertIsNone(restored.promising_policy)
        self.assertEqual(restored.group_counts()[group_key], 5)

    def test_p5_030_snapshot_rejects_metadata_config_mismatch(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=111)
        payload = optimizer.to_snapshot()
        payload["slots"][0]["genome"]["hp_decay"] = 2
        with self.assertRaises(ValueError):
            SteadyStateOptimizer.from_snapshot(payload)

    def test_p5_031_one_seed_mutation_child_is_not_selection_eligible(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=112)
        local = [slot for slot in optimizer.slots if slot.category == "masked_copy"]
        parent = local[0]
        child = optimizer.replace_free_slot(
            free_index=31,
            parent=parent,
            direction=-1,
            field="hp_decay",
        )
        optimizer.slots[31] = child
        child.fitness = Fitness(success=1)

        local = [slot for slot in optimizer.slots if slot.category == "masked_copy"]
        self.assertNotIn(31, optimizer._protected_indices(local))
        selected = optimizer._select_parent(local, excluded_index=30)
        self.assertNotEqual(selected.index, 31)

    def test_p5_032_incomplete_mutation_child_group_is_completed_from_pruned_slot(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=113,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        local = [slot for slot in optimizer.slots if slot.category == "masked_copy"]
        parent = local[0]
        child = optimizer.replace_free_slot(
            free_index=31,
            parent=parent,
            direction=-1,
            field="hp_decay",
        )
        optimizer.slots[31] = child
        for slot in optimizer.slots:
            if slot.category == "masked_copy":
                slot.growth_windows = (0x0F, 0x0F, 0x0F, 0x0F)
        optimizer.slots[0].growth_windows = (0, 0, 0, 0)

        summary = optimizer.step()
        replacement = next(item for item in summary["replacements"] if item["index"] == 0)

        self.assertEqual(replacement["allocation_reason"], "seed_evidence")
        self.assertEqual(replacement["parent_index"], 31)
        self.assertIsNone(replacement["mutation_field"])
        self.assertEqual(replacement["group_count"], 2)

    def test_p5_033_incomplete_mutation_child_is_not_pruned_before_minimum_evidence(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=114,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        parent = next(slot for slot in optimizer.slots if slot.category == "masked_copy")
        child = optimizer.replace_free_slot(
            free_index=31,
            parent=parent,
            direction=-1,
            field="hp_decay",
        )
        optimizer.slots[31] = child
        for slot in optimizer.slots:
            if slot.category == "masked_copy":
                slot.growth_windows = (0x0F, 0x0F, 0x0F, 0x0F)
        child.growth_windows = (0, 0, 0, 0)

        summary = optimizer.step()

        self.assertEqual(summary["replacement_count"], 0)
        self.assertIs(optimizer.slots[31], child)


if __name__ == "__main__":
    unittest.main()
