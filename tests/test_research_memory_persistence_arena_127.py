from __future__ import annotations

import json
from pathlib import Path
import unittest

from core import physics as P
from core.physics import PhysicsConfig, create_universe
from core.runner import load_config
from core.state import UniverseState
from research.memory_persistence_arena_127 import (
    BASELINE,
    EMPIRICAL_CANDIDATES,
    ENERGY_TO_LATENT_XOR,
    ENERGY_TO_STRUCTURE_PROMOTE,
    HP_NO_DECAY_REFERENCE,
    PRIMARY_DENSITY32_SEEDS,
    REQUIRED_PRIMARY,
    candidate_config,
    case_plan,
    variant_step,
)


def metrics_projection(metrics):
    return {
        "generation": metrics.generation,
        "active_cells": metrics.active_cells,
        "collision_count": metrics.collision_count,
        "collision_pair_evaluations": metrics.collision_pair_evaluations,
        "bond_contact_count": metrics.bond_contact_count,
        "latent_transmission_count": metrics.latent_transmission_count,
        "fusion_count": metrics.fusion_count,
        "fragmentation_count": metrics.fragmentation_count,
        "noise_spawn_count": metrics.noise_spawn_count,
    }


class MemoryPersistenceArena127Tests(unittest.TestCase):
    def test_frozen_plan_and_gate(self) -> None:
        self.assertEqual(
            PRIMARY_DENSITY32_SEEDS,
            (0, 5, 8, 9, 12, 14, 18, 19, 20, 22, 24, 29),
        )
        self.assertEqual(REQUIRED_PRIMARY, 8)
        self.assertEqual(
            EMPIRICAL_CANDIDATES,
            (
                ENERGY_TO_LATENT_XOR,
                ENERGY_TO_STRUCTURE_PROMOTE,
                HP_NO_DECAY_REFERENCE,
            ),
        )
        plan = case_plan()
        self.assertEqual(len(plan), 63)
        for candidate in EMPIRICAL_CANDIDATES:
            self.assertEqual(
                sum(item["candidate"] == candidate for item in plan),
                21,
            )

    def test_generated_baseline_step_matches_production(self) -> None:
        for density in (4, 32):
            config = PhysicsConfig(
                initial_density=density,
                initial_latent=1,
                initial_speed_code=1,
                hp_decay=1,
                recovery_hp=32,
            )
            left = create_universe(seed=7, config=config)
            right = UniverseState.from_snapshot(
                left.to_snapshot(), config=config
            )
            for generation in range(6):
                active = left.active_slots()
                stimulus = (
                    (active[0],)
                    if generation % 2 == 0 and active
                    else ()
                )
                production = P.step(left, stimulus_slots=stimulus)
                research = variant_step(
                    right,
                    stimulus_slots=stimulus,
                    candidate=BASELINE,
                    candidate_write_log=[],
                )
                self.assertEqual(left.to_snapshot(), right.to_snapshot())
                self.assertEqual(
                    metrics_projection(production),
                    metrics_projection(research),
                )

    def test_candidate_hooks_change_only_frozen_target_field(self) -> None:
        config = PhysicsConfig(
            initial_density=1,
            initial_latent=1,
            initial_speed_code=0,
            hp_decay=1,
            recovery_hp=32,
        )
        base = create_universe(seed=3, config=config)
        slot = base.active_slots()[0]
        base.hp[slot] = 100
        source = base.to_snapshot()

        baseline = UniverseState.from_snapshot(source, config=config)
        latent = UniverseState.from_snapshot(source, config=config)
        structure = UniverseState.from_snapshot(source, config=config)

        variant_step(
            baseline,
            stimulus_slots=(slot,),
            candidate=BASELINE,
            candidate_write_log=[],
        )
        latent_log = []
        variant_step(
            latent,
            stimulus_slots=(slot,),
            candidate=ENERGY_TO_LATENT_XOR,
            candidate_write_log=latent_log,
        )
        structure_log = []
        variant_step(
            structure,
            stimulus_slots=(slot,),
            candidate=ENERGY_TO_STRUCTURE_PROMOTE,
            candidate_write_log=structure_log,
        )

        self.assertEqual(latent.hp, baseline.hp)
        self.assertEqual(structure.hp, baseline.hp)
        self.assertNotEqual(latent.latent[slot], baseline.latent[slot])
        self.assertEqual(latent.structure, baseline.structure)
        self.assertNotEqual(
            structure.structure[slot], baseline.structure[slot]
        )
        self.assertEqual(structure.latent, baseline.latent)
        self.assertEqual(len(latent_log), 1)
        self.assertEqual(len(structure_log), 1)

    def test_saturated_external_contact_does_not_consolidate(self) -> None:
        config = PhysicsConfig(
            initial_density=1,
            initial_latent=1,
            initial_speed_code=0,
            hp_decay=1,
            recovery_hp=32,
        )
        state = create_universe(seed=4, config=config)
        slot = state.active_slots()[0]
        state.hp[slot] = 255
        before_latent = state.latent[slot]
        log = []
        variant_step(
            state,
            stimulus_slots=(slot,),
            candidate=ENERGY_TO_LATENT_XOR,
            candidate_write_log=log,
        )
        self.assertEqual(log, [])
        self.assertEqual(state.latent[slot], before_latent)

    def test_hp_reference_is_parameter_only(self) -> None:
        payload = load_config(Path("config/default.json"))
        baseline = candidate_config(
            payload, density=32, candidate=BASELINE
        )
        reference = candidate_config(
            payload, density=32, candidate=HP_NO_DECAY_REFERENCE
        )
        self.assertEqual(baseline.hp_decay, 1)
        self.assertEqual(reference.hp_decay, 0)
        baseline_values = baseline.to_dict()
        reference_values = reference.to_dict()
        baseline_values["hp_decay"] = 0
        self.assertEqual(baseline_values, reference_values)


if __name__ == "__main__":
    unittest.main()

    def test_energy_to_latent_xor_uses_positive_recovery_amount(self) -> None:
        config = candidate_config(
            self.config_payload,
            1,
            C1_ENERGY_TO_LATENT_XOR,
        )
        state = create_universe(seed=3, config=config)
        state.hp[0] = 100
        state.latent[0] = 1

        _, writes = candidate_step(
            state,
            config,
            variant=C1_ENERGY_TO_LATENT_XOR,
            stimulus_slots=(0,),
        )

        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]["field"], "latent")
        self.assertEqual(writes[0]["energy"], config.recovery_hp)
        self.assertEqual(state.latent[0], 1 ^ config.recovery_hp)

    def test_energy_candidate_no_write_when_no_positive_recovery(self) -> None:
        config = candidate_config(
            self.config_payload,
            1,
            C1_ENERGY_TO_LATENT_XOR,
        )
        state = create_universe(seed=4, config=config)
        state.hp[0] = 255
        before = state.latent[0]

        _, writes = candidate_step(
            state,
            config,
            variant=C1_ENERGY_TO_LATENT_XOR,
            stimulus_slots=(0,),
        )

        self.assertEqual(writes, [])
        self.assertEqual(state.latent[0], before)

    def test_hp_no_decay_reference_only_changes_hp_decay(self) -> None:
        baseline = candidate_config(
            self.config_payload,
            4,
            C0_BASELINE,
        )
        reference = candidate_config(
            self.config_payload,
            4,
            C4_HP_NO_DECAY_REFERENCE,
        )
        self.assertEqual(reference.hp_decay, 0)
        self.assertNotEqual(baseline.hp_decay, reference.hp_decay)
        baseline_values = baseline.to_mapping()["physics"]
        reference_values = reference.to_mapping()["physics"]
        changed = {
            key
            for key in baseline_values
            if baseline_values[key] != reference_values[key]
        }
        self.assertEqual(changed, {"hp_decay"})

    def test_completed_case_ledger_is_resume_readable(self) -> None:
        first = {
            "status": "complete",
            "variant": C0_BASELINE,
            "seed": 0,
            "initial_density": 32,
        }
        second = {
            "status": "complete",
            "variant": C1_ENERGY_TO_LATENT_XOR,
            "seed": 5,
            "initial_density": 32,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "partial.jsonl"
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                append_case(handle, first)
            completed = read_completed(path)
            self.assertEqual(
                set(completed),
                {case_key(C0_BASELINE, 32, 0)},
            )

            with path.open("a", encoding="utf-8", newline="\n") as handle:
                append_case(handle, second)
            completed = read_completed(path)
            self.assertEqual(
                set(completed),
                {
                    case_key(C0_BASELINE, 32, 0),
                    case_key(C1_ENERGY_TO_LATENT_XOR, 32, 5),
                },
            )


if __name__ == "__main__":
    unittest.main()
