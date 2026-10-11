"""D16 #217 dormant one-COMPLETE-selection stage adapter, no science launcher.

Consumes an INJECTED already original-D15-verifying round evaluator; this
module itself never dispatches GitHub Actions or evolves reserved seed16384.
An extra hosted job after failure is NOT authorized: replay is exclusively
for the SAME still-authorized job/process replacement and frozen UTC budget.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from research.d16_complete_round_checkpoint_217 import (
    read_completed, write_completed_atomic,
)
from research.d16_complete_prefix_recovery_217 import (
    RecoveredPrefix, immutable_receipt, replay_completed_prefix,
)
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, accept_transfer, hash_of, need,
)
from research.d16_twojob_stage_fsm_217 import StageState, split_at

NativeCompletedEvaluator = Callable[
    [int, Mapping[str, Any] | None, GlobalClock], dict[str, Any]
]


@dataclass(frozen=True)
class AcceptedStep:
    stage: StageState
    selected_file: Path
    receipt_file: Path
    provenance_authenticated: bool = False

    @property
    def last_completed_selected_round(self) -> int:
        return self.stage.selected_round


def prepare_dormant_state(*, folder: Path, source_sha: str, seed: int,
                          original_genesis: Mapping[str, Any],
                          study_started_unix_ms: int, job: int,
                          now_unix_ms: int,
                          source_bound_inbound_manifest: Mapping[str, Any] | None,
                          ) -> RecoveredPrefix:
    """Verify every recovered complete selected round before ANY evaluator.

    Job2 must carry a manifest authenticated against job1 original committed
    round20 (or explicit exposed test seed0 round1); it cannot reset the
    first hosted job's absolute clock or derive progress from a partial patch.
    """
    recovered = replay_completed_prefix(
        folder, source_sha=source_sha, seed=seed,
        original_genesis=original_genesis,
        study_started_unix_ms=study_started_unix_ms,
    )
    state = recovered.stage
    if job == 1:
        need(state.job == 1 and state.result == "IN_PROGRESS"
             and source_bound_inbound_manifest is None,
             "original first job cannot use a second-job handoff or terminal prefix")
        return recovered
    need(job == 2 and source_bound_inbound_manifest is not None,
         "original source-bound second-job manifest required")
    boundary = split_at(seed)
    need(recovered.count >= boundary,
         "second hosted job cannot start before complete selected original boundary")
    selected = read_completed(
        Path(folder)/f"selected-round-{boundary:02d}.json",
        source_sha=source_sha,seed=seed,ordinal=boundary,
    )
    manifest = dict(source_bound_inbound_manifest)
    need(manifest.get("observer_ledger_sha256") ==
         hash_of(selected["d15_verified_observer"]),
         "hosted handoff actual native D15 observer ledger hash mismatch")
    accepted_clock = accept_transfer(
        manifest=manifest,snapshot=selected["selected_snapshot"],
        actual_source=source_sha,expected_seed=seed,
        expected_selected_round=boundary,now_unix_ms=now_unix_ms,
    )
    boundary_receipt=json.loads(
        (Path(folder)/f"selected-receipt-{boundary:02d}.json").read_bytes()
    )
    need(accepted_clock.study_started_unix_ms == study_started_unix_ms
         and accepted_clock.study_started_unix_ms ==
         state.global_clock.study_started_unix_ms
         and accepted_clock.prior_elapsed_ms >=
         boundary_receipt["global_elapsed_ms"],
         "replayed first-host clock/elapsed time was reset")
    if state.job == 1:
        state = state.accept_second_job(
            verified_selected20_v7=selected["selected_v7_sha256"],
            clock_from_immutable_manifest=accepted_clock,
            now_unix_ms=now_unix_ms,
        )
    need(state.job == 2 and state.result == "IN_PROGRESS",
         "second hosted job not in correct source-native progress state")
    return RecoveredPrefix(
        stage=state,last_selected_snapshot=recovered.last_selected_snapshot,
        count=recovered.count,
        provenance_authenticated=False,
    )


def advance_one_verified_complete_round(
    *, folder: Path, source_sha: str, seed: int,
    original_genesis: Mapping[str, Any], study_started_unix_ms: int,
    job: int, now_unix_ms: Callable[[], int],
    local_elapsed_ms: Callable[[], int],
    native_completed_evaluator: NativeCompletedEvaluator,
    source_bound_inbound_manifest: Mapping[str, Any] | None = None,
) -> AcceptedStep:
    """Single committed original selected128 native round then progress receipt.

    No while loop and no original seed16384 process is started by this
    function alone: live native evaluation is supplied by an approved caller.
    A failed or partial evaluation publishes no new selected state. A crash
    AFTER selected state but BEFORE receipt leaves an orphan and blocks silent
    reuse until explicitly reconciled.
    """
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    ready=prepare_dormant_state(
        folder=folder,source_sha=source_sha,seed=seed,
        original_genesis=original_genesis,
        study_started_unix_ms=study_started_unix_ms,job=job,
        now_unix_ms=now_unix_ms(),
        source_bound_inbound_manifest=source_bound_inbound_manifest,
    )
    stage=ready.stage
    ordinal=stage.selected_round+1
    stage.global_clock.check(now_unix_ms=now_unix_ms(),
                             local_elapsed_ms=local_elapsed_ms())
    selected=native_completed_evaluator(
        ordinal,ready.last_selected_snapshot,stage.global_clock,
    )
    stage_next=stage.append(
        complete=selected,now_unix_ms=now_unix_ms(),
        local_elapsed_ms=local_elapsed_ms(),
    )
    full_file=write_completed_atomic(folder,selected)
    receipt_file=immutable_receipt(
        folder,source_sha=source_sha,seed=seed,ordinal=ordinal,job=job,
        clock=stage.global_clock,now_unix_ms=now_unix_ms(),
        local_elapsed_ms=local_elapsed_ms(),
    )
    return AcceptedStep(stage_next,full_file,receipt_file,False)
