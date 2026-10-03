from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from core.experiment import (
    ExperimentConfig,
    FixedOrgans,
    IOExperiment,
    compare_baseline_trained,
)
from core.io_bus import InputBus, OutputEdgeDetector, OutputEvent, validate_byte
from core.physics import PhysicsConfig, create_universe
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
        self.assertEqual(status["next_phase"], "Phase 5 UniverseGenome optimizer")
        self.assertTrue(raw["features"]["io_learning"])
        self.assertFalse(raw["features"]["evolution"])
        with (ROOT / "config" / "experiment_v0_1.json").open(encoding="utf-8") as handle:
            experiment = json.load(handle)
        self.assertEqual(experiment["status"], "implemented_phase4_learning_outcome_recorded")


if __name__ == "__main__":
    unittest.main()
