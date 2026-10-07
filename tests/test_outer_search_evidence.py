from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from research.legacy_outer_search_oracle import load_legacy_base_config
from search.evolution import SteadyStateOptimizer, seed_escalation
from search.outer_search import (
    CandidateValues,
    ComparisonStratum,
    EvidenceSeedAssignment,
    RuleDimension,
    RuleSearch,
    ScalarDimension,
    ScalarSearch,
    SearchPlan,
    SearchRegistry,
    allocate_matched_evidence_seed,
    evidence_tier_target,
)


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = (
    ROOT
    / "research"
    / "artifacts"
    / "legacy_outer_search_oracle_v1"
    / "oracle.json"
)


class OuterSearchEvidenceTests(unittest.TestCase):
    def test_generic_matched_seed_policy_uses_candidate_equivalence_across_rule_strata(self):
        registry = SearchRegistry(
            scalar_dimensions={
                "physical_x": ScalarDimension(
                    dimension_id="physical_x",
                    physics_field="hp_decay",
                    value_type="int",
                    default=1,
                    allowed_values=(1, 2),
                    strategy_ids=("adjacent_binary",),
                ),
            },
            rule_dimensions={
                "rule_family": RuleDimension(
                    dimension_id="rule_family",
                    physics_field="latent_operator",
                    variants=("r3", "r1"),
                    default_variant="r3",
                    strategy_ids=("finite_variant",),
                ),
            },
        )
        plan = SearchPlan(
            schema_version=1,
            plan_id="test-matched-evidence",
            plan_version=1,
            population_size=8,
            search={
                "physical_x": ScalarSearch("adjacent_binary", (1, 2)),
            },
            rules={
                "rule_family": RuleSearch(("r3", "r1"), "finite_variant"),
            },
            strata=(
                ComparisonStratum(
                    group_by=("rule_family",),
                    selection_scope="within",
                    allocation_policy="tiered_category_rank",
                    matched_evidence_policy="legacy_matched_seed",
                ),
            ),
        )
        target = CandidateValues(
            scalars={"physical_x": 1},
            rules={"rule_family": "r1"},
        )
        assignments = (
            EvidenceSeedAssignment(
                candidate_values=CandidateValues(
                    scalars={"physical_x": 1},
                    rules={"rule_family": "r1"},
                ),
                seed=10,
            ),
            EvidenceSeedAssignment(
                candidate_values=CandidateValues(
                    scalars={"physical_x": 2},
                    rules={"rule_family": "r1"},
                ),
                seed=11,
            ),
            EvidenceSeedAssignment(
                candidate_values=CandidateValues(
                    scalars={"physical_x": 1},
                    rules={"rule_family": "r3"},
                ),
                seed=12,
            ),
            EvidenceSeedAssignment(
                candidate_values=CandidateValues(
                    scalars={"physical_x": 2},
                    rules={"rule_family": "r3"},
                ),
                seed=9,
            ),
        )

        decision = allocate_matched_evidence_seed(
            plan=plan,
            registry=registry,
            target_candidate=target,
            assignments=assignments,
            allocation_cursor=20,
        )

        self.assertEqual(decision.seed, 12)
        self.assertTrue(decision.matched_existing_evidence)
        self.assertEqual(decision.next_allocation_cursor, 20)

    def test_generic_matched_seed_fallback_uses_target_stratum_occupancy_and_cursor(self):
        registry = SearchRegistry(
            scalar_dimensions={
                "physical_x": ScalarDimension(
                    dimension_id="physical_x",
                    physics_field="hp_decay",
                    value_type="int",
                    default=1,
                    allowed_values=(1, 2),
                    strategy_ids=("adjacent_binary",),
                ),
            },
            rule_dimensions={
                "rule_family": RuleDimension(
                    dimension_id="rule_family",
                    physics_field="latent_operator",
                    variants=("left", "right"),
                    default_variant="left",
                    strategy_ids=("finite_variant",),
                ),
            },
        )
        plan = SearchPlan(
            schema_version=1,
            plan_id="test-matched-fallback",
            plan_version=1,
            population_size=8,
            search={"physical_x": ScalarSearch("adjacent_binary", (1, 2))},
            rules={"rule_family": RuleSearch(("left", "right"), "finite_variant")},
            strata=(
                ComparisonStratum(
                    group_by=("rule_family",),
                    selection_scope="within",
                    allocation_policy="tiered_category_rank",
                    matched_evidence_policy="legacy_matched_seed",
                ),
            ),
        )
        target = CandidateValues(
            scalars={"physical_x": 1},
            rules={"rule_family": "right"},
        )
        assignments = (
            EvidenceSeedAssignment(
                candidate_values=CandidateValues(
                    scalars={"physical_x": 1},
                    rules={"rule_family": "left"},
                ),
                seed=20,
            ),
            EvidenceSeedAssignment(
                candidate_values=CandidateValues(
                    scalars={"physical_x": 2},
                    rules={"rule_family": "right"},
                ),
                seed=20,
            ),
            EvidenceSeedAssignment(
                candidate_values=CandidateValues(
                    scalars={"physical_x": 1},
                    rules={"rule_family": "right"},
                ),
                seed=21,
            ),
        )

        decision = allocate_matched_evidence_seed(
            plan=plan,
            registry=registry,
            target_candidate=target,
            assignments=assignments,
            allocation_cursor=20,
        )

        self.assertEqual(decision.seed, 22)
        self.assertFalse(decision.matched_existing_evidence)
        self.assertEqual(decision.next_allocation_cursor, 23)

    def test_frozen_phase_a_seed_evidence_probes_match_integrated_generic_route(self):
        oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
        probes = oracle["decisions"]["seed_evidence_probes"]
        base = load_legacy_base_config()

        self.assertEqual(len(probes), 4)
        for probe in probes:
            optimizer = SteadyStateOptimizer.from_defaults(
                base_seed=0,
                base_config=base,
            )
            self.assertEqual(optimizer.scheduler, probe["scheduler_before"])
            parent = optimizer.slots[int(probe["parent"]["index"])]

            with patch(
                "search.evolution.allocate_matched_evidence_seed",
                wraps=allocate_matched_evidence_seed,
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

    def test_frozen_evidence_escalation_remains_allocation_policy_authority(self):
        oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
        frozen = oracle["decisions"]["seed_escalation"]

        for count in (4, 8, 16, 32):
            expected = int(frozen[str(count)])
            self.assertEqual(
                evidence_tier_target("tiered_category_rank", count),
                expected,
            )
            self.assertEqual(seed_escalation(count), expected)


if __name__ == "__main__":
    unittest.main()
