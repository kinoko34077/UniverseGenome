from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from core.physics import PhysicsConfig
from research.legacy_outer_search_oracle import load_legacy_base_config
from search.evolution import SteadyStateOptimizer
from search.genome import UniverseGenome
from search.outer_search import (
    build_default_search_registry,
    legacy_candidate_values,
    legacy_mutation_directions,
    legacy_mutation_plan_for_base_config,
    legacy_search_plan,
    mutate_legacy_candidate,
    mutate_scalar_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "research" / "artifacts" / "legacy_outer_search_oracle_v1" / "oracle.json"


class OuterSearchMutationTests(unittest.TestCase):
    def test_generic_scalar_mutation_matches_frozen_phase_a_probes(self):
        probes = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))["decisions"]["mutation_probes"]
        registry = build_default_search_registry()
        plan = legacy_search_plan(base_seed=0)
        base = load_legacy_base_config()

        self.assertEqual(len(probes), 4)
        for probe in probes:
            parent = UniverseGenome.from_dict(dict(probe["parent"]["genome"]))
            candidate = legacy_candidate_values(parent, probe["category"])
            result = mutate_scalar_candidate(
                plan=plan,
                registry=registry,
                candidate=candidate,
                dimension_id=probe["mutation_field"],
                direction=int(probe["mutation_direction"]),
                base_config=base,
            )
            self.assertEqual(result.dimension_id, probe["mutation_field"])
            self.assertEqual(result.direction, probe["mutation_direction"])
            self.assertEqual(result.before, probe["mutation_before"])
            self.assertEqual(result.after, probe["mutation_after"])
            self.assertEqual(result.candidate_values.scalars, probe["child"]["genome"])
            self.assertEqual(
                result.resolved_candidate.universe_spec.to_physics_config(base).to_dict(),
                probe["child"]["state"]["config"],
            )

    def test_integrated_legacy_mutation_matches_frozen_scheduler_probes(self):
        probes = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))["decisions"]["mutation_probes"]
        base = load_legacy_base_config()

        for probe in probes:
            optimizer = SteadyStateOptimizer.from_defaults(
                base_seed=0,
                base_config=base,
            )
            self.assertEqual(optimizer.scheduler, probe["scheduler_before"])
            parent = optimizer.slots[int(probe["parent"]["index"])]
            child = optimizer.replace_free_slot(
                free_index=int(probe["child"]["index"]),
                parent=parent,
            )

            self.assertEqual(child.last_mutation_field, probe["mutation_field"])
            self.assertEqual(child.genome.to_dict(), probe["child"]["genome"])
            self.assertEqual(child.seed, probe["child"]["seed"])
            self.assertEqual(child.state.config.to_dict(), probe["child"]["state"]["config"])
            self.assertEqual(child.parent_index, probe["child"]["parent_index"])
            self.assertEqual(child.parent_genome_key, probe["child"]["parent_genome_key"])
            self.assertEqual(child.allocation_reason, probe["child"]["allocation_reason"])
            self.assertEqual(optimizer.scheduler, probe["scheduler_after"])

            before = int(probe["mutation_before"])
            after = int(getattr(child.genome, probe["mutation_field"]))
            actual_direction = 1 if after > before else -1
            self.assertEqual(actual_direction, probe["mutation_direction"])
            self.assertEqual(after, probe["mutation_after"])

    def test_generic_mutation_directions_respect_effective_max_cells(self):
        registry = build_default_search_registry()
        plan = legacy_search_plan(base_seed=0)
        base = PhysicsConfig(max_cells=8)

        upper = legacy_candidate_values(UniverseGenome(initial_density=8), "masked_copy")
        lower = legacy_candidate_values(UniverseGenome(initial_density=0), "masked_copy")

        self.assertEqual(
            legacy_mutation_directions(
                plan=plan,
                registry=registry,
                candidate=upper,
                dimension_id="initial_density",
                base_config=base,
            ),
            (-1,),
        )
        self.assertEqual(
            legacy_mutation_directions(
                plan=plan,
                registry=registry,
                candidate=lower,
                dimension_id="initial_density",
                base_config=base,
            ),
            (1,),
        )

    def test_legacy_mutation_keeps_explicit_fixed_research_physics_fixed(self):
        base = PhysicsConfig(
            max_cells=8,
            trace_write_cap=32,
            trace_transfer_cap=8,
            trace_discharge_cap=16,
            trace_decay_rate=256,
            trace_bonus_shift=5,
        )
        plan = legacy_mutation_plan_for_base_config(base)
        self.assertNotIn("trace_write_cap", plan.search)
        self.assertEqual(
            tuple(
                plan.fixed[key]
                for key in (
                    "trace_write_cap",
                    "trace_transfer_cap",
                    "trace_discharge_cap",
                    "trace_decay_rate",
                    "trace_bonus_shift",
                )
            ),
            (32, 8, 16, 256, 5),
        )

        optimizer = SteadyStateOptimizer.from_defaults(base_seed=0, base_config=base)
        child = optimizer.replace_free_slot(
            free_index=31,
            parent=optimizer.slots[0],
            field="hp_decay",
            direction=1,
        )
        self.assertEqual(child.state.config.trace_write_cap, 32)
        self.assertEqual(child.state.config.trace_transfer_cap, 8)
        self.assertEqual(child.state.config.trace_discharge_cap, 16)
        self.assertEqual(child.state.config.trace_decay_rate, 256)
        self.assertEqual(child.state.config.trace_bonus_shift, 5)

    def test_phase5_replace_free_slot_routes_through_generic_mutation(self):
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=0,
            base_config=PhysicsConfig(max_cells=8),
        )
        parent = optimizer.slots[0]

        with patch(
            "search.evolution.mutate_legacy_candidate",
            wraps=mutate_legacy_candidate,
        ) as routed:
            child = optimizer.replace_free_slot(
                free_index=31,
                parent=parent,
                field="hp_decay",
                direction=1,
            )

        routed.assert_called_once()
        self.assertEqual(child.last_mutation_field, "hp_decay")
        self.assertEqual(child.genome.hp_decay, 2)
        self.assertEqual(child.category, parent.category)
        self.assertEqual(child.parent_genome_key, parent.genome_key)
        self.assertEqual(child.allocation_reason, "mutation_child")


if __name__ == "__main__":
    unittest.main()
