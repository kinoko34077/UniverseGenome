"""Declarative generalized Outer Search model and canonical legacy projection.

Phase C introduces representation/resolution only. The existing Phase 5 optimizer
continues to own mutation/allocation/selection until later gated checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
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
    scalar_values: Mapping[str, Any]
    rule_values: Mapping[str, str]
    active_dimensions: tuple[str, ...]
    physics_values: Mapping[str, Any]
    rule_physics_values: Mapping[str, Any]
    candidate_identity: str
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
            "active_dimensions": list(self.active_dimensions),
            "physics_values": {
                key: self.physics_values[key] for key in sorted(self.physics_values)
            },
            "rule_physics_values": {
                key: self.rule_physics_values[key]
                for key in sorted(self.rule_physics_values)
            },
            "candidate_identity": self.candidate_identity,
        }


@dataclass(frozen=True)
class ResolvedPopulationSlot:
    index: int
    seed: int
    candidate_values: CandidateValues
    resolved_spec: ResolvedUniverseSpec
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
) -> ResolvedUniverseSpec:
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

    return ResolvedUniverseSpec(
        scalar_values=scalar_values,
        rule_values=rule_values,
        active_dimensions=active_dimensions,
        physics_values=physics_values,
        rule_physics_values=rule_physics_values,
        candidate_identity=candidate_identity,
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
                resolved_spec = resolve_candidate(
                    resolved_plan,
                    resolved_registry,
                    candidate,
                )
                effective = resolved_spec.to_physics_config(base_config)
                state = create_universe(seed=seed, config=effective)
                result.append(
                    ResolvedPopulationSlot(
                        index=index,
                        seed=seed,
                        candidate_values=candidate,
                        resolved_spec=resolved_spec,
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
