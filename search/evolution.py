"""Deterministic bounded steady-state replacement primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from core.experiment import ExperimentConfig, LearningMeasurement, compare_baseline_trained
from core.physics import PhysicsConfig
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
    seed_count: int = 4


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
            seed_count=seed_escalation(parent.seed_count),
        )


def evaluate_candidate(
    *,
    genome: UniverseGenome,
    seeds: Iterable[int],
    base_config: PhysicsConfig | None = None,
    experiment: ExperimentConfig | None = None,
) -> LearningMeasurement:
    """Evaluate a genome through the real Phase 4 baseline/trained collector."""
    effective = genome.to_physics_config(base_config)
    return compare_baseline_trained(
        seeds=seeds,
        config=effective,
        experiment=experiment,
    )


def _measurement_summary(measurement: LearningMeasurement) -> dict[str, Any]:
    return {
        "seed_count": measurement.seed_count,
        "baseline_successes": measurement.baseline_successes,
        "trained_successes": measurement.trained_successes,
        "criterion": measurement.criterion,
        "learning_claim": measurement.learning_claim,
        "per_seed": [
            {
                "seed": item.seed,
                "baseline_success": item.baseline.success,
                "trained_success": item.trained.success,
                "baseline_event_count": len(item.baseline.autonomous_events),
                "trained_event_count": len(item.trained.autonomous_events),
            }
            for item in measurement.per_seed
        ],
    }


def run_optimizer_headless(
    *,
    genome: UniverseGenome | None = None,
    seeds: Iterable[int] = (0, 1, 2, 3),
    base_config: PhysicsConfig | None = None,
    experiment: ExperimentConfig | None = None,
) -> dict[str, object]:
    candidate = genome or UniverseGenome.default()
    measurement = evaluate_candidate(
        genome=candidate,
        seeds=seeds,
        base_config=base_config,
        experiment=experiment,
    )
    optimizer = SteadyStateOptimizer()
    replacement = CandidateSlot(
        index=0,
        category="masked_copy",
        genome=candidate,
        seed=0,
        fitness=Fitness(),
        growth_windows=(),
    )
    replacements: list[CandidateSlot] = []
    for _ in range(4):
        replacement = optimizer.replace_free_slot(
            free_index=1,
            parent=replacement,
            direction=1,
        )
        replacements.append(replacement)
    return {
        "genome_fields": list(UNIVERSE_GENOME_FIELDS),
        "seed_escalation": [seed_escalation(value) for value in (4, 8, 16, 32)],
        "cross_category_selection": False,
        "phase4_learning_claim": measurement.learning_claim,
        "candidate_genome": candidate.to_dict(),
        "candidate_measurement": _measurement_summary(measurement),
        "replacement_seed_counts": [item.seed_count for item in replacements],
        "replacement_categories": [item.category for item in replacements],
    }
