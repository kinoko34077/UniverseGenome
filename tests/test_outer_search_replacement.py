from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from research.legacy_outer_search_oracle import load_legacy_base_config
from search.evolution import SteadyStateOptimizer
from search.genome import UniverseGenome
from search.outer_search import (
    build_default_search_registry,
    build_mutation_replacement,
    build_seed_evidence_replacement,
    legacy_candidate_values,
    legacy_mutation_plan_for_base_config,
    mutate_scalar_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = (
    ROOT
    / "research"
    / "artifacts"
    / "legacy_outer_search_oracle_v1"
    / "oracle.json"
)


class OuterSearchReplacementTests(unittest.TestCase):
    def test_seed_evidence_replacement_record_preserves_candidate_and_lineage(self):
        base = load_legacy_base_config()
        registry = build_default_search_registry()
        plan = legacy_mutation_plan_for_base_config(base)
        parent = legacy_candidate_values(UniverseGenome.default(), "masked_copy")

        replacement = build_seed_evidence_replacement(
            plan=plan,
            registry=registry,
            parent_candidate=parent,
            target_index=31,
            parent_index=0,
            seed=32,
            parent_evidence_mature=True,
        )

        self.assertEqual(replacement.target_index, 31)
        self.assertEqual(replacement.seed, 32)
        self.assertEqual(replacement.allocation_reason, "seed_evidence")
        self.assertIsNone(replacement.mutation_dimension)
        self.assertIsNone(replacement.mutation_direction)
        self.assertTrue(replacement.evidence_mature)
        self.assertEqual(replacement.candidate_values, parent)
        self.assertEqual(
            replacement.parent_candidate_identity,
            replacement.resolved_candidate.candidate_identity,
        )

    def test_mutation_replacement_record_preserves_generic_child_and_parent_identity(self):
        base = load_legacy_base_config()
        registry = build_default_search_registry()
        plan = legacy_mutation_plan_for_base_config(base)
        parent = legacy_candidate_values(UniverseGenome.default(), "masked_copy")
        mutation = mutate_scalar_candidate(
            plan=plan,
            registry=registry,
            candidate=parent,
            dimension_id="hp_decay",
            direction=1,
            base_config=base,
        )

        replacement = build_mutation_replacement(
            plan=plan,
            registry=registry,
            parent_candidate=parent,
            mutation=mutation,
            target_index=31,
            parent_index=0,
            seed=32,
        )

        self.assertEqual(replacement.target_index, 31)
        self.assertEqual(replacement.seed, 32)
        self.assertEqual(replacement.allocation_reason, "mutation_child")
        self.assertEqual(replacement.mutation_dimension, "hp_decay")
        self.assertEqual(replacement.mutation_direction, 1)
        self.assertFalse(replacement.evidence_mature)
        self.assertNotEqual(
            replacement.parent_candidate_identity,
            replacement.resolved_candidate.candidate_identity,
        )
        self.assertEqual(replacement.candidate_values.scalars["hp_decay"], 2)

    def test_integrated_replacement_paths_match_frozen_phase_a_probes(self):
        oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
        base = load_legacy_base_config()

        for probe in oracle["decisions"]["seed_evidence_probes"]:
            optimizer = SteadyStateOptimizer.from_defaults(base_seed=0, base_config=base)
            parent = optimizer.slots[int(probe["parent"]["index"])]
            with patch(
                "search.evolution.build_seed_evidence_replacement",
                wraps=build_seed_evidence_replacement,
            ) as routed:
                child = optimizer.allocate_seed_slot(
                    free_index=int(probe["child"]["index"]),
                    parent=parent,
                )
            routed.assert_called_once()
            self.assertEqual(child.seed, probe["child"]["seed"])
            self.assertEqual(child.genome.to_dict(), probe["child"]["genome"])
            self.assertEqual(child.category, probe["child"]["category"])
            self.assertEqual(child.parent_index, probe["child"]["parent_index"])
            self.assertEqual(child.parent_genome_key, probe["child"]["parent_genome_key"])
            self.assertEqual(child.allocation_reason, probe["child"]["allocation_reason"])
            self.assertEqual(child.state.config.to_dict(), probe["child"]["state"]["config"])
            self.assertEqual(optimizer.scheduler, probe["scheduler_after"])

        for probe in oracle["decisions"]["mutation_probes"]:
            optimizer = SteadyStateOptimizer.from_defaults(base_seed=0, base_config=base)
            parent = optimizer.slots[int(probe["parent"]["index"])]
            with patch(
                "search.evolution.build_mutation_replacement",
                wraps=build_mutation_replacement,
            ) as routed:
                child = optimizer.replace_free_slot(
                    free_index=int(probe["child"]["index"]),
                    parent=parent,
                )
            routed.assert_called_once()
            self.assertEqual(child.seed, probe["child"]["seed"])
            self.assertEqual(child.genome.to_dict(), probe["child"]["genome"])
            self.assertEqual(child.category, probe["child"]["category"])
            self.assertEqual(child.parent_index, probe["child"]["parent_index"])
            self.assertEqual(child.parent_genome_key, probe["child"]["parent_genome_key"])
            self.assertEqual(child.last_mutation_field, probe["mutation_field"])
            self.assertEqual(child.allocation_reason, probe["child"]["allocation_reason"])
            self.assertEqual(child.state.config.to_dict(), probe["child"]["state"]["config"])
            self.assertEqual(optimizer.scheduler, probe["scheduler_after"])


if __name__ == "__main__":
    unittest.main()
