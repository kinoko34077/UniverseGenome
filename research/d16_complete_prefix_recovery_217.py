"""D16 #217 offline completed-prefix recovery, no evaluation / no study dispatch.

Read-only replay of already committed D15-selected round snapshots plus an
immutable source/time-bound receipt per ORIGINAL completed selection. Never
infer progress from a partial D15 patch, mutable report or untrusted SHA alone.
Same-host process restart only: a new hosted job is NOT an authorized 3rd job.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from typing import Any, Mapping

from research.d16_complete_round_checkpoint_217 import read_completed
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, canonical_bytes, hash_of,
)
from research.d16_twojob_stage_fsm_217 import StageState, split_at

SCHEMA="D16_SOURCE_BOUND_COMPLETED_PREFIX_RECEIPT_V1"
ROUND_FILE=re.compile(r"selected-round-([0-9]{2})\.json")
RECEIPT_FILE=re.compile(r"selected-receipt-([0-9]{2})\.json")
MAX_RECEIPT_BYTES=4096


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open("rb") as reader:
        while data:=reader.read(1024*1024):
            h.update(data)
    return h.hexdigest()


def immutable_receipt(folder: Path, *, source_sha: str, seed: int, ordinal: int,
                      job: int, clock: GlobalClock, now_unix_ms: int,
                      local_elapsed_ms: int) -> Path:
    """Publish only AFTER the original fully selected-v7 checkpoint exists.

    Does not rewrite or recover an incomplete D15 journal. Refuses overwrites.
    """
    folder=Path(folder)
    complete_path=folder/f"selected-round-{ordinal:02d}.json"
    complete=read_completed(complete_path,source_sha=source_sha,
                            seed=seed,ordinal=ordinal)
    if job != (1 if ordinal <= split_at(seed) else 2):
        raise D16BoundaryError("receipt from wrong original hosted job")
    elapsed=clock.check(now_unix_ms=now_unix_ms,
                        local_elapsed_ms=local_elapsed_ms)
    if complete.get("global_wall_ms",2**64) > elapsed:
        raise D16BoundaryError("completed selected source clock exceeds receipt")
    record={
        "schema":SCHEMA,"source_sha":source_sha,"seed":seed,
        "ordinal":ordinal,"job":job,
        "selected_file_sha256":sha256_file(complete_path),
        "selected_v7_sha256":complete["selected_v7_sha256"],
        "actual_d15_observer_sha256":hash_of(complete["d15_verified_observer"]),
        "study_started_unix_ms":clock.study_started_unix_ms,
        "global_elapsed_ms":elapsed,"local_elapsed_ms":local_elapsed_ms,
        "learning_claim":False,
    }
    raw=canonical_bytes(record)+b"\n"
    if len(raw)>MAX_RECEIPT_BYTES:
        raise D16BoundaryError("source-bound progress receipt too large")
    target=folder/f"selected-receipt-{ordinal:02d}.json"
    if target.exists():
        raise FileExistsError("immutable complete-prefix receipt already exists")
    tmp=folder/f".receipt-{ordinal:02d}-{uuid.uuid4().hex}.tmp"
    try:
        with tmp.open("xb") as writer:
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
        os.link(tmp,target)  # create without overwriting a concurrent receipt
        directory_fd=os.open(folder,os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        tmp.unlink(missing_ok=True)
    return target


@dataclass(frozen=True)
class RecoveredPrefix:
    stage: StageState
    last_selected_snapshot: Mapping[str,Any] | None
    count: int
    provenance_authenticated: bool = False

    @property
    def next_selected_round(self) -> int:
        return self.count+1


def replay_completed_prefix(folder: Path, *, source_sha: str, seed: int,
                            original_genesis: Mapping[str,Any],
                            study_started_unix_ms: int) -> RecoveredPrefix:
    """Fail closed on holes/duplicates/orphans, replay only complete records.

    Native state is revalidated by StageState on every verified checkpoint.
    Receipt timestamps cannot move backwards or reset the time between jobs.
    Does not authorize another hosted runner after a prior job failed.
    """
    folder=Path(folder)
    if not folder.exists():
        raise D16BoundaryError("missing original progress folder")
    names={p.name for p in folder.iterdir() if p.is_file()}
    if any(name.startswith(".selected-") or name.startswith(".receipt-")
           for name in names):
        raise D16BoundaryError("uncommitted temporary evidence requires explicit recovery")
    snapshots={int(m[1]) for name in names if (m:=ROUND_FILE.fullmatch(name))}
    receipts={int(m[1]) for name in names if (m:=RECEIPT_FILE.fullmatch(name))}
    if snapshots != receipts:
        raise D16BoundaryError("orphan completed selected snapshot or orphan time receipt")
    if snapshots != set(range(1,len(snapshots)+1)):
        raise D16BoundaryError("original completed selected prefix has a gap")
    if len(snapshots) > (2 if seed==0 else 40):
        raise D16BoundaryError("completed prefix exceeds fixed study/test horizon")

    state=StageState.start(source_sha=source_sha,seed=seed,
                           original_genesis=original_genesis,
                           job1_start_unix_ms=study_started_unix_ms)
    previous_local=0
    previous_global=0
    previous_job=1
    last=None
    last_boundary_elapsed=None
    for ordinal in sorted(snapshots):
        filename=folder/f"selected-round-{ordinal:02d}.json"
        receipt_path=folder/f"selected-receipt-{ordinal:02d}.json"
        if receipt_path.stat().st_size>MAX_RECEIPT_BYTES:
            raise D16BoundaryError("oversized progress receipt")
        receipt=json.loads(receipt_path.read_bytes())
        current_job=1 if ordinal<=split_at(seed) else 2
        if (set(receipt)!={
            "schema","source_sha","seed","ordinal","job",
            "selected_file_sha256","selected_v7_sha256",
            "actual_d15_observer_sha256","study_started_unix_ms",
            "global_elapsed_ms","local_elapsed_ms","learning_claim",
        } or receipt["schema"]!=SCHEMA or receipt["source_sha"]!=source_sha
                or receipt["seed"]!=seed or receipt["ordinal"]!=ordinal
                or receipt["job"]!=current_job
                or receipt["study_started_unix_ms"]!=study_started_unix_ms
                or receipt["learning_claim"] is not False):
            raise D16BoundaryError("receipt source/seed/round/job/time anchor drift")
        complete=read_completed(filename,source_sha=source_sha,seed=seed,
                                ordinal=ordinal)
        if (sha256_file(filename)!=receipt["selected_file_sha256"]
                or complete["selected_v7_sha256"]!=receipt["selected_v7_sha256"]
                or hash_of(complete["d15_verified_observer"])
                !=receipt["actual_d15_observer_sha256"]):
            raise D16BoundaryError("source-bound original checkpoint receipt tampered")
        wall=receipt["global_elapsed_ms"]
        local=receipt["local_elapsed_ms"]
        if (type(wall) is not int or type(local) is not int
                or wall<previous_global or
                (current_job==previous_job and local<previous_local)):
            raise D16BoundaryError("source-native absolute or local time went backwards")
        if current_job!=previous_job:
            if previous_job!=1 or current_job!=2 or last_boundary_elapsed is None:
                raise D16BoundaryError("invalid original stage transition")
            stage_clock=GlobalClock(study_started_unix_ms,
                                    last_boundary_elapsed)
            state=state.accept_second_job(
                verified_selected20_v7=state.selected_v7_sha256,
                clock_from_immutable_manifest=stage_clock,
                now_unix_ms=study_started_unix_ms+wall,
            )
            previous_local=0
        state=state.append(
            complete=complete,
            now_unix_ms=study_started_unix_ms+wall,
            local_elapsed_ms=local,
        )
        if ordinal==split_at(seed):
            last_boundary_elapsed=wall
        previous_job=current_job
        previous_local=local
        previous_global=wall
        last=complete["selected_snapshot"]
    return RecoveredPrefix(stage=state,last_selected_snapshot=last,
                           count=len(snapshots))
