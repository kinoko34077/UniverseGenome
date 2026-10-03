"""Universe-genome fields and deterministic adjacent binary-grid mutation."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from core.physics import PhysicsConfig

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

INITIAL_GENOME_VARIATION_FIELDS = (
    "hp_decay",
    "hp_gain",
    "noise_rate",
    "bond_gain",
    "bond_decay",
    "collision_threshold",
    "fusion_threshold",
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
    initial_density: int = 4
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

    def __post_init__(self) -> None:
        for name in UNIVERSE_GENOME_FIELDS:
            value = getattr(self, name)
            lower, upper = GENOME_BOUNDS[name]
            if not isinstance(value, int) or not lower <= value <= upper:
                raise ValueError(f"{name} must be an integer in {lower}..{upper}")

    @classmethod
    def default(cls) -> "UniverseGenome":
        return cls()

    @classmethod
    def initial_population(cls, count: int = 8) -> tuple["UniverseGenome", ...]:
        if count != 8:
            raise ValueError("Phase 5 initial population requires exactly 8 genomes")
        base = cls.default()
        return (base,) + tuple(
            base.mutate(field, direction=1)
            for field in INITIAL_GENOME_VARIATION_FIELDS
        )

    def to_dict(self) -> dict[str, int]:
        return {field.name: int(getattr(self, field.name)) for field in fields(self)}

    def to_physics_config(self, base: PhysicsConfig | None = None) -> PhysicsConfig:
        """Return the effective physics config represented by every genome field."""
        resolved = base or PhysicsConfig()
        if self.initial_density > resolved.max_cells:
            raise ValueError("initial_density cannot exceed PhysicsConfig.max_cells")
        values = resolved.to_dict()
        values.update({
            "initial_density": self.initial_density,
            "hp_decay": self.hp_decay,
            "recovery_hp": self.hp_gain,
            "noise_rate": self.noise_rate,
            "bond_gain": self.bond_gain,
            "bond_decay": self.bond_decay,
            "collision_threshold": self.collision_threshold,
            "fusion_velocity_threshold": self.fusion_threshold,
            "fragmentation_rate": self.fragmentation_base_probability,
            "black_hole_grace": self.black_hole_grace,
            "rotate_amount": self.rotate_amount,
        })
        return PhysicsConfig(**values)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UniverseGenome":
        unknown = set(payload) - set(UNIVERSE_GENOME_FIELDS)
        if unknown:
            raise ValueError(f"unknown universe genome fields: {sorted(unknown)}")
        return cls(**{name: int(payload.get(name, getattr(cls(), name))) for name in UNIVERSE_GENOME_FIELDS})

    def effective_bounds(
        self,
        field: str,
        *,
        base: PhysicsConfig | None = None,
    ) -> tuple[int, int]:
        """Return genome bounds after applying dependent physics limits."""
        if field not in UNIVERSE_GENOME_FIELDS:
            raise ValueError(f"cannot mutate non-genome field: {field}")
        resolved = base or PhysicsConfig()
        lower, upper = GENOME_BOUNDS[field]
        if field == "initial_density":
            upper = min(upper, resolved.max_cells)
        return lower, upper

    @staticmethod
    def _next_mutation_value(
        current: int,
        *,
        direction: int,
        lower: int,
        upper: int,
    ) -> int:
        if direction > 0:
            next_value = 1 if current == 0 else current * 2
        else:
            next_value = 0 if current <= 1 else current // 2
        return min(upper, max(lower, next_value))

    def mutation_directions(
        self,
        field: str,
        *,
        base: PhysicsConfig | None = None,
    ) -> tuple[int, ...]:
        """Return directions that produce a valid, changed effective genome."""
        lower, upper = self.effective_bounds(field, base=base)
        resolved = base or PhysicsConfig()
        current = int(getattr(self, field))
        valid: list[int] = []
        for direction in (-1, 1):
            next_value = self._next_mutation_value(
                current,
                direction=direction,
                lower=lower,
                upper=upper,
            )
            if next_value == current:
                continue
            values = self.to_dict()
            values[field] = next_value
            candidate = type(self)(**values)
            try:
                candidate.to_physics_config(resolved)
            except ValueError:
                continue
            valid.append(direction)
        return tuple(valid)

    def mutate(
        self,
        field: str,
        *,
        direction: int,
        base: PhysicsConfig | None = None,
    ) -> "UniverseGenome":
        if field not in UNIVERSE_GENOME_FIELDS:
            raise ValueError(f"cannot mutate non-genome field: {field}")
        if direction not in (-1, 1):
            raise ValueError("direction must be -1 or 1")
        current = int(getattr(self, field))
        valid_directions = self.mutation_directions(field, base=base)
        if direction not in valid_directions:
            raise ValueError(
                f"mutation direction {direction} does not produce a valid adjacent value"
            )
        lower, upper = self.effective_bounds(field, base=base)
        next_value = self._next_mutation_value(
            current,
            direction=direction,
            lower=lower,
            upper=upper,
        )
        values = self.to_dict()
        values[field] = next_value
        return type(self)(**values)
