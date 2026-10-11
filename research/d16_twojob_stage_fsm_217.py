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
    plan_for_round, need, SOURCE_RE,
)
from research.d8_genome_diversity_190 import digest

FULL_KIND = "D16_ORIGINAL_COMPLETED_SELECTED128_ROUND_CHECKPOINT_V1"


def split_at(seed: int) -> int:
    """Only exposed benchmark seed0 has a tiny 1+1 test fixture partition."""
    need(type(seed) is int and seed in (0,16384),
         "unsupported study seed or test-only benchmark")
    return 1 if seed == 0 else 20


@dataclass(frozen=True)
class StageState:
    source_sha: str
    seed: int
    job: int
    selected_round: int
    selected_v7_sha256: str
    category_names: tuple[str, ...]
    global_clock: GlobalClock
    mature_categories: tuple[str, ...]
    observed_native_retirements: int
    last_global_elapsed_ms: int
    result: str = "IN_PROGRESS"

    @classmethod
    def start(cls, *, source_sha: str, seed: int,
              original_genesis: Mapping[str, Any],
              job1_start_unix_ms: int) -> "StageState":
        need(isinstance(source_sha,str) and bool(SOURCE_RE.fullmatch(source_sha)),
             "pinned exact source SHA required")
        digest_v7 = native_state_checked(original_genesis,
                                         expected_seed=seed, expected_generation=0)
        from search.evolution import SteadyStateOptimizer
        genesis = SteadyStateOptimizer.from_snapshot(dict(original_genesis))
        categories = tuple(sorted(set(s.category for s in genesis.slots)))
        need(len(categories)==4,"native original four category names not established")
        return cls(source_sha=source_sha, seed=seed, job=1, selected_round=0,
                   selected_v7_sha256=digest_v7,
                   category_names=categories,
                   global_clock=GlobalClock(job1_start_unix_ms),
                   mature_categories=(), observed_native_retirements=0,
                   last_global_elapsed_ms=0)

    def append(self, *, complete: Mapping[str, Any], now_unix_ms: int,
               local_elapsed_ms: int) -> "StageState":
        need(self.result == "IN_PROGRESS", "no further selection after terminal/handoff")
        ordinal = self.selected_round + 1
        boundary = split_at(self.seed)
        need(ordinal <= (2 if self.seed == 0 else 40)
             and self.job == (1 if ordinal <= boundary else 2),
             "frozen original 20+20 or exposed seed0 1+1 partition violated")
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
        need(isinstance(categories, Mapping)
             and tuple(sorted(categories)) == self.category_names,
             "not original source-native four frozen category observations")
        mature = set(self.mature_categories)
        for category, data in categories.items():
            need(isinstance(category, str) and isinstance(data, Mapping),
                 "malformed native category observer")
            n = data.get("complete_nonfailure_count")
            need(type(n) is int and 0 <= n <= 32,
                 "invalid complete nonfailure evidence count")
            replacement = data.get("native_replacement_count")
            need(type(replacement) is int and 0 <= replacement <= 1,
                 "original native finalizer may retire at most one per category")
            if n:
                need(ordinal >= 37, "four-window maturity claimed before genuine37")
                mature.add(category)
        retiring = observer.get("actual_native_replacement_count")
        need(type(retiring) is int and 0 <= retiring <= 4
             and retiring == sum(data.get("native_replacement_count", -1)
                                  for data in categories.values()),
             "actual native retirement / per-category observer inconsistent")
        # A category's early absolute-failure retirement or a retirement in
        # a DIFFERENT immature category does not prove mature native pruning.
        # Require an actual source-observed retirement in a category with its
        # own complete four-window growth history at/after round37.
        mature_retiring = sum(
            data["native_replacement_count"] for data in categories.values()
            if ordinal >= 37 and data["complete_nonfailure_count"] > 0
        )
        total_retirements = self.observed_native_retirements + mature_retiring
        status = (
            "HANDOFF_READY" if ordinal == boundary else
            "FIXTURE_COMPLETE_NO_SCIENCE" if self.seed == 0 and ordinal == 2 else
            classify_stop(ordinal,
                          mature_categories={name: name in mature for name in categories},
                          actual_replacements=min(total_retirements,4))
            if ordinal >= 37 else "IN_PROGRESS"
        )
        # The frozen terminal predicate's CONTINUE means the FSM remains
        # IN_PROGRESS and must accept the next complete selected round.
        if status == "CONTINUE":
            status = "IN_PROGRESS"
        return replace(self, selected_round=ordinal, selected_v7_sha256=sha,
                       mature_categories=tuple(sorted(mature)),
                       observed_native_retirements=total_retirements,
                       last_global_elapsed_ms=elapsed, result=status)

    def accept_second_job(self, *, verified_selected20_v7: str,
                          clock_from_immutable_manifest: GlobalClock,
                          now_unix_ms: int) -> "StageState":
        need(self.job == 1 and self.selected_round == split_at(self.seed)
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
