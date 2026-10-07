from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from core.physics import PhysicsConfig
from search.evolution import SteadyStateOptimizer
from search.genome import UniverseGenome
from search.outer_search import (
    build_default_search_registry,
    legacy_candidate_values,
    legacy_mutation_directions,
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
                base_config=PhysicsConfig(max_cells=8),
            )
            self.assertEqual(result.dimension_id, probe["mutation_field"])
            self.assertEqual(result.direction, probe["mutation_direction"])
            self.assertEqual(result.before, probe["mutation_before"])
            self.assertEqual(result.after, probe["mutation_after"])
            self.assertEqual(result.candidate_values.scalars, probe["child"]["genome"])
            self.assertEqual(
                result.resolved_candidate.universe_spec.to_physics_config(
                    PhysicsConfig(max_cells=8)
                ).to_dict(),
                probe["child"]["state"]["config"],
            )

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
