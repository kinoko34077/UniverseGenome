"""Declared later-phase latent operator families.

The names are specification metadata only; runtime propagation begins in Phase 2.
"""

LATENT_OPERATOR_CATEGORIES = (
    "masked_copy",
    "masked_xor",
    "rotate_masked_copy",
    "masked_and",
)

IMPLEMENTATION_PHASE = 2
