"""D15 #213: research-only native selected128 atomic midround replay.

Original Phase5 slot physics and exactly-once category-local selection are
reused. A checkpoint contains one complete pre-round optimizer snapshot,
ordered sparse post-evaluation slot patches, and one atomic final selected
snapshot; no partial state is passed off as a completed Outer round.

Linux / POSIX only (memory/cgroup and advisory single-writer lock).
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import threading
from pathlib import Path
from contextlib import nullcontext
import time
from typing import Any, Callable

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d13_outer_execution_204 import OuterResearchPlan
from research.d15_sparse_recovery_213 import (
    CheckpointPolicy, JournalIntegrityError, ResourceBudget,
    SparseEvaluationJournal,
)
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer, UniverseSlot

FROZEN_PRE_D14_SELECTED_SHA = "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321"
SLOTS = 128


def execute_selected_round(
    root: Path,
    *,
    source_commit: str,
    base_seed: int = 0,
    experiment: ExperimentConfig | None = None,
    base_config: PhysicsConfig | None = None,
    base_snapshot: dict[str, Any] | None = None,
    evaluation_batch_size: int = 16,
    memory_mib: int = 1536,
    checkpoint_policy: CheckpointPolicy | None = None,
    max_journal_bytes: int = 128 * 1024 * 1024,
    workers: int = 1,
    on_checkpoint: Callable[[int], None] | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run/resume EXACTLY one native selected128 Outer step, fail-closed.

    The callbacks are injection points for controlled process-kill research.
    They never choose a slot, fitness value, genetic operator or result.
    Call with the true current implementation/source revision: the journal
    rejects any different revision on future open.
    """
    if type(workers) is not int or workers not in (1, 2, 4):
        raise ValueError("D15 workers must be exactly 1, 2 or 4")
    if workers > 1 and threading.current_thread() is not threading.main_thread():
        raise ValueError("D15 spawn workers require the original long-lived main thread")
    if not isinstance(source_commit, str) or not source_commit.strip():
        raise ValueError("D15 source_commit is required")
    if base_snapshot is not None and not isinstance(base_snapshot, dict):
        raise ValueError("D15 completed previous-round base_snapshot must be a dictionary")
    if type(evaluation_batch_size) is not int or not 1 <= evaluation_batch_size <= SLOTS:
        raise ValueError("D15 selected evaluation_batch_size must be 1..128 exact int")
    if type(base_seed) is not int or not 0 <= base_seed <= 0x7FFFFFFF:
        raise ValueError("D15 base_seed outside allowed range")
    if on_checkpoint is not None and not callable(on_checkpoint):
        raise ValueError("on_checkpoint must be callable")
    if on_stage is not None and not callable(on_stage):
        raise ValueError("on_stage must be callable")

    protocol = experiment or ExperimentConfig()
    physics = base_config or PhysicsConfig()
    policy = checkpoint_policy or CheckpointPolicy()
    budget = ResourceBudget(memory_mib)
    # Inherited D13 preallocation CPU, world-count and physics admission.
    plan = OuterResearchPlan(
        mode="native_selection", base_seed=base_seed, outer_steps=1,
        evaluated_worlds=SLOTS, worlds_per_batch=evaluation_batch_size,
    )
    plan.validate(physics=physics, experiment=protocol)

    root = Path(root)
    root.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    peak_rss = 0
    saves = 0

    def sample_budget() -> None:
        nonlocal peak_rss
        current = budget.current_rss_bytes()
        peak_rss = max(current, peak_rss)
        # Conservative headroom for up to the next patch + one world.
        # This is an admission estimate; not an OS-enforced hard RSS cap.
        allowance = max(64 * 1024 * 1024,
                        min(SLOTS, policy.max_worlds_between_saves) * physics.max_cells * 4096)
        budget.admit(
            estimated_additional_bytes=allowance,
            current_rss_bytes=current,
            available_host_bytes=budget.available_host_bytes(),
        )

    def verify_native_config(opt: SteadyStateOptimizer) -> None:
        if opt.experiment.to_dict() != protocol.to_dict():
            raise JournalIntegrityError("D15 native experiment config changed")
        if opt.base_config.to_dict() != physics.to_dict():
            raise JournalIntegrityError("D15 native physical config changed")
        if opt.search_plan.scheduler_base_seed != base_seed:
            raise JournalIntegrityError("D15 source-bound search seed changed")
        if len(opt.slots) != SLOTS or any(slot.index != i for i, slot in enumerate(opt.slots)):
            raise JournalIntegrityError("D15 selected128 slot identity changed")

    # A persistent sibling lock path is intentional; do NOT unlink lock
    # in either normal or crash cleanup (which could split flock identity).
    lock_path = root.with_name(root.name + ".writer.lock")
    with lock_path.open("a+b") as single_writer:
        try:
            fcntl.flock(single_writer.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            raise JournalIntegrityError("D15 journal already has an active writer") from exc
        try:
            sample_budget()
            if (root / "manifest.json").exists():
                journal = SparseEvaluationJournal.open(root, source_commit=source_commit)
                if base_snapshot is not None:
                    supplied_hash = hashlib.sha256(json.dumps(
                        base_snapshot, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")).hexdigest()
                    if supplied_hash != journal.manifest["base_sha256"]:
                        raise JournalIntegrityError("D15 supplied completed-round base disagrees with journal")
            else:
                if root.exists() and any(root.iterdir()):
                    raise JournalIntegrityError("incomplete journal initialization requires manual rejection")
                opt = (SteadyStateOptimizer.from_snapshot(base_snapshot)
                       if base_snapshot is not None else
                       SteadyStateOptimizer.from_defaults(
                           base_seed=base_seed, experiment=protocol, base_config=physics,
                       ))
                verify_native_config(opt)
                sample_budget()
                journal = SparseEvaluationJournal.create(
                    root, base_snapshot=opt.to_snapshot(),
                    source_commit=source_commit, max_bytes=max_journal_bytes,
                )

            view = journal.recover()
            opt = SteadyStateOptimizer.from_snapshot(
                view.final_snapshot if view.final_committed else view.snapshot
            )
            verify_native_config(opt)
            original_generation = journal.manifest["base_generation"]
            if view.final_committed:
                if opt.generation != original_generation + 1:
                    raise JournalIntegrityError("D15 completed generation mismatch")
                sample_budget()
                final_snapshot = opt.to_snapshot()
                return {
                    "final_snapshot": final_snapshot,
                    "final_digest": digest(final_snapshot),
                    "resumed_from": SLOTS,
                    "new_evaluations": 0,
                    "checkpoint_writes": 0,
                    "finalization_performed": False,
                    "final_committed": True,
                    "selected_step": None,
                    "journal_bytes": sum(p.stat().st_size for p in root.iterdir() if p.is_file()),
                    "peak_rss_bytes": peak_rss,
                    "elapsed_wall_seconds": time.perf_counter() - started,
                    "learning_claim": False,
                }
            if view.read_only or opt.generation != original_generation:
                raise JournalIntegrityError("D15 unfinished source is read-only or wrong generation")
            if not 0 <= view.next_index <= SLOTS:
                raise JournalIntegrityError("D15 next slot index invalid")
            resumed_from = view.next_index
            pending: list[dict[str, Any]] = []
            last_save_at = time.monotonic()

            if workers == 1:
                # Preserve original serial evaluation and journal semantics.
                worker_context = nullcontext(None)
            else:
                from research.d15_spawn_workers_226 import SpawnEvaluator
                worker_context = SpawnEvaluator(
                    opt.to_snapshot(), workers=workers,
                    budget=budget, lock_path=lock_path,
                )
            # Pool ends BEFORE native selection and final commit; only the
            # parent owns the existing journal + exclusive writer lock.
            with worker_context as worker_pool:
                for first in range(resumed_from, SLOTS, evaluation_batch_size):
                    indices = tuple(range(first, min(first + evaluation_batch_size, SLOTS)))
                    # Evaluate the complete bounded batch in children without
                    # committing ANY unvalidated partial set to the journal.
                    child_records = (
                        {} if worker_pool is None else worker_pool.evaluate(indices)
                    )
                    for index in indices:
                        sample_budget()
                        slot = opt.slots[index]
                        if slot.index != index:
                            raise JournalIntegrityError("D15 native evaluation index diverged")
                        if worker_pool is None:
                            # Original authoritative source, unchanged.
                            opt._evaluate_slot(slot)
                        else:
                            candidate = UniverseSlot.from_dict(
                                child_records[index], base_config=opt.base_config,
                            )
                            if (
                                candidate.index != index or
                                candidate.seed != slot.seed or
                                candidate.category != slot.category or
                                candidate.genome_key != slot.genome_key
                            ):
                                raise JournalIntegrityError("D15 worker slot identity changed")
                            opt.slots[index] = slot = candidate
                        pending.append(slot.to_dict())
                        if policy.should_commit(
                            pending_worlds=len(pending),
                            seconds_since_save=time.monotonic() - last_save_at,
                        ) or index + 1 == SLOTS:
                            journal.commit(pending)
                            saves += 1
                            pending = []
                            last_save_at = time.monotonic()
                            sample_budget()
                            if on_checkpoint is not None:
                                on_checkpoint(index + 1)

            if pending:
                raise JournalIntegrityError("D15 uncommitted evaluations after loop")
            posteval = journal.recover()
            if not posteval.evaluation_complete or posteval.next_index != SLOTS:
                raise JournalIntegrityError("D15 cannot select before 128 evaluations")
            # Catches omissions, double-evaluation or malformed slot patches
            # before any irreversible selected-round final checkpoint.
            if posteval.snapshot != opt.to_snapshot():
                raise JournalIntegrityError("D15 in-memory and journal evaluated state disagree")

            sample_budget()
            # Same EXACT category-local finalizer as normal optimizer.step(),
            # never a copied/reimplemented selection algorithm.
            selected_step = opt._finalize_evaluated_step(
                evaluated_slots=SLOTS, started=started,
            )
            final_snapshot = opt.to_snapshot()
            final_digest = digest(final_snapshot)
            # Locked historical oracle applies only to identical original
            # default physics/experiment/golden seed; no posthoc adaptation.
            if (base_seed == 0
                    and physics.to_dict() == PhysicsConfig().to_dict()
                    and protocol.to_dict() ==
                        ExperimentConfig(evaluation_timeout_generations=2).to_dict()
                    and original_generation == 0
                    and final_digest != FROZEN_PRE_D14_SELECTED_SHA):
                raise JournalIntegrityError("D15 native selected state differs from frozen PRE-D14 golden")
            if on_stage is not None:
                on_stage("before_final_commit")
            journal.commit_final(final_snapshot)
            if on_stage is not None:
                on_stage("after_final_commit")
            sample_budget()
            result = {
                "final_snapshot": final_snapshot,
                "final_digest": final_digest,
                "resumed_from": resumed_from,
                "new_evaluations": SLOTS - resumed_from,
                "checkpoint_writes": saves,
                "finalization_performed": True,
                "final_committed": True,
                "selected_step": selected_step,
                "journal_bytes": sum(p.stat().st_size for p in root.iterdir() if p.is_file()),
                "peak_rss_bytes": peak_rss,
                "elapsed_wall_seconds": time.perf_counter() - started,
                "learning_claim": False,
            }
            if worker_pool is not None:
                # Retain new opt-in worker resource evidence only. Original
                # workers=1 return contract remains byte-for-byte identical.
                result["peak_aggregate_rss_bytes"] = worker_pool.peak_aggregate_rss
                result["worker_hard_virtual_cap_bytes"] = worker_pool.virtual_cap
            return result
        finally:
            fcntl.flock(single_writer.fileno(), fcntl.LOCK_UN)
