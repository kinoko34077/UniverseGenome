"""Bounded growth windows and category-local pruning decisions."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .fitness import Fitness

SHORT_WINDOW = 16
GROWTH_WINDOW = 128
STAGNATION_HORIZON = 512
SHORT_HEALTH_HISTORY_LIMIT = 4
RESPONSE_HISTORY_LIMIT = STAGNATION_HORIZON // GROWTH_WINDOW
GROWTH_BIT_RETENTION = 5
GROWTH_BIT_NOISE_ROBUSTNESS = 6
# Compatibility aliases for pre-remediation callers. These names must not be
# interpreted as equivalence with Phase 4 counterfactual-clean observables.
GROWTH_BIT_NO_INPUT_CLEAN = GROWTH_BIT_RETENTION
GROWTH_BIT_ALTERNATE_INPUT_CLEAN = GROWTH_BIT_NOISE_ROBUSTNESS
SHORT_HEALTH_ACTIVE_CELLS = 1 << 0
SHORT_HEALTH_MEANINGFUL_ACTIVITY = 1 << 1


def short_health_flags(*, active_cells: int, activity_cost: int) -> int:
    """Encode measurable health at one authoritative short-window boundary."""
    if active_cells < 0 or activity_cost < 0:
        raise ValueError("short-health metrics must be non-negative")
    flags = 0
    if active_cells > 0:
        flags |= SHORT_HEALTH_ACTIVE_CELLS
    if activity_cost > 0:
        flags |= SHORT_HEALTH_MEANINGFUL_ACTIVITY
    return flags


def absolute_failure_reason(
    history: tuple[int, ...],
    *,
    response_history: tuple[int, ...] = (),
) -> str | None:
    """Return an accepted measurable absolute-failure reason.

    Short health owns immediate all-active-cell loss. Persistent non-response
    is task-level: four consecutive 128-generation boundary observations with
    no autonomous output event, while active cells still remain.
    """
    windows = tuple(int(value) for value in history)
    responses = tuple(int(value) for value in response_history)
    if any(not 0 <= value <= 0b11 for value in windows):
        raise ValueError("short-health flags must fit two bits")
    if any(value not in (0, 1) for value in responses):
        raise ValueError("response-history flags must be binary")
    if len(responses) > RESPONSE_HISTORY_LIMIT:
        raise ValueError("response history exceeds the 512-generation horizon")
    if windows and not (windows[-1] & SHORT_HEALTH_ACTIVE_CELLS):
        return "all_active_cells_gone"
    if (
        windows
        and (windows[-1] & SHORT_HEALTH_ACTIVE_CELLS)
        and len(responses) == RESPONSE_HISTORY_LIMIT
        and not any(responses)
    ):
        return "persistent_non_response"
    return None


def growth_flags(previous: Fitness, current: Fitness) -> int:
    flags = 0
    if current.success > previous.success:
        flags |= 1 << 0
    if current.wrong_outputs < previous.wrong_outputs:
        flags |= 1 << 1
    if current.timeouts < previous.timeouts:
        flags |= 1 << 2
    if current.response_latency < previous.response_latency:
        flags |= 1 << 3
    if current.activity_cost < previous.activity_cost:
        flags |= 1 << 4
    if (
        previous.retention_evidence_count > 0
        and current.retention_evidence_count > 0
        and current.retention > previous.retention
    ):
        flags |= 1 << GROWTH_BIT_RETENTION
    if current.noise_robustness > previous.noise_robustness:
        flags |= 1 << GROWTH_BIT_NOISE_ROBUSTNESS
    return flags


@dataclass
class GrowthHistory:
    value: int = 0
    window_count: int = 0

    def push(self, flags: int) -> None:
        if not 0 <= flags <= 0xFF:
            raise ValueError("growth flags must fit uint8")
        self.value = ((self.value << 8) | flags) & 0xFFFFFFFF
        self.window_count = min(4, self.window_count + 1)

    @property
    def score(self) -> int:
        return self.value.bit_count()


def protected_indices(records: list[object]) -> set[int]:
    if not records:
        return set()
    by_category: dict[str, list[object]] = {}
    for record in records:
        by_category.setdefault(record.category, []).append(record)
    protected: set[int] = set()
    for category_records in by_category.values():
        count = max(1, len(category_records) // 8)
        ordered = sorted(category_records, key=lambda record: record.fitness.sort_key())
        protected.update(record.index for record in ordered[:count])
    return protected


def prune_candidates(
    records: list[object],
    *,
    protected: set[int] | None = None,
) -> set[int]:
    result: set[int] = {
        record.index
        for record in records
        if bool(getattr(record, "absolute_failure", False))
    }
    by_category: dict[str, list[object]] = {}
    for record in records:
        by_category.setdefault(record.category, []).append(record)
    for category_records in by_category.values():
        live_records = [
            record
            for record in category_records
            if not bool(getattr(record, "absolute_failure", False))
        ]
        if not live_records:
            continue
        category_protected = (
            protected & {record.index for record in live_records}
            if protected is not None
            else protected_indices(live_records)
        )
        recent_by_record = {
            record.index: tuple(int(window).bit_count() for window in record.growth_windows[-4:])
            for record in live_records
        }
        complete_records = [record for record in live_records if len(recent_by_record[record.index]) == 4]
        if not complete_records:
            continue
        medians = tuple(
            median(recent_by_record[record.index][offset] for record in complete_records)
            for offset in range(4)
        )
        # Keep a zero-median category able to discard candidates with no
        # observed growth while retaining the per-window scale.
        thresholds = tuple(int(value) >> 1 for value in medians)
        for record in complete_records:
            recent_windows = recent_by_record[record.index]
            if record.index in category_protected:
                continue
            if all(window < threshold for window, threshold in zip(recent_windows, thresholds)):
                result.add(record.index)
    return result
