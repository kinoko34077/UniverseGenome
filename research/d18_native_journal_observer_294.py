"""D18.1 read-only E1 / E2 observer for an ACTUALLY COMPLETE D15 native round.

No evaluator, no science launcher, no seed allocation. Reconstructs the 128
evaluated PRE-selection slots from checksum-chained D15 patches and compares
the ORIGINAL native pruning witness with actual committed prune-history.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from research.d15_sparse_recovery_213 import JournalIntegrityError, SparseEvaluationJournal
from research.d16_native_journal_observer_217 import observe_committed_round
from research.d18_native_growth_gate_290 import inspect_native_preselection_state
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer


def observe_completed_native_round(root: Path, *, source_commit: str) -> dict[str, Any]:
    """Observe without ever stepping, rewinding, or changing authoritative state."""
    # The accepted D16 observer first cryptographically verifies the full
    # genuine native D15 journal and source-bound one-time selected state.
    source = observe_committed_round(root, source_commit=source_commit)
    journal = SparseEvaluationJournal.open(Path(root), source_commit=source_commit)
    view = journal.recover()
    if (view.read_only or not view.final_committed or not view.evaluation_complete
            or view.next_index != 128 or view.final_snapshot is None):
        raise JournalIntegrityError("D18 cannot observe incomplete or salvaged native round")

    evaluated = SteadyStateOptimizer.from_snapshot(view.snapshot)
    selected = SteadyStateOptimizer.from_snapshot(view.final_snapshot)
    original_pre_sha = digest(evaluated.to_snapshot())
    selected_sha = digest(selected.to_snapshot())
    witness = inspect_native_preselection_state(evaluated)
    if (source["source_commit"] != source_commit
            or source["evaluated_preselect_v7_sha256"] != original_pre_sha
            or source["selected_post_v7_sha256"] != selected_sha
            or source["before_optimizer_generation"] != evaluated.generation
            or source["selected_optimizer_generation"] != selected.generation
            or witness["original_selected_v7_sha256_before_after"] != original_pre_sha
            or source["evaluated_native_worlds"] != 128
            or not source["d15_journal_chain_verified"]
            or not source["original_selected_once_proven_by_D15_final"]
            or not source["read_only"]
            or source["learning_claim"]):
        raise JournalIntegrityError("D18 source-bound native snapshot/observer mismatch")

    events = source["native_retirements"]
    e2_events = []
    categories = {}
    for category, entry in witness["categories"].items():
        original = source["categories"][category]
        native_pruned = entry["native_pruned_indices"]
        if (native_pruned != original["native_eligible_prune_indices"]
                or len(entry["absolute_failure_indices"]) != original["absolute_failure_count"]
                or entry["complete_nonfailure_count"] != original["complete_nonfailure_count"]):
            raise JournalIntegrityError("D18 E1 preselection/native D16 category disagreement")
        retirement = [x for x in events if x["category"] == category]
        if len(retirement) > 1:
            raise JournalIntegrityError("D18 multiple native retirements in category")
        if bool(retirement) != bool(original["native_replacement_count"]):
            raise JournalIntegrityError("D18 original retirement/category accounting mismatch")
        if retirement:
            actual = retirement[0]
            predicted = entry["native_predicted_target_index"]
            if actual["index"] != predicted or predicted is None:
                raise JournalIntegrityError("D18 actual source target differs from preselection ranking")
            actual_is_growth = actual["retirement_reason"] == "growth_pruned"
            expected_is_growth = entry["native_predicted_target_class"] == "growth_only"
            if actual_is_growth != expected_is_growth:
                raise JournalIntegrityError("D18 actual native retirement misclassified as growth")
            if actual_is_growth:
                e2_events.append(actual)
        categories[category] = {
            **entry,
            "actual_native_retirement_E2": retirement[0] if retirement else None,
            "authentic_growth_pruned_E2": bool(
                retirement and retirement[0]["retirement_reason"] == "growth_pruned"
            ),
            "authenticated_source_native_preselected": True,
        }
    if len(events) != source["actual_native_replacement_count"]:
        raise JournalIntegrityError("D18 native source retirement count drift")
    if (digest(evaluated.to_snapshot()) != original_pre_sha
            or digest(selected.to_snapshot()) != selected_sha):
        raise JournalIntegrityError("D18 read-only observer mutated source D15 journal states")
    return {
        "schema": "D18_ORIGINAL_D15_ACTUAL_SELECTED_E1_E2_OBSERVER_V1",
        "source_commit": source_commit,
        "seed": source["base_seed"],
        "original_selected_round": selected.generation,
        "evaluated_preselect_v7_sha256": original_pre_sha,
        "selected_post_v7_sha256": selected_sha,
        "original_native_evaluated_worlds": 128,
        "categories": categories,
        "E1_growth_only_candidate_count": sum(
            len(x["growth_only_candidate_indices_E1"]) for x in categories.values()
        ),
        "E2_actual_growth_pruned_count": len(e2_events),
        "original_native_retirements": events,
        "read_only": True,
        "learning_claim": False,
        "independent_generalization_claim": False,
    }
