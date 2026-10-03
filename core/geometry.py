"""Geometry constants/helpers that do not implement Phase 1 movement."""

LOGICAL_SIZE = 32
SUBDIVISIONS_PER_TILE = 8
FIXED_POINT_SIZE = LOGICAL_SIZE * SUBDIVISIONS_PER_TILE


def wrap_fixed(value: int) -> int:
    """Wrap one internal fixed-point coordinate onto the 256-unit torus."""
    return value % FIXED_POINT_SIZE


def tile_coordinate(fixed_value: int) -> int:
    """Map an internal fixed-point coordinate to its logical tile."""
    return wrap_fixed(fixed_value) >> 3


def spatial_address(tile_x: int, tile_y: int) -> int:
    """Return the 0..1023 logical spatial address."""
    if not 0 <= tile_x < LOGICAL_SIZE or not 0 <= tile_y < LOGICAL_SIZE:
        raise ValueError("logical tile coordinate out of range")
    return (tile_y << 5) | tile_x
