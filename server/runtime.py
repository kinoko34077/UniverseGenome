"""Authoritative Phase 5 optimizer runtime exposed to the browser observer."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
from threading import Event, RLock, Thread
from typing import Any, Mapping

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig, step
from core.state import UniverseState, structure_level
from search.evolution import SteadyStateOptimizer, UniverseSlot
from search.fitness import Fitness
from search.genome import UniverseGenome


HISTORY_LENGTHS = (128, 256, 512)
RESET_PARAMETER_FIELDS = (
    "noise_attempts",
    "collision_damage",
    "structure_damage_threshold",
    "bond_velocity_threshold",
    "fusion_enabled",
    "fragmentation_enabled",
    "aging_enabled",
)


@dataclass
class OptimizerObservationClone:
    """Isolated selected-slot clone plus immutable source metadata."""

    index: int
    category: str
    genome: UniverseGenome
    seed: int
    state: UniverseState
    fitness: Fitness
    growth_windows: tuple[int, ...]
    evidence_group_size: int
    evidence_mature: bool
    parent_index: int | None
    last_mutation_field: str | None
    allocation_reason: str
    absolute_failure: bool
    absolute_failure_reason: str | None


class PopulationRuntime:
    """Own the single authoritative Phase 5 optimizer and observer controls.

    The historical class name is retained for API/import compatibility. It no
    longer owns a parallel core.population.Population.
    """

    MAX_CONTROL_GENERATIONS = 512
    MAX_SEARCH_ITERATIONS = 16
    DEFAULT_HISTORY_LENGTH = 512

    def __init__(
        self,
        *,
        base_seed: int = 0,
        history_length: int = DEFAULT_HISTORY_LENGTH,
        config: PhysicsConfig | None = None,
        experiment: ExperimentConfig | None = None,
    ) -> None:
        if int(history_length) not in HISTORY_LENGTHS:
            raise ValueError(f"history_length must be one of {HISTORY_LENGTHS}")
        self.base_seed = int(base_seed)
        self.history_length = int(history_length)
        self.config = config or PhysicsConfig()
        self.experiment = experiment or ExperimentConfig()
        self.optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=self.base_seed,
            base_config=self.config,
            experiment=self.experiment,
        )
        self.selected_index = 0
        self.observation_clone: OptimizerObservationClone | None = None
        self._clone_history: deque[dict[str, Any]] = deque(
            maxlen=self.history_length + 1
        )
        self.pending_reset_parameters: dict[str, Any] = {}
        self.last_search: dict[str, Any] = self._empty_search_summary()
        self.last_error: str | None = None
        self.running = False
        self._lock = RLock()
        self._stop = Event()
        self._thread: Thread | None = None

    @staticmethod
    def _cell_payload(state: UniverseState) -> list[dict[str, int]]:
        return [
            {
                "slot": slot,
                "x": (state.x[slot] // 8) % 32,
                "y": (state.y[slot] // 8) % 32,
                "structure": state.structure[slot],
                "hierarchy": structure_level(state.structure[slot]),
                "latent": state.latent[slot],
                "hp": state.hp[slot],
                "bond": state.bond_strength[slot],
                "activity": min(
                    255,
                    state.bond_strength[slot]
                    + state.latent[slot].bit_count() * 16,
                ),
                "age": state.age[slot],
            }
            for slot in state.active_slots()
        ]

    @classmethod
    def _overview_payload(cls, state: UniverseState) -> list[dict[str, int]]:
        """Project a 32x32 state into the accepted 8x8 spatial overview."""
        overview = [
            {"activity": 0, "hierarchy": 0, "occupied": 0}
            for _ in range(64)
        ]
        for cell in cls._cell_payload(state):
            bucket_x = min(7, cell["x"] // 4)
            bucket_y = min(7, cell["y"] // 4)
            bucket = bucket_y * 8 + bucket_x
            overview[bucket]["activity"] = max(
                overview[bucket]["activity"], cell["activity"]
            )
            overview[bucket]["hierarchy"] = max(
                overview[bucket]["hierarchy"], cell["hierarchy"]
            )
            overview[bucket]["occupied"] += 1
        return overview

    def _group_counts(self) -> dict[tuple[str, str], int]:
        counts: dict[tuple[str, str], int] = {}
        for slot in self.optimizer.slots:
            counts[slot.evidence_group] = counts.get(slot.evidence_group, 0) + 1
        return counts

    def _last_event_by_index(self) -> dict[int, dict[str, Any]]:
        replacements = self.last_search.get("replacements", ())
        if not isinstance(replacements, list):
            return {}
        return {
            int(item["index"]): dict(item)
            for item in replacements
            if isinstance(item, Mapping) and item.get("index") is not None
        }

    def _slot_metadata(
        self,
        slot: UniverseSlot,
        *,
        group_counts: Mapping[tuple[str, str], int],
        event_by_index: Mapping[int, dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "index": slot.index,
            "category": slot.category,
            "genome": slot.genome.to_dict(),
            "genome_key": slot.genome_key,
            "seed": slot.seed,
            "generation": slot.physical_generations,
            "fitness": slot.fitness.to_dict(),
            "growth_windows": list(slot.growth_windows),
            "evidence_group_size": int(group_counts.get(slot.evidence_group, 0)),
            "evidence_mature": slot.evidence_mature,
            "parent_index": slot.parent_index,
            "last_mutation_field": slot.last_mutation_field,
            "allocation_reason": slot.allocation_reason,
            "absolute_failure": slot.absolute_failure,
            "absolute_failure_reason": slot.absolute_failure_reason,
            "last_event": event_by_index.get(slot.index),
        }

    def _slot_summary(
        self,
        slot: UniverseSlot,
        *,
        group_counts: Mapping[tuple[str, str], int],
        event_by_index: Mapping[int, dict[str, Any]],
    ) -> dict[str, Any]:
        cells = self._cell_payload(slot.state)
        return {
            **self._slot_metadata(
                slot,
                group_counts=group_counts,
                event_by_index=event_by_index,
            ),
            "active_cells": len(cells),
            "overview": self._overview_payload(slot.state),
        }

    def _selected_authoritative_slot(self) -> UniverseSlot:
        return self.optimizer.slots[self.selected_index]

    def _clone_metadata(self, slot: UniverseSlot) -> OptimizerObservationClone:
        counts = self._group_counts()
        clone_state = UniverseState.from_snapshot(
            slot.state.to_snapshot(),
            config=slot.state.config,
        )
        return OptimizerObservationClone(
            index=slot.index,
            category=slot.category,
            genome=slot.genome,
            seed=slot.seed,
            state=clone_state,
            fitness=slot.fitness,
            growth_windows=tuple(slot.growth_windows),
            evidence_group_size=int(counts.get(slot.evidence_group, 0)),
            evidence_mature=slot.evidence_mature,
            parent_index=slot.parent_index,
            last_mutation_field=slot.last_mutation_field,
            allocation_reason=slot.allocation_reason,
            absolute_failure=slot.absolute_failure,
            absolute_failure_reason=slot.absolute_failure_reason,
        )

    def _selected_payload(
        self,
        *,
        group_counts: Mapping[tuple[str, str], int],
        event_by_index: Mapping[int, dict[str, Any]],
    ) -> dict[str, Any]:
        if self.observation_clone is None:
            slot = self._selected_authoritative_slot()
            payload = self._slot_summary(
                slot,
                group_counts=group_counts,
                event_by_index=event_by_index,
            )
            payload["cells"] = self._cell_payload(slot.state)
            return payload

        clone = self.observation_clone
        cells = self._cell_payload(clone.state)
        return {
            "index": clone.index,
            "category": clone.category,
            "genome": clone.genome.to_dict(),
            "genome_key": json.dumps(
                clone.genome.to_dict(),
                sort_keys=True,
                separators=(",", ":"),
            ),
            "seed": clone.seed,
            "generation": int(clone.state.generation),
            "fitness": clone.fitness.to_dict(),
            "growth_windows": list(clone.growth_windows),
            "evidence_group_size": clone.evidence_group_size,
            "evidence_mature": clone.evidence_mature,
            "parent_index": clone.parent_index,
            "last_mutation_field": clone.last_mutation_field,
            "allocation_reason": clone.allocation_reason,
            "absolute_failure": clone.absolute_failure,
            "absolute_failure_reason": clone.absolute_failure_reason,
            "last_event": None,
            "active_cells": len(cells),
            "overview": self._overview_payload(clone.state),
            "cells": cells,
        }

    def _empty_search_summary(self) -> dict[str, Any]:
        categories = (
            "masked_copy",
            "masked_xor",
            "rotate_copy",
            "masked_and",
        )
        return {
            "generation": self.optimizer.generation,
            "evaluated_slots": 0,
            "category_counts": {
                category: sum(
                    slot.category == category for slot in self.optimizer.slots
                )
                for category in categories
            },
            "group_counts": self.optimizer.group_counts(),
            "cross_category_selection": False,
            "replacement_count": 0,
            "pruned_count": 0,
            "replacements": [],
            "generations_per_second": 0.0,
        }

    def state(self) -> dict[str, Any]:
        with self._lock:
            group_counts = self._group_counts()
            events = self._last_event_by_index()
            summaries = [
                self._slot_summary(
                    slot,
                    group_counts=group_counts,
                    event_by_index=events,
                )
                for slot in self.optimizer.slots
            ]
            selected = self._selected_payload(
                group_counts=group_counts,
                event_by_index=events,
            )
            category_counts = self.last_search.get("category_counts")
            if not isinstance(category_counts, dict):
                category_counts = self._empty_search_summary()["category_counts"]
            return {
                "authority": "phase5_optimizer",
                "generation": self.optimizer.generation,
                "optimizer_generation": self.optimizer.generation,
                "slot_count": len(self.optimizer.slots),
                "category_counts": category_counts,
                "group_counts": self.optimizer.group_counts(),
                "scheduler": dict(self.optimizer.scheduler),
                "running": self.running,
                "selected_index": self.selected_index,
                "observation_target": (
                    "clone" if self.observation_clone is not None else "authoritative"
                ),
                "history_length": self.history_length,
                "history_size": len(self._clone_history),
                "pending_reset_parameters": dict(self.pending_reset_parameters),
                "reset_config": self.config.to_dict(),
                "experiment": self.experiment.to_dict(),
                "activity_semantics": (
                    "display-only proxy: min(255, bond_strength + "
                    "16 * popcount(latent)); not optimizer activity_cost"
                ),
                "last_search": dict(self.last_search),
                "last_error": self.last_error,
                "summaries": summaries,
                "selected": selected,
            }

    def _run_loop(self) -> None:
        while not self._stop.wait(0.05):
            with self._lock:
                if not self.running:
                    continue
                try:
                    self.last_search = self.optimizer.step()
                    self.last_error = None
                except Exception as exc:  # pragma: no cover
                    self.last_error = str(exc)
                    self.running = False

    def run(self) -> None:
        with self._lock:
            self.running = True
            if self._thread is None or not self._thread.is_alive():
                self._stop.clear()
                self._thread = Thread(target=self._run_loop, daemon=True)
                self._thread.start()

    def pause(self) -> None:
        with self._lock:
            self.running = False

    @staticmethod
    def _bounded(value: Any, *, default: int, maximum: int, label: str) -> int:
        resolved = int(default if value is None else value)
        if not 0 <= resolved <= maximum:
            raise ValueError(f"{label} exceeds bounded runtime limit")
        return resolved

    def _bounded_generations(self, value: Any) -> int:
        return self._bounded(
            value,
            default=1,
            maximum=self.MAX_CONTROL_GENERATIONS,
            label="control generations",
        )

    def _bounded_iterations(self, value: Any) -> int:
        return self._bounded(
            value,
            default=1,
            maximum=self.MAX_SEARCH_ITERATIONS,
            label="search iterations",
        )

    def _record_clone_history(self) -> None:
        if self.observation_clone is not None:
            self._clone_history.append(self.observation_clone.state.to_snapshot())

    def _set_history_length(self, value: Any) -> None:
        history_length = int(value)
        if history_length not in HISTORY_LENGTHS:
            raise ValueError(f"history_length must be one of {HISTORY_LENGTHS}")
        existing = list(self._clone_history)[-(history_length + 1) :]
        self.history_length = history_length
        self._clone_history = deque(existing, maxlen=history_length + 1)

    def _rewind_clone(self, generations: int) -> None:
        if self.observation_clone is None:
            raise ValueError("observation rewind requires an isolated clone")
        target = int(self.observation_clone.state.generation) - generations
        record = next(
            (
                item
                for item in reversed(self._clone_history)
                if int(item.get("generation", -1)) == target
            ),
            None,
        )
        if record is None:
            raise ValueError("requested rewind exceeds observation clone history")
        config = self.observation_clone.state.config
        self.observation_clone.state = UniverseState.from_snapshot(
            record,
            config=config,
        )
        retained = [
            item
            for item in self._clone_history
            if int(item.get("generation", -1)) <= target
        ]
        self._clone_history = deque(
            retained[-(self.history_length + 1) :],
            maxlen=self.history_length + 1,
        )

    def _stage_parameters(self, raw: Any) -> None:
        if not isinstance(raw, Mapping):
            raise ValueError("parameters must be an object")
        unknown = set(raw) - set(RESET_PARAMETER_FIELDS)
        if unknown:
            raise ValueError(f"unsupported reset parameters: {sorted(unknown)}")

        staged = dict(self.pending_reset_parameters)
        bool_fields = {"fusion_enabled", "fragmentation_enabled", "aging_enabled"}
        for key, value in raw.items():
            if key in bool_fields:
                if not isinstance(value, bool):
                    raise ValueError(f"{key} must be boolean")
                staged[key] = value
            else:
                if isinstance(value, bool):
                    raise ValueError(f"{key} must be an integer")
                staged[key] = int(value)

        candidate = self.config.to_dict()
        candidate.update(staged)
        PhysicsConfig(**candidate)
        self.pending_reset_parameters = staged

    def _apply_pending_reset_config(self) -> None:
        if not self.pending_reset_parameters:
            return
        values = self.config.to_dict()
        values.update(self.pending_reset_parameters)
        self.config = PhysicsConfig(**values)
        self.pending_reset_parameters = {}

    def control(self, action: str, **payload: Any) -> dict[str, Any]:
        with self._lock:
            if action == "run":
                self.run()
            elif action == "pause":
                self.pause()
            elif action == "search_step":
                self.running = False
                iterations = self._bounded_iterations(payload.get("iterations", 1))
                self.last_search = self.optimizer.run(iterations=iterations)
                self.last_error = None
            elif action == "step":
                if self.observation_clone is None:
                    raise ValueError(
                        "physical step requires Clone for Observation; "
                        "authoritative search slots are not manually stepped"
                    )
                for _ in range(
                    self._bounded_generations(payload.get("generations", 1))
                ):
                    step(self.observation_clone.state)
                    self._record_clone_history()
            elif action == "reset":
                self.running = False
                self._apply_pending_reset_config()
                self.optimizer = SteadyStateOptimizer.from_defaults(
                    base_seed=self.base_seed,
                    base_config=self.config,
                    experiment=self.experiment,
                )
                self.selected_index = 0
                self.observation_clone = None
                self._clone_history.clear()
                self.last_search = self._empty_search_summary()
                self.last_error = None
            elif action == "select":
                index = int(payload["index"])
                if not 0 <= index < len(self.optimizer.slots):
                    raise IndexError("selected universe index out of range")
                self.selected_index = index
                self.observation_clone = None
                self._clone_history.clear()
            elif action == "clone":
                self.observation_clone = self._clone_metadata(
                    self._selected_authoritative_slot()
                )
                self._clone_history = deque(maxlen=self.history_length + 1)
                self._record_clone_history()
            elif action == "rewind":
                self._rewind_clone(
                    self._bounded_generations(payload.get("generations", 1))
                )
            elif action == "set_history_length":
                self._set_history_length(payload.get("history_length"))
            elif action == "set_parameters":
                self._stage_parameters(payload.get("parameters"))
            elif action == "load":
                self.running = False
                raw_snapshot = payload.get("snapshot")
                if not isinstance(raw_snapshot, Mapping):
                    raise ValueError("optimizer snapshot must be an object")
                self.optimizer = SteadyStateOptimizer.from_snapshot(raw_snapshot)
                self.config = self.optimizer.base_config
                self.experiment = self.optimizer.experiment
                self.selected_index = min(
                    self.selected_index,
                    len(self.optimizer.slots) - 1,
                )
                self.observation_clone = None
                self._clone_history.clear()
                self.pending_reset_parameters = {}
                self.last_search = self._empty_search_summary()
                self.last_error = None
            elif action == "save":
                return {**self.state(), "snapshot": self.optimizer.to_snapshot()}
            else:
                raise ValueError(f"unsupported runtime action: {action}")
            return self.state()

    def close(self) -> None:
        self._stop.set()
        self.pause()
        if self._thread is not None:
            self._thread.join(timeout=1)
