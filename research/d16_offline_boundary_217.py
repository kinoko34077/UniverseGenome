"""D16 #217 OFFLINE syntactic/structural ledger guard; never runs original seed.

Every SHA field must be populated by independently verified D15 evidence.
A well-formed hash is NOT a cryptographic attestation of a claimed result.
A future study runner must authenticate byte content before calling this API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import re

_SHA = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{40}")


class EvidenceError(ValueError):
    """An offline row violates the prospectively frozen research envelope."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


@dataclass(frozen=True)
class Protocol:
    source: str
    initial_selected_sha: str
    experiment_sha: str
    physics_sha: str
    category_names: tuple[str, ...]
    seed: int = 16384
    min_rounds: int = 37
    max_rounds: int = 40
    max_jobs: int = 2
    rounds_per_job: int = 20
    preferred_seconds: int = 1200
    cap_seconds: int = 1800
    max_rss_bytes: int = 1536 * 1024 * 1024
    max_journal_bytes: int = 128 * 1024 * 1024
    max_retained_bytes: int = 512 * 1024 * 1024

    def __post_init__(self) -> None:
        _require(bool(_COMMIT.fullmatch(self.source)), "exact source commit required")
        for v in (self.initial_selected_sha, self.experiment_sha, self.physics_sha):
            _require(bool(_SHA.fullmatch(v)), "full digest required")
        _require(self.seed == 16384 and self.min_rounds == 37
                 and self.max_rounds == 40 and self.max_jobs == 2
                 and self.rounds_per_job == 20
                 and self.preferred_seconds == 1200 and self.cap_seconds == 1800,
                 "frozen D16 scientific protocol changed")
        _require(len(self.category_names) == 4 and len(set(self.category_names)) == 4,
                 "four original native categories required")


@dataclass(frozen=True)
class Patch:
    first: int
    after: int
    sha256: str


@dataclass(frozen=True)
class Round:
    number: int
    job: int
    source: str
    seed: int
    experiment_sha: str
    physics_sha: str
    predecessor_sha: str
    evaluated_preselect_sha: str
    observer_preselect_sha: str
    selected_sha: str
    evaluated_worlds: int
    selection_count: int
    categories: Mapping[str, int]
    patches: tuple[Patch, ...]
    journal_bytes: int
    retained_bytes: int
    peak_sampled_rss_bytes: int
    global_seconds: float
    local_seconds: float
    prunable_count: int
    replacement_count: int
    completed_growth_nonfailed: int
    absolute_failure_count: int


def validate(protocol: Protocol, rows: tuple[Round, ...]) -> None:
    """Read-only fail-closed structural check, not provenance authentication."""
    _require(len(rows) <= protocol.max_rounds, "study exceeded declared horizon")
    previous = None
    job_counts: dict[int, int] = {}
    for row in rows:
        expected_round = 1 if previous is None else previous.number + 1
        expected_predecessor = (protocol.initial_selected_sha if previous is None
                                else previous.selected_sha)
        _require(type(row.number) is int and row.number == expected_round,
                 "selected rounds not consecutive")
        _require(type(row.job) is int and 1 <= row.job <= protocol.max_jobs,
                 "invalid job")
        # Prospective immutable 2-job partition avoids post-outcome scheduler edits:
        # job1 selected rounds 1..20, job2 rounds 21..40.
        _require(row.job == (1 if row.number <= 20 else 2),
                 "frozen 20+20 two-job partition drift")
        _require(row.job == (1 if previous is None else row.job)
                 and (previous is None or row.job in
                      (previous.job, previous.job + 1)), "job order discontinuity")
        job_counts[row.job] = job_counts.get(row.job, 0) + 1
        _require(job_counts[row.job] <= protocol.rounds_per_job,
                 "job did more than 20 rounds")
        _require(row.source == protocol.source and row.seed == protocol.seed,
                 "source or scientific seed drift")
        _require(row.experiment_sha == protocol.experiment_sha
                 and row.physics_sha == protocol.physics_sha, "config drift")
        _require(row.predecessor_sha == expected_predecessor,
                 "full selected-state handoff mismatch")
        for sha in (row.predecessor_sha, row.evaluated_preselect_sha,
                    row.observer_preselect_sha, row.selected_sha):
            _require(isinstance(sha, str) and bool(_SHA.fullmatch(sha)),
                     "malformed evidence digest")
        _require(row.observer_preselect_sha == row.evaluated_preselect_sha,
                 "read-only observer provenance mismatch")
        _require(row.evaluated_worlds == 128 and row.selection_count == 1,
                 "original full128 native selection required")
        _require(dict(row.categories) == {cat: 32 for cat in protocol.category_names},
                 "native category counts drift")
        _require(1 <= len(row.patches) <= 128, "no complete D15 journal")
        # Adaptive D15 batches can be <16 due to elapsed-time commits.
        covered = 0
        for patch in row.patches:
            _require(patch.first == covered and type(patch.after) is int
                     and 0 < patch.after - patch.first <= 16,
                     "journal not disjoint, contiguous and capped")
            _require(isinstance(patch.sha256, str)
                     and bool(_SHA.fullmatch(patch.sha256)), "unhashed patch")
            covered = patch.after
        _require(covered == 128, "journal does not cover 128 worlds")
        _require(0 < row.journal_bytes <= protocol.max_journal_bytes
                 and 0 <= row.retained_bytes <= protocol.max_retained_bytes
                 and 0 <= row.peak_sampled_rss_bytes <= protocol.max_rss_bytes,
                 "disk/RSS envelope exceeded")
        _require(0 <= row.global_seconds <= protocol.cap_seconds
                 and 0 <= row.local_seconds <= 18 * 60,
                 "wall envelope exceeded")
        if previous is not None:
            _require(row.global_seconds >= previous.global_seconds, "global clock regressed")
            if row.job == previous.job:
                _require(row.local_seconds >= previous.local_seconds,
                         "same-job clock regressed")
        _require(0 <= row.replacement_count <= 4
                 and row.replacement_count <= row.prunable_count <= 128,
                 "native finalizer/prune cardinality inconsistent")
        _require(0 <= row.completed_growth_nonfailed <= 128
                 and 0 <= row.absolute_failure_count <= 128,
                 "invalid native maturity/failure evidence")
        _require(row.number >= 37 or row.completed_growth_nonfailed == 0,
                 "all four growth windows falsely reported before physical round37")
        previous = row


def classify(protocol: Protocol, rows: tuple[Round, ...],
             *, budget_bound: bool = False) -> dict[str, object]:
    """Report native co-observation only; never infer learning or causation."""
    validate(protocol, rows)
    mature_replace = any(
        x.completed_growth_nonfailed > 0 and x.replacement_count > 0 for x in rows
    )
    total = len(rows)
    elapsed = rows[-1].global_seconds if rows else 0
    if budget_bound:
        outcome = "BUDGET_BOUND_INCOMPLETE"
    elif total < protocol.min_rounds:
        outcome = "IN_PROGRESS"
    elif mature_replace:
        outcome = "GROWTH_AND_REPLACEMENT_COOBSERVED_NO_CAUSAL_CLAIM"
    elif total >= protocol.max_rounds:
        outcome = "NOT_OBSERVED_WITHIN_FROZEN_HORIZON"
    else:
        outcome = "IN_PROGRESS"
    return {
        "outcome": outcome,
        "rounds": total,
        "global_seconds": elapsed,
        # Throughput and terminal research status are distinct: 37 completed
        # rounds alone do NOT mean the frozen study has reached an endpoint.
        "completed_37_rounds_by_1200": (
            total >= protocol.min_rounds
            and elapsed <= protocol.preferred_seconds and not budget_bound
        ),
        "target_1200_met": (
            outcome in (
                "GROWTH_AND_REPLACEMENT_COOBSERVED_NO_CAUSAL_CLAIM",
                "NOT_OBSERVED_WITHIN_FROZEN_HORIZON",
            ) and elapsed <= protocol.preferred_seconds and not budget_bound
        ),
        "replacements": sum(x.replacement_count for x in rows),
        "learning_claim": False,
        "provenance_authenticated": False,
    }
