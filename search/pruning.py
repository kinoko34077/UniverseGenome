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
    count = max(1, len(records) // 8)
    ordered = sorted(records, key=lambda record: record.fitness.sort_key())
    return {record.index for record in ordered[:count]}


def prune_candidates(records: list[object]) -> set[int]:
    protected = protected_indices(records)
    result: set[int] = set()
    by_category: dict[str, list[object]] = {}
    for record in records:
        by_category.setdefault(record.category, []).append(record)
    for category_records in by_category.values():
        if not category_records:
            continue
        scores = [sum(category_record.growth_windows) for category_record in category_records]
        threshold = int(median(scores)) >> 1
        for record, score in zip(category_records, scores):
            if record.index in protected:
                continue
            if len(record.growth_windows) >= 4 and score < threshold:
                result.add(record.index)
    return result
