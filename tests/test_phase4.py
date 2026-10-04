from __future__ import annotations

import json
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core import experiment as experiment_module
from core.experiment import (
    ExperimentConfig,
    EvaluationResult,
    FixedOrgans,
    IOExperiment,
    compare_baseline_trained,
)
from core.io_bus import InputBus, OutputEdgeDetector, OutputEvent, read_output_signal, validate_byte
from core.physics import PhysicsConfig, StepMetrics, create_universe, destination_footprint, step
from core.state import SHAPE_HORIZONTAL
from core.runner import build_status, load_config


ROOT = Path(__file__).resolve().parents[1]


def experiment_physics_config(**overrides):
    values = {
        "max_cells": 16,
        "hp_decay": 0,
        "bond_gain": 0,
        "bond_decay": 0,
    }
    values.update(overrides)
    return PhysicsConfig(**values)


class Phase4IOTests(unittest.TestCase):
    def test_p4_001_raw_bytes_and_fixed_organs(self):
        self.assertEqual(validate_byte(0), 0)
        self.assertEqual(validate_byte(255), 255)
        with self.assertRaises(ValueError):
            validate_byte(256)
        self.assertEqual(FixedOrgans.input_anchor[0], 8)
        self.assertEqual(FixedOrgans.output_anchor[0], 24)
        self.assertNotEqual(FixedOrgans.input_anchor, FixedOrgans.output_anchor)
        self.assertEqual(set(FixedOrgans.coordinates()), set(FixedOrgans.all_names()))
        self.assertEqual(FixedOrgans.coordinates()["IN0"], (8, 12))
        self.assertEqual(FixedOrgans.coordinates()["OUT7"], (24, 19))

        bus = InputBus()
        self.assertEqual(bus.drive(0, valid=True).value, 0)
        self.assertTrue(bus.signal.valid)
        self.assertEqual(bus.signal.value, 0)

    def test_p4_002_output_events_are_rising_edge_only(self):
        detector = OutputEdgeDetector()
        self.assertEqual(detector.observe(valid=False, value=66), [])
        self.assertEqual(detector.observe(valid=True, value=66), [OutputEvent.byte(66)])
        self.assertEqual(detector.observe(valid=True, value=67), [])
        self.assertEqual(detector.observe(valid=False, value=67), [])
        self.assertEqual(detector.observe(valid=True, value=67), [OutputEvent.byte(67)])
        self.assertEqual(detector.observe(valid=False, null=True), [])
        self.assertEqual(detector.observe(valid=True, null=True), [OutputEvent.null()])

    def test_p4_003_teacher_events_are_not_autonomous(self):
        experiment = IOExperiment(
            create_universe(seed=81, config=experiment_physics_config()),
            experiment=ExperimentConfig(teacher_delay_generations=1),
        )
        trained_before = experiment.state.to_snapshot()
        record = experiment.train_a_to_b_null(input_byte=65, output_byte=66)
        self.assertEqual(record.teacher_events, (OutputEvent.byte(66), OutputEvent.null()))
        evaluation = experiment.evaluate_autonomous(input_byte=65, expected=(OutputEvent.byte(66), OutputEvent.null()))
        self.assertEqual(evaluation.autonomous_events, ())
        self.assertFalse(evaluation.success)
        self.assertNotEqual(experiment.state.to_snapshot(), trained_before)

    def test_p4_004_evaluation_clone_does_not_mutate_training_state(self):
        experiment = IOExperiment(
            create_universe(seed=82, config=experiment_physics_config()),
            experiment=ExperimentConfig(evaluation_timeout_generations=4),
        )
        experiment.train_a_to_b_null(input_byte=65, output_byte=66)
        before = experiment.state.to_snapshot()
        generation = experiment.state.generation
        result = experiment.evaluate_autonomous(input_byte=65, expected=())
        self.assertEqual(result.autonomous_events, ())
        self.assertEqual(experiment.state.to_snapshot(), before)
        self.assertEqual(experiment.state.generation, generation)

    def test_p4_005_multi_seed_baseline_and_trained_measurement_is_explicit(self):
        measurement = compare_baseline_trained(
            seeds=(83, 84, 85),
            config=experiment_physics_config(),
            experiment=ExperimentConfig(teacher_delay_generations=1, evaluation_timeout_generations=4),
        )
        self.assertEqual(measurement.seed_count, 3)
        self.assertEqual(measurement.baseline_successes, 0)
        self.assertEqual(measurement.trained_successes, 0)
        self.assertFalse(measurement.learning_claim)
        self.assertIn("all seeds", measurement.criterion)

    def test_p4_006_status_and_config(self):
        raw = load_config(ROOT / "config" / "default.json")
        status = build_status(raw)
        self.assertTrue(status["phase4_io_learning_implemented"])
        self.assertEqual(status["next_phase"], "Phase 6.3 multi-event output timing (bounded child Issue required)")
        self.assertTrue(raw["features"]["io_learning"])
        self.assertTrue(raw["features"]["evolution"])
        with (ROOT / "config" / "experiment_v0_1.json").open(encoding="utf-8") as handle:
            experiment = json.load(handle)
        self.assertEqual(experiment["status"], "implemented_phase4_learning_outcome_recorded")

    def test_p4_007_autonomous_evaluation_collects_real_output_edges(self):
        state = create_universe(
            seed=91,
            config=experiment_physics_config(
                fusion_enabled=False,
                fragmentation_enabled=False,
            ),
        )
        coordinates = FixedOrgans.coordinates()
        for bit in (1, 6):  # byte 66 (B)
            x, y = coordinates[f"OUT{bit}"]
            state.spawn(x=x * 8, y=y * 8, hp=255, speed_code=0)
        x, y = coordinates[FixedOrgans.output_valid]
        state.spawn(x=x * 8, y=y * 8, hp=255, speed_code=0)

        result = IOExperiment(
            state,
            experiment=ExperimentConfig(evaluation_timeout_generations=3),
        ).evaluate_autonomous(input_byte=65, expected=(OutputEvent.byte(66),))

        self.assertEqual(result.autonomous_events, ())
        self.assertFalse(result.success)

    def test_p4_009_persistent_high_at_evaluation_start_is_not_a_new_edge(self):
        detector = OutputEdgeDetector()
        detector.prime(valid=True, value=66)
        self.assertEqual(detector.observe(valid=True, value=66), [])
        detector.observe(valid=False)
        self.assertEqual(detector.observe(valid=True, value=67), [OutputEvent.byte(67)])

    def test_p4_010_initial_and_noise_spawns_avoid_fixed_organ_footprints(self):
        config = experiment_physics_config(
            max_cells=64,
            initial_density=32,
            noise_rate=0xFFFF,
            noise_structure=SHAPE_HORIZONTAL,
            noise_speed_code=0,
            initial_speed_code=0,
        )
        state = create_universe(seed=92, config=config)
        fixed = set(FixedOrgans.coordinates().values())
        for slot in state.active_slots():
            self.assertTrue(destination_footprint(state.structure[slot], state.x[slot], state.y[slot]).isdisjoint(fixed))
        for _ in range(32):
            step(state)
        self.assertEqual(len(state.active_slots()), 64)
        for slot in state.active_slots():
            self.assertTrue(destination_footprint(state.structure[slot], state.x[slot], state.y[slot]).isdisjoint(fixed))

    def test_p4_011_io_uses_compound_cell_footprint(self):
        state = create_universe(seed=93, config=experiment_physics_config())
        state.spawn(x=23 * 8, y=12 * 8, structure=SHAPE_HORIZONTAL, speed_code=0)
        signal = read_output_signal(state)
        self.assertEqual(signal.value, 1)

        state.spawn(x=6 * 8, y=12 * 8, structure=SHAPE_HORIZONTAL, speed_code=0)
        experiment = IOExperiment(state)
        nearby = experiment._nearby_slots(((8, 12),))
        self.assertEqual(nearby, (1,))

    def test_p4_012_learning_measurement_requires_counterfactuals(self):
        measurement = compare_baseline_trained(
            seeds=(94, 95),
            config=experiment_physics_config(),
            experiment=ExperimentConfig(teacher_delay_generations=1, evaluation_timeout_generations=2),
        )
        self.assertEqual(measurement.no_input_clean, 2)
        self.assertEqual(measurement.alternate_input_clean, 2)
        self.assertIn("no-input", measurement.criterion)
        self.assertIn("alternate-input", measurement.criterion)

    def test_p4_008_experiment_config_is_explicit_and_loadable(self):
        loader = getattr(experiment_module, "load_experiment_config", None)
        self.assertIsNotNone(loader)
        config = loader(ROOT / "config" / "experiment_v0_1.json")

        self.assertEqual(config, ExperimentConfig(
            byte_hold_generations=4,
            byte_gap_generations=4,
            teacher_delay_generations=4,
            teacher_repetitions=1,
            evaluation_timeout_generations=1024,
        ))

    def test_p4_013_evaluation_result_reports_named_observables(self):
        metrics = StepMetrics(
            generation=1,
            active_cells=2,
            collision_count=1,
            collision_pair_evaluations=1,
            bond_contact_count=2,
            latent_transmission_count=3,
            fusion_count=4,
            fragmentation_count=5,
            noise_spawn_count=6,
            generations_per_second=1.0,
        )
        self.assertEqual(metrics.activity_cost, 21)

        result = EvaluationResult(
            expected_events=(OutputEvent.byte(66), OutputEvent.null()),
            autonomous_events=(OutputEvent.byte(65), OutputEvent.byte(66)),
            success=False,
            clone_generation=8,
            event_generations=(3, 5),
            evaluation_generations=8,
            activity_cost=11,
            timed_out=True,
        )

        self.assertEqual(result.wrong_output_count, 1)
        self.assertEqual(result.response_latency, 5)
        self.assertEqual(result.activity_cost, 11)
        self.assertTrue(result.timed_out)

    def test_p4_014_timeout_and_evaluation_cadence_are_explicit(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            evaluation_timeout_generations=3,
        )
        result = IOExperiment(
            create_universe(seed=96, config=experiment_physics_config()),
            experiment=protocol,
        ).evaluate_autonomous(input_byte=65, expected=(OutputEvent.byte(66),))

        self.assertEqual(result.evaluation_generations, 3)
        self.assertTrue(result.timed_out)
        self.assertEqual(result.response_latency, 3)

    def test_p4_015_training_callback_observes_each_authoritative_generation(self):
        self.assertIn("on_generation", inspect.signature(IOExperiment.train_a_to_b_null).parameters)
        state = create_universe(seed=97, config=experiment_physics_config())
        seen = []
        IOExperiment(
            state,
            experiment=ExperimentConfig(
                byte_hold_generations=2,
                byte_gap_generations=1,
                teacher_delay_generations=1,
            ),
        ).train_a_to_b_null(on_generation=seen.append)

        self.assertEqual(seen, list(range(1, 7)))
        self.assertEqual(state.generation, 6)

    def test_p4_016_current_state_measurement_is_clone_only(self):
        self.assertTrue(callable(getattr(experiment_module, "measure_trained_state", None)))
        state = create_universe(seed=98, config=experiment_physics_config())
        before = state.to_snapshot()
        measurement = experiment_module.measure_trained_state(
            state,
            experiment=ExperimentConfig(evaluation_timeout_generations=3),
        )

        self.assertEqual(state.to_snapshot(), before)
        self.assertEqual(measurement.seed_count, 1)
        self.assertEqual(measurement.per_seed[0].trained.evaluation_generations, 11)


    def test_p6_001_multi_mapping_protocol_is_serializable_and_rejects_ambiguity(self):
        ByteMapping = getattr(experiment_module, "ByteMapping")
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

        payload = protocol.to_dict()
        self.assertEqual(
            payload["mappings"],
            [
                {"input_byte": 65, "output_byte": 66},
                {"input_byte": 67, "output_byte": 68},
            ],
        )
        self.assertEqual(payload["counterfactual_input_byte"], 66)
        self.assertEqual(ExperimentConfig.from_mapping(payload), protocol)

        with self.assertRaises(ValueError):
            ExperimentConfig(
                mappings=(
                    ByteMapping(65, 66),
                    ByteMapping(65, 68),
                ),
            )
        with self.assertRaises(ValueError):
            ExperimentConfig(
                mappings=(
                    ByteMapping(65, 66),
                    ByteMapping(67, 68),
                ),
                counterfactual_input_byte=67,
            )

    def test_p6_002_declared_mappings_train_one_authoritative_state_in_order(self):
        ByteMapping = getattr(experiment_module, "ByteMapping")
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
        state = create_universe(seed=301, config=experiment_physics_config())
        io = IOExperiment(state, experiment=protocol)

        records = io.train_mappings()

        self.assertEqual(
            [(item.input_byte, item.output_byte) for item in records],
            [(65, 66), (67, 68)],
        )
        self.assertEqual(
            io.teacher_events,
            [
                OutputEvent.byte(66),
                OutputEvent.null(),
                OutputEvent.byte(68),
                OutputEvent.null(),
            ],
        )
        self.assertEqual(state.generation, 6)

    def test_p6_003_multi_mapping_measurement_is_mapping_specific_and_clone_only(self):
        ByteMapping = getattr(experiment_module, "ByteMapping")
        protocol = ExperimentConfig(
            byte_hold_generations=0,
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

        measurement = compare_baseline_trained(
            seeds=(302, 303),
            config=experiment_physics_config(),
            experiment=protocol,
        )

        self.assertEqual(measurement.seed_count, 2)
        self.assertEqual(measurement.mapping_count, 2)
        self.assertEqual(measurement.evaluation_case_count, 4)
        self.assertEqual(measurement.counterfactual_input_byte, 66)
        self.assertEqual(
            [
                (item.mapping.input_byte, item.mapping.output_byte)
                for item in measurement.per_mapping
            ],
            [(65, 66), (67, 68)],
        )
        self.assertEqual(
            [
                (item.mapping.input_byte, item.mapping.output_byte)
                for item in measurement.per_seed[0].mapping_results
            ],
            [(65, 66), (67, 68)],
        )
        self.assertTrue(
            all(
                item.baseline.expected_events
                == (OutputEvent.byte(item.mapping.output_byte), OutputEvent.null())
                and item.trained.expected_events
                == (OutputEvent.byte(item.mapping.output_byte), OutputEvent.null())
                for seed in measurement.per_seed
                for item in seed.mapping_results
            )
        )
        self.assertEqual(measurement.trained_successes, 0)
        self.assertFalse(measurement.learning_claim)
        self.assertIn("all mappings", measurement.criterion)
        self.assertIn("unmapped-input", measurement.criterion)

    def test_p6_004_measure_trained_state_does_not_mutate_authority_for_two_mappings(self):
        ByteMapping = getattr(experiment_module, "ByteMapping")
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=1,
            mappings=(
                ByteMapping(65, 66),
                ByteMapping(67, 68),
            ),
            counterfactual_input_byte=66,
        )
        state = create_universe(seed=304, config=experiment_physics_config())
        IOExperiment(state, experiment=protocol).train_mappings()
        before = state.to_snapshot()

        measurement = experiment_module.measure_trained_state(
            state,
            experiment=protocol,
        )

        self.assertEqual(state.to_snapshot(), before)
        self.assertEqual(measurement.mapping_count, 2)
        self.assertEqual(len(measurement.per_seed[0].mapping_results), 2)


    def test_p6_006_phase6_multi_mapping_config_is_explicit_and_loadable(self):
        loader = getattr(experiment_module, "load_experiment_config")
        ByteMapping = getattr(experiment_module, "ByteMapping")
        config = loader(ROOT / "config" / "experiment_phase6_multi_mapping.json")

        self.assertEqual(
            config.mappings,
            (
                ByteMapping(65, 66),
                ByteMapping(67, 68),
            ),
        )
        self.assertEqual(config.counterfactual_input_byte, 66)
        self.assertEqual(config.evaluation_timeout_generations, 1024)


    def test_p62_001_two_byte_sequence_protocol_serializes_timing_and_controls(self):
        ByteSequenceMapping = getattr(experiment_module, "ByteSequenceMapping")
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
            inter_input_generations=2,
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
        )

        payload = protocol.to_dict()
        self.assertEqual(
            payload["mappings"],
            [
                {"input_bytes": [65, 65], "output_byte": 66},
                {"input_bytes": [65, 67], "output_byte": 68},
            ],
        )
        self.assertEqual(payload["inter_input_generations"], 2)
        self.assertEqual(payload["counterfactual_prefix"], [65])
        self.assertEqual(payload["counterfactual_input_sequence"], [67, 65])
        self.assertEqual(ExperimentConfig.from_mapping(payload), protocol)

        with self.assertRaises(ValueError):
            ByteSequenceMapping((65,), 66)
        with self.assertRaises(ValueError):
            ExperimentConfig(
                mappings=(
                    ByteSequenceMapping((65, 65), 66),
                    ByteSequenceMapping((65, 65), 68),
                ),
                counterfactual_prefix=(65,),
                counterfactual_input_sequence=(67, 65),
            )
        with self.assertRaises(ValueError):
            ExperimentConfig(
                mappings=(ByteSequenceMapping((65, 65), 66),),
                counterfactual_prefix=(65,),
                counterfactual_input_sequence=(65, 65),
            )

    def test_p62_002_sequence_training_completes_both_inputs_before_teacher_output(self):
        ByteSequenceMapping = getattr(experiment_module, "ByteSequenceMapping")
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            inter_input_generations=1,
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
        )
        state = create_universe(seed=401, config=experiment_physics_config())
        timeline = []

        class RecordingExperiment(IOExperiment):
            def drive_input(self, value, *, valid=True):
                timeline.append(("input", value, self.state.generation))
                return super().drive_input(value, valid=valid)

            def teacher_output(self, event, **kwargs):
                timeline.append(("teacher", event, self.state.generation))
                return super().teacher_output(event, **kwargs)

        io = RecordingExperiment(state, experiment=protocol)
        records = io.train_mappings()

        self.assertEqual(
            [item.input_bytes for item in records],
            [(65, 65), (65, 67)],
        )
        self.assertEqual(
            timeline[:4],
            [
                ("input", 65, 0),
                ("input", 65, 2),
                ("teacher", OutputEvent.byte(66), 3),
                ("teacher", OutputEvent.null(), 4),
            ],
        )
        self.assertEqual(
            timeline[4:],
            [
                ("input", 65, 5),
                ("input", 67, 7),
                ("teacher", OutputEvent.byte(68), 8),
                ("teacher", OutputEvent.null(), 9),
            ],
        )
        self.assertEqual(state.generation, 10)

    def test_p62_003_output_before_full_sequence_is_failure_even_when_event_tuple_matches(self):
        protocol = ExperimentConfig(
            byte_hold_generations=1,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            evaluation_timeout_generations=1,
            inter_input_generations=1,
        )
        io = IOExperiment(
            create_universe(seed=402, config=experiment_physics_config()),
            experiment=protocol,
        )
        expected = (OutputEvent.byte(66), OutputEvent.null())

        with patch.object(
            experiment_module.IOExperiment,
            "observe_output_state",
            side_effect=([OutputEvent.byte(66)], [], [], [OutputEvent.null()]),
        ):
            result = io.evaluate_autonomous_sequence(
                input_bytes=(65, 65),
                expected=expected,
            )

        self.assertEqual(result.autonomous_events, expected)
        self.assertEqual(result.input_complete_generation, 3)
        self.assertEqual(result.early_output_count, 1)
        self.assertGreater(result.wrong_output_count, 0)
        self.assertFalse(result.success)

    def test_p62_004_sequence_measurement_gates_prefix_and_unmapped_sequence_controls(self):
        ByteSequenceMapping = getattr(experiment_module, "ByteSequenceMapping")
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
            mappings=(
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
            inter_input_generations=0,
            counterfactual_prefix=(65,),
            counterfactual_input_sequence=(67, 65),
        )

        measurement = compare_baseline_trained(
            seeds=(403, 404),
            config=experiment_physics_config(),
            experiment=protocol,
        )

        self.assertEqual(measurement.mapping_count, 2)
        self.assertEqual(measurement.evaluation_case_count, 4)
        self.assertEqual(measurement.counterfactual_prefix, (65,))
        self.assertEqual(measurement.counterfactual_input_sequence, (67, 65))
        self.assertEqual(measurement.trained_prefix_input_clean, 2)
        self.assertEqual(measurement.trained_sequence_counterfactual_clean, 2)
        self.assertIn("prefix-only", measurement.criterion)
        self.assertIn("unmapped-sequence", measurement.criterion)
        self.assertFalse(measurement.learning_claim)


    def test_p62_005_temporal_sequence_config_is_explicit_and_loadable(self):
        loader = getattr(experiment_module, "load_experiment_config")
        ByteSequenceMapping = getattr(experiment_module, "ByteSequenceMapping")
        config = loader(
            ROOT / "config" / "experiment_phase6_temporal_sequence.json"
        )

        self.assertEqual(
            config.mappings,
            (
                ByteSequenceMapping((65, 65), 66),
                ByteSequenceMapping((65, 67), 68),
            ),
        )
        self.assertEqual(config.inter_input_generations, 4)
        self.assertEqual(config.counterfactual_prefix, (65,))
        self.assertEqual(config.counterfactual_input_sequence, (67, 65))
        self.assertEqual(config.evaluation_timeout_generations, 1024)


if __name__ == "__main__":
    unittest.main()
