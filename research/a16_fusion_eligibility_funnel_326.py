"""#326 A1.6: non-mutating native fusion eligibility funnel (source-only).

Use this on a source-native *post movement/contact, pre-fusion* state and
occupancy, not on a pre-step snapshot as if it were the native fusion state.
No new seed, no phenotype scoring, no physics or decision mutation.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

from core.physics import (
    PhysicsConfig,
    _fusion_candidates,
    destination_footprint,
    relative_velocity,
)
from core.state import UniverseState, structure_level
from core.geometry import LOGICAL_SIZE


STAGES = (
    "enumerated_groups",
    "footprints_inside_region",
    "nonoverlap",
    "exact_cover",
    "same_level",
    "sufficient_bond",
    "compatible_velocity",
)


def native_fusion_eligibility_funnel(
    state: UniverseState,
    occupancy: dict[tuple[int, int], list[int]],
    config: PhysicsConfig,
) -> dict[str, Any]:
    """Observe native exact-cover eligibility without modifying a single cell.

    The candidate returned by the original native _fusion_candidates is the
    independent oracle. Every stage has an explicit denominator and ordering.
    A native candidate is still NOT necessarily fused if previous groups
    consume its cells or some cells are not ACTIVE at actual native fusion.
    """
    if state.config != config:
        raise ValueError("state/config identity must match native physics")
    snapshot = state.to_snapshot()
    counters: Counter[str] = Counter()
    locally_eligible = []
    anchors = {
        ((x + dx) % LOGICAL_SIZE, (y + dy) % LOGICAL_SIZE)
        for x, y in occupancy for dx in (0, -1) for dy in (0, -1)
    }
    for ax, ay in sorted(anchors, key=lambda point: (point[1], point[0])):
        region = {
            (ax, ay), ((ax + 1) % LOGICAL_SIZE, ay),
            (ax, (ay + 1) % LOGICAL_SIZE),
            ((ax + 1) % LOGICAL_SIZE, (ay + 1) % LOGICAL_SIZE),
        }
        slots = sorted({s for tile in region for s in occupancy.get(tile, ())})[:8]
        for size in range(2, min(4, len(slots)) + 1):
            for group in combinations(slots, size):
                counters["enumerated_groups"] += 1
                footprints = [
                    destination_footprint(
                        state.structure[s], state.x[s], state.y[s]
                    )
                    for s in group
                ]
                if any(not fp or not fp.issubset(region) for fp in footprints):
                    continue
                counters["footprints_inside_region"] += 1
                covered = set()
                overlap = False
                for fp in footprints:
                    if covered.intersection(fp):
                        overlap = True
                        break
                    covered.update(fp)
                if overlap:
                    continue
                counters["nonoverlap"] += 1
                if covered != region:
                    continue
                counters["exact_cover"] += 1
                levels = {structure_level(state.structure[s]) for s in group}
                if len(levels) != 1 or max(levels) >= 7:
                    continue
                counters["same_level"] += 1
                if any(
                    state.bond_strength[s] < config.fusion_bond_threshold
                    for s in group
                ):
                    continue
                counters["sufficient_bond"] += 1
                if any(
                    relative_velocity(
                        state.direction[a], state.speed_code[a],
                        state.direction[b], state.speed_code[b],
                    ) > config.fusion_velocity_threshold
                    for a, b in combinations(group, 2)
                ):
                    continue
                counters["compatible_velocity"] += 1
                locally_eligible.append(((ax, ay), group))

    native = _fusion_candidates(state, occupancy, config)
    if locally_eligible != native:
        raise ValueError("observer diverged from original native candidates")
    if state.to_snapshot() != snapshot:
        raise ValueError("fusion eligibility observer mutated physical state")
    result = {s: int(counters[s]) for s in STAGES}
    if not all(result[a] >= result[b] for a, b in zip(STAGES, STAGES[1:])):
        raise ValueError("eligibility funnel stage counts are not monotonic")
    return {
        "schema": "UG_A16_NATIVE_FUSION_GATE_FUNNEL_V1",
        "original_native_candidate_count": len(native),
        "fuse_flag_enabled": bool(config.fusion_enabled),
        "candidate_processing_enabled": bool(config.fusion_enabled),
        "gate_counts": result,
        "candidate_groups": [
            {"anchor":list(anchor), "size":len(group)}
            for anchor, group in native
        ],
        "is_natural_evolution_evidence": False,
        "learning_claim": False,
    }
