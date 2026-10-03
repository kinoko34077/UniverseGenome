"""Deterministic bounded steady-state replacement primitives."""

from __future__ import annotations

from dataclasses import dataclass

from .fitness import Fitness
from .genome import UNIVERSE_GENOME_FIELDS, UniverseGenome

IMPLEMENTATION_PHASE = 5


def seed_escalation(seed_count: int) -> int:
    value = int(seed_count)
    if value < 4:
        raise ValueError("seed_count must start at 4")
    return min(32, value * 2)


@dataclass(frozen=True)
class CandidateSlot:
    index: int
    category: str
    genome: UniverseGenome
    seed: int
    fitness: Fitness
    growth_windows: tuple[int, ...]


class SteadyStateOptimizer:
    def replace_free_slot(self, *, free_index: int, parent: CandidateSlot, direction: int = 1) -> CandidateSlot:
        if free_index < 0:
            raise ValueError("free_index must be non-negative")
        child_genome = parent.genome.mutate("hp_decay", direction=direction)
        return CandidateSlot(
            index=int(free_index),
            category=parent.category,
            genome=child_genome,
            seed=parent.seed + 1,
            fitness=Fitness(),
            growth_windows=(),
        )


def run_optimizer_headless() -> dict[str, object]:
    return {
        "genome_fields": list(UNIVERSE_GENOME_FIELDS),
        "seed_escalation": [seed_escalation(value) for value in (4, 8, 16, 32)],
        "cross_category_selection": False,
        "phase4_learning_claim": False,
    }
