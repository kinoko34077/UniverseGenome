"""Counter-based deterministic event randomness for Phase 1."""

from typing import Tuple

MASK64 = (1 << 64) - 1


def event_key(
    universe_seed: int,
    generation: int,
    spatial_address: int,
    event_type: int,
    local_index: int,
) -> Tuple[int, int, int, int, int]:
    return (
        int(universe_seed),
        int(generation),
        int(spatial_address),
        int(event_type),
        int(local_index),
    )


def _mix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return (value ^ (value >> 31)) & MASK64


def event_value(key: Tuple[int, int, int, int, int]) -> int:
    """Return a stable uint64 derived only from the explicit event key."""
    value = 0xD1B54A32D192ED03
    for part in key:
        value = _mix64(value ^ (int(part) & MASK64))
    return value


def event_u16(key: Tuple[int, int, int, int, int]) -> int:
    return event_value(key) & 0xFFFF


def event_index(key: Tuple[int, int, int, int, int], upper_bound: int) -> int:
    if upper_bound <= 0:
        raise ValueError("upper_bound must be positive")
    return event_value(key) % upper_bound
