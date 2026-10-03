"""Deterministic-randomness interface boundary.

Phase 0 defines the event-key contract but intentionally does not choose or
implement the Phase 1 hash/counter PRNG primitive.
"""

from typing import Tuple


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
