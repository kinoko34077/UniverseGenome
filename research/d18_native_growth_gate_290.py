"""D18.0 #290: source-native READ-ONLY pruning-gate witness, never an experiment.

Native rules are called unchanged. Synthetic records prove logical reachability,
not reachability under the physics, actual E2 selection or any learning claim.
"""
from __future__ import annotations

from statistics import median
from typing import Sequence

from core.population import CATEGORY_OPERATORS
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer
from search.outer_search import (
    SelectionRecord,
    protected_selection_indices,
    prune_selection_indices,
    select_prune_target_index,
)

REQUIRED_PER_CATEGORY = 32


def inspect_native_category(
    records: Sequence[SelectionRecord], *, category: str
) -> dict:
    """Use the EXACT native protection/prune/target functions; never mutate."""
    values = tuple(records)
    if category not in CATEGORY_OPERATORS or len(values) != REQUIRED_PER_CATEGORY:
        raise ValueError("D18 exactly one original 32-slot native category required")
    if any(
        not isinstance(record, SelectionRecord)
        or not isinstance(record.group_key, tuple)
        or not record.group_key
        or record.group_key[0] != category
        for record in values
    ):
        raise ValueError("D18 mixed or invalid native category records")
    indices = [r.index for r in values]
    if indices != sorted(set(indices)):
        raise ValueError("D18 native category records must be original ordered distinct indices")

    # These are the accepted native functions, NOT reimplementations.
    protected = protected_selection_indices(values)
    pruned = prune_selection_indices(values, protected=protected)
    failures = {r.index for r in values if r.absolute_failure}
    if not failures.issubset(pruned):
        raise AssertionError("source-native absolute failures were silently dropped")

    healthy_complete = [
        r for r in values
        if r.evidence_mature and not r.absolute_failure and len(r.growth_windows[-4:]) == 4
    ]
    scores = {
        r.index: tuple(int(w).bit_count() for w in r.growth_windows[-4:])
        for r in healthy_complete
    }
    medians = (
        tuple(median(scores[r.index][position] for r in healthy_complete)
              for position in range(4))
        if healthy_complete else ()
    )
    thresholds = tuple(int(x) >> 1 for x in medians)
    expected_growth = {
        r.index for r in healthy_complete
        if r.index not in protected
        and all(score < threshold for score, threshold
                in zip(scores[r.index], thresholds))
    }
    actual_growth = pruned - failures
    if actual_growth != expected_growth:
        raise AssertionError("read-only witness differs from accepted native pruning")
    target = select_prune_target_index(values, pruned) if pruned else None
    target_record = next((r for r in values if r.index == target), None)

    return {
        "category": category,
        "occupied": len(values),
        "complete_nonfailure_count": len(healthy_complete),
        "complete_healthy_indices": [r.index for r in healthy_complete],
        "complete_healthy_bitcounts": {str(k): list(v) for k, v in sorted(scores.items())},
        "median_growth_bitcounts": list(medians),
        "native_half_median_thresholds": list(thresholds),
        "protected_indices": sorted(protected),
        "absolute_failure_indices": sorted(failures),
        "native_pruned_indices": sorted(pruned),
        "growth_only_candidate_indices_E1": sorted(actual_growth),
        "native_predicted_target_index": target,
        "native_predicted_target_class": (
            "absolute_failure" if target_record is not None and target_record.absolute_failure
            else "growth_only" if target_record is not None else None
        ),
        "actual_native_retirement_E2": None,
        "physics_reachability_proven": False,
        "learning_claim": False,
    }


def inspect_native_preselection_state(opt: SteadyStateOptimizer) -> dict:
    """One genuine optimizer snapshot, observed without evaluation or selection.

    Does not use any new seed itself: the caller provides the fixed state.
    """
    if not isinstance(opt, SteadyStateOptimizer):
        raise TypeError("D18 requires existing canonical optimizer instance")
    before = digest(opt.to_snapshot())
    rows = {}
    for _stratum, local in opt._comparison_strata():
        if not local:
            raise ValueError("missing original comparison stratum")
        category = local[0].category
        rows[category] = inspect_native_category(
            opt._selection_records(local), category=category
        )
    after = digest(opt.to_snapshot())
    if before != after or set(rows) != set(CATEGORY_OPERATORS):
        raise AssertionError("D18 observer changed optimizer or lost original strata")
    return {
        "kind": "D18_ORIGINAL_NATIVE_READONLY_PRESELECTION_GATE_V1",
        "original_optimizer_generation": opt.generation,
        "original_selected_v7_sha256_before_after": before,
        "categories": rows,
        "native_state_unchanged": True,
        "physics_reachability_proven": False,
        "actual_native_retirement_E2": None,
        "learning_claim": False,
    }
