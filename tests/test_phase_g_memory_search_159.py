import unittest
from dataclasses import replace

from core.physics import PhysicsConfig
from search.evolution import SteadyStateOptimizer
from search.outer_search import (
    CandidateValues,
    build_default_search_registry,
    legacy_mutation_plan_for_base_config,
)
from research.phase_g_memory_search_159 import (
    DECAY_DOMAIN,
    HELDOUT_POOL,
    OLD_140_PRIMARY_SEEDS,
    SEARCH_POOL,
    build_phase_g_registry,
    decay_candidate,
    phase_g_search_plan,
    qualify_case_h0,
    select_qualification_cohort,
)


class PhaseGMemorySearch159Tests(unittest.TestCase):
    def test_production_optimizer_still_rejects_nonlegacy_plan(self) -> None:
        base = PhysicsConfig()
        registry = build_default_search_registry()
        legacy = legacy_mutation_plan_for_base_config(base)
        SteadyStateOptimizer(base_config=base, search_plan=legacy, search_registry=registry)

        nonlegacy_on_production_registry = replace(legacy, plan_id="phase_g_probe")
        with self.assertRaisesRegex(ValueError, "legacy-equivalent SearchPlan"):
            SteadyStateOptimizer(
                base_config=base,
                search_plan=nonlegacy_on_production_registry,
                search_registry=registry,
            )

        with self.assertRaisesRegex(ValueError, "current registered search surface"):
            SteadyStateOptimizer(
                base_config=base,
                search_plan=phase_g_search_plan(),
                search_registry=build_phase_g_registry(),
            )

    def test_phase_g_plan_is_decay_only_and_research_bounded(self) -> None:
        plan = phase_g_search_plan()
        registry = build_phase_g_registry()
        plan.validate(registry)

        self.assertEqual(tuple(plan.search), ("trace_decay_rate",))
        self.assertEqual(tuple(plan.search["trace_decay_rate"].domain), DECAY_DOMAIN)
        self.assertEqual(
            {
                "trace_write_cap": plan.fixed["trace_write_cap"],
                "trace_transfer_cap": plan.fixed["trace_transfer_cap"],
                "trace_discharge_cap": plan.fixed["trace_discharge_cap"],
                "trace_bonus_shift": plan.fixed["trace_bonus_shift"],
            },
            {
                "trace_write_cap": 32,
                "trace_transfer_cap": 8,
                "trace_discharge_cap": 16,
                "trace_bonus_shift": 5,
            },
        )
        self.assertNotIn("trace_decay_rate", plan.fixed)
        self.assertEqual(tuple(plan.rules["latent_operator"].variants), ("masked_copy",))
        self.assertEqual(plan.validation_cohort_policy, "phase_g_heldout_qualified_h0_v1")

    def test_decay_candidate_resolves_exact_reference_physics(self) -> None:
        plan = phase_g_search_plan()
        registry = build_phase_g_registry()
        resolved = plan
        candidate = decay_candidate(256)
        from search.outer_search import resolve_candidate

        result = resolve_candidate(plan, registry, candidate)
        config = result.universe_spec.to_physics_config(PhysicsConfig())
        self.assertEqual(config.initial_density, 32)
        self.assertEqual(config.trace_write_cap, 32)
        self.assertEqual(config.trace_transfer_cap, 8)
        self.assertEqual(config.trace_discharge_cap, 16)
        self.assertEqual(config.trace_decay_rate, 256)
        self.assertEqual(config.trace_bonus_shift, 5)
        self.assertEqual(config.latent_operator, "masked_copy")

    def test_seed_pools_are_disjoint_and_exclude_historical_primary(self) -> None:
        self.assertTrue(set(SEARCH_POOL).isdisjoint(HELDOUT_POOL))
        self.assertTrue(set(SEARCH_POOL).isdisjoint(OLD_140_PRIMARY_SEEDS))
        self.assertTrue(set(HELDOUT_POOL).isdisjoint(OLD_140_PRIMARY_SEEDS))

    def test_qualification_selector_is_deterministic(self) -> None:
        cases = [
            {"seed": 40, "b_vs_h_distinct": True},
            {"seed": 33, "b_vs_h_distinct": False},
            {"seed": 32, "b_vs_h_distinct": True},
            {"seed": 35, "b_vs_h_distinct": False},
            {"seed": 34, "b_vs_h_distinct": True},
        ]
        selected = select_qualification_cohort(cases, positive_count=2, negative_count=2)
        self.assertEqual(selected["positive"], [32, 34])
        self.assertEqual(selected["negative"], [33, 35])

    def test_h0_qualification_has_no_post_teacher_horizon(self) -> None:
        case = qualify_case_h0(seed=32)
        self.assertEqual(case["max_horizon"], 0)
        self.assertIn("b_vs_h_distinct", case)
        self.assertIn("control_clean", case)
        self.assertNotIn("h100", case)
        self.assertNotIn("h1000", case)


if __name__ == "__main__":
    unittest.main()
