"""Deterministic single-universe physics through Phase 2B."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Iterable, Mapping

from .geometry import FIXED_POINT_SIZE, LOGICAL_SIZE, tile_coordinate, wrap_fixed
from .rng import event_index, event_key, event_u16
from .state import (
    Lifecycle,
    SHAPE_HORIZONTAL,
    SHAPE_SINGLE,
    SHAPE_VERTICAL,
    UniverseState,
    degrade_structure,
    structure_shape,
)


SPEED_MAGNITUDES = (0, 1, 2, 4, 8, 16, 32, 64)
EVENT_NOISE = 1
EVENT_COLLISION_PAIR = 2
EVENT_LATENT_MASK = 3
LATENT_OPERATORS = {"masked_copy", "masked_xor", "rotate_copy", "masked_and"}


@dataclass(frozen=True)
class PhysicsConfig:
    logical_size: int = LOGICAL_SIZE
    fixed_point_size: int = FIXED_POINT_SIZE
    max_cells: int = 1024
    noise_rate: int = 0
    noise_attempts: int = 0
    noise_spawn_hp: int = 255
    noise_structure: int = SHAPE_SINGLE
    hp_decay: int = 0
    recovery_hp: int = 32
    collision_threshold: int = 8
    collision_damage: int = 8
    latent_damage_mask: int = 1
    structure_damage_threshold: int = 16
    black_hole_grace: int = 2
    bond_gain: int = 4
    bond_decay: int = 1
    bond_velocity_threshold: int = 8
    latent_operator: str = "masked_copy"
    rotate_amount: int = 4

    def __post_init__(self) -> None:
        if self.logical_size != 32 or self.fixed_point_size != 256:
            raise ValueError("Phase 1 requires a 32x32 / 256-unit world")
        if self.max_cells < 1:
            raise ValueError("max_cells must be positive")
        if not 0 <= self.noise_rate <= 0xFFFF:
            raise ValueError("noise_rate must be in 0..65535")
        for name in (
            "noise_attempts", "hp_decay", "recovery_hp", "collision_threshold",
            "collision_damage", "structure_damage_threshold", "black_hole_grace",
            "bond_velocity_threshold",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if not 0 <= self.bond_gain <= 0xFF or not 0 <= self.bond_decay <= 0xFF:
            raise ValueError("bond gain/decay must fit uint8")
        if self.latent_operator not in LATENT_OPERATORS:
            raise ValueError(f"unsupported latent operator: {self.latent_operator}")
        if not 0 <= self.rotate_amount < 16:
            raise ValueError("rotate_amount must be in 0..15")
        if not 0 <= self.noise_spawn_hp <= 0xFF or not 0 <= self.recovery_hp <= 0xFF:
            raise ValueError("HP parameters must fit uint8")
        if not 0 <= self.noise_structure <= 0xFFFF:
            raise ValueError("noise_structure must fit uint16")
        if not 0 <= self.latent_damage_mask <= 0xFFFF:
            raise ValueError("latent_damage_mask must fit uint16")

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "PhysicsConfig":
        world = mapping.get("world", {}) if isinstance(mapping.get("world", {}), Mapping) else {}
        values = mapping.get("physics", mapping)
        if not isinstance(values, Mapping):
            values = {}
        return cls(
            logical_size=int(world.get("logical_size", values.get("logical_size", LOGICAL_SIZE))),
            fixed_point_size=int(world.get("fixed_point_size", values.get("fixed_point_size", FIXED_POINT_SIZE))),
            max_cells=int(world.get("max_cells", values.get("max_cells", 1024))),
            noise_rate=int(values.get("noise_rate", 0)),
            noise_attempts=int(values.get("noise_attempts", 0)),
            noise_spawn_hp=int(values.get("noise_spawn_hp", 255)),
            noise_structure=int(values.get("noise_structure", SHAPE_SINGLE)),
            hp_decay=int(values.get("hp_decay", 0)),
            recovery_hp=int(values.get("recovery_hp", 32)),
            collision_threshold=int(values.get("collision_threshold", 8)),
            collision_damage=int(values.get("collision_damage", 8)),
            latent_damage_mask=int(values.get("latent_damage_mask", 1)),
            structure_damage_threshold=int(values.get("structure_damage_threshold", 16)),
            black_hole_grace=int(values.get("black_hole_grace", 2)),
            bond_gain=int(values.get("bond_gain", 4)),
            bond_decay=int(values.get("bond_decay", 1)),
            bond_velocity_threshold=int(values.get("bond_velocity_threshold", 8)),
            latent_operator=str(values.get("latent_operator", "masked_copy")),
            rotate_amount=int(values.get("rotate_amount", 4)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "logical_size": self.logical_size,
            "fixed_point_size": self.fixed_point_size,
            "max_cells": self.max_cells,
            "noise_rate": self.noise_rate,
            "noise_attempts": self.noise_attempts,
            "noise_spawn_hp": self.noise_spawn_hp,
            "noise_structure": self.noise_structure,
            "hp_decay": self.hp_decay,
            "recovery_hp": self.recovery_hp,
            "collision_threshold": self.collision_threshold,
            "collision_damage": self.collision_damage,
            "latent_damage_mask": self.latent_damage_mask,
            "structure_damage_threshold": self.structure_damage_threshold,
            "black_hole_grace": self.black_hole_grace,
            "bond_gain": self.bond_gain,
            "bond_decay": self.bond_decay,
            "bond_velocity_threshold": self.bond_velocity_threshold,
            "latent_operator": self.latent_operator,
            "rotate_amount": self.rotate_amount,
        }


@dataclass(frozen=True)
class StepMetrics:
    generation: int
    active_cells: int
    collision_count: int
    collision_pair_evaluations: int
    bond_contact_count: int
    latent_transmission_count: int
    noise_spawn_count: int
    generations_per_second: float


def create_universe(seed: int = 0, config: PhysicsConfig | Mapping[str, Any] | None = None) -> UniverseState:
    if config is None:
        resolved = PhysicsConfig()
    elif isinstance(config, PhysicsConfig):
        resolved = config
    else:
        resolved = PhysicsConfig.from_mapping(config)
    return UniverseState(seed=int(seed), max_cells=resolved.max_cells, config=resolved)


def speed_code_for_magnitude(magnitude: int) -> int:
    try:
        return SPEED_MAGNITUDES.index(int(magnitude))
    except ValueError as exc:
        raise ValueError(f"unsupported speed magnitude: {magnitude}") from exc


def velocity_vector(direction: int, speed_code: int) -> tuple[int, int]:
    if not 0 <= direction < 8 or not 0 <= speed_code < len(SPEED_MAGNITUDES):
        raise ValueError("direction or speed code out of range")
    magnitude = SPEED_MAGNITUDES[speed_code]
    vectors = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))
    dx, dy = vectors[direction]
    return dx * magnitude, dy * magnitude


def relative_velocity(direction_a: int, speed_a: int, direction_b: int, speed_b: int) -> int:
    ax, ay = velocity_vector(direction_a, speed_a)
    bx, by = velocity_vector(direction_b, speed_b)
    return max(abs(ax - bx), abs(ay - by))


def transmission_mask(
    seed: int,
    generation: int,
    address: int,
    pair: tuple[int, int],
    bond_strength: int,
) -> int:
    """Select a deterministic anonymous subset of the sixteen latent bits."""
    if not 0 <= bond_strength <= 0xFF:
        raise ValueError("bond_strength must fit uint8")
    if len(pair) != 2:
        raise ValueError("pair must contain two slots")
    width = 1 + (bond_strength >> 4)
    available = list(range(16))
    mask = 0
    pair_index = ((int(pair[0]) & 0xFFFF) << 16) | (int(pair[1]) & 0xFFFF)
    for choice in range(width):
        key = event_key(seed, generation, address, EVENT_LATENT_MASK, pair_index + choice)
        selected = available.pop(event_index(key, len(available)))
        mask |= 1 << selected
    return mask


def apply_latent_operator(
    operator: str,
    source: int,
    destination: int,
    mask: int,
    *,
    rotate_amount: int = 4,
) -> int:
    """Apply one 16-bit local operator without widening latent state."""
    if operator not in LATENT_OPERATORS:
        raise ValueError(f"unsupported latent operator: {operator}")
    if not 0 <= rotate_amount < 16:
        raise ValueError("rotate_amount must be in 0..15")
    source = int(source) & 0xFFFF
    destination = int(destination) & 0xFFFF
    mask = int(mask) & 0xFFFF
    if operator == "masked_copy":
        result = (destination & ~mask) | (source & mask)
    elif operator == "masked_xor":
        result = destination ^ (source & mask)
    elif operator == "rotate_copy":
        rotated = ((source << rotate_amount) | (source >> ((16 - rotate_amount) % 16))) & 0xFFFF
        result = (destination & ~mask) | (rotated & mask)
    else:
        result = destination & (source | (~mask & 0xFFFF))
    return result & 0xFFFF


def destination_footprint(structure: int, x: int, y: int) -> set[tuple[int, int]]:
    tile_x = tile_coordinate(x)
    tile_y = tile_coordinate(y)
    shape = structure_shape(structure)
    if shape == SHAPE_HORIZONTAL:
        return {(tile_x, tile_y), ((tile_x + 1) % LOGICAL_SIZE, tile_y)}
    if shape == SHAPE_VERTICAL:
        return {(tile_x, tile_y), (tile_x, (tile_y + 1) % LOGICAL_SIZE)}
    if shape == SHAPE_SINGLE:
        return {(tile_x, tile_y)}
    return set()


def _collision_pair(
    state: UniverseState,
    candidates: list[int],
    address: int,
    generation: int,
) -> tuple[int, int]:
    ordered = sorted(set(candidates))
    if len(ordered) == 2:
        return ordered[0], ordered[1]
    first = event_index(event_key(state.seed, generation, address, EVENT_COLLISION_PAIR, 0), len(ordered))
    second = event_index(event_key(state.seed, generation, address, EVENT_COLLISION_PAIR, 1), len(ordered) - 1)
    if second >= first:
        second += 1
    pair = (ordered[first], ordered[second])
    return tuple(sorted(pair))


def _spawn_noise(state: UniverseState, config: PhysicsConfig, generation: int) -> int:
    spawned = 0
    for attempt in range(config.noise_attempts):
        base = attempt * 4
        chance_key = event_key(state.seed, generation, 0, EVENT_NOISE, base)
        if event_u16(chance_key) >= config.noise_rate:
            continue
        x = event_u16(event_key(state.seed, generation, 0, EVENT_NOISE, base + 1)) & 0xFF
        y = event_u16(event_key(state.seed, generation, 0, EVENT_NOISE, base + 2)) & 0xFF
        direction = event_u16(event_key(state.seed, generation, 0, EVENT_NOISE, base + 3)) & 0x07
        try:
            state.spawn(
                x=x,
                y=y,
                structure=config.noise_structure,
                hp=config.noise_spawn_hp,
                direction=direction,
                speed_code=0,
            )
        except RuntimeError:
            # Capacity is a declared deterministic boundary, not permission
            # to grow the authoritative arrays.
            continue
        spawned += 1
    return spawned


def _transmit_latent(
    state: UniverseState,
    config: PhysicsConfig,
    pairs: set[tuple[int, int]],
    pair_addresses: dict[tuple[int, int], int],
    generation: int,
) -> tuple[int, set[int]]:
    """Resolve one deterministic, non-overlapping transmission per active slot."""
    selected_pairs: list[tuple[int, int]] = []
    selected_slots: set[int] = set()
    for pair in sorted(pairs):
        if pair[0] in selected_slots or pair[1] in selected_slots:
            continue
        selected_pairs.append(pair)
        selected_slots.update(pair)

    before = list(state.latent)
    updates: dict[int, int] = {}
    activity_slots: set[int] = set()
    for first, second in selected_pairs:
        address = pair_addresses[(first, second)]
        first_mask = transmission_mask(
            state.seed,
            generation,
            address,
            (first, second),
            state.bond_strength[first],
        )
        second_mask = transmission_mask(
            state.seed,
            generation,
            address,
            (second, first),
            state.bond_strength[second],
        )
        updates[second] = apply_latent_operator(
            config.latent_operator,
            before[first],
            before[second],
            first_mask,
            rotate_amount=config.rotate_amount,
        )
        updates[first] = apply_latent_operator(
            config.latent_operator,
            before[second],
            before[first],
            second_mask,
            rotate_amount=config.rotate_amount,
        )
        activity_slots.update((first, second))

    for slot, value in updates.items():
        state.latent[slot] = value
    return len(selected_pairs), activity_slots


def _enter_black_hole(state: UniverseState, slot: int, config: PhysicsConfig) -> None:
    state.lifecycle[slot] = int(Lifecycle.BLACK_HOLE)
    state.black_hole_timer[slot] = config.black_hole_grace
    state.hp[slot] = 0


def step(
    state: UniverseState,
    config: PhysicsConfig | None = None,
    *,
    stimulus_slots: Iterable[int] = (),
) -> StepMetrics:
    """Advance one synchronous generation in-place and return bounded metrics."""
    resolved = config or state.config or PhysicsConfig(max_cells=state.max_cells)
    if state.max_cells != resolved.max_cells:
        raise ValueError("state/config capacity mismatch")
    state.config = resolved
    started = time.perf_counter()
    generation = state.generation
    stimulated = set(int(slot) for slot in stimulus_slots)
    recovered_slots: set[int] = set()

    for slot in range(state.max_cells):
        if state.lifecycle[slot] == Lifecycle.BLACK_HOLE:
            if slot in stimulated:
                state.lifecycle[slot] = int(Lifecycle.ACTIVE)
                state.hp[slot] = resolved.recovery_hp
                state.black_hole_timer[slot] = 0
                recovered_slots.add(slot)
            else:
                state.black_hole_timer[slot] -= 1
                if state.black_hole_timer[slot] <= 0:
                    state.free(slot)

    noise_spawn_count = _spawn_noise(state, resolved, generation)
    active = state.active_slots()
    proposals: dict[int, tuple[int, int, set[tuple[int, int]]]] = {}
    for slot in active:
        dx, dy = velocity_vector(state.direction[slot], state.speed_code[slot])
        proposed_x = wrap_fixed(state.x[slot] + dx)
        proposed_y = wrap_fixed(state.y[slot] + dy)
        proposals[slot] = (
            proposed_x,
            proposed_y,
            destination_footprint(state.structure[slot], proposed_x, proposed_y),
        )

    occupancy: dict[tuple[int, int], list[int]] = {}
    for slot, (proposed_x, proposed_y, footprint) in proposals.items():
        state.x[slot] = proposed_x
        state.y[slot] = proposed_y
        for tile in footprint:
            occupancy.setdefault(tile, []).append(slot)

    pairs: set[tuple[int, int]] = set()
    pair_addresses: dict[tuple[int, int], int] = {}
    for tile_x, tile_y in sorted(occupancy):
        candidates = occupancy[(tile_x, tile_y)]
        if len(set(candidates)) >= 2:
            address = (tile_y << 5) | tile_x
            pair = _collision_pair(state, candidates, address, generation)
            pairs.add(pair)
            pair_addresses.setdefault(pair, address)

    collision_count = len(pairs)
    compatible_pairs: set[tuple[int, int]] = set()
    for first, second in sorted(pairs):
        if state.lifecycle[first] != Lifecycle.ACTIVE or state.lifecycle[second] != Lifecycle.ACTIVE:
            continue
        relative = relative_velocity(
            state.direction[first], state.speed_code[first],
            state.direction[second], state.speed_code[second],
        )
        if relative <= resolved.bond_velocity_threshold:
            compatible_pairs.add((first, second))
        if relative >= resolved.collision_threshold:
            state.hp[first] = max(0, state.hp[first] - resolved.collision_damage)
            state.hp[second] = max(0, state.hp[second] - resolved.collision_damage)
            state.latent[first] &= ~resolved.latent_damage_mask
            state.latent[second] &= ~resolved.latent_damage_mask
            if relative >= resolved.structure_damage_threshold:
                state.structure[first] = degrade_structure(state.structure[first])
                state.structure[second] = degrade_structure(state.structure[second])

    bond_contact_slots = {
        slot
        for pair in compatible_pairs
        for slot in pair
    }
    for slot in active:
        if state.lifecycle[slot] != Lifecycle.ACTIVE:
            continue
        if slot in bond_contact_slots:
            state.bond_strength[slot] = min(0xFF, state.bond_strength[slot] + resolved.bond_gain)
        else:
            state.bond_strength[slot] = max(0, state.bond_strength[slot] - resolved.bond_decay)

    latent_transmission_count, latent_activity_slots = _transmit_latent(
        state,
        resolved,
        compatible_pairs,
        {pair: pair_addresses[pair] for pair in compatible_pairs},
        generation,
    )
    for slot in active:
        if state.lifecycle[slot] != Lifecycle.ACTIVE:
            continue
        if slot in stimulated and slot not in recovered_slots:
            state.hp[slot] = min(0xFF, state.hp[slot] + resolved.recovery_hp)
        elif slot in latent_activity_slots:
            state.hp[slot] = min(0xFF, state.hp[slot] + resolved.recovery_hp)
        state.hp[slot] = max(0, state.hp[slot] - resolved.hp_decay)
        state.age[slot] = min(0xFFFFFFFF, state.age[slot] + 1)
        if state.hp[slot] == 0:
            _enter_black_hole(state, slot, resolved)

    state.generation += 1
    elapsed = max(time.perf_counter() - started, 1e-12)
    return StepMetrics(
        generation=state.generation,
        active_cells=len(state.active_slots()),
        collision_count=collision_count,
        collision_pair_evaluations=collision_count,
        bond_contact_count=len(compatible_pairs),
        latent_transmission_count=latent_transmission_count,
        noise_spawn_count=noise_spawn_count,
        generations_per_second=1.0 / elapsed,
    )
