from __future__ import annotations

import json
from pathlib import Path
import unittest

from core.physics import PhysicsConfig
from research.legacy_outer_search_oracle import canonical_digest, load_legacy_base_config
from search.genome import UNIVERSE_GENOME_FIELDS
from search.outer_search import (
    ActivationCondition,
    CandidateValues,
    ScalarDimension,
    SearchPlan,
    SearchRegistry,
    build_default_search_registry,
    build_legacy_initial_population,
    legacy_initial_scheduler,
    legacy_search_plan,
    resolve_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "research" / "artifacts" / "legacy_outer_search_oracle_v1" / "oracle.json"


class OuterSearchModelTests(unittest.TestCase):
    def test_legacy_plan_represents_current_search_without_broadening(self):
        registry = build_default_search_registry()
        plan = legacy_search_plan(base_seed=0)

        self.assertEqual(plan.population_size, 128)
        self.assertEqual(set(plan.search), set(UNIVERSE_GENOME_FIELDS))
        self.assertEqual(
            tuple(plan.rules["latent_operator"].variants),
            ("masked_copy", "masked_xor", "rotate_copy", "masked_and"),
        )
        self.assertEqual(
            {key: plan.fixed[key] for key in (
                "trace_write_cap",
                "trace_transfer_cap",
                "trace_discharge_cap",
                "trace_decay_rate",
                "trace_bonus_shift",
            )},
            {
                "trace_write_cap": 0,
                "trace_transfer_cap": 0,
                "trace_discharge_cap": 0,
                "trace_decay_rate": 0,
                "trace_bonus_shift": 8,
            },
        )
        self.assertNotIn("seed", registry.scalar_dimensions)
        self.assertNotIn("teacher_repetitions", registry.scalar_dimensions)
        self.assertEqual(plan.strata[0].group_by, ("latent_operator",))
        self.assertEqual(plan.strata[0].selection_scope, "within")
        self.assertEqual(plan.objective_profile_id, "phase5_legacy")
        self.assertEqual(plan.objective_profile_version, 1)

        plan.validate(registry)

        static_oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))["static"]
        self.assertEqual(legacy_initial_scheduler(plan), static_oracle["initial_scheduler"])

    def test_conditional_inactive_dimension_is_canonical_and_not_identity_bearing(self):
        registry = SearchRegistry(
            scalar_dimensions={
                "mode": ScalarDimension(
                    dimension_id="mode",
                    physics_field="hp_decay",
                    value_type="int",
                    default=0,
                    allowed_values=(0, 1),
                    strategy_ids=("fixed",),
                ),
                "conditional": ScalarDimension(
                    dimension_id="conditional",
                    physics_field="bond_gain",
                    value_type="int",
                    default=4,
                    allowed_values=(4, 8),
                    strategy_ids=("adjacent_binary",),
                    activation=ActivationCondition(
                        dimension_id="mode",
                        allowed_values=(1,),
                    ),
                ),
            },
            rule_dimensions={},
        )
        plan = SearchPlan(
            schema_version=1,
            plan_id="test-conditional",
            plan_version=1,
            population_size=1,
            fixed={"mode": 0},
            search={"conditional": ("adjacent_binary", (4, 8))},
        )
        plan.validate(registry)

        first = resolve_candidate(
            plan,
            registry,
            CandidateValues(scalars={"conditional": 4}, rules={}),
        )
        second = resolve_candidate(
            plan,
            registry,
            CandidateValues(scalars={"conditional": 8}, rules={}),
        )

        self.assertEqual(first.universe_spec.scalar_values["conditional"], 4)
        self.assertEqual(second.universe_spec.scalar_values["conditional"], 4)
        self.assertEqual(first.candidate_identity, second.candidate_identity)
        self.assertEqual(first.active_dimensions, ("mode",))
        self.assertNotIn("candidate_identity", first.universe_spec.to_dict())
        self.assertNotIn("active_dimensions", first.universe_spec.to_dict())

    def test_plan_validation_rejects_conditional_dependency_cycle(self):
        registry = SearchRegistry(
            scalar_dimensions={
                "a": ScalarDimension(
                    dimension_id="a",
                    physics_field="hp_decay",
                    value_type="int",
                    default=0,
                    allowed_values=(0, 1),
                    strategy_ids=("fixed",),
                    activation=ActivationCondition("b", (1,)),
                ),
                "b": ScalarDimension(
                    dimension_id="b",
                    physics_field="bond_gain",
                    value_type="int",
                    default=0,
                    allowed_values=(0, 1),
                    strategy_ids=("fixed",),
                    activation=ActivationCondition("a", (1,)),
                ),
            },
            rule_dimensions={},
        )
        plan = SearchPlan(
            schema_version=1,
            plan_id="cycle",
            plan_version=1,
            population_size=1,
            fixed={"a": 0, "b": 0},
        )

        with self.assertRaisesRegex(ValueError, "cycle"):
            plan.validate(registry)

    def test_plan_validation_rejects_unknown_seed_protocol_and_rule_ids(self):
        registry = build_default_search_registry()

        with self.assertRaisesRegex(ValueError, "unknown scalar dimension"):
            SearchPlan(
                schema_version=1,
                plan_id="unknown",
                plan_version=1,
                population_size=1,
                search={"not_registered": ("adjacent_binary", (1, 2))},
            ).validate(registry)

        with self.assertRaisesRegex(ValueError, "unknown scalar dimension"):
            SearchPlan(
                schema_version=1,
                plan_id="seed",
                plan_version=1,
                population_size=1,
                search={"seed": ("adjacent_binary", (1, 2))},
            ).validate(registry)

        with self.assertRaisesRegex(ValueError, "unknown scalar dimension"):
            SearchPlan(
                schema_version=1,
                plan_id="protocol",
                plan_version=1,
                population_size=1,
                search={"teacher_repetitions": ("adjacent_binary", (1, 2))},
            ).validate(registry)

        bad_rule = legacy_search_plan(base_seed=0).with_rule_variants(
            "latent_operator",
            ("masked_copy", "does_not_exist"),
        )
        with self.assertRaisesRegex(ValueError, "unknown rule variant"):
            bad_rule.validate(registry)

    def test_legacy_static_population_matches_all_128_frozen_oracle_slots(self):
        oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))["static"]["slots"]
        base = load_legacy_base_config()
        actual = build_legacy_initial_population(
            base_seed=0,
            base_config=base,
            registry=build_default_search_registry(),
            plan=legacy_search_plan(base_seed=0),
        )

        self.assertEqual(len(actual), 128)
        self.assertEqual(len(oracle), 128)

        identity_by_genome_and_category: dict[tuple[str, str], str] = {}
        seeds_by_identity: dict[str, set[int]] = {}

        for slot, expected in zip(actual, oracle, strict=True):
            self.assertEqual(slot.index, expected["index"])
            self.assertEqual(slot.rule_values["latent_operator"], expected["category"])
            self.assertEqual(slot.seed, expected["seed"])
            self.assertEqual(slot.legacy_genome_values, expected["genome"])
            self.assertEqual(
                slot.resolved_candidate.universe_spec.to_physics_config(base).to_dict(),
                expected["state"]["config"],
            )
            self.assertEqual(slot.state.generation, 0)
            self.assertEqual(
                canonical_digest(slot.state.to_snapshot()),
                expected["state"]["state_digest"],
            )

            key = (expected["category"], json.dumps(expected["genome"], sort_keys=True))
            previous = identity_by_genome_and_category.setdefault(
                key,
                slot.resolved_candidate.candidate_identity,
            )
            self.assertEqual(previous, slot.resolved_candidate.candidate_identity)
            seeds_by_identity.setdefault(slot.resolved_candidate.candidate_identity, set()).add(slot.seed)

        self.assertEqual(len(identity_by_genome_and_category), 32)
        self.assertTrue(all(len(seeds) == 4 for seeds in seeds_by_identity.values()))


if __name__ == "__main__":
    unittest.main()
