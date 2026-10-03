"""Bounded growth windows and category-local pruning decisions."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .fitness import Fitness

SHORT_WINDOW = 16
GROWTH_WINDOW = 128
STAGNATION_HORIZON = 512


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
    if current.retention > previous.retention:
        flags |= 1 << 5
    if current.noise_robustness > previous.noise_robustness:
        flags |= 1 << 6
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


def prune_candidates(records: list[object]) -> set[int]:
    result: set[int] = set()
    by_category: dict[str, list[object]] = {}
    for record in records:
        by_category.setdefault(record.category, []).append(record)
    for category_records in by_category.values():
        if not category_records:
            continue
        protected = protected_indices(category_records)
        recent_by_record = {
            record.index: tuple(int(window).bit_count() for window in record.growth_windows[-4:])
            for record in category_records
        }
        complete_records = [record for record in category_records if len(recent_by_record[record.index]) == 4]
        if not complete_records:
            continue
        medians = tuple(
            median(recent_by_record[record.index][offset] for record in complete_records)
            for offset in range(4)
        )
        # Keep a zero-median category able to discard candidates with no
        # observed growth while retaining the per-window scale.
        thresholds = tuple(max(1, int(value) >> 1) for value in medians)
        for record in complete_records:
            recent_windows = recent_by_record[record.index]
            if record.index in protected:
                continue
            if all(window < threshold for window, threshold in zip(recent_windows, thresholds)):
                result.add(record.index)
    return result
