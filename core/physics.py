"""Deterministic single-universe physics through Phase 2E."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
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
    structure_level,
    structure_shape,
)


SPEED_MAGNITUDES = (0, 1, 2, 4, 8, 16, 32, 64)
EVENT_NOISE = 1
EVENT_COLLISION_PAIR = 2
EVENT_LATENT_MASK = 3
EVENT_FRAGMENTATION = 4
EVENT_INITIAL_DENSITY = 5
EVENT_SLOW_TRACE_DECAY = 6
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
    noise_latent: int = 1
    noise_speed_code: int = 1
    initial_density: int = 0
    initial_latent: int = 1
    initial_speed_code: int = 1
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
    fusion_enabled: bool = False
    fusion_velocity_threshold: int = 8
    fusion_bond_threshold: int = 32
    fragmentation_enabled: bool = False
    fragmentation_rate: int = 0
    aging_enabled: bool = False
    trace_write_cap: int = 0
    trace_transfer_cap: int = 0
    trace_discharge_cap: int = 0
    trace_decay_rate: int = 0
    trace_bonus_shift: int = 8

    def __post_init__(self) -> None:
        if self.logical_size != 32 or self.fixed_point_size != 256:
            raise ValueError("Phase 1 requires a 32x32 / 256-unit world")
        if self.max_cells < 1:
            raise ValueError("max_cells must be positive")
        if not 0 <= self.initial_density <= self.max_cells:
            raise ValueError("initial_density must be within max_cells")
        if not 0 <= self.noise_rate <= 0xFFFF:
            raise ValueError("noise_rate must be in 0..65535")
        for name in (
            "noise_attempts", "hp_decay", "recovery_hp", "collision_threshold",
            "collision_damage", "structure_damage_threshold", "black_hole_grace",
            "bond_velocity_threshold",
            "fusion_velocity_threshold",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if not 0 <= self.bond_gain <= 0xFF or not 0 <= self.bond_decay <= 0xFF:
            raise ValueError("bond gain/decay must fit uint8")
        if self.latent_operator not in LATENT_OPERATORS:
            raise ValueError(f"unsupported latent operator: {self.latent_operator}")
        if not 0 <= self.rotate_amount < 16:
            raise ValueError("rotate_amount must be in 0..15")
        if not 0 <= self.fusion_bond_threshold <= 0xFF:
            raise ValueError("fusion_bond_threshold must fit uint8")
        if not 0 <= self.fragmentation_rate <= 0xFFFF:
            raise ValueError("fragmentation_rate must fit uint16")
        if not 0 <= self.noise_spawn_hp <= 0xFF or not 0 <= self.recovery_hp <= 0xFF:
            raise ValueError("HP parameters must fit uint8")
        if not 0 <= self.noise_structure <= 0xFFFF:
            raise ValueError("noise_structure must fit uint16")
        for name in ("noise_latent", "initial_latent"):
            if not 0 <= getattr(self, name) <= 0xFFFF:
                raise ValueError(f"{name} must fit uint16")
        for name in ("noise_speed_code", "initial_speed_code"):
            if not 0 <= getattr(self, name) < len(SPEED_MAGNITUDES):
                raise ValueError(f"{name} must be a supported speed code")
        if not 0 <= self.latent_damage_mask <= 0xFFFF:
            raise ValueError("latent_damage_mask must fit uint16")
        for name in ("trace_write_cap", "trace_transfer_cap", "trace_discharge_cap"):
            if not 0 <= getattr(self, name) <= 0xFF:
                raise ValueError(f"{name} must fit uint8")
        if not 0 <= self.trace_decay_rate <= 0xFFFF:
            raise ValueError("trace_decay_rate must fit uint16")
        if not 0 <= self.trace_bonus_shift <= 8:
            raise ValueError("trace_bonus_shift must be in 0..8")

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
            noise_latent=int(values.get("noise_latent", 1)),
            noise_speed_code=int(values.get("noise_speed_code", 1)),
            initial_density=int(values.get("initial_density", 0)),
            initial_latent=int(values.get("initial_latent", 1)),
            initial_speed_code=int(values.get("initial_speed_code", 1)),
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
            fusion_enabled=bool(values.get("fusion_enabled", False)),
            fusion_velocity_threshold=int(values.get("fusion_velocity_threshold", 8)),
            fusion_bond_threshold=int(values.get("fusion_bond_threshold", 32)),
            fragmentation_enabled=bool(values.get("fragmentation_enabled", False)),
            fragmentation_rate=int(values.get("fragmentation_rate", 0)),
            trace_write_cap=int(values.get("trace_write_cap", 0)),
            trace_transfer_cap=int(values.get("trace_transfer_cap", 0)),
            trace_discharge_cap=int(values.get("trace_discharge_cap", 0)),
            trace_decay_rate=int(values.get("trace_decay_rate", 0)),
            trace_bonus_shift=int(values.get("trace_bonus_shift", 8)),
            aging_enabled=bool(
                mapping.get("features", {}).get("aging", values.get("aging_enabled", False))
                if isinstance(mapping.get("features", {}), Mapping)
                else values.get("aging_enabled", False)
            ),
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
            "noise_latent": self.noise_latent,
            "noise_speed_code": self.noise_speed_code,
            "initial_density": self.initial_density,
            "initial_latent": self.initial_latent,
            "initial_speed_code": self.initial_speed_code,
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
            "fusion_enabled": self.fusion_enabled,
            "fusion_velocity_threshold": self.fusion_velocity_threshold,
            "fusion_bond_threshold": self.fusion_bond_threshold,
            "fragmentation_enabled": self.fragmentation_enabled,
            "fragmentation_rate": self.fragmentation_rate,
            "aging_enabled": self.aging_enabled,
            "trace_write_cap": self.trace_write_cap,
            "trace_transfer_cap": self.trace_transfer_cap,
            "trace_discharge_cap": self.trace_discharge_cap,
            "trace_decay_rate": self.trace_decay_rate,
            "trace_bonus_shift": self.trace_bonus_shift,
        }


@dataclass(frozen=True)
class StepMetrics:
    generation: int
    active_cells: int
    collision_count: int
    collision_pair_evaluations: int
    bond_contact_count: int
    latent_transmission_count: int
    fusion_count: int
    fragmentation_count: int
    noise_spawn_count: int
    generations_per_second: float

    @property
    def activity_cost(self) -> int:
        """Count bounded physical activity events for fitness accounting."""
        return (
            self.collision_count
            + self.bond_contact_count
            + self.latent_transmission_count
            + self.fusion_count
            + self.fragmentation_count
            + self.noise_spawn_count
        )


def create_universe(seed: int = 0, config: PhysicsConfig | Mapping[str, Any] | None = None) -> UniverseState:
    if config is None:
        resolved = PhysicsConfig()
    elif isinstance(config, PhysicsConfig):
        resolved = config
    else:
        resolved = PhysicsConfig.from_mapping(config)
    state = UniverseState(seed=int(seed), max_cells=resolved.max_cells, config=resolved)
    for slot in range(resolved.initial_density):
        x, y = _safe_spawn_position(
            seed=state.seed,
            generation=0,
            address=slot,
            event_type=EVENT_INITIAL_DENSITY,
            structure=resolved.noise_structure,
            base_index=0,
        )
        state.spawn(
            x=x,
            y=y,
            structure=resolved.noise_structure,
            latent=resolved.initial_latent,
            hp=resolved.noise_spawn_hp,
            direction=event_u16(event_key(state.seed, 0, slot, EVENT_INITIAL_DENSITY, 2)) & 0x07,
            speed_code=resolved.initial_speed_code,
        )
    return state


def _safe_spawn_position(
    *,
    seed: int,
    generation: int,
    address: int,
    event_type: int,
    structure: int,
    base_index: int,
) -> tuple[int, int]:
    """Choose a deterministic spawn position whose footprint misses fixed organs."""
    from .io_bus import FixedOrgans

    fixed = FixedOrgans.occupied_coordinates()
    for attempt in range(32):
        offset = base_index + (attempt * 2)
        x = event_u16(event_key(seed, generation, address, event_type, offset)) & 0xFF
        y = event_u16(event_key(seed, generation, address, event_type, offset + 1)) & 0xFF
        if destination_footprint(structure, x, y).isdisjoint(fixed):
            return x, y

    # A deterministic logical-tile fallback guarantees progress even when a
    # particular event stream repeatedly samples a fixed-organ coordinate.
    for tile_y in range(LOGICAL_SIZE):
        for tile_x in range(LOGICAL_SIZE):
            x, y = tile_x * 8, tile_y * 8
            if destination_footprint(structure, x, y).isdisjoint(fixed):
                return x, y
    raise RuntimeError("no spawn position remains outside fixed I/O organs")


def speed_code_for_magnitude(magnitude: int) -> int:
    try:
        return SPEED_MAGNITUDES.index(int(magnitude))
    except ValueError as exc:
        raise ValueError(f"unsupported speed magnitude: {magnitude}") from exc


def age_class(age: int) -> int:
    """Return the highest-set-bit age class, with age zero in the base class."""
    value = int(age)
    if value <= 0:
        return 0
    return value.bit_length() - 1


def age_scaled_fragmentation_rate(
    base_rate: int,
    age: int,
    *,
    aging_enabled: bool = True,
) -> int:
    """Scale the base uint16 rate by a power of two for the cell's age class."""
    rate = int(base_rate)
    if not 0 <= rate <= 0xFFFF:
        raise ValueError("base_rate must fit uint16")
    if not aging_enabled:
        return rate
    return min(0xFFFF, rate << age_class(age))


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
    participant: UniverseState | None = None,
    *,
    source_trace: int | None = None,
) -> int:
    """Select a deterministic anonymous subset without using slot identity."""
    if not 0 <= bond_strength <= 0xFF:
        raise ValueError("bond_strength must fit uint8")
    if len(pair) != 2:
        raise ValueError("pair must contain two slots")
    base_width = 1 + (bond_strength >> 4)
    trace_value = 0 if source_trace is None else int(source_trace)
    trace_shift = 8
    available = list(range(16))
    mask = 0
    if participant is None:
        local_index = 0
    else:
        slot = int(pair[0])
        participant._validate_slot(slot)
        local_index = ((participant.x[slot] & 0xFF) << 8) | (participant.y[slot] & 0xFF)
        if source_trace is None:
            trace_value = int(participant.slow_trace[slot])
        if participant.config is not None:
            trace_shift = int(participant.config.trace_bonus_shift)
    if not 0 <= trace_value <= 0xFF:
        raise ValueError("source_trace must fit uint8")
    if not 0 <= trace_shift <= 8:
        raise ValueError("trace_bonus_shift must be in 0..8")
    width = min(16, base_width + (trace_value >> trace_shift))
    for choice in range(width):
        key = event_key(seed, generation, address, EVENT_LATENT_MASK, local_index + choice)
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


def rotate_left16(value: int, amount: int) -> int:
    amount %= 16
    value &= 0xFFFF
    return ((value << amount) | (value >> ((16 - amount) % 16))) & 0xFFFF


def mix_fusion_latent(latents: Iterable[int]) -> int:
    accumulator = 0
    for index, latent in enumerate(latents):
        accumulator ^= rotate_left16(int(latent), (index % 4) * 4)
    return accumulator & 0xFFFF


def fragmentation_split_mask(
    seed: int,
    generation: int,
    spatial_address: int,
    local_index: int,
) -> int:
    """Return a split mask addressed by physical location, never a slot."""
    return event_u16(event_key(seed, generation, int(spatial_address), EVENT_FRAGMENTATION, int(local_index)))


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
    ordered = sorted(set(candidates), key=lambda slot: _cell_order_key(state, slot))
    if len(ordered) == 2:
        return ordered[0], ordered[1]
    first = event_index(event_key(state.seed, generation, address, EVENT_COLLISION_PAIR, 0), len(ordered))
    second = event_index(event_key(state.seed, generation, address, EVENT_COLLISION_PAIR, 1), len(ordered) - 1)
    if second >= first:
        second += 1
    pair = (ordered[first], ordered[second])
    return tuple(sorted(pair))


def _cell_order_key(state: UniverseState, slot: int) -> tuple[int, ...]:
    """Order equivalent physical participants without using storage identity."""
    return (
        tile_coordinate(state.y[slot]),
        tile_coordinate(state.x[slot]),
        state.structure[slot],
        state.latent[slot],
        state.hp[slot],
        state.bond_strength[slot],
        state.direction[slot],
        state.speed_code[slot],
        state.age[slot],
    )


def _spawn_noise(state: UniverseState, config: PhysicsConfig, generation: int) -> int:
    chance_key = event_key(state.seed, generation, 0, EVENT_NOISE, 0)
    if event_u16(chance_key) >= config.noise_rate:
        return 0
    x, y = _safe_spawn_position(
        seed=state.seed,
        generation=generation,
        address=0,
        event_type=EVENT_NOISE,
        structure=config.noise_structure,
        base_index=1,
    )
    direction = event_u16(event_key(state.seed, generation, 0, EVENT_NOISE, 3)) & 0x07
    try:
        state.spawn(
            x=x,
            y=y,
            structure=config.noise_structure,
            latent=config.noise_latent,
            hp=config.noise_spawn_hp,
            direction=direction,
            speed_code=config.noise_speed_code,
        )
    except RuntimeError:
        # Capacity is a declared deterministic boundary, not permission
        # to grow the authoritative arrays.
        return 0
    return 1


def _transmit_latent(
    state: UniverseState,
    config: PhysicsConfig,
    pairs: set[tuple[int, int]],
    pair_addresses: dict[tuple[int, int], int],
    generation: int,
    trace_start: list[int],
) -> tuple[int, set[int], tuple[tuple[int, int], ...]]:
    """Resolve one deterministic, non-overlapping transmission per active slot."""
    selected_pairs: list[tuple[int, int]] = []
    selected_slots: set[int] = set()
    for pair in sorted(
        pairs,
        key=lambda item: (_cell_order_key(state, item[0]), _cell_order_key(state, item[1])),
    ):
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
            participant=state,
            source_trace=trace_start[first],
        )
        second_mask = transmission_mask(
            state.seed,
            generation,
            address,
            (second, first),
            state.bond_strength[second],
            participant=state,
            source_trace=trace_start[second],
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
    return len(selected_pairs), activity_slots, tuple(selected_pairs)


def _fusion_candidates(
    state: UniverseState,
    occupancy: dict[tuple[int, int], list[int]],
    config: PhysicsConfig,
) -> list[tuple[tuple[int, int], tuple[int, ...]]]:
    """Find deterministic local exact covers of 2x2 destination regions."""
    candidates_by_anchor: list[tuple[tuple[int, int], tuple[int, ...]]] = []
    anchors = {
        ((tile_x + dx) % LOGICAL_SIZE, (tile_y + dy) % LOGICAL_SIZE)
        for tile_x, tile_y in occupancy
        for dx in (0, -1)
        for dy in (0, -1)
    }
    for anchor_x, anchor_y in sorted(anchors, key=lambda item: (item[1], item[0])):
            region = {
                (anchor_x, anchor_y),
                ((anchor_x + 1) % LOGICAL_SIZE, anchor_y),
                (anchor_x, (anchor_y + 1) % LOGICAL_SIZE),
                ((anchor_x + 1) % LOGICAL_SIZE, (anchor_y + 1) % LOGICAL_SIZE),
            }
            local_slots = sorted({slot for tile in region for slot in occupancy.get(tile, ())})
            # A fusion group has at most four non-overlapping footprints. Keep
            # candidate enumeration a local constant even under dense contact.
            local_slots = local_slots[:8]
            for size in range(2, min(4, len(local_slots)) + 1):
                for group in combinations(local_slots, size):
                    footprints = [destination_footprint(state.structure[slot], state.x[slot], state.y[slot]) for slot in group]
                    if any(not footprint or not footprint.issubset(region) for footprint in footprints):
                        continue
                    covered: set[tuple[int, int]] = set()
                    overlap = False
                    for footprint in footprints:
                        if covered.intersection(footprint):
                            overlap = True
                            break
                        covered.update(footprint)
                    if overlap:
                        continue
                    if covered != region:
                        continue
                    levels = {structure_level(state.structure[slot]) for slot in group}
                    if len(levels) != 1 or max(levels) >= 7:
                        continue
                    if any(state.bond_strength[slot] < config.fusion_bond_threshold for slot in group):
                        continue
                    if any(
                        relative_velocity(
                            state.direction[first], state.speed_code[first],
                            state.direction[second], state.speed_code[second],
                        ) > config.fusion_velocity_threshold
                        for first, second in combinations(group, 2)
                    ):
                        continue
                    candidates_by_anchor.append(((anchor_x, anchor_y), group))
    return candidates_by_anchor


def _fuse_groups(
    state: UniverseState,
    config: PhysicsConfig,
    occupancy: dict[tuple[int, int], list[int]],
) -> tuple[int, set[int]]:
    fused_slots: set[int] = set()
    fusion_count = 0
    for (anchor_x, anchor_y), group in _fusion_candidates(state, occupancy, config):
        if any(slot in fused_slots or state.lifecycle[slot] != Lifecycle.ACTIVE for slot in group):
            continue
        level = structure_level(state.structure[group[0]])
        result_slot = min(group)
        ordered = tuple(sorted(group, key=lambda slot: _cell_order_key(state, slot)))
        hp_values = {slot: state.hp[slot] for slot in group}
        best_slot = max(group, key=lambda slot: (hp_values[slot], _cell_order_key(state, slot)))
        best_direction = state.direction[best_slot]
        total_hp = min(0xFF, sum(hp_values.values()))
        total_trace = min(0xFF, sum(state.slow_trace[slot] for slot in group))
        latent = mix_fusion_latent(state.latent[slot] for slot in ordered)
        speed_code = min(state.speed_code[slot] for slot in group)
        result_structure = SHAPE_SINGLE << ((level + 1) * 2)

        for slot in group:
            if slot != result_slot:
                state.free(slot)
        state.lifecycle[result_slot] = int(Lifecycle.ACTIVE)
        state.x[result_slot] = anchor_x * 8
        state.y[result_slot] = anchor_y * 8
        state.structure[result_slot] = result_structure & 0xFFFF
        state.latent[result_slot] = latent
        state.hp[result_slot] = total_hp
        state.bond_strength[result_slot] = 0
        state.direction[result_slot] = best_direction
        state.speed_code[result_slot] = speed_code
        state.age[result_slot] = 0
        state.black_hole_timer[result_slot] = 0
        state.slow_trace[result_slot] = total_trace
        fused_slots.update(group)
        fusion_count += 1
    return fusion_count, fused_slots


def _fragment_active_cells(
    state: UniverseState,
    config: PhysicsConfig,
    active: list[int],
    generation: int,
    fused_slots: set[int],
) -> tuple[int, set[int]]:
    fragmentation_count = 0
    fragmented_core_slots: set[int] = set()
    for slot in active:
        if slot in fused_slots or state.lifecycle[slot] != Lifecycle.ACTIVE:
            continue
        rate = age_scaled_fragmentation_rate(
            config.fragmentation_rate,
            state.age[slot],
            aging_enabled=config.aging_enabled,
        )
        old_x = state.x[slot]
        old_y = state.y[slot]
        spatial_address = (tile_coordinate(old_y) << 5) | tile_coordinate(old_x)
        physical_local_index = ((old_x & 0xFF) << 8) | (old_y & 0xFF)
        chance_local_index = 0x10000 | physical_local_index
        if (
            event_u16(
                event_key(
                    state.seed,
                    generation,
                    spatial_address,
                    EVENT_FRAGMENTATION,
                    chance_local_index,
                )
            )
            >= rate
        ):
            continue
        structure = state.structure[slot]
        level = structure_level(structure)
        shape = structure_shape(structure)
        if level == 0:
            if shape in (SHAPE_HORIZONTAL, SHAPE_VERTICAL):
                state.structure[slot] = SHAPE_SINGLE
                state.bond_strength[slot] = 0
                fragmentation_count += 1
            elif shape == SHAPE_SINGLE:
                state.free(slot)
                fragmentation_count += 1
            continue

        old_latent = state.latent[slot]
        old_hp = state.hp[slot]
        old_age = state.age[slot]
        old_direction = state.direction[slot]
        old_speed = state.speed_code[slot]
        old_trace = state.slow_trace[slot]
        split_mask = fragmentation_split_mask(
            state.seed,
            generation,
            spatial_address,
            physical_local_index,
        )
        dx, dy = velocity_vector(old_direction, speed_code_for_magnitude(1))
        try:
            fragment = state.spawn(
                x=wrap_fixed(old_x - (dx * 8)),
                y=wrap_fixed(old_y - (dy * 8)),
                structure=SHAPE_SINGLE << ((level - 1) * 2),
                latent=old_latent & split_mask,
                hp=old_hp >> 1,
                direction=(old_direction + 4) % 8,
                speed_code=old_speed,
            )
        except RuntimeError:
            continue
        state.age[fragment] = 0
        state.bond_strength[fragment] = 0
        state.slow_trace[fragment] = old_trace // 2
        state.latent[slot] = old_latent & (~split_mask & 0xFFFF)
        state.hp[slot] = old_hp - (old_hp >> 1)
        state.age[slot] = old_age >> 1
        state.bond_strength[slot] = 0
        state.slow_trace[slot] = old_trace - state.slow_trace[fragment]
        fragmented_core_slots.add(slot)
        fragmentation_count += 1
    return fragmentation_count, fragmented_core_slots


def _slow_trace_inert(config: PhysicsConfig) -> bool:
    return (
        config.trace_write_cap == 0
        and config.trace_transfer_cap == 0
        and config.trace_discharge_cap == 0
        and config.trace_decay_rate == 0
        and config.trace_bonus_shift == 8
    )


def _apply_slow_trace_writes(
    state: UniverseState,
    config: PhysicsConfig,
    activity_amounts: Mapping[int, int],
) -> None:
    if config.trace_write_cap <= 0:
        return
    for slot, amount in activity_amounts.items():
        if state.lifecycle[slot] == Lifecycle.FREE or amount <= 0:
            continue
        write = min(int(amount), config.trace_write_cap)
        state.slow_trace[slot] = min(0xFF, state.slow_trace[slot] + write)


def _transfer_slow_trace(
    state: UniverseState,
    config: PhysicsConfig,
    selected_pairs: Iterable[tuple[int, int]],
) -> None:
    if config.trace_transfer_cap <= 0:
        return
    before = list(state.slow_trace)
    updates: dict[int, int] = {}
    for first, second in selected_pairs:
        if state.lifecycle[first] == Lifecycle.FREE or state.lifecycle[second] == Lifecycle.FREE:
            continue
        first_trace = before[first]
        second_trace = before[second]
        if first_trace > second_trace:
            quantity = min(config.trace_transfer_cap, (first_trace - second_trace) // 2)
            updates[first] = first_trace - quantity
            updates[second] = second_trace + quantity
        elif second_trace > first_trace:
            quantity = min(config.trace_transfer_cap, (second_trace - first_trace) // 2)
            updates[second] = second_trace - quantity
            updates[first] = first_trace + quantity
    for slot, value in updates.items():
        state.slow_trace[slot] = value


def _trace_physical_order_key(state: UniverseState, slot: int) -> tuple[Any, ...]:
    return (_cell_order_key(state, slot), slot)


def _discharge_slow_trace(
    state: UniverseState,
    config: PhysicsConfig,
) -> None:
    if config.trace_discharge_cap <= 0:
        return
    carriers = sorted(
        (
            slot
            for slot in range(state.max_cells)
            if state.lifecycle[slot] == Lifecycle.BLACK_HOLE and state.slow_trace[slot] > 0
        ),
        key=lambda slot: _trace_physical_order_key(state, slot),
    )
    for carrier in carriers:
        budget = min(config.trace_discharge_cap, state.slow_trace[carrier])
        if budget <= 0:
            continue
        footprint = destination_footprint(
            state.structure[carrier], state.x[carrier], state.y[carrier]
        )
        recipients = sorted(
            (
                slot
                for slot in state.active_slots()
                if destination_footprint(
                    state.structure[slot], state.x[slot], state.y[slot]
                ).intersection(footprint)
            ),
            key=lambda slot: _trace_physical_order_key(state, slot),
        )
        for recipient in recipients:
            if budget <= 0:
                break
            headroom = 0xFF - state.slow_trace[recipient]
            if headroom <= 0:
                continue
            quantity = min(budget, headroom)
            state.slow_trace[carrier] -= quantity
            state.slow_trace[recipient] += quantity
            budget -= quantity


def _decay_slow_trace(
    state: UniverseState,
    config: PhysicsConfig,
    generation: int,
    pending_free: set[int],
) -> None:
    if config.trace_decay_rate <= 0:
        return
    for slot in range(state.max_cells):
        if (
            slot in pending_free
            or state.lifecycle[slot] == Lifecycle.FREE
            or state.slow_trace[slot] <= 0
        ):
            continue
        x = state.x[slot] & 0xFF
        y = state.y[slot] & 0xFF
        spatial_address = (tile_coordinate(y) << 5) | tile_coordinate(x)
        local_index = (x << 8) | y
        key = event_key(
            state.seed,
            generation,
            spatial_address,
            EVENT_SLOW_TRACE_DECAY,
            local_index,
        )
        if event_u16(key) < config.trace_decay_rate:
            state.slow_trace[slot] -= 1


def _enter_black_hole(state: UniverseState, slot: int, config: PhysicsConfig) -> None:
    state.lifecycle[slot] = int(Lifecycle.BLACK_HOLE)
    state.black_hole_timer[slot] = config.black_hole_grace
    state.hp[slot] = 0


def _local_revival_slots(state: UniverseState) -> set[int]:
    """Permit a nearby active latent/bond signal to revive a black-hole slot."""
    active = state.active_slots()
    black_holes = [
        slot for slot, lifecycle in enumerate(state.lifecycle)
        if lifecycle == Lifecycle.BLACK_HOLE
    ]
    revived: set[int] = set()
    for black_hole in black_holes:
        black_hole_footprint = destination_footprint(
            state.structure[black_hole], state.x[black_hole], state.y[black_hole]
        )
        for participant in active:
            if not (state.latent[participant] or state.bond_strength[participant]):
                continue
            participant_footprint = destination_footprint(
                state.structure[participant], state.x[participant], state.y[participant]
            )
            if black_hole_footprint.intersection(participant_footprint):
                revived.add(black_hole)
                break
    return revived


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
    trace_start = state.slow_trace if _slow_trace_inert(resolved) else bytes(state.slow_trace)
    external_stimulated = set(int(slot) for slot in stimulus_slots)
    local_revival = _local_revival_slots(state)
    stimulated = external_stimulated | local_revival
    recovered_slots: set[int] = set()
    pending_free: set[int] = set()
    activity_amounts: dict[int, int] = {}

    for slot in range(state.max_cells):
        if state.lifecycle[slot] != Lifecycle.BLACK_HOLE:
            continue
        if slot in stimulated:
            state.lifecycle[slot] = int(Lifecycle.ACTIVE)
            state.hp[slot] = resolved.recovery_hp
            state.black_hole_timer[slot] = 0
            recovered_slots.add(slot)
            if slot in external_stimulated:
                activity_amounts[slot] = activity_amounts.get(slot, 0) + resolved.recovery_hp
        else:
            state.black_hole_timer[slot] -= 1
            if state.black_hole_timer[slot] <= 0:
                if _slow_trace_inert(resolved):
                    state.free(slot)
                else:
                    pending_free.add(slot)

    for slot in external_stimulated:
        if state.lifecycle[slot] == Lifecycle.ACTIVE and slot not in recovered_slots:
            activity_amounts[slot] = activity_amounts.get(slot, 0) + resolved.recovery_hp

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
                for slot in (first, second):
                    degraded = degrade_structure(state.structure[slot])
                    if degraded == 0:
                        state.free(slot)
                    else:
                        state.structure[slot] = degraded

    bond_contact_slots = {slot for pair in compatible_pairs for slot in pair}
    for slot in active:
        if state.lifecycle[slot] != Lifecycle.ACTIVE:
            continue
        if slot in bond_contact_slots:
            state.bond_strength[slot] = min(0xFF, state.bond_strength[slot] + resolved.bond_gain)
        else:
            state.bond_strength[slot] = max(0, state.bond_strength[slot] - resolved.bond_decay)

    latent_transmission_count, latent_activity_slots, selected_pairs = _transmit_latent(
        state,
        resolved,
        compatible_pairs,
        {pair: pair_addresses[pair] for pair in compatible_pairs},
        generation,
        trace_start,
    )
    for slot in latent_activity_slots:
        if slot in external_stimulated and slot not in recovered_slots:
            continue
        activity_amounts[slot] = activity_amounts.get(slot, 0) + resolved.recovery_hp

    _apply_slow_trace_writes(state, resolved, activity_amounts)
    _transfer_slow_trace(state, resolved, selected_pairs)

    if resolved.fusion_enabled:
        fusion_count, fused_slots = _fuse_groups(state, resolved, occupancy)
    else:
        fusion_count, fused_slots = 0, set()
    if resolved.fragmentation_enabled:
        fragmentation_count, fragmented_core_slots = _fragment_active_cells(
            state,
            resolved,
            active,
            generation,
            fused_slots,
        )
    else:
        fragmentation_count, fragmented_core_slots = 0, set()

    for slot in active:
        if state.lifecycle[slot] != Lifecycle.ACTIVE or slot in fused_slots:
            continue
        if slot in stimulated and slot not in recovered_slots:
            state.hp[slot] = min(0xFF, state.hp[slot] + resolved.recovery_hp)
        elif slot in latent_activity_slots:
            state.hp[slot] = min(0xFF, state.hp[slot] + resolved.recovery_hp)
        state.hp[slot] = max(0, state.hp[slot] - resolved.hp_decay)
        if slot not in fragmented_core_slots:
            state.age[slot] = min(0xFFFFFFFF, state.age[slot] + 1)
        if state.hp[slot] == 0:
            _enter_black_hole(state, slot, resolved)

    _discharge_slow_trace(state, resolved)
    _decay_slow_trace(state, resolved, generation, pending_free)
    for slot in sorted(pending_free):
        if state.lifecycle[slot] == Lifecycle.BLACK_HOLE:
            state.free(slot)

    state.generation += 1
    elapsed = max(time.perf_counter() - started, 1e-12)
    return StepMetrics(
        generation=state.generation,
        active_cells=len(state.active_slots()),
        collision_count=collision_count,
        collision_pair_evaluations=collision_count,
        bond_contact_count=len(compatible_pairs),
        latent_transmission_count=latent_transmission_count,
        fusion_count=fusion_count,
        fragmentation_count=fragmentation_count,
        noise_spawn_count=noise_spawn_count,
        generations_per_second=1.0 / elapsed,
    )
