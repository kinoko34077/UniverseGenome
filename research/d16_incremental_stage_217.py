"""D16 #217 DORMANT incremental native selected-round stage composer.

No CLI, no workflow_dispatch, no GitHub API, no original seed16384 execution
without an externally supplied, separately authorized source-native evaluator.
Never changes D15 physics, optimizer, search or selection. Actual manual study
launch and hard hosted-job timeout are NOT provided here.

Use immutable source-bound prefix replay only at job start / same-host process
recovery. Within uninterrupted work, keep StageState and v7 selected snapshot
in memory instead of O(N^2) repeated full-prefix JSON parsing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import uuid
from typing import Any, Callable, Mapping

from research.d16_complete_round_checkpoint_217 import (
    read_completed, write_completed_atomic,
)
from research.d16_complete_prefix_recovery_217 import immutable_receipt
from research.d16_dormant_stage_driver_217 import (
    NativeCompletedEvaluator, prepare_dormant_state,
)
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, canonical_bytes, hash_of, make_transfer, need,
)
from research.d16_twojob_stage_fsm_217 import split_at

MAX_STUDY_RETAINED_BYTES=512*1024*1024
MAX_TRANSIENT_JOURNAL_BYTES=128*1024*1024
COMPLETE_TERMINALS={"OBSERVED_FINAL","NOT_OBSERVED_FINAL",
                    "FIXTURE_COMPLETE_NO_SCIENCE"}


def retained_bytes(root: Path) -> int:
    """Count all source-bound artifacts in the stage root, both jobs combined."""
    return sum(p.stat().st_size for p in Path(root).iterdir() if p.is_file())


def immutable_json(path: Path, payload: Mapping[str,Any]) -> None:
    """Atomic single-writer publication, never a replaceable verdict."""
    path=Path(path)
    data=canonical_bytes(dict(payload))+b"\n"
    temp=path.with_name("."+path.name+"-"+uuid.uuid4().hex+".tmp")
    try:
        with temp.open("xb") as writer:
            writer.write(data)
            writer.flush()
            os.fsync(writer.fileno())
        os.link(temp,path)
        folderfd=os.open(path.parent,os.O_RDONLY)
        try:
            os.fsync(folderfd)
        finally:
            os.close(folderfd)
    finally:
        temp.unlink(missing_ok=True)


def run_dormant_stage(
    *, root: Path, source_sha: str, seed: int,
    original_genesis: Mapping[str,Any], study_started_unix_ms: int,
    job: int, now_unix_ms: Callable[[],int],
    local_elapsed_ms: Callable[[],int],
    native_completed_evaluator: NativeCompletedEvaluator,
    source_bound_inbound_manifest: Mapping[str,Any] | None = None,
    max_new_rounds: int | None = None,
) -> dict[str,Any]:
    """Testable original stage loop; NO built-in effectful study executor.

    An approved external script must pin actual Git checkout/source and supply
    the original D15 observer-verifying source evaluator and hosted hard caps.
    A trial/injected fake result CANNOT authenticate scientific provenance.
    """
    need(type(seed) is int and seed in (0,16384),
         "only exposed fixture0 or originally frozen science seed16384")
    need(type(job) is int and job in (1,2),"only exactly two original hosted jobs")
    need(max_new_rounds is None or
         (type(max_new_rounds) is int and 1 <= max_new_rounds <= 20),
         "bounded same-job work unit must have <=20 original selected rounds")
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    restored=prepare_dormant_state(
        folder=root,source_sha=source_sha,seed=seed,
        original_genesis=original_genesis,
        study_started_unix_ms=study_started_unix_ms,job=job,
        now_unix_ms=now_unix_ms(),
        source_bound_inbound_manifest=source_bound_inbound_manifest,
    )
    state=restored.stage
    previous=restored.last_selected_snapshot
    if previous is None:
        previous=original_genesis
    before_new=state.selected_round
    end_of_job=split_at(seed) if job==1 else (2 if seed==0 else 40)

    while state.result=="IN_PROGRESS" and state.selected_round < end_of_job:
        ordinal=state.selected_round+1
        state.global_clock.check(now_unix_ms=now_unix_ms(),
                                 local_elapsed_ms=local_elapsed_ms())
        # The INJECTED evaluator (future accepted original D15 source) must
        # already have checked the complete original selected128 source state.
        complete=native_completed_evaluator(ordinal,previous,state.global_clock)
        after=state.append(
            complete=complete,now_unix_ms=now_unix_ms(),
            local_elapsed_ms=local_elapsed_ms(),
        )
        # Immutable complete selection first, separate time-bound receipt
        # second. If crash splits them, replay FAILS CLOSED on the orphan.
        write_completed_atomic(root,complete)
        immutable_receipt(
            root,source_sha=source_sha,seed=seed,ordinal=ordinal,job=job,
            clock=state.global_clock,now_unix_ms=now_unix_ms(),
            local_elapsed_ms=local_elapsed_ms(),
        )
        state=after
        previous=complete["selected_snapshot"]
        if retained_bytes(root)+MAX_TRANSIENT_JOURNAL_BYTES>MAX_STUDY_RETAINED_BYTES:
            raise D16BoundaryError("whole original study retained evidence incl journal bound exceeded")
        if max_new_rounds is not None and state.selected_round-before_new >= max_new_rounds:
            break

    status=state.result
    if job==1 and status=="HANDOFF_READY":
        complete=read_completed(
            root/f"selected-round-{split_at(seed):02d}.json",
            source_sha=source_sha,seed=seed,ordinal=split_at(seed),
        )
        manifest=make_transfer(
            source_sha=source_sha,
            selected_snapshot=complete["selected_snapshot"],
            seed=seed,selected_round=state.selected_round,
            clock=state.global_clock,now_unix_ms=now_unix_ms(),
            local_elapsed_ms=local_elapsed_ms(),
            observer_selected_digest=complete["selected_v7_sha256"],
            ledger_sha=hash_of(complete["d15_verified_observer"]),
        )
        immutable_json(root/"original-job1-selected-transfer.json",manifest)
    elif job==2 and status in COMPLETE_TERMINALS:
        outcome={
            "schema":"D16_ORIGINAL_TERMINAL_BY_SOURCE_EVIDENCE_V1",
            "source_sha":source_sha,"seed":seed,
            "last_completed_round":state.selected_round,
            "stage_result":status,
            "global_elapsed_ms":state.last_global_elapsed_ms,
            "preferred_1200_met":(
                seed==16384 and state.last_global_elapsed_ms <= 1200*1000
            ),
            "original_seed16384_executed":seed==16384,
            "learning_claim":False,
            "provenance_authenticated":False,
        }
        immutable_json(root/"terminal-verdict.json",outcome)
    return {
        "stage_result":status,"last_completed_round":state.selected_round,
        "new_complete_selections":state.selected_round-before_new,
        "study_global_elapsed_ms":state.last_global_elapsed_ms,
        "source_sha":source_sha,"seed":seed,
        "original_science_outcome_claimed":False,
        "independent_provenance_authenticated":False,
    }
