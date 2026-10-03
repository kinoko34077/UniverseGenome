"""Authoritative bounded runtime exposed to the Phase 3 observer surface."""

from __future__ import annotations

from threading import Event, RLock, Thread
from typing import Any

from core.population import Population
from core.physics import PhysicsConfig


class PopulationRuntime:
    """Own population state and controls outside the browser render loop."""

    MAX_CONTROL_GENERATIONS = 512

    def __init__(
        self,
        *,
        base_seed: int = 0,
        history_length: int = 128,
        config: PhysicsConfig | None = None,
    ) -> None:
        self.base_seed = int(base_seed)
        self.history_length = int(history_length)
        self.config = config or PhysicsConfig(initial_density=4)
        self.population = Population.from_defaults(
            base_seed=self.base_seed,
            config=self.config,
            history_length=self.history_length,
        )
        self.selected_index = 0
        self.running = False
        self._lock = RLock()
        self._stop = Event()
        self._thread: Thread | None = None

    @staticmethod
    def _cell_payload(state: Any) -> list[dict[str, int]]:
        return [
            {
                "slot": slot,
                "x": (state.x[slot] // 8) % 32,
                "y": (state.y[slot] // 8) % 32,
                "structure": state.structure[slot],
                "latent": state.latent[slot],
                "hp": state.hp[slot],
                "bond": state.bond_strength[slot],
                "age": state.age[slot],
            }
            for slot in state.active_slots()
        ]

    def _slot_summary(self, index: int) -> dict[str, Any]:
        slot = self.population.slots[index]
        cells = self._cell_payload(slot.state)
        return {
            "index": slot.index,
            "category": slot.category,
            "genome_id": slot.genome_id,
            "seed": slot.seed,
            "active_cells": len(cells),
        }

    def state(self) -> dict[str, Any]:
        with self._lock:
            selected = self.population.slots[self.selected_index]
            return {
                **self.population.summary(),
                "running": self.running,
                "selected_index": self.selected_index,
                "summaries": [self._slot_summary(index) for index in range(len(self.population.slots))],
                "selected": {
                    **self._slot_summary(self.selected_index),
                    "generation": selected.state.generation,
                    "cells": self._cell_payload(selected.state),
                },
            }

    def _run_loop(self) -> None:
        while not self._stop.wait(0.05):
            with self._lock:
                if not self.running:
                    continue
                self.population.step()

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

    def _bounded_generations(self, value: Any) -> int:
        generations = int(value if value is not None else 1)
        if not 0 <= generations <= self.MAX_CONTROL_GENERATIONS:
            raise ValueError("control generations exceed bounded runtime limit")
        return generations

    def control(self, action: str, **payload: Any) -> dict[str, Any]:
        with self._lock:
            if action == "run":
                self.run()
            elif action == "pause":
                self.pause()
            elif action == "step":
                self.pause()
                for _ in range(self._bounded_generations(payload.get("generations", 1))):
                    self.population.step()
            elif action == "reset":
                self.pause()
                self.population = Population.from_defaults(
                    base_seed=self.base_seed,
                    config=self.config,
                    history_length=self.history_length,
                )
                self.selected_index = 0
            elif action == "select":
                index = int(payload["index"])
                if not 0 <= index < len(self.population.slots):
                    raise IndexError("selected universe index out of range")
                self.selected_index = index
            elif action == "clone":
                clone = self.population.clone_for_observation(self.selected_index)
                return {
                    **self.state(),
                    "clone": {
                        "index": clone.index,
                        "category": clone.category,
                        "genome_id": clone.genome_id,
                        "seed": clone.seed,
                        "generation": clone.state.generation,
                        "active_cells": len(clone.state.active_slots()),
                    },
                }
            elif action == "rewind":
                self.pause()
                self.population.rewind(self._bounded_generations(payload.get("generations", 1)))
            elif action == "load":
                self.pause()
                self.population = Population.from_snapshot(payload["snapshot"])
                self.history_length = self.population.history_length
                loaded_config = self.population.slots[0].state.config
                if isinstance(loaded_config, PhysicsConfig):
                    self.config = loaded_config
                self.selected_index = min(self.selected_index, len(self.population.slots) - 1)
            elif action == "save":
                return {**self.state(), "snapshot": self.population.to_snapshot()}
            else:
                raise ValueError(f"unsupported runtime action: {action}")
            return self.state()

    def close(self) -> None:
        self._stop.set()
        self.pause()
        if self._thread is not None:
            self._thread.join(timeout=1)
