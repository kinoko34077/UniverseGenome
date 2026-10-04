"""Phase 4 external I/O episodes and isolated autonomous evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .io_bus import (
    FixedOrgans,
    InputBus,
    OutputEdgeDetector,
    OutputEvent,
    read_output_signal,
    validate_byte,
)
from .physics import PhysicsConfig, StepMetrics, create_universe, destination_footprint, step
from .state import UniverseState


@dataclass(frozen=True, order=True)
class ByteMapping:
    input_byte: int
    output_byte: int

    def __post_init__(self) -> None:
        validate_byte(self.input_byte)
        validate_byte(self.output_byte)

    def to_dict(self) -> dict[str, int]:
        return {
            "input_byte": int(self.input_byte),
            "output_byte": int(self.output_byte),
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ByteMapping":
        return cls(
            input_byte=int(mapping["input_byte"]),
            output_byte=int(mapping["output_byte"]),
        )


DEFAULT_BYTE_MAPPINGS = (ByteMapping(65, 66),)


@dataclass(frozen=True)
class ExperimentConfig:
    byte_hold_generations: int = 4
    byte_gap_generations: int = 4
    teacher_delay_generations: int = 4
    teacher_repetitions: int = 1
    evaluation_timeout_generations: int = 1024
    mappings: tuple[ByteMapping, ...] = DEFAULT_BYTE_MAPPINGS
    counterfactual_input_byte: int = 66

    def __post_init__(self) -> None:
        for name in (
            "byte_hold_generations", "byte_gap_generations", "teacher_delay_generations",
            "teacher_repetitions", "evaluation_timeout_generations",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.teacher_repetitions < 1:
            raise ValueError("teacher_repetitions must be positive")
        if not self.mappings:
            raise ValueError("at least one byte mapping is required")
        if any(not isinstance(item, ByteMapping) for item in self.mappings):
            raise ValueError("mappings must contain ByteMapping values")
        inputs = tuple(item.input_byte for item in self.mappings)
        if len(set(inputs)) != len(inputs):
            raise ValueError("mapping input bytes must be unique")
        validate_byte(self.counterfactual_input_byte)
        if self.counterfactual_input_byte in set(inputs):
            raise ValueError("counterfactual input byte must be unmapped")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "byte_hold_generations": self.byte_hold_generations,
            "byte_gap_generations": self.byte_gap_generations,
            "teacher_delay_generations": self.teacher_delay_generations,
            "teacher_repetitions": self.teacher_repetitions,
            "evaluation_timeout_generations": self.evaluation_timeout_generations,
        }
        if (
            self.mappings != DEFAULT_BYTE_MAPPINGS
            or self.counterfactual_input_byte != 66
        ):
            payload["mappings"] = [item.to_dict() for item in self.mappings]
            payload["counterfactual_input_byte"] = self.counterfactual_input_byte
        return payload

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ExperimentConfig":
        values: dict[str, Any] = {
            name: mapping[name]
            for name in (
                "byte_hold_generations", "byte_gap_generations",
                "teacher_delay_generations", "teacher_repetitions",
                "evaluation_timeout_generations",
            )
            if mapping.get(name) is not None
        }
        if mapping.get("mappings") is not None:
            raw_mappings = mapping["mappings"]
            if not isinstance(raw_mappings, (list, tuple)):
                raise ValueError("mappings must be an array")
            values["mappings"] = tuple(
                ByteMapping.from_mapping(item)
                for item in raw_mappings
            )
        if mapping.get("counterfactual_input_byte") is not None:
            values["counterfactual_input_byte"] = int(
                mapping["counterfactual_input_byte"]
            )
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
    event_generations: tuple[int, ...] = ()
    evaluation_generations: int = 0
    activity_cost: int = 0
    timed_out: bool = False

    @property
    def wrong_output_count(self) -> int:
        expected_index = 0
        wrong = 0
        for event in self.autonomous_events:
            if (
                expected_index < len(self.expected_events)
                and event == self.expected_events[expected_index]
            ):
                expected_index += 1
            else:
                wrong += 1
        return wrong

    @property
    def response_latency(self) -> int:
        if not self.expected_events:
            return 0
        expected_index = 0
        for event, generation in zip(self.autonomous_events, self.event_generations):
            if event != self.expected_events[expected_index]:
                continue
            if expected_index == 0:
                return int(generation)
            expected_index += 1
        return int(self.evaluation_generations)


@dataclass(frozen=True)
class MappingSeedMeasurement:
    mapping: ByteMapping
    baseline: EvaluationResult
    trained: EvaluationResult


@dataclass(frozen=True)
class MappingMeasurement:
    mapping: ByteMapping
    baseline_successes: int
    trained_successes: int


@dataclass(frozen=True)
class SeedMeasurement:
    seed: int
    baseline: EvaluationResult
    trained: EvaluationResult
    baseline_no_input: EvaluationResult
    trained_no_input: EvaluationResult
    baseline_alternate: EvaluationResult
    trained_alternate: EvaluationResult
    mapping_results: tuple[MappingSeedMeasurement, ...] = ()

    @property
    def baseline_evaluations(self) -> tuple[EvaluationResult, ...]:
        if self.mapping_results:
            return tuple(item.baseline for item in self.mapping_results)
        return (self.baseline,)

    @property
    def trained_evaluations(self) -> tuple[EvaluationResult, ...]:
        if self.mapping_results:
            return tuple(item.trained for item in self.mapping_results)
        return (self.trained,)


@dataclass(frozen=True)
class LearningMeasurement:
    seed_count: int
    baseline_successes: int
    trained_successes: int
    baseline_no_input_clean: int
    trained_no_input_clean: int
    baseline_alternate_input_clean: int
    trained_alternate_input_clean: int
    criterion: str
    learning_claim: bool
    per_seed: tuple[SeedMeasurement, ...]
    mapping_count: int = 1
    counterfactual_input_byte: int = 66
    per_mapping: tuple[MappingMeasurement, ...] = ()

    @property
    def no_input_clean(self) -> int:
        return self.trained_no_input_clean

    @property
    def alternate_input_clean(self) -> int:
        return self.trained_alternate_input_clean

    @property
    def evaluation_case_count(self) -> int:
        return self.seed_count * self.mapping_count

    @property
    def evaluation_generations(self) -> int:
        return max(
            (
                result.evaluation_generations
                for item in self.per_seed
                for result in item.trained_evaluations
            ),
            default=0,
        )


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
            footprint = destination_footprint(
                self.state.structure[slot], self.state.x[slot], self.state.y[slot]
            )
            if any(
                _torus_distance(tile_x, anchor[0]) <= 1
                and _torus_distance(tile_y, anchor[1]) <= 1
                for tile_x, tile_y in footprint
                for anchor in anchor_values
            ):
                result.append(slot)
        return tuple(result)

    def _advance(self, anchors: Iterable[tuple[int, int]] = ()) -> Any:
        stimulus = self._nearby_slots(anchors)
        return step(self.state, stimulus_slots=stimulus)

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

    def teacher_output(
        self,
        event: OutputEvent,
        *,
        on_generation: Callable[[int], None] | None = None,
        on_step: Callable[[int, StepMetrics], None] | None = None,
    ) -> None:
        """Apply teacher-side stimulation without passing the event to autonomous scoring."""
        self.teacher_events.append(event)
        metrics = self._advance(self._teacher_coordinates(event))
        if on_step is not None:
            on_step(self.state.generation, metrics)
        if on_generation is not None:
            on_generation(self.state.generation)

    def _train_mapping_once(
        self,
        mapping: ByteMapping,
        *,
        on_generation: Callable[[int], None] | None = None,
        on_step: Callable[[int, StepMetrics], None] | None = None,
    ) -> TrainingRecord:
        def advance(anchors: Iterable[tuple[int, int]]) -> None:
            metrics = self._advance(anchors)
            if on_step is not None:
                on_step(self.state.generation, metrics)
            if on_generation is not None:
                on_generation(self.state.generation)

        for _ in range(self.experiment.byte_hold_generations):
            self.drive_input(mapping.input_byte)
            advance(self.input_bus.signal_coordinates())
        for _ in range(self.experiment.byte_gap_generations):
            self.release_input()
            advance(())
        for _ in range(self.experiment.teacher_delay_generations):
            self.release_input()
            advance(())
        byte_event = OutputEvent.byte(mapping.output_byte)
        null_event = OutputEvent.null()
        self.teacher_output(
            byte_event,
            on_generation=on_generation,
            on_step=on_step,
        )
        self.teacher_output(
            null_event,
            on_generation=on_generation,
            on_step=on_step,
        )
        return TrainingRecord(
            input_byte=mapping.input_byte,
            output_byte=mapping.output_byte,
            teacher_events=(byte_event, null_event),
            generation=self.state.generation,
        )

    def train_mappings(
        self,
        *,
        on_generation: Callable[[int], None] | None = None,
        on_step: Callable[[int, StepMetrics], None] | None = None,
    ) -> tuple[TrainingRecord, ...]:
        records: list[TrainingRecord] = []
        for _ in range(self.experiment.teacher_repetitions):
            for mapping in self.experiment.mappings:
                records.append(
                    self._train_mapping_once(
                        mapping,
                        on_generation=on_generation,
                        on_step=on_step,
                    )
                )
        return tuple(records)

    def train_a_to_b_null(
        self,
        *,
        input_byte: int = 65,
        output_byte: int = 66,
        on_generation: Callable[[int], None] | None = None,
        on_step: Callable[[int, StepMetrics], None] | None = None,
    ) -> TrainingRecord:
        mapping = ByteMapping(input_byte, output_byte)
        teacher_events: list[OutputEvent] = []
        last_generation = self.state.generation
        for _ in range(self.experiment.teacher_repetitions):
            record = self._train_mapping_once(
                mapping,
                on_generation=on_generation,
                on_step=on_step,
            )
            teacher_events.extend(record.teacher_events)
            last_generation = record.generation
        return TrainingRecord(
            input_byte=input_byte,
            output_byte=output_byte,
            teacher_events=tuple(teacher_events),
            generation=last_generation,
        )

    def evaluate_autonomous(
        self,
        *,
        input_byte: int = 65,
        input_valid: bool = True,
        expected: Iterable[OutputEvent] = (),
    ) -> EvaluationResult:
        clone = _clone_state(self.state)
        clone_experiment = IOExperiment(clone, experiment=self.experiment)
        clone_experiment.output_detector.prime_signal(read_output_signal(clone))
        observed: list[OutputEvent] = []
        event_generations: list[int] = []
        evaluation_generations = 0
        activity_cost = 0

        def advance_and_observe(anchors: Iterable[tuple[int, int]]) -> None:
            nonlocal evaluation_generations, activity_cost
            metrics = clone_experiment._advance(anchors)
            evaluation_generations += 1
            activity_cost += metrics.activity_cost
            events = clone_experiment.observe_output_state()
            observed.extend(events)
            event_generations.extend([evaluation_generations] * len(events))

        for _ in range(self.experiment.byte_hold_generations):
            if input_valid:
                clone_experiment.drive_input(input_byte)
            else:
                clone_experiment.release_input()
            advance_and_observe(clone_experiment.input_bus.signal_coordinates())
        for _ in range(self.experiment.byte_gap_generations):
            clone_experiment.release_input()
            advance_and_observe(())
        for _ in range(self.experiment.evaluation_timeout_generations):
            clone_experiment.release_input()
            advance_and_observe(())
        actual = tuple(observed)
        expected_tuple = tuple(expected)
        expected_index = 0
        for event in actual:
            if expected_index < len(expected_tuple) and event == expected_tuple[expected_index]:
                expected_index += 1
        return EvaluationResult(
            expected_events=expected_tuple,
            autonomous_events=actual,
            success=actual == expected_tuple,
            clone_generation=clone.generation,
            event_generations=tuple(event_generations),
            evaluation_generations=evaluation_generations,
            activity_cost=activity_cost,
            timed_out=expected_index < len(expected_tuple),
        )


def _seed_measurement(
    *,
    seed: int,
    baseline_state: UniverseState,
    trained_state: UniverseState,
    protocol: ExperimentConfig,
) -> SeedMeasurement:
    baseline = IOExperiment(baseline_state, experiment=protocol)
    trained = IOExperiment(trained_state, experiment=protocol)
    mapping_results: list[MappingSeedMeasurement] = []

    for mapping in protocol.mappings:
        expected = (OutputEvent.byte(mapping.output_byte), OutputEvent.null())
        mapping_results.append(
            MappingSeedMeasurement(
                mapping=mapping,
                baseline=baseline.evaluate_autonomous(
                    input_byte=mapping.input_byte,
                    expected=expected,
                ),
                trained=trained.evaluate_autonomous(
                    input_byte=mapping.input_byte,
                    expected=expected,
                ),
            )
        )

    first = mapping_results[0]
    baseline_no_input = baseline.evaluate_autonomous(
        input_byte=protocol.mappings[0].input_byte,
        input_valid=False,
        expected=(),
    )
    trained_no_input = trained.evaluate_autonomous(
        input_byte=protocol.mappings[0].input_byte,
        input_valid=False,
        expected=(),
    )
    baseline_alternate = baseline.evaluate_autonomous(
        input_byte=protocol.counterfactual_input_byte,
        expected=(),
    )
    trained_alternate = trained.evaluate_autonomous(
        input_byte=protocol.counterfactual_input_byte,
        expected=(),
    )
    return SeedMeasurement(
        seed=seed,
        baseline=first.baseline,
        trained=first.trained,
        baseline_no_input=baseline_no_input,
        trained_no_input=trained_no_input,
        baseline_alternate=baseline_alternate,
        trained_alternate=trained_alternate,
        mapping_results=tuple(mapping_results),
    )


def _assemble_learning_measurement(
    measurements: Iterable[SeedMeasurement],
    *,
    mappings: Iterable[ByteMapping] = DEFAULT_BYTE_MAPPINGS,
    counterfactual_input_byte: int = 66,
) -> LearningMeasurement:
    records = tuple(measurements)
    if not records:
        raise ValueError("at least one seed measurement is required")
    mapping_values = tuple(mappings)
    if not mapping_values:
        raise ValueError("at least one byte mapping is required")

    baseline_successes = sum(
        result.success
        for item in records
        for result in item.baseline_evaluations
    )
    trained_successes = sum(
        result.success
        for item in records
        for result in item.trained_evaluations
    )
    baseline_no_input_clean = sum(item.baseline_no_input.success for item in records)
    trained_no_input_clean = sum(item.trained_no_input.success for item in records)
    baseline_alternate_input_clean = sum(item.baseline_alternate.success for item in records)
    trained_alternate_input_clean = sum(item.trained_alternate.success for item in records)
    seed_count = len(records)
    required_cases = seed_count * len(mapping_values)

    per_mapping = tuple(
        MappingMeasurement(
            mapping=mapping,
            baseline_successes=sum(
                item.mapping_results[index].baseline.success
                for item in records
            ),
            trained_successes=sum(
                item.mapping_results[index].trained.success
                for item in records
            ),
        )
        for index, mapping in enumerate(mapping_values)
    )

    if len(mapping_values) == 1:
        criterion = (
            "all seeds must autonomously emit B then NULL after training, trained successes must exceed baseline, "
            "and no-input/alternate-input counterfactuals must remain output-clean"
        )
    else:
        criterion = (
            "all mappings across all seeds must autonomously emit each declared output byte then NULL after training, "
            "trained successes must exceed baseline, and no-input/unmapped-input counterfactuals must remain output-clean"
        )

    return LearningMeasurement(
        seed_count=seed_count,
        baseline_successes=baseline_successes,
        trained_successes=trained_successes,
        baseline_no_input_clean=baseline_no_input_clean,
        trained_no_input_clean=trained_no_input_clean,
        baseline_alternate_input_clean=baseline_alternate_input_clean,
        trained_alternate_input_clean=trained_alternate_input_clean,
        criterion=criterion,
        learning_claim=(
            trained_successes >= required_cases
            and trained_successes > baseline_successes
            and trained_no_input_clean >= seed_count
            and trained_alternate_input_clean >= seed_count
        ),
        per_seed=records,
        mapping_count=len(mapping_values),
        counterfactual_input_byte=counterfactual_input_byte,
        per_mapping=per_mapping,
    )


def measure_trained_state(
    state: UniverseState,
    *,
    experiment: ExperimentConfig | None = None,
) -> LearningMeasurement:
    """Measure a current authoritative training state through disposable clones."""
    protocol = experiment or ExperimentConfig()
    resolved = state.config or PhysicsConfig()
    measurement = _seed_measurement(
        seed=state.seed,
        baseline_state=create_universe(seed=state.seed, config=resolved),
        trained_state=state,
        protocol=protocol,
    )
    return _assemble_learning_measurement(
        (measurement,),
        mappings=protocol.mappings,
        counterfactual_input_byte=protocol.counterfactual_input_byte,
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
    measurements: list[SeedMeasurement] = []
    for seed in seed_values:
        baseline_state = create_universe(seed=seed, config=resolved)
        trained_state = create_universe(seed=seed, config=resolved)
        IOExperiment(trained_state, experiment=protocol).train_mappings()
        measurements.append(
            _seed_measurement(
                seed=seed,
                baseline_state=baseline_state,
                trained_state=trained_state,
                protocol=protocol,
            )
        )
    return _assemble_learning_measurement(
        measurements,
        mappings=protocol.mappings,
        counterfactual_input_byte=protocol.counterfactual_input_byte,
    )
