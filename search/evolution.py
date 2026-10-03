"""Deterministic bounded steady-state replacement primitives."""

from __future__ import annotations

from dataclasses import dataclass, replace
import time
from typing import Any, Iterable, Mapping

from core.experiment import ExperimentConfig, LearningMeasurement, compare_baseline_trained
from core.physics import PhysicsConfig, create_universe
from .fitness import Fitness
from .genome import UNIVERSE_GENOME_FIELDS, UniverseGenome
from .pruning import growth_flags, prune_candidates, protected_indices

IMPLEMENTATION_PHASE = 5
CATEGORY_OPERATORS = ("masked_copy", "masked_xor", "rotate_copy", "masked_and")
SLOTS_PER_CATEGORY = 32
OPTIMIZER_POPULATION_SIZE = len(CATEGORY_OPERATORS) * SLOTS_PER_CATEGORY


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
    parent_index: int | None = None
    universe_snapshot: dict[str, Any] | None = None
    last_mutation_field: str | None = None

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("candidate index must be non-negative")
        if self.seed_count not in (4, 8, 16, 32):
            raise ValueError("candidate seed_count must be one of 4, 8, 16, 32")
        if self.parent_index is not None and self.parent_index < 0:
            raise ValueError("candidate parent_index must be non-negative")
        if any(not 0 <= int(window) <= 0xFF for window in self.growth_windows):
            raise ValueError("candidate growth windows must fit uint8")
        if self.last_mutation_field is not None and self.last_mutation_field not in UNIVERSE_GENOME_FIELDS:
            raise ValueError("candidate mutation field must be a genome field")
        if self.universe_snapshot is not None and not isinstance(self.universe_snapshot, dict):
            raise ValueError("candidate universe_snapshot must be an object")

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "category": self.category,
            "genome": self.genome.to_dict(),
            "seed": self.seed,
            "fitness": self.fitness.to_dict(),
            "growth_windows": list(self.growth_windows),
            "seed_count": self.seed_count,
            "parent_index": self.parent_index,
            "universe_snapshot": self.universe_snapshot,
            "last_mutation_field": self.last_mutation_field,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CandidateSlot":
        raw_windows = payload.get("growth_windows", ())
        if not isinstance(raw_windows, (list, tuple)):
            raise ValueError("candidate growth_windows must be an array")
        return cls(
            index=int(payload["index"]),
            category=str(payload["category"]),
            genome=UniverseGenome.from_dict(payload["genome"]),
            seed=int(payload["seed"]),
            fitness=Fitness.from_dict(payload.get("fitness", {})),
            growth_windows=tuple(int(window) for window in raw_windows),
            seed_count=int(payload.get("seed_count", 4)),
            parent_index=(None if payload.get("parent_index") is None else int(payload["parent_index"])),
            universe_snapshot=(
                None
                if payload.get("universe_snapshot") is None
                else dict(payload["universe_snapshot"])
            ),
            last_mutation_field=(
                None
                if payload.get("last_mutation_field") is None
                else str(payload["last_mutation_field"])
            ),
        )


class SteadyStateOptimizer:
    def __init__(
        self,
        candidates: Iterable[CandidateSlot] = (),
        *,
        base_config: PhysicsConfig | None = None,
        experiment: ExperimentConfig | None = None,
        generation: int = 0,
        scheduler: Mapping[str, Any] | None = None,
    ) -> None:
        if generation < 0:
            raise ValueError("optimizer generation must be non-negative")
        self.candidates = list(candidates)
        self.base_config = base_config or PhysicsConfig()
        self.experiment = experiment or ExperimentConfig()
        self.generation = int(generation)
        self.scheduler: dict[str, Any] = {
            "mutation_cursor": 0,
            "replacement_count": 0,
            "evaluation_count": 0,
            "replacement_seed_counts": [],
            "escalation_queue": [],
        }
        if scheduler is not None:
            for key, value in scheduler.items():
                if key in ("replacement_seed_counts", "escalation_queue"):
                    self.scheduler[key] = [int(item) for item in value]
                else:
                    self.scheduler[key] = int(value)

    @classmethod
    def from_defaults(
        cls,
        *,
        base_seed: int = 0,
        base_config: PhysicsConfig | None = None,
        experiment: ExperimentConfig | None = None,
    ) -> "SteadyStateOptimizer":
        base = base_config or PhysicsConfig()
        protocol = experiment or ExperimentConfig()
        slots: list[CandidateSlot] = []
        index = 0
        for category in CATEGORY_OPERATORS:
            for _genome_id in range(8):
                genome = UniverseGenome.default()
                for seed_offset in range(4):
                    seed = int(base_seed) + (_genome_id * 4) + seed_offset
                    slots.append(CandidateSlot(
                        index=index,
                        category=category,
                        genome=genome,
                        seed=seed,
                        fitness=Fitness(),
                        growth_windows=(),
                        universe_snapshot=cls._make_universe_snapshot(genome, category, seed, base),
                    ))
                    index += 1
        return cls(slots, base_config=base, experiment=protocol)

    @staticmethod
    def _effective_config(
        genome: UniverseGenome,
        category: str,
        base_config: PhysicsConfig,
    ) -> PhysicsConfig:
        values = genome.to_physics_config(base_config).to_dict()
        values["latent_operator"] = category
        return PhysicsConfig(**values)

    @classmethod
    def _make_universe_snapshot(
        cls,
        genome: UniverseGenome,
        category: str,
        seed: int,
        base_config: PhysicsConfig,
    ) -> dict[str, Any]:
        return create_universe(
            seed=seed,
            config=cls._effective_config(genome, category, base_config),
        ).to_snapshot()

    @staticmethod
    def _fitness_from_measurement(measurement: LearningMeasurement) -> Fitness:
        trained = tuple(item.trained for item in measurement.per_seed)
        return Fitness(
            success=measurement.trained_successes,
            wrong_outputs=sum(not result.success for result in trained),
            timeouts=sum(
                not result.autonomous_events and result.clone_generation > 0
                for result in trained
            ),
            response_latency=sum(result.clone_generation for result in trained),
            activity_cost=sum(len(result.autonomous_events) for result in trained),
            retention=measurement.trained_no_input_clean,
            noise_robustness=measurement.trained_alternate_input_clean,
        )

    def _evaluate_slot(self, slot: CandidateSlot) -> LearningMeasurement:
        seeds = range(slot.seed, slot.seed + slot.seed_count)
        return evaluate_candidate(
            genome=slot.genome,
            seeds=seeds,
            base_config=self.base_config,
            experiment=self.experiment,
            category=slot.category,
        )

    def _mutation_field(self, parent: CandidateSlot) -> str:
        cursor = int(self.scheduler["mutation_cursor"])
        category_offset = parent.index // SLOTS_PER_CATEGORY
        field = UNIVERSE_GENOME_FIELDS[(category_offset + cursor) % len(UNIVERSE_GENOME_FIELDS)]
        self.scheduler["mutation_cursor"] = cursor + 1
        return field

    def replace_free_slot(
        self,
        *,
        free_index: int,
        parent: CandidateSlot,
        direction: int = 1,
        field: str | None = None,
    ) -> CandidateSlot:
        if free_index < 0:
            raise ValueError("free_index must be non-negative")
        mutation_field = field or self._mutation_field(parent)
        child_genome = parent.genome.mutate(mutation_field, direction=direction)
        return CandidateSlot(
            index=int(free_index),
            category=parent.category,
            genome=child_genome,
            seed=parent.seed + 1,
            fitness=Fitness(),
            growth_windows=(),
            seed_count=seed_escalation(parent.seed_count),
            parent_index=parent.index,
            last_mutation_field=mutation_field,
        )

    def step(self) -> dict[str, Any]:
        if len(self.candidates) != OPTIMIZER_POPULATION_SIZE:
            raise ValueError(f"integrated optimizer requires {OPTIMIZER_POPULATION_SIZE} candidates")
        started = time.perf_counter()
        evaluated: list[CandidateSlot] = []
        measurements: dict[int, LearningMeasurement] = {}
        for slot in self.candidates:
            measurement = self._evaluate_slot(slot)
            measurements[slot.index] = measurement
            current_fitness = self._fitness_from_measurement(measurement)
            flags = growth_flags(slot.fitness, current_fitness)
            evaluated.append(CandidateSlot(
                index=slot.index,
                category=slot.category,
                genome=slot.genome,
                seed=slot.seed,
                fitness=current_fitness,
                growth_windows=(*slot.growth_windows, flags)[-4:],
                seed_count=slot.seed_count,
                parent_index=slot.parent_index,
                universe_snapshot=slot.universe_snapshot or self._make_universe_snapshot(
                    slot.genome, slot.category, slot.seed, self.base_config
                ),
                last_mutation_field=slot.last_mutation_field,
            ))
        self.candidates = evaluated
        queued_indices = set(self.scheduler["escalation_queue"])
        self.scheduler["escalation_queue"] = []
        replacements: list[dict[str, Any]] = []
        pruned_count = 0
        for category in CATEGORY_OPERATORS:
            local = [slot for slot in self.candidates if slot.category == category]
            protected = protected_indices(local)
            pruned = prune_candidates(local)
            pruned_count += len(pruned)
            queued = [slot for slot in local if slot.index in queued_indices]
            if pruned:
                target_index = max(
                    pruned,
                    key=lambda index: next(slot for slot in local if slot.index == index).fitness.sort_key(),
                )
                reason = "growth_pruned"
            elif queued:
                target = min(queued, key=lambda slot: slot.index)
                target_index = target.index
                reason = "seed_escalation"
            else:
                eligible = [slot for slot in local if slot.index not in protected]
                target = max(eligible, key=lambda slot: slot.fitness.sort_key())
                target_index = target.index
                reason = "steady_state_exploration"
            target = next(slot for slot in local if slot.index == target_index)
            if reason == "seed_escalation":
                parent = target
            else:
                parents = [slot for slot in local if slot.index != target.index]
                parent = min(parents, key=lambda slot: slot.fitness.sort_key())
            mutation_field = self._mutation_field(parent)
            child = self.replace_free_slot(
                free_index=target.index,
                parent=parent,
                direction=1,
                field=mutation_field,
            )
            child = replace(
                child,
                universe_snapshot=self._make_universe_snapshot(
                    child.genome, child.category, child.seed, self.base_config
                ),
            )
            self.candidates[target.index] = child
            replacements.append({
                "index": child.index,
                "category": child.category,
                "parent_index": child.parent_index,
                "mutation_field": child.last_mutation_field,
                "seed_count": child.seed_count,
                "reason": reason,
            })
            self.scheduler["replacement_seed_counts"].append(child.seed_count)
            if child.seed_count < 32:
                self.scheduler["escalation_queue"].append(child.index)
        self.generation += 1
        self.scheduler["replacement_count"] += len(replacements)
        self.scheduler["evaluation_count"] += len(measurements)
        elapsed = max(time.perf_counter() - started, 1e-12)
        return {
            "generation": self.generation,
            "evaluated_slots": len(measurements),
            "category_counts": {
                category: sum(slot.category == category for slot in self.candidates)
                for category in CATEGORY_OPERATORS
            },
            "cross_category_selection": False,
            "replacement_count": len(replacements),
            "pruned_count": pruned_count,
            "replacements": replacements,
            "generations_per_second": 1.0 / elapsed,
        }

    def run(self, iterations: int = 1) -> dict[str, Any]:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        summary: dict[str, Any] = {
            "generation": self.generation,
            "evaluated_slots": 0,
            "category_counts": {
                category: sum(slot.category == category for slot in self.candidates)
                for category in CATEGORY_OPERATORS
            },
            "cross_category_selection": False,
            "replacement_count": 0,
            "pruned_count": 0,
            "replacements": [],
            "generations_per_second": 0.0,
        }
        all_replacements: list[dict[str, Any]] = []
        total_evaluated = 0
        started = time.perf_counter()
        for _ in range(iterations):
            summary = self.step()
            total_evaluated += int(summary["evaluated_slots"])
            all_replacements.extend(summary["replacements"])
        if iterations:
            summary["evaluated_slots"] = total_evaluated
            summary["replacement_count"] = len(all_replacements)
            summary["replacements"] = all_replacements
            summary["generations_per_second"] = iterations / max(time.perf_counter() - started, 1e-12)
        return summary

    def to_snapshot(self) -> dict[str, Any]:
        if len(self.candidates) != OPTIMIZER_POPULATION_SIZE:
            raise ValueError(f"integrated optimizer requires {OPTIMIZER_POPULATION_SIZE} candidates")
        return {
            "format_version": 2,
            "kind": "UniverseGenomePhase5SteadyStateOptimizer",
            "generation": self.generation,
            "base_config": self.base_config.to_dict(),
            "experiment": self.experiment.to_dict(),
            "scheduler": dict(self.scheduler),
            "candidates": [slot.to_dict() for slot in self.candidates],
        }

    @classmethod
    def from_snapshot(cls, payload: Mapping[str, Any]) -> "SteadyStateOptimizer":
        if payload.get("format_version") != 2 or payload.get("kind") != "UniverseGenomePhase5SteadyStateOptimizer":
            raise ValueError("unsupported integrated Phase 5 optimizer snapshot")
        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, list) or len(raw_candidates) != OPTIMIZER_POPULATION_SIZE:
            raise ValueError("integrated optimizer snapshot must contain 128 candidates")
        candidates = [CandidateSlot.from_dict(record) for record in raw_candidates]
        if [slot.index for slot in candidates] != list(range(OPTIMIZER_POPULATION_SIZE)):
            raise ValueError("integrated optimizer candidate indices must be complete")
        if {slot.category for slot in candidates} != set(CATEGORY_OPERATORS):
            raise ValueError("integrated optimizer categories do not match Phase 5")
        if any(sum(slot.category == category for slot in candidates) != SLOTS_PER_CATEGORY
               for category in CATEGORY_OPERATORS):
            raise ValueError("integrated optimizer categories must contain 32 slots each")
        return cls(
            candidates,
            base_config=PhysicsConfig.from_mapping(payload["base_config"]),
            experiment=ExperimentConfig.from_mapping(payload["experiment"]),
            generation=int(payload["generation"]),
            scheduler=payload.get("scheduler", {}),
        )


def optimizer_snapshot(candidates: Iterable[CandidateSlot], *, generation: int = 0) -> dict[str, Any]:
    records = tuple(candidates)
    if generation < 0:
        raise ValueError("optimizer generation must be non-negative")
    if len({record.index for record in records}) != len(records):
        raise ValueError("optimizer candidate indices must be unique")
    return {
        "format_version": 1,
        "kind": "UniverseGenomePhase5Optimizer",
        "generation": int(generation),
        "candidates": [record.to_dict() for record in records],
    }


def restore_optimizer_snapshot(payload: Mapping[str, Any]) -> tuple[int, tuple[CandidateSlot, ...]]:
    if payload.get("format_version") != 1 or payload.get("kind") != "UniverseGenomePhase5Optimizer":
        raise ValueError("unsupported Phase 5 optimizer snapshot")
    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError("optimizer snapshot candidates must be an array")
    records = tuple(CandidateSlot.from_dict(record) for record in raw_candidates)
    if len({record.index for record in records}) != len(records):
        raise ValueError("optimizer snapshot candidate indices must be unique")
    return int(payload["generation"]), records


def evaluate_candidate(
    *,
    genome: UniverseGenome,
    seeds: Iterable[int],
    base_config: PhysicsConfig | None = None,
    experiment: ExperimentConfig | None = None,
    category: str | None = None,
) -> LearningMeasurement:
    """Evaluate a genome through the real Phase 4 baseline/trained collector."""
    effective = genome.to_physics_config(base_config)
    if category is not None:
        if category not in CATEGORY_OPERATORS:
            raise ValueError(f"unsupported optimizer category: {category}")
        values = effective.to_dict()
        values["latent_operator"] = category
        effective = PhysicsConfig(**values)
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
        "baseline_no_input_clean": measurement.baseline_no_input_clean,
        "trained_no_input_clean": measurement.trained_no_input_clean,
        "baseline_alternate_input_clean": measurement.baseline_alternate_input_clean,
        "trained_alternate_input_clean": measurement.trained_alternate_input_clean,
        "criterion": measurement.criterion,
        "learning_claim": measurement.learning_claim,
        "per_seed": [
            {
                "seed": item.seed,
                "baseline_success": item.baseline.success,
                "trained_success": item.trained.success,
                "baseline_no_input_clean": item.baseline_no_input.success,
                "trained_no_input_clean": item.trained_no_input.success,
                "baseline_alternate_input_clean": item.baseline_alternate.success,
                "trained_alternate_input_clean": item.trained_alternate.success,
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
    iterations: int = 1,
) -> dict[str, object]:
    if iterations < 0:
        raise ValueError("optimizer iterations must be non-negative")
    candidate = genome or UniverseGenome.default()
    seed_values = tuple(int(seed) for seed in seeds)
    measurement = evaluate_candidate(
        genome=candidate,
        seeds=seed_values,
        base_config=base_config,
        experiment=experiment,
    )
    optimizer = SteadyStateOptimizer.from_defaults(
        base_seed=seed_values[0] if seed_values else 0,
        base_config=base_config,
        experiment=experiment,
    )
    integrated_summary = optimizer.run(iterations=iterations)
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
        "population_size": len(optimizer.candidates),
        "category_counts": integrated_summary["category_counts"],
        "integrated_generation": integrated_summary["generation"],
        "optimizer_iterations": iterations,
        "evaluated_slots": integrated_summary["evaluated_slots"],
        "replacement_count": integrated_summary["replacement_count"],
        "integrated_seed_counts": list(optimizer.scheduler["replacement_seed_counts"]),
        "mutation_fields": sorted({
            item["mutation_field"]
            for item in integrated_summary["replacements"]
            if item["mutation_field"] is not None
        }),
        "genome_fields": list(UNIVERSE_GENOME_FIELDS),
        "seed_escalation": [seed_escalation(value) for value in (4, 8, 16, 32)],
        "cross_category_selection": False,
        "phase4_learning_claim": measurement.learning_claim,
        "candidate_genome": candidate.to_dict(),
        "candidate_measurement": _measurement_summary(measurement),
        "counterfactual_clean": {
            "no_input": measurement.no_input_clean,
            "alternate_input": measurement.alternate_input_clean,
        },
        "replacement_seed_counts": [item.seed_count for item in replacements],
        "replacement_categories": [item.category for item in replacements],
    }
