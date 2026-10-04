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

    @property
    def input_bytes(self) -> tuple[int, ...]:
        return (int(self.input_byte),)

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


@dataclass(frozen=True, order=True)
class ByteSequenceMapping:
    input_bytes: tuple[int, ...]
    output_byte: int
    output_bytes: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        values = tuple(int(value) for value in self.input_bytes)
        explicit_outputs = tuple(int(value) for value in self.output_bytes)
        object.__setattr__(self, "input_bytes", values)
        object.__setattr__(self, "output_bytes", explicit_outputs)
        if len(values) not in (2, 3):
            raise ValueError("bounded sequence mappings require two or three input bytes")
        for value in values:
            validate_byte(value)
        validate_byte(self.output_byte)
        for value in explicit_outputs:
            validate_byte(value)
        if explicit_outputs:
            if len(explicit_outputs) not in (2, 3):
                raise ValueError(
                    "bounded explicit output sequences require two or three bytes"
                )
            if len(set(explicit_outputs)) != len(explicit_outputs):
                raise ValueError(
                    "bounded P6.7 explicit output sequence bytes must be distinct"
                )
            if explicit_outputs[0] != self.output_byte:
                raise ValueError(
                    "output_byte must equal the first explicit output sequence byte"
                )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "input_bytes": [int(value) for value in self.input_bytes],
            "output_byte": int(self.output_byte),
        }
        if self.output_bytes:
            payload["output_bytes"] = [int(value) for value in self.output_bytes]
        return payload

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ByteSequenceMapping":
        raw = mapping["input_bytes"]
        if not isinstance(raw, (list, tuple)):
            raise ValueError("input_bytes must be an array")
        raw_outputs = mapping.get("output_bytes", ())
        if not isinstance(raw_outputs, (list, tuple)):
            raise ValueError("output_bytes must be an array")
        return cls(
            input_bytes=tuple(int(value) for value in raw),
            output_byte=int(mapping["output_byte"]),
            output_bytes=tuple(int(value) for value in raw_outputs),
        )


ProtocolMapping = ByteMapping | ByteSequenceMapping


def _mapping_output_bytes(
    mapping: ProtocolMapping,
    output_event_count: int,
) -> tuple[int, ...]:
    if isinstance(mapping, ByteSequenceMapping) and mapping.output_bytes:
        return mapping.output_bytes
    return (mapping.output_byte,) * int(output_event_count)


DEFAULT_BYTE_MAPPINGS = (ByteMapping(65, 66),)


@dataclass(frozen=True)
class ExperimentConfig:
    byte_hold_generations: int = 4
    byte_gap_generations: int = 4
    teacher_delay_generations: int = 4
    teacher_repetitions: int = 1
    evaluation_timeout_generations: int = 1024
    mappings: tuple[ProtocolMapping, ...] = DEFAULT_BYTE_MAPPINGS
    counterfactual_input_byte: int = 66
    inter_input_generations: int = 0
    counterfactual_prefix: tuple[int, ...] = ()
    counterfactual_input_sequence: tuple[int, ...] = ()
    output_event_count: int = 1
    output_event_interval_generations: int = 0
    retention_delay_generations: int = 0
    retention_interference_repetitions: int = 0
    relearning_teacher_repetitions: int = 0
    noise_robustness_rate_delta: int = 0
    held_out_mapping: ByteSequenceMapping | None = None

    def __post_init__(self) -> None:
        for name in (
            "byte_hold_generations", "byte_gap_generations", "teacher_delay_generations",
            "teacher_repetitions", "evaluation_timeout_generations",
            "inter_input_generations", "output_event_interval_generations",
            "retention_delay_generations",
            "retention_interference_repetitions",
            "relearning_teacher_repetitions",
            "noise_robustness_rate_delta",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.teacher_repetitions < 1:
            raise ValueError("teacher_repetitions must be positive")
        if self.noise_robustness_rate_delta > 0xFFFF:
            raise ValueError("noise_robustness_rate_delta must fit uint16")
        if self.output_event_count not in (1, 2):
            raise ValueError("legacy/default output_event_count must be 1 or 2")
        if self.retention_enabled:
            if self.retention_delay_generations <= 0:
                raise ValueError("P6.4 retention delay must be positive")
            if self.retention_interference_repetitions <= 0:
                raise ValueError("P6.4 interference repetitions must be positive")
            if self.relearning_teacher_repetitions <= 0:
                raise ValueError("P6.4 relearning repetitions must be positive")
        if not self.mappings:
            raise ValueError("at least one byte mapping is required")
        if any(
            not isinstance(item, (ByteMapping, ByteSequenceMapping))
            for item in self.mappings
        ):
            raise ValueError("mappings must contain protocol mapping values")
        input_sequences = tuple(item.input_bytes for item in self.mappings)
        if len(set(input_sequences)) != len(input_sequences):
            raise ValueError("mapping input sequences must be unique")

        input_lengths = {len(sequence) for sequence in input_sequences}
        mapping_output_counts = tuple(
            (
                len(item.output_bytes)
                if isinstance(item, ByteSequenceMapping) and item.output_bytes
                else self.output_event_count
            )
            for item in self.mappings
        )
        mixed_length_protocol = (
            len(input_lengths) > 1
            or len(set(mapping_output_counts)) > 1
        )
        if mixed_length_protocol:
            for first in input_sequences:
                for second in input_sequences:
                    if (
                        first != second
                        and len(first) < len(second)
                        and second[: len(first)] == first
                    ):
                        raise ValueError(
                            "bounded mixed-length mapped inputs must be prefix-free"
                        )
        else:
            for item in self.mappings:
                if (
                    isinstance(item, ByteSequenceMapping)
                    and item.output_bytes
                    and len(item.output_bytes) != self.output_event_count
                ):
                    raise ValueError(
                        "explicit output sequence length must match output_event_count"
                    )

        max_output_event_count = max(mapping_output_counts)
        if (
            max_output_event_count == 1
            and self.output_event_interval_generations != 0
        ):
            raise ValueError("one-event protocols require output interval 0")
        if (
            max_output_event_count > 1
            and self.output_event_interval_generations < 2
        ):
            raise ValueError(
                "multi-event protocols require output interval >= 2"
            )
        validate_byte(self.counterfactual_input_byte)
        one_byte_inputs = {
            item.input_bytes[0]
            for item in self.mappings
            if len(item.input_bytes) == 1
        }
        if self.counterfactual_input_byte in one_byte_inputs:
            raise ValueError("counterfactual input byte must be unmapped")

        prefix = tuple(int(value) for value in self.counterfactual_prefix)
        counterfactual_sequence = tuple(
            int(value) for value in self.counterfactual_input_sequence
        )
        object.__setattr__(self, "counterfactual_prefix", prefix)
        object.__setattr__(
            self,
            "counterfactual_input_sequence",
            counterfactual_sequence,
        )
        for value in (*prefix, *counterfactual_sequence):
            validate_byte(value)

        sequence_mappings = tuple(
            item for item in self.mappings
            if isinstance(item, ByteSequenceMapping)
        )
        if self.retention_enabled and not counterfactual_sequence:
            raise ValueError("P6.4 requires a deterministic unmapped interference sequence")

        if sequence_mappings:
            if mixed_length_protocol:
                if not prefix:
                    raise ValueError(
                        "mixed-length protocols require one proper-prefix control"
                    )
                if not any(
                    len(prefix) < len(sequence)
                    and sequence[: len(prefix)] == prefix
                    for sequence in input_sequences
                ):
                    raise ValueError(
                        "mixed-length counterfactual_prefix must be a proper mapped prefix"
                    )
                if not counterfactual_sequence:
                    raise ValueError(
                        "mixed-length protocols require one unmapped sequence control"
                    )
                if counterfactual_sequence in set(input_sequences):
                    raise ValueError("counterfactual input sequence must be unmapped")
            else:
                if len(prefix) != 1:
                    raise ValueError("P6.2 counterfactual_prefix must contain one byte")
                if not all(item.input_bytes[:1] == prefix for item in sequence_mappings):
                    raise ValueError("counterfactual_prefix must match the shared sequence prefix")
                if len(counterfactual_sequence) != 2:
                    raise ValueError(
                        "P6.2 counterfactual_input_sequence must contain two bytes"
                    )
                if counterfactual_sequence in set(input_sequences):
                    raise ValueError("counterfactual input sequence must be unmapped")

        if self.held_out_mapping is not None:
            held_out = self.held_out_mapping
            if not isinstance(held_out, ByteSequenceMapping):
                raise ValueError("P6.6 held_out_mapping must be a two-byte sequence mapping")
            if len(sequence_mappings) != len(self.mappings):
                raise ValueError("P6.6 requires all teacher mappings to be two-byte sequences")
            if self.output_event_count != 2:
                raise ValueError("P6.6 requires the accepted two-event output protocol")
            relation_mappings = (*sequence_mappings, held_out)
            relation_prefix = held_out.input_bytes[0]
            if any(item.input_bytes[0] != relation_prefix for item in relation_mappings):
                raise ValueError("P6.6 relation mappings must share one fixed prefix")
            if any(
                item.input_bytes[1] >= 0xFF
                or item.output_byte != item.input_bytes[1] + 1
                for item in relation_mappings
            ):
                raise ValueError(
                    "P6.6 relation requires output byte = second input byte + 1"
                )
            if held_out.input_bytes in set(input_sequences):
                raise ValueError("P6.6 held-out input must not be teacher-trained")
            training_second_bytes = {
                item.input_bytes[1] for item in sequence_mappings
            }
            if held_out.input_bytes[1] in training_second_bytes:
                raise ValueError("P6.6 held-out second byte must be distinct")
            training_targets = {item.output_byte for item in sequence_mappings}
            if held_out.output_byte in training_targets:
                raise ValueError("P6.6 held-out target must not be a teacher target")

    @property
    def retention_enabled(self) -> bool:
        return bool(
            self.retention_delay_generations
            or self.retention_interference_repetitions
            or self.relearning_teacher_repetitions
        )

    @property
    def noise_robustness_enabled(self) -> bool:
        return self.noise_robustness_rate_delta > 0

    @property
    def generalization_enabled(self) -> bool:
        return self.held_out_mapping is not None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "byte_hold_generations": self.byte_hold_generations,
            "byte_gap_generations": self.byte_gap_generations,
            "teacher_delay_generations": self.teacher_delay_generations,
            "teacher_repetitions": self.teacher_repetitions,
            "evaluation_timeout_generations": self.evaluation_timeout_generations,
        }
        if self.inter_input_generations:
            payload["inter_input_generations"] = self.inter_input_generations
        if self.counterfactual_prefix:
            payload["counterfactual_prefix"] = list(self.counterfactual_prefix)
        if self.counterfactual_input_sequence:
            payload["counterfactual_input_sequence"] = list(
                self.counterfactual_input_sequence
            )
        if self.output_event_count != 1:
            payload["output_event_count"] = self.output_event_count
            payload["output_event_interval_generations"] = (
                self.output_event_interval_generations
            )
        if (
            self.retention_delay_generations
            or self.retention_interference_repetitions
            or self.relearning_teacher_repetitions
        ):
            payload["retention_delay_generations"] = self.retention_delay_generations
            payload["retention_interference_repetitions"] = (
                self.retention_interference_repetitions
            )
            payload["relearning_teacher_repetitions"] = (
                self.relearning_teacher_repetitions
            )
        if self.noise_robustness_rate_delta:
            payload["noise_robustness_rate_delta"] = self.noise_robustness_rate_delta
        if self.held_out_mapping is not None:
            payload["held_out_mapping"] = self.held_out_mapping.to_dict()
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
            parsed_mappings: list[ProtocolMapping] = []
            for item in raw_mappings:
                if not isinstance(item, Mapping):
                    raise ValueError("mapping records must be objects")
                if item.get("input_bytes") is not None:
                    parsed_mappings.append(ByteSequenceMapping.from_mapping(item))
                else:
                    parsed_mappings.append(ByteMapping.from_mapping(item))
            values["mappings"] = tuple(parsed_mappings)
        if mapping.get("counterfactual_input_byte") is not None:
            values["counterfactual_input_byte"] = int(
                mapping["counterfactual_input_byte"]
            )
        if mapping.get("inter_input_generations") is not None:
            values["inter_input_generations"] = int(
                mapping["inter_input_generations"]
            )
        if mapping.get("counterfactual_prefix") is not None:
            raw_prefix = mapping["counterfactual_prefix"]
            if not isinstance(raw_prefix, (list, tuple)):
                raise ValueError("counterfactual_prefix must be an array")
            values["counterfactual_prefix"] = tuple(int(value) for value in raw_prefix)
        if mapping.get("counterfactual_input_sequence") is not None:
            raw_sequence = mapping["counterfactual_input_sequence"]
            if not isinstance(raw_sequence, (list, tuple)):
                raise ValueError("counterfactual_input_sequence must be an array")
            values["counterfactual_input_sequence"] = tuple(
                int(value) for value in raw_sequence
            )
        if mapping.get("output_event_count") is not None:
            values["output_event_count"] = int(mapping["output_event_count"])
        if mapping.get("output_event_interval_generations") is not None:
            values["output_event_interval_generations"] = int(
                mapping["output_event_interval_generations"]
            )
        for name in (
            "retention_delay_generations",
            "retention_interference_repetitions",
            "relearning_teacher_repetitions",
            "noise_robustness_rate_delta",
        ):
            if mapping.get(name) is not None:
                values[name] = int(mapping[name])
        if mapping.get("held_out_mapping") is not None:
            raw_held_out = mapping["held_out_mapping"]
            if not isinstance(raw_held_out, Mapping):
                raise ValueError("held_out_mapping must be an object")
            values["held_out_mapping"] = ByteSequenceMapping.from_mapping(raw_held_out)
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
    input_bytes: tuple[int, ...] = ()


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
    input_complete_generation: int = 0
    expected_output_event_count: int = 1
    expected_output_interval_generations: int = 0

    @property
    def early_output_count(self) -> int:
        if self.input_complete_generation <= 0:
            return 0
        return sum(
            generation < self.input_complete_generation
            for generation in self.event_generations
        )

    @property
    def wrong_output_count(self) -> int:
        expected_index = 0
        wrong = 0
        last_matched_output_generation: int | None = None
        for event, generation in zip(self.autonomous_events, self.event_generations):
            if (
                self.input_complete_generation > 0
                and generation < self.input_complete_generation
            ):
                wrong += 1
                continue
            if (
                expected_index >= len(self.expected_events)
                or event != self.expected_events[expected_index]
            ):
                wrong += 1
                continue
            if (
                expected_index < self.expected_output_event_count
                and expected_index > 0
                and self.expected_output_interval_generations > 0
                and (
                    last_matched_output_generation is None
                    or generation - last_matched_output_generation
                    != self.expected_output_interval_generations
                )
            ):
                wrong += 1
                continue
            if expected_index < self.expected_output_event_count:
                last_matched_output_generation = generation
            expected_index += 1
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
    mapping: ProtocolMapping
    baseline: EvaluationResult
    trained: EvaluationResult
    t1: EvaluationResult | None = None
    t2: EvaluationResult | None = None
    noisy: EvaluationResult | None = None

    @property
    def t0(self) -> EvaluationResult:
        return self.trained


@dataclass(frozen=True)
class MappingMeasurement:
    mapping: ProtocolMapping
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
    baseline_prefix: EvaluationResult | None = None
    trained_prefix: EvaluationResult | None = None
    baseline_sequence_counterfactual: EvaluationResult | None = None
    trained_sequence_counterfactual: EvaluationResult | None = None
    baseline_held_out: EvaluationResult | None = None
    trained_held_out: EvaluationResult | None = None
    retention_checkpoint_generations: tuple[int, int, int] = ()
    noisy_no_input: EvaluationResult | None = None
    noisy_alternate: EvaluationResult | None = None
    noisy_prefix: EvaluationResult | None = None
    noisy_sequence_counterfactual: EvaluationResult | None = None
    clean_noise_rate: int = 0
    noisy_noise_rate: int = 0

    @property
    def noisy_controls_clean(self) -> bool:
        if self.noisy_no_input is None or not self.noisy_no_input.success:
            return False
        if self.noisy_prefix is not None or self.noisy_sequence_counterfactual is not None:
            return bool(
                self.noisy_prefix is not None
                and self.noisy_prefix.success
                and self.noisy_sequence_counterfactual is not None
                and self.noisy_sequence_counterfactual.success
            )
        return bool(
            self.noisy_alternate is not None
            and self.noisy_alternate.success
        )

    def noise_classification(
        self,
        mapping: MappingSeedMeasurement,
    ) -> tuple[bool, bool, bool]:
        eligible = bool(
            mapping.noisy is not None
            and mapping.trained.success
            and self.noisy_noise_rate > self.clean_noise_rate
        )
        robust = bool(
            eligible
            and mapping.noisy is not None
            and mapping.noisy.success
            and self.noisy_controls_clean
        )
        return eligible, robust, bool(eligible and not robust)

    @property
    def generalization_controls_clean(self) -> bool:
        if self.trained_prefix is not None or self.trained_sequence_counterfactual is not None:
            return bool(
                self.trained_no_input.success
                and self.trained_prefix is not None
                and self.trained_prefix.success
                and self.trained_sequence_counterfactual is not None
                and self.trained_sequence_counterfactual.success
            )
        return bool(
            self.trained_no_input.success
            and self.trained_alternate.success
        )

    def generalization_classification(self) -> tuple[bool, bool, bool, bool]:
        training_qualified = bool(
            self.mapping_results
            and all(
                record.trained.success and not record.baseline.success
                for record in self.mapping_results
            )
            and self.generalization_controls_clean
        )
        eligible = bool(
            training_qualified
            and self.baseline_held_out is not None
            and self.trained_held_out is not None
            and not self.baseline_held_out.success
        )
        generalized = bool(
            eligible
            and self.trained_held_out is not None
            and self.trained_held_out.success
        )
        return (
            training_qualified,
            eligible,
            generalized,
            bool(eligible and not generalized),
        )

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
    counterfactual_prefix: tuple[int, ...] = ()
    counterfactual_input_sequence: tuple[int, ...] = ()
    baseline_prefix_input_clean: int = 0
    trained_prefix_input_clean: int = 0
    baseline_sequence_counterfactual_clean: int = 0
    trained_sequence_counterfactual_clean: int = 0
    output_event_count: int = 1
    output_event_interval_generations: int = 0
    retention_eligible_count: int = 0
    retained_count: int = 0
    forgotten_count: int = 0
    relearning_eligible_count: int = 0
    relearned_count: int = 0
    noise_robustness_eligible_count: int = 0
    noise_robust_count: int = 0
    noise_failed_count: int = 0
    held_out_mapping: ByteSequenceMapping | None = None
    training_qualified_count: int = 0
    generalization_eligible_count: int = 0
    generalized_count: int = 0
    generalization_failed_count: int = 0

    @property
    def retention_rate(self) -> float | None:
        if self.retention_eligible_count <= 0:
            return None
        return self.retained_count / self.retention_eligible_count

    @property
    def relearning_rate(self) -> float | None:
        if self.relearning_eligible_count <= 0:
            return None
        return self.relearned_count / self.relearning_eligible_count

    @property
    def noise_robustness_rate(self) -> float | None:
        if self.noise_robustness_eligible_count <= 0:
            return None
        return self.noise_robust_count / self.noise_robustness_eligible_count

    @property
    def generalization_rate(self) -> float | None:
        if self.generalization_eligible_count <= 0:
            return None
        return self.generalized_count / self.generalization_eligible_count

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


def _noise_robustness_state(
    state: UniverseState,
    *,
    protocol: ExperimentConfig,
) -> tuple[UniverseState, int, int]:
    if not protocol.noise_robustness_enabled:
        raise ValueError("P6.5 noise robustness protocol is not enabled")
    clean_config = state.config or PhysicsConfig()
    clean_rate = int(clean_config.noise_rate)
    noisy_rate = min(0xFFFF, clean_rate + protocol.noise_robustness_rate_delta)
    values = clean_config.to_dict()
    values["noise_rate"] = noisy_rate
    noisy_config = PhysicsConfig(**values)
    noisy_state = UniverseState.from_snapshot(
        state.to_snapshot(),
        config=noisy_config,
    )
    return noisy_state, clean_rate, noisy_rate


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
        mapping: ProtocolMapping,
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

        input_bytes = mapping.input_bytes
        for index, input_byte in enumerate(input_bytes):
            for _ in range(self.experiment.byte_hold_generations):
                self.drive_input(input_byte)
                advance(self.input_bus.signal_coordinates())
            if index < len(input_bytes) - 1:
                for _ in range(self.experiment.inter_input_generations):
                    self.release_input()
                    advance(())
        for _ in range(self.experiment.byte_gap_generations):
            self.release_input()
            advance(())
        for _ in range(self.experiment.teacher_delay_generations):
            self.release_input()
            advance(())
        output_bytes = _mapping_output_bytes(
            mapping,
            self.experiment.output_event_count,
        )
        null_event = OutputEvent.null()
        teacher_events: list[OutputEvent] = []
        for output_index, output_byte in enumerate(output_bytes):
            byte_event = OutputEvent.byte(output_byte)
            self.teacher_output(
                byte_event,
                on_generation=on_generation,
                on_step=on_step,
            )
            teacher_events.append(byte_event)
            if output_index < len(output_bytes) - 1:
                for _ in range(
                    self.experiment.output_event_interval_generations - 1
                ):
                    self.release_input()
                    advance(())
        self.teacher_output(
            null_event,
            on_generation=on_generation,
            on_step=on_step,
        )
        teacher_events.append(null_event)
        return TrainingRecord(
            input_byte=mapping.input_bytes[0],
            output_byte=mapping.output_byte,
            teacher_events=tuple(teacher_events),
            generation=self.state.generation,
            input_bytes=mapping.input_bytes,
        )

    def train_mappings(
        self,
        *,
        repetitions: int | None = None,
        on_generation: Callable[[int], None] | None = None,
        on_step: Callable[[int, StepMetrics], None] | None = None,
    ) -> tuple[TrainingRecord, ...]:
        repetition_count = (
            self.experiment.teacher_repetitions
            if repetitions is None
            else int(repetitions)
        )
        if repetition_count < 1:
            raise ValueError("training repetitions must be positive")
        records: list[TrainingRecord] = []
        for _ in range(repetition_count):
            for mapping in self.experiment.mappings:
                records.append(
                    self._train_mapping_once(
                        mapping,
                        on_generation=on_generation,
                        on_step=on_step,
                    )
                )
        return tuple(records)

    def advance_without_teacher(self, generations: int) -> None:
        count = int(generations)
        if count < 0:
            raise ValueError("idle generations must be non-negative")
        self.release_input()
        for _ in range(count):
            self._advance(())

    def experience_input_sequence_without_teacher(
        self,
        input_bytes: Iterable[int],
    ) -> None:
        sequence = tuple(int(value) for value in input_bytes)
        if not sequence:
            raise ValueError("interference input sequence must not be empty")
        for value in sequence:
            validate_byte(value)
        for index, input_byte in enumerate(sequence):
            for _ in range(self.experiment.byte_hold_generations):
                self.drive_input(input_byte)
                self._advance(self.input_bus.signal_coordinates())
            if index < len(sequence) - 1:
                for _ in range(self.experiment.inter_input_generations):
                    self.release_input()
                    self._advance(())
        self.release_input()
        for _ in range(self.experiment.byte_gap_generations):
            self._advance(())

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
            input_bytes=(input_byte,),
        )

    def _evaluate_input_sequence(
        self,
        *,
        input_bytes: Iterable[int],
        input_valid: bool = True,
        expected: Iterable[OutputEvent] = (),
        enforce_full_sequence: bool = False,
    ) -> EvaluationResult:
        sequence = tuple(int(value) for value in input_bytes)
        if not sequence:
            raise ValueError("input sequence must not be empty")
        for value in sequence:
            validate_byte(value)

        clone = _clone_state(self.state)
        clone_experiment = IOExperiment(clone, experiment=self.experiment)
        clone_experiment.output_detector.prime_signal(read_output_signal(clone))
        observed: list[OutputEvent] = []
        event_generations: list[int] = []
        evaluation_generations = 0
        activity_cost = 0
        input_complete_generation = 0

        def advance_and_observe(anchors: Iterable[tuple[int, int]]) -> None:
            nonlocal evaluation_generations, activity_cost
            metrics = clone_experiment._advance(anchors)
            evaluation_generations += 1
            activity_cost += metrics.activity_cost
            events = clone_experiment.observe_output_state()
            observed.extend(events)
            event_generations.extend([evaluation_generations] * len(events))

        for index, input_byte in enumerate(sequence):
            for _ in range(self.experiment.byte_hold_generations):
                if input_valid:
                    clone_experiment.drive_input(input_byte)
                else:
                    clone_experiment.release_input()
                advance_and_observe(clone_experiment.input_bus.signal_coordinates())
            if index < len(sequence) - 1:
                for _ in range(self.experiment.inter_input_generations):
                    clone_experiment.release_input()
                    advance_and_observe(())
        if enforce_full_sequence:
            input_complete_generation = evaluation_generations
        for _ in range(self.experiment.byte_gap_generations):
            clone_experiment.release_input()
            advance_and_observe(())
        for _ in range(self.experiment.evaluation_timeout_generations):
            clone_experiment.release_input()
            advance_and_observe(())

        actual = tuple(observed)
        expected_tuple = tuple(expected)
        expected_output_event_count = sum(
            event.kind == "byte"
            for event in expected_tuple
        )
        expected_index = 0
        for event in actual:
            if expected_index < len(expected_tuple) and event == expected_tuple[expected_index]:
                expected_index += 1
        early_output_count = (
            sum(
                generation < input_complete_generation
                for generation in event_generations
            )
            if enforce_full_sequence
            else 0
        )
        timing_valid = True
        if (
            expected_output_event_count > 1
            and len(actual) >= expected_output_event_count
            and len(event_generations) >= expected_output_event_count
        ):
            timing_valid = all(
                event_generations[index] - event_generations[index - 1]
                == self.experiment.output_event_interval_generations
                for index in range(1, expected_output_event_count)
            )
        return EvaluationResult(
            expected_events=expected_tuple,
            autonomous_events=actual,
            success=(
                actual == expected_tuple
                and early_output_count == 0
                and timing_valid
            ),
            clone_generation=clone.generation,
            event_generations=tuple(event_generations),
            evaluation_generations=evaluation_generations,
            activity_cost=activity_cost,
            timed_out=expected_index < len(expected_tuple),
            input_complete_generation=input_complete_generation,
            expected_output_event_count=expected_output_event_count,
            expected_output_interval_generations=(
                self.experiment.output_event_interval_generations
            ),
        )

    def evaluate_autonomous(
        self,
        *,
        input_byte: int = 65,
        input_valid: bool = True,
        expected: Iterable[OutputEvent] = (),
    ) -> EvaluationResult:
        return self._evaluate_input_sequence(
            input_bytes=(input_byte,),
            input_valid=input_valid,
            expected=expected,
            enforce_full_sequence=False,
        )

    def evaluate_autonomous_sequence(
        self,
        *,
        input_bytes: Iterable[int],
        expected: Iterable[OutputEvent] = (),
    ) -> EvaluationResult:
        sequence = tuple(int(value) for value in input_bytes)
        return self._evaluate_input_sequence(
            input_bytes=sequence,
            expected=expected,
            enforce_full_sequence=len(sequence) > 1,
        )


def _seed_measurement(
    *,
    seed: int,
    baseline_state: UniverseState,
    trained_state: UniverseState,
    protocol: ExperimentConfig,
    retention_state: UniverseState | None = None,
    relearned_state: UniverseState | None = None,
    retention_checkpoint_generations: tuple[int, int, int] = (),
    noisy_state: UniverseState | None = None,
    clean_noise_rate: int = 0,
    noisy_noise_rate: int = 0,
) -> SeedMeasurement:
    baseline = IOExperiment(baseline_state, experiment=protocol)
    trained = IOExperiment(trained_state, experiment=protocol)
    retention = (
        IOExperiment(retention_state, experiment=protocol)
        if retention_state is not None
        else None
    )
    relearned = (
        IOExperiment(relearned_state, experiment=protocol)
        if relearned_state is not None
        else None
    )
    noisy = (
        IOExperiment(noisy_state, experiment=protocol)
        if noisy_state is not None
        else None
    )
    mapping_results: list[MappingSeedMeasurement] = []

    def evaluate(
        experiment: IOExperiment,
        mapping: ProtocolMapping,
        expected: tuple[OutputEvent, ...],
    ) -> EvaluationResult:
        if isinstance(mapping, ByteSequenceMapping):
            return experiment.evaluate_autonomous_sequence(
                input_bytes=mapping.input_bytes,
                expected=expected,
            )
        return experiment.evaluate_autonomous(
            input_byte=mapping.input_byte,
            expected=expected,
        )

    for mapping in protocol.mappings:
        expected = (
            *(
                OutputEvent.byte(value)
                for value in _mapping_output_bytes(
                    mapping,
                    protocol.output_event_count,
                )
            ),
            OutputEvent.null(),
        )
        baseline_result = evaluate(baseline, mapping, expected)
        trained_result = evaluate(trained, mapping, expected)
        mapping_results.append(
            MappingSeedMeasurement(
                mapping=mapping,
                baseline=baseline_result,
                trained=trained_result,
                t1=(
                    evaluate(retention, mapping, expected)
                    if retention is not None
                    else None
                ),
                t2=(
                    evaluate(relearned, mapping, expected)
                    if relearned is not None
                    else None
                ),
                noisy=(
                    evaluate(noisy, mapping, expected)
                    if noisy is not None
                    else None
                ),
            )
        )

    first = mapping_results[0]
    baseline_no_input = baseline.evaluate_autonomous(
        input_byte=protocol.mappings[0].input_bytes[0],
        input_valid=False,
        expected=(),
    )
    trained_no_input = trained.evaluate_autonomous(
        input_byte=protocol.mappings[0].input_bytes[0],
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
    baseline_prefix = None
    trained_prefix = None
    baseline_sequence_counterfactual = None
    trained_sequence_counterfactual = None
    if protocol.counterfactual_prefix:
        baseline_prefix = baseline.evaluate_autonomous_sequence(
            input_bytes=protocol.counterfactual_prefix,
            expected=(),
        )
        trained_prefix = trained.evaluate_autonomous_sequence(
            input_bytes=protocol.counterfactual_prefix,
            expected=(),
        )
    if protocol.counterfactual_input_sequence:
        baseline_sequence_counterfactual = baseline.evaluate_autonomous_sequence(
            input_bytes=protocol.counterfactual_input_sequence,
            expected=(),
        )
        trained_sequence_counterfactual = trained.evaluate_autonomous_sequence(
            input_bytes=protocol.counterfactual_input_sequence,
            expected=(),
        )

    baseline_held_out = None
    trained_held_out = None
    if protocol.held_out_mapping is not None:
        held_out_expected = (
            *(
                OutputEvent.byte(value)
                for value in _mapping_output_bytes(
                    protocol.held_out_mapping,
                    protocol.output_event_count,
                )
            ),
            OutputEvent.null(),
        )
        baseline_held_out = evaluate(
            baseline,
            protocol.held_out_mapping,
            held_out_expected,
        )
        trained_held_out = evaluate(
            trained,
            protocol.held_out_mapping,
            held_out_expected,
        )

    noisy_no_input = None
    noisy_alternate = None
    noisy_prefix = None
    noisy_sequence_counterfactual = None
    if noisy is not None:
        noisy_no_input = noisy.evaluate_autonomous(
            input_byte=protocol.mappings[0].input_bytes[0],
            input_valid=False,
            expected=(),
        )
        noisy_alternate = noisy.evaluate_autonomous(
            input_byte=protocol.counterfactual_input_byte,
            expected=(),
        )
        if protocol.counterfactual_prefix:
            noisy_prefix = noisy.evaluate_autonomous_sequence(
                input_bytes=protocol.counterfactual_prefix,
                expected=(),
            )
        if protocol.counterfactual_input_sequence:
            noisy_sequence_counterfactual = noisy.evaluate_autonomous_sequence(
                input_bytes=protocol.counterfactual_input_sequence,
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
        baseline_prefix=baseline_prefix,
        trained_prefix=trained_prefix,
        baseline_sequence_counterfactual=baseline_sequence_counterfactual,
        trained_sequence_counterfactual=trained_sequence_counterfactual,
        baseline_held_out=baseline_held_out,
        trained_held_out=trained_held_out,
        retention_checkpoint_generations=retention_checkpoint_generations,
        noisy_no_input=noisy_no_input,
        noisy_alternate=noisy_alternate,
        noisy_prefix=noisy_prefix,
        noisy_sequence_counterfactual=noisy_sequence_counterfactual,
        clean_noise_rate=clean_noise_rate,
        noisy_noise_rate=noisy_noise_rate,
    )


def _assemble_learning_measurement(
    measurements: Iterable[SeedMeasurement],
    *,
    mappings: Iterable[ProtocolMapping] = DEFAULT_BYTE_MAPPINGS,
    counterfactual_input_byte: int = 66,
    counterfactual_prefix: tuple[int, ...] = (),
    counterfactual_input_sequence: tuple[int, ...] = (),
    output_event_count: int = 1,
    output_event_interval_generations: int = 0,
    held_out_mapping: ByteSequenceMapping | None = None,
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
    baseline_prefix_input_clean = sum(
        item.baseline_prefix is not None and item.baseline_prefix.success
        for item in records
    )
    trained_prefix_input_clean = sum(
        item.trained_prefix is not None and item.trained_prefix.success
        for item in records
    )
    baseline_sequence_counterfactual_clean = sum(
        item.baseline_sequence_counterfactual is not None
        and item.baseline_sequence_counterfactual.success
        for item in records
    )
    trained_sequence_counterfactual_clean = sum(
        item.trained_sequence_counterfactual is not None
        and item.trained_sequence_counterfactual.success
        for item in records
    )
    sequence_protocol = any(
        isinstance(mapping, ByteSequenceMapping)
        for mapping in mapping_values
    )
    retention_records = tuple(
        mapping
        for item in records
        for mapping in item.mapping_results
        if mapping.t1 is not None and mapping.t2 is not None
    )
    retention_eligible_count = sum(
        mapping.t0.success for mapping in retention_records
    )
    retained_count = sum(
        mapping.t0.success and bool(mapping.t1 and mapping.t1.success)
        for mapping in retention_records
    )
    forgotten_count = sum(
        mapping.t0.success and bool(mapping.t1 is not None and not mapping.t1.success)
        for mapping in retention_records
    )
    relearning_eligible_count = forgotten_count
    relearned_count = sum(
        mapping.t0.success
        and bool(mapping.t1 is not None and not mapping.t1.success)
        and bool(mapping.t2 and mapping.t2.success)
        for mapping in retention_records
    )

    noise_classifications = tuple(
        item.noise_classification(mapping)
        for item in records
        for mapping in item.mapping_results
        if mapping.noisy is not None
    )
    noise_robustness_eligible_count = sum(
        eligible for eligible, _, _ in noise_classifications
    )
    noise_robust_count = sum(
        robust for _, robust, _ in noise_classifications
    )
    noise_failed_count = sum(
        failed for _, _, failed in noise_classifications
    )

    generalization_classifications = tuple(
        item.generalization_classification()
        for item in records
        if held_out_mapping is not None
    )
    training_qualified_count = sum(
        qualified
        for qualified, _, _, _ in generalization_classifications
    )
    generalization_eligible_count = sum(
        eligible
        for _, eligible, _, _ in generalization_classifications
    )
    generalized_count = sum(
        generalized
        for _, _, generalized, _ in generalization_classifications
    )
    generalization_failed_count = sum(
        failed
        for _, _, _, failed in generalization_classifications
    )

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

    explicit_output_sequence_protocol = any(
        isinstance(mapping, ByteSequenceMapping) and bool(mapping.output_bytes)
        for mapping in mapping_values
    )

    if explicit_output_sequence_protocol:
        criterion = (
            "all sequences across all seeds must autonomously emit each declared ordered output-byte sequence "
            f"at the declared {output_event_interval_generations}-generation onset interval then NULL only after the full input sequence, "
            "trained successes must exceed baseline, and no-input/prefix-only/unmapped-sequence counterfactuals must remain output-clean"
        )
    elif sequence_protocol and output_event_count > 1:
        criterion = (
            "all sequences across all seeds must autonomously emit the declared output byte "
            f"{output_event_count} times at the declared {output_event_interval_generations}-generation onset interval then NULL only after the full input sequence, "
            "trained successes must exceed baseline, and no-input/prefix-only/unmapped-sequence counterfactuals must remain output-clean"
        )
    elif sequence_protocol:
        criterion = (
            "all sequences across all seeds must autonomously emit each declared output byte then NULL only after the full input sequence, "
            "trained successes must exceed baseline, and no-input/prefix-only/unmapped-sequence counterfactuals must remain output-clean"
        )
    elif len(mapping_values) == 1:
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
            and (
                (
                    trained_prefix_input_clean >= seed_count
                    and trained_sequence_counterfactual_clean >= seed_count
                )
                if sequence_protocol
                else trained_alternate_input_clean >= seed_count
            )
        ),
        per_seed=records,
        mapping_count=len(mapping_values),
        counterfactual_input_byte=counterfactual_input_byte,
        per_mapping=per_mapping,
        counterfactual_prefix=counterfactual_prefix,
        counterfactual_input_sequence=counterfactual_input_sequence,
        baseline_prefix_input_clean=baseline_prefix_input_clean,
        trained_prefix_input_clean=trained_prefix_input_clean,
        baseline_sequence_counterfactual_clean=baseline_sequence_counterfactual_clean,
        trained_sequence_counterfactual_clean=trained_sequence_counterfactual_clean,
        output_event_count=output_event_count,
        output_event_interval_generations=output_event_interval_generations,
        retention_eligible_count=retention_eligible_count,
        retained_count=retained_count,
        forgotten_count=forgotten_count,
        relearning_eligible_count=relearning_eligible_count,
        relearned_count=relearned_count,
        noise_robustness_eligible_count=noise_robustness_eligible_count,
        noise_robust_count=noise_robust_count,
        noise_failed_count=noise_failed_count,
        held_out_mapping=held_out_mapping,
        training_qualified_count=training_qualified_count,
        generalization_eligible_count=generalization_eligible_count,
        generalized_count=generalized_count,
        generalization_failed_count=generalization_failed_count,
    )



def _retention_checkpoint_states(
    state: UniverseState,
    *,
    protocol: ExperimentConfig,
    isolate_authority: bool = False,
) -> tuple[UniverseState, UniverseState, UniverseState, tuple[int, int, int]]:
    if not protocol.retention_enabled:
        raise ValueError("P6.4 retention protocol is not enabled")

    working = _clone_state(state) if isolate_authority else state
    t0_state = _clone_state(working)
    t0_generation = working.generation

    experiment = IOExperiment(working, experiment=protocol)
    experiment.advance_without_teacher(protocol.retention_delay_generations)
    for _ in range(protocol.retention_interference_repetitions):
        experiment.experience_input_sequence_without_teacher(
            protocol.counterfactual_input_sequence
        )
    t1_state = _clone_state(working)
    t1_generation = working.generation

    experiment.train_mappings(
        repetitions=protocol.relearning_teacher_repetitions,
    )
    t2_state = _clone_state(working)
    t2_generation = working.generation

    return (
        t0_state,
        t1_state,
        t2_state,
        (t0_generation, t1_generation, t2_generation),
    )


def measure_trained_state(
    state: UniverseState,
    *,
    experiment: ExperimentConfig | None = None,
) -> LearningMeasurement:
    """Measure a current authoritative training state through disposable clones."""
    protocol = experiment or ExperimentConfig()
    resolved = state.config or PhysicsConfig()
    if protocol.retention_enabled:
        t0_state, t1_state, t2_state, checkpoint_generations = (
            _retention_checkpoint_states(
                state,
                protocol=protocol,
                isolate_authority=True,
            )
        )
        noisy_state = None
        clean_noise_rate = int((t0_state.config or resolved).noise_rate)
        noisy_noise_rate = clean_noise_rate
        if protocol.noise_robustness_enabled:
            noisy_state, clean_noise_rate, noisy_noise_rate = _noise_robustness_state(
                t0_state,
                protocol=protocol,
            )
        measurement = _seed_measurement(
            seed=state.seed,
            baseline_state=create_universe(seed=state.seed, config=resolved),
            trained_state=t0_state,
            retention_state=t1_state,
            relearned_state=t2_state,
            retention_checkpoint_generations=checkpoint_generations,
            noisy_state=noisy_state,
            clean_noise_rate=clean_noise_rate,
            noisy_noise_rate=noisy_noise_rate,
            protocol=protocol,
        )
    else:
        noisy_state = None
        clean_noise_rate = int((state.config or resolved).noise_rate)
        noisy_noise_rate = clean_noise_rate
        if protocol.noise_robustness_enabled:
            noisy_state, clean_noise_rate, noisy_noise_rate = _noise_robustness_state(
                state,
                protocol=protocol,
            )
        measurement = _seed_measurement(
            seed=state.seed,
            baseline_state=create_universe(seed=state.seed, config=resolved),
            trained_state=state,
            noisy_state=noisy_state,
            clean_noise_rate=clean_noise_rate,
            noisy_noise_rate=noisy_noise_rate,
            protocol=protocol,
        )
    return _assemble_learning_measurement(
        (measurement,),
        mappings=protocol.mappings,
        counterfactual_input_byte=protocol.counterfactual_input_byte,
        counterfactual_prefix=protocol.counterfactual_prefix,
        counterfactual_input_sequence=protocol.counterfactual_input_sequence,
        output_event_count=protocol.output_event_count,
        output_event_interval_generations=protocol.output_event_interval_generations,
        held_out_mapping=protocol.held_out_mapping,
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
        if protocol.retention_enabled:
            t0_state, t1_state, t2_state, checkpoint_generations = (
                _retention_checkpoint_states(trained_state, protocol=protocol)
            )
            noisy_state = None
            clean_noise_rate = int((t0_state.config or resolved).noise_rate)
            noisy_noise_rate = clean_noise_rate
            if protocol.noise_robustness_enabled:
                noisy_state, clean_noise_rate, noisy_noise_rate = _noise_robustness_state(
                    t0_state,
                    protocol=protocol,
                )
            measurements.append(
                _seed_measurement(
                    seed=seed,
                    baseline_state=baseline_state,
                    trained_state=t0_state,
                    retention_state=t1_state,
                    relearned_state=t2_state,
                    retention_checkpoint_generations=checkpoint_generations,
                    noisy_state=noisy_state,
                    clean_noise_rate=clean_noise_rate,
                    noisy_noise_rate=noisy_noise_rate,
                    protocol=protocol,
                )
            )
        else:
            noisy_state = None
            clean_noise_rate = int((trained_state.config or resolved).noise_rate)
            noisy_noise_rate = clean_noise_rate
            if protocol.noise_robustness_enabled:
                noisy_state, clean_noise_rate, noisy_noise_rate = _noise_robustness_state(
                    trained_state,
                    protocol=protocol,
                )
            measurements.append(
                _seed_measurement(
                    seed=seed,
                    baseline_state=baseline_state,
                    trained_state=trained_state,
                    noisy_state=noisy_state,
                    clean_noise_rate=clean_noise_rate,
                    noisy_noise_rate=noisy_noise_rate,
                    protocol=protocol,
                )
            )
    return _assemble_learning_measurement(
        measurements,
        mappings=protocol.mappings,
        counterfactual_input_byte=protocol.counterfactual_input_byte,
        counterfactual_prefix=protocol.counterfactual_prefix,
        counterfactual_input_sequence=protocol.counterfactual_input_sequence,
        output_event_count=protocol.output_event_count,
        output_event_interval_generations=protocol.output_event_interval_generations,
        held_out_mapping=protocol.held_out_mapping,
    )
