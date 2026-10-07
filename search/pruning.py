"""Bounded growth windows and category-local pruning decisions."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .fitness import Fitness
from .outer_search import (
    legacy_objective_profile,
    objective_absolute_failure_reason,
    objective_growth_flags,
    objective_short_health_flags,
)

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
    """Compatibility adapter for the canonical legacy ObjectiveProfile."""
    return objective_short_health_flags(
        legacy_objective_profile(),
        active_cells=active_cells,
        activity_cost=activity_cost,
    )


def absolute_failure_reason(
    history: tuple[int, ...],
    *,
    response_history: tuple[int, ...] = (),
) -> str | None:
    """Compatibility adapter for the canonical legacy ObjectiveProfile."""
    return objective_absolute_failure_reason(
        legacy_objective_profile(),
        history,
        response_history=response_history,
    )

def growth_flags(previous: Fitness, current: Fitness) -> int:
    """Compatibility adapter for the canonical legacy ObjectiveProfile."""
    return objective_growth_flags(
        legacy_objective_profile(),
        previous.to_dict(),
        current.to_dict(),
    )


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
