"""Declarative generalized Outer Search model and canonical legacy projection.

Phase C introduces representation/resolution only. The existing Phase 5 optimizer
continues to own mutation/allocation/selection until later gated checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from itertools import product
from statistics import median
from typing import Any, Mapping

from core.physics import PhysicsConfig, create_universe
from core.state import UniverseState
from .genome import (
    GENOME_BOUNDS,
    UNIVERSE_GENOME_FIELDS,
    UniverseGenome,
)


LEGACY_LATENT_OPERATORS = (
    "masked_copy",
    "masked_xor",
    "rotate_copy",
    "masked_and",
)
LEGACY_POPULATION_SIZE = 128
LEGACY_SLOTS_PER_STRATUM = 32
LEGACY_EVIDENCE_SEEDS = 4
LEGACY_OBJECTIVE_PROFILE_ID = "phase5_legacy"
LEGACY_OBJECTIVE_PROFILE_VERSION = 1
LEGACY_PROMISING_POLICY = "tiered_category_rank"

LEGACY_TRACE_FIXED = {
    "trace_write_cap": 0,
    "trace_transfer_cap": 0,
    "trace_discharge_cap": 0,
    "trace_decay_rate": 0,
    "trace_bonus_shift": 8,
}

_GENOME_PHYSICS_FIELDS = {
    "initial_density": "initial_density",
    "hp_decay": "hp_decay",
    "hp_gain": "recovery_hp",
    "noise_rate": "noise_rate",
    "bond_gain": "bond_gain",
    "bond_decay": "bond_decay",
    "collision_threshold": "collision_threshold",
    "fusion_threshold": "fusion_velocity_threshold",
    "fragmentation_base_probability": "fragmentation_rate",
    "black_hole_grace": "black_hole_grace",
    "rotate_amount": "rotate_amount",
}

_TRACE_BOUNDS = {
    "trace_write_cap": (0, 0xFF),
    "trace_transfer_cap": (0, 0xFF),
    "trace_discharge_cap": (0, 0xFF),
    "trace_decay_rate": (0, 0xFFFF),
    "trace_bonus_shift": (0, 8),
}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ActivationCondition:
    """Structured activation predicate over one already-resolved dimension/rule."""

    dimension_id: str
    allowed_values: tuple[Any, ...]

    def __post_init__(self) -> None:
        if not self.dimension_id:
            raise ValueError("activation dimension_id must be non-empty")
        if not self.allowed_values:
            raise ValueError("activation allowed_values must be non-empty")

    def evaluate(
        self,
        scalar_values: Mapping[str, Any],
        rule_values: Mapping[str, str],
    ) -> bool:
        if self.dimension_id in scalar_values:
            value = scalar_values[self.dimension_id]
        elif self.dimension_id in rule_values:
            value = rule_values[self.dimension_id]
        else:
            raise ValueError(
                f"activation dependency is unresolved: {self.dimension_id}"
            )
        return value in self.allowed_values

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "allowed_values": list(self.allowed_values),
        }


@dataclass(frozen=True)
class ValueConstraint:
    """Bounded structured value constraint, optionally conditional."""

    dimension_id: str
    allowed_values: tuple[Any, ...]
    when: ActivationCondition | None = None

    def __post_init__(self) -> None:
        if not self.dimension_id:
            raise ValueError("constraint dimension_id must be non-empty")
        if not self.allowed_values:
            raise ValueError("constraint allowed_values must be non-empty")


@dataclass(frozen=True)
class ScalarDimension:
    dimension_id: str
    physics_field: str
    value_type: str
    default: Any
    allowed_values: tuple[Any, ...] | None = None
    lower: int | None = None
    upper: int | None = None
    strategy_ids: tuple[str, ...] = ("fixed",)
    activation: ActivationCondition | None = None

    def __post_init__(self) -> None:
        if not self.dimension_id or not self.physics_field:
            raise ValueError("scalar dimension id/physics field must be non-empty")
        if self.value_type != "int":
            raise ValueError("Phase C scalar dimensions support int values only")
        if self.allowed_values is not None and not self.allowed_values:
            raise ValueError("allowed_values must be non-empty when provided")
        if self.allowed_values is None and (self.lower is None or self.upper is None):
            raise ValueError("scalar dimension requires allowed_values or bounds")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("scalar lower bound cannot exceed upper bound")
        if not self.strategy_ids:
            raise ValueError("scalar dimension requires at least one strategy")
        self.validate_value(self.default)

    def validate_value(self, value: Any) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{self.dimension_id} must be int")
        if self.allowed_values is not None and value not in self.allowed_values:
            raise ValueError(
                f"{self.dimension_id} value {value} is outside registered values"
            )
        if self.lower is not None and value < self.lower:
            raise ValueError(
                f"{self.dimension_id} value {value} is below registered lower bound"
            )
        if self.upper is not None and value > self.upper:
            raise ValueError(
                f"{self.dimension_id} value {value} is above registered upper bound"
            )

    def domain_contains(self, value: Any) -> bool:
        try:
            self.validate_value(value)
        except ValueError:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "physics_field": self.physics_field,
            "value_type": self.value_type,
            "default": self.default,
            "allowed_values": (
                None if self.allowed_values is None else list(self.allowed_values)
            ),
            "lower": self.lower,
            "upper": self.upper,
            "strategy_ids": list(self.strategy_ids),
            "activation": (
                None if self.activation is None else self.activation.to_dict()
            ),
        }


@dataclass(frozen=True)
class RuleDimension:
    dimension_id: str
    physics_field: str
    variants: tuple[str, ...]
    default_variant: str
    strategy_ids: tuple[str, ...] = ("fixed",)
    activation: ActivationCondition | None = None

    def __post_init__(self) -> None:
        if not self.dimension_id or not self.physics_field:
            raise ValueError("rule dimension id/physics field must be non-empty")
        if not self.variants or len(set(self.variants)) != len(self.variants):
            raise ValueError("rule dimension variants must be unique/non-empty")
        if self.default_variant not in self.variants:
            raise ValueError("rule default_variant must be registered")
        if not self.strategy_ids:
            raise ValueError("rule dimension requires at least one strategy")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "physics_field": self.physics_field,
            "variants": list(self.variants),
            "default_variant": self.default_variant,
            "strategy_ids": list(self.strategy_ids),
            "activation": (
                None if self.activation is None else self.activation.to_dict()
            ),
        }


@dataclass(frozen=True)
class SearchRegistry:
    scalar_dimensions: Mapping[str, ScalarDimension]
    rule_dimensions: Mapping[str, RuleDimension]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported search registry schema_version")
        for key, definition in self.scalar_dimensions.items():
            if key != definition.dimension_id:
                raise ValueError("scalar registry key/id mismatch")
        for key, definition in self.rule_dimensions.items():
            if key != definition.dimension_id:
                raise ValueError("rule registry key/id mismatch")
        overlap = set(self.scalar_dimensions) & set(self.rule_dimensions)
        if overlap:
            raise ValueError(f"dimension ids must be globally unique: {sorted(overlap)}")
        for definition in (
            *self.scalar_dimensions.values(),
            *self.rule_dimensions.values(),
        ):
            condition = definition.activation
            if condition is None:
                continue
            if (
                condition.dimension_id not in self.scalar_dimensions
                and condition.dimension_id not in self.rule_dimensions
            ):
                raise ValueError(
                    f"unknown activation dependency: {condition.dimension_id}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scalars": {
                key: self.scalar_dimensions[key].to_dict()
                for key in sorted(self.scalar_dimensions)
            },
            "rules": {
                key: self.rule_dimensions[key].to_dict()
                for key in sorted(self.rule_dimensions)
            },
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class ScalarSearch:
    strategy: str
    domain: tuple[Any, ...] | str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "domain": self.domain if isinstance(self.domain, str) else list(self.domain),
        }


@dataclass(frozen=True)
class RuleSearch:
    variants: tuple[str, ...]
    strategy: str = "finite_variant"

    def __post_init__(self) -> None:
        if not self.variants:
            raise ValueError("rule search variants must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {"variants": list(self.variants), "strategy": self.strategy}


@dataclass(frozen=True)
class ComparisonStratum:
    group_by: tuple[str, ...]
    selection_scope: str
    allocation_policy: str
    matched_evidence_policy: str

    def __post_init__(self) -> None:
        if not self.group_by:
            raise ValueError("stratum group_by must be non-empty")
        if self.selection_scope not in ("within", "across"):
            raise ValueError("stratum selection_scope must be within or across")
        if not self.allocation_policy or not self.matched_evidence_policy:
            raise ValueError("stratum policy ids must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_by": list(self.group_by),
            "selection_scope": self.selection_scope,
            "allocation_policy": self.allocation_policy,
            "matched_evidence_policy": self.matched_evidence_policy,
        }


@dataclass(frozen=True)
class ResolvedComparisonStratum:
    """One concrete comparison-stratum membership resolved from a plan."""

    values: tuple[tuple[str, Any], ...]
    selection_scope: str
    allocation_policy: str
    matched_evidence_policy: str
    definition_index: int = 0

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("resolved comparison stratum values must be non-empty")
        ids = tuple(dimension_id for dimension_id, _ in self.values)
        if len(set(ids)) != len(ids):
            raise ValueError("resolved comparison stratum dimensions must be unique")
        if self.selection_scope not in ("within", "across"):
            raise ValueError("resolved stratum selection_scope must be within or across")
        if self.definition_index < 0:
            raise ValueError("resolved stratum definition_index must be non-negative")

    @property
    def primary_value(self) -> Any:
        if len(self.values) != 1:
            raise ValueError("primary_value requires exactly one grouping dimension")
        return self.values[0][1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "values": [
                {"dimension_id": dimension_id, "value": value}
                for dimension_id, value in self.values
            ],
            "selection_scope": self.selection_scope,
            "allocation_policy": self.allocation_policy,
            "matched_evidence_policy": self.matched_evidence_policy,
            "definition_index": self.definition_index,
        }


def _normalize_scalar_search(value: Any) -> ScalarSearch:
    if isinstance(value, ScalarSearch):
        return value
    if isinstance(value, tuple) and len(value) == 2:
        strategy, domain = value
        if isinstance(domain, str):
            normalized_domain: tuple[Any, ...] | str = domain
        else:
            normalized_domain = tuple(domain)
        return ScalarSearch(str(strategy), normalized_domain)
    if isinstance(value, Mapping):
        domain = value["domain"]
        return ScalarSearch(
            str(value["strategy"]),
            str(domain) if isinstance(domain, str) else tuple(domain),
        )
    raise TypeError("search declaration must be ScalarSearch, pair, or mapping")


def _normalize_rule_search(value: Any) -> RuleSearch:
    if isinstance(value, RuleSearch):
        return value
    if isinstance(value, Mapping):
        return RuleSearch(
            tuple(str(item) for item in value["variants"]),
            str(value.get("strategy", "finite_variant")),
        )
    raise TypeError("rule declaration must be RuleSearch or mapping")


@dataclass(frozen=True)
class SearchPlan:
    schema_version: int
    plan_id: str
    plan_version: int
    population_size: int
    fixed: Mapping[str, Any] = field(default_factory=dict)
    search: Mapping[str, ScalarSearch | tuple[Any, Any] | Mapping[str, Any]] = field(
        default_factory=dict
    )
    rules: Mapping[str, RuleSearch | Mapping[str, Any]] = field(default_factory=dict)
    constraints: tuple[ValueConstraint, ...] = ()
    strata: tuple[ComparisonStratum, ...] = ()
    objective_profile_id: str = LEGACY_OBJECTIVE_PROFILE_ID
    objective_profile_version: int = LEGACY_OBJECTIVE_PROFILE_VERSION
    search_cohort_policy: str = "legacy_optimizer_evidence"
    validation_cohort_policy: str = "none"
    scheduler_base_seed: int = 0
    scheduler_policy: str = "legacy_phase5"
    initialization_policy: str = "legacy_phase5_eight"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fixed",
            {str(key): value for key, value in self.fixed.items()},
        )
        object.__setattr__(
            self,
            "search",
            {
                str(key): _normalize_scalar_search(value)
                for key, value in self.search.items()
            },
        )
        object.__setattr__(
            self,
            "rules",
            {
                str(key): _normalize_rule_search(value)
                for key, value in self.rules.items()
            },
        )
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(self, "strata", tuple(self.strata))

    def validate(self, registry: SearchRegistry) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported SearchPlan schema_version")
        if not self.plan_id or self.plan_version < 1:
            raise ValueError("SearchPlan id/version must be valid")
        if self.population_size < 1:
            raise ValueError("SearchPlan population_size must be positive")
        if self.objective_profile_version < 1 or not self.objective_profile_id:
            raise ValueError("ObjectiveProfile id/version must be valid")
        if self.scheduler_base_seed < 0:
            raise ValueError("scheduler base seed must be non-negative")

        fixed_ids = set(self.fixed)
        search_ids = set(self.search)
        overlap = fixed_ids & search_ids
        if overlap:
            raise ValueError(f"fixed/search overlap: {sorted(overlap)}")

        for dimension_id, value in self.fixed.items():
            definition = registry.scalar_dimensions.get(dimension_id)
            if definition is None:
                raise ValueError(f"unknown scalar dimension: {dimension_id}")
            definition.validate_value(value)

        for dimension_id, declaration in self.search.items():
            definition = registry.scalar_dimensions.get(dimension_id)
            if definition is None:
                raise ValueError(f"unknown scalar dimension: {dimension_id}")
            if declaration.strategy not in definition.strategy_ids:
                raise ValueError(
                    f"unsupported strategy {declaration.strategy} for {dimension_id}"
                )
            if declaration.domain != "registered":
                if not declaration.domain:
                    raise ValueError(f"search domain is empty: {dimension_id}")
                for value in declaration.domain:
                    definition.validate_value(value)

        for dimension_id, declaration in self.rules.items():
            definition = registry.rule_dimensions.get(dimension_id)
            if definition is None:
                raise ValueError(f"unknown rule dimension: {dimension_id}")
            if declaration.strategy not in definition.strategy_ids:
                raise ValueError(
                    f"unsupported rule strategy {declaration.strategy} for {dimension_id}"
                )
            for variant in declaration.variants:
                if variant not in definition.variants:
                    raise ValueError(
                        f"unknown rule variant {variant} for {dimension_id}"
                    )

        declared = fixed_ids | search_ids | set(self.rules)
        for dimension_id in declared:
            definition = (
                registry.scalar_dimensions.get(dimension_id)
                or registry.rule_dimensions.get(dimension_id)
            )
            if definition is None or definition.activation is None:
                continue
            dependency = definition.activation.dimension_id
            if dependency not in declared:
                raise ValueError(
                    f"conditional dependency {dependency} is not declared in SearchPlan"
                )

        completed: set[str] = set()
        for dimension_id in sorted(declared):
            _check_activation_cycle(
                dimension_id,
                registry,
                declared,
                set(),
                completed,
            )

        for constraint in self.constraints:
            if constraint.dimension_id not in declared:
                raise ValueError(
                    f"constraint dimension is not declared: {constraint.dimension_id}"
                )
            if constraint.when is not None:
                if constraint.when.dimension_id not in declared:
                    raise ValueError(
                        "constraint activation dependency is not declared: "
                        f"{constraint.when.dimension_id}"
                    )

        for stratum in self.strata:
            for dimension_id in stratum.group_by:
                if dimension_id not in declared:
                    raise ValueError(
                        f"stratum dimension is not declared: {dimension_id}"
                    )

    def with_rule_variants(
        self,
        dimension_id: str,
        variants: tuple[str, ...],
    ) -> "SearchPlan":
        rules = dict(self.rules)
        current = rules.get(dimension_id)
        strategy = (
            current.strategy
            if isinstance(current, RuleSearch)
            else "finite_variant"
        )
        rules[dimension_id] = RuleSearch(tuple(variants), strategy)
        return replace(self, rules=rules)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "population_size": self.population_size,
            "fixed": {key: self.fixed[key] for key in sorted(self.fixed)},
            "search": {
                key: self.search[key].to_dict() for key in sorted(self.search)
            },
            "rules": {
                key: self.rules[key].to_dict() for key in sorted(self.rules)
            },
            "constraints": [
                {
                    "dimension_id": item.dimension_id,
                    "allowed_values": list(item.allowed_values),
                    "when": None if item.when is None else item.when.to_dict(),
                }
                for item in self.constraints
            ],
            "strata": [item.to_dict() for item in self.strata],
            "objective_profile": {
                "id": self.objective_profile_id,
                "version": self.objective_profile_version,
            },
            "cohorts": {
                "search": self.search_cohort_policy,
                "validation": self.validation_cohort_policy,
            },
            "scheduler": {
                "base_seed": self.scheduler_base_seed,
                "policy": self.scheduler_policy,
            },
            "initialization_policy": self.initialization_policy,
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class CandidateValues:
    scalars: Mapping[str, Any]
    rules: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scalars",
            {str(key): value for key, value in self.scalars.items()},
        )
        object.__setattr__(
            self,
            "rules",
            {str(key): str(value) for key, value in self.rules.items()},
        )


@dataclass(frozen=True)
class ResolvedUniverseSpec:
    """Fully resolved physical input for Inner construction only."""

    scalar_values: Mapping[str, Any]
    rule_values: Mapping[str, str]
    physics_values: Mapping[str, Any]
    rule_physics_values: Mapping[str, Any]
    schema_version: int = 1

    def to_physics_config(self, base: PhysicsConfig | None = None) -> PhysicsConfig:
        resolved = base or PhysicsConfig()
        values = resolved.to_dict()
        values.update(self.physics_values)
        values.update(self.rule_physics_values)
        return PhysicsConfig(**values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scalar_values": {
                key: self.scalar_values[key] for key in sorted(self.scalar_values)
            },
            "rule_values": {
                key: self.rule_values[key] for key in sorted(self.rule_values)
            },
            "physics_values": {
                key: self.physics_values[key] for key in sorted(self.physics_values)
            },
            "rule_physics_values": {
                key: self.rule_physics_values[key]
                for key in sorted(self.rule_physics_values)
            },
        }


@dataclass(frozen=True)
class ResolvedCandidate:
    """Outer metadata paired with an Inner-safe resolved physical specification."""

    candidate_identity: str
    active_dimensions: tuple[str, ...]
    universe_spec: ResolvedUniverseSpec

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_identity": self.candidate_identity,
            "active_dimensions": list(self.active_dimensions),
            "universe_spec": self.universe_spec.to_dict(),
        }


@dataclass(frozen=True)
class ScalarMutationResult:
    dimension_id: str
    direction: int
    before: Any
    after: Any
    candidate_values: CandidateValues
    resolved_candidate: ResolvedCandidate


@dataclass(frozen=True)
class EvidenceSeedAssignment:
    candidate_values: CandidateValues
    seed: int

    def __post_init__(self) -> None:
        if int(self.seed) < 0:
            raise ValueError("evidence seed must be non-negative")


@dataclass(frozen=True)
class EvidenceSeedDecision:
    seed: int
    next_allocation_cursor: int
    matched_existing_evidence: bool

    def __post_init__(self) -> None:
        if self.seed < 0 or self.next_allocation_cursor < 0:
            raise ValueError("evidence seed/cursor must be non-negative")


@dataclass(frozen=True)
class SelectionRecord:
    """Outer-only comparable evidence record for one occupied slot."""

    index: int
    group_key: Any
    objective_key: tuple[Any, ...]
    evidence_count: int
    candidate_tie_key: Any
    growth_windows: tuple[int, ...] = ()
    absolute_failure: bool = False
    evidence_mature: bool = False

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("selection record index must be non-negative")
        if self.evidence_count < 0:
            raise ValueError("selection record evidence_count must be non-negative")
        if any(int(window) < 0 for window in self.growth_windows):
            raise ValueError("selection record growth windows must be non-negative")

    @property
    def selection_key(self) -> tuple[tuple[Any, ...], Any, int]:
        return self.objective_key, self.group_key, self.index


@dataclass(frozen=True)
class CandidateReplacement:
    target_index: int
    seed: int
    candidate_values: CandidateValues
    resolved_candidate: ResolvedCandidate
    parent_candidate_identity: str
    parent_index: int
    allocation_reason: str
    evidence_mature: bool
    mutation_dimension: str | None = None
    mutation_direction: int | None = None

    def __post_init__(self) -> None:
        if self.target_index < 0 or self.seed < 0 or self.parent_index < 0:
            raise ValueError("replacement indices/seed must be non-negative")
        if self.allocation_reason not in ("seed_evidence", "mutation_child"):
            raise ValueError("unsupported replacement allocation reason")
        if self.allocation_reason == "seed_evidence":
            if self.mutation_dimension is not None or self.mutation_direction is not None:
                raise ValueError("seed evidence replacement cannot carry mutation metadata")
        else:
            if not self.mutation_dimension or self.mutation_direction not in (-1, 1):
                raise ValueError("mutation replacement requires dimension and direction")


@dataclass(frozen=True)
class ResolvedPopulationSlot:
    index: int
    seed: int
    candidate_values: CandidateValues
    resolved_candidate: ResolvedCandidate
    state: UniverseState
    legacy_genome_values: Mapping[str, int]
    rule_values: Mapping[str, str]


def _check_activation_cycle(
    dimension_id: str,
    registry: SearchRegistry,
    declared: set[str],
    visiting: set[str],
    completed: set[str],
) -> None:
    if dimension_id in completed:
        return
    if dimension_id in visiting:
        raise ValueError("conditional activation dependency cycle")
    visiting.add(dimension_id)
    definition = (
        registry.scalar_dimensions.get(dimension_id)
        or registry.rule_dimensions.get(dimension_id)
    )
    if definition is not None and definition.activation is not None:
        dependency = definition.activation.dimension_id
        if dependency not in declared:
            raise ValueError(
                f"conditional dependency {dependency} is not declared in SearchPlan"
            )
        _check_activation_cycle(
            dependency,
            registry,
            declared,
            visiting,
            completed,
        )
    visiting.remove(dimension_id)
    completed.add(dimension_id)


def resolve_candidate(
    plan: SearchPlan,
    registry: SearchRegistry,
    candidate: CandidateValues,
) -> ResolvedCandidate:
    """Resolve one candidate without exposing search metadata to Inner physics."""

    plan.validate(registry)
    extra_scalars = set(candidate.scalars) - set(plan.search)
    if extra_scalars:
        raise ValueError(
            f"candidate contains non-search scalar values: {sorted(extra_scalars)}"
        )
    extra_rules = set(candidate.rules) - set(plan.rules)
    if extra_rules:
        raise ValueError(
            f"candidate contains undeclared rule values: {sorted(extra_rules)}"
        )

    declared = set(plan.fixed) | set(plan.search) | set(plan.rules)
    completed: set[str] = set()
    for dimension_id in sorted(declared):
        _check_activation_cycle(
            dimension_id,
            registry,
            declared,
            set(),
            completed,
        )

    scalar_values: dict[str, Any] = {}
    rule_values: dict[str, str] = {}
    active: dict[str, bool] = {}

    def resolve_rule(dimension_id: str) -> str:
        if dimension_id in rule_values:
            return rule_values[dimension_id]
        definition = registry.rule_dimensions[dimension_id]
        is_active = True
        if definition.activation is not None:
            dependency = definition.activation.dimension_id
            if dependency in registry.scalar_dimensions:
                resolve_scalar(dependency)
            elif dependency in registry.rule_dimensions:
                resolve_rule(dependency)
            is_active = definition.activation.evaluate(scalar_values, rule_values)
        active[dimension_id] = is_active
        declaration = plan.rules[dimension_id]
        if not is_active:
            value = definition.default_variant
        elif dimension_id in candidate.rules:
            value = candidate.rules[dimension_id]
        elif len(declaration.variants) == 1:
            value = declaration.variants[0]
        else:
            raise ValueError(f"active rule value is unresolved: {dimension_id}")
        if value not in declaration.variants and is_active:
            raise ValueError(
                f"candidate rule {value} is outside SearchPlan variants for {dimension_id}"
            )
        if value not in definition.variants:
            raise ValueError(f"unknown rule variant {value} for {dimension_id}")
        rule_values[dimension_id] = value
        return value

    def resolve_scalar(dimension_id: str) -> Any:
        if dimension_id in scalar_values:
            return scalar_values[dimension_id]
        definition = registry.scalar_dimensions[dimension_id]
        is_active = True
        if definition.activation is not None:
            dependency = definition.activation.dimension_id
            if dependency in registry.scalar_dimensions:
                resolve_scalar(dependency)
            elif dependency in registry.rule_dimensions:
                resolve_rule(dependency)
            is_active = definition.activation.evaluate(scalar_values, rule_values)
        active[dimension_id] = is_active
        if not is_active:
            value = (
                plan.fixed[dimension_id]
                if dimension_id in plan.fixed
                else definition.default
            )
        elif dimension_id in plan.fixed:
            value = plan.fixed[dimension_id]
        elif dimension_id in plan.search:
            if dimension_id not in candidate.scalars:
                raise ValueError(
                    f"active searchable scalar is unresolved: {dimension_id}"
                )
            value = candidate.scalars[dimension_id]
            declaration = plan.search[dimension_id]
            if declaration.domain != "registered" and value not in declaration.domain:
                raise ValueError(
                    f"candidate scalar {value} is outside SearchPlan domain for "
                    f"{dimension_id}"
                )
        else:
            raise ValueError(f"scalar dimension is not declared: {dimension_id}")
        definition.validate_value(value)
        scalar_values[dimension_id] = value
        return value

    for dimension_id in sorted(plan.fixed):
        resolve_scalar(dimension_id)
    for dimension_id in sorted(plan.search):
        resolve_scalar(dimension_id)
    for dimension_id in sorted(plan.rules):
        resolve_rule(dimension_id)

    for constraint in plan.constraints:
        should_apply = True
        if constraint.when is not None:
            should_apply = constraint.when.evaluate(scalar_values, rule_values)
        if not should_apply:
            continue
        value = (
            scalar_values[constraint.dimension_id]
            if constraint.dimension_id in scalar_values
            else rule_values[constraint.dimension_id]
        )
        if value not in constraint.allowed_values:
            raise ValueError(
                f"resolved candidate violates constraint for {constraint.dimension_id}"
            )

    active_dimensions = tuple(
        sorted(dimension_id for dimension_id, enabled in active.items() if enabled)
    )
    identity_payload = {
        "scalars": {
            key: scalar_values[key]
            for key in sorted(scalar_values)
            if active.get(key, False)
        },
        "rules": {
            key: rule_values[key]
            for key in sorted(rule_values)
            if active.get(key, False)
        },
    }
    candidate_identity = _digest(identity_payload)

    physics_values = {
        registry.scalar_dimensions[key].physics_field: scalar_values[key]
        for key in scalar_values
    }
    rule_physics_values = {
        registry.rule_dimensions[key].physics_field: rule_values[key]
        for key in rule_values
    }

    universe_spec = ResolvedUniverseSpec(
        scalar_values=scalar_values,
        rule_values=rule_values,
        physics_values=physics_values,
        rule_physics_values=rule_physics_values,
    )
    return ResolvedCandidate(
        candidate_identity=candidate_identity,
        active_dimensions=active_dimensions,
        universe_spec=universe_spec,
    )


def _comparison_group_domain(
    plan: SearchPlan,
    registry: SearchRegistry,
    dimension_id: str,
) -> tuple[Any, ...]:
    if dimension_id in plan.rules:
        return tuple(plan.rules[dimension_id].variants)
    if dimension_id in plan.fixed:
        return (plan.fixed[dimension_id],)
    if dimension_id in plan.search:
        declaration = plan.search[dimension_id]
        if declaration.domain == "registered":
            definition = registry.scalar_dimensions[dimension_id]
            if definition.allowed_values is None:
                raise ValueError(
                    "cannot enumerate a registered-bounds scalar comparison stratum: "
                    f"{dimension_id}"
                )
            return tuple(definition.allowed_values)
        return tuple(declaration.domain)
    raise ValueError(f"stratum dimension is not declared: {dimension_id}")


def enumerate_comparison_strata(
    plan: SearchPlan,
    registry: SearchRegistry,
) -> tuple[ResolvedComparisonStratum, ...]:
    """Enumerate finite concrete strata in declared plan/domain order."""

    plan.validate(registry)
    resolved: list[ResolvedComparisonStratum] = []
    for definition_index, definition in enumerate(plan.strata):
        domains: list[tuple[Any, ...]] = []
        for dimension_id in definition.group_by:
            registered = (
                registry.scalar_dimensions.get(dimension_id)
                or registry.rule_dimensions.get(dimension_id)
            )
            if registered is None:
                raise ValueError(f"unknown stratum dimension: {dimension_id}")
            if registered.activation is not None:
                raise ValueError(
                    "conditional comparison strata require candidate resolution: "
                    f"{dimension_id}"
                )
            domain = _comparison_group_domain(plan, registry, dimension_id)
            if not domain:
                raise ValueError(f"comparison stratum domain is empty: {dimension_id}")
            domains.append(domain)

        for combination in product(*domains):
            resolved.append(
                ResolvedComparisonStratum(
                    values=tuple(zip(definition.group_by, combination, strict=True)),
                    selection_scope=definition.selection_scope,
                    allocation_policy=definition.allocation_policy,
                    matched_evidence_policy=definition.matched_evidence_policy,
                    definition_index=definition_index,
                )
            )
    return tuple(resolved)


def resolve_candidate_strata(
    plan: SearchPlan,
    registry: SearchRegistry,
    candidate: CandidateValues,
) -> tuple[ResolvedComparisonStratum, ...]:
    """Resolve one candidate into its concrete declared comparison strata."""

    resolved_candidate = resolve_candidate(plan, registry, candidate)
    values = resolved_candidate.universe_spec
    memberships: list[ResolvedComparisonStratum] = []
    for definition_index, definition in enumerate(plan.strata):
        grouped: list[tuple[str, Any]] = []
        for dimension_id in definition.group_by:
            if dimension_id in values.scalar_values:
                value = values.scalar_values[dimension_id]
            elif dimension_id in values.rule_values:
                value = values.rule_values[dimension_id]
            else:
                raise ValueError(
                    f"resolved candidate lacks stratum dimension: {dimension_id}"
                )
            grouped.append((dimension_id, value))
        memberships.append(
            ResolvedComparisonStratum(
                values=tuple(grouped),
                selection_scope=definition.selection_scope,
                allocation_policy=definition.allocation_policy,
                matched_evidence_policy=definition.matched_evidence_policy,
                definition_index=definition_index,
            )
        )
    return tuple(memberships)


def resolve_candidate_stratum(
    plan: SearchPlan,
    registry: SearchRegistry,
    candidate: CandidateValues,
) -> ResolvedComparisonStratum:
    memberships = resolve_candidate_strata(plan, registry, candidate)
    if len(memberships) != 1:
        raise ValueError(
            "singular candidate stratum resolution requires exactly one stratum definition"
        )
    return memberships[0]


def legacy_comparison_strata(
    *,
    plan: SearchPlan | None = None,
    registry: SearchRegistry | None = None,
) -> tuple[ResolvedComparisonStratum, ...]:
    resolved_registry = registry or build_default_search_registry()
    resolved_plan = plan or legacy_search_plan()
    return enumerate_comparison_strata(resolved_plan, resolved_registry)


def selection_eligible_indices(
    records: tuple[SelectionRecord, ...] | list[SelectionRecord],
    *,
    minimum_evidence: int = 4,
) -> set[int]:
    if minimum_evidence < 1:
        raise ValueError("minimum_evidence must be positive")
    return {
        record.index
        for record in records
        if record.evidence_count >= minimum_evidence
    }


def select_parent_index(
    records: tuple[SelectionRecord, ...] | list[SelectionRecord],
    *,
    excluded_index: int,
    minimum_evidence: int = 4,
) -> int:
    eligible = selection_eligible_indices(
        records,
        minimum_evidence=minimum_evidence,
    )
    sources = [
        record
        for record in records
        if record.index != excluded_index and record.index in eligible
    ]
    if not sources:
        raise ValueError("a stratum must retain a minimum-evidence parent source")
    return min(sources, key=lambda record: record.selection_key).index


def protected_selection_indices(
    records: tuple[SelectionRecord, ...] | list[SelectionRecord],
    *,
    minimum_evidence: int = 4,
) -> set[int]:
    values = list(records)
    eligible = [
        record
        for record in values
        if record.evidence_count >= minimum_evidence
    ]
    count = min(max(1, len(values) // 8), len(eligible))
    ordered = sorted(eligible, key=lambda record: record.selection_key)
    return {record.index for record in ordered[:count]}


def _promising_tier_divisor(seed_count: int, *, minimum_evidence: int) -> int | None:
    if minimum_evidence <= seed_count < 8:
        return 2
    if 8 <= seed_count < 16:
        return 4
    if 16 <= seed_count < 32:
        return 8
    return None


def _selection_groups(
    records: tuple[SelectionRecord, ...] | list[SelectionRecord],
) -> dict[Any, SelectionRecord]:
    groups: dict[Any, SelectionRecord] = {}
    for record in records:
        current = groups.get(record.group_key)
        if current is None:
            groups[record.group_key] = record
            continue
        if (
            current.evidence_count != record.evidence_count
            or current.objective_key != record.objective_key
            or current.candidate_tie_key != record.candidate_tie_key
        ):
            raise ValueError("selection group records must share aggregate metadata")
        if record.index < current.index:
            groups[record.group_key] = record
    return groups


def promising_group_keys(
    records: tuple[SelectionRecord, ...] | list[SelectionRecord],
    *,
    policy_id: str | None,
    minimum_evidence: int = 4,
) -> set[Any]:
    if policy_id is None:
        return set()
    if policy_id != LEGACY_PROMISING_POLICY:
        raise ValueError(f"unsupported promising allocation policy: {policy_id}")

    groups = _selection_groups(records)
    ranked = sorted(
        (
            record
            for record in groups.values()
            if record.evidence_count >= minimum_evidence
        ),
        key=lambda record: (
            record.objective_key,
            record.candidate_tie_key,
        ),
    )
    rank_by_group = {
        record.group_key: rank
        for rank, record in enumerate(ranked)
    }
    promising: set[Any] = set()
    for record in ranked:
        divisor = _promising_tier_divisor(
            record.evidence_count,
            minimum_evidence=minimum_evidence,
        )
        if divisor is None:
            continue
        cutoff = max(1, len(ranked) // divisor)
        if rank_by_group[record.group_key] < cutoff:
            promising.add(record.group_key)
    return promising


def select_promising_parent_index(
    records: tuple[SelectionRecord, ...] | list[SelectionRecord],
    *,
    policy_id: str | None,
    minimum_evidence: int = 4,
    excluded_group: Any | None = None,
) -> int | None:
    candidates = [
        record
        for record in records
        if excluded_group is None or record.group_key != excluded_group
    ]
    promising = promising_group_keys(
        candidates,
        policy_id=policy_id,
        minimum_evidence=minimum_evidence,
    )
    if not promising:
        return None
    representatives = _selection_groups(candidates)
    selected = [
        record
        for group_key, record in representatives.items()
        if group_key in promising
    ]
    return min(
        selected,
        key=lambda record: (
            record.evidence_count,
            record.objective_key,
            record.candidate_tie_key,
            record.index,
        ),
    ).index


def prune_selection_indices(
    records: tuple[SelectionRecord, ...] | list[SelectionRecord],
    *,
    protected: set[int] | None = None,
) -> set[int]:
    values = [
        record
        for record in records
        if record.evidence_mature or record.absolute_failure
    ]
    result = {
        record.index
        for record in values
        if record.absolute_failure
    }
    live = [record for record in values if not record.absolute_failure]
    if not live:
        return result

    category_protected = protected or set()
    recent_by_record = {
        record.index: tuple(
            int(window).bit_count()
            for window in record.growth_windows[-4:]
        )
        for record in live
    }
    complete = [
        record
        for record in live
        if len(recent_by_record[record.index]) == 4
    ]
    if not complete:
        return result

    medians = tuple(
        median(recent_by_record[record.index][offset] for record in complete)
        for offset in range(4)
    )
    thresholds = tuple(int(value) >> 1 for value in medians)
    for record in complete:
        if record.index in category_protected:
            continue
        recent_windows = recent_by_record[record.index]
        if all(
            window < threshold
            for window, threshold in zip(recent_windows, thresholds)
        ):
            result.add(record.index)
    return result


def select_prune_target_index(
    records: tuple[SelectionRecord, ...] | list[SelectionRecord],
    pruned_indices: set[int],
) -> int:
    candidates = [
        record
        for record in records
        if record.index in pruned_indices
    ]
    if not candidates:
        raise ValueError("prune target selection requires a pruned record")
    return max(candidates, key=lambda record: record.selection_key).index


def build_seed_evidence_replacement(
    *,
    plan: SearchPlan,
    registry: SearchRegistry,
    parent_candidate: CandidateValues,
    target_index: int,
    parent_index: int,
    seed: int,
    parent_evidence_mature: bool,
) -> CandidateReplacement:
    resolved_parent = resolve_candidate(plan, registry, parent_candidate)
    return CandidateReplacement(
        target_index=int(target_index),
        seed=int(seed),
        candidate_values=parent_candidate,
        resolved_candidate=resolved_parent,
        parent_candidate_identity=resolved_parent.candidate_identity,
        parent_index=int(parent_index),
        allocation_reason="seed_evidence",
        evidence_mature=bool(parent_evidence_mature),
    )


def build_mutation_replacement(
    *,
    plan: SearchPlan,
    registry: SearchRegistry,
    parent_candidate: CandidateValues,
    mutation: ScalarMutationResult,
    target_index: int,
    parent_index: int,
    seed: int,
) -> CandidateReplacement:
    resolved_parent = resolve_candidate(plan, registry, parent_candidate)
    return CandidateReplacement(
        target_index=int(target_index),
        seed=int(seed),
        candidate_values=mutation.candidate_values,
        resolved_candidate=mutation.resolved_candidate,
        parent_candidate_identity=resolved_parent.candidate_identity,
        parent_index=int(parent_index),
        allocation_reason="mutation_child",
        evidence_mature=False,
        mutation_dimension=mutation.dimension_id,
        mutation_direction=mutation.direction,
    )


def _matched_evidence_key(
    plan: SearchPlan,
    registry: SearchRegistry,
    candidate: CandidateValues,
    stratum: ResolvedComparisonStratum,
) -> str:
    resolved = resolve_candidate(plan, registry, candidate)
    grouped = {dimension_id for dimension_id, _ in stratum.values}
    payload = {
        "scalars": {
            key: resolved.universe_spec.scalar_values[key]
            for key in sorted(resolved.universe_spec.scalar_values)
            if key not in grouped
        },
        "rules": {
            key: resolved.universe_spec.rule_values[key]
            for key in sorted(resolved.universe_spec.rule_values)
            if key not in grouped
        },
    }
    return _digest(payload)


def allocate_matched_evidence_seed(
    *,
    plan: SearchPlan,
    registry: SearchRegistry,
    target_candidate: CandidateValues,
    assignments: tuple[EvidenceSeedAssignment, ...],
    allocation_cursor: int,
) -> EvidenceSeedDecision:
    """Choose evidence seed using the declared matched-evidence policy."""

    if allocation_cursor < 0:
        raise ValueError("allocation_cursor must be non-negative")
    plan.validate(registry)
    target_stratum = resolve_candidate_stratum(plan, registry, target_candidate)
    if target_stratum.matched_evidence_policy != "legacy_matched_seed":
        raise ValueError(
            "unsupported matched-evidence policy: "
            f"{target_stratum.matched_evidence_policy}"
        )
    target_key = _matched_evidence_key(
        plan,
        registry,
        target_candidate,
        target_stratum,
    )

    occupied_target: set[int] = set()
    matched_other: set[int] = set()
    for assignment in assignments:
        assignment_stratum = resolve_candidate_stratum(
            plan,
            registry,
            assignment.candidate_values,
        )
        seed = int(assignment.seed)
        if assignment_stratum.values == target_stratum.values:
            occupied_target.add(seed)
            continue
        if _matched_evidence_key(
            plan,
            registry,
            assignment.candidate_values,
            assignment_stratum,
        ) == target_key:
            matched_other.add(seed)

    reusable = sorted(seed for seed in matched_other if seed not in occupied_target)
    if reusable:
        return EvidenceSeedDecision(
            seed=reusable[0],
            next_allocation_cursor=allocation_cursor,
            matched_existing_evidence=True,
        )

    seed = int(allocation_cursor)
    while seed in occupied_target:
        seed += 1
    return EvidenceSeedDecision(
        seed=seed,
        next_allocation_cursor=seed + 1,
        matched_existing_evidence=False,
    )


def evidence_tier_target(allocation_policy: str, evidence_count: int) -> int:
    """Return the next real-slot evidence tier for the declared legacy policy."""

    if allocation_policy != LEGACY_PROMISING_POLICY:
        raise ValueError(f"unsupported allocation policy: {allocation_policy}")
    count = int(evidence_count)
    if count < LEGACY_EVIDENCE_SEEDS:
        raise ValueError(
            f"evidence_count must start at {LEGACY_EVIDENCE_SEEDS}"
        )
    return min(LEGACY_SLOTS_PER_STRATUM, count * 2)


def _adjacent_binary_value(
    definition: ScalarDimension,
    current: int,
    *,
    direction: int,
) -> int:
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1")
    if not isinstance(current, int) or isinstance(current, bool):
        raise ValueError("adjacent_binary requires an integer scalar")
    if direction > 0:
        next_value = 1 if current == 0 else current * 2
    else:
        next_value = 0 if current <= 1 else current // 2
    if definition.lower is not None:
        next_value = max(int(definition.lower), next_value)
    if definition.upper is not None:
        next_value = min(int(definition.upper), next_value)
    return next_value


def scalar_mutation_directions(
    *,
    plan: SearchPlan,
    registry: SearchRegistry,
    candidate: CandidateValues,
    dimension_id: str,
    base_config: PhysicsConfig | None = None,
) -> tuple[int, ...]:
    """Return legal adjacent-binary directions for one active searchable scalar."""

    plan.validate(registry)
    declaration = plan.search.get(dimension_id)
    if declaration is None:
        raise ValueError(f"dimension is not searchable in SearchPlan: {dimension_id}")
    if declaration.strategy != "adjacent_binary":
        raise ValueError(
            f"unsupported scalar mutation strategy for Phase D1: {declaration.strategy}"
        )
    definition = registry.scalar_dimensions.get(dimension_id)
    if definition is None:
        raise ValueError(f"unknown scalar dimension: {dimension_id}")

    resolved_current = resolve_candidate(plan, registry, candidate)
    if dimension_id not in resolved_current.active_dimensions:
        return ()
    current = int(resolved_current.universe_spec.scalar_values[dimension_id])

    valid: list[int] = []
    for direction in (-1, 1):
        next_value = _adjacent_binary_value(
            definition,
            current,
            direction=direction,
        )
        if next_value == current:
            continue
        try:
            definition.validate_value(next_value)
        except ValueError:
            continue
        if declaration.domain != "registered" and next_value not in declaration.domain:
            continue

        scalar_values = dict(candidate.scalars)
        scalar_values[dimension_id] = next_value
        mutated_values = CandidateValues(
            scalars=scalar_values,
            rules=candidate.rules,
        )
        try:
            resolved_next = resolve_candidate(plan, registry, mutated_values)
            resolved_next.universe_spec.to_physics_config(base_config)
        except ValueError:
            continue
        if resolved_next.candidate_identity == resolved_current.candidate_identity:
            continue
        valid.append(direction)
    return tuple(valid)


def mutate_scalar_candidate(
    *,
    plan: SearchPlan,
    registry: SearchRegistry,
    candidate: CandidateValues,
    dimension_id: str,
    direction: int,
    base_config: PhysicsConfig | None = None,
) -> ScalarMutationResult:
    """Mutate one active scalar through its registered adjacent-binary strategy."""

    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1")
    valid = scalar_mutation_directions(
        plan=plan,
        registry=registry,
        candidate=candidate,
        dimension_id=dimension_id,
        base_config=base_config,
    )
    if direction not in valid:
        raise ValueError(
            f"mutation direction {direction} does not produce a valid adjacent value"
        )

    definition = registry.scalar_dimensions[dimension_id]
    resolved_current = resolve_candidate(plan, registry, candidate)
    before = int(resolved_current.universe_spec.scalar_values[dimension_id])
    after = _adjacent_binary_value(
        definition,
        before,
        direction=direction,
    )
    scalar_values = dict(candidate.scalars)
    scalar_values[dimension_id] = after
    mutated_values = CandidateValues(
        scalars=scalar_values,
        rules=candidate.rules,
    )
    resolved_next = resolve_candidate(plan, registry, mutated_values)
    resolved_next.universe_spec.to_physics_config(base_config)
    return ScalarMutationResult(
        dimension_id=dimension_id,
        direction=direction,
        before=before,
        after=after,
        candidate_values=mutated_values,
        resolved_candidate=resolved_next,
    )


def legacy_candidate_values(
    genome: UniverseGenome,
    category: str,
) -> CandidateValues:
    if category not in LEGACY_LATENT_OPERATORS:
        raise ValueError(f"unsupported legacy latent operator: {category}")
    return CandidateValues(
        scalars=genome.to_dict(),
        rules={"latent_operator": category},
    )


def legacy_mutation_plan_for_base_config(
    base_config: PhysicsConfig,
    *,
    base_seed: int = 0,
) -> SearchPlan:
    """Preserve explicit fixed research physics without making it searchable."""

    plan = legacy_search_plan(base_seed=base_seed)
    fixed = dict(plan.fixed)
    for dimension_id in LEGACY_TRACE_FIXED:
        fixed[dimension_id] = int(getattr(base_config, dimension_id))
    return replace(plan, fixed=fixed)


def legacy_mutation_directions(
    *,
    plan: SearchPlan,
    registry: SearchRegistry,
    candidate: CandidateValues,
    dimension_id: str,
    base_config: PhysicsConfig | None = None,
) -> tuple[int, ...]:
    return scalar_mutation_directions(
        plan=plan,
        registry=registry,
        candidate=candidate,
        dimension_id=dimension_id,
        base_config=base_config,
    )


def mutate_legacy_candidate(
    *,
    genome: UniverseGenome,
    category: str,
    dimension_id: str,
    direction: int,
    base_config: PhysicsConfig,
    registry: SearchRegistry | None = None,
    plan: SearchPlan | None = None,
) -> ScalarMutationResult:
    resolved_registry = registry or build_default_search_registry()
    resolved_plan = plan or legacy_mutation_plan_for_base_config(base_config)
    return mutate_scalar_candidate(
        plan=resolved_plan,
        registry=resolved_registry,
        candidate=legacy_candidate_values(genome, category),
        dimension_id=dimension_id,
        direction=direction,
        base_config=base_config,
    )


def build_default_search_registry() -> SearchRegistry:
    """Return the registered Phase C universe-physics surface."""

    default_genome = UniverseGenome.default()
    scalars: dict[str, ScalarDimension] = {}
    for dimension_id in UNIVERSE_GENOME_FIELDS:
        lower, upper = GENOME_BOUNDS[dimension_id]
        scalars[dimension_id] = ScalarDimension(
            dimension_id=dimension_id,
            physics_field=_GENOME_PHYSICS_FIELDS[dimension_id],
            value_type="int",
            default=int(getattr(default_genome, dimension_id)),
            lower=int(lower),
            upper=int(upper),
            strategy_ids=("fixed", "adjacent_binary"),
        )

    for dimension_id, (lower, upper) in _TRACE_BOUNDS.items():
        scalars[dimension_id] = ScalarDimension(
            dimension_id=dimension_id,
            physics_field=dimension_id,
            value_type="int",
            default=LEGACY_TRACE_FIXED[dimension_id],
            lower=lower,
            upper=upper,
            strategy_ids=("fixed", "adjacent_binary"),
        )

    rules = {
        "latent_operator": RuleDimension(
            dimension_id="latent_operator",
            physics_field="latent_operator",
            variants=LEGACY_LATENT_OPERATORS,
            default_variant="masked_copy",
            strategy_ids=("fixed", "finite_variant", "stratified_fixed"),
        )
    }
    return SearchRegistry(
        scalar_dimensions=scalars,
        rule_dimensions=rules,
    )


def legacy_search_plan(*, base_seed: int = 0) -> SearchPlan:
    """Canonical declarative representation of accepted Phase 5 search."""

    return SearchPlan(
        schema_version=1,
        plan_id="phase5_legacy",
        plan_version=1,
        population_size=LEGACY_POPULATION_SIZE,
        fixed=dict(LEGACY_TRACE_FIXED),
        search={
            dimension_id: ScalarSearch("adjacent_binary", "registered")
            for dimension_id in UNIVERSE_GENOME_FIELDS
        },
        rules={
            "latent_operator": RuleSearch(
                LEGACY_LATENT_OPERATORS,
                "stratified_fixed",
            )
        },
        strata=(
            ComparisonStratum(
                group_by=("latent_operator",),
                selection_scope="within",
                allocation_policy=LEGACY_PROMISING_POLICY,
                matched_evidence_policy="legacy_matched_seed",
            ),
        ),
        objective_profile_id=LEGACY_OBJECTIVE_PROFILE_ID,
        objective_profile_version=LEGACY_OBJECTIVE_PROFILE_VERSION,
        search_cohort_policy="legacy_optimizer_evidence",
        validation_cohort_policy="none",
        scheduler_base_seed=int(base_seed),
        scheduler_policy="legacy_phase5",
        initialization_policy="legacy_phase5_eight",
    )


def legacy_initial_scheduler(plan: SearchPlan) -> dict[str, Any]:
    """Static legacy scheduler state represented by the canonical plan."""

    scheduler: dict[str, Any] = {
        "mutation_cursor": 0,
        "allocation_cursor": int(plan.scheduler_base_seed) + 32,
        "replacement_count": 0,
        "evaluation_count": 0,
        "promising_policy": LEGACY_PROMISING_POLICY,
    }
    variants = plan.rules["latent_operator"].variants
    for variant in variants:
        scheduler[f"allocation_mode_cursor:{variant}"] = 0
    return scheduler


def build_legacy_initial_population(
    *,
    base_seed: int,
    base_config: PhysicsConfig,
    registry: SearchRegistry | None = None,
    plan: SearchPlan | None = None,
) -> tuple[ResolvedPopulationSlot, ...]:
    """Build the legacy 128-slot static population through the generalized model."""

    resolved_registry = registry or build_default_search_registry()
    resolved_plan = plan or legacy_search_plan(base_seed=base_seed)
    resolved_plan.validate(resolved_registry)
    if resolved_plan.plan_id != "phase5_legacy":
        raise ValueError("legacy population builder requires phase5_legacy plan")
    if resolved_plan.population_size != LEGACY_POPULATION_SIZE:
        raise ValueError("legacy plan population_size must be 128")
    if resolved_plan.scheduler_base_seed != int(base_seed):
        raise ValueError("legacy plan/base_seed mismatch")
    if resolved_plan.initialization_policy != "legacy_phase5_eight":
        raise ValueError("legacy plan initialization policy mismatch")

    variants = resolved_plan.rules["latent_operator"].variants
    if tuple(variants) != LEGACY_LATENT_OPERATORS:
        raise ValueError("legacy latent operator variants/order must remain exact")

    result: list[ResolvedPopulationSlot] = []
    index = 0
    for category in variants:
        for genome_id, genome in enumerate(UniverseGenome.initial_population()):
            for seed_offset in range(LEGACY_EVIDENCE_SEEDS):
                seed = int(base_seed) + (genome_id * LEGACY_EVIDENCE_SEEDS) + seed_offset
                candidate = CandidateValues(
                    scalars=genome.to_dict(),
                    rules={"latent_operator": category},
                )
                resolved_candidate = resolve_candidate(
                    resolved_plan,
                    resolved_registry,
                    candidate,
                )
                effective = resolved_candidate.universe_spec.to_physics_config(
                    base_config
                )
                state = create_universe(seed=seed, config=effective)
                result.append(
                    ResolvedPopulationSlot(
                        index=index,
                        seed=seed,
                        candidate_values=candidate,
                        resolved_candidate=resolved_candidate,
                        state=state,
                        legacy_genome_values=genome.to_dict(),
                        rule_values={"latent_operator": category},
                    )
                )
                index += 1

    if len(result) != resolved_plan.population_size:
        raise RuntimeError(
            f"legacy initialization produced {len(result)} slots, "
            f"expected {resolved_plan.population_size}"
        )
    return tuple(result)
