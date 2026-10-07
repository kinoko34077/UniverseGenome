from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core.physics import PhysicsConfig
from search.evolution import SteadyStateOptimizer
from search.fitness import Fitness
from search.outer_search import (
    LEGACY_OBJECTIVE_PROFILE_ID,
    LEGACY_OBJECTIVE_PROFILE_VERSION,
    bind_objective_profile,
    build_default_search_registry,
    legacy_objective_profile,
    legacy_search_plan,
    objective_absolute_failure_reason,
    objective_growth_flags,
    objective_key,
    objective_short_health_flags,
)


class OuterSearchObjectiveProfileTests(unittest.TestCase):
    def test_legacy_profile_freezes_phase5_objective_contract(self):
        profile = legacy_objective_profile()

        self.assertEqual(profile.profile_id, LEGACY_OBJECTIVE_PROFILE_ID)
        self.assertEqual(profile.version, LEGACY_OBJECTIVE_PROFILE_VERSION)
        self.assertEqual(profile.minimum_evidence, 4)
        self.assertEqual(
            [(item.metric_id, item.direction) for item in profile.comparison_metrics],
            [
                ("success", "maximize"),
                ("wrong_outputs", "minimize"),
                ("timeouts", "minimize"),
                ("response_latency", "minimize"),
                ("activity_cost", "minimize"),
            ],
        )
        self.assertEqual(
            [(item.metric_id, item.growth_bit) for item in profile.growth_metrics],
            [
                ("success", 0),
                ("wrong_outputs", 1),
                ("timeouts", 2),
                ("response_latency", 3),
                ("activity_cost", 4),
                ("retention", 5),
                ("noise_robustness", 6),
            ],
        )
        self.assertEqual(
            profile.negative_control_fields,
            (
                "counterfactual_no_input_clean",
                "counterfactual_alternate_input_clean",
            ),
        )
        self.assertEqual(profile.negative_control_policy, "observe_only")
        self.assertEqual(profile.invalid_evidence_policy, "ineligible")
        self.assertEqual(profile.short_health_policy, "phase5_short_health_v1")
        self.assertEqual(profile.failure_policy, "phase5_failure_v1")
        self.assertEqual(profile.response_window_limit, 4)

    def test_plan_binding_rejects_unknown_objective_profile(self):
        registry = build_default_search_registry()
        plan = legacy_search_plan(base_seed=0)

        bound = bind_objective_profile(plan, registry)
        self.assertEqual(bound, legacy_objective_profile())

        unknown = plan.__class__(
            **{
                **plan.__dict__,
                "objective_profile_id": "does_not_exist",
                "objective_profile_version": 1,
            }
        )
        with self.assertRaisesRegex(ValueError, "unknown ObjectiveProfile"):
            unknown.validate(registry)

    def test_legacy_profile_key_matches_fitness_sort_key_and_ignores_negative_controls(self):
        profile = legacy_objective_profile()
        fitness = Fitness(
            success=0.75,
            wrong_outputs=1.25,
            timeouts=0.5,
            response_latency=7.0,
            activity_cost=20.0,
            retention=0.8,
            noise_robustness=0.6,
            counterfactual_no_input_clean=0.25,
            counterfactual_alternate_input_clean=0.5,
        )
        payload = fitness.to_dict()

        self.assertEqual(objective_key(profile, payload), fitness.sort_key())

        changed_controls = dict(payload)
        changed_controls["counterfactual_no_input_clean"] = 999.0
        changed_controls["counterfactual_alternate_input_clean"] = 999.0
        self.assertEqual(
            objective_key(profile, changed_controls),
            fitness.sort_key(),
        )

    def test_legacy_growth_health_and_failure_helpers_match_current_semantics(self):
        profile = legacy_objective_profile()
        before = Fitness(
            success=0.0,
            wrong_outputs=4,
            timeouts=3,
            response_latency=8,
            activity_cost=10,
            retention=0.2,
            noise_robustness=0.3,
            retention_evidence_count=1,
            noise_robustness_evidence_count=1,
        )
        after = Fitness(
            success=1.0,
            wrong_outputs=3,
            timeouts=2,
            response_latency=7,
            activity_cost=9,
            retention=0.4,
            noise_robustness=0.5,
            retention_evidence_count=1,
            noise_robustness_evidence_count=1,
        )
        self.assertEqual(
            objective_growth_flags(profile, before.to_dict(), after.to_dict()),
            0b1111111,
        )
        no_retention_evidence = dict(after.to_dict())
        no_retention_evidence["retention_evidence_count"] = 0
        self.assertEqual(
            objective_growth_flags(
                profile,
                before.to_dict(),
                no_retention_evidence,
            )
            & (1 << 5),
            0,
        )

        self.assertEqual(
            objective_short_health_flags(
                profile,
                active_cells=1,
                activity_cost=1,
            ),
            0b11,
        )
        self.assertEqual(
            objective_absolute_failure_reason(
                profile,
                (0,),
                response_history=(),
            ),
            "all_active_cells_gone",
        )
        self.assertEqual(
            objective_absolute_failure_reason(
                profile,
                (1,),
                response_history=(0, 0, 0, 0),
            ),
            "persistent_non_response",
        )

    def test_optimizer_routes_selection_growth_and_health_through_bound_profile(self):
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=0,
            base_config=PhysicsConfig(max_cells=8),
        )
        local = [slot for slot in optimizer.slots if slot.category == "masked_copy"]
        parent = local[0]

        with patch(
            "search.evolution.objective_key",
            wraps=objective_key,
        ) as key_route:
            optimizer._selection_records(local)
        self.assertGreater(key_route.call_count, 0)

        before = Fitness(
            success=0.0,
            retention=0.2,
            retention_evidence_count=1,
        )
        after = Fitness(
            success=1.0,
            retention=0.3,
            retention_evidence_count=1,
        )
        with patch(
            "search.evolution.objective_growth_flags",
            wraps=objective_growth_flags,
        ) as growth_route:
            flags = optimizer._objective_growth_flags(before, after)
        growth_route.assert_called_once()
        self.assertTrue(flags & 1)

        with patch(
            "search.evolution.objective_short_health_flags",
            wraps=objective_short_health_flags,
        ) as health_route:
            optimizer._observe_short_health(
                parent,
                SimpleNamespace(active_cells=1, activity_cost=1),
            )
        health_route.assert_called_once()


if __name__ == "__main__":
    unittest.main()
