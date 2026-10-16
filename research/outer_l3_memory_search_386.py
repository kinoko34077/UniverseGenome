"""#386 SOURCE-ONLY: multi-axis Outer L3 search plan + strict evidence eligibility.

This module never creates an Inner Universe or executes native physics.
A declaration is not an integrated Optimizer runner, a selected winner, or
independent evidence of inherited memory. Reserved seeds cannot run here.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping

from core.physics import PhysicsConfig
from search.outer_search import (
    CandidateValues, ComparisonStratum, ObjectiveMetric, ObjectiveProfile,
    RuleSearch, ScalarSearch, SearchPlan, SearchRegistry,
    build_default_search_registry, resolve_candidate,
)

PROTOCOL_PATH = Path("research/outer_l3_search_protocol_386.json")
SCHEMA = "UG_OUTER_L3_386_SEARCH_SPACE_OBJECTIVE_V1"


def _protocol() -> dict:
    p = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if (p["schema"] != SCHEMA or p["issue"] != 386
            or p["mode"] != "SOURCE_ONLY_NOT_AUTHORIZED_TO_RUN_NEW_ORIGINAL_WORLD"
            or p["effectful_search_executed"] is not False
            or p["winning_candidate_selected"] is not False
            or p["heldout_used"] is not False
            or p["learning_claim"] is not False
            or p["cohorts"]["manifest_required_before_execution"] is not True
            or p["cohorts"]["no_reserved_phase_h_seed_range"] != [96, 159]
            or p["backward_compatibility"]["preserve_legacy_optimizer_exact"] is not True):
        raise ValueError("refuse to change source-only cohort and science boundary")
    if len(p["search_domains"]) < 10 or len(p["rule_domains"]) < 1:
        raise ValueError("not the preregistered multi-axis Outer search")
    return p


def build_outer_l3_registry() -> SearchRegistry:
    """Extend ONLY the research registry with a named objective, not production."""
    p = _protocol()
    base = build_default_search_registry()
    spec = p["objective"]
    metrics = tuple(
        ObjectiveMetric(metric_id=m, direction="maximize", comparison=True)
        for m in spec["scientific_ranking"]
    ) + (ObjectiveMetric(metric_id=spec["resource_tiebreaker"],
                         direction="minimize", comparison=True),)
    profile = ObjectiveProfile(
        profile_id=spec["id"], version=spec["version"], metrics=metrics,
        minimum_evidence=spec["minimum_evidence_cases"],
        tie_breakers=("candidate_identity",), invalid_evidence_policy="reject",
        negative_control_fields=tuple(spec["hard_validity"]),
        negative_control_policy="gate",
        short_health_policy="phase5_short_health_v1",
        failure_policy="phase5_failure_v1", response_window_limit=4,
    )
    return SearchRegistry(
        scalar_dimensions=dict(base.scalar_dimensions),
        rule_dimensions=dict(base.rule_dimensions),
        objective_profiles={**base.objective_profiles, (profile.profile_id, profile.version): profile},
        schema_version=base.schema_version,
    )


def build_outer_l3_search_plan() -> SearchPlan:
    """Create an Outer research plan with DOMAIN values, no chosen winner."""
    p = _protocol()
    registry = build_outer_l3_registry()
    domains = p["search_domains"]
    rules = p["rule_domains"]
    if (p.get("search_domain_mutation_invariant")
            != "each_sorted_adjacent_scalar_pair_has_bidirectional_existing_adjacent_binary_step"
            or p.get("search_domain_mutation_strategy") != "adjacent_binary_registered"):
        raise ValueError("reviewed Outer mutation reachability specification missing")
    # The accepted generic mutation helper doubles/halves a value (0->1).
    # Domains with holes such as 0,256 cannot be reached by candidate evolution.
    # Assert BOTH directions for every adjacent permitted scalar value.
    for dimension_id, values in domains.items():
        if values != sorted(set(values)) or len(values) < 2:
            raise ValueError(f"unordered/degenerate search domain: {dimension_id}")
        for left, right in zip(values, values[1:]):
            if ((1 if left == 0 else left * 2) != right
                    or (0 if right <= 1 else right // 2) != left):
                raise ValueError(f"disconnected candidate mutation domain: {dimension_id}")
    if (set(domains) != set(registry.scalar_dimensions)
            or set(rules) != set(registry.rule_dimensions)):
        raise ValueError("all current registered physics variables/rules must be declared")
    if (0 not in domains["noise_rate"] or 0 not in domains["fragmentation_base_probability"]
            or not any(x > 0 for x in domains["noise_rate"])
            or not any(x > 0 for x in domains["fragmentation_base_probability"])):
        raise ValueError("birth-disabled and birth-capable strata both required")
    plan = SearchPlan(
        schema_version=1,
        plan_id="outer_l3_multiaxis_research_386", plan_version=1,
        population_size=p["population"]["capacity_slots"],
        fixed={},
        search={k: ScalarSearch(strategy="adjacent_binary", domain=tuple(v))
                for k, v in domains.items()},
        rules={k: RuleSearch(variants=tuple(v), strategy="finite_variant")
               for k, v in rules.items()},
        strata=(ComparisonStratum(
            group_by=tuple(p["comparison"]["stratum"]), selection_scope="within",
            allocation_policy="tiered_category_rank",
            matched_evidence_policy=p["comparison"]["matched_seed_policy"]),),
        objective_profile_id=p["objective"]["id"],
        objective_profile_version=p["objective"]["version"],
        search_cohort_policy=p["cohorts"]["search_role"],
        validation_cohort_policy=p["cohorts"]["validation_role"],
        scheduler_base_seed=0,
        scheduler_policy="research_386_source_only_not_running",
        initialization_policy=p["population"]["initialization"],
    )
    plan.validate(registry)
    return plan


def resolve_outer_l3_candidate(
    scalars: Mapping[str, int], rules: Mapping[str, str],
    *, base_config: PhysicsConfig,
):
    """Resolve COMPLETE explicit candidate into physical config without stepping.

    The caller (future independently gated Outer adapter) supplies values.
    Neither zero, maximum nor first domain element is a preselected winner.
    """
    plan = build_outer_l3_search_plan()
    if set(scalars) != set(plan.search) or set(rules) != set(plan.rules):
        raise ValueError("candidate must explicitly declare EVERY search dimension and rule")
    candidate = CandidateValues(scalars=dict(scalars), rules=dict(rules))
    result = resolve_candidate(plan, build_outer_l3_registry(), candidate)
    physical = result.universe_spec.to_physics_config(base_config)
    if physical.fragmentation_rate and not physical.fragmentation_enabled:
        raise ValueError("fragmentation enabled flag must admit the searched physical rule")
    if physical.noise_rate < 0 or physical.fragmentation_rate < 0:
        raise ValueError("invalid native spawn setting")
    return result, physical


def birth_mode(config: PhysicsConfig) -> str:
    noise = config.noise_rate > 0
    fragmentation = config.fragmentation_enabled and config.fragmentation_rate > 0
    return (
        "both" if noise and fragmentation else
        "noise_only" if noise else
        "fragmentation_only" if fragmentation else "neither"
    )


@dataclass(frozen=True)
class ScreeningResult:
    classification: str
    rankable: bool
    objective_key: tuple[int, ...] | None
    learning_proven: bool = False
    independent_validation: bool = False


def screen_real_outer_evidence(
    evidence: Mapping[str, object], *,
    config: PhysicsConfig,
) -> ScreeningResult:
    """Fail closed on reported evidence; never creates/authenticates native logs.

    This is a contract gate only. A future genuine observer must authenticate
    actual event bytes, epoch free/spawn chronology and B/H sham provenance.
    """
    p = _protocol()
    if type(evidence) is not dict:
        raise ValueError("require a complete source-authenticated evidence mapping")
    spec = p["objective"]
    checks = spec["hard_validity"]
    if any(type(evidence.get(f)) is not bool for f in checks):
        raise ValueError("missing or malformed validity/negative controls")
    if not all(evidence[f] for f in checks):
        return ScreeningResult("INVALID_PROVENANCE_OR_NEGATIVE_CONTROL", False, None)
    if type(evidence.get("distinct_h0_qualified_search_seeds")) is not int:
        raise ValueError("missing matched distinct h0-only training case count")
    if evidence["distinct_h0_qualified_search_seeds"] < spec["minimum_evidence_cases"]:
        return ScreeningResult("INSUFFICIENT_MATCHED_H0_EVIDENCE", False, None)
    required_counts = (
        "real_post_h0_born_epoch_count",
        "native_selected_contact_count",
        "native_masked_source_contrast_count",
        "distinct_living_epoch_causal_candidate_count",
        *spec["scientific_ranking"],
        spec["resource_tiebreaker"],
    )
    if any(type(evidence.get(f)) is not int or evidence[f] < 0 for f in required_counts):
        raise ValueError("missing/invalid nonnegative genuine native evidence counts")
    if not (config.noise_rate > 0 or
            (config.fragmentation_enabled and config.fragmentation_rate > 0)):
        return ScreeningResult("BIRTH_DISABLED_BY_EFFECTIVE_PHYSICS", False, None)
    if evidence["real_post_h0_born_epoch_count"] == 0:
        return ScreeningResult("BIRTH_CAPABLE_BUT_UNREACHED", False, None)
    if (evidence["native_selected_contact_count"] == 0
            or evidence["native_masked_source_contrast_count"] == 0
            or evidence["distinct_living_epoch_causal_candidate_count"] == 0):
        return ScreeningResult("NO_AUTHENTIC_CROSS_EPOCH_CAUSAL_CANDIDATE", False, None)
    if evidence[spec["scientific_ranking"][0]] == 0:
        return ScreeningResult("NO_LONG_HORIZON_TEACHER_SPECIFIC_CONTRAST", False, None)
    rank = tuple(-evidence[k] for k in spec["scientific_ranking"]) + (
        evidence[spec["resource_tiebreaker"]],)
    return ScreeningResult("ELIGIBLE_FOR_TRAINING_RANKING_ONLY", True, rank)
