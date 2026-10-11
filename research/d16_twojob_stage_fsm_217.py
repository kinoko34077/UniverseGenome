"""D16 #217 dormant, data-only two-job selected-round stage state machine.

This module never invokes D15, never executes original seed16384 physical
evolution, and cannot dispatch a GitHub workflow. Only an independently
verified, completely selected original D15 round may enter append().
Synthetic tests do NOT establish authenticity or scientific claims.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, classify_stop, native_state_checked,
    plan_for_round, need,
)
from research.d8_genome_diversity_190 import digest

FULL_KIND = "D16_ORIGINAL_COMPLETED_SELECTED128_ROUND_CHECKPOINT_V1"


@dataclass(frozen=True)
class StageState:
    source_sha: str
    seed: int
    job: int
    selected_round: int
    selected_v7_sha256: str
    global_clock: GlobalClock
    mature_categories: tuple[str, ...]
    observed_native_retirements: int
    last_global_elapsed_ms: int
    result: str = "IN_PROGRESS"

    @classmethod
    def start(cls, *, source_sha: str, seed: int,
              original_genesis: Mapping[str, Any],
              job1_start_unix_ms: int) -> "StageState":
        digest_v7 = native_state_checked(original_genesis,
                                         expected_seed=seed, expected_generation=0)
        return cls(source_sha=source_sha, seed=seed, job=1, selected_round=0,
                   selected_v7_sha256=digest_v7,
                   global_clock=GlobalClock(job1_start_unix_ms),
                   mature_categories=(), observed_native_retirements=0,
                   last_global_elapsed_ms=0)

    def append(self, *, complete: Mapping[str, Any], now_unix_ms: int,
               local_elapsed_ms: int) -> "StageState":
        need(self.result == "IN_PROGRESS", "no further selection after terminal/handoff")
        ordinal = self.selected_round + 1
        need(self.job == plan_for_round(ordinal),
             "original study crossed 20-round job without validated handoff")
        elapsed = self.global_clock.check(now_unix_ms=now_unix_ms,
                                          local_elapsed_ms=local_elapsed_ms)
        need(elapsed >= self.last_global_elapsed_ms,
             "completed source evidence global timestamp regressed")
        need(complete.get("kind") == FULL_KIND
             and complete.get("source_sha") == self.source_sha
             and complete.get("seed") == self.seed
             and complete.get("ordinal") == ordinal
             and complete.get("learning_claim") is False,
             "not next original source-bound completely selected round")
        selected = complete.get("selected_snapshot")
        need(isinstance(selected, Mapping), "missing selected optimizer-v7 state")
        sha = native_state_checked(selected, expected_seed=self.seed,
                                   expected_generation=ordinal)
        need(sha == complete.get("selected_v7_sha256"),
             "native selected-v7 digest mismatch")
        observer = complete.get("d15_verified_observer")
        need(isinstance(observer, Mapping)
             and observer.get("source_commit") == self.source_sha
             and observer.get("base_seed") == self.seed
             and observer.get("before_optimizer_generation") == ordinal-1
             and observer.get("selected_optimizer_generation") == ordinal
             and observer.get("selected_post_v7_sha256") == sha
             and observer.get("evaluated_native_worlds") == 128
             and observer.get("selected_native_worlds") == 128
             and observer.get("d15_journal_chain_verified") is True
             and observer.get("original_selected_once_proven_by_D15_final") is True,
             "missing original D15 verified evaluation/selection provenance")
        categories = observer.get("categories")
        need(isinstance(categories, Mapping) and len(categories) == 4,
             "not four original source-native category observations")
        mature = set(self.mature_categories)
        for category, data in categories.items():
            need(isinstance(category, str) and isinstance(data, Mapping),
                 "malformed native category observer")
            n = data.get("complete_nonfailure_count")
            need(type(n) is int and 0 <= n <= 32,
                 "invalid complete nonfailure evidence count")
            if n:
                need(ordinal >= 37, "four-window maturity claimed before genuine37")
                mature.add(category)
        retiring = observer.get("actual_native_replacement_count")
        need(type(retiring) is int and 0 <= retiring <= 4,
             "actual native retirement invalid")
        total_retirements = self.observed_native_retirements + retiring
        status = ("HANDOFF_READY" if ordinal == 20 else
                  classify_stop(ordinal,
                                mature_categories={name: name in mature
                                                  for name in categories},
                                actual_replacements=min(total_retirements,4))
                  if ordinal >= 37 else "IN_PROGRESS")
        return replace(self, selected_round=ordinal, selected_v7_sha256=sha,
                       mature_categories=tuple(sorted(mature)),
                       observed_native_retirements=total_retirements,
                       last_global_elapsed_ms=elapsed, result=status)

    def accept_second_job(self, *, verified_selected20_v7: str,
                          clock_from_immutable_manifest: GlobalClock,
                          now_unix_ms: int) -> "StageState":
        need(self.job == 1 and self.selected_round == 20
             and self.result == "HANDOFF_READY"
             and self.selected_v7_sha256 == verified_selected20_v7,
             "must handoff precisely a complete source-bound original round20")
        need(clock_from_immutable_manifest.study_started_unix_ms ==
             self.global_clock.study_started_unix_ms
             and clock_from_immutable_manifest.prior_elapsed_ms >=
             self.last_global_elapsed_ms, "study-global job2 clock reset or altered")
        clock_from_immutable_manifest.check(now_unix_ms=now_unix_ms,
                                            local_elapsed_ms=0)
        return replace(self, job=2, global_clock=clock_from_immutable_manifest,
                       result="IN_PROGRESS")
