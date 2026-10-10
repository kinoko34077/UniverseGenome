"""Authoritative fixed-capacity universe state through Phase 2E.

Slot indices are reusable storage positions only. They are deliberately not
cell identities and are never included in deterministic event keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

STRUCTURE_BITS = 16
LATENT_BITS = 16
HP_BITS = 8
SLOW_TRACE_BITS = 8
DEFAULT_MAX_CELLS = 1024


class Lifecycle(IntEnum):
    FREE = 0
    ACTIVE = 1
    BLACK_HOLE = 2


SHAPE_EMPTY = 0
SHAPE_SINGLE = 1
SHAPE_HORIZONTAL = 2
SHAPE_VERTICAL = 3


def structure_level(structure: int) -> int:
    """Return the highest non-empty two-bit hierarchy level."""
    value = int(structure) & 0xFFFF
    for level in range(7, -1, -1):
        if ((value >> (level * 2)) & 0b11) != SHAPE_EMPTY:
            return level
    return 0


def structure_shape(structure: int) -> int:
    level = structure_level(structure)
    return (int(structure) >> (level * 2)) & 0b11


def degrade_structure(structure: int) -> int:
    """Reduce collision damage to one lower structure step without identity."""
    value = int(structure) & 0xFFFF
    level = structure_level(value)
    shape = structure_shape(value)
    if level == 0:
        if shape in (SHAPE_HORIZONTAL, SHAPE_VERTICAL):
            return SHAPE_SINGLE
        return SHAPE_EMPTY
    return SHAPE_SINGLE << ((level - 1) * 2)


@dataclass
class UniverseState:
    """Fixed-size structure-of-arrays state for one authoritative universe."""

    seed: int
    max_cells: int = DEFAULT_MAX_CELLS
    generation: int = 0
    config: Any | None = None
    lifecycle: list[int] = field(init=False)
    x: list[int] = field(init=False)
    y: list[int] = field(init=False)
    structure: list[int] = field(init=False)
    latent: list[int] = field(init=False)
    hp: list[int] = field(init=False)
    bond_strength: list[int] = field(init=False)
    direction: list[int] = field(init=False)
    speed_code: list[int] = field(init=False)
    age: list[int] = field(init=False)
    black_hole_timer: list[int] = field(init=False)
    slow_trace: bytearray = field(init=False)

    def __post_init__(self) -> None:
        if self.max_cells < 1:
            raise ValueError("max_cells must be positive")
        self.lifecycle = [int(Lifecycle.FREE)] * self.max_cells
        self.x = [0] * self.max_cells
        self.y = [0] * self.max_cells
        self.structure = [0] * self.max_cells
        self.latent = [0] * self.max_cells
        self.hp = [0] * self.max_cells
        self.bond_strength = [0] * self.max_cells
        self.direction = [0] * self.max_cells
        self.speed_code = [0] * self.max_cells
        self.age = [0] * self.max_cells
        self.black_hole_timer = [0] * self.max_cells
        self.slow_trace = bytearray(self.max_cells)

    def active_slots(self) -> list[int]:
        """Return ACTIVE storage indices using CPython's C-level list search.

        This is identical to scanning lifecycle in ascending slot order; it
        avoids running a Python comparison for every FREE/BLACK_HOLE entry
        in our fixed-capacity sparse 1024-slot states. It has no cache and
        therefore remains correct after all in-place physical transitions.
        """
        active = int(Lifecycle.ACTIVE)
        indices: list[int] = []
        start = 0
        while True:
            try:
                slot = self.lifecycle.index(active, start)
            except ValueError:
                return indices
            indices.append(slot)
            start = slot + 1

    def spawn(
        self,
        *,
        x: int,
        y: int,
        structure: int = SHAPE_SINGLE,
        latent: int = 0,
        hp: int = 255,
        direction: int = 0,
        speed_code: int = 0,
    ) -> int:
        if not 0 <= structure <= 0xFFFF:
            raise ValueError("structure must fit uint16")
        if not 0 <= latent <= 0xFFFF:
            raise ValueError("latent must fit uint16")
        if not 0 <= hp <= 0xFF:
            raise ValueError("hp must fit uint8")
        if not 0 <= direction < 8:
            raise ValueError("direction must be in 0..7")
        if not 0 <= speed_code < 8:
            raise ValueError("speed_code must be in 0..7")
        for slot in range(self.max_cells):
            if self.lifecycle[slot] == Lifecycle.FREE:
                self.lifecycle[slot] = int(Lifecycle.ACTIVE)
                self.x[slot] = int(x) % 256
                self.y[slot] = int(y) % 256
                self.structure[slot] = int(structure)
                self.latent[slot] = int(latent)
                self.hp[slot] = int(hp)
                self.bond_strength[slot] = 0
                self.direction[slot] = int(direction)
                self.speed_code[slot] = int(speed_code)
                self.age[slot] = 0
                self.black_hole_timer[slot] = 0
                self.slow_trace[slot] = 0
                return slot
        raise RuntimeError("universe cell capacity is full")

    def free(self, slot: int) -> None:
        self._validate_slot(slot)
        self.lifecycle[slot] = int(Lifecycle.FREE)
        self.x[slot] = 0
        self.y[slot] = 0
        self.structure[slot] = 0
        self.latent[slot] = 0
        self.hp[slot] = 0
        self.bond_strength[slot] = 0
        self.direction[slot] = 0
        self.speed_code[slot] = 0
        self.age[slot] = 0
        self.black_hole_timer[slot] = 0
        self.slow_trace[slot] = 0

    def _validate_slot(self, slot: int) -> None:
        if not isinstance(slot, int) or not 0 <= slot < self.max_cells:
            raise IndexError("slot out of range")

    def to_snapshot(self) -> dict[str, Any]:
        config = self.config.to_dict() if self.config is not None else None
        return {
            "format_version": 2,
            "kind": "UniverseGenomePhase1",
            "generation": int(self.generation),
            "seed": int(self.seed),
            "config": config,
            "arrays": {
                "lifecycle": [int(value) for value in self.lifecycle],
                "x": list(self.x),
                "y": list(self.y),
                "structure": list(self.structure),
                "latent": list(self.latent),
                "hp": list(self.hp),
                "bond_strength": list(self.bond_strength),
                "direction": list(self.direction),
                "speed_code": list(self.speed_code),
                "age": list(self.age),
                "black_hole_timer": list(self.black_hole_timer),
                "slow_trace": list(self.slow_trace),
            },
        }

    @classmethod
    def from_snapshot(cls, payload: dict[str, Any], *, config: Any | None = None) -> "UniverseState":
        format_version = int(payload.get("format_version", -1))
        if format_version not in (1, 2) or payload.get("kind") != "UniverseGenomePhase1":
            raise ValueError("unsupported UniverseState snapshot")
        arrays = payload.get("arrays")
        if not isinstance(arrays, dict):
            raise ValueError("snapshot arrays are required")
        lengths = {len(value) for value in arrays.values() if isinstance(value, list)}
        if len(lengths) != 1 or not lengths:
            raise ValueError("snapshot arrays must have equal lengths")
        max_cells = lengths.pop()
        legacy_required = {
            "lifecycle", "x", "y", "structure", "latent", "hp", "bond_strength",
            "direction", "speed_code", "age", "black_hole_timer",
        }
        required = set(legacy_required)
        if format_version == 2:
            required.add("slow_trace")
        if set(arrays) != required:
            raise ValueError("snapshot arrays do not match UniverseState format")
        if format_version == 1 and config is not None and hasattr(config, "to_dict"):
            values = config.to_dict()
            values.update({
                "trace_write_cap": 0,
                "trace_transfer_cap": 0,
                "trace_discharge_cap": 0,
                "trace_decay_rate": 0,
                "trace_bonus_shift": 8,
            })
            config = type(config)(**values)
        state = cls(
            seed=int(payload["seed"]),
            max_cells=max_cells,
            generation=int(payload["generation"]),
            config=config,
        )
        for name in legacy_required:
            values = arrays[name]
            if not isinstance(values, list):
                raise ValueError(f"snapshot array {name!r} is invalid")
            setattr(state, name, [int(value) for value in values])
        if format_version == 1:
            state.slow_trace = bytearray(max_cells)
        else:
            values = arrays["slow_trace"]
            if not isinstance(values, list) or len(values) != max_cells:
                raise ValueError("snapshot slow_trace array is invalid")
            converted = [int(value) for value in values]
            if any(value < 0 or value > 0xFF for value in converted):
                raise ValueError("slow_trace values must fit uint8")
            state.slow_trace = bytearray(converted)
            if any(
                state.lifecycle[slot] == Lifecycle.FREE and state.slow_trace[slot] != 0
                for slot in range(max_cells)
            ):
                raise ValueError("FREE snapshot slots must have zero slow_trace")
        return state
