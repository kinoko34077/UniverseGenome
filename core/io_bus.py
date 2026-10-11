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
    from .physics import destination_footprint

    coordinates = FixedOrgans.coordinates()
    # Only the ten output organ tiles can affect the read. A coordinate
    # may intentionally alias another through a custom organ mapping:
    # combine its bits rather than overwriting them.
    targets: dict[tuple[int, int], int] = {}
    for bit in range(OUTPUT_DATA_LINES):
        tile = coordinates[f"OUT{bit}"]
        targets[tile] = targets.get(tile, 0) | (1 << bit)
    valid_bit = 1 << OUTPUT_DATA_LINES
    null_bit = valid_bit << 1
    tile = coordinates[FixedOrgans.output_valid]
    targets[tile] = targets.get(tile, 0) | valid_bit
    tile = coordinates[FixedOrgans.output_null]
    targets[tile] = targets.get(tile, 0) | null_bit

    observed = 0
    full_mask = null_bit | valid_bit | ((1 << OUTPUT_DATA_LINES) - 1)
    for slot in state.active_slots():
        # Reuse the original footprint implementation, including wrapping,
        # shape hierarchy and ACTIVE-only enumeration; only its projection
        # onto output tiles differs from the old full occupied-set union.
        for tile in destination_footprint(state.structure[slot], state.x[slot], state.y[slot]):
            observed |= targets.get(tile, 0)
        if observed == full_mask:
            break

    return OutputSignal(
        value=observed & ((1 << OUTPUT_DATA_LINES) - 1),
        valid=bool(observed & valid_bit),
        null=bool(observed & null_bit),
    )


@dataclass
class OutputEdgeDetector:
    previous_valid: bool = False

    def prime(self, *, valid: bool, value: int = 0, null: bool = False) -> None:
        """Set the initial line level without treating it as a new event."""
        validate_byte(value)
        self.previous_valid = bool(valid)

    def prime_signal(self, signal: OutputSignal) -> None:
        self.prime(valid=signal.valid, value=signal.value, null=signal.null)

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

    @classmethod
    def occupied_coordinates(cls) -> set[tuple[int, int]]:
        """Return every logical tile occupied by a fixed I/O organ line."""
        return set(cls.coordinates().values())
