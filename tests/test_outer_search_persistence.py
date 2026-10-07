from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from search.evolution import SteadyStateOptimizer
from search.genome import UniverseGenome
from search.outer_search import (
    build_default_search_registry,
    legacy_candidate_values,
    legacy_mutation_plan_for_base_config,
    legacy_objective_profile,
    resolve_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
FROZEN_V6 = (
    ROOT
    / "research"
    / "artifacts"
    / "legacy_outer_search_oracle_v1"
    / "initial_optimizer_v6.json"
)


def load_frozen_v6() -> dict:
    payload = json.loads(FROZEN_V6.read_text(encoding="utf-8"))
    if payload.get("format_version") != 6:
        raise AssertionError("frozen optimizer artifact is not v6")
    return payload


def legacy_fields(payload: dict) -> dict:
    return {
        key: payload[key]
        for key in (
            "kind",
            "generation",
            "base_config",
            "experiment",
            "scheduler",
            "prune_history",
            "slots",
        )
    }


class OuterSearchPersistenceTests(unittest.TestCase):
    def test_frozen_v6_migrates_to_v7_without_changing_legacy_authoritative_payload(self):
        v6 = load_frozen_v6()

        restored = SteadyStateOptimizer.from_snapshot(v6)
        v7 = restored.to_snapshot()

        self.assertEqual(v7["format_version"], 7)
        self.assertEqual(legacy_fields(v7), legacy_fields(v6))
        self.assertTrue(
            all(record["state"]["format_version"] == 2 for record in v7["slots"])
        )

        outer = v7["outer_search"]
        self.assertEqual(outer["schema_version"], 1)

        registry = build_default_search_registry()
        plan = legacy_mutation_plan_for_base_config(restored.base_config, base_seed=0)
        profile = legacy_objective_profile()

        self.assertEqual(outer["search_plan"]["payload"], plan.to_dict())
        self.assertEqual(outer["search_plan"]["digest"], plan.digest)
        self.assertEqual(outer["registry"]["schema_version"], registry.schema_version)
        self.assertEqual(outer["registry"]["digest"], registry.digest)
        self.assertEqual(
            outer["objective_profile"],
            {"id": profile.profile_id, "version": profile.version},
        )
        self.assertEqual(len(outer["comparison_strata"]), 4)
        self.assertEqual(len(outer["candidates"]), 128)

        for slot_payload, candidate_payload in zip(
            v7["slots"],
            outer["candidates"],
            strict=True,
        ):
            candidate = legacy_candidate_values(
                UniverseGenome.from_dict(dict(slot_payload["genome"])),
                str(slot_payload["category"]),
            )
            resolved = resolve_candidate(plan, registry, candidate)
            self.assertEqual(candidate_payload["slot_index"], slot_payload["index"])
            self.assertEqual(
                candidate_payload["candidate_identity"],
                resolved.candidate_identity,
            )
            self.assertEqual(
                candidate_payload["candidate_values"],
                {
                    "scalars": dict(candidate.scalars),
                    "rules": dict(candidate.rules),
                },
            )
            self.assertEqual(candidate_payload["evidence_seed"], slot_payload["seed"])
            self.assertEqual(candidate_payload["cohort_role"], "search")

        provenance = outer["provenance"]
        self.assertEqual(provenance["migration_source_format"], 6)
        self.assertEqual(provenance["search_plan_digest"], plan.digest)
        self.assertEqual(provenance["registry_digest"], registry.digest)
        self.assertEqual(provenance["objective_profile_id"], profile.profile_id)
        self.assertEqual(provenance["objective_profile_version"], profile.version)
        self.assertEqual(provenance["search_cohort_policy"], "legacy_optimizer_evidence")
        self.assertEqual(provenance["validation_cohort_policy"], "none")

    def test_v7_roundtrip_is_exact(self):
        migrated = SteadyStateOptimizer.from_snapshot(load_frozen_v6())
        v7 = migrated.to_snapshot()

        restored = SteadyStateOptimizer.from_snapshot(v7)

        self.assertEqual(restored.to_snapshot(), v7)

    def test_native_legacy_v7_keeps_default_slow_trace_fixed_and_seed_out_of_candidate(self):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=37)
        payload = optimizer.to_snapshot()

        self.assertEqual(payload["format_version"], 7)
        plan = payload["outer_search"]["search_plan"]["payload"]
        self.assertEqual(
            plan["fixed"],
            {
                "trace_write_cap": 0,
                "trace_transfer_cap": 0,
                "trace_discharge_cap": 0,
                "trace_decay_rate": 0,
                "trace_bonus_shift": 8,
            },
        )
        self.assertEqual(plan["scheduler"]["base_seed"], 37)
        self.assertNotIn("seed", plan["search"])
        self.assertTrue(
            all(
                "seed" not in record["candidate_values"]["scalars"]
                and "seed" not in record["candidate_values"]["rules"]
                for record in payload["outer_search"]["candidates"]
            )
        )

    def test_v7_rejects_inconsistent_generalized_metadata_fail_closed(self):
        payload = SteadyStateOptimizer.from_defaults(base_seed=0).to_snapshot()

        cases = []

        bad = dict(payload)
        outer = copy.deepcopy(payload["outer_search"])
        outer["search_plan"]["digest"] = "0" * 64
        bad["outer_search"] = outer
        cases.append(("search plan digest", bad))

        bad = dict(payload)
        outer = copy.deepcopy(payload["outer_search"])
        outer["registry"]["digest"] = "0" * 64
        bad["outer_search"] = outer
        cases.append(("registry digest", bad))

        bad = dict(payload)
        outer = copy.deepcopy(payload["outer_search"])
        outer["objective_profile"]["id"] = "does_not_exist"
        bad["outer_search"] = outer
        cases.append(("objective profile", bad))

        bad = dict(payload)
        outer = copy.deepcopy(payload["outer_search"])
        outer["candidates"][0]["candidate_identity"] = "0" * 64
        bad["outer_search"] = outer
        cases.append(("candidate identity", bad))

        bad = dict(payload)
        outer = copy.deepcopy(payload["outer_search"])
        outer["candidates"][0]["candidate_values"]["scalars"]["seed"] = 123
        bad["outer_search"] = outer
        cases.append(("seed candidate dimension", bad))

        bad = dict(payload)
        outer = copy.deepcopy(payload["outer_search"])
        outer.pop("provenance")
        bad["outer_search"] = outer
        cases.append(("missing provenance", bad))

        for label, malformed in cases:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    SteadyStateOptimizer.from_snapshot(malformed)

    def test_migrated_v6_snapshot_restore_continuation_matches(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        original = SteadyStateOptimizer.from_defaults(
            base_seed=0,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        native_v7 = original.to_snapshot()
        v6 = {
            key: value
            for key, value in native_v7.items()
            if key != "outer_search"
        }
        v6["format_version"] = 6

        migrated = SteadyStateOptimizer.from_snapshot(v6)
        restored = SteadyStateOptimizer.from_snapshot(migrated.to_snapshot())

        first = migrated.step()
        second = restored.step()

        deterministic_first = {
            key: value
            for key, value in first.items()
            if key != "generations_per_second"
        }
        deterministic_second = {
            key: value
            for key, value in second.items()
            if key != "generations_per_second"
        }
        self.assertEqual(deterministic_first, deterministic_second)
        self.assertEqual(migrated.to_snapshot(), restored.to_snapshot())


if __name__ == "__main__":
    unittest.main()
