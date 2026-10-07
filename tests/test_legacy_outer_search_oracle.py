import json
from pathlib import Path
import unittest

from core.physics import PhysicsConfig
from research.legacy_outer_search_oracle import (
    ACCEPTED_SOURCE_SHA,
    ORACLE_SCHEMA_VERSION,
    build_dynamic_oracle,
    build_static_oracle,
    canonical_digest,
)


ROOT = Path(__file__).resolve().parents[1]
FROZEN_V6 = (
    ROOT
    / "research"
    / "artifacts"
    / "legacy_outer_search_oracle_v1"
    / "initial_optimizer_v6.json"
)


class LegacyOuterSearchOracleTests(unittest.TestCase):
    def test_static_oracle_freezes_exact_legacy_initial_layout(self):
        oracle = build_static_oracle(
            source_sha=ACCEPTED_SOURCE_SHA,
            base_seed=0,
            base_config=PhysicsConfig(max_cells=8),
        )

        self.assertEqual(oracle["schema_version"], ORACLE_SCHEMA_VERSION)
        self.assertEqual(oracle["source_sha"], ACCEPTED_SOURCE_SHA)
        frozen_v6 = json.loads(FROZEN_V6.read_text(encoding="utf-8"))
        self.assertEqual(frozen_v6["format_version"], 6)
        self.assertEqual(
            frozen_v6["kind"],
            "UniverseGenomePhase5SteadyStateOptimizer",
        )
        self.assertEqual(oracle["optimizer_snapshot"]["format_version"], 7)
        self.assertEqual(oracle["optimizer_snapshot"]["kind"], "UniverseGenomePhase5SteadyStateOptimizer")
        self.assertEqual(len(oracle["slots"]), 128)
        self.assertEqual(
            oracle["category_counts"],
            {
                "masked_copy": 32,
                "masked_xor": 32,
                "rotate_copy": 32,
                "masked_and": 32,
            },
        )
        self.assertEqual(oracle["distinct_genomes_per_category"], 8)
        self.assertEqual(oracle["seeds_per_genome_per_category"], 4)
        self.assertEqual(oracle["distinct_seed_count"], 32)
        self.assertEqual(oracle["initial_scheduler"]["allocation_cursor"], 32)
        self.assertTrue(all(slot["state"]["generation"] == 0 for slot in oracle["slots"]))

    def test_dynamic_oracle_captures_short_and_growth_boundaries_for_all_slots(self):
        oracle = build_dynamic_oracle(
            source_sha=ACCEPTED_SOURCE_SHA,
            base_seed=0,
            base_config=PhysicsConfig(max_cells=8),
            terminal_generation=128,
        )

        self.assertEqual(set(oracle["checkpoints"]), {"16", "128"})
        self.assertEqual(len(oracle["checkpoints"]["16"]), 128)
        self.assertEqual(len(oracle["checkpoints"]["128"]), 128)
        self.assertTrue(
            all(record["state"]["generation"] == 16 for record in oracle["checkpoints"]["16"])
        )
        self.assertTrue(
            all(record["state"]["generation"] == 128 for record in oracle["checkpoints"]["128"])
        )
        self.assertTrue(
            all(len(record["growth_windows"]) == 1 for record in oracle["checkpoints"]["128"])
        )
        self.assertEqual(oracle["integrated_step"]["evaluated_slots"], 128)

    def test_canonical_digest_is_order_stable(self):
        first = {"b": [2, 1], "a": {"y": 2, "x": 1}}
        second = {"a": {"x": 1, "y": 2}, "b": [2, 1]}
        self.assertEqual(canonical_digest(first), canonical_digest(second))


if __name__ == "__main__":
    unittest.main()
