"""D16 #217: read-only observation of a fully COMMITTED original D15 journal.

No simulation, no writer lock, no commit, no D16 seed dispatch. Unlike the
synthetic D16 offline ledger, this calls the existing journal byte/checksum
validator before reading the authentic evaluated + selected optimizer snapshots.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from research.d12_real_prune_eligibility_202 import eligibility_snapshot
from research.d15_sparse_recovery_213 import JournalIntegrityError, SparseEvaluationJournal
from research.d8_genome_diversity_190 import analyze, digest
from search.evolution import SteadyStateOptimizer

COMMIT = re.compile(r"[0-9a-f]{40}")


def observe_committed_round(root: Path, *, source_commit: str) -> dict[str, Any]:
    """Return authentic source-bound native pre/post-selection evidence.

    Only existing D15 journal files are read. The original D15 journal itself
    owns checksum and patch-chain verification. This function additionally
    rejects selected-generation mismatch, forged journal finalization, and
    a changed nonselected history. It is NOT a replacement for writer safety.
    """
    if not isinstance(source_commit, str) or not COMMIT.fullmatch(source_commit):
        raise ValueError("source_commit must be a pinned 40-character SHA")
    journal = SparseEvaluationJournal.open(Path(root), source_commit=source_commit)
    view = journal.recover()
    if (view.read_only or not view.final_committed
            or not view.evaluation_complete or view.next_index != 128
            or view.final_snapshot is None):
        raise JournalIntegrityError("D16 observer requires a COMPLETE D15 selected128 journal")

    original = SteadyStateOptimizer.from_snapshot(view.snapshot)
    selected = SteadyStateOptimizer.from_snapshot(view.final_snapshot)
    if (len(original.slots) != 128 or len(selected.slots) != 128
            or selected.generation != original.generation + 1
            or journal.manifest["base_generation"] != original.generation):
        raise JournalIntegrityError("D16 native selected generation/size mismatch")

    before_sha, after_sha = digest(original.to_snapshot()), digest(selected.to_snapshot())
    try:
        eligibility = eligibility_snapshot(original)
        before_diversity = analyze(original)
        after_diversity = analyze(selected)
    except (AssertionError, ValueError, KeyError) as exc:
        raise JournalIntegrityError("D16 native original observer rejected journal state") from exc

    if (digest(original.to_snapshot()) != before_sha
            or digest(selected.to_snapshot()) != after_sha):
        raise JournalIntegrityError("D16 observer mutated authoritative native state")

    before_history, after_history = original.prune_history, selected.prune_history
    if len(after_history) < len(before_history) or after_history[:len(before_history)] != before_history:
        raise JournalIntegrityError("D16 selected prune history lost existing provenance")
    retirements = after_history[len(before_history):]
    if len(retirements) > 4:
        raise JournalIntegrityError("D16 native selection retired >1 world per category")
    actual_by_category: dict[str, int] = {}
    eligible_by_category = {
        name: set(info["native_pruned_indices"])
        for name, info in eligibility["strata"].items()
    }
    for record in retirements:
        category = record["category"]
        index = record["index"]
        if (record["optimizer_generation"] != selected.generation
                or category not in eligible_by_category
                or index not in eligible_by_category[category]):
            raise JournalIntegrityError("D16 native retired slot not in authentic preselection prune set")
        if (actual_by_category.get(category, 0) >= 1
                or selected.slots[index].category != category
                or selected.slots[index].index != index):
            raise JournalIntegrityError("D16 multiple/cross-category native replacements")
        actual_by_category[category] = 1

    counts = selected._category_counts()
    if (set(counts) != set(eligible_by_category)
            or len(counts) != 4 or any(count != 32 for count in counts.values())):
        raise JournalIntegrityError("D16 selected population not native 4x32")

    summary = {
        category: {
            "native_eligible_prune_indices": info["native_pruned_indices"],
            "native_eligibility_gate": info["gate"],
            "complete_nonfailure_count": info["complete_nonfailure_count"],
            "absolute_failure_count": info["absolute_failure_count"],
            "growth_window_length_histogram": info["growth_window_length_histogram"],
            "native_replacement_count": actual_by_category.get(category, 0),
        }
        for category, info in eligibility["strata"].items()
    }
    return {
        "kind": "D16_READONLY_AUTHENTIC_D15_SELECTED128_OBSERVER_V1",
        "source_commit": source_commit,
        "base_seed": original.search_plan.scheduler_base_seed,
        "before_optimizer_generation": original.generation,
        "selected_optimizer_generation": selected.generation,
        "evaluated_native_worlds": 128,
        "selected_native_worlds": 128,
        "original_selected_once_proven_by_D15_final": True,
        "d15_journal_chain_verified": True,
        "evaluated_preselect_v7_sha256": before_sha,
        "selected_post_v7_sha256": after_sha,
        "categories": summary,
        "actual_native_replacement_count": len(retirements),
        "native_retirements": retirements,
        "before_diversity": before_diversity["strata"],
        "after_diversity": after_diversity["strata"],
        "learning_claim": False,
        "independent_generalization_claim": False,
        "read_only": True,
    }
