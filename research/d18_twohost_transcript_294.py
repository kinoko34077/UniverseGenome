"""D18 #294: immutable, DATA-ONLY two-host original E1/E2 transcript.

No runner, worlds, interpreter or research seed is executed here. Admission
rows must FIRST be obtained from the source-bound completed D15 journal guard.
This ledger tracks the whole study, not just the last round's growth witness.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any, Mapping

from research.d16_twojob_run_control_217 import hash_of

SOURCE = re.compile(r"[a-f0-9]{40}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
SEED = 49152
MAX_GLOBAL_MS = 1_800_000
MAX_RETAINED = 512 * 1024 * 1024
FIRST_STAGE_END = 20
LAST_ROUND = 40
SCHEMA = "D18_ORIGINAL_TWOHOST_ADMITTED_TRANSCRIPT_V1"


def _check(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def _shape(row: Mapping[str, Any], source: str, ordinal: int, job: int) -> None:
    _check(isinstance(row, Mapping) and row.get("schema") ==
           "D18_NEW_SEED_NATIVE_JOURNAL_ADMISSION_V1", "not a D18 D15-admitted row")
    _check(row.get("source_sha") == source and row.get("seed") == SEED
           and type(row.get("ordinal")) is int and row["ordinal"] == ordinal
           and type(row.get("job")) is int and row["job"] == job,
           "D18 original source, seed, ordinal or job changed")
    _check(row.get("read_only") is True and row.get("learning_claim") is False,
           "D18 source evidence or learning boundary missing")
    _check(isinstance(row.get("selected_post_v7_sha256"),str) and
           bool(DIGEST.fullmatch(row["selected_post_v7_sha256"])),
           "D18 selected source-native optimizer-v7 hash missing")
    # E1 is the number of ELIGIBLE GROWTH CANDIDATES across native128
    # worlds. E2 is actual retirement, at most one per four categories.
    _check(type(row.get("E1_count")) is int and 0<=row["E1_count"]<=128,
           "D18 invalid original native128 E1 candidate count")
    _check(type(row.get("E2_count")) is int and 0<=row["E2_count"]<=4,
           "D18 invalid original at-most-four E2 retirement count")
    _check(row["E2_count"]<=row["E1_count"],
           "D18 source-native E2 cannot occur without E1")
    _check(type(row.get("journal_bytes")) is int and
           0 < row["journal_bytes"]<=128*1024*1024,
           "D18 original journal bound failed")
    _check(type(row.get("global_elapsed_ms")) is int and
           0<=row["global_elapsed_ms"]<=MAX_GLOBAL_MS,
           "D18 cross-host global clock out of budget")


@dataclass(frozen=True)
class OriginalD18Transcript:
    source_sha: str
    job: int = 1
    rows: tuple[dict[str, Any], ...] = ()
    stage1_digest: str | None = None
    result: str = "IN_PROGRESS"

    @classmethod
    def begin(cls, source_sha: str) -> "OriginalD18Transcript":
        _check(type(source_sha) is str and bool(SOURCE.fullmatch(source_sha)),
               "source must be pinned before any new seed outcome")
        return cls(source_sha=source_sha)

    @property
    def selected_round(self) -> int:
        return len(self.rows)

    @property
    def e1_ever(self) -> bool:
        return any(row["E1_count"] > 0 for row in self.rows)

    @property
    def e2_ever(self) -> bool:
        return any(row["E2_count"] > 0 for row in self.rows)

    def append(self, admission: Mapping[str, Any]) -> "OriginalD18Transcript":
        _check(self.result == "IN_PROGRESS","D18 terminal/handoff state is immutable")
        ordinal=self.selected_round+1
        _check(1<=ordinal<=LAST_ROUND and
               self.job == (1 if ordinal<=FIRST_STAGE_END else 2),
               "D18 two-host original partition exceeded")
        _shape(admission,self.source_sha,ordinal,self.job)
        if self.rows:
            prev=self.rows[-1]
            _check(admission["global_elapsed_ms"]>=prev["global_elapsed_ms"],
                   "D18 source clock moved backward between selected rounds")
        row={
            "schema":"D18_NEW_SEED_NATIVE_JOURNAL_ADMISSION_V1",
            "source_sha":self.source_sha,"seed":SEED,"ordinal":ordinal,
            "job":self.job,
            "selected_post_v7_sha256":admission["selected_post_v7_sha256"],
            "global_elapsed_ms":admission["global_elapsed_ms"],
            "journal_bytes":admission["journal_bytes"],
            "E1_count":admission["E1_count"],"E2_count":admission["E2_count"],
            "read_only":True,"learning_claim":False,
        }
        next_rows=self.rows+(row,)
        if ordinal==FIRST_STAGE_END:
            result="HANDOFF_READY"
        elif ordinal>=37 and any(item["E2_count"]>0 for item in next_rows):
            result="OBSERVED_E2_FINAL"
        elif ordinal==LAST_ROUND:
            result="E2_NOT_OBSERVED_FINAL"
        else:
            result="IN_PROGRESS"
        # No E1_ever inference from last round: it is retained across ALL rows.
        return replace(self,rows=next_rows,result=result)

    def stage1_manifest(self) -> dict[str, Any]:
        _check(self.job==1 and self.selected_round==FIRST_STAGE_END and
               self.result=="HANDOFF_READY","D18 handoff requires complete original round20")
        payload={
            "schema":SCHEMA,"source_sha":self.source_sha,"seed":SEED,
            "selected_round":FIRST_STAGE_END,
            "selected_v7_sha256":self.rows[-1]["selected_post_v7_sha256"],
            "global_elapsed_ms":self.rows[-1]["global_elapsed_ms"],
            "first20_rows_sha256":hash_of(list(self.rows)),
            "learning_claim":False,
        }
        return {**payload,"manifest_sha256":hash_of(payload)}

    def accept_second_host(self, inbound: Mapping[str, Any], *,
                           copied_rows: tuple[dict[str,Any], ...],
                           current_global_elapsed_ms: int) -> "OriginalD18Transcript":
        manifest=self.stage1_manifest()
        _check(isinstance(inbound, Mapping) and dict(inbound)==manifest,
               "D18 incoming immutable source/state handoff corrupted")
        _check(tuple(copied_rows)==self.rows and
               hash_of(list(copied_rows))==manifest["first20_rows_sha256"],
               "D18 original first20 rows missing or modified")
        _check(type(current_global_elapsed_ms) is int and
               manifest["global_elapsed_ms"]<=current_global_elapsed_ms<=MAX_GLOBAL_MS,
               "D18 elapsed UTC reset between hosts")
        return replace(self,job=2,stage1_digest=manifest["manifest_sha256"],
                       result="IN_PROGRESS")

    def verdict(self) -> dict[str, Any]:
        _check(self.result in ("OBSERVED_E2_FINAL","E2_NOT_OBSERVED_FINAL"),
               "D18 authentic terminal outcome not yet available")
        return {
            "schema":SCHEMA,"source_sha":self.source_sha,"seed":SEED,
            "rounds":self.selected_round,"first20_manifest_sha256":self.stage1_digest,
            "E1_ever_observed":self.e1_ever,
            "E2_ever_observed":self.e2_ever,
            "E1_first_round":next((r["ordinal"] for r in self.rows if r["E1_count"]),None),
            "E2_first_round":next((r["ordinal"] for r in self.rows if r["E2_count"]),None),
            "status":self.result,
            "final_selected_v7_sha256":self.rows[-1]["selected_post_v7_sha256"],
            "global_elapsed_ms":self.rows[-1]["global_elapsed_ms"],
            "learning_claim":False,
            "independent_generalization_claim":False,
            "admission_rows_are_from_original_journal":False,
            "provenance_limit":"Ledger is data-only; each row must be admitted from an actual source-verified full D15 journal separately.",
        }
