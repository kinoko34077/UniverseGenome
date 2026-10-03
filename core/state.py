"""Authoritative state contracts established by the v0.1 specification.

This module intentionally defines no permanent cell identity. Storage slots
introduced in Phase 1 are reusable implementation positions, not semantic IDs.
"""

from enum import IntEnum

STRUCTURE_BITS = 16
LATENT_BITS = 16
HP_BITS = 8
DEFAULT_MAX_CELLS = 1024


class Lifecycle(IntEnum):
    FREE = 0
    ACTIVE = 1
    BLACK_HOLE = 2
