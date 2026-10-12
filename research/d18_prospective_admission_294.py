"""D18.1 #294: source-only admission of a GENUINE completed new-seed D15 journal.

This module cannot evaluate worlds, start GitHub Actions, or extend a study.
The evidence authority is the original D15 chain and native D18 E1/E2 observer.
Study seed 49152 is discovery-only, not a held-out generalization cohort.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_sparse_recovery_213 import JournalIntegrityError, SparseEvaluationJournal
from research.d16_twojob_run_control_217 import GlobalClock
from research.d18_native_journal_observer_294 import observe_completed_native_round
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

SEARCH_SEED = 49152
STAGE1_LAST = 20
MIN_TERMINAL_ROUND = 37
MAX_ROUNDS = 40
MAX_JOBS = 2
MAX_JOURNAL_BYTES = 128 * 1024 * 1024
MAX_AGGREGATE_RSS = 1536 * 1024 * 1024
MAX_RETAINED_BYTES = 512 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{40}\Z")


def stage_for_round(ordinal: int) -> int:
    if type(ordinal) is not int or not 1 <= ordinal <= MAX_ROUNDS:
        raise ValueError("D18 original selected ordinal must be 1..40")
    return 1 if ordinal <= STAGE1_LAST else 2


def interpret_genuine_e1_e2(round_number: int, authentic: dict[str, Any]) -> str:
    """Classify only a caller-authenticated actual D15/D18 journal observation."""
    stage_for_round(round_number)
    if (type(authentic) is not dict
            or authentic.get("schema") != "D18_ORIGINAL_D15_ACTUAL_SELECTED_E1_E2_OBSERVER_V1"
            or authentic.get("seed") != SEARCH_SEED
            or authentic.get("original_selected_round") != round_number
            or authentic.get("original_native_evaluated_worlds") != 128
            or authentic.get("read_only") is not True
            or authentic.get("learning_claim") is not False):
        raise ValueError("D18 outcome lacks exact original source journal provenance")
    categories = authentic.get("categories")
    if not isinstance(categories, dict) or len(categories) != 4:
        raise ValueError("D18 requires all original four categories")
    e1 = sum(len(row["growth_only_candidate_indices_E1"]) for row in categories.values())
    e2 = sum(1 for row in categories.values() if row["authentic_growth_pruned_E2"] is True)
    if (authentic.get("E1_growth_only_candidate_count") != e1
            or authentic.get("E2_actual_growth_pruned_count") != e2):
        raise ValueError("D18 E1/E2 aggregate does not match native category counts")
    for row in categories.values():
        if row["authentic_growth_pruned_E2"] is True:
            evt = row.get("actual_native_retirement_E2")
            if (not isinstance(evt, dict) or evt.get("retirement_reason") != "growth_pruned"
                    or evt.get("index") not in row["growth_only_candidate_indices_E1"]
                    or evt.get("index") != row.get("native_predicted_target_index")):
                raise ValueError("D18 E2 must retire a real preselected growth-only E1")
    if round_number < MIN_TERMINAL_ROUND:
        return "CONTINUE"
    if e2:
        return "OBSERVED_E2_FINAL"
    if round_number < MAX_ROUNDS:
        return "CONTINUE"
    return "E1_ONLY_FINAL" if e1 else "NO_E1_FINAL"


def admit_completed_native_journal(
    root: Path,
    *,
    source_sha: str,
    ordinal: int,
    job: int,
    study_started_unix_ms: int,
    prior_elapsed_ms: int,
    now_unix_ms: int,
    local_elapsed_ms: int,
) -> dict[str, Any]:
    """Source-bound read-only pre/post observer; never dispatches a world."""
    if not isinstance(source_sha, str) or not SHA.fullmatch(source_sha):
        raise ValueError("D18 must pin an exact source SHA before first outcome")
    if type(job) is not int or job not in (1, 2) or stage_for_round(ordinal) != job:
        raise ValueError("D18 permits exactly two partitioned original hosted jobs")
    clock = GlobalClock(study_started_unix_ms, prior_elapsed_ms)
    global_elapsed_ms = clock.check(
        now_unix_ms=now_unix_ms, local_elapsed_ms=local_elapsed_ms,
    )
    journal = SparseEvaluationJournal.open(Path(root), source_commit=source_sha)
    view = journal.recover()
    if (view.read_only or not view.final_committed or not view.evaluation_complete
            or view.next_index != 128 or view.final_snapshot is None):
        raise JournalIntegrityError("D18 original full128 journal not committed")
    sizes = sum(x.stat().st_size for x in Path(root).iterdir() if x.is_file())
    if sizes > MAX_JOURNAL_BYTES:
        raise JournalIntegrityError("D18 original D15 journal exceeded 128MiB")
    selected = SteadyStateOptimizer.from_snapshot(view.final_snapshot)
    if (selected.generation != ordinal
            or selected.search_plan.scheduler_base_seed != SEARCH_SEED
            or len(selected.slots) != 128
            or sorted(selected._category_counts().values()) != [32, 32, 32, 32]
            or selected.experiment.to_dict() != ExperimentConfig().to_dict()
            or selected.base_config.to_dict() != PhysicsConfig().to_dict()):
        raise JournalIntegrityError("D18 original default128 seed/physics/ordinal mismatch")
    selected_sha = digest(selected.to_snapshot())
    actual = observe_completed_native_round(root, source_commit=source_sha)
    if (actual["seed"] != SEARCH_SEED
            or actual["original_selected_round"] != ordinal
            or actual["selected_post_v7_sha256"] != selected_sha
            or actual["source_commit"] != source_sha):
        raise JournalIntegrityError("D18 source-native D15/D18 outcome mismatch")
    decision = interpret_genuine_e1_e2(ordinal, actual)
    return {
        "schema": "D18_NEW_SEED_NATIVE_JOURNAL_ADMISSION_V1",
        "source_sha": source_sha,
        "seed": SEARCH_SEED,
        "ordinal": ordinal,
        "job": job,
        "selected_post_v7_sha256": selected_sha,
        "global_elapsed_ms": global_elapsed_ms,
        "journal_bytes": sizes,
        "E1_count": actual["E1_growth_only_candidate_count"],
        "E2_count": actual["E2_actual_growth_pruned_count"],
        "status": decision,
        "read_only": True,
        "learning_claim": False,
        "independent_generalization_claim": False,
    }
