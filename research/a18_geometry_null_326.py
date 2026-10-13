"""A1.8 #326: exact *hypothetical* uniform n-occupied-site 2x2 null.

This is NOT an observed universe probability, prospective experiment,
seed generator, inference of natural fusion, or learning outcome.
"""
from __future__ import annotations

from fractions import Fraction
from core.geometry import LOGICAL_SIZE


def expected_complete_2x2_blocks(occupied_unique_sites: int, *, side: int = LOGICAL_SIZE) -> Fraction:
    """Uniform n-subset of a periodic side*side torus, 2x2 anchored blocks.

    Each anchored block has 4 distinct tiles when side>=3.
    This exact expectation needs *uniform snapshot marginal occupancy*,
    but NOT independent timestamps for expected sums.
    """
    if type(side) is not int or side < 3:
        raise ValueError("side must be integer >=3 (distinct toroidal block sites)")
    n=occupied_unique_sites
    total=side*side
    if type(n) is not int or not 0<=n<=total:
        raise ValueError("occupied_unique_sites must be integer 0..side^2")
    if n<4:
        return Fraction(0,1)
    return Fraction(total * n * (n-1) * (n-2) * (n-3),
                    total * (total-1) * (total-2) * (total-3))


def expected_complete_2x2_counts_for_marginals(counts: tuple[int,...], *, side: int = LOGICAL_SIZE) -> Fraction:
    """Expected sum ONLY when every actual time marginal follows uniform n-subset.

    No temporal independence needed for this linear expected-count result.
    """
    return sum(
        (expected_complete_2x2_blocks(n,side=side) for n in counts),
        Fraction(0,1),
    )


def conservative_uniform_null_upper_bound(max_unique_sites: int, steps: int, *,side: int = LOGICAL_SIZE) -> Fraction:
    """Conditional bound under uniform, without-replacement per-step marginal.

    NOT a bound on actual deterministic physics or observed event likelihood.
    """
    if type(steps) is not int or steps<0:
        raise ValueError("steps must be nonnegative int")
    return expected_complete_2x2_blocks(max_unique_sites,side=side)*steps
