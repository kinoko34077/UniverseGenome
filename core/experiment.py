"""Phase 4 external I/O episodes and isolated autonomous evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .io_bus import FixedOrgans, InputBus, OutputEdgeDetector, OutputEvent, read_output_signal
from .physics import PhysicsConfig, create_universe, step
from .state import UniverseState


@dataclass(frozen=True)
class ExperimentConfig:
    byte_hold_generations: int = 4
    byte_gap_generations: int = 4
    teacher_delay_generations: int = 4
    teacher_repetitions: int = 1
    evaluation_timeout_generations: int = 1024

    def __post_init__(self) -> None:
        for name in (
            "byte_hold_generations", "byte_gap_generations", "teacher_delay_generations",
            "teacher_repetitions", "evaluation_timeout_generations",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.teacher_repetitions < 1:
            raise ValueError("teacher_repetitions must be positive")

    def to_dict(self) -> dict[str, int]:
        return {
            "byte_hold_generations": self.byte_hold_generations,
            "byte_gap_generations": self.byte_gap_generations,
            "teacher_delay_generations": self.teacher_delay_generations,
            "teacher_repetitions": self.teacher_repetitions,
            "evaluation_timeout_generations": self.evaluation_timeout_generations,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ExperimentConfig":
        values = {
            name: mapping[name]
            for name in (
                "byte_hold_generations", "byte_gap_generations",
                "teacher_delay_generations", "teacher_repetitions",
                "evaluation_timeout_generations",
            )
            if mapping.get(name) is not None
        }
        return cls(**values)


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("experiment config must be an object")
    return ExperimentConfig.from_mapping(payload)


@dataclass(frozen=True)
class TrainingRecord:
    input_byte: int
    output_byte: int
    teacher_events: tuple[OutputEvent, ...]
    generation: int


@dataclass(frozen=True)
class EvaluationResult:
    expected_events: tuple[OutputEvent, ...]
    autonomous_events: tuple[OutputEvent, ...]
    success: bool
    clone_generation: int


@dataclass(frozen=True)
class SeedMeasurement:
    seed: int
    baseline: EvaluationResult
    trained: EvaluationResult


@dataclass(frozen=True)
class LearningMeasurement:
    seed_count: int
    baseline_successes: int
    trained_successes: int
    criterion: str
    learning_claim: bool
    per_seed: tuple[SeedMeasurement, ...]


def _clone_state(state: UniverseState) -> UniverseState:
    return UniverseState.from_snapshot(state.to_snapshot(), config=state.config)


def _torus_distance(first: int, second: int, size: int = 32) -> int:
    difference = abs(first - second) % size
    return min(difference, size - difference)


class IOExperiment:
    """External protocol wrapper; fixed organs are not stored as normal cells."""

    def __init__(self, state: UniverseState, *, experiment: ExperimentConfig | None = None) -> None:
        self.state = state
        self.experiment = experiment or ExperimentConfig()
        self.input_bus = InputBus()
        self.output_detector = OutputEdgeDetector()
        self.teacher_events: list[OutputEvent] = []

    def _nearby_slots(self, anchors: Iterable[tuple[int, int]]) -> tuple[int, ...]:
        anchor_values = tuple(anchors)
        if not anchor_values:
            return ()
        result = []
        for slot in self.state.active_slots():
            x = (self.state.x[slot] // 8) % 32
            y = (self.state.y[slot] // 8) % 32
            if any(
                _torus_distance(x, anchor[0]) <= 1 and _torus_distance(y, anchor[1]) <= 1
                for anchor in anchor_values
            ):
                result.append(slot)
        return tuple(result)

    def _advance(self, anchors: Iterable[tuple[int, int]] = ()) -> None:
        stimulus = self._nearby_slots(anchors)
        step(self.state, stimulus_slots=stimulus)

    def drive_input(self, value: int, *, valid: bool = True) -> None:
        self.input_bus.drive(value, valid=valid)

    def release_input(self) -> None:
        self.input_bus.release()

    def observe_output(self, *, valid: bool, value: int = 0, null: bool = False) -> list[OutputEvent]:
        return self.output_detector.observe(valid=valid, value=value, null=null)

    def observe_output_state(self) -> list[OutputEvent]:
        return self.output_detector.observe_signal(read_output_signal(self.state))

    @staticmethod
    def _teacher_coordinates(event: OutputEvent) -> tuple[tuple[int, int], ...]:
        coordinates = FixedOrgans.coordinates()
        result = [coordinates[FixedOrgans.output_valid]]
        if event.kind == "byte":
            result.extend(
                coordinates[f"OUT{bit}"]
                for bit in range(8)
                if int(event.value or 0) & (1 << bit)
            )
        elif event.kind == "null":
            result.append(coordinates[FixedOrgans.output_null])
        else:
            raise ValueError(f"unsupported teacher output event: {event.kind}")
        return tuple(result)

    def teacher_output(self, event: OutputEvent) -> None:
        """Apply teacher-side stimulation without passing the event to autonomous scoring."""
        self.teacher_events.append(event)
        self._advance(self._teacher_coordinates(event))

    def train_a_to_b_null(self, *, input_byte: int = 65, output_byte: int = 66) -> TrainingRecord:
        teacher_events: list[OutputEvent] = []
        for _ in range(self.experiment.teacher_repetitions):
            for _ in range(self.experiment.byte_hold_generations):
                self.drive_input(input_byte)
                self._advance(self.input_bus.signal_coordinates())
            for _ in range(self.experiment.byte_gap_generations):
                self.release_input()
                self._advance()
            for _ in range(self.experiment.teacher_delay_generations):
                self.release_input()
                self._advance()
            byte_event = OutputEvent.byte(output_byte)
            null_event = OutputEvent.null()
            self.teacher_output(byte_event)
            self.teacher_output(null_event)
            teacher_events.extend((byte_event, null_event))
        return TrainingRecord(
            input_byte=input_byte,
            output_byte=output_byte,
            teacher_events=tuple(teacher_events),
            generation=self.state.generation,
        )

    def evaluate_autonomous(
        self,
        *,
        input_byte: int = 65,
        expected: Iterable[OutputEvent] = (),
    ) -> EvaluationResult:
        clone = _clone_state(self.state)
        clone_experiment = IOExperiment(clone, experiment=self.experiment)
        observed: list[OutputEvent] = []
        for _ in range(self.experiment.byte_hold_generations):
            clone_experiment.drive_input(input_byte)
            clone_experiment._advance(clone_experiment.input_bus.signal_coordinates())
            observed.extend(clone_experiment.observe_output_state())
        for _ in range(self.experiment.byte_gap_generations):
            clone_experiment.release_input()
            clone_experiment._advance()
            observed.extend(clone_experiment.observe_output_state())
        for _ in range(self.experiment.evaluation_timeout_generations):
            clone_experiment.release_input()
            clone_experiment._advance()
            observed.extend(clone_experiment.observe_output_state())
        actual = tuple(observed)
        expected_tuple = tuple(expected)
        return EvaluationResult(
            expected_events=expected_tuple,
            autonomous_events=actual,
            success=actual == expected_tuple,
            clone_generation=clone.generation,
        )


def compare_baseline_trained(
    *,
    seeds: Iterable[int],
    config: PhysicsConfig | None = None,
    experiment: ExperimentConfig | None = None,
) -> LearningMeasurement:
    seed_values = tuple(int(seed) for seed in seeds)
    if not seed_values:
        raise ValueError("at least one seed is required")
    resolved = config or PhysicsConfig()
    protocol = experiment or ExperimentConfig()
    expected = (OutputEvent.byte(66), OutputEvent.null())
    measurements: list[SeedMeasurement] = []
    for seed in seed_values:
        baseline = IOExperiment(create_universe(seed=seed, config=resolved), experiment=protocol)
        baseline_result = baseline.evaluate_autonomous(input_byte=65, expected=expected)
        trained = IOExperiment(create_universe(seed=seed, config=resolved), experiment=protocol)
        trained.train_a_to_b_null(input_byte=65, output_byte=66)
        trained_result = trained.evaluate_autonomous(input_byte=65, expected=expected)
        measurements.append(SeedMeasurement(seed, baseline_result, trained_result))
    baseline_successes = sum(item.baseline.success for item in measurements)
    trained_successes = sum(item.trained.success for item in measurements)
    required = len(seed_values)
    criterion = "all seeds must autonomously emit B then NULL after training and trained successes must exceed baseline"
    return LearningMeasurement(
        seed_count=len(seed_values),
        baseline_successes=baseline_successes,
        trained_successes=trained_successes,
        criterion=criterion,
        learning_claim=trained_successes >= required and trained_successes > baseline_successes,
        per_seed=tuple(measurements),
    )
