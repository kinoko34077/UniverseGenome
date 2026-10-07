from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import experiment as experiment_module
from core.experiment import (
    ByteMapping,
    ByteSequenceMapping,
    EvaluationResult,
    ExperimentConfig,
    IOExperiment,
    LearningMeasurement,
    MappingSeedMeasurement,
    SeedMeasurement,
    compare_baseline_trained,
    load_experiment_config,
    measure_trained_state,
)
from core.io_bus import OutputEvent, OutputSignal
from core.population import run_population_headless
from core.physics import PhysicsConfig, StepMetrics, create_universe
from core.runner import build_status, load_config, main as runner_main
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
from search.pruning import (
    GROWTH_BIT_NOISE_ROBUSTNESS,
    GROWTH_BIT_RETENTION,
    GrowthHistory,
    absolute_failure_reason,
    growth_flags,
    prune_candidates,
    protected_indices,
    short_health_flags,
)


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
        self.assertEqual(fitness.retention, 0.0)
        self.assertEqual(fitness.noise_robustness, 0.0)
        self.assertEqual(fitness.counterfactual_no_input_clean, 1.0)
        self.assertEqual(fitness.counterfactual_alternate_input_clean, 1.0)
        self.assertTrue(
            SteadyStateOptimizer._measurement_has_autonomous_response(measurement)
        )
        self.assertEqual(growth_flags(Fitness(), fitness) & ((1 << 5) | (1 << 6)), 0)
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
        self.assertEqual(status["next_phase"], "Phase 6+ roadmap review (explicit next capability decision required)")
        self.assertTrue(raw["features"]["multi_universe_search"])
        self.assertTrue(raw["features"]["evolution"])
        self.assertTrue(raw["features"]["phase6_capabilities"])
        self.assertTrue(raw["features"]["phase6_multi_mapping"])
        self.assertTrue(raw["features"]["phase6_retention_relearning"])
        self.assertTrue(raw["features"]["phase6_noise_robustness"])
        self.assertTrue(raw["features"]["phase6_generalization"])
        self.assertTrue(raw["features"]["phase6_multi_byte_sequences"])
        self.assertTrue(raw["features"]["phase6_raw_utf8"])
        self.assertTrue(raw["features"]["phase6_mixed_length_sequences"])
        self.assertTrue(status["phase6_raw_utf8_implemented"])
        self.assertTrue(status["phase6_mixed_length_sequences_implemented"])
        with (ROOT / "config" / "experiment_v0_1.json").open(encoding="utf-8") as handle:
            experiment = json.load(handle)
        self.assertEqual(experiment["learning_claim"], False)
        handoff = (ROOT / "docs" / "PHASE6_HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("P6.1 through P6.9 accepted", handoff)
        self.assertIn("No automatic P6.10 is authorized", handoff)

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
        self.assertEqual(payload["format_version"], 7)
        self.assertEqual(len(payload["slots"]), 128)
        self.assertTrue(all("state" in slot for slot in payload["slots"]))

    def test_p2g_growth_flags_include_retention_and_noise_robustness(self):
        before = Fitness(
            success=0,
            wrong_outputs=4,
            timeouts=3,
            response_latency=8,
            activity_cost=10,
            retention=0,
            noise_robustness=0,
            retention_evidence_count=1,
            noise_robustness_evidence_count=1,
        )
        after = Fitness(
            success=1,
            wrong_outputs=3,
            timeouts=2,
            response_latency=7,
            activity_cost=9,
            retention=1,
            noise_robustness=1,
            retention_evidence_count=1,
            noise_robustness_evidence_count=1,
        )
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
        self.assertEqual(payload["format_version"], 7)
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
        self.assertEqual(result["promising_policy"], "tiered_category_rank")

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

        self.assertEqual(payload["format_version"], 7)
        self.assertEqual(len(payload["slots"]), 128)
        self.assertTrue(all("state" in record for record in payload["slots"]))
        self.assertTrue(all("training_states" not in record for record in payload["slots"]))

    def test_p5_028_promising_policy_defaults_to_approved_tiered_category_rank(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=109)
        self.assertEqual(optimizer.promising_policy, "tiered_category_rank")
        restored = SteadyStateOptimizer.from_snapshot(optimizer.to_snapshot())
        self.assertEqual(restored.promising_policy, "tiered_category_rank")

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
        self.assertEqual(restored.promising_policy, "tiered_category_rank")
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


    def test_p5_034_initial_groups_are_mature_and_mutation_groups_start_provisional(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=115)
        initial = [
            slot for slot in optimizer.slots
            if slot.category == "masked_copy"
            and slot.genome == UniverseGenome.initial_population()[0]
        ]
        self.assertEqual(len(initial), 4)
        self.assertTrue(all(slot.evidence_mature for slot in initial))

        child = optimizer.replace_free_slot(
            free_index=31,
            parent=initial[0],
            direction=-1,
            field="hp_decay",
        )
        self.assertFalse(child.evidence_mature)

    def test_p5_035_mutation_group_becomes_mature_at_four_real_seed_slots(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=116)
        parent = next(slot for slot in optimizer.slots if slot.category == "masked_copy")
        child = optimizer.replace_free_slot(
            free_index=31,
            parent=parent,
            direction=-1,
            field="hp_decay",
        )
        optimizer.slots[31] = child
        evidence_slots = [child]
        for free_index in (30, 29, 28):
            evidence = optimizer.allocate_seed_slot(
                free_index=free_index,
                parent=child,
            )
            optimizer.slots[free_index] = evidence
            evidence_slots.append(evidence)
            optimizer._refresh_evidence_maturity(child.evidence_group)

        self.assertEqual(len(evidence_slots), 4)
        self.assertTrue(all(slot.evidence_mature for slot in evidence_slots))
        self.assertTrue(all(
            slot.index in {
                candidate.index
                for candidate in optimizer._selection_eligible_slots(
                    [item for item in optimizer.slots if item.category == "masked_copy"]
                )
            }
            for slot in evidence_slots
        ))

    def test_p5_036_depleted_mature_group_stays_prunable_but_not_selectable(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=117)
        genome = UniverseGenome.initial_population()[0]
        original = [
            slot for slot in optimizer.slots
            if slot.category == "masked_copy" and slot.genome == genome
        ]
        self.assertEqual(len(original), 4)
        victim = original[-1]
        child = optimizer.replace_free_slot(
            free_index=victim.index,
            parent=next(
                slot for slot in optimizer.slots
                if slot.category == "masked_copy" and slot.genome != genome
            ),
            direction=1,
            field="hp_decay",
        )
        optimizer.slots[victim.index] = child

        local = [slot for slot in optimizer.slots if slot.category == "masked_copy"]
        remaining = [slot for slot in local if slot.genome == genome]
        self.assertEqual(len(remaining), 3)
        self.assertTrue(all(slot.evidence_mature for slot in remaining))

        selection_indices = {
            slot.index for slot in optimizer._selection_eligible_slots(local)
        }
        pruning_indices = {
            slot.index for slot in optimizer._pruning_eligible_slots(local)
        }
        self.assertTrue(all(slot.index not in selection_indices for slot in remaining))
        self.assertTrue(all(slot.index in pruning_indices for slot in remaining))
        self.assertNotIn(child.index, pruning_indices)

    def test_p5_037_evidence_maturity_roundtrips_in_snapshot(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=118)
        parent = next(slot for slot in optimizer.slots if slot.category == "masked_copy")
        child = optimizer.replace_free_slot(
            free_index=31,
            parent=parent,
            direction=-1,
            field="hp_decay",
        )
        optimizer.slots[31] = child

        payload = optimizer.to_snapshot()
        restored = SteadyStateOptimizer.from_snapshot(payload)

        self.assertTrue(restored.slots[parent.index].evidence_mature)
        self.assertFalse(restored.slots[31].evidence_mature)
        self.assertEqual(restored.to_snapshot(), payload)


    def test_p5_038_depleted_mature_mutation_group_is_not_treated_as_provisional(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=119)
        local = [slot for slot in optimizer.slots if slot.category == "masked_copy"]
        parent = local[0]
        child = optimizer.replace_free_slot(
            free_index=31,
            parent=parent,
            direction=-1,
            field="hp_decay",
        )
        optimizer.slots[31] = child
        mutation_group = [child]
        for free_index in (30, 29, 28):
            evidence = optimizer.allocate_seed_slot(
                free_index=free_index,
                parent=child,
            )
            optimizer.slots[free_index] = evidence
            mutation_group.append(evidence)
            optimizer._refresh_evidence_maturity(child.evidence_group)

        self.assertTrue(all(slot.evidence_mature for slot in mutation_group))

        optimizer.slots[28] = optimizer.allocate_seed_slot(
            free_index=28,
            parent=next(
                slot for slot in local
                if slot.genome != parent.genome
            ),
        )
        local = [slot for slot in optimizer.slots if slot.category == "masked_copy"]
        remaining = [slot for slot in local if slot.evidence_group == child.evidence_group]
        self.assertEqual(len(remaining), 3)
        self.assertTrue(all(slot.evidence_mature for slot in remaining))
        self.assertIsNone(
            optimizer._incomplete_mutation_parent(
                local,
                excluded_index=0,
            )
        )


    def test_p5_039_snapshot_rejects_inconsistent_evidence_maturity(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=120)
        payload = optimizer.to_snapshot()
        first_group = [
            record for record in payload["slots"]
            if record["category"] == "masked_copy"
            and record["genome"] == UniverseGenome.initial_population()[0].to_dict()
        ]
        self.assertEqual(len(first_group), 4)
        first_group[0]["evidence_mature"] = False

        with self.assertRaises(ValueError):
            SteadyStateOptimizer.from_snapshot(payload)


    def test_p5_040_depleted_mature_group_can_continue_retirement(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=121,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        genome = UniverseGenome.initial_population()[0]
        target_group = [
            slot for slot in optimizer.slots
            if slot.category == "masked_copy" and slot.genome == genome
        ]
        victim = target_group[-1]
        parent = next(
            slot for slot in optimizer.slots
            if slot.category == "masked_copy" and slot.genome != genome
        )
        optimizer.slots[victim.index] = optimizer.replace_free_slot(
            free_index=victim.index,
            parent=parent,
            direction=1,
            field="hp_decay",
        )

        local = [slot for slot in optimizer.slots if slot.category == "masked_copy"]
        remaining = [slot for slot in local if slot.genome == genome]
        self.assertEqual(len(remaining), 3)
        self.assertTrue(all(slot.evidence_mature for slot in remaining))

        for slot in local:
            if slot.evidence_mature:
                slot.growth_windows = (0x0F, 0x0F, 0x0F, 0x0F)
        for slot in remaining:
            slot.growth_windows = (0, 0, 0, 0)

        summary = optimizer.step()
        replaced_indices = {item["index"] for item in summary["replacements"]}
        self.assertTrue(replaced_indices & {slot.index for slot in remaining})
        surviving = [
            slot for slot in optimizer.slots
            if slot.category == "masked_copy" and slot.genome == genome
        ]
        self.assertLess(len(surviving), 3)

    def test_p5_041_growth_bits_keep_canonical_retention_and_noise_names(self):
        before = Fitness(
            retention=0,
            noise_robustness=0,
            retention_evidence_count=1,
            noise_robustness_evidence_count=1,
        )
        no_input_after = Fitness(
            retention=1,
            noise_robustness=0,
            retention_evidence_count=1,
            noise_robustness_evidence_count=1,
        )
        alternate_after = Fitness(
            retention=0,
            noise_robustness=1,
            retention_evidence_count=1,
            noise_robustness_evidence_count=1,
        )

        self.assertFalse(hasattr(before, "trained_no_input_clean"))
        self.assertFalse(hasattr(before, "trained_alternate_input_clean"))
        self.assertEqual(
            growth_flags(before, no_input_after),
            1 << GROWTH_BIT_RETENTION,
        )
        self.assertEqual(
            growth_flags(before, alternate_after),
            1 << GROWTH_BIT_NOISE_ROBUSTNESS,
        )

    def test_p5_042_short_health_runs_at_authoritative_16_generation_boundaries(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=16,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=122,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        slot = optimizer.slots[0]
        for cell in tuple(slot.state.active_slots()):
            slot.state.free(cell)

        optimizer._evaluate_slot(slot)

        self.assertEqual(slot.physical_generations, 32)
        self.assertEqual(slot.short_health_windows, (0, 0))
        self.assertTrue(slot.absolute_failure)
        self.assertEqual(slot.absolute_failure_reason, "all_active_cells_gone")

    def test_p5_043_persistent_non_response_requires_four_128_generation_response_windows(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=123)
        slot = optimizer.slots[0]
        self.assertTrue(tuple(slot.state.active_slots()))
        slot.short_health_windows = (
            short_health_flags(active_cells=1, activity_cost=0),
        )

        for _ in range(3):
            optimizer._record_response_observation(slot, responded=False)
            self.assertFalse(slot.absolute_failure)

        optimizer._record_response_observation(slot, responded=True)
        self.assertFalse(slot.absolute_failure)
        self.assertEqual(slot.response_windows, (0, 0, 0, 1))

        for _ in range(3):
            optimizer._record_response_observation(slot, responded=False)
            self.assertFalse(slot.absolute_failure)

        optimizer._record_response_observation(slot, responded=False)
        self.assertTrue(slot.absolute_failure)
        self.assertEqual(slot.absolute_failure_reason, "persistent_non_response")
        self.assertEqual(slot.response_windows, (0, 0, 0, 0))

        restored = SteadyStateOptimizer.from_snapshot(optimizer.to_snapshot())
        restored_slot = restored.slots[slot.index]
        self.assertEqual(restored_slot.response_windows, (0, 0, 0, 0))
        self.assertTrue(restored_slot.absolute_failure)
        self.assertEqual(
            restored_slot.absolute_failure_reason,
            "persistent_non_response",
        )


    def test_p5_044_absolute_failure_is_prunable_without_growth_or_maturity(self):
        record = make_slot(index=7, seed=7)
        record.absolute_failure = True
        record.absolute_failure_reason = "all_active_cells_gone"

        self.assertIn(7, prune_candidates([record], protected={7}))

    def test_p5_045_mutation_directions_respect_effective_max_cells(self):
        base = PhysicsConfig(max_cells=8)
        upper = UniverseGenome(initial_density=8)
        lower = UniverseGenome(initial_density=0)

        self.assertEqual(
            upper.mutation_directions("initial_density", base=base),
            (-1,),
        )
        self.assertEqual(
            lower.mutation_directions("initial_density", base=base),
            (1,),
        )
        self.assertEqual(
            upper.mutate("initial_density", direction=-1, base=base).initial_density,
            4,
        )
        with self.assertRaises(ValueError):
            upper.mutate("initial_density", direction=1, base=base)

    def test_p5_046_integrated_mutation_flips_from_an_invalid_upper_direction(self):
        base = PhysicsConfig(max_cells=8)
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=124,
            base_config=base,
        )
        genome = UniverseGenome(initial_density=8)
        config = SteadyStateOptimizer._effective_config(
            genome,
            "masked_copy",
            base,
        )
        parent = UniverseSlot(
            index=0,
            category="masked_copy",
            genome=genome,
            seed=999,
            state=create_universe(seed=999, config=config),
            evidence_mature=True,
        )

        child = optimizer.replace_free_slot(
            free_index=31,
            parent=parent,
            direction=1,
            field="initial_density",
        )

        self.assertEqual(child.genome.initial_density, 4)
        self.assertNotEqual(child.genome, parent.genome)
        child.genome.to_physics_config(base)

    def test_p5_047_short_health_uses_window_activity_and_roundtrips(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=125)
        slot = optimizer.slots[0]
        active_metrics = StepMetrics(
            generation=1,
            active_cells=1,
            collision_count=1,
            collision_pair_evaluations=1,
            bond_contact_count=0,
            latent_transmission_count=0,
            fusion_count=0,
            fragmentation_count=0,
            noise_spawn_count=0,
            generations_per_second=1.0,
        )
        boundary_metrics = StepMetrics(
            generation=16,
            active_cells=1,
            collision_count=0,
            collision_pair_evaluations=0,
            bond_contact_count=0,
            latent_transmission_count=0,
            fusion_count=0,
            fragmentation_count=0,
            noise_spawn_count=0,
            generations_per_second=1.0,
        )

        optimizer._record_short_health_step(slot, 1, active_metrics)
        optimizer._record_short_health_step(slot, 16, boundary_metrics)

        self.assertEqual(slot.short_health_windows, (3,))
        self.assertEqual(slot.short_health_activity_cost, 0)
        self.assertFalse(slot.absolute_failure)

        slot.short_health_activity_cost = 2
        payload = optimizer.to_snapshot()
        restored = SteadyStateOptimizer.from_snapshot(payload)
        self.assertEqual(restored.slots[0].short_health_windows, (3,))
        self.assertEqual(restored.slots[0].short_health_activity_cost, 2)
        self.assertEqual(restored.to_snapshot(), payload)


    def test_p5_048_tiered_category_rank_uses_group_rank_and_real_seed_tiers(self):
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=126,
            promising_policy="tiered_category_rank",
        )
        genomes = UniverseGenome.initial_population()

        four_seed_local = []
        index = 0
        for rank, genome in enumerate(genomes):
            for _ in range(4):
                slot = make_slot(
                    index=index,
                    seed=2000 + index,
                    genome=genome,
                    fitness=Fitness(success=float(len(genomes) - rank)),
                )
                slot.evidence_mature = True
                four_seed_local.append(slot)
                index += 1

        self.assertTrue(optimizer._is_promising(four_seed_local[0], four_seed_local))
        self.assertTrue(optimizer._is_promising(four_seed_local[12], four_seed_local))
        self.assertFalse(optimizer._is_promising(four_seed_local[16], four_seed_local))

        eight_seed_local = []
        index = 0
        for rank, genome in enumerate(genomes[:4]):
            for _ in range(8):
                slot = make_slot(
                    index=index,
                    seed=3000 + index,
                    genome=genome,
                    fitness=Fitness(success=float(4 - rank)),
                )
                slot.evidence_mature = True
                eight_seed_local.append(slot)
                index += 1

        self.assertTrue(optimizer._is_promising(eight_seed_local[0], eight_seed_local))
        self.assertFalse(optimizer._is_promising(eight_seed_local[8], eight_seed_local))

        full_group = [
            make_slot(
                index=index,
                seed=4000 + index,
                genome=genomes[0],
                fitness=Fitness(success=1),
            )
            for index in range(32)
        ]
        for slot in full_group:
            slot.evidence_mature = True
        self.assertFalse(optimizer._is_promising(full_group[0], full_group))

    def test_p5_049_promising_parent_prefers_lower_evidence_count_before_fitness(self):
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=127,
            promising_policy="tiered_category_rank",
        )
        genomes = UniverseGenome.initial_population()
        local = []
        index = 0
        group_specs = (
            (genomes[0], 4, 0.8),
            (genomes[1], 7, 0.9),
            (genomes[2], 4, 0.2),
            (genomes[3], 4, 0.1),
        )
        for genome, count, success in group_specs:
            for _ in range(count):
                slot = make_slot(
                    index=index,
                    seed=5000 + index,
                    genome=genome,
                    fitness=Fitness(success=success),
                )
                slot.evidence_mature = True
                local.append(slot)
                index += 1

        selected = optimizer._select_promising_parent(local)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.genome, genomes[0])

    def test_p5_050_promising_and_mutation_allocation_alternate_per_category(self):
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=128,
            promising_policy="tiered_category_rank",
        )

        self.assertEqual(
            optimizer._next_allocation_mode("masked_copy", promising_available=False),
            "mutation_child",
        )
        self.assertEqual(
            optimizer._next_allocation_mode("masked_copy", promising_available=True),
            "seed_evidence",
        )
        self.assertEqual(
            optimizer._next_allocation_mode("masked_copy", promising_available=True),
            "mutation_child",
        )
        self.assertEqual(
            optimizer._next_allocation_mode("masked_xor", promising_available=True),
            "seed_evidence",
        )

        restored = SteadyStateOptimizer.from_snapshot(optimizer.to_snapshot())
        self.assertEqual(
            restored._next_allocation_mode("masked_copy", promising_available=True),
            "seed_evidence",
        )
        self.assertEqual(
            restored._next_allocation_mode("masked_xor", promising_available=True),
            "mutation_child",
        )


    def test_p5_051_optimizer_cli_preserves_canonical_protocol_unless_override_is_explicit(self):
        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--json",
                    ]),
                    0,
                )
        default_payload = json.loads(stdout.getvalue())
        self.assertEqual(captured[-1].evaluation_timeout_generations, 1024)
        self.assertEqual(
            default_payload["optimizer_protocol"]["mode"],
            "canonical",
        )
        self.assertEqual(
            default_payload["optimizer_protocol"]["evaluation_timeout_generations"],
            1024,
        )

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--optimizer-timeout-generations",
                        "8",
                        "--json",
                    ]),
                    0,
                )
        smoke_payload = json.loads(stdout.getvalue())
        self.assertEqual(captured[-1].evaluation_timeout_generations, 8)
        self.assertEqual(
            smoke_payload["optimizer_protocol"]["mode"],
            "explicit_timeout_override",
        )
        self.assertEqual(
            smoke_payload["optimizer_protocol"]["evaluation_timeout_generations"],
            8,
        )


    def test_p5_052_post_initial_seed_evidence_prefers_cross_category_match_when_practical(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=200)
        genome = UniverseGenome.initial_population()[0]
        copy_parent = next(
            slot
            for slot in optimizer.slots
            if slot.category == "masked_copy" and slot.genome == genome
        )
        xor_parent = next(
            slot
            for slot in optimizer.slots
            if slot.category == "masked_xor" and slot.genome == genome
        )

        copy_evidence = optimizer.allocate_seed_slot(
            free_index=31,
            parent=copy_parent,
        )
        optimizer.slots[31] = copy_evidence

        xor_evidence = optimizer.allocate_seed_slot(
            free_index=63,
            parent=xor_parent,
        )

        self.assertEqual(copy_evidence.seed, 232)
        self.assertEqual(xor_evidence.seed, copy_evidence.seed)
        self.assertEqual(xor_evidence.genome, genome)
        self.assertEqual(xor_evidence.category, "masked_xor")


    def test_p5_053_parent_genome_reference_is_durable_across_slot_reuse_and_snapshot(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=201)
        parent = optimizer.slots[0]
        expected_parent_genome_key = parent.genome_key

        child = optimizer.replace_free_slot(
            free_index=31,
            parent=parent,
            direction=1,
            field="hp_decay",
        )
        optimizer.slots[31] = child
        optimizer._refresh_evidence_maturity(child.evidence_group)
        self.assertEqual(child.parent_genome_key, expected_parent_genome_key)
        self.assertEqual(child.parent_index, parent.index)

        other_parent = optimizer.slots[4]
        replacement = optimizer.replace_free_slot(
            free_index=parent.index,
            parent=other_parent,
            direction=1,
            field="hp_decay",
        )
        optimizer.slots[parent.index] = replacement
        optimizer._refresh_evidence_maturity(replacement.evidence_group)
        self.assertNotEqual(
            optimizer.slots[parent.index].genome_key,
            expected_parent_genome_key,
        )

        payload = optimizer.to_snapshot()
        self.assertEqual(payload["format_version"], 7)
        restored = SteadyStateOptimizer.from_snapshot(payload)
        self.assertEqual(
            restored.slots[31].parent_genome_key,
            expected_parent_genome_key,
        )

    def test_p5_054_prune_history_records_actual_retirement_and_roundtrips(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=202,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        target = optimizer.slots[0]
        retired = {
            "index": target.index,
            "category": target.category,
            "genome_key": target.genome_key,
            "seed": target.seed,
        }
        target.absolute_failure = True
        target.absolute_failure_reason = "all_active_cells_gone"

        summary = optimizer.step()

        self.assertEqual(summary["replacement_count"], 1)
        self.assertEqual(len(optimizer.prune_history), 1)
        event = optimizer.prune_history[0]
        self.assertEqual(event["optimizer_generation"], 1)
        self.assertEqual(event["index"], retired["index"])
        self.assertEqual(event["category"], retired["category"])
        self.assertEqual(event["genome_key"], retired["genome_key"])
        self.assertEqual(event["seed"], retired["seed"])
        self.assertEqual(event["retirement_reason"], "all_active_cells_gone")

        payload = optimizer.to_snapshot()
        self.assertEqual(payload["prune_history"], optimizer.prune_history)
        restored = SteadyStateOptimizer.from_snapshot(payload)
        self.assertEqual(restored.prune_history, optimizer.prune_history)
        self.assertEqual(restored.to_snapshot(), payload)

    def test_p5_055_snapshot_v4_restores_without_new_lineage_history_fields(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=203)
        payload = optimizer.to_snapshot()
        payload["format_version"] = 4
        payload.pop("outer_search", None)
        payload.pop("prune_history", None)
        for slot in payload["slots"]:
            slot.pop("parent_genome_key", None)

        restored = SteadyStateOptimizer.from_snapshot(payload)

        self.assertEqual(restored.prune_history, [])
        self.assertTrue(
            all(slot.parent_genome_key is None for slot in restored.slots)
        )
        self.assertEqual(restored.to_snapshot()["format_version"], 7)


    def test_p5_056_snapshot_v5_rejects_missing_durable_parent_genome_key_for_child(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=204)
        parent = optimizer.slots[0]
        child = optimizer.replace_free_slot(
            free_index=31,
            parent=parent,
            direction=1,
            field="hp_decay",
        )
        optimizer.slots[31] = child
        optimizer._refresh_evidence_maturity(child.evidence_group)

        payload = optimizer.to_snapshot()
        payload["format_version"] = 5
        payload.pop("outer_search", None)
        self.assertEqual(payload["format_version"], 5)
        child_payload = payload["slots"][31]
        self.assertEqual(child_payload["allocation_reason"], "mutation_child")
        child_payload.pop("parent_genome_key")

        with self.assertRaises(ValueError):
            SteadyStateOptimizer.from_snapshot(payload)


    def test_p6_005_phase5_fitness_consumes_all_mapping_evaluations(self):
        clean = EvaluationResult(
            expected_events=(OutputEvent.byte(66), OutputEvent.null()),
            autonomous_events=(),
            success=False,
            clone_generation=0,
            event_generations=(),
            evaluation_generations=1,
            activity_cost=2,
            timed_out=True,
        )
        wrong = EvaluationResult(
            expected_events=(OutputEvent.byte(68), OutputEvent.null()),
            autonomous_events=(OutputEvent.byte(66),),
            success=False,
            clone_generation=0,
            event_generations=(1,),
            evaluation_generations=1,
            activity_cost=6,
            timed_out=True,
        )
        seed_record = SimpleNamespace(
            trained=clean,
            mapping_results=(
                SimpleNamespace(trained=clean),
                SimpleNamespace(trained=wrong),
            ),
        )
        measurement = SimpleNamespace(
            seed_count=1,
            mapping_count=2,
            evaluation_case_count=2,
            trained_successes=0,
            trained_no_input_clean=1,
            trained_alternate_input_clean=1,
            no_input_clean=1,
            alternate_input_clean=1,
            per_seed=(seed_record,),
        )

        fitness = SteadyStateOptimizer._fitness_from_measurement(measurement)

        self.assertEqual(fitness.success, 0.0)
        self.assertEqual(fitness.wrong_outputs, 0.5)
        self.assertEqual(fitness.timeouts, 1.0)
        self.assertEqual(fitness.activity_cost, 4.0)


    def test_p6_007_phase5_authoritative_training_uses_all_declared_mappings(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
            mappings=(
                ByteMapping(65, 66),
                ByteMapping(67, 68),
            ),
            counterfactual_input_byte=66,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=305,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        slot = optimizer.slots[0]

        measurement = optimizer._evaluate_slot(slot)

        self.assertEqual(slot.state.generation, 6)
        self.assertEqual(measurement.mapping_count, 2)
        self.assertEqual(len(measurement.per_seed[0].mapping_results), 2)


    def test_p6_008_optimizer_snapshot_roundtrips_multi_mapping_protocol(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=2,
            mappings=(
                ByteMapping(65, 66),
                ByteMapping(67, 68),
            ),
            counterfactual_input_byte=66,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=306,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )

        payload = optimizer.to_snapshot()
        restored = SteadyStateOptimizer.from_snapshot(payload)

        self.assertEqual(restored.experiment, protocol)
        self.assertEqual(
            payload["experiment"]["mappings"],
            [
                {"input_byte": 65, "output_byte": 66},
                {"input_byte": 67, "output_byte": 68},
            ],
        )
        self.assertEqual(restored.to_snapshot(), payload)

    def test_p6_009_optimizer_timeout_override_preserves_mapping_protocol(self):
        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--experiment-config",
                        "config/experiment_phase6_multi_mapping_smoke.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--optimizer-timeout-generations",
                        "1",
                        "--json",
                    ]),
                    0,
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(captured[-1].evaluation_timeout_generations, 1)
        self.assertEqual(
            [(item.input_byte, item.output_byte) for item in captured[-1].mappings],
            [(65, 66), (67, 68)],
        )
        self.assertEqual(payload["optimizer_protocol"]["mapping_count"], 2)
        self.assertEqual(
            payload["optimizer_protocol"]["mode"],
            "explicit_timeout_override",
        )


    def test_p62_005_optimizer_snapshot_roundtrips_sequence_protocol(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=1,
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            inter_input_generations=1,
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=405,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )

        payload = optimizer.to_snapshot()
        restored = SteadyStateOptimizer.from_snapshot(payload)

        self.assertEqual(restored.experiment, protocol)
        self.assertEqual(
            payload["experiment"]["mappings"],
            [
                {"input_bytes": [65, 65], "output_byte": 66},
                {"input_bytes": [65, 67], "output_byte": 68},
            ],
        )
        self.assertEqual(payload["experiment"]["inter_input_generations"], 1)
        self.assertEqual(payload["experiment"]["counterfactual_prefix"], [65])
        self.assertEqual(
            payload["experiment"]["counterfactual_input_sequence"],
            [67, 65],
        )

    def test_p62_006_optimizer_timeout_override_preserves_sequence_protocol(self):
        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--experiment-config",
                        "config/experiment_phase6_temporal_sequence_smoke.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--optimizer-timeout-generations",
                        "1",
                        "--json",
                    ]),
                    0,
                )

        protocol = captured[-1]
        payload = json.loads(stdout.getvalue())
        self.assertEqual(protocol.evaluation_timeout_generations, 1)
        self.assertEqual(
            [item.input_bytes for item in protocol.mappings],
            [(65, 65), (65, 67)],
        )
        self.assertEqual(protocol.inter_input_generations, 1)
        self.assertEqual(protocol.counterfactual_prefix, (65,))
        self.assertEqual(protocol.counterfactual_input_sequence, (67, 65))
        self.assertEqual(payload["optimizer_protocol"]["mapping_count"], 2)
        self.assertEqual(
            payload["optimizer_protocol"]["counterfactual_prefix"],
            [65],
        )
        self.assertEqual(
            payload["optimizer_protocol"]["counterfactual_input_sequence"],
            [67, 65],
        )

    def test_p62_007_runner_reports_sequence_results_and_controls(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(
                runner_main([
                    "--config",
                    "config/default.json",
                    "--experiment",
                    "--experiment-config",
                    "config/experiment_phase6_temporal_sequence_smoke.json",
                    "--json",
                ]),
                0,
            )

        payload = json.loads(stdout.getvalue())["experiment_measurement"]
        self.assertEqual(payload["mapping_count"], 2)
        self.assertEqual(payload["evaluation_case_count"], 6)
        self.assertEqual(
            [item["input_bytes"] for item in payload["per_mapping"]],
            [[65, 65], [65, 67]],
        )
        self.assertEqual(payload["counterfactual_prefix"], [65])
        self.assertEqual(payload["counterfactual_input_sequence"], [67, 65])
        self.assertEqual(payload["trained_prefix_input_clean"], 3)
        self.assertEqual(payload["trained_sequence_counterfactual_clean"], 3)
        self.assertFalse(payload["learning_claim"])




    def test_p63_005_optimizer_snapshot_roundtrips_multi_event_timing_protocol(self):
        protocol = load_experiment_config(
            ROOT / "config" / "experiment_phase6_multi_event_timing_smoke.json"
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=505,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )

        payload = optimizer.to_snapshot()
        restored = SteadyStateOptimizer.from_snapshot(payload)

        self.assertEqual(protocol.output_event_count, 2)
        self.assertEqual(protocol.output_event_interval_generations, 2)
        self.assertEqual(restored.experiment, protocol)
        self.assertEqual(payload["experiment"]["output_event_count"], 2)
        self.assertEqual(
            payload["experiment"]["output_event_interval_generations"],
            2,
        )

    def test_p63_006_optimizer_timeout_override_preserves_multi_event_timing(self):
        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--experiment-config",
                        "config/experiment_phase6_multi_event_timing_smoke.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--optimizer-timeout-generations",
                        "1",
                        "--json",
                    ]),
                    0,
                )

        protocol = captured[-1]
        payload = json.loads(stdout.getvalue())
        self.assertEqual(protocol.evaluation_timeout_generations, 1)
        self.assertEqual(protocol.output_event_count, 2)
        self.assertEqual(protocol.output_event_interval_generations, 2)
        self.assertEqual(payload["optimizer_protocol"]["output_event_count"], 2)
        self.assertEqual(
            payload["optimizer_protocol"]["output_event_interval_generations"],
            2,
        )

    def test_p63_007_runner_reports_per_seed_multi_event_timing_results(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(
                runner_main([
                    "--config",
                    "config/default.json",
                    "--experiment",
                    "--experiment-config",
                    "config/experiment_phase6_multi_event_timing_smoke.json",
                    "--json",
                ]),
                0,
            )

        payload = json.loads(stdout.getvalue())["experiment_measurement"]
        self.assertEqual(payload["mapping_count"], 2)
        self.assertEqual(payload["evaluation_case_count"], 6)
        self.assertEqual(payload["output_event_count"], 2)
        self.assertEqual(payload["output_event_interval_generations"], 2)
        self.assertEqual(len(payload["per_seed"]), 3)
        for seed_record in payload["per_seed"]:
            self.assertEqual(len(seed_record["mappings"]), 2)
            for mapping_record in seed_record["mappings"]:
                self.assertIn("baseline_success", mapping_record)
                self.assertIn("trained_success", mapping_record)
                self.assertIn("baseline_event_generations", mapping_record)
                self.assertIn("trained_event_generations", mapping_record)
                self.assertIsInstance(
                    mapping_record["baseline_event_generations"],
                    list,
                )
                self.assertIsInstance(
                    mapping_record["trained_event_generations"],
                    list,
                )
        self.assertFalse(payload["learning_claim"])


    def test_p64_001_retention_protocol_fields_roundtrip_without_changing_legacy_defaults(self):
        legacy = ExperimentConfig()
        self.assertEqual(legacy.retention_delay_generations, 0)
        self.assertEqual(legacy.retention_interference_repetitions, 0)
        self.assertEqual(legacy.relearning_teacher_repetitions, 0)

        protocol = ExperimentConfig(
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            retention_delay_generations=128,
            retention_interference_repetitions=1,
            relearning_teacher_repetitions=1,
        )
        restored = ExperimentConfig.from_mapping(protocol.to_dict())

        self.assertEqual(restored, protocol)
        self.assertEqual(restored.retention_delay_generations, 128)
        self.assertEqual(restored.retention_interference_repetitions, 1)
        self.assertEqual(restored.relearning_teacher_repetitions, 1)

    def test_p64_002_retention_rates_are_none_without_eligible_cases(self):
        base = dict(
            seed_count=1,
            baseline_successes=0,
            trained_successes=0,
            baseline_no_input_clean=1,
            trained_no_input_clean=1,
            baseline_alternate_input_clean=1,
            trained_alternate_input_clean=1,
            criterion="test",
            learning_claim=False,
            per_seed=(),
        )
        unavailable = LearningMeasurement(
            **base,
            retention_eligible_count=0,
            retained_count=0,
            forgotten_count=0,
            relearning_eligible_count=0,
            relearned_count=0,
        )
        self.assertIsNone(unavailable.retention_rate)
        self.assertIsNone(unavailable.relearning_rate)

        measured = LearningMeasurement(
            **base,
            retention_eligible_count=2,
            retained_count=1,
            forgotten_count=1,
            relearning_eligible_count=1,
            relearned_count=1,
        )
        self.assertEqual(measured.retention_rate, 0.5)
        self.assertEqual(measured.relearning_rate, 1.0)

    def test_p64_003_growth_bit5_requires_comparable_retention_evidence(self):
        unavailable_before = Fitness(retention=0.0, retention_evidence_count=0)
        newly_evaluable = Fitness(retention=1.0, retention_evidence_count=2)
        self.assertEqual(
            growth_flags(unavailable_before, newly_evaluable)
            & (1 << GROWTH_BIT_RETENTION),
            0,
        )

        comparable_before = Fitness(retention=0.25, retention_evidence_count=2)
        comparable_after = Fitness(retention=0.5, retention_evidence_count=2)
        self.assertEqual(
            growth_flags(comparable_before, comparable_after)
            & (1 << GROWTH_BIT_RETENTION),
            1 << GROWTH_BIT_RETENTION,
        )
        self.assertEqual(
            Fitness(
                success=1,
                retention=0.0,
                retention_evidence_count=0,
            ).sort_key(),
            Fitness(
                success=1,
                retention=1.0,
                retention_evidence_count=2,
            ).sort_key(),
        )

    def test_p64_004_phase5_fitness_uses_only_evaluable_retention_rate(self):
        result = EvaluationResult(
            expected_events=(OutputEvent.byte(66), OutputEvent.null()),
            autonomous_events=(),
            success=False,
            clone_generation=4,
            evaluation_generations=4,
            timed_out=True,
        )
        seed_measurement = SeedMeasurement(
            seed=1,
            baseline=result,
            trained=result,
            baseline_no_input=result,
            trained_no_input=result,
            baseline_alternate=result,
            trained_alternate=result,
        )
        measurement = LearningMeasurement(
            seed_count=1,
            baseline_successes=0,
            trained_successes=0,
            baseline_no_input_clean=1,
            trained_no_input_clean=1,
            baseline_alternate_input_clean=1,
            trained_alternate_input_clean=1,
            criterion="test",
            learning_claim=False,
            per_seed=(seed_measurement,),
            retention_eligible_count=2,
            retained_count=1,
            forgotten_count=1,
            relearning_eligible_count=1,
            relearned_count=0,
        )

        fitness = SteadyStateOptimizer._fitness_from_measurement(measurement)
        self.assertEqual(fitness.retention, 0.5)
        self.assertEqual(fitness.retention_evidence_count, 2)
        self.assertEqual(
            fitness.sort_key(),
            Fitness(
                timeouts=1,
                response_latency=4,
                retention=0.0,
                retention_evidence_count=0,
            ).sort_key(),
        )


    def test_p64_005_retention_protocol_records_t0_t1_t2_on_one_continuing_state(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=1,
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            retention_delay_generations=2,
            retention_interference_repetitions=1,
            relearning_teacher_repetitions=1,
        )

        measurement = compare_baseline_trained(
            seeds=(701,),
            config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        seed_record = measurement.per_seed[0]

        self.assertEqual(len(seed_record.mapping_results), 2)
        self.assertEqual(len(seed_record.retention_checkpoint_generations), 3)
        t0_generation, t1_generation, t2_generation = (
            seed_record.retention_checkpoint_generations
        )
        self.assertLess(t0_generation, t1_generation)
        self.assertGreaterEqual(
            t1_generation - t0_generation,
            protocol.retention_delay_generations,
        )
        self.assertLess(t1_generation, t2_generation)

        for mapping_record in seed_record.mapping_results:
            self.assertIs(mapping_record.t0, mapping_record.trained)
            self.assertIsNotNone(mapping_record.t1)
            self.assertIsNotNone(mapping_record.t2)

        self.assertEqual(measurement.retention_eligible_count, 0)
        self.assertIsNone(measurement.retention_rate)
        self.assertIsNone(measurement.relearning_rate)
        self.assertFalse(measurement.learning_claim)

    def test_p64_006_retention_classification_uses_t0_t1_t2_eligibility(self):
        expected = (OutputEvent.byte(66), OutputEvent.null())

        def result(success: bool) -> EvaluationResult:
            return EvaluationResult(
                expected_events=expected,
                autonomous_events=expected if success else (),
                success=success,
                clone_generation=4,
                evaluation_generations=4,
                timed_out=not success,
            )

        mappings = (
            ByteMapping(65, 66),
            ByteMapping(67, 68),
            ByteMapping(69, 70),
        )
        mapping_results = (
            MappingSeedMeasurement(
                mapping=mappings[0],
                baseline=result(False),
                trained=result(True),
                t1=result(True),
                t2=result(True),
            ),
            MappingSeedMeasurement(
                mapping=mappings[1],
                baseline=result(False),
                trained=result(True),
                t1=result(False),
                t2=result(True),
            ),
            MappingSeedMeasurement(
                mapping=mappings[2],
                baseline=result(False),
                trained=result(False),
                t1=result(False),
                t2=result(True),
            ),
        )
        seed_record = SeedMeasurement(
            seed=1,
            baseline=mapping_results[0].baseline,
            trained=mapping_results[0].trained,
            baseline_no_input=result(True),
            trained_no_input=result(True),
            baseline_alternate=result(True),
            trained_alternate=result(True),
            mapping_results=mapping_results,
        )

        measurement = experiment_module._assemble_learning_measurement(
            (seed_record,),
            mappings=mappings,
        )

        self.assertEqual(measurement.retention_eligible_count, 2)
        self.assertEqual(measurement.retained_count, 1)
        self.assertEqual(measurement.forgotten_count, 1)
        self.assertEqual(measurement.relearning_eligible_count, 1)
        self.assertEqual(measurement.relearned_count, 1)
        self.assertEqual(measurement.retention_rate, 0.5)
        self.assertEqual(measurement.relearning_rate, 1.0)

    def test_p64_007_phase5_retention_probe_does_not_mutate_authoritative_state(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=1,
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            retention_delay_generations=2,
            retention_interference_repetitions=1,
            relearning_teacher_repetitions=1,
        )
        state = create_universe(seed=702, config=PhysicsConfig(max_cells=8))
        IOExperiment(state, experiment=protocol).train_mappings()
        before = state.to_snapshot()

        measurement = measure_trained_state(state, experiment=protocol)

        self.assertEqual(state.to_snapshot(), before)
        self.assertEqual(len(measurement.per_seed), 1)
        for mapping_record in measurement.per_seed[0].mapping_results:
            self.assertIsNotNone(mapping_record.t1)
            self.assertIsNotNone(mapping_record.t2)


    def test_p64_008_canonical_and_smoke_retention_configs_are_explicit(self):
        canonical = load_experiment_config(
            ROOT / "config" / "experiment_phase6_forgetting_relearning.json"
        )
        smoke = load_experiment_config(
            ROOT / "config" / "experiment_phase6_forgetting_relearning_smoke.json"
        )

        self.assertTrue(canonical.retention_enabled)
        self.assertEqual(canonical.retention_delay_generations, 128)
        self.assertEqual(canonical.retention_interference_repetitions, 1)
        self.assertEqual(canonical.relearning_teacher_repetitions, 1)
        self.assertEqual(canonical.output_event_count, 2)
        self.assertEqual(canonical.output_event_interval_generations, 4)

        self.assertTrue(smoke.retention_enabled)
        self.assertEqual(smoke.retention_delay_generations, 2)
        self.assertEqual(smoke.retention_interference_repetitions, 1)
        self.assertEqual(smoke.relearning_teacher_repetitions, 1)
        self.assertEqual(smoke.output_event_count, 2)
        self.assertEqual(smoke.output_event_interval_generations, 2)

    def test_p64_009_runner_reports_public_retention_checkpoints_and_classification(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(
                runner_main([
                    "--config",
                    "config/default.json",
                    "--experiment",
                    "--experiment-config",
                    "config/experiment_phase6_forgetting_relearning_smoke.json",
                    "--json",
                ]),
                0,
            )

        payload = json.loads(stdout.getvalue())["experiment_measurement"]
        self.assertEqual(payload["retention_delay_generations"], 2)
        self.assertEqual(payload["retention_interference_repetitions"], 1)
        self.assertEqual(payload["relearning_teacher_repetitions"], 1)
        self.assertIn("retention_eligible_count", payload)
        self.assertIn("retained_count", payload)
        self.assertIn("forgotten_count", payload)
        self.assertIn("relearning_eligible_count", payload)
        self.assertIn("relearned_count", payload)
        self.assertIn("retention_rate", payload)
        self.assertIn("relearning_rate", payload)
        self.assertEqual(len(payload["per_seed"]), 3)
        for seed_record in payload["per_seed"]:
            self.assertEqual(len(seed_record["retention_checkpoint_generations"]), 3)
            for mapping_record in seed_record["mappings"]:
                for name in ("t0", "t1", "t2"):
                    self.assertIn(f"{name}_success", mapping_record)
                    self.assertIn(f"{name}_event_generations", mapping_record)
                    self.assertIsInstance(
                        mapping_record[f"{name}_event_generations"],
                        list,
                    )

    def test_p64_010_snapshot_and_timeout_override_preserve_retention_protocol(self):
        protocol = load_experiment_config(
            ROOT / "config" / "experiment_phase6_forgetting_relearning_smoke.json"
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=703,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        payload = optimizer.to_snapshot()
        restored = SteadyStateOptimizer.from_snapshot(payload)
        self.assertEqual(restored.experiment, protocol)
        self.assertEqual(payload["experiment"]["retention_delay_generations"], 2)
        self.assertEqual(payload["experiment"]["retention_interference_repetitions"], 1)
        self.assertEqual(payload["experiment"]["relearning_teacher_repetitions"], 1)

        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--experiment-config",
                        "config/experiment_phase6_forgetting_relearning_smoke.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--optimizer-timeout-generations",
                        "1",
                        "--json",
                    ]),
                    0,
                )

        overridden = captured[-1]
        optimizer_payload = json.loads(stdout.getvalue())["optimizer_protocol"]
        self.assertEqual(overridden.evaluation_timeout_generations, 1)
        self.assertEqual(overridden.retention_delay_generations, 2)
        self.assertEqual(overridden.retention_interference_repetitions, 1)
        self.assertEqual(overridden.relearning_teacher_repetitions, 1)
        self.assertEqual(optimizer_payload["retention_delay_generations"], 2)
        self.assertEqual(optimizer_payload["retention_interference_repetitions"], 1)
        self.assertEqual(optimizer_payload["relearning_teacher_repetitions"], 1)


    def test_p65_001_noise_robustness_protocol_field_roundtrips_without_changing_legacy_defaults(self):
        legacy = ExperimentConfig()
        self.assertEqual(legacy.noise_robustness_rate_delta, 0)
        self.assertFalse(legacy.noise_robustness_enabled)

        protocol = ExperimentConfig(
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            retention_delay_generations=2,
            retention_interference_repetitions=1,
            relearning_teacher_repetitions=1,
            noise_robustness_rate_delta=256,
        )
        restored = ExperimentConfig.from_mapping(protocol.to_dict())

        self.assertTrue(protocol.noise_robustness_enabled)
        self.assertEqual(restored, protocol)
        self.assertEqual(restored.noise_robustness_rate_delta, 256)

    def test_p65_002_noise_robustness_rate_is_none_without_clean_success_evidence(self):
        base = dict(
            seed_count=1,
            baseline_successes=0,
            trained_successes=0,
            baseline_no_input_clean=1,
            trained_no_input_clean=1,
            baseline_alternate_input_clean=1,
            trained_alternate_input_clean=1,
            criterion="test",
            learning_claim=False,
            per_seed=(),
        )
        unavailable = LearningMeasurement(
            **base,
            noise_robustness_eligible_count=0,
            noise_robust_count=0,
            noise_failed_count=0,
        )
        self.assertIsNone(unavailable.noise_robustness_rate)

        measured = LearningMeasurement(
            **base,
            noise_robustness_eligible_count=4,
            noise_robust_count=3,
            noise_failed_count=1,
        )
        self.assertEqual(measured.noise_robustness_rate, 0.75)

    def test_p65_003_growth_bit6_requires_comparable_noise_robustness_evidence(self):
        unavailable_before = Fitness(
            noise_robustness=0.0,
            noise_robustness_evidence_count=0,
        )
        newly_evaluable = Fitness(
            noise_robustness=1.0,
            noise_robustness_evidence_count=2,
        )
        self.assertEqual(
            growth_flags(unavailable_before, newly_evaluable)
            & (1 << GROWTH_BIT_NOISE_ROBUSTNESS),
            0,
        )

        comparable_before = Fitness(
            noise_robustness=0.25,
            noise_robustness_evidence_count=2,
        )
        comparable_after = Fitness(
            noise_robustness=0.5,
            noise_robustness_evidence_count=2,
        )
        self.assertEqual(
            growth_flags(comparable_before, comparable_after)
            & (1 << GROWTH_BIT_NOISE_ROBUSTNESS),
            1 << GROWTH_BIT_NOISE_ROBUSTNESS,
        )
        self.assertEqual(
            comparable_before.sort_key(),
            Fitness(
                noise_robustness=1.0,
                noise_robustness_evidence_count=99,
            ).sort_key(),
        )

    def test_p65_004_phase5_projects_only_evaluable_noise_robustness_evidence(self):
        result = EvaluationResult(
            expected_events=(OutputEvent.byte(66), OutputEvent.null()),
            autonomous_events=(),
            success=False,
            clone_generation=1,
            evaluation_generations=1,
            timed_out=True,
        )
        seed_record = SeedMeasurement(
            seed=1,
            baseline=result,
            trained=result,
            baseline_no_input=result,
            trained_no_input=result,
            baseline_alternate=result,
            trained_alternate=result,
        )
        measurement = LearningMeasurement(
            seed_count=1,
            baseline_successes=0,
            trained_successes=0,
            baseline_no_input_clean=1,
            trained_no_input_clean=1,
            baseline_alternate_input_clean=1,
            trained_alternate_input_clean=1,
            criterion="test",
            learning_claim=False,
            per_seed=(seed_record,),
            noise_robustness_eligible_count=4,
            noise_robust_count=3,
            noise_failed_count=1,
        )

        fitness = SteadyStateOptimizer._fitness_from_measurement(measurement)

        self.assertEqual(fitness.noise_robustness, 0.75)
        self.assertEqual(fitness.noise_robustness_evidence_count, 4)


    def test_p65_005_noise_measurement_uses_matched_t0_clones_and_additive_physical_rate(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=2,
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            retention_delay_generations=2,
            retention_interference_repetitions=1,
            relearning_teacher_repetitions=1,
            noise_robustness_rate_delta=256,
        )
        measurement = compare_baseline_trained(
            seeds=(801,),
            config=PhysicsConfig(max_cells=8, noise_rate=64),
            experiment=protocol,
        )
        seed_record = measurement.per_seed[0]

        self.assertEqual(seed_record.clean_noise_rate, 64)
        self.assertEqual(seed_record.noisy_noise_rate, 320)
        self.assertEqual(len(seed_record.mapping_results), 2)
        for mapping_record in seed_record.mapping_results:
            self.assertIsNotNone(mapping_record.noisy)
        self.assertIsNotNone(seed_record.noisy_no_input)
        self.assertIsNotNone(seed_record.noisy_prefix)
        self.assertIsNotNone(seed_record.noisy_sequence_counterfactual)

    def test_p65_006_noise_classification_requires_clean_success_and_noisy_controls(self):
        expected = (OutputEvent.byte(66), OutputEvent.null())

        def result(success: bool) -> EvaluationResult:
            return EvaluationResult(
                expected_events=expected,
                autonomous_events=expected if success else (),
                success=success,
                clone_generation=4,
                evaluation_generations=4,
                timed_out=not success,
            )

        mappings = (
            ByteMapping(65, 66),
            ByteMapping(67, 68),
            ByteMapping(69, 70),
        )
        mapping_results = (
            MappingSeedMeasurement(
                mapping=mappings[0],
                baseline=result(False),
                trained=result(True),
                noisy=result(True),
            ),
            MappingSeedMeasurement(
                mapping=mappings[1],
                baseline=result(False),
                trained=result(True),
                noisy=result(False),
            ),
            MappingSeedMeasurement(
                mapping=mappings[2],
                baseline=result(False),
                trained=result(False),
                noisy=result(True),
            ),
        )
        clean_control = EvaluationResult(
            expected_events=(),
            autonomous_events=(),
            success=True,
            clone_generation=4,
            evaluation_generations=4,
            timed_out=False,
        )
        seed_record = SeedMeasurement(
            seed=1,
            baseline=mapping_results[0].baseline,
            trained=mapping_results[0].trained,
            baseline_no_input=clean_control,
            trained_no_input=clean_control,
            baseline_alternate=clean_control,
            trained_alternate=clean_control,
            mapping_results=mapping_results,
            noisy_no_input=clean_control,
            noisy_alternate=clean_control,
            clean_noise_rate=0,
            noisy_noise_rate=256,
        )
        measurement = experiment_module._assemble_learning_measurement(
            (seed_record,),
            mappings=mappings,
        )

        self.assertEqual(measurement.noise_robustness_eligible_count, 2)
        self.assertEqual(measurement.noise_robust_count, 1)
        self.assertEqual(measurement.noise_failed_count, 1)
        self.assertEqual(measurement.noise_robustness_rate, 0.5)

        dirty_control = EvaluationResult(
            expected_events=(),
            autonomous_events=(OutputEvent.byte(66),),
            success=False,
            clone_generation=4,
            evaluation_generations=4,
            timed_out=False,
        )
        dirty_seed = SeedMeasurement(
            seed=2,
            baseline=mapping_results[0].baseline,
            trained=mapping_results[0].trained,
            baseline_no_input=clean_control,
            trained_no_input=clean_control,
            baseline_alternate=clean_control,
            trained_alternate=clean_control,
            mapping_results=(mapping_results[0],),
            noisy_no_input=dirty_control,
            noisy_alternate=clean_control,
            clean_noise_rate=0,
            noisy_noise_rate=256,
        )
        dirty = experiment_module._assemble_learning_measurement(
            (dirty_seed,),
            mappings=(mappings[0],),
        )
        self.assertEqual(dirty.noise_robustness_eligible_count, 1)
        self.assertEqual(dirty.noise_robust_count, 0)
        self.assertEqual(dirty.noise_failed_count, 1)
        self.assertEqual(dirty.noise_robustness_rate, 0.0)

    def test_p65_007_phase5_noise_probe_does_not_mutate_authoritative_state(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=2,
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            retention_delay_generations=2,
            retention_interference_repetitions=1,
            relearning_teacher_repetitions=1,
            noise_robustness_rate_delta=256,
        )
        state = create_universe(
            seed=802,
            config=PhysicsConfig(max_cells=8, noise_rate=64),
        )
        IOExperiment(state, experiment=protocol).train_mappings()
        before = state.to_snapshot()

        measurement = measure_trained_state(state, experiment=protocol)

        self.assertEqual(state.to_snapshot(), before)
        seed_record = measurement.per_seed[0]
        self.assertEqual(seed_record.clean_noise_rate, 64)
        self.assertEqual(seed_record.noisy_noise_rate, 320)
        self.assertTrue(all(item.noisy is not None for item in seed_record.mapping_results))


    def test_p65_008_canonical_and_smoke_noise_configs_are_explicit(self):
        canonical = load_experiment_config(
            ROOT / "config" / "experiment_phase6_noise_robustness.json"
        )
        smoke = load_experiment_config(
            ROOT / "config" / "experiment_phase6_noise_robustness_smoke.json"
        )

        self.assertTrue(canonical.noise_robustness_enabled)
        self.assertEqual(canonical.noise_robustness_rate_delta, 256)
        self.assertEqual(canonical.retention_delay_generations, 128)
        self.assertEqual(canonical.output_event_count, 2)

        self.assertTrue(smoke.noise_robustness_enabled)
        self.assertEqual(smoke.noise_robustness_rate_delta, 65535)
        self.assertEqual(smoke.retention_delay_generations, 2)
        self.assertEqual(smoke.output_event_count, 2)

    def test_p65_009_runner_reports_public_noise_robustness_evidence(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(
                runner_main([
                    "--config",
                    "config/default.json",
                    "--experiment",
                    "--experiment-config",
                    "config/experiment_phase6_noise_robustness_smoke.json",
                    "--json",
                ]),
                0,
            )

        payload = json.loads(stdout.getvalue())["experiment_measurement"]
        self.assertTrue(payload["noise_robustness_enabled"])
        self.assertEqual(payload["noise_robustness_rate_delta"], 65535)
        self.assertIn("noise_robustness_eligible_count", payload)
        self.assertIn("noise_robust_count", payload)
        self.assertIn("noise_failed_count", payload)
        self.assertIn("noise_robustness_rate", payload)
        self.assertEqual(len(payload["per_seed"]), 3)
        for seed_record in payload["per_seed"]:
            self.assertIn("clean_noise_rate", seed_record)
            self.assertIn("noisy_noise_rate", seed_record)
            self.assertGreater(
                seed_record["noisy_noise_rate"],
                seed_record["clean_noise_rate"],
            )
            self.assertIn("noisy_no_input_clean", seed_record)
            self.assertIn("noisy_sequence_counterfactual_clean", seed_record)
            for mapping_record in seed_record["mappings"]:
                self.assertIn("noisy_success", mapping_record)
                self.assertIn("noisy_event_generations", mapping_record)
                self.assertIn("noise_eligible", mapping_record)
                self.assertIn("noise_robust", mapping_record)
                self.assertIn("noise_failed", mapping_record)
                self.assertEqual(
                    mapping_record["noise_failed"],
                    bool(
                        mapping_record["noise_eligible"]
                        and not mapping_record["noise_robust"]
                    ),
                )
                self.assertIsInstance(
                    mapping_record["noisy_event_generations"],
                    list,
                )

    def test_p65_010_snapshot_and_timeout_override_preserve_noise_protocol(self):
        protocol = load_experiment_config(
            ROOT / "config" / "experiment_phase6_noise_robustness_smoke.json"
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=803,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        payload = optimizer.to_snapshot()
        restored = SteadyStateOptimizer.from_snapshot(payload)
        self.assertEqual(restored.experiment, protocol)
        self.assertEqual(
            payload["experiment"]["noise_robustness_rate_delta"],
            65535,
        )

        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--experiment-config",
                        "config/experiment_phase6_noise_robustness_smoke.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--optimizer-timeout-generations",
                        "1",
                        "--json",
                    ]),
                    0,
                )

        overridden = captured[-1]
        optimizer_payload = json.loads(stdout.getvalue())["optimizer_protocol"]
        self.assertEqual(overridden.evaluation_timeout_generations, 1)
        self.assertEqual(overridden.noise_robustness_rate_delta, 65535)
        self.assertTrue(overridden.noise_robustness_enabled)
        self.assertEqual(optimizer_payload["noise_robustness_rate_delta"], 65535)
        self.assertTrue(optimizer_payload["noise_robustness_enabled"])


    def test_p66_001_held_out_relation_roundtrips_without_changing_legacy_default(self):
        legacy = ExperimentConfig()
        self.assertIsNone(legacy.held_out_mapping)
        self.assertFalse(legacy.generalization_enabled)

        protocol = ExperimentConfig(
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            held_out_mapping=ByteSequenceMapping((65, 69), 70),
        )
        restored = ExperimentConfig.from_mapping(protocol.to_dict())

        self.assertTrue(protocol.generalization_enabled)
        self.assertEqual(restored, protocol)
        self.assertEqual(
            protocol.to_dict()["held_out_mapping"],
            {"input_bytes": [65, 69], "output_byte": 70},
        )

    def test_p66_002_held_out_relation_validates_shared_prefix_and_second_byte_plus_one(self):
        base = dict(
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
        )

        with self.assertRaises(ValueError):
            ExperimentConfig(
                **base,
                held_out_mapping=ByteSequenceMapping((66, 69), 70),
            )
        with self.assertRaises(ValueError):
            ExperimentConfig(
                **base,
                held_out_mapping=ByteSequenceMapping((65, 69), 71),
            )
        with self.assertRaises(ValueError):
            ExperimentConfig(
                **base,
                held_out_mapping=ByteSequenceMapping((65, 67), 68),
            )

    def test_p66_003_generalization_rejects_training_mapping_outside_predeclared_relation(self):
        with self.assertRaises(ValueError):
            ExperimentConfig(
                mappings=(
                    ByteSequenceMapping((65, 65), 66),
                    ByteSequenceMapping((65, 67), 69),
                ),
                counterfactual_prefix=(65,),
                counterfactual_input_sequence=(67, 65),
                output_event_count=2,
                output_event_interval_generations=2,
                held_out_mapping=ByteSequenceMapping((65, 69), 70),
            )


    def test_p66_004_training_curriculum_never_teacher_trains_held_out_case(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=2,
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            held_out_mapping=ByteSequenceMapping((65, 69), 70),
        )
        state = create_universe(seed=901, config=PhysicsConfig(max_cells=8))
        experiment = IOExperiment(state, experiment=protocol)

        records = experiment.train_mappings()

        self.assertEqual(
            [(record.input_bytes, record.output_byte) for record in records],
            [((65, 65), 66), ((65, 67), 68)],
        )
        teacher_bytes = [
            event.value
            for event in experiment.teacher_events
            if event.kind == "byte"
        ]
        self.assertNotIn(70, teacher_bytes)

    def test_p66_005_held_out_baseline_and_trained_evaluation_are_separate_clone_evidence(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=2,
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            held_out_mapping=ByteSequenceMapping((65, 69), 70),
        )
        state = create_universe(seed=902, config=PhysicsConfig(max_cells=8))
        IOExperiment(state, experiment=protocol).train_mappings()
        before = state.to_snapshot()

        measurement = measure_trained_state(state, experiment=protocol)
        seed_record = measurement.per_seed[0]

        self.assertEqual(state.to_snapshot(), before)
        self.assertEqual(len(seed_record.mapping_results), 2)
        self.assertIsNotNone(seed_record.baseline_held_out)
        self.assertIsNotNone(seed_record.trained_held_out)
        self.assertEqual(
            seed_record.baseline_held_out.expected_events,
            (
                OutputEvent.byte(70),
                OutputEvent.byte(70),
                OutputEvent.null(),
            ),
        )
        self.assertEqual(
            seed_record.trained_held_out.expected_events,
            seed_record.baseline_held_out.expected_events,
        )
        self.assertIsInstance(seed_record.baseline_held_out.event_generations, tuple)
        self.assertIsInstance(seed_record.trained_held_out.event_generations, tuple)


    def test_p66_006_generalization_classification_is_baseline_relative_and_null_aware(self):
        expected = (
            OutputEvent.byte(70),
            OutputEvent.byte(70),
            OutputEvent.null(),
        )

        def result(success: bool) -> EvaluationResult:
            return EvaluationResult(
                expected_events=expected,
                autonomous_events=expected if success else (),
                success=success,
                clone_generation=4,
                evaluation_generations=4,
                timed_out=not success,
            )

        clean_control = EvaluationResult(
            expected_events=(),
            autonomous_events=(),
            success=True,
            clone_generation=4,
            evaluation_generations=4,
            timed_out=False,
        )
        training_mappings = (
            ByteSequenceMapping((65, 65), 66),
            ByteSequenceMapping((65, 67), 68),
        )

        def seed_record(
            seed: int,
            *,
            held_baseline: bool,
            held_trained: bool,
            second_baseline_success: bool = False,
        ) -> SeedMeasurement:
            mapping_results = (
                MappingSeedMeasurement(
                    mapping=training_mappings[0],
                    baseline=result(False),
                    trained=result(True),
                ),
                MappingSeedMeasurement(
                    mapping=training_mappings[1],
                    baseline=result(second_baseline_success),
                    trained=result(True),
                ),
            )
            return SeedMeasurement(
                seed=seed,
                baseline=mapping_results[0].baseline,
                trained=mapping_results[0].trained,
                baseline_no_input=clean_control,
                trained_no_input=clean_control,
                baseline_alternate=clean_control,
                trained_alternate=clean_control,
                mapping_results=mapping_results,
                baseline_prefix=clean_control,
                trained_prefix=clean_control,
                baseline_sequence_counterfactual=clean_control,
                trained_sequence_counterfactual=clean_control,
                baseline_held_out=result(held_baseline),
                trained_held_out=result(held_trained),
            )

        generalized = seed_record(1, held_baseline=False, held_trained=True)
        failed = seed_record(2, held_baseline=False, held_trained=False)
        innate = seed_record(3, held_baseline=True, held_trained=True)
        not_improved = seed_record(
            4,
            held_baseline=False,
            held_trained=True,
            second_baseline_success=True,
        )

        measurement = experiment_module._assemble_learning_measurement(
            (generalized, failed, innate, not_improved),
            mappings=training_mappings,
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
            held_out_mapping=ByteSequenceMapping((65, 69), 70),
        )

        self.assertEqual(generalized.generalization_classification(), (True, True, True, False))
        self.assertEqual(failed.generalization_classification(), (True, True, False, True))
        self.assertEqual(innate.generalization_classification(), (True, False, False, False))
        self.assertEqual(not_improved.generalization_classification(), (False, False, False, False))
        self.assertEqual(measurement.training_qualified_count, 3)
        self.assertEqual(measurement.generalization_eligible_count, 2)
        self.assertEqual(measurement.generalized_count, 1)
        self.assertEqual(measurement.generalization_failed_count, 1)
        self.assertEqual(measurement.generalization_rate, 0.5)

    def test_p66_007_zero_generalization_eligible_cases_report_none(self):
        measurement = LearningMeasurement(
            seed_count=1,
            baseline_successes=0,
            trained_successes=0,
            baseline_no_input_clean=1,
            trained_no_input_clean=1,
            baseline_alternate_input_clean=1,
            trained_alternate_input_clean=1,
            criterion="test",
            learning_claim=False,
            per_seed=(),
            training_qualified_count=0,
            generalization_eligible_count=0,
            generalized_count=0,
            generalization_failed_count=0,
        )
        self.assertIsNone(measurement.generalization_rate)


    def test_p66_008_canonical_and_smoke_generalization_configs_are_explicit(self):
        canonical = load_experiment_config(
            ROOT / "config" / "experiment_phase6_generalization.json"
        )
        smoke = load_experiment_config(
            ROOT / "config" / "experiment_phase6_generalization_smoke.json"
        )

        for protocol in (canonical, smoke):
            self.assertTrue(protocol.generalization_enabled)
            self.assertEqual(
                protocol.held_out_mapping,
                ByteSequenceMapping((65, 69), 70),
            )
            self.assertEqual(
                tuple((item.input_bytes, item.output_byte) for item in protocol.mappings),
                (((65, 65), 66), ((65, 67), 68)),
            )
            self.assertEqual(protocol.output_event_count, 2)

    def test_p66_009_runner_reports_public_generalization_evidence(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(
                runner_main([
                    "--config",
                    "config/default.json",
                    "--experiment",
                    "--experiment-config",
                    "config/experiment_phase6_generalization_smoke.json",
                    "--json",
                ]),
                0,
            )

        payload = json.loads(stdout.getvalue())["experiment_measurement"]
        self.assertTrue(payload["generalization_enabled"])
        self.assertEqual(
            payload["held_out_mapping"],
            {"input_bytes": [65, 69], "output_byte": 70},
        )
        for name in (
            "training_qualified_count",
            "generalization_eligible_count",
            "generalized_count",
            "generalization_failed_count",
            "generalization_rate",
        ):
            self.assertIn(name, payload)
        self.assertEqual(len(payload["per_seed"]), 3)
        for seed_record in payload["per_seed"]:
            self.assertIn("baseline_held_out_success", seed_record)
            self.assertIn("trained_held_out_success", seed_record)
            self.assertIn("baseline_held_out_event_generations", seed_record)
            self.assertIn("trained_held_out_event_generations", seed_record)
            self.assertIn("training_qualified", seed_record)
            self.assertIn("generalization_eligible", seed_record)
            self.assertIn("generalized", seed_record)
            self.assertIn("generalization_failed", seed_record)

    def test_p66_010_snapshot_and_timeout_override_preserve_held_out_protocol(self):
        protocol = load_experiment_config(
            ROOT / "config" / "experiment_phase6_generalization_smoke.json"
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=903,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        payload = optimizer.to_snapshot()
        restored = SteadyStateOptimizer.from_snapshot(payload)

        self.assertEqual(restored.experiment, protocol)
        self.assertEqual(
            payload["experiment"]["held_out_mapping"],
            {"input_bytes": [65, 69], "output_byte": 70},
        )

        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--experiment-config",
                        "config/experiment_phase6_generalization_smoke.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--optimizer-timeout-generations",
                        "1",
                        "--json",
                    ]),
                    0,
                )

        overridden = captured[-1]
        optimizer_payload = json.loads(stdout.getvalue())["optimizer_protocol"]
        self.assertEqual(overridden.evaluation_timeout_generations, 1)
        self.assertEqual(
            overridden.held_out_mapping,
            ByteSequenceMapping((65, 69), 70),
        )
        self.assertTrue(optimizer_payload["generalization_enabled"])
        self.assertEqual(
            optimizer_payload["held_out_mapping"],
            {"input_bytes": [65, 69], "output_byte": 70},
        )

    def test_p66_011_generalization_evidence_does_not_change_phase5_fitness_or_growth_bit7(self):
        result = EvaluationResult(
            expected_events=(OutputEvent.byte(66), OutputEvent.null()),
            autonomous_events=(),
            success=False,
            clone_generation=1,
            evaluation_generations=1,
            timed_out=True,
        )
        mapping_record = MappingSeedMeasurement(
            mapping=ByteMapping(65, 66),
            baseline=result,
            trained=result,
        )
        seed_record = SeedMeasurement(
            seed=1,
            baseline=result,
            trained=result,
            baseline_no_input=result,
            trained_no_input=result,
            baseline_alternate=result,
            trained_alternate=result,
            mapping_results=(mapping_record,),
        )
        base = dict(
            seed_count=1,
            baseline_successes=0,
            trained_successes=0,
            baseline_no_input_clean=0,
            trained_no_input_clean=0,
            baseline_alternate_input_clean=0,
            trained_alternate_input_clean=0,
            criterion="test",
            learning_claim=False,
            per_seed=(seed_record,),
            mapping_count=1,
        )
        without_generalization = LearningMeasurement(**base)
        with_generalization = LearningMeasurement(
            **base,
            training_qualified_count=1,
            generalization_eligible_count=1,
            generalized_count=1,
            generalization_failed_count=0,
        )

        before = SteadyStateOptimizer._fitness_from_measurement(without_generalization)
        after = SteadyStateOptimizer._fitness_from_measurement(with_generalization)
        self.assertEqual(after, before)
        self.assertEqual(growth_flags(before, after) & (1 << 7), 0)


    def test_p67_001_explicit_output_sequence_roundtrips_without_changing_legacy_shape(self):
        legacy = ByteSequenceMapping((65, 65), 66)
        self.assertEqual(legacy.output_bytes, ())
        self.assertEqual(
            legacy.to_dict(),
            {"input_bytes": [65, 65], "output_byte": 66},
        )
        self.assertEqual(
            ByteSequenceMapping.from_mapping(legacy.to_dict()),
            legacy,
        )

        explicit = ByteSequenceMapping(
            (65, 65),
            66,
            output_bytes=(66, 67),
        )
        self.assertEqual(explicit.output_bytes, (66, 67))
        self.assertEqual(
            explicit.to_dict(),
            {
                "input_bytes": [65, 65],
                "output_byte": 66,
                "output_bytes": [66, 67],
            },
        )
        self.assertEqual(
            ByteSequenceMapping.from_mapping(explicit.to_dict()),
            explicit,
        )

    def test_p67_002_explicit_output_sequence_is_bounded_distinct_and_matches_event_count(self):
        with self.assertRaises(ValueError):
            ByteSequenceMapping(
                (65, 65),
                66,
                output_bytes=(66,),
            )
        with self.assertRaises(ValueError):
            ByteSequenceMapping(
                (65, 65),
                66,
                output_bytes=(66, 66),
            )

        protocol = ExperimentConfig(
            mappings=(
                ByteSequenceMapping((65, 65), 66, output_bytes=(66, 67)),
                ByteSequenceMapping((65, 67), 68, output_bytes=(68, 69)),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=4,
        )
        self.assertEqual(
            tuple(item.output_bytes for item in protocol.mappings),
            ((66, 67), (68, 69)),
        )

        with self.assertRaises(ValueError):
            ExperimentConfig(
                mappings=(
                    ByteSequenceMapping((65, 65), 66, output_bytes=(66, 67)),
                    ByteSequenceMapping((65, 67), 68, output_bytes=(68, 69)),
                ),
                counterfactual_prefix=(65,),
                counterfactual_input_sequence=(67, 65),
                output_event_count=1,
                output_event_interval_generations=0,
            )


    def test_p67_003_teacher_emits_distinct_output_sequence_in_declared_order(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=1,
            mappings=(
                ByteSequenceMapping((65, 65), 66, output_bytes=(66, 67)),
                ByteSequenceMapping((65, 67), 68, output_bytes=(68, 69)),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            inter_input_generations=1,
            output_event_count=2,
            output_event_interval_generations=2,
        )
        state = create_universe(seed=1401, config=PhysicsConfig(max_cells=8))
        records = IOExperiment(state, experiment=protocol).train_mappings()

        self.assertEqual(
            records[0].teacher_events,
            (
                OutputEvent.byte(66),
                OutputEvent.byte(67),
                OutputEvent.null(),
            ),
        )
        self.assertEqual(
            records[1].teacher_events,
            (
                OutputEvent.byte(68),
                OutputEvent.byte(69),
                OutputEvent.null(),
            ),
        )

    def test_p67_004_mapping_evaluation_expects_distinct_sequence_content(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=1,
            mappings=(
                ByteSequenceMapping((65, 65), 66, output_bytes=(66, 67)),
                ByteSequenceMapping((65, 67), 68, output_bytes=(68, 69)),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            inter_input_generations=1,
            output_event_count=2,
            output_event_interval_generations=2,
        )
        baseline = create_universe(seed=1402, config=PhysicsConfig(max_cells=8))
        trained = create_universe(seed=1402, config=PhysicsConfig(max_cells=8))
        measurement = experiment_module._seed_measurement(
            seed=1402,
            baseline_state=baseline,
            trained_state=trained,
            protocol=protocol,
        )

        self.assertEqual(
            measurement.mapping_results[0].trained.expected_events,
            (
                OutputEvent.byte(66),
                OutputEvent.byte(67),
                OutputEvent.null(),
            ),
        )
        self.assertEqual(
            measurement.mapping_results[1].trained.expected_events,
            (
                OutputEvent.byte(68),
                OutputEvent.byte(69),
                OutputEvent.null(),
            ),
        )


    def test_p67_003_teacher_emits_declared_distinct_bytes_in_order(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=2,
            mappings=(
                ByteSequenceMapping(
                    (65, 65),
                    66,
                    output_bytes=(66, 67),
                ),
                ByteSequenceMapping(
                    (65, 67),
                    68,
                    output_bytes=(68, 69),
                ),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
        )
        state = create_universe(seed=1001, config=PhysicsConfig(max_cells=8))
        experiment = IOExperiment(state, experiment=protocol)

        records = experiment.train_mappings()

        self.assertEqual(
            [event.value for event in experiment.teacher_events if event.kind == "byte"],
            [66, 67, 68, 69],
        )
        self.assertEqual(
            [
                tuple(event.value for event in record.teacher_events if event.kind == "byte")
                for record in records
            ],
            [(66, 67), (68, 69)],
        )


    def test_p67_005_distinct_sequence_evaluation_rejects_content_order_timing_and_termination_errors(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=5,
            mappings=(
                ByteSequenceMapping((65, 65), 66, output_bytes=(66, 67)),
                ByteSequenceMapping((65, 67), 68, output_bytes=(68, 69)),
            ),
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
            output_event_count=2,
            output_event_interval_generations=2,
        )
        state = create_universe(seed=1403, config=PhysicsConfig(max_cells=8))
        experiment = IOExperiment(state, experiment=protocol)
        expected = (
            OutputEvent.byte(66),
            OutputEvent.byte(67),
            OutputEvent.null(),
        )

        def evaluate_with(signals):
            values = iter(signals)

            def next_signal(_state):
                return next(values, OutputSignal())

            with patch("core.experiment.read_output_signal", side_effect=next_signal):
                return experiment.evaluate_autonomous_sequence(
                    input_bytes=(65, 65),
                    expected=expected,
                )

        quiet = OutputSignal()
        byte_b = OutputSignal(value=66, valid=True)
        byte_c = OutputSignal(value=67, valid=True)
        byte_x = OutputSignal(value=88, valid=True)
        null = OutputSignal(valid=True, null=True)

        correct = evaluate_with(
            (quiet, quiet, quiet, byte_b, quiet, byte_c, quiet, null)
        )
        reversed_order = evaluate_with(
            (quiet, quiet, quiet, byte_c, quiet, byte_b, quiet, null)
        )
        repeated = evaluate_with(
            (quiet, quiet, quiet, byte_b, quiet, byte_b, quiet, null)
        )
        wrong_timing = evaluate_with(
            (quiet, quiet, quiet, byte_b, quiet, quiet, byte_c, null)
        )
        extra = evaluate_with(
            (quiet, quiet, quiet, byte_b, quiet, byte_c, quiet, byte_x)
        )
        missing_null = evaluate_with(
            (quiet, quiet, quiet, byte_b, quiet, byte_c, quiet, quiet)
        )

        self.assertTrue(correct.success)
        self.assertEqual(correct.autonomous_events, expected)
        self.assertEqual(correct.event_generations[:2], (3, 5))
        for failure in (
            reversed_order,
            repeated,
            wrong_timing,
            extra,
            missing_null,
        ):
            self.assertFalse(failure.success)


    def test_p67_006_canonical_and_smoke_configs_declare_distinct_sequences(self):
        canonical = load_experiment_config(
            ROOT / "config" / "experiment_phase6_multi_byte_sequences.json"
        )
        smoke = load_experiment_config(
            ROOT / "config" / "experiment_phase6_multi_byte_sequences_smoke.json"
        )

        self.assertEqual(
            tuple(item.output_bytes for item in canonical.mappings),
            ((66, 67), (68, 69)),
        )
        self.assertEqual(canonical.output_event_count, 2)
        self.assertEqual(canonical.output_event_interval_generations, 4)
        self.assertEqual(canonical.evaluation_timeout_generations, 1024)

        self.assertEqual(
            tuple(item.output_bytes for item in smoke.mappings),
            ((66, 67), (68, 69)),
        )
        self.assertEqual(smoke.output_event_count, 2)
        self.assertEqual(smoke.output_event_interval_generations, 2)
        self.assertEqual(smoke.evaluation_timeout_generations, 2)

    def test_p67_007_snapshot_and_timeout_override_preserve_distinct_sequences(self):
        protocol = load_experiment_config(
            ROOT / "config" / "experiment_phase6_multi_byte_sequences_smoke.json"
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=1404,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        restored = SteadyStateOptimizer.from_snapshot(optimizer.to_snapshot())
        self.assertEqual(restored.experiment, protocol)
        self.assertEqual(
            tuple(item.output_bytes for item in restored.experiment.mappings),
            ((66, 67), (68, 69)),
        )

        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--experiment-config",
                        "config/experiment_phase6_multi_byte_sequences_smoke.json",
                        "--optimizer-timeout-generations",
                        "1",
                        "--json",
                    ]),
                    0,
                )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(captured[-1].evaluation_timeout_generations, 1)
        self.assertEqual(
            tuple(item.output_bytes for item in captured[-1].mappings),
            ((66, 67), (68, 69)),
        )
        self.assertEqual(
            [item["output_bytes"] for item in payload["optimizer_protocol"]["mappings"]],
            [[66, 67], [68, 69]],
        )

    def test_p67_008_runner_reports_declared_and_observed_sequence_evidence(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(
                runner_main([
                    "--config",
                    "config/default.json",
                    "--experiment",
                    "--experiment-config",
                    "config/experiment_phase6_multi_byte_sequences_smoke.json",
                    "--json",
                ]),
                0,
            )

        payload = json.loads(stdout.getvalue())["experiment_measurement"]
        self.assertEqual(
            [item["output_bytes"] for item in payload["per_mapping"]],
            [[66, 67], [68, 69]],
        )
        self.assertEqual(len(payload["per_seed"]), 3)
        for seed_record in payload["per_seed"]:
            self.assertEqual(len(seed_record["mappings"]), 2)
            for mapping_record in seed_record["mappings"]:
                self.assertIn(mapping_record["output_bytes"], ([66, 67], [68, 69]))
                self.assertIsInstance(mapping_record["baseline_events"], list)
                self.assertIsInstance(mapping_record["trained_events"], list)
                for event in (
                    mapping_record["baseline_events"]
                    + mapping_record["trained_events"]
                ):
                    self.assertIn(event["kind"], ("byte", "null"))
                    self.assertIn("value", event)
                    self.assertIsInstance(event["generation"], int)
        self.assertFalse(payload["learning_claim"])
        self.assertIn(
            "declared ordered output-byte sequence",
            payload["criterion"],
        )
        self.assertNotIn("output byte 2 times", payload["criterion"])


    def test_p68_001_canonical_and_smoke_configs_are_raw_valid_utf8_bytes(self):
        canonical = load_experiment_config(
            ROOT / "config" / "experiment_phase6_raw_utf8.json"
        )
        smoke = load_experiment_config(
            ROOT / "config" / "experiment_phase6_raw_utf8_smoke.json"
        )

        expected_inputs = (
            tuple("é".encode("utf-8")),
            tuple("ö".encode("utf-8")),
        )
        expected_outputs = (
            tuple("ñ".encode("utf-8")),
            tuple("ø".encode("utf-8")),
        )
        self.assertEqual(expected_inputs, ((0xC3, 0xA9), (0xC3, 0xB6)))
        self.assertEqual(expected_outputs, ((0xC3, 0xB1), (0xC3, 0xB8)))

        for protocol in (canonical, smoke):
            self.assertEqual(
                tuple(item.input_bytes for item in protocol.mappings),
                expected_inputs,
            )
            self.assertEqual(
                tuple(item.output_bytes for item in protocol.mappings),
                expected_outputs,
            )
            self.assertEqual(protocol.counterfactual_prefix, (0xC3,))
            self.assertEqual(
                protocol.counterfactual_input_sequence,
                tuple("ç".encode("utf-8")),
            )
            for item in protocol.mappings:
                bytes(item.input_bytes).decode("utf-8")
                bytes(item.output_bytes).decode("utf-8")

        self.assertEqual(canonical.output_event_count, 2)
        self.assertEqual(canonical.output_event_interval_generations, 4)
        self.assertEqual(canonical.evaluation_timeout_generations, 1024)
        self.assertEqual(smoke.output_event_count, 2)
        self.assertEqual(smoke.output_event_interval_generations, 2)
        self.assertEqual(smoke.evaluation_timeout_generations, 2)

    def test_p68_002_teacher_path_receives_only_raw_utf8_byte_values(self):
        protocol = load_experiment_config(
            ROOT / "config" / "experiment_phase6_raw_utf8_smoke.json"
        )
        state = create_universe(seed=1501, config=PhysicsConfig(max_cells=8))
        records = IOExperiment(state, experiment=protocol).train_mappings()

        self.assertEqual(
            [
                tuple(event.value for event in record.teacher_events if event.kind == "byte")
                for record in records
            ],
            [
                tuple("ñ".encode("utf-8")),
                tuple("ø".encode("utf-8")),
            ],
        )
        self.assertEqual(
            [tuple(item.input_bytes) for item in protocol.mappings],
            [
                tuple("é".encode("utf-8")),
                tuple("ö".encode("utf-8")),
            ],
        )

    def test_p68_003_snapshot_and_timeout_override_preserve_raw_utf8_bytes(self):
        protocol = load_experiment_config(
            ROOT / "config" / "experiment_phase6_raw_utf8_smoke.json"
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=1502,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        restored = SteadyStateOptimizer.from_snapshot(optimizer.to_snapshot())
        self.assertEqual(restored.experiment, protocol)

        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--experiment-config",
                        "config/experiment_phase6_raw_utf8_smoke.json",
                        "--optimizer-timeout-generations",
                        "1",
                        "--json",
                    ]),
                    0,
                )

        payload = json.loads(stdout.getvalue())
        effective = captured[-1]
        self.assertEqual(effective.evaluation_timeout_generations, 1)
        self.assertEqual(
            [list(item.input_bytes) for item in effective.mappings],
            [[0xC3, 0xA9], [0xC3, 0xB6]],
        )
        self.assertEqual(
            [list(item.output_bytes) for item in effective.mappings],
            [[0xC3, 0xB1], [0xC3, 0xB8]],
        )
        self.assertEqual(
            payload["optimizer_protocol"]["mappings"],
            [
                {
                    "input_bytes": [0xC3, 0xA9],
                    "output_byte": 0xC3,
                    "output_bytes": [0xC3, 0xB1],
                },
                {
                    "input_bytes": [0xC3, 0xB6],
                    "output_byte": 0xC3,
                    "output_bytes": [0xC3, 0xB8],
                },
            ],
        )

    def test_p68_004_runner_reports_raw_utf8_declared_and_observed_byte_evidence(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(
                runner_main([
                    "--config",
                    "config/default.json",
                    "--experiment",
                    "--experiment-config",
                    "config/experiment_phase6_raw_utf8_smoke.json",
                    "--json",
                ]),
                0,
            )

        payload = json.loads(stdout.getvalue())["experiment_measurement"]
        self.assertEqual(
            [item["input_bytes"] for item in payload["per_mapping"]],
            [[0xC3, 0xA9], [0xC3, 0xB6]],
        )
        self.assertEqual(
            [item["output_bytes"] for item in payload["per_mapping"]],
            [[0xC3, 0xB1], [0xC3, 0xB8]],
        )
        self.assertEqual(payload["counterfactual_prefix"], [0xC3])
        self.assertEqual(
            payload["counterfactual_input_sequence"],
            [0xC3, 0xA7],
        )
        self.assertFalse(payload["learning_claim"])
        for seed_record in payload["per_seed"]:
            for mapping_record in seed_record["mappings"]:
                self.assertIsInstance(mapping_record["baseline_events"], list)
                self.assertIsInstance(mapping_record["trained_events"], list)


    def test_p69_001_mixed_length_mapping_contract_roundtrips(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=2,
            mappings=(
                ByteMapping(0x41, 0x42),
                ByteSequenceMapping(
                    (0x43, 0x44),
                    0x45,
                    output_bytes=(0x45, 0x46),
                ),
                ByteSequenceMapping(
                    (0x47, 0x48, 0x49),
                    0x4A,
                    output_bytes=(0x4A, 0x4B, 0x4C),
                ),
            ),
            counterfactual_input_byte=0x4D,
            inter_input_generations=1,
            counterfactual_prefix=(0x47, 0x48),
            counterfactual_input_sequence=(0x4D, 0x4E),
            output_event_count=1,
            output_event_interval_generations=2,
        )

        self.assertEqual(
            tuple(len(item.input_bytes) for item in protocol.mappings),
            (1, 2, 3),
        )
        self.assertEqual(
            tuple(
                len(getattr(item, "output_bytes", ()) or (item.output_byte,))
                for item in protocol.mappings
            ),
            (1, 2, 3),
        )
        self.assertEqual(
            ExperimentConfig.from_mapping(protocol.to_dict()),
            protocol,
        )

        with self.assertRaises(ValueError):
            ByteSequenceMapping(
                (1, 2, 3, 4),
                5,
                output_bytes=(5, 6, 7),
            )
        with self.assertRaises(ValueError):
            ByteSequenceMapping(
                (1, 2, 3),
                5,
                output_bytes=(5, 6, 7, 8),
            )

    def test_p69_002_teacher_and_evaluation_use_mapping_specific_output_lengths(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=2,
            mappings=(
                ByteMapping(0x41, 0x42),
                ByteSequenceMapping(
                    (0x43, 0x44),
                    0x45,
                    output_bytes=(0x45, 0x46),
                ),
                ByteSequenceMapping(
                    (0x47, 0x48, 0x49),
                    0x4A,
                    output_bytes=(0x4A, 0x4B, 0x4C),
                ),
            ),
            counterfactual_input_byte=0x4D,
            inter_input_generations=1,
            counterfactual_prefix=(0x47, 0x48),
            counterfactual_input_sequence=(0x4D, 0x4E),
            output_event_count=1,
            output_event_interval_generations=2,
        )

        trained = create_universe(seed=1601, config=PhysicsConfig(max_cells=8))
        records = IOExperiment(trained, experiment=protocol).train_mappings()
        self.assertEqual(
            [
                tuple(
                    event.value
                    for event in record.teacher_events
                    if event.kind == "byte"
                )
                for record in records
            ],
            [
                (0x42,),
                (0x45, 0x46),
                (0x4A, 0x4B, 0x4C),
            ],
        )

        measurement = experiment_module._seed_measurement(
            seed=1601,
            baseline_state=create_universe(
                seed=1601,
                config=PhysicsConfig(max_cells=8),
            ),
            trained_state=trained,
            protocol=protocol,
        )
        self.assertEqual(
            [
                result.trained.expected_output_event_count
                for result in measurement.mapping_results
            ],
            [1, 2, 3],
        )
        self.assertEqual(
            [
                tuple(event.value for event in result.trained.expected_events if event.kind == "byte")
                for result in measurement.mapping_results
            ],
            [
                (0x42,),
                (0x45, 0x46),
                (0x4A, 0x4B, 0x4C),
            ],
        )


    def test_p69_003_configs_snapshot_and_timeout_override_preserve_mixed_lengths(self):
        canonical = load_experiment_config(
            ROOT / "config" / "experiment_phase6_mixed_length_sequences.json"
        )
        smoke = load_experiment_config(
            ROOT / "config" / "experiment_phase6_mixed_length_sequences_smoke.json"
        )

        for protocol in (canonical, smoke):
            self.assertEqual(
                [len(item.input_bytes) for item in protocol.mappings],
                [1, 2, 3],
            )
            self.assertEqual(
                [
                    len(getattr(item, "output_bytes", ()) or (item.output_byte,))
                    for item in protocol.mappings
                ],
                [1, 2, 3],
            )
            self.assertEqual(protocol.counterfactual_prefix, (0x47, 0x48))
            self.assertEqual(
                protocol.counterfactual_input_sequence,
                (0x4D, 0x4E),
            )
            self.assertEqual(
                ExperimentConfig.from_mapping(protocol.to_dict()),
                protocol,
            )

        self.assertEqual(canonical.evaluation_timeout_generations, 1024)
        self.assertEqual(canonical.output_event_interval_generations, 4)
        self.assertEqual(smoke.evaluation_timeout_generations, 2)
        self.assertEqual(smoke.output_event_interval_generations, 2)

        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=1602,
            base_config=PhysicsConfig(max_cells=8),
            experiment=smoke,
        )
        restored = SteadyStateOptimizer.from_snapshot(optimizer.to_snapshot())
        self.assertEqual(restored.experiment, smoke)

        captured = []

        def fake_optimizer(**kwargs):
            captured.append(kwargs["experiment"])
            return {"stub": True}

        stdout = StringIO()
        with patch("core.runner.run_optimizer_headless", side_effect=fake_optimizer):
            with redirect_stdout(stdout):
                self.assertEqual(
                    runner_main([
                        "--config",
                        "config/default.json",
                        "--optimizer",
                        "--optimizer-iterations",
                        "0",
                        "--experiment-config",
                        "config/experiment_phase6_mixed_length_sequences_smoke.json",
                        "--optimizer-timeout-generations",
                        "1",
                        "--json",
                    ]),
                    0,
                )

        payload = json.loads(stdout.getvalue())
        effective = captured[-1]
        self.assertEqual(effective.evaluation_timeout_generations, 1)
        self.assertEqual(
            [len(item.input_bytes) for item in effective.mappings],
            [1, 2, 3],
        )
        self.assertEqual(
            payload["optimizer_protocol"]["mapping_input_lengths"],
            [1, 2, 3],
        )
        self.assertEqual(
            payload["optimizer_protocol"]["mapping_output_event_counts"],
            [1, 2, 3],
        )
        self.assertEqual(
            payload["optimizer_protocol"]["output_event_interval_generations"],
            2,
        )

    def test_p69_004_runner_reports_truthful_mixed_length_byte_evidence(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(
                runner_main([
                    "--config",
                    "config/default.json",
                    "--experiment",
                    "--experiment-config",
                    "config/experiment_phase6_mixed_length_sequences_smoke.json",
                    "--json",
                ]),
                0,
            )

        payload = json.loads(stdout.getvalue())["experiment_measurement"]
        self.assertEqual(payload["mapping_input_lengths"], [1, 2, 3])
        self.assertEqual(
            payload["mapping_output_event_counts"],
            [1, 2, 3],
        )
        self.assertEqual(
            [item["input_bytes"] for item in payload["per_mapping"]],
            [
                [0x41],
                [0x43, 0x44],
                [0x47, 0x48, 0x49],
            ],
        )
        self.assertEqual(
            [item["output_bytes"] for item in payload["per_mapping"]],
            [
                [0x42],
                [0x45, 0x46],
                [0x4A, 0x4B, 0x4C],
            ],
        )
        self.assertEqual(payload["counterfactual_prefix"], [0x47, 0x48])
        self.assertEqual(
            payload["counterfactual_input_sequence"],
            [0x4D, 0x4E],
        )
        self.assertFalse(payload["learning_claim"])
        for seed_record in payload["per_seed"]:
            self.assertEqual(len(seed_record["mappings"]), 3)
            for mapping_record in seed_record["mappings"]:
                self.assertIsInstance(mapping_record["baseline_events"], list)
                self.assertIsInstance(mapping_record["trained_events"], list)

    def test_p69_005_mixed_length_mapped_inputs_must_be_prefix_free(self):
        with self.assertRaises(ValueError):
            ExperimentConfig(
                mappings=(
                    ByteMapping(0x41, 0x42),
                    ByteSequenceMapping(
                        (0x41, 0x43),
                        0x44,
                        output_bytes=(0x44, 0x45),
                    ),
                ),
                counterfactual_input_byte=0x4D,
                inter_input_generations=1,
                counterfactual_prefix=(0x41,),
                counterfactual_input_sequence=(0x4D, 0x4E),
                output_event_count=1,
                output_event_interval_generations=2,
            )


if __name__ == "__main__":
    unittest.main()
