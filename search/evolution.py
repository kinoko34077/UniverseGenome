"""Deterministic bounded Phase 5 optimizer over authoritative Universe slots."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Iterable, Mapping

from core.experiment import (
    ExperimentConfig,
    IOExperiment,
    LearningMeasurement,
    compare_baseline_trained,
    measure_trained_state,
)
from core.physics import PhysicsConfig, StepMetrics, create_universe
from core.state import UniverseState
from .fitness import Fitness
from .genome import UNIVERSE_GENOME_FIELDS, UniverseGenome
from .outer_search import (
    LEGACY_LATENT_OPERATORS,
    EvidenceSeedAssignment,
    ResolvedComparisonStratum,
    allocate_matched_evidence_seed,
    build_default_search_registry,
    evidence_tier_target,
    legacy_candidate_values,
    legacy_comparison_strata,
    legacy_mutation_directions,
    legacy_mutation_plan_for_base_config,
    legacy_search_plan,
    mutate_legacy_candidate,
)
from .pruning import (
    RESPONSE_HISTORY_LIMIT,
    SHORT_HEALTH_HISTORY_LIMIT,
    SHORT_WINDOW,
    absolute_failure_reason,
    growth_flags,
    prune_candidates,
    short_health_flags,
)

IMPLEMENTATION_PHASE = 5
CATEGORY_OPERATORS = LEGACY_LATENT_OPERATORS
SLOTS_PER_CATEGORY = 32
OPTIMIZER_POPULATION_SIZE = 128
GROWTH_WINDOW_GENERATIONS = 128
MINIMUM_EVIDENCE_SEEDS = 4
PROMISING_POLICY_TIERED_CATEGORY_RANK = "tiered_category_rank"


def seed_escalation(seed_count: int) -> int:
    """Retain the historical pure escalation helper for callers and reports."""
    return evidence_tier_target(PROMISING_POLICY_TIERED_CATEGORY_RANK, seed_count)


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
    parent_genome_key: str | None = None
    last_mutation_field: str | None = None
    allocation_reason: str = "initial"
    evidence_mature: bool = False
    short_health_windows: tuple[int, ...] = ()
    short_health_activity_cost: int = 0
    response_windows: tuple[int, ...] = ()
    absolute_failure: bool = False
    absolute_failure_reason: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.index < OPTIMIZER_POPULATION_SIZE:
            raise ValueError("universe slot index must be within the fixed population")
        if self.category not in CATEGORY_OPERATORS:
            raise ValueError("unsupported universe slot category")
        if int(self.seed) != int(self.state.seed):
            raise ValueError("slot seed must match authoritative UniverseState seed")
        if self.parent_index is not None and self.parent_index < 0:
            raise ValueError("slot parent_index must be non-negative")
        if self.parent_genome_key is not None and not self.parent_genome_key:
            raise ValueError("slot parent_genome_key must be non-empty when present")
        if any(not 0 <= int(window) <= 0xFF for window in self.growth_windows):
            raise ValueError("slot growth windows must fit uint8")
        if any(not 0 <= int(window) <= 0b11 for window in self.short_health_windows):
            raise ValueError("slot short-health windows must fit two bits")
        if self.short_health_activity_cost < 0:
            raise ValueError("slot short-health activity cost must be non-negative")
        if any(int(window) not in (0, 1) for window in self.response_windows):
            raise ValueError("slot response windows must be binary")
        if len(self.response_windows) > RESPONSE_HISTORY_LIMIT:
            raise ValueError("slot response history exceeds the 512-generation horizon")
        if self.growth_reference is not None and not isinstance(self.growth_reference, Fitness):
            raise ValueError("slot growth_reference must be Fitness")
        if self.last_mutation_field is not None and self.last_mutation_field not in UNIVERSE_GENOME_FIELDS:
            raise ValueError("slot mutation field must be a genome field")
        if self.allocation_reason not in ("initial", "seed_evidence", "mutation_child"):
            raise ValueError("unsupported slot allocation reason")
        if not isinstance(self.evidence_mature, bool):
            raise ValueError("slot evidence_mature must be bool")
        if not isinstance(self.absolute_failure, bool):
            raise ValueError("slot absolute_failure must be bool")
        if self.absolute_failure_reason not in (
            None,
            "all_active_cells_gone",
            "persistent_non_response",
        ):
            raise ValueError("unsupported slot absolute failure reason")
        if self.absolute_failure_reason is not None and not self.absolute_failure:
            raise ValueError("absolute failure reason requires absolute_failure")

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
            "parent_genome_key": self.parent_genome_key,
            "last_mutation_field": self.last_mutation_field,
            "allocation_reason": self.allocation_reason,
            "evidence_mature": self.evidence_mature,
            "short_health_windows": list(self.short_health_windows),
            "short_health_activity_cost": self.short_health_activity_cost,
            "response_windows": list(self.response_windows),
            "absolute_failure": self.absolute_failure,
            "absolute_failure_reason": self.absolute_failure_reason,
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
        category = str(payload["category"])
        genome = UniverseGenome.from_dict(dict(payload["genome"]))
        expected_values = genome.to_physics_config(base_config).to_dict()
        expected_values["latent_operator"] = category
        expected_config = PhysicsConfig(**expected_values)
        if state_config.to_dict() != expected_config.to_dict():
            raise ValueError("slot metadata does not match authoritative state config")
        state = UniverseState.from_snapshot(dict(raw_state), config=state_config)
        raw_windows = payload.get("growth_windows", ())
        if not isinstance(raw_windows, (list, tuple)):
            raise ValueError("slot growth_windows must be an array")
        raw_health_windows = payload.get("short_health_windows", ())
        if not isinstance(raw_health_windows, (list, tuple)):
            raise ValueError("slot short_health_windows must be an array")
        raw_response_windows = payload.get("response_windows", ())
        if not isinstance(raw_response_windows, (list, tuple)):
            raise ValueError("slot response_windows must be an array")
        absolute_failure = bool(payload.get("absolute_failure", False))
        absolute_failure_reason_value = payload.get("absolute_failure_reason")
        if absolute_failure_reason_value is not None:
            absolute_failure_reason_value = str(absolute_failure_reason_value)
        return cls(
            index=int(payload["index"]),
            category=category,
            genome=genome,
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
            parent_genome_key=(
                None
                if payload.get("parent_genome_key") is None
                else str(payload["parent_genome_key"])
            ),
            last_mutation_field=(
                None
                if payload.get("last_mutation_field") is None
                else str(payload["last_mutation_field"])
            ),
            allocation_reason=str(payload.get("allocation_reason", "initial")),
            evidence_mature=bool(payload["evidence_mature"]),
            short_health_windows=tuple(int(window) for window in raw_health_windows),
            short_health_activity_cost=int(payload.get("short_health_activity_cost", 0)),
            response_windows=tuple(int(window) for window in raw_response_windows),
            absolute_failure=absolute_failure,
            absolute_failure_reason=absolute_failure_reason_value,
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
        promising_policy: str | None = PROMISING_POLICY_TIERED_CATEGORY_RANK,
        prune_history: Iterable[Mapping[str, Any]] = (),
    ) -> None:
        if generation < 0:
            raise ValueError("optimizer generation must be non-negative")
        if promising_policy not in (None, PROMISING_POLICY_TIERED_CATEGORY_RANK):
            raise ValueError(f"unsupported promising allocation policy: {promising_policy}")
        self.slots = list(slots)
        self.base_config = base_config or PhysicsConfig()
        self.experiment = experiment or ExperimentConfig()
        self.generation = int(generation)
        self.prune_history: list[dict[str, Any]] = []
        for raw_event in prune_history:
            if not isinstance(raw_event, Mapping):
                raise ValueError("prune history entries must be objects")
            event = {
                "optimizer_generation": int(raw_event["optimizer_generation"]),
                "index": int(raw_event["index"]),
                "category": str(raw_event["category"]),
                "genome_key": str(raw_event["genome_key"]),
                "seed": int(raw_event["seed"]),
                "retirement_reason": str(raw_event["retirement_reason"]),
            }
            if event["optimizer_generation"] < 1:
                raise ValueError("prune history generation must be positive")
            if not 0 <= event["index"] < OPTIMIZER_POPULATION_SIZE:
                raise ValueError("prune history index must be within the fixed population")
            if event["category"] not in CATEGORY_OPERATORS:
                raise ValueError("prune history category is unsupported")
            if not event["genome_key"] or not event["retirement_reason"]:
                raise ValueError("prune history genome/reason must be non-empty")
            self.prune_history.append(event)
        self.scheduler: dict[str, Any] = {
            "mutation_cursor": 0,
            "allocation_cursor": 0,
            "replacement_count": 0,
            "evaluation_count": 0,
            "promising_policy": promising_policy,
        }
        for stratum in legacy_comparison_strata():
            category = str(stratum.primary_value)
            self.scheduler[f"allocation_mode_cursor:{category}"] = 0
        if scheduler is not None:
            for key, value in scheduler.items():
                if key == "promising_policy":
                    if value not in (None, PROMISING_POLICY_TIERED_CATEGORY_RANK):
                        raise ValueError(
                            f"unsupported promising allocation policy: {value}"
                        )
                    self.scheduler[key] = value
                else:
                    self.scheduler[key] = int(value)

    @property
    def candidates(self) -> list[UniverseSlot]:
        """Compatibility view; each item is still one real authoritative slot."""
        return self.slots

    @property
    def promising_policy(self) -> str | None:
        return self.scheduler["promising_policy"]

    @classmethod
    def from_defaults(
        cls,
        *,
        base_seed: int = 0,
        base_config: PhysicsConfig | None = None,
        experiment: ExperimentConfig | None = None,
        promising_policy: str | None = PROMISING_POLICY_TIERED_CATEGORY_RANK,
    ) -> "SteadyStateOptimizer":
        base = base_config or PhysicsConfig()
        protocol = experiment or ExperimentConfig()
        slots: list[UniverseSlot] = []
        index = 0
        for stratum in legacy_comparison_strata():
            category = str(stratum.primary_value)
            for genome_id, genome in enumerate(UniverseGenome.initial_population()):
                for seed_offset in range(4):
                    seed = int(base_seed) + (genome_id * 4) + seed_offset
                    config = cls._effective_config(genome, category, base)
                    state = create_universe(seed=seed, config=config)
                    slots.append(
                        UniverseSlot(
                            index=index,
                            category=category,
                            genome=genome,
                            seed=seed,
                            state=state,
                            evidence_mature=True,
                        )
                    )
                    index += 1
        return cls(
            slots,
            base_config=base,
            experiment=protocol,
            promising_policy=promising_policy,
            scheduler={"allocation_cursor": int(base_seed) + 32},
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
    def _trained_mapping_evaluations(
        measurement: LearningMeasurement,
    ) -> tuple[EvaluationResult, ...]:
        results: list[EvaluationResult] = []
        for item in measurement.per_seed:
            mapping_results = tuple(getattr(item, "mapping_results", ()))
            if mapping_results:
                results.extend(mapping.trained for mapping in mapping_results)
            else:
                results.append(item.trained)
        return tuple(results)

    @staticmethod
    def _fitness_from_measurement(measurement: LearningMeasurement) -> Fitness:
        trained = SteadyStateOptimizer._trained_mapping_evaluations(measurement)
        evaluation_denominator = float(len(trained))
        seed_denominator = float(measurement.seed_count)
        return Fitness(
            success=measurement.trained_successes / evaluation_denominator,
            wrong_outputs=sum(result.wrong_output_count for result in trained) / evaluation_denominator,
            timeouts=sum(result.timed_out for result in trained) / evaluation_denominator,
            response_latency=sum(result.response_latency for result in trained) / evaluation_denominator,
            activity_cost=sum(result.activity_cost for result in trained) / evaluation_denominator,
            retention=(
                getattr(measurement, "retention_rate", None)
                if getattr(measurement, "retention_rate", None) is not None
                else 0.0
            ),
            counterfactual_no_input_clean=measurement.trained_no_input_clean / seed_denominator,
            counterfactual_alternate_input_clean=(
                measurement.trained_alternate_input_clean / seed_denominator
            ),
            retention_evidence_count=float(
                getattr(measurement, "retention_eligible_count", 0)
            ),
            noise_robustness=(
                getattr(measurement, "noise_robustness_rate", None)
                if getattr(measurement, "noise_robustness_rate", None) is not None
                else 0.0
            ),
            noise_robustness_evidence_count=float(
                getattr(measurement, "noise_robustness_eligible_count", 0)
            ),
        )

    def _measure_slot(self, slot: UniverseSlot) -> tuple[LearningMeasurement, Fitness]:
        measurement = measure_trained_state(slot.state, experiment=self.experiment)
        return measurement, self._fitness_from_measurement(measurement)

    def _observe_short_health(
        self,
        slot: UniverseSlot,
        metrics: StepMetrics,
        *,
        activity_cost: int | None = None,
    ) -> None:
        flags = short_health_flags(
            active_cells=metrics.active_cells,
            activity_cost=metrics.activity_cost if activity_cost is None else activity_cost,
        )
        slot.short_health_windows = (
            *slot.short_health_windows,
            flags,
        )[-SHORT_HEALTH_HISTORY_LIMIT:]
        reason = absolute_failure_reason(
            slot.short_health_windows,
            response_history=slot.response_windows,
        )
        if not slot.absolute_failure and reason is not None:
            slot.absolute_failure = True
            slot.absolute_failure_reason = reason

    def _record_short_health_step(
        self,
        slot: UniverseSlot,
        generation: int,
        metrics: StepMetrics,
    ) -> None:
        """Accumulate one physical step and close an aligned short window."""
        slot.short_health_activity_cost += metrics.activity_cost
        if generation > 0 and generation % SHORT_WINDOW == 0:
            self._observe_short_health(
                slot,
                metrics,
                activity_cost=slot.short_health_activity_cost,
            )
            slot.short_health_activity_cost = 0

    @staticmethod
    def _measurement_has_autonomous_response(
        measurement: LearningMeasurement,
    ) -> bool:
        return any(
            bool(result.autonomous_events)
            for result in SteadyStateOptimizer._trained_mapping_evaluations(measurement)
        )

    def _record_response_observation(
        self,
        slot: UniverseSlot,
        *,
        responded: bool,
    ) -> None:
        slot.response_windows = (
            *slot.response_windows,
            1 if responded else 0,
        )[-RESPONSE_HISTORY_LIMIT:]
        reason = absolute_failure_reason(
            slot.short_health_windows,
            response_history=slot.response_windows,
        )
        if not slot.absolute_failure and reason is not None:
            slot.absolute_failure = True
            slot.absolute_failure_reason = reason

    def _observe_growth_boundary(self, slot: UniverseSlot) -> None:
        measurement, observed_fitness = self._measure_slot(slot)
        if slot.growth_reference is not None:
            flags = growth_flags(slot.growth_reference, observed_fitness)
            slot.growth_windows = (*slot.growth_windows, flags)[-4:]
        self._record_response_observation(
            slot,
            responded=self._measurement_has_autonomous_response(measurement),
        )
        slot.growth_reference = observed_fitness
        slot.fitness = observed_fitness

    def _evaluate_slot(self, slot: UniverseSlot) -> LearningMeasurement:
        if slot.growth_reference is None:
            _, slot.fitness = self._measure_slot(slot)
            slot.growth_reference = slot.fitness

        def on_generation(generation: int) -> None:
            if generation > 0 and generation % GROWTH_WINDOW_GENERATIONS == 0:
                self._observe_growth_boundary(slot)

        def on_step(generation: int, metrics: StepMetrics) -> None:
            self._record_short_health_step(slot, generation, metrics)

        trainer = IOExperiment(slot.state, experiment=self.experiment)
        trainer.train_mappings(on_generation=on_generation, on_step=on_step)
        measurement, slot.fitness = self._measure_slot(slot)
        return measurement

    def _mutation_field(self, parent: UniverseSlot) -> str:
        cursor = int(self.scheduler["mutation_cursor"])
        category_offset = parent.index // SLOTS_PER_CATEGORY
        mutation_dimensions = tuple(legacy_search_plan().search)
        field = mutation_dimensions[
            (category_offset + cursor) % len(mutation_dimensions)
        ]
        self.scheduler["mutation_cursor"] = cursor + 1
        return field

    def _next_seed(
        self,
        category: str,
        *,
        genome: UniverseGenome | None = None,
    ) -> int:
        if genome is None:
            occupied = {slot.seed for slot in self.slots if slot.category == category}
            candidate = int(self.scheduler["allocation_cursor"])
            while candidate in occupied:
                candidate += 1
            self.scheduler["allocation_cursor"] = candidate + 1
            return candidate

        registry = build_default_search_registry()
        plan = legacy_mutation_plan_for_base_config(self.base_config)
        decision = allocate_matched_evidence_seed(
            plan=plan,
            registry=registry,
            target_candidate=legacy_candidate_values(genome, category),
            assignments=tuple(
                EvidenceSeedAssignment(
                    candidate_values=legacy_candidate_values(slot.genome, slot.category),
                    seed=slot.seed,
                )
                for slot in self.slots
            ),
            allocation_cursor=int(self.scheduler["allocation_cursor"]),
        )
        self.scheduler["allocation_cursor"] = decision.next_allocation_cursor
        return decision.seed

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
        seed = self._next_seed(parent.category, genome=parent.genome)
        config = self._effective_config(parent.genome, parent.category, self.base_config)
        state = create_universe(seed=seed, config=config)
        return UniverseSlot(
            index=free_index,
            category=parent.category,
            genome=parent.genome,
            seed=seed,
            state=state,
            parent_index=parent.index,
            parent_genome_key=parent.genome_key,
            allocation_reason="seed_evidence",
            evidence_mature=parent.evidence_mature,
        )

    def replace_free_slot(
        self,
        *,
        free_index: int,
        parent: UniverseSlot,
        direction: int | None = None,
        field: str | None = None,
    ) -> UniverseSlot:
        if not 0 <= free_index < OPTIMIZER_POPULATION_SIZE:
            raise ValueError("free_index must be within the fixed population")
        if parent.index == free_index:
            raise ValueError("mutation child must use a free slot distinct from parent")
        mutation_field = field or self._mutation_field(parent)
        if direction is not None and direction not in (-1, 1):
            raise ValueError("direction must be -1 or 1")
        registry = build_default_search_registry()
        plan = legacy_mutation_plan_for_base_config(self.base_config)
        candidate_values = legacy_candidate_values(parent.genome, parent.category)
        valid_directions = legacy_mutation_directions(
            plan=plan,
            registry=registry,
            candidate=candidate_values,
            dimension_id=mutation_field,
            base_config=self.base_config,
        )
        if not valid_directions:
            raise ValueError(f"no valid adjacent mutation exists for {mutation_field}")
        preferred_direction = direction
        if preferred_direction is None:
            cursor = int(self.scheduler["mutation_cursor"])
            mutation_dimensions = tuple(plan.search)
            field_offset = mutation_dimensions.index(mutation_field)
            preferred_direction = -1 if (cursor + parent.index + field_offset) % 2 else 1
        if preferred_direction not in valid_directions:
            preferred_direction = next(
                candidate
                for candidate in valid_directions
                if candidate != preferred_direction
            )
        mutation = mutate_legacy_candidate(
            genome=parent.genome,
            category=parent.category,
            dimension_id=mutation_field,
            direction=preferred_direction,
            base_config=self.base_config,
            registry=registry,
            plan=plan,
        )
        child_genome = UniverseGenome.from_dict(dict(mutation.candidate_values.scalars))
        seed = self._next_seed(parent.category, genome=child_genome)
        config = mutation.resolved_candidate.universe_spec.to_physics_config(
            self.base_config
        )
        state = create_universe(seed=seed, config=config)
        return UniverseSlot(
            index=free_index,
            category=parent.category,
            genome=child_genome,
            seed=seed,
            state=state,
            parent_index=parent.index,
            parent_genome_key=parent.genome_key,
            last_mutation_field=mutation_field,
            allocation_reason="mutation_child",
            evidence_mature=False,
        )

    @staticmethod
    def _aggregate_fitness(records: Iterable[UniverseSlot]) -> Fitness:
        values = tuple(records)
        if not values:
            raise ValueError("cannot aggregate an empty evidence group")
        denominator = float(len(values))
        retention_evidence_count = sum(
            slot.fitness.retention_evidence_count for slot in values
        )
        retention = (
            sum(
                slot.fitness.retention * slot.fitness.retention_evidence_count
                for slot in values
            )
            / retention_evidence_count
            if retention_evidence_count > 0
            else 0.0
        )
        noise_robustness_evidence_count = sum(
            slot.fitness.noise_robustness_evidence_count for slot in values
        )
        noise_robustness = (
            sum(
                slot.fitness.noise_robustness
                * slot.fitness.noise_robustness_evidence_count
                for slot in values
            )
            / noise_robustness_evidence_count
            if noise_robustness_evidence_count > 0
            else 0.0
        )
        return Fitness(
            success=sum(slot.fitness.success for slot in values) / denominator,
            wrong_outputs=sum(slot.fitness.wrong_outputs for slot in values) / denominator,
            timeouts=sum(slot.fitness.timeouts for slot in values) / denominator,
            response_latency=sum(slot.fitness.response_latency for slot in values) / denominator,
            activity_cost=sum(slot.fitness.activity_cost for slot in values) / denominator,
            retention=retention,
            noise_robustness=noise_robustness,
            counterfactual_no_input_clean=(
                sum(slot.fitness.counterfactual_no_input_clean for slot in values)
                / denominator
            ),
            counterfactual_alternate_input_clean=(
                sum(slot.fitness.counterfactual_alternate_input_clean for slot in values)
                / denominator
            ),
            retention_evidence_count=retention_evidence_count,
            noise_robustness_evidence_count=noise_robustness_evidence_count,
        )

    def group_fitnesses(
        self,
        records: Iterable[UniverseSlot] | None = None,
    ) -> dict[tuple[str, str], Fitness]:
        groups: dict[tuple[str, str], list[UniverseSlot]] = {}
        for slot in self.slots if records is None else records:
            groups.setdefault(slot.evidence_group, []).append(slot)
        return {
            key: self._aggregate_fitness(group)
            for key, group in groups.items()
        }

    def _selection_key(
        self,
        slot: UniverseSlot,
        aggregates: Mapping[tuple[str, str], Fitness],
    ) -> tuple[tuple[float, float, float, float, float], tuple[str, str], int]:
        return aggregates[slot.evidence_group].sort_key(), slot.evidence_group, slot.index

    @staticmethod
    def _evidence_group_counts(
        records: Iterable[UniverseSlot],
    ) -> dict[tuple[str, str], int]:
        counts: dict[tuple[str, str], int] = {}
        for slot in records:
            counts[slot.evidence_group] = counts.get(slot.evidence_group, 0) + 1
        return counts

    @classmethod
    def _selection_eligible_slots(
        cls,
        records: Iterable[UniverseSlot],
    ) -> list[UniverseSlot]:
        values = list(records)
        counts = cls._evidence_group_counts(values)
        return [
            slot
            for slot in values
            if counts[slot.evidence_group] >= MINIMUM_EVIDENCE_SEEDS
        ]

    def _refresh_evidence_maturity(self, group_key: tuple[str, str]) -> None:
        group = [slot for slot in self.slots if slot.evidence_group == group_key]
        if len(group) < MINIMUM_EVIDENCE_SEEDS:
            return
        for slot in group:
            slot.evidence_mature = True

    @staticmethod
    def _pruning_eligible_slots(records: Iterable[UniverseSlot]) -> list[UniverseSlot]:
        """Return slots whose group has established the minimum evidence tier at least once."""
        return [slot for slot in records if slot.evidence_mature or slot.absolute_failure]

    def _incomplete_mutation_parent(
        self,
        local: list[UniverseSlot],
        *,
        excluded_index: int,
    ) -> UniverseSlot | None:
        groups: dict[tuple[str, str], list[UniverseSlot]] = {}
        for slot in local:
            groups.setdefault(slot.evidence_group, []).append(slot)
        for group_key in sorted(groups):
            group = groups[group_key]
            if len(group) >= MINIMUM_EVIDENCE_SEEDS:
                continue
            if any(slot.evidence_mature for slot in group):
                continue
            if not any(slot.allocation_reason == "mutation_child" for slot in group):
                continue
            sources = [slot for slot in group if slot.index != excluded_index]
            if sources:
                return min(sources, key=lambda slot: slot.index)
        return None

    def _select_parent(
        self,
        local: list[UniverseSlot],
        *,
        excluded_index: int,
    ) -> UniverseSlot:
        eligible_indices = {
            slot.index for slot in self._selection_eligible_slots(local)
        }
        sources = [
            slot
            for slot in local
            if slot.index != excluded_index and slot.index in eligible_indices
        ]
        if not sources:
            raise ValueError("a category must retain a minimum-evidence parent source")
        aggregates = self.group_fitnesses(local)
        return min(sources, key=lambda slot: self._selection_key(slot, aggregates))

    @staticmethod
    def _promising_tier_divisor(seed_count: int) -> int | None:
        if MINIMUM_EVIDENCE_SEEDS <= seed_count < 8:
            return 2
        if 8 <= seed_count < 16:
            return 4
        if 16 <= seed_count < 32:
            return 8
        return None

    def _promising_group_keys(
        self,
        local: list[UniverseSlot],
    ) -> set[tuple[str, str]]:
        if self.promising_policy is None:
            return set()
        if self.promising_policy != PROMISING_POLICY_TIERED_CATEGORY_RANK:
            raise ValueError(
                f"unsupported promising allocation policy: {self.promising_policy}"
            )
        if not local:
            return set()
        categories = {slot.category for slot in local}
        if len(categories) != 1:
            raise ValueError("promising ranking must be category-local")

        counts = self._evidence_group_counts(local)
        aggregates = self.group_fitnesses(local)
        eligible_keys = [
            group_key
            for group_key, count in counts.items()
            if count >= MINIMUM_EVIDENCE_SEEDS
        ]
        ranked = sorted(
            eligible_keys,
            key=lambda group_key: (
                aggregates[group_key].sort_key(),
                group_key[1],
            ),
        )
        rank_by_group = {
            group_key: rank
            for rank, group_key in enumerate(ranked)
        }

        promising: set[tuple[str, str]] = set()
        for group_key in ranked:
            count = counts[group_key]
            divisor = self._promising_tier_divisor(count)
            if divisor is None:
                continue
            cutoff = max(1, len(ranked) // divisor)
            if rank_by_group[group_key] < cutoff:
                promising.add(group_key)
        return promising

    def _is_promising(self, slot: UniverseSlot, local: list[UniverseSlot]) -> bool:
        return slot.evidence_group in self._promising_group_keys(local)

    def _select_promising_parent(
        self,
        local: list[UniverseSlot],
        *,
        excluded_group: tuple[str, str] | None = None,
    ) -> UniverseSlot | None:
        candidates = [
            slot
            for slot in local
            if excluded_group is None or slot.evidence_group != excluded_group
        ]
        promising = self._promising_group_keys(candidates)
        if not promising:
            return None

        counts = self._evidence_group_counts(candidates)
        aggregates = self.group_fitnesses(candidates)
        representatives: dict[tuple[str, str], UniverseSlot] = {}
        for slot in candidates:
            if slot.evidence_group not in promising:
                continue
            current = representatives.get(slot.evidence_group)
            if current is None or slot.index < current.index:
                representatives[slot.evidence_group] = slot

        return min(
            representatives.values(),
            key=lambda slot: (
                counts[slot.evidence_group],
                aggregates[slot.evidence_group].sort_key(),
                slot.genome_key,
                slot.index,
            ),
        )

    def _next_allocation_mode(
        self,
        category: str,
        *,
        promising_available: bool,
    ) -> str:
        if category not in CATEGORY_OPERATORS:
            raise ValueError("unsupported optimizer category")
        if not promising_available:
            return "mutation_child"
        key = f"allocation_mode_cursor:{category}"
        cursor = int(self.scheduler.get(key, 0))
        self.scheduler[key] = cursor + 1
        return "seed_evidence" if cursor % 2 == 0 else "mutation_child"

    def _protected_indices(self, local: list[UniverseSlot]) -> set[int]:
        aggregates = self.group_fitnesses(local)
        eligible = self._selection_eligible_slots(local)
        count = min(max(1, len(local) // 8), len(eligible))
        ordered = sorted(eligible, key=lambda slot: self._selection_key(slot, aggregates))
        return {slot.index for slot in ordered[:count]}

    def group_counts(self) -> dict[str, int]:
        counts: dict[tuple[str, str], int] = {}
        for slot in self.slots:
            counts[slot.evidence_group] = counts.get(slot.evidence_group, 0) + 1
        return {
            f"{category}:{genome}": count
            for (category, genome), count in sorted(counts.items())
        }

    def _comparison_strata(
        self,
    ) -> tuple[tuple[ResolvedComparisonStratum, list[UniverseSlot]], ...]:
        strata = legacy_comparison_strata()
        groups: dict[ResolvedComparisonStratum, list[UniverseSlot]] = {
            stratum: [] for stratum in strata
        }
        by_category = {
            str(stratum.primary_value): stratum
            for stratum in strata
        }
        if len(by_category) != len(strata):
            raise ValueError("legacy comparison strata must map to unique categories")
        for slot in self.slots:
            stratum = by_category.get(slot.category)
            if stratum is None:
                raise ValueError(
                    f"slot category is outside declared legacy strata: {slot.category}"
                )
            groups[stratum].append(slot)
        return tuple((stratum, groups[stratum]) for stratum in strata)

    def _category_counts(self) -> dict[str, int]:
        return {
            local[0].category: len(local)
            for _, local in self._comparison_strata()
            if local
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
        for _stratum, local in self._comparison_strata():
            if not local:
                continue
            category = local[0].category
            if any(slot.category != category for slot in local):
                raise ValueError("comparison stratum mixed legacy categories")
            protected = self._protected_indices(local)
            eligible = self._selection_eligible_slots(local)
            pruning_eligible = self._pruning_eligible_slots(local)
            pruned = prune_candidates(pruning_eligible, protected=protected)
            pruned_count += len(pruned)
            if not pruned:
                continue

            aggregates = self.group_fitnesses(local)
            target_index = max(
                pruned,
                key=lambda index: self._selection_key(
                    next(item for item in local if item.index == index),
                    aggregates,
                ),
            )
            reason = "growth_pruned"

            target = next(slot for slot in local if slot.index == target_index)
            sources = [slot for slot in local if slot.index != target_index]
            completion_parent = self._incomplete_mutation_parent(
                local,
                excluded_index=target_index,
            )
            if completion_parent is not None:
                parent = completion_parent
                child = self.allocate_seed_slot(
                    free_index=target.index,
                    parent=parent,
                )
                reason = "seed_evidence"
            else:
                promising_parent = self._select_promising_parent(
                    sources,
                    excluded_group=target.evidence_group,
                )
                allocation_mode = self._next_allocation_mode(
                    category,
                    promising_available=promising_parent is not None,
                )
                if allocation_mode == "seed_evidence":
                    if promising_parent is None:
                        raise RuntimeError("seed-evidence mode requires a promising parent")
                    parent = promising_parent
                    child = self.allocate_seed_slot(
                        free_index=target.index,
                        parent=parent,
                    )
                    reason = "seed_evidence"
                else:
                    parent = self._select_parent(local, excluded_index=target_index)
                    child = self.replace_free_slot(
                        free_index=target.index,
                        parent=parent,
                    )
            retirement_reason = (
                target.absolute_failure_reason
                or ("absolute_failure" if target.absolute_failure else "growth_pruned")
            )
            self.prune_history.append(
                {
                    "optimizer_generation": self.generation + 1,
                    "index": target.index,
                    "category": target.category,
                    "genome_key": target.genome_key,
                    "seed": target.seed,
                    "retirement_reason": retirement_reason,
                }
            )
            self.slots[target.index] = child
            self._refresh_evidence_maturity(child.evidence_group)
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
            "format_version": 6,
            "kind": "UniverseGenomePhase5SteadyStateOptimizer",
            "generation": self.generation,
            "base_config": self.base_config.to_dict(),
            "experiment": self.experiment.to_dict(),
            "scheduler": dict(self.scheduler),
            "prune_history": [dict(event) for event in self.prune_history],
            "slots": [slot.to_dict() for slot in self.slots],
        }

    @classmethod
    def from_snapshot(cls, payload: Mapping[str, Any]) -> "SteadyStateOptimizer":
        format_version = int(payload.get("format_version", -1))
        if (
            format_version not in (4, 5, 6)
            or payload.get("kind") != "UniverseGenomePhase5SteadyStateOptimizer"
        ):
            raise ValueError("unsupported authoritative Phase 5 optimizer snapshot")
        trace_config_fields = {
            "trace_write_cap",
            "trace_transfer_cap",
            "trace_discharge_cap",
            "trace_decay_rate",
            "trace_bonus_shift",
        }
        if format_version == 6:
            raw_base_config = payload.get("base_config")
            if (
                not isinstance(raw_base_config, Mapping)
                or not trace_config_fields.issubset(raw_base_config)
            ):
                raise ValueError("v6 optimizer requires slow-trace base configuration")
        raw_slots = payload.get("slots")
        if not isinstance(raw_slots, list) or len(raw_slots) != OPTIMIZER_POPULATION_SIZE:
            raise ValueError("authoritative optimizer snapshot must contain 128 slots")
        if format_version >= 5:
            for record in raw_slots:
                if not isinstance(record, Mapping):
                    raise ValueError("authoritative slot records must be objects")
                if format_version == 6:
                    raw_state = record.get("state")
                    if (
                        not isinstance(raw_state, Mapping)
                        or int(raw_state.get("format_version", -1)) != 2
                    ):
                        raise ValueError("v6 optimizer requires nested UniverseState v2")
                    raw_state_config = raw_state.get("config")
                    if (
                        not isinstance(raw_state_config, Mapping)
                        or not trace_config_fields.issubset(raw_state_config)
                    ):
                        raise ValueError("v6 optimizer requires nested slow-trace configuration")
                allocation_reason = str(record.get("allocation_reason", "initial"))
                if (
                    allocation_reason in ("seed_evidence", "mutation_child")
                    and not record.get("parent_genome_key")
                ):
                    raise ValueError(
                        "v5 allocated child requires durable parent_genome_key"
                    )
        base_config = PhysicsConfig.from_mapping(payload["base_config"])
        if format_version in (4, 5):
            values = base_config.to_dict()
            values.update({
                "trace_write_cap": 0,
                "trace_transfer_cap": 0,
                "trace_discharge_cap": 0,
                "trace_decay_rate": 0,
                "trace_bonus_shift": 8,
            })
            base_config = PhysicsConfig(**values)
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
        maturity_groups: dict[tuple[str, str], list[UniverseSlot]] = {}
        for slot in slots:
            maturity_groups.setdefault(slot.evidence_group, []).append(slot)
        for group in maturity_groups.values():
            markers = {slot.evidence_mature for slot in group}
            if len(markers) != 1:
                raise ValueError("evidence maturity must be consistent within one genome group")
            if len(group) >= MINIMUM_EVIDENCE_SEEDS and not next(iter(markers)):
                raise ValueError("minimum-evidence group must be marked mature")
        scheduler = payload.get("scheduler", {})
        promising_policy = (
            scheduler.get("promising_policy")
            if isinstance(scheduler, Mapping)
            else None
        )
        raw_prune_history = payload.get("prune_history", ())
        if format_version >= 5 and not isinstance(raw_prune_history, list):
            raise ValueError("optimizer prune_history must be an array")
        if format_version == 4:
            raw_prune_history = ()
        return cls(
            slots,
            base_config=base_config,
            experiment=ExperimentConfig.from_mapping(payload["experiment"]),
            generation=int(payload["generation"]),
            scheduler=scheduler if isinstance(scheduler, Mapping) else {},
            promising_policy=promising_policy,
            prune_history=raw_prune_history,
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
        "held_out_mapping": (
            measurement.held_out_mapping.to_dict()
            if measurement.held_out_mapping is not None
            else None
        ),
        "training_qualified_count": measurement.training_qualified_count,
        "generalization_eligible_count": measurement.generalization_eligible_count,
        "generalized_count": measurement.generalized_count,
        "generalization_failed_count": measurement.generalization_failed_count,
        "generalization_rate": measurement.generalization_rate,
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
                "baseline_held_out_success": (
                    item.baseline_held_out.success
                    if item.baseline_held_out is not None
                    else None
                ),
                "trained_held_out_success": (
                    item.trained_held_out.success
                    if item.trained_held_out is not None
                    else None
                ),
                "baseline_held_out_event_generations": (
                    list(item.baseline_held_out.event_generations)
                    if item.baseline_held_out is not None
                    else []
                ),
                "trained_held_out_event_generations": (
                    list(item.trained_held_out.event_generations)
                    if item.trained_held_out is not None
                    else []
                ),
                "training_qualified": item.generalization_classification()[0],
                "generalization_eligible": item.generalization_classification()[1],
                "generalized": item.generalization_classification()[2],
                "generalization_failed": item.generalization_classification()[3],
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
        "promising_policy": optimizer.promising_policy,
        "phase4_learning_claim": measurement.learning_claim,
        "candidate_genome": candidate.to_dict(),
        "candidate_measurement": _measurement_summary(measurement),
        "counterfactual_clean": {
            "no_input": measurement.no_input_clean,
            "alternate_input": measurement.alternate_input_clean,
        },
        "replacements": integrated_summary["replacements"],
    }
