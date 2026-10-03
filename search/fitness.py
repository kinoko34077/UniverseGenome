"""Phase 5 lexicographic absolute-fitness comparison."""

from __future__ import annotations

from dataclasses import dataclass

FITNESS_ORDER = (
    "success",
    "wrong_outputs",
    "timeouts",
    "response_latency",
    "activity_cost",
)


@dataclass(frozen=True)
class Fitness:
    success: int = 0
    wrong_outputs: int = 0
    timeouts: int = 0
    response_latency: int = 0
    activity_cost: int = 0

    def __post_init__(self) -> None:
        if any(value < 0 for value in (self.success, self.wrong_outputs, self.timeouts, self.response_latency, self.activity_cost)):
            raise ValueError("fitness values must be non-negative")

    def sort_key(self) -> tuple[int, int, int, int, int]:
        return (-self.success, self.wrong_outputs, self.timeouts, self.response_latency, self.activity_cost)


def compare_fitness(first: Fitness, second: Fitness) -> int:
    if first.sort_key() < second.sort_key():
        return 1
    if first.sort_key() > second.sort_key():
        return -1
    return 0
