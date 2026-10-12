"""D16 #217 DORMANT incremental two-stage original-selection composition.

Never dispatches an Action or starts reserved seed16384 evolution by itself.
The only evaluator is explicitly injected by a separately authorized caller.
All progress derives from original D15 source-bound COMPLETE selected evidence.

An uninterrupted hosted job replays its immutable prefix ONCE on open(), then
advances in memory; it never performs a quadratic replay per selected round.
A process may reopen the SAME hosted job; a failed job must not create job3.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from research.d16_complete_prefix_recovery_217 import immutable_receipt
from research.d16_complete_round_checkpoint_217 import (
    MAX_COMPLETED_BUNDLE_BYTES, write_completed_atomic, read_completed,
)
from research.d16_dormant_stage_driver_217 import (
    AcceptedStep, NativeCompletedEvaluator, prepare_dormant_state,
)
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, hash_of, make_transfer, need,
)
from research.d16_twojob_stage_fsm_217 import StageState, split_at

MAX_RETAINED_STUDY_BYTES = 512 * 1024 * 1024
RECEIPT_RESERVE_BYTES = 4096


def retained_bytes(folder: Path) -> int:
    """Both hosted stages use one logical prefix; report all persisted bytes."""
    return sum(p.stat().st_size for p in Path(folder).iterdir() if p.is_file())


@dataclass
class DormantIncrementalStage:
    folder: Path
    source_sha: str
    seed: int
    job: int
    stage: StageState
    last_selected_snapshot: Mapping[str, Any] | None
    now_unix_ms: Callable[[], int]
    local_elapsed_ms: Callable[[], int]
    native_completed_evaluator: NativeCompletedEvaluator
    reopened_completed_count: int

    @classmethod
    def open(
        cls, *, folder: Path, source_sha: str, seed: int, job: int,
        original_genesis: Mapping[str, Any],
        study_started_unix_ms: int,
        now_unix_ms: Callable[[], int],
        local_elapsed_ms: Callable[[], int],
        native_completed_evaluator: NativeCompletedEvaluator,
        source_bound_inbound_manifest: Mapping[str, Any] | None = None,
    ) -> "DormantIncrementalStage":
        """Replay exactly once and admit only the original authorized stage."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        need(type(job) is int and job in (1, 2), "only two hosted jobs authorized")
        need(type(seed) is int and seed in (0, 16384),
             "only exposed seed0 fixture or original seed16384")
        before = retained_bytes(folder)
        need(before <= MAX_RETAINED_STUDY_BYTES, "whole original study retention exceeded")
        recovered = prepare_dormant_state(
            folder=folder, source_sha=source_sha, seed=seed,
            original_genesis=original_genesis,
            study_started_unix_ms=study_started_unix_ms, job=job,
            now_unix_ms=now_unix_ms(),
            source_bound_inbound_manifest=source_bound_inbound_manifest,
        )
        recovered.stage.global_clock.check(
            now_unix_ms=now_unix_ms(), local_elapsed_ms=local_elapsed_ms(),
        )
        need(recovered.stage.result == "IN_PROGRESS",
             "already terminal original stage cannot restart/advance")
        return cls(
            folder, source_sha, seed, job, recovered.stage,
            recovered.last_selected_snapshot or original_genesis,
            now_unix_ms, local_elapsed_ms, native_completed_evaluator,
            recovered.count,
        )

    def advance(self) -> AcceptedStep:
        """Evaluate once, verify original native D15 ledger, commit, then receipt.

        A crash before selected/receipt publication is never reported as
        accepted. Orphan selected files fail closed on any later replay.
        """
        need(self.stage.job == self.job and self.stage.result == "IN_PROGRESS",
             "original stage not advanceable; no third job or extra selection")
        ordinal = self.stage.selected_round + 1
        need(ordinal <= (split_at(self.seed) if self.job == 1
                         else (2 if self.seed == 0 else 40)),
             "selected round exceeds frozen hosted-stage boundary")
        self.stage.global_clock.check(
            now_unix_ms=self.now_unix_ms(), local_elapsed_ms=self.local_elapsed_ms(),
        )
        need(retained_bytes(self.folder) + MAX_COMPLETED_BUNDLE_BYTES
             + RECEIPT_RESERVE_BYTES <= MAX_RETAINED_STUDY_BYTES,
             "insufficient whole-study retained evidence admission")
        complete = self.native_completed_evaluator(
            ordinal, self.last_selected_snapshot, self.stage.global_clock,
        )
        accepted = self.stage.append(
            complete=complete, now_unix_ms=self.now_unix_ms(),
            local_elapsed_ms=self.local_elapsed_ms(),
        )
        selected_file = write_completed_atomic(self.folder, complete)
        receipt_file = immutable_receipt(
            self.folder, source_sha=self.source_sha, seed=self.seed,
            ordinal=ordinal, job=self.job, clock=self.stage.global_clock,
            now_unix_ms=self.now_unix_ms(),
            local_elapsed_ms=self.local_elapsed_ms(),
        )
        # Publication succeeded. The next failure must preserve this complete
        # prefix as evidence; never quietly redo a selected round.
        self.stage = accepted
        self.last_selected_snapshot = complete["selected_snapshot"]
        need(retained_bytes(self.folder) <= MAX_RETAINED_STUDY_BYTES,
             "whole-study retained evidence bound exceeded after selected commit")
        return AcceptedStep(accepted, selected_file, receipt_file, False)

    def run_to_stage_end(self) -> StageState:
        """Dormant library loop. No CLI/Action/seed authorization is supplied."""
        while self.stage.result == "IN_PROGRESS":
            self.advance()
        return self.stage

    def verified_handoff(self) -> dict[str, Any]:
        """For exactly complete first hosted stage; no simulated boundary."""
        need(self.job == 1 and self.stage.result == "HANDOFF_READY"
             and self.stage.selected_round == split_at(self.seed),
             "original first stage not ready for frozen two-job handoff")
        complete = read_completed(
            self.folder / f"selected-round-{self.stage.selected_round:02d}.json",
            source_sha=self.source_sha, seed=self.seed,
            ordinal=self.stage.selected_round,
        )
        need(complete["selected_v7_sha256"] == self.stage.selected_v7_sha256,
             "first-host original state differs from source-bound selected receipt")
        return make_transfer(
            source_sha=self.source_sha,
            selected_snapshot=complete["selected_snapshot"],
            seed=self.seed,
            selected_round=self.stage.selected_round,
            clock=self.stage.global_clock,
            now_unix_ms=self.now_unix_ms(),
            local_elapsed_ms=self.local_elapsed_ms(),
            observer_selected_digest=complete["selected_v7_sha256"],
            ledger_sha=hash_of(complete["d15_verified_observer"]),
        )
