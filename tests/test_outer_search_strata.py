from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from research.legacy_outer_search_oracle import load_legacy_base_config
from search.evolution import SteadyStateOptimizer
from search.outer_search import (
    CandidateValues,
    ComparisonStratum,
    RuleDimension,
    RuleSearch,
    SearchPlan,
    SearchRegistry,
    build_default_search_registry,
    enumerate_comparison_strata,
    legacy_comparison_strata,
    legacy_search_plan,
    resolve_candidate_stratum,
)


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "research" / "artifacts" / "legacy_outer_search_oracle_v1" / "oracle.json"


class OuterSearchStrataTests(unittest.TestCase):
    def test_legacy_rule_strata_match_frozen_four_category_layout(self):
        oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))["static"]
        registry = build_default_search_registry()
        plan = legacy_search_plan(base_seed=0)

        strata = legacy_comparison_strata(plan=plan, registry=registry)

        self.assertEqual(len(strata), 4)
        self.assertEqual(
            [dict(item.values)["latent_operator"] for item in strata],
            ["masked_copy", "masked_xor", "rotate_copy", "masked_and"],
        )
        self.assertTrue(all(item.selection_scope == "within" for item in strata))
        self.assertTrue(
            all(item.allocation_policy == "tiered_category_rank" for item in strata)
        )
        self.assertTrue(
            all(item.matched_evidence_policy == "legacy_matched_seed" for item in strata)
        )
        self.assertEqual(
            oracle["category_counts"],
            {dict(item.values)["latent_operator"]: 32 for item in strata},
        )

    def test_generic_rule_strata_do_not_require_hard_coded_variant_names(self):
        registry = SearchRegistry(
            scalar_dimensions={},
            rule_dimensions={
                "memory_rule": RuleDimension(
                    dimension_id="memory_rule",
                    physics_field="latent_operator",
                    variants=("alpha", "beta", "gamma"),
                    default_variant="alpha",
                    strategy_ids=("finite_variant",),
                ),
            },
        )
        plan = SearchPlan(
            schema_version=1,
            plan_id="test-rule-strata",
            plan_version=1,
            population_size=6,
            rules={
                "memory_rule": RuleSearch(
                    ("gamma", "alpha"),
                    "finite_variant",
                ),
            },
            strata=(
                ComparisonStratum(
                    group_by=("memory_rule",),
                    selection_scope="within",
                    allocation_policy="test-allocation",
                    matched_evidence_policy="test-matched",
                ),
            ),
        )
        plan.validate(registry)

        strata = enumerate_comparison_strata(plan, registry)

        self.assertEqual(
            [item.values for item in strata],
            [
                (("memory_rule", "gamma"),),
                (("memory_rule", "alpha"),),
            ],
        )
        self.assertTrue(all(item.selection_scope == "within" for item in strata))

    def test_candidate_resolves_to_declared_rule_stratum(self):
        registry = build_default_search_registry()
        plan = legacy_search_plan(base_seed=0)
        candidate = CandidateValues(
            scalars={
                key: value.default
                for key, value in registry.scalar_dimensions.items()
                if key in plan.search
            },
            rules={"latent_operator": "rotate_copy"},
        )

        stratum = resolve_candidate_stratum(
            plan,
            registry,
            candidate,
        )

        self.assertEqual(stratum.values, (("latent_operator", "rotate_copy"),))
        self.assertEqual(stratum.selection_scope, "within")

    def test_legacy_optimizer_category_projection_routes_through_generic_strata(self):
        base = load_legacy_base_config()
        with patch(
            "search.evolution.legacy_comparison_strata",
            wraps=legacy_comparison_strata,
        ) as routed:
            optimizer = SteadyStateOptimizer.from_defaults(
                base_seed=0,
                base_config=base,
            )
            counts = optimizer._category_counts()
            groups = optimizer._comparison_strata()

        self.assertGreaterEqual(routed.call_count, 1)
        self.assertEqual(
            [local[0].category for _, local in groups],
            ["masked_copy", "masked_xor", "rotate_copy", "masked_and"],
        )
        self.assertEqual([len(local) for _, local in groups], [32, 32, 32, 32])
        self.assertEqual(
            counts,
            {
                "masked_copy": 32,
                "masked_xor": 32,
                "rotate_copy": 32,
                "masked_and": 32,
            },
        )
        self.assertEqual(
            {
                key: value
                for key, value in optimizer.scheduler.items()
                if key.startswith("allocation_mode_cursor:")
            },
            {
                "allocation_mode_cursor:masked_copy": 0,
                "allocation_mode_cursor:masked_xor": 0,
                "allocation_mode_cursor:rotate_copy": 0,
                "allocation_mode_cursor:masked_and": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
