"""Fixed Phase 4 8-bit I/O contracts and edge-based event primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

INPUT_DATA_LINES = 8
INPUT_VALID_LINES = 1
OUTPUT_DATA_LINES = 8
OUTPUT_VALID_LINES = 1
OUTPUT_NULL_LINES = 1
IMPLEMENTATION_PHASE = 4


def validate_byte(value: int) -> int:
    value = int(value)
    if not 0 <= value <= 0xFF:
        raise ValueError("byte value must be in 0..255")
    return value


@dataclass(frozen=True)
class InputSignal:
    value: int = 0
    valid: bool = False


@dataclass
class InputBus:
    signal: InputSignal = field(default_factory=InputSignal)

    def drive(self, value: int, *, valid: bool = True) -> InputSignal:
        self.signal = InputSignal(value=validate_byte(value), valid=bool(valid))
        return self.signal

    def release(self) -> InputSignal:
        self.signal = InputSignal(value=self.signal.value, valid=False)
        return self.signal

    def signal_coordinates(self) -> tuple[tuple[int, int], ...]:
        """Return fixed-organ tiles carrying the currently valid input signal."""
        if not self.signal.valid:
            return ()
        coordinates = FixedOrgans.coordinates()
        active = [coordinates[FixedOrgans.input_valid]]
        active.extend(
            coordinates[f"IN{bit}"]
            for bit in range(INPUT_DATA_LINES)
            if self.signal.value & (1 << bit)
        )
        return tuple(active)


@dataclass(frozen=True)
class OutputEvent:
    kind: str
    value: int | None = None

    @classmethod
    def byte(cls, value: int) -> "OutputEvent":
        return cls("byte", validate_byte(value))

    @classmethod
    def null(cls) -> "OutputEvent":
        return cls("null", None)


@dataclass(frozen=True)
class OutputSignal:
    value: int = 0
    valid: bool = False
    null: bool = False

    def __post_init__(self) -> None:
        validate_byte(self.value)


def read_output_signal(state: Any) -> OutputSignal:
    """Read a byte/NULL signal from ordinary cells adjacent to fixed output organs."""
    coordinates = FixedOrgans.coordinates()
    occupied = {
        ((state.x[slot] // 8) % 32, (state.y[slot] // 8) % 32)
        for slot in state.active_slots()
    }
    value = sum(
        (1 << bit)
        for bit in range(OUTPUT_DATA_LINES)
        if coordinates[f"OUT{bit}"] in occupied
    )
    return OutputSignal(
        value=value,
        valid=coordinates[FixedOrgans.output_valid] in occupied,
        null=coordinates[FixedOrgans.output_null] in occupied,
    )


@dataclass
class OutputEdgeDetector:
    previous_valid: bool = False

    def observe(self, *, valid: bool, value: int = 0, null: bool = False) -> list[OutputEvent]:
        event: list[OutputEvent] = []
        if bool(valid) and not self.previous_valid:
            event.append(OutputEvent.null() if null else OutputEvent.byte(value))
        self.previous_valid = bool(valid)
        return event

    def observe_signal(self, signal: OutputSignal) -> list[OutputEvent]:
        return self.observe(valid=signal.valid, value=signal.value, null=signal.null)


class FixedOrgans:
    """Non-cell I/O coordinates; fixed organs never enter the cell slot pool."""

    input_data = tuple(f"IN{index}" for index in range(INPUT_DATA_LINES))
    input_valid = "IN_VALID"
    output_data = tuple(f"OUT{index}" for index in range(OUTPUT_DATA_LINES))
    output_valid = "OUT_VALID"
    output_null = "OUT_NULL"
    input_anchor = (8, 16)
    output_anchor = (24, 16)

    @classmethod
    def coordinates(cls) -> dict[str, tuple[int, int]]:
        input_coordinates = {
            name: (cls.input_anchor[0], cls.input_anchor[1] + offset - 4)
            for offset, name in enumerate(cls.input_data)
        }
        input_coordinates[cls.input_valid] = (cls.input_anchor[0], cls.input_anchor[1] + 5)
        output_coordinates = {
            name: (cls.output_anchor[0], cls.output_anchor[1] + offset - 4)
            for offset, name in enumerate(cls.output_data)
        }
        output_coordinates[cls.output_valid] = (cls.output_anchor[0], cls.output_anchor[1] + 5)
        output_coordinates[cls.output_null] = (cls.output_anchor[0], cls.output_anchor[1] + 6)
        return {**input_coordinates, **output_coordinates}

    @classmethod
    def all_names(cls) -> tuple[str, ...]:
        return cls.input_data + (cls.input_valid,) + cls.output_data + (cls.output_valid, cls.output_null)
