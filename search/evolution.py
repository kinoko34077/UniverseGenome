"""Deterministic bounded Phase 5 optimizer over authoritative Universe slots."""

from __future__ import annotations

from dataclasses import dataclass
import json
import statistics
import time
from typing import Any, Iterable, Mapping

from core.experiment import (
    ExperimentConfig,
    IOExperiment,
    LearningMeasurement,
    compare_baseline_trained,
    measure_trained_state,
)
from core.physics import PhysicsConfig, create_universe
from core.state import UniverseState
from .fitness import Fitness
from .genome import UNIVERSE_GENOME_FIELDS, UniverseGenome
from .pruning import growth_flags, prune_candidates, protected_indices

IMPLEMENTATION_PHASE = 5
CATEGORY_OPERATORS = ("masked_copy", "masked_xor", "rotate_copy", "masked_and")
SLOTS_PER_CATEGORY = 32
OPTIMIZER_POPULATION_SIZE = 128
GROWTH_WINDOW_GENERATIONS = 128
PROMISING_POLICIES = ("strict_fitness",)


def seed_escalation(seed_count: int) -> int:
    """Retain the historical pure escalation helper for callers and reports."""
    value = int(seed_count)
    if value < 4:
        raise ValueError("seed_count must start at 4")
    return min(32, value * 2)


def _genome_key(genome: UniverseGenome) -> str:
    return json.dumps(genome.to_dict(), sort_keys=True, separators=(",", ":"))


@dataclass
class UniverseSlot:
    """One occupied authoritative search slot and its persistent universe."""

    index: int
    category: str
    genome: UniverseGenome
    seed: int
    state: UniverseState
    fitness: Fitness = Fitness()
    growth_windows: tuple[int, ...] = ()
    growth_reference: Fitness | None = None
    parent_index: int | None = None
    last_mutation_field: str | None = None
    allocation_reason: str = "initial"

    def __post_init__(self) -> None:
        if not 0 <= self.index < OPTIMIZER_POPULATION_SIZE:
            raise ValueError("universe slot index must be within the fixed population")
        if self.category not in CATEGORY_OPERATORS:
            raise ValueError("unsupported universe slot category")
        if int(self.seed) != int(self.state.seed):
            raise ValueError("slot seed must match authoritative UniverseState seed")
        if self.parent_index is not None and self.parent_index < 0:
            raise ValueError("slot parent_index must be non-negative")
        if any(not 0 <= int(window) <= 0xFF for window in self.growth_windows):
            raise ValueError("slot growth windows must fit uint8")
        if self.growth_reference is not None and not isinstance(self.growth_reference, Fitness):
            raise ValueError("slot growth_reference must be Fitness")
        if self.last_mutation_field is not None and self.last_mutation_field not in UNIVERSE_GENOME_FIELDS:
            raise ValueError("slot mutation field must be a genome field")
        if self.allocation_reason not in ("initial", "seed_evidence", "mutation_child"):
            raise ValueError("unsupported slot allocation reason")

    @property
    def physical_generations(self) -> int:
        return int(self.state.generation)

    @property
    def genome_key(self) -> str:
        return _genome_key(self.genome)

    @property
    def evidence_group(self) -> tuple[str, str]:
        return self.category, self.genome_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "category": self.category,
            "genome": self.genome.to_dict(),
            "seed": self.seed,
            "state": self.state.to_snapshot(),
            "fitness": self.fitness.to_dict(),
            "growth_windows": list(self.growth_windows),
            "growth_reference": (
                None if self.growth_reference is None else self.growth_reference.to_dict()
            ),
            "parent_index": self.parent_index,
            "last_mutation_field": self.last_mutation_field,
            "allocation_reason": self.allocation_reason,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        base_config: PhysicsConfig,
    ) -> "UniverseSlot":
        raw_state = payload.get("state")
        if not isinstance(raw_state, Mapping):
            raise ValueError("authoritative slot state is required")
        raw_config = raw_state.get("config")
        state_config = (
            PhysicsConfig.from_mapping(raw_config)
            if isinstance(raw_config, Mapping)
            else base_config
        )
        state = UniverseState.from_snapshot(dict(raw_state), config=state_config)
        raw_windows = payload.get("growth_windows", ())
        if not isinstance(raw_windows, (list, tuple)):
            raise ValueError("slot growth_windows must be an array")
        return cls(
            index=int(payload["index"]),
            category=str(payload["category"]),
            genome=UniverseGenome.from_dict(dict(payload["genome"])),
            seed=int(payload["seed"]),
            state=state,
            fitness=Fitness.from_dict(dict(payload.get("fitness", {}))),
            growth_windows=tuple(int(window) for window in raw_windows),
            growth_reference=(
                None
                if payload.get("growth_reference") is None
                else Fitness.from_dict(dict(payload["growth_reference"]))
            ),
            parent_index=(
                None
                if payload.get("parent_index") is None
                else int(payload["parent_index"])
            ),
            last_mutation_field=(
                None
                if payload.get("last_mutation_field") is None
                else str(payload["last_mutation_field"])
            ),
            allocation_reason=str(payload.get("allocation_reason", "initial")),
        )


class SteadyStateOptimizer:
    """Steady-state optimizer whose slots are the authoritative universes."""

    def __init__(
        self,
        slots: Iterable[UniverseSlot] = (),
        *,
        base_config: PhysicsConfig | None = None,
        experiment: ExperimentConfig | None = None,
        generation: int = 0,
        scheduler: Mapping[str, Any] | None = None,
        promising_policy: str = "strict_fitness",
    ) -> None:
        if generation < 0:
            raise ValueError("optimizer generation must be non-negative")
        if promising_policy not in PROMISING_POLICIES:
            raise ValueError("unsupported promising policy")
        self.slots = list(slots)
        self.base_config = base_config or PhysicsConfig()
        self.experiment = experiment or ExperimentConfig()
        self.generation = int(generation)
        self.scheduler: dict[str, Any] = {
            "mutation_cursor": 0,
            "allocation_cursor": 0,
            "replacement_count": 0,
            "evaluation_count": 0,
            "promising_policy": promising_policy,
        }
        if scheduler is not None:
            for key, value in scheduler.items():
                if key == "promising_policy":
                    if value not in PROMISING_POLICIES:
                        raise ValueError("unsupported promising policy in scheduler")
                    self.scheduler[key] = str(value)
                else:
                    self.scheduler[key] = int(value)

    @property
    def candidates(self) -> list[UniverseSlot]:
        """Compatibility view; each item is still one real authoritative slot."""
        return self.slots

    @property
    def promising_policy(self) -> str:
        return str(self.scheduler["promising_policy"])

    @classmethod
    def from_defaults(
        cls,
        *,
        base_seed: int = 0,
        base_config: PhysicsConfig | None = None,
        experiment: ExperimentConfig | None = None,
        promising_policy: str = "strict_fitness",
    ) -> "SteadyStateOptimizer":
        base = base_config or PhysicsConfig()
        protocol = experiment or ExperimentConfig()
        slots: list[UniverseSlot] = []
        index = 0
        next_seed = int(base_seed)
        for category in CATEGORY_OPERATORS:
            for genome in UniverseGenome.initial_population():
                for _ in range(4):
                    config = cls._effective_config(genome, category, base)
                    state = create_universe(seed=next_seed, config=config)
                    slots.append(
                        UniverseSlot(
                            index=index,
                            category=category,
                            genome=genome,
                            seed=next_seed,
                            state=state,
                        )
                    )
                    index += 1
                    next_seed += 1
        return cls(
            slots,
            base_config=base,
            experiment=protocol,
            promising_policy=promising_policy,
            scheduler={"allocation_cursor": next_seed},
        )

    @staticmethod
    def _effective_config(
        genome: UniverseGenome,
        category: str,
        base_config: PhysicsConfig,
    ) -> PhysicsConfig:
        values = genome.to_physics_config(base_config).to_dict()
        values["latent_operator"] = category
        return PhysicsConfig(**values)

    @staticmethod
    def _fitness_from_measurement(measurement: LearningMeasurement) -> Fitness:
        trained = tuple(item.trained for item in measurement.per_seed)
        denominator = float(measurement.seed_count)
        return Fitness(
            success=measurement.trained_successes / denominator,
            wrong_outputs=sum(result.wrong_output_count for result in trained) / denominator,
            timeouts=sum(result.timed_out for result in trained) / denominator,
            response_latency=sum(result.response_latency for result in trained) / denominator,
            activity_cost=sum(result.activity_cost for result in trained) / denominator,
            retention=measurement.trained_no_input_clean / denominator,
            noise_robustness=measurement.trained_alternate_input_clean / denominator,
        )

    def _measure_slot(self, slot: UniverseSlot) -> tuple[LearningMeasurement, Fitness]:
        measurement = measure_trained_state(slot.state, experiment=self.experiment)
        return measurement, self._fitness_from_measurement(measurement)

    def _observe_growth_boundary(self, slot: UniverseSlot) -> None:
        measurement, observed_fitness = self._measure_slot(slot)
        if slot.growth_reference is not None:
            flags = growth_flags(slot.growth_reference, observed_fitness)
            slot.growth_windows = (*slot.growth_windows, flags)[-4:]
        slot.growth_reference = observed_fitness
        slot.fitness = observed_fitness
        del measurement

    def _evaluate_slot(self, slot: UniverseSlot) -> LearningMeasurement:
        if slot.growth_reference is None:
            _, slot.fitness = self._measure_slot(slot)

        def on_generation(generation: int) -> None:
            if generation > 0 and generation % GROWTH_WINDOW_GENERATIONS == 0:
                self._observe_growth_boundary(slot)

        trainer = IOExperiment(slot.state, experiment=self.experiment)
        trainer.train_a_to_b_null(on_generation=on_generation)
        measurement, slot.fitness = self._measure_slot(slot)
        return measurement

    def _mutation_field(self, parent: UniverseSlot) -> str:
        cursor = int(self.scheduler["mutation_cursor"])
        category_offset = parent.index // SLOTS_PER_CATEGORY
        field = UNIVERSE_GENOME_FIELDS[
            (category_offset + cursor) % len(UNIVERSE_GENOME_FIELDS)
        ]
        self.scheduler["mutation_cursor"] = cursor + 1
        return field

    def _next_seed(self) -> int:
        occupied = {slot.seed for slot in self.slots}
        candidate = int(self.scheduler["allocation_cursor"])
        while candidate in occupied:
            candidate += 1
        self.scheduler["allocation_cursor"] = candidate + 1
        return candidate

    def allocate_seed_slot(
        self,
        *,
        free_index: int,
        parent: UniverseSlot,
    ) -> UniverseSlot:
        if not 0 <= free_index < OPTIMIZER_POPULATION_SIZE:
            raise ValueError("free_index must be within the fixed population")
        if parent.index == free_index:
            raise ValueError("seed evidence must use a free slot distinct from parent")
        seed = self._next_seed()
        config = self._effective_config(parent.genome, parent.category, self.base_config)
        state = create_universe(seed=seed, config=config)
        return UniverseSlot(
            index=free_index,
            category=parent.category,
            genome=parent.genome,
            seed=seed,
            state=state,
            parent_index=parent.index,
            allocation_reason="seed_evidence",
        )

    def replace_free_slot(
        self,
        *,
        free_index: int,
        parent: UniverseSlot,
        direction: int = 1,
        field: str | None = None,
    ) -> UniverseSlot:
        if not 0 <= free_index < OPTIMIZER_POPULATION_SIZE:
            raise ValueError("free_index must be within the fixed population")
        if parent.index == free_index:
            raise ValueError("mutation child must use a free slot distinct from parent")
        mutation_field = field or self._mutation_field(parent)
        child_genome = parent.genome.mutate(mutation_field, direction=direction)
        seed = self._next_seed()
        config = self._effective_config(child_genome, parent.category, self.base_config)
        state = create_universe(seed=seed, config=config)
        return UniverseSlot(
            index=free_index,
            category=parent.category,
            genome=child_genome,
            seed=seed,
            state=state,
            parent_index=parent.index,
            last_mutation_field=mutation_field,
            allocation_reason="mutation_child",
        )

    def _is_promising(self, slot: UniverseSlot, local: list[UniverseSlot]) -> bool:
        if self.promising_policy != "strict_fitness":
            raise ValueError("unsupported promising policy")
        median_key = statistics.median_low(
            [candidate.fitness.sort_key() for candidate in local]
        )
        return slot.fitness.sort_key() < median_key

    def group_counts(self) -> dict[str, int]:
        counts: dict[tuple[str, str], int] = {}
        for slot in self.slots:
            counts[slot.evidence_group] = counts.get(slot.evidence_group, 0) + 1
        return {
            f"{category}:{genome}": count
            for (category, genome), count in sorted(counts.items())
        }

    def _category_counts(self) -> dict[str, int]:
        return {
            category: sum(slot.category == category for slot in self.slots)
            for category in CATEGORY_OPERATORS
        }

    def step(self) -> dict[str, Any]:
        if len(self.slots) != OPTIMIZER_POPULATION_SIZE:
            raise ValueError(
                f"integrated optimizer requires {OPTIMIZER_POPULATION_SIZE} authoritative slots"
            )
        started = time.perf_counter()
        measurements: dict[int, LearningMeasurement] = {}
        for slot in self.slots:
            measurements[slot.index] = self._evaluate_slot(slot)

        replacements: list[dict[str, Any]] = []
        pruned_count = 0
        for category in CATEGORY_OPERATORS:
            local = [slot for slot in self.slots if slot.category == category]
            protected = protected_indices(local)
            pruned = prune_candidates(local)
            pruned_count += len(pruned)
            if pruned:
                target_index = max(
                    pruned,
                    key=lambda index: next(
                        item for item in local if item.index == index
                    ).fitness.sort_key(),
                )
                reason = "growth_pruned"
            else:
                target = max(
                    (slot for slot in local if slot.index not in protected),
                    key=lambda slot: slot.fitness.sort_key(),
                )
                target_index = target.index
                reason = "steady_state_exploration"

            target = next(slot for slot in local if slot.index == target_index)
            sources = [slot for slot in local if slot.index != target_index]
            promising = [slot for slot in sources if self._is_promising(slot, local)]
            if promising:
                parent = min(promising, key=lambda slot: slot.fitness.sort_key())
                child = self.allocate_seed_slot(free_index=target.index, parent=parent)
                reason = "seed_evidence"
            else:
                parent = min(sources, key=lambda slot: slot.fitness.sort_key())
                child = self.replace_free_slot(
                    free_index=target.index,
                    parent=parent,
                    direction=1,
                )
            self.slots[target.index] = child
            replacements.append(
                {
                    "index": child.index,
                    "category": child.category,
                    "parent_index": child.parent_index,
                    "mutation_field": child.last_mutation_field,
                    "allocation_reason": child.allocation_reason,
                    "seed": child.seed,
                    "group_count": self.group_counts()[
                        f"{child.category}:{child.genome_key}"
                    ],
                    "reason": reason,
                }
            )

        self.generation += 1
        self.scheduler["replacement_count"] += len(replacements)
        self.scheduler["evaluation_count"] += len(measurements)
        elapsed = max(time.perf_counter() - started, 1e-12)
        return {
            "generation": self.generation,
            "evaluated_slots": len(measurements),
            "category_counts": self._category_counts(),
            "group_counts": self.group_counts(),
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
            "category_counts": self._category_counts(),
            "group_counts": self.group_counts(),
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
            summary["generations_per_second"] = iterations / max(
                time.perf_counter() - started, 1e-12
            )
        return summary

    def to_snapshot(self) -> dict[str, Any]:
        if len(self.slots) != OPTIMIZER_POPULATION_SIZE:
            raise ValueError(
                f"integrated optimizer requires {OPTIMIZER_POPULATION_SIZE} authoritative slots"
            )
        return {
            "format_version": 4,
            "kind": "UniverseGenomePhase5SteadyStateOptimizer",
            "generation": self.generation,
            "base_config": self.base_config.to_dict(),
            "experiment": self.experiment.to_dict(),
            "scheduler": dict(self.scheduler),
            "slots": [slot.to_dict() for slot in self.slots],
        }

    @classmethod
    def from_snapshot(cls, payload: Mapping[str, Any]) -> "SteadyStateOptimizer":
        if (
            payload.get("format_version") != 4
            or payload.get("kind") != "UniverseGenomePhase5SteadyStateOptimizer"
        ):
            raise ValueError("unsupported authoritative Phase 5 optimizer snapshot")
        raw_slots = payload.get("slots")
        if not isinstance(raw_slots, list) or len(raw_slots) != OPTIMIZER_POPULATION_SIZE:
            raise ValueError("authoritative optimizer snapshot must contain 128 slots")
        base_config = PhysicsConfig.from_mapping(payload["base_config"])
        slots = [
            UniverseSlot.from_dict(record, base_config=base_config)
            for record in raw_slots
        ]
        if [slot.index for slot in slots] != list(range(OPTIMIZER_POPULATION_SIZE)):
            raise ValueError("authoritative slot indices must be complete")
        if any(
            sum(slot.category == category for slot in slots) != SLOTS_PER_CATEGORY
            for category in CATEGORY_OPERATORS
        ):
            raise ValueError("authoritative categories must contain 32 slots each")
        scheduler = payload.get("scheduler", {})
        promising_policy = (
            str(scheduler.get("promising_policy", "strict_fitness"))
            if isinstance(scheduler, Mapping)
            else "strict_fitness"
        )
        return cls(
            slots,
            base_config=base_config,
            experiment=ExperimentConfig.from_mapping(payload["experiment"]),
            generation=int(payload["generation"]),
            scheduler=scheduler if isinstance(scheduler, Mapping) else {},
            promising_policy=promising_policy,
        )


def evaluate_candidate(
    *,
    genome: UniverseGenome,
    seeds: Iterable[int],
    base_config: PhysicsConfig | None = None,
    experiment: ExperimentConfig | None = None,
    category: str | None = None,
) -> LearningMeasurement:
    """Evaluate a disposable candidate without touching authoritative slots."""
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
                "wrong_output_count": item.trained.wrong_output_count,
                "timed_out": item.trained.timed_out,
                "response_latency": item.trained.response_latency,
                "activity_cost": item.trained.activity_cost,
                "evaluation_generations": item.trained.evaluation_generations,
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
    return {
        "population_size": len(optimizer.slots),
        "authoritative_slot_count": len(optimizer.slots),
        "category_counts": integrated_summary["category_counts"],
        "integrated_generation": integrated_summary["generation"],
        "optimizer_iterations": iterations,
        "evaluated_slots": integrated_summary["evaluated_slots"],
        "replacement_count": integrated_summary["replacement_count"],
        "mutation_fields": sorted(
            {
                item["mutation_field"]
                for item in integrated_summary["replacements"]
                if item["mutation_field"] is not None
            }
        ),
        "genome_fields": list(UNIVERSE_GENOME_FIELDS),
        "cross_category_selection": False,
        "group_counts": integrated_summary["group_counts"],
        "phase4_learning_claim": measurement.learning_claim,
        "candidate_genome": candidate.to_dict(),
        "candidate_measurement": _measurement_summary(measurement),
        "counterfactual_clean": {
            "no_input": measurement.no_input_clean,
            "alternate_input": measurement.alternate_input_clean,
        },
        "replacements": integrated_summary["replacements"],
    }
