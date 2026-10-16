"""O2-3 #388: source-only eligible Outer selection/mutation, never Inner physics.

Only a proposed SYNTHETIC selection shape. This module cannot authenticate
GitHub original job bytes or a future training manifest, run a universe,
claim a winning physical parameter, nor issue a new independent Seed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from core.physics import PhysicsConfig
from search.outer_search import (
    CandidateValues, SelectionRecord, build_mutation_replacement,
    mutate_scalar_candidate, protected_selection_indices,
    prune_selection_indices, select_parent_index,
)
from research.outer_l3_inner_adapter_388 import resolve_inner_execution_input
from research.outer_l3_memory_search_386 import (
    _protocol, build_outer_l3_registry, build_outer_l3_search_plan,
    screen_real_outer_evidence,
)

EXPOSED_ORIGINAL_SEEDS = frozenset((544, 545))
SYNTHETIC_ONLY = "SYNTHETIC_STRUCTURE_ONLY_NOT_SOURCE_AUTHENTICATED"


@dataclass(frozen=True)
class ProposedOuterSlot:
    index: int
    candidate: CandidateValues
    case_seed_ids: tuple[int, ...]
    evidence: Mapping[str, object]
    evidence_mature: bool = False
    absolute_failure: bool = False
    growth_windows: tuple[int, ...] = ()


@dataclass(frozen=True)
class ProposedOuterRanking:
    """No real population result; numbers are pure nonattested test proposals."""

    records: tuple[SelectionRecord, ...]
    rejected: tuple[tuple[int, str], ...]
    operators: tuple[tuple[int, str], ...]
    identities: tuple[tuple[int, str], ...]
    candidate_slots: tuple[ProposedOuterSlot, ...]
    approved_seed_ids: tuple[int, ...]
    status: str = SYNTHETIC_ONLY
    source_provenance_verified: bool = False
    actual_physics_executed: bool = False
    independent_validation: bool = False
    learning_claim: bool = False
    winner_fixed: bool = False


def _training_seeds(seeds: tuple[int, ...]) -> tuple[int, ...]:
    """Only syntactically approve a hypothetical h0-only manifest for PR tests.

    True cohort h0 eligibility and exclusion MUST be externally authenticated
    before any actual physical experiment is permitted.
    """
    p = _protocol()
    if type(seeds) is not tuple or len(seeds) < p["objective"]["minimum_evidence_cases"]:
        raise ValueError("full explicit training manifest required")
    if (any(type(seed) is not int or seed < 0 for seed in seeds)
            or tuple(sorted(set(seeds))) != seeds):
        raise ValueError("training seeds must be distinct sorted nonnegative integers")
    lo, hi = p["cohorts"]["no_reserved_phase_h_seed_range"]
    if any(lo <= seed <= hi or seed in EXPOSED_ORIGINAL_SEEDS for seed in seeds):
        raise ValueError("reserved Phase H or exposed original seed cannot be training evidence")
    return seeds


def proposal_from_screened_cases(
    slots: tuple[ProposedOuterSlot, ...], *,
    training_seed_manifest: tuple[int, ...],
    base_config: PhysicsConfig,
) -> ProposedOuterRanking:
    """Supply only rankable screened cases to the existing generic selector.

    Exact training seed IDs must match across every candidate. Evidence and
    h0-only cohort claims are synthetic caller-supplied and NOT attested here.
    """
    p = _protocol()
    ids = _training_seeds(training_seed_manifest)
    if (not isinstance(base_config, PhysicsConfig)
            or type(slots) is not tuple or
            not 1 <= len(slots) <= p["population"]["capacity_slots"]):
        raise ValueError("bounded slots and native physics base configuration required")
    seen = set()
    records, rejected, operators, identities = [], [], [], []
    for slot in slots:
        if (type(slot) is not ProposedOuterSlot
                or type(slot.index) is not int
                or not 0 <= slot.index < p["population"]["capacity_slots"]
                or slot.index in seen):
            raise ValueError("unique bounded Outer slot indices required")
        seen.add(slot.index)
        if slot.case_seed_ids != ids:
            raise ValueError("all compared candidates require identical manifest seeds")
        if (type(slot.evidence) is not dict
                or slot.evidence.get("distinct_h0_qualified_search_seeds") != len(ids)):
            raise ValueError("case count and approved matched seed IDs must agree")
        if type(slot.absolute_failure) is not bool or type(slot.evidence_mature) is not bool:
            raise ValueError("invalid source-only status flag")
        if (type(slot.growth_windows) is not tuple or
                any(type(g) is not int or g < 0 for g in slot.growth_windows)):
            raise ValueError("invalid source-only growth windows")

        envelope = resolve_inner_execution_input(
            slot.candidate.scalars, slot.candidate.rules,
            base_config=base_config,
        )
        check = screen_real_outer_evidence(
            slot.evidence, config=envelope.input.to_physics_config(),
        )
        op = slot.candidate.rules["latent_operator"]
        operators.append((slot.index, op))
        identities.append((slot.index, envelope.candidate_identity))
        if slot.absolute_failure or not check.rankable:
            rejected.append((
                slot.index,
                "ABSOLUTE_FAILURE" if slot.absolute_failure else check.classification,
            ))
            continue
        records.append(SelectionRecord(
            index=slot.index, group_key=envelope.candidate_identity,
            objective_key=check.objective_key,
            evidence_count=len(ids),
            candidate_tie_key=envelope.candidate_identity,
            growth_windows=slot.growth_windows,
            evidence_mature=slot.evidence_mature,
            absolute_failure=False,
        ))
    return ProposedOuterRanking(
        records=tuple(sorted(records, key=lambda x: x.index)),
        rejected=tuple(sorted(rejected)),
        operators=tuple(sorted(operators)),
        identities=tuple(sorted(identities)),
        candidate_slots=tuple(sorted(slots, key=lambda x: x.index)),
        approved_seed_ids=ids,
    )


def proposed_same_operator_parent(
    ranking: ProposedOuterRanking, *, target_index: int,
) -> int:
    """Parent must be physically screened/rankable in target operator stratum."""
    operators = dict(ranking.operators)
    if type(target_index) is not int or target_index not in operators:
        raise ValueError("target must belong to this proposed Outer population")
    valid = [r for r in ranking.records
             if operators[r.index] == operators[target_index]]
    return select_parent_index(
        valid, excluded_index=target_index,
        minimum_evidence=_protocol()["objective"]["minimum_evidence_cases"],
    )


def proposed_prune_indices(ranking: ProposedOuterRanking) -> frozenset[int]:
    """Never promote an invalid case into the existing pruning/protection pool."""
    valid = list(ranking.records)
    protected = protected_selection_indices(valid)
    return frozenset(prune_selection_indices(valid, protected=protected))


def proposed_mutation_from_parent(
    ranking: ProposedOuterRanking, *, target_index: int,
    dimension_id: str, direction: int, seed: int,
    base_config: PhysicsConfig,
):
    """An optional SOURCE-ONLY child proposal, not a run or selected winner."""
    parent = proposed_same_operator_parent(ranking, target_index=target_index)
    if type(seed) is not int or seed not in ranking.approved_seed_ids:
        raise ValueError("mutation child may only use a frozen training seed ID")
    source = next(s for s in ranking.candidate_slots if s.index == parent)
    plan = build_outer_l3_search_plan()
    registry = build_outer_l3_registry()
    if dimension_id not in plan.search:
        raise ValueError("mutation must use a preregistered numeric physics gene")
    mutation = mutate_scalar_candidate(
        plan=plan, registry=registry, candidate=source.candidate,
        dimension_id=dimension_id, direction=direction,
        base_config=base_config,
    )
    return build_mutation_replacement(
        plan=plan, registry=registry,
        parent_candidate=source.candidate, mutation=mutation,
        target_index=target_index, parent_index=parent, seed=seed,
    )
