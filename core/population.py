"""Bounded deterministic Phase 3 population and observation runtime."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time
from typing import Any, Iterable

from .physics import PhysicsConfig, create_universe, step
from .state import Lifecycle, UniverseState


CATEGORY_OPERATORS = ("masked_copy", "masked_xor", "rotate_copy", "masked_and")
HISTORY_LENGTHS = (128, 256, 512)
HISTORY_MEMORY_BUDGET_BYTES = 256 * 1024 * 1024
GENOME_COUNT = 8
SEEDS_PER_GENOME = 4
SLOTS_PER_CATEGORY = GENOME_COUNT * SEEDS_PER_GENOME
POPULATION_SIZE = len(CATEGORY_OPERATORS) * SLOTS_PER_CATEGORY

DEFAULT_GENOME_OVERRIDES: tuple[tuple[tuple[str, Any], ...], ...] = (
    (("hp_decay", 0),),
    (("hp_decay", 1),),
    (("bond_gain", 2),),
    (("bond_gain", 8),),
    (("bond_decay", 1),),
    (("bond_decay", 2),),
    (("fragmentation_rate", 0),),
    (("fragmentation_rate", 1),),
)


@dataclass(frozen=True)
class ParameterGenome:
    """A small immutable universe-parameter record; seed is intentionally absent."""

    genome_id: int
    overrides: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "genome_id": self.genome_id,
            "overrides": {key: value for key, value in self.overrides},
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ParameterGenome":
        overrides = payload.get("overrides", {})
        if not isinstance(overrides, dict):
            raise ValueError("genome overrides must be an object")
        return cls(
            genome_id=int(payload["genome_id"]),
            overrides=tuple(sorted(overrides.items())),
        )

    def physics_config(self, base: PhysicsConfig, operator: str) -> PhysicsConfig:
        values = base.to_dict()
        values.update(dict(self.overrides))
        values["latent_operator"] = operator
        return PhysicsConfig(**values)


@dataclass
class PopulationSlot:
    index: int
    category: str
    genome: ParameterGenome
    seed: int
    state: UniverseState

    @property
    def genome_id(self) -> int:
        return self.genome.genome_id


@dataclass
class ObservationClone:
    """An isolated state copy for inspection; it is not an authoritative slot."""

    index: int
    category: str
    genome: ParameterGenome
    seed: int
    state: UniverseState

    @property
    def genome_id(self) -> int:
        return self.genome.genome_id


def default_genomes() -> tuple[ParameterGenome, ...]:
    return tuple(
        ParameterGenome(genome_id=index, overrides=overrides)
        for index, overrides in enumerate(DEFAULT_GENOME_OVERRIDES)
    )


def _compact_state(state: UniverseState) -> dict[str, Any]:
    fields = [
        "lifecycle", "x", "y", "structure", "latent", "hp", "bond_strength",
        "direction", "speed_code", "age", "black_hole_timer",
    ]
    active = []
    for index, lifecycle in enumerate(state.lifecycle):
        if lifecycle == Lifecycle.FREE:
            continue
        active.append([index, *[getattr(state, field)[index] for field in fields]])
    config = state.config.to_dict() if state.config is not None else None
    return {
        "seed": int(state.seed),
        "max_cells": int(state.max_cells),
        "generation": int(state.generation),
        "config": config,
        "fields": fields,
        "active": active,
    }


def _restore_compact(record: dict[str, Any]) -> UniverseState:
    raw_config = record.get("config")
    config = PhysicsConfig.from_mapping(raw_config) if isinstance(raw_config, dict) else PhysicsConfig()
    state = UniverseState(
        seed=int(record["seed"]),
        max_cells=int(record["max_cells"]),
        generation=int(record["generation"]),
        config=config,
    )
    expected = (
        "lifecycle", "x", "y", "structure", "latent", "hp", "bond_strength",
        "direction", "speed_code", "age", "black_hole_timer",
    )
    if tuple(record.get("fields", ())) != expected:
        raise ValueError("population checkpoint fields do not match Phase 3 state")
    for values in record.get("active", []):
        if not isinstance(values, list) or len(values) != len(expected) + 1:
            raise ValueError("population checkpoint cell record is invalid")
        index = int(values[0])
        if not 0 <= index < state.max_cells:
            raise ValueError("population checkpoint cell index is invalid")
        for field, value in zip(expected, values[1:]):
            getattr(state, field)[index] = int(value)
    return state


def _encode_history(record: dict[str, Any]) -> str:
    """Store one population checkpoint as compact deterministic JSON text."""
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode_history(record: str | dict[str, Any]) -> dict[str, Any]:
    """Decode compact history while accepting pre-remediation dict records."""
    if isinstance(record, dict):
        return record
    if not isinstance(record, str):
        raise ValueError("population history record must be compact JSON text")
    try:
        decoded = json.loads(record)
    except json.JSONDecodeError as exc:
        raise ValueError("population history record is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError("population history record must decode to an object")
    return decoded


class Population:
    """Four isolated categories with matched genome/seed pairs and bounded history."""

    def __init__(self, slots: Iterable[PopulationSlot], *, history_length: int = 128) -> None:
        if history_length not in HISTORY_LENGTHS:
            raise ValueError(f"history_length must be one of {HISTORY_LENGTHS}")
        self.slots = list(slots)
        if len(self.slots) != POPULATION_SIZE:
            raise ValueError(f"population must contain exactly {POPULATION_SIZE} slots")
        if sorted(slot.index for slot in self.slots) != list(range(POPULATION_SIZE)):
            raise ValueError("population slot indices must be a complete 0..127 range")
        if {slot.category for slot in self.slots} != set(CATEGORY_OPERATORS):
            raise ValueError("population categories do not match Phase 3")
        if any(sum(slot.category == category for slot in self.slots) != SLOTS_PER_CATEGORY for category in CATEGORY_OPERATORS):
            raise ValueError("each Phase 3 category must contain exactly 32 slots")
        expected_pairs = [
            (slot.genome_id, slot.seed)
            for slot in self.slots
            if slot.category == CATEGORY_OPERATORS[0]
        ]
        for category in CATEGORY_OPERATORS[1:]:
            pairs = [
                (slot.genome_id, slot.seed)
                for slot in self.slots
                if slot.category == category
            ]
            if pairs != expected_pairs:
                raise ValueError("Phase 3 categories must align genome/seed pairs")
        self.history_length = history_length
        self._history: deque[str] = deque(maxlen=history_length + 1)
        self._record_history()

    @classmethod
    def from_defaults(
        cls,
        *,
        base_seed: int = 0,
        config: PhysicsConfig | None = None,
        history_length: int = 128,
    ) -> "Population":
        base = config or PhysicsConfig()
        genomes = default_genomes()
        slots: list[PopulationSlot] = []
        index = 0
        for category in CATEGORY_OPERATORS:
            for genome in genomes:
                for seed_offset in range(SEEDS_PER_GENOME):
                    seed = int(base_seed) + (genome.genome_id * SEEDS_PER_GENOME) + seed_offset
                    slot_config = genome.physics_config(base, category)
                    slots.append(
                        PopulationSlot(
                            index=index,
                            category=category,
                            genome=genome,
                            seed=seed,
                            state=create_universe(seed=seed, config=slot_config),
                        )
                    )
                    index += 1
        return cls(slots, history_length=history_length)

    @property
    def generation(self) -> int:
        generations = {slot.state.generation for slot in self.slots}
        if len(generations) != 1:
            raise RuntimeError("population slots are not generation-aligned")
        return generations.pop()

    @property
    def history_size(self) -> int:
        return len(self._history)

    @property
    def history_memory_bytes(self) -> int:
        """Return a reproducible estimate of retained compact history memory."""
        return sys.getsizeof(self._history) + sum(sys.getsizeof(record) for record in self._history)

    def _record_history(self) -> None:
        self._history.append(_encode_history({
            "generation": self.generation,
            "states": [_compact_state(slot.state) for slot in self.slots],
        }))

    def step(self) -> list[Any]:
        metrics = [step(slot.state) for slot in self.slots]
        self._record_history()
        return metrics

    def run(self, generations: int) -> None:
        if generations < 0:
            raise ValueError("generations must be non-negative")
        for _ in range(generations):
            self.step()

    def rewind(self, generations: int) -> None:
        if generations < 0:
            raise ValueError("generations must be non-negative")
        target = self.generation - int(generations)
        checkpoint = next(
            (item for item in reversed(self._history) if _decode_history(item)["generation"] == target),
            None,
        )
        if checkpoint is None:
            raise ValueError("requested rewind exceeds bounded history")
        decoded_checkpoint = _decode_history(checkpoint)
        for slot, record in zip(self.slots, decoded_checkpoint["states"]):
            slot.state = _restore_compact(record)
        self._history = deque(
            (item for item in self._history if _decode_history(item)["generation"] <= target),
            maxlen=self.history_length + 1,
        )

    def clone_for_observation(self, index: int) -> ObservationClone:
        slot = self._slot(index)
        return ObservationClone(
            index=slot.index,
            category=slot.category,
            genome=slot.genome,
            seed=slot.seed,
            state=_restore_compact(_compact_state(slot.state)),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "slot_count": len(self.slots),
            "category_counts": dict(Counter(slot.category for slot in self.slots)),
            "active_cells": sum(len(slot.state.active_slots()) for slot in self.slots),
            "history_size": self.history_size,
            "history_length": self.history_length,
            "history_entry_count": self.history_size,
            "history_memory_bytes": self.history_memory_bytes,
            "history_memory_budget_bytes": HISTORY_MEMORY_BUDGET_BYTES,
            "history_memory_within_budget": self.history_memory_bytes <= HISTORY_MEMORY_BUDGET_BYTES,
        }

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "format_version": 1,
            "kind": "UniverseGenomePhase3Population",
            "history_length": self.history_length,
            "slots": [
                {
                    "index": slot.index,
                    "category": slot.category,
                    "genome": slot.genome.to_dict(),
                    "seed": slot.seed,
                }
                for slot in self.slots
            ],
            "history": list(self._history),
        }

    @classmethod
    def from_snapshot(cls, payload: dict[str, Any]) -> "Population":
        if payload.get("format_version") != 1 or payload.get("kind") != "UniverseGenomePhase3Population":
            raise ValueError("unsupported Phase 3 population snapshot")
        raw_history = payload.get("history")
        raw_slots = payload.get("slots")
        if not isinstance(raw_history, list) or not isinstance(raw_slots, list):
            raise ValueError("population snapshot requires slots and history")
        if len(raw_slots) != POPULATION_SIZE or not raw_history:
            raise ValueError("population snapshot has invalid dimensions")
        latest = _decode_history(raw_history[-1])
        states = latest.get("states")
        if not isinstance(states, list) or len(states) != POPULATION_SIZE:
            raise ValueError("population snapshot has invalid state records")
        slots = []
        for metadata, record in zip(raw_slots, states):
            if not isinstance(metadata, dict):
                raise ValueError("population slot metadata is invalid")
            genome = ParameterGenome.from_dict(metadata["genome"])
            slots.append(
                PopulationSlot(
                    index=int(metadata["index"]),
                    category=str(metadata["category"]),
                    genome=genome,
                    seed=int(metadata["seed"]),
                    state=_restore_compact(record),
                )
            )
        population = cls(slots, history_length=int(payload["history_length"]))
        population._history = deque(
            (_encode_history(_decode_history(record)) for record in raw_history),
            maxlen=population.history_length + 1,
        )
        return population

    def _slot(self, index: int) -> PopulationSlot:
        if not isinstance(index, int) or not 0 <= index < len(self.slots):
            raise IndexError("population slot index out of range")
        return self.slots[index]


def save_population(path: str | Path, population: Population) -> None:
    Path(path).write_text(
        json.dumps(population.to_snapshot(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_population(path: str | Path) -> Population:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("unable to read Phase 3 population snapshot") from exc
    if not isinstance(payload, dict):
        raise ValueError("population snapshot must be an object")
    return Population.from_snapshot(payload)


def run_population_headless(
    *,
    seed: int = 0,
    generations: int = 0,
    config: PhysicsConfig | None = None,
    history_length: int = 128,
) -> dict[str, Any]:
    population = Population.from_defaults(
        base_seed=seed,
        config=config,
        history_length=history_length,
    )
    started = time.perf_counter()
    population.run(generations)
    elapsed = max(time.perf_counter() - started, 1e-12)
    summary = population.summary()
    summary["generations"] = generations
    summary["generation_count"] = generations
    summary["slot_steps"] = generations * len(population.slots)
    summary["generations_per_second"] = generations / elapsed if generations else 0.0
    return summary
