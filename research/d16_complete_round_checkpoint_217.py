"""D16 #217 reusable ORIGINAL one-round D15 evidence + atomic completed checkpoint.

No CLI, workflow_dispatch or study launcher. The only generator here is the
accepted source-native D15 selected128 evaluator; no new physics/genetics.
This function must NOT be wired to the original seed16384 study until a
separate effectful launch authority and externally enforced Actions time cap.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import uuid
from typing import Any, Mapping

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import (
    JournalIntegrityError, execute_selected_round,
)
from research.d16_native_journal_observer_217 import observe_committed_round
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, canonical_bytes, hash_of, utc_now_ms,
)
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

MAX_COMPLETED_BUNDLE_BYTES = 32 * 1024 * 1024
KIND = "D16_ORIGINAL_COMPLETED_SELECTED128_ROUND_CHECKPOINT_V1"


def check_round(*, source_sha: str, seed: int, ordinal: int,
                predecessor: Mapping[str, Any] | None,
                selected: Mapping[str, Any],
                observer: Mapping[str, Any], result: Mapping[str, Any],
                experiment: ExperimentConfig,
                physics: PhysicsConfig) -> None:
    """Fail-closed original D15 final and actual source-native observer match."""
    if (not result.get("final_committed")
            or not result.get("finalization_performed")
            or result.get("new_evaluations") != 128
            or result.get("resumed_from") != 0
            or result.get("final_digest") != digest(selected)):
        raise D16BoundaryError("not a once-completed original full128 native selection")
    current = SteadyStateOptimizer.from_snapshot(dict(selected))
    if (current.generation != ordinal or len(current.slots) != 128
            or current.search_plan.scheduler_base_seed != seed
            or current.experiment.to_dict() != experiment.to_dict()
            or current.base_config.to_dict() != physics.to_dict()):
        raise D16BoundaryError("original science seed/generation/experiment changed")
    categories: dict[str, int] = {}
    for i, slot in enumerate(current.slots):
        if i != slot.index:
            raise D16BoundaryError("authoritative native slot order diverged")
        categories[slot.category] = categories.get(slot.category, 0) + 1
    if len(categories) != 4 or sorted(categories.values()) != [32] * 4:
        raise D16BoundaryError("original native128 4x32 category population changed")
    if predecessor is not None:
        before = SteadyStateOptimizer.from_snapshot(dict(predecessor))
        if before.generation != ordinal - 1 or before.search_plan.scheduler_base_seed != seed:
            raise D16BoundaryError("original previous selected state mismatch")
        if observer["before_optimizer_generation"] != before.generation:
            raise D16BoundaryError("D15 preselected original predecessor mismatch")
    if (
        observer.get("source_commit") != source_sha
        or observer.get("base_seed") != seed
        or observer.get("selected_optimizer_generation") != ordinal
        or observer.get("evaluated_native_worlds") != 128
        or observer.get("selected_native_worlds") != 128
        or observer.get("d15_journal_chain_verified") is not True
        or observer.get("original_selected_once_proven_by_D15_final") is not True
        or observer.get("selected_post_v7_sha256") != result.get("final_digest")
        or observer.get("actual_native_replacement_count", -1) > 4
        or observer.get("learning_claim") is not False
    ):
        raise D16BoundaryError("D15 source-bound observer and native final mismatch")
    if (result.get("journal_bytes", 0) > 128 * 1024 * 1024
            or result.get("peak_aggregate_rss_bytes",result.get("peak_rss_bytes",2**63))
            > 1536 * 1024 * 1024):
        raise D16BoundaryError("original D15 resource envelope exceeded")


def one_authentic_selected_round(*, source_sha: str, seed: int,
                               ordinal: int, predecessor: Mapping[str, Any] | None,
                               experiment: ExperimentConfig, physics: PhysicsConfig,
                               clock: GlobalClock, job_started_monotonic: float,
                               workers: int = 4) -> dict[str, Any]:
    """Execute exactly one full source-native D15 round, verified before return.

    This is an internal callable, not an authorized study launch. The caller
    must separately guarantee a true external OS/job hard timeout.
    """
    if seed not in (0,16384) or type(seed) is not int:
        raise D16BoundaryError("only exposed fixture0 or original study16384")
    if seed == 16384 and (experiment.to_dict() != ExperimentConfig().to_dict()
                          or physics.to_dict() != PhysicsConfig().to_dict()):
        raise D16BoundaryError("original D16 physics/experiment cannot change")
    if workers not in (1,2,4) or type(workers) is not int:
        raise D16BoundaryError("native D15 worker fanout invalid")

    def check_budget(*_unused: Any) -> None:
        clock.check(now_unix_ms=utc_now_ms(),
                    local_elapsed_ms=int((time.monotonic() - job_started_monotonic)*1000))

    check_budget()
    with TemporaryDirectory(prefix="d16-completed-native128-") as tmp:
        root = Path(tmp) / "journal"
        result = execute_selected_round(
            root, source_commit=source_sha, base_seed=seed,
            experiment=experiment, base_config=physics,
            base_snapshot=None if predecessor is None else dict(predecessor),
            workers=workers, memory_mib=1536,
            evaluation_batch_size=16,
            on_checkpoint=lambda _i: check_budget(),
            on_stage=lambda _event: check_budget(),
        )
        check_budget()
        observer = observe_committed_round(root, source_commit=source_sha)
        selected = result["final_snapshot"]
        check_round(
            source_sha=source_sha, seed=seed, ordinal=ordinal,
            predecessor=predecessor, selected=selected, observer=observer,
            result=result, experiment=experiment, physics=physics,
        )
        check_budget()
        return {
            "kind": KIND,
            "source_sha": source_sha,
            "seed": seed,
            "ordinal": ordinal,
            "selected_snapshot": selected,
            "selected_v7_sha256": result["final_digest"],
            "d15_verified_observer": observer,
            "d15_journal_bytes": result["journal_bytes"],
            "rss_sampled_bytes": result.get("peak_aggregate_rss_bytes",
                                             result.get("peak_rss_bytes")),
            "global_wall_ms": clock.check(
                now_unix_ms=utc_now_ms(),
                local_elapsed_ms=int((time.monotonic()-job_started_monotonic)*1000),
            ),
            "learning_claim": False,
        }


def write_completed_atomic(folder: Path, checkpoint: Mapping[str, Any]) -> Path:
    """Single atomic bundle per completely selected round, no partial pass."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if checkpoint.get("kind") != KIND:
        raise D16BoundaryError("not a verified original completed round")
    ordinal = checkpoint.get("ordinal")
    if type(ordinal) is not int or not 1 <= ordinal <= 40:
        raise D16BoundaryError("selected round checkpoint index invalid")
    # Recompute the canonical selected optimizer digest even on a path write.
    selected = checkpoint.get("selected_snapshot")
    if not isinstance(selected, dict) or digest(selected) != checkpoint.get("selected_v7_sha256"):
        raise D16BoundaryError("selected v7 checkpoint checksum mismatch")
    envelope = {
        "schema": KIND, "round": ordinal,
        "payload": dict(checkpoint),
        "payload_sha256": hash_of(dict(checkpoint)),
    }
    raw = canonical_bytes(envelope) + b"\n"
    if len(raw) > MAX_COMPLETED_BUNDLE_BYTES:
        raise D16BoundaryError("complete selected bundle exceeds transfer limit")
    target = folder / f"selected-round-{ordinal:02d}.json"
    if target.exists():
        raise FileExistsError("completed round is immutable; no silent overwrite")
    temp = folder / f".selected-{ordinal:02d}-{uuid.uuid4().hex}.tmp"
    try:
        with temp.open("xb") as fh:
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return target


def read_completed(path: Path, *, source_sha: str, seed: int, ordinal: int) -> dict[str, Any]:
    path = Path(path)
    if path.stat().st_size > MAX_COMPLETED_BUNDLE_BYTES:
        raise D16BoundaryError("completed round bundle oversized")
    envelope = json.loads(path.read_bytes())
    if (envelope.get("schema") != KIND or envelope.get("round") != ordinal
            or not isinstance(envelope.get("payload"), dict)
            or envelope.get("payload_sha256") != hash_of(envelope["payload"])):
        raise D16BoundaryError("completed round bundle tampered")
    record = envelope["payload"]
    if (record.get("source_sha") != source_sha or record.get("seed") != seed
            or record.get("ordinal") != ordinal
            or record.get("kind") != KIND
            or record.get("learning_claim") is not False):
        raise D16BoundaryError("completed round provenance mismatch")
    selected = record.get("selected_snapshot")
    if not isinstance(selected, dict) or digest(selected) != record.get("selected_v7_sha256"):
        raise D16BoundaryError("completed original selected state corrupt")
    return record
