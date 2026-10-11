"""D16 #217 prospective two-job complete-state control (NO launch entrypoint).

This module does not execute a universe. It guards source-pinned completed
selected-v7 transfer, immutable two-job partition, and job/global time budgets.
Synthetic and exposed seed0 fixtures may test it; actual D16 seed16384 launch
must be separately authorized and connected only by a reviewed runner.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

SOURCE_RE = re.compile(r"[a-f0-9]{40}")
SHA_RE = re.compile(r"[a-f0-9]{64}")
CATEGORY_CAPACITY = (32, 32, 32, 32)
D16_SEED = 16384
FIRST_LAST_ROUND = 20
MAX_ROUNDS = 40
MIN_ROUNDS = 37
PREFERRED_GLOBAL_SECONDS = 1200
ABSOLUTE_GLOBAL_SECONDS = 1800
MAX_JOB_SECONDS = 18 * 60
MAX_TRANSFER_BYTES = 32 * 1024 * 1024
SCHEMA = "UniverseGenome.D16.CompleteSelectedTransfer.v1"


class D16BoundaryError(ValueError):
    """Required original-study invariant or evidence boundary did not hold."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise D16BoundaryError(reason)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def hash_of(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def plan_for_round(number: int) -> int:
    need(type(number) is int and 1 <= number <= MAX_ROUNDS,
         "original selected-round ordinal outside 1..40")
    return 1 if number <= FIRST_LAST_ROUND else 2


def classify_stop(number: int, *, mature_categories: Mapping[str, bool],
                  actual_replacements: int) -> str:
    """Decide at a completely selected original round, never mid-generation."""
    need(type(number) is int and 1 <= number <= MAX_ROUNDS, "round outside frozen horizon")
    need(len(mature_categories) == 4
         and all(type(k) is str and type(v) is bool
                 for k, v in mature_categories.items()), "exact four maturity observations required")
    need(type(actual_replacements) is int and 0 <= actual_replacements <= 4,
         "invalid native retirement count")
    if number < MIN_ROUNDS:
        return "CONTINUE"
    if all(mature_categories.values()) and actual_replacements > 0:
        return "OBSERVED_FINAL"
    if number == MAX_ROUNDS:
        return "NOT_OBSERVED_FINAL"
    return "CONTINUE"


def native_state_checked(snapshot: Mapping[str, Any], *,
                         expected_seed: int, expected_generation: int) -> str:
    """Recompute the original optimizer-v7 digest from unmodified native state."""
    need(type(expected_seed) is int and expected_seed in (0, D16_SEED),
         "unsupported source seed for test or dormant original study")
    need(type(expected_generation) is int and 0 <= expected_generation <= MAX_ROUNDS,
         "generation invalid")
    opt = SteadyStateOptimizer.from_snapshot(dict(snapshot))
    counts: dict[str, int] = {}
    for index, slot in enumerate(opt.slots):
        need(slot.index == index, "original slot order drift")
        counts[slot.category] = counts.get(slot.category, 0) + 1
    need(len(opt.slots) == 128 and sorted(counts.values()) == list(CATEGORY_CAPACITY),
         "original native 4x32/128 population changed")
    need(opt.generation == expected_generation
         and opt.search_plan.scheduler_base_seed == expected_seed,
         "original seed/generation drift")
    need(opt.experiment.to_dict() == ExperimentConfig().to_dict()
         and opt.base_config.to_dict() == PhysicsConfig().to_dict(),
         "original native default physics/experiment changed")
    need(opt.to_snapshot() == snapshot, "native optimizer-v7 snapshot not canonical")
    return digest(opt.to_snapshot())


@dataclass(frozen=True)
class GlobalClock:
    """Absolute UTC wall anchor carries between independent hosted runners.

    One job's local monotonic clock cannot represent inter-job queue/wait.
    UTC is cross-host, must be corroborated by actual GitHub job timestamps.
    """
    study_started_unix_ms: int
    prior_elapsed_ms: int = 0

    def __post_init__(self) -> None:
        need(type(self.study_started_unix_ms) is int
             and self.study_started_unix_ms > 1600000000000,
             "invalid study UTC anchor")
        need(type(self.prior_elapsed_ms) is int
             and 0 <= self.prior_elapsed_ms <= ABSOLUTE_GLOBAL_SECONDS * 1000,
             "previous elapsed time outside ceiling")

    def check(self, *, now_unix_ms: int, local_elapsed_ms: int) -> int:
        need(type(now_unix_ms) is int and type(local_elapsed_ms) is int,
             "wall/monotonic clocks must be integer milliseconds")
        need(local_elapsed_ms >= 0 and local_elapsed_ms <= MAX_JOB_SECONDS * 1000,
             "local job exceeded 18-minute boundary")
        elapsed = now_unix_ms - self.study_started_unix_ms
        need(self.prior_elapsed_ms <= elapsed <= ABSOLUTE_GLOBAL_SECONDS * 1000,
             "cross-job global wall budget exceeded or clock moved backwards")
        return elapsed


def make_transfer(*, source_sha: str, selected_snapshot: Mapping[str, Any],
                  seed: int, selected_round: int, clock: GlobalClock,
                  now_unix_ms: int, local_elapsed_ms: int,
                  observer_selected_digest: str,
                  ledger_sha: str) -> dict[str, Any]:
    need(isinstance(source_sha, str) and bool(SOURCE_RE.fullmatch(source_sha)),
         "exact source SHA required")
    need(seed in (0, D16_SEED) and type(seed) is int, "source seed invalid")
    need(type(selected_round) is int and selected_round in range(1, MAX_ROUNDS + 1),
         "completed original selected round missing")
    need(selected_round == (FIRST_LAST_ROUND if seed == D16_SEED else 1),
         "cross-job transfer requires original job1 round20 or test-only seed0 round1")
    need(bool(SHA_RE.fullmatch(observer_selected_digest)), "invalid native observer digest")
    need(bool(SHA_RE.fullmatch(ledger_sha)), "invalid observer ledger digest")
    elapsed = clock.check(now_unix_ms=now_unix_ms,
                          local_elapsed_ms=local_elapsed_ms)
    native_sha = native_state_checked(selected_snapshot, expected_seed=seed,
                                      expected_generation=selected_round)
    need(native_sha == observer_selected_digest,
         "authentic completed original D15 selected state differs from observer")
    manifest = {
        "schema": SCHEMA,
        "source_sha": source_sha,
        "seed": seed,
        "selected_round": selected_round,
        "job": plan_for_round(selected_round),
        "first_job_start_unix_ms": clock.study_started_unix_ms,
        "elapsed_global_ms": elapsed,
        "selected_snapshot_sha256": hash_of(selected_snapshot),
        "selected_native_v7_sha256": native_sha,
        "observer_ledger_sha256": ledger_sha,
        "experiment_sha256": hash_of(ExperimentConfig().to_dict()),
        "physics_sha256": hash_of(PhysicsConfig().to_dict()),
        "learning_claim": False,
    }
    need(len(canonical_bytes(selected_snapshot)) <= MAX_TRANSFER_BYTES,
         "full-v7 transfer exceeds declared bound")
    return manifest


def accept_transfer(*, manifest: Mapping[str, Any],
                    snapshot: Mapping[str, Any], actual_source: str,
                    expected_seed: int, expected_selected_round: int,
                    now_unix_ms: int) -> GlobalClock:
    need(set(manifest) == {
        "schema", "source_sha", "seed", "selected_round", "job",
        "first_job_start_unix_ms", "elapsed_global_ms",
        "selected_snapshot_sha256", "selected_native_v7_sha256",
        "observer_ledger_sha256", "experiment_sha256", "physics_sha256",
        "learning_claim",
    }, "transfer manifest unknown/missing fields")
    need(manifest["schema"] == SCHEMA
         and manifest["source_sha"] == actual_source
         and bool(SOURCE_RE.fullmatch(actual_source)),
         "transfer source mismatch")
    need(manifest["seed"] == expected_seed and type(expected_seed) is int
         and expected_seed in (0, D16_SEED), "transfer seed mismatch")
    need(manifest["selected_round"] == expected_selected_round
         and type(expected_selected_round) is int
         and manifest["job"] == plan_for_round(expected_selected_round),
         "transfer selected generation/job mismatch")
    need(expected_selected_round == (FIRST_LAST_ROUND if expected_seed == D16_SEED else 1),
         "handoff of nonterminal first-job state prohibited")
    need(manifest["learning_claim"] is False
         and manifest["experiment_sha256"] == hash_of(ExperimentConfig().to_dict())
         and manifest["physics_sha256"] == hash_of(PhysicsConfig().to_dict()),
         "transfer default scientific contract mismatch")
    need(len(canonical_bytes(snapshot)) <= MAX_TRANSFER_BYTES,
         "transfer too large")
    need(manifest["selected_snapshot_sha256"] == hash_of(snapshot)
         and bool(SHA_RE.fullmatch(manifest["observer_ledger_sha256"])),
         "transfer byte/observer ledger mismatch")
    actual = native_state_checked(snapshot, expected_seed=expected_seed,
                                  expected_generation=expected_selected_round)
    need(manifest["selected_native_v7_sha256"] == actual,
         "transfer native selected v7 mismatch")
    c = GlobalClock(manifest["first_job_start_unix_ms"],
                    manifest["elapsed_global_ms"])
    c.check(now_unix_ms=now_unix_ms, local_elapsed_ms=0)
    return c


def utc_now_ms() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)
