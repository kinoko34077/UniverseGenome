"""D18 #294: pure two-host state machine for ONE prospectively frozen seed49152 study.

Consumes only source-authenticated D18 per-round admission receipts. It NEVER
evaluates a world, launches a workflow, writes a journal, or changes native
selection. Synthetic fixtures test structure only, not physical reachability.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from research.d16_twojob_run_control_217 import GlobalClock

SEED = 49152
FIRST_LAST = 20
MAX_ROUNDS = 40
MIN_TERMINAL = 37
SOURCE_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
GENESIS_CHAIN = "0" * 64
SCHEMA = "D18_PROSPECTIVE_NATIVE_TWOHOST_STAGE_V1"
ADMISSION_SCHEMA = "D18_NEW_SEED_NATIVE_JOURNAL_ADMISSION_V1"


def need(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def hash_receipt(prior_chain: str, row: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(row), sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(prior_chain.encode("ascii") + b"\n" + raw).hexdigest()


@dataclass(frozen=True)
class D18TwoHostState:
    source_sha: str
    job: int
    ordinal: int
    started_unix_ms: int
    last_global_elapsed_ms: int
    last_selected_v7: str | None
    receipt_chain_sha256: str
    saw_growth_candidate_E1: bool
    saw_real_growth_retirement_E2: bool
    status: str

    @classmethod
    def first_host(cls, *, source_sha: str, started_unix_ms: int) -> "D18TwoHostState":
        need(isinstance(source_sha, str) and bool(SOURCE_PATTERN.fullmatch(source_sha)),
             "D18 must freeze an exact current source SHA")
        GlobalClock(started_unix_ms, 0)
        return cls(source_sha, 1, 0, started_unix_ms, 0, None, GENESIS_CHAIN,
                   False, False, "IN_PROGRESS")

    @classmethod
    def from_verified_handoff(
        cls, manifest: Mapping[str, Any], *, expected_source_sha: str
    ) -> "D18TwoHostState":
        need(isinstance(manifest, Mapping) and manifest.get("schema") == SCHEMA,
             "D18 stage2 needs original stage1 handoff schema")
        need(manifest.get("source_sha") == expected_source_sha
             and isinstance(expected_source_sha, str)
             and bool(SOURCE_PATTERN.fullmatch(expected_source_sha)),
             "D18 cross-host source SHA change")
        need(manifest.get("seed") == SEED and type(manifest.get("seed")) is int
             and manifest.get("stage1_job") == 1
             and manifest.get("selected_round") == FIRST_LAST
             and isinstance(manifest.get("selected_v7"), str)
             and bool(DIGEST_PATTERN.fullmatch(manifest["selected_v7"]))
             and isinstance(manifest.get("receipt_chain_sha256"), str)
             and bool(DIGEST_PATTERN.fullmatch(manifest["receipt_chain_sha256"]))
             and type(manifest.get("e1_seen")) is bool
             and type(manifest.get("e2_seen")) is bool,
             "D18 cross-host stage1 witness invalid")
        GlobalClock(manifest["started_unix_ms"], manifest["global_elapsed_ms"])
        need(manifest["global_elapsed_ms"] > 0, "D18 stage1 must actually complete")
        # Handoff object is NOT self-authenticating; receiving launcher must
        # reverify original stage1 20 complete source-locked D15 receipts.
        return cls(expected_source_sha, 2, FIRST_LAST,
                   manifest["started_unix_ms"], manifest["global_elapsed_ms"],
                   manifest["selected_v7"], manifest["receipt_chain_sha256"],
                   manifest["e1_seen"], manifest["e2_seen"], "IN_PROGRESS")

    def append(self, source_admitted: Mapping[str, Any]) -> "D18TwoHostState":
        need(self.status == "IN_PROGRESS" and self.job in (1, 2),
             "D18 cannot append terminal job or third job")
        need(isinstance(source_admitted, Mapping)
             and source_admitted.get("schema") == ADMISSION_SCHEMA
             and source_admitted.get("source_sha") == self.source_sha
             and type(source_admitted.get("seed")) is int
             and source_admitted.get("seed") == SEED
             and type(source_admitted.get("ordinal")) is int
             and source_admitted.get("ordinal") == self.ordinal + 1
             and type(source_admitted.get("job")) is int
             and source_admitted.get("job") == self.job
             and source_admitted.get("read_only") is True
             and source_admitted.get("learning_claim") is False,
             "D18 native admitted source/seed/job/contiguous round mismatch")
        new_number = self.ordinal + 1
        need(new_number <= (FIRST_LAST if self.job == 1 else MAX_ROUNDS),
             "D18 may not cross the two original hosted partitions")
        sha = source_admitted.get("selected_post_v7_sha256")
        need(isinstance(sha, str) and bool(DIGEST_PATTERN.fullmatch(sha)),
             "D18 original selected-v7 hash missing")
        elapsed = source_admitted.get("global_elapsed_ms")
        need(type(elapsed) is int
             and self.last_global_elapsed_ms <= elapsed <= 1800000,
             "D18 cross-host global wall clock not monotone or over budget")
        journal_size = source_admitted.get("journal_bytes")
        need(type(journal_size) is int and 0 < journal_size <= 128 * 1024 * 1024,
             "D18 original native128 sparse journal exceeds budget")
        e1 = source_admitted.get("E1_count")
        e2 = source_admitted.get("E2_count")
        need(type(e1) is int and type(e2) is int
             and 0 <= e1 <= 128 and 0 <= e2 <= 4 and e2 <= e1,
             "D18 native E1/E2 counts invalid")
        own_status = source_admitted.get("status")
        need(own_status in ("CONTINUE", "OBSERVED_E2_FINAL",
                            "E2_NOT_OBSERVED_FINAL"),
             "D18 individual authentic journal stop class invalid")
        saw_e1 = self.saw_growth_candidate_E1 or bool(e1)
        saw_e2 = self.saw_real_growth_retirement_E2 or bool(e2)
        status = "IN_PROGRESS"
        if self.job == 1 and new_number == FIRST_LAST:
            status = "HANDOFF_READY"
        if self.job == 2 and new_number >= MIN_TERMINAL:
            if saw_e2:
                status = "E2_CONFIRMED_FINAL"
            elif new_number == MAX_ROUNDS:
                status = "E1_ONLY_FINAL" if saw_e1 else "NO_E1_FINAL"
        # Per-round observer must have used the source-native single-round
        # verdict, while this FSM aggregates the ENTIRE contiguous cohort.
        if (new_number < MIN_TERMINAL and own_status != "CONTINUE"
                or new_number >= MIN_TERMINAL and e2 > 0
                and own_status != "OBSERVED_E2_FINAL"
                or new_number == MAX_ROUNDS and e2 == 0
                and own_status != "E2_NOT_OBSERVED_FINAL"):
            raise ValueError("D18 per-round and cumulative terminal evidence disagree")
        return replace(
            self, ordinal=new_number, last_global_elapsed_ms=elapsed,
            last_selected_v7=sha,
            receipt_chain_sha256=hash_receipt(self.receipt_chain_sha256, source_admitted),
            saw_growth_candidate_E1=saw_e1, saw_real_growth_retirement_E2=saw_e2,
            status=status,
        )

    def transfer_manifest(self) -> dict[str, Any]:
        need(self.job == 1 and self.ordinal == FIRST_LAST
             and self.status == "HANDOFF_READY"
             and self.last_selected_v7 is not None,
             "D18 no handoff before all twenty authentic original selected rounds")
        return {
            "schema": SCHEMA, "source_sha": self.source_sha, "seed": SEED,
            "stage1_job": 1, "selected_round": FIRST_LAST,
            "started_unix_ms": self.started_unix_ms,
            "global_elapsed_ms": self.last_global_elapsed_ms,
            "selected_v7": self.last_selected_v7,
            "receipt_chain_sha256": self.receipt_chain_sha256,
            "e1_seen": self.saw_growth_candidate_E1,
            "e2_seen": self.saw_real_growth_retirement_E2,
            "learning_claim": False,
        }
