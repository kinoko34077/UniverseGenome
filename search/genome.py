"""Universe-genome fields and deterministic adjacent binary-grid mutation."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

UNIVERSE_GENOME_FIELDS = (
    "initial_density",
    "hp_decay",
    "hp_gain",
    "noise_rate",
    "bond_gain",
    "bond_decay",
    "collision_threshold",
    "fusion_threshold",
    "fragmentation_base_probability",
    "black_hole_grace",
    "rotate_amount",
)


GENOME_BOUNDS = {
    "initial_density": (0, 0xFFFF),
    "hp_decay": (0, 0xFF),
    "hp_gain": (0, 0xFF),
    "noise_rate": (0, 0xFFFF),
    "bond_gain": (0, 0xFF),
    "bond_decay": (0, 0xFF),
    "collision_threshold": (0, 0xFF),
    "fusion_threshold": (0, 0xFF),
    "fragmentation_base_probability": (0, 0xFFFF),
    "black_hole_grace": (0, 0xFFFF),
    "rotate_amount": (0, 15),
}


@dataclass(frozen=True)
class UniverseGenome:
    initial_density: int = 0
    hp_decay: int = 1
    hp_gain: int = 32
    noise_rate: int = 0
    bond_gain: int = 4
    bond_decay: int = 1
    collision_threshold: int = 8
    fusion_threshold: int = 8
    fragmentation_base_probability: int = 0
    black_hole_grace: int = 2
    rotate_amount: int = 4

    @classmethod
    def default(cls) -> "UniverseGenome":
        return cls()

    def to_dict(self) -> dict[str, int]:
        return {field.name: int(getattr(self, field.name)) for field in fields(self)}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UniverseGenome":
        unknown = set(payload) - set(UNIVERSE_GENOME_FIELDS)
        if unknown:
            raise ValueError(f"unknown universe genome fields: {sorted(unknown)}")
        return cls(**{name: int(payload.get(name, getattr(cls(), name))) for name in UNIVERSE_GENOME_FIELDS})

    def mutate(self, field: str, *, direction: int) -> "UniverseGenome":
        if field not in UNIVERSE_GENOME_FIELDS:
            raise ValueError(f"cannot mutate non-genome field: {field}")
        if direction not in (-1, 1):
            raise ValueError("direction must be -1 or 1")
        current = int(getattr(self, field))
        lower, upper = GENOME_BOUNDS[field]
        if direction > 0:
            next_value = 1 if current == 0 else current * 2
        else:
            next_value = 0 if current <= 1 else current // 2
        next_value = min(upper, max(lower, next_value))
        values = self.to_dict()
        values[field] = next_value
        return type(self)(**values)
