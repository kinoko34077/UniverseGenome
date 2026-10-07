from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from search.evolution import SteadyStateOptimizer
from search.fitness import Fitness
from search.outer_search import (
    SelectionRecord,
    promising_group_keys,
    protected_selection_indices,
    prune_selection_indices,
    select_parent_index,
    select_promising_parent_index,
    select_prune_target_index,
)

ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "research" / "artifacts" / "legacy_outer_search_oracle_v1" / "oracle.json"


def oracle_selection_records(items: list[dict[str, object]]) -> tuple[SelectionRecord, ...]:
    groups: dict[str, list[dict[str, object]]] = {}
    for item in items:
        groups.setdefault(str(item["genome_key"]), []).append(item)
    aggregates = {
        genome_key: SteadyStateOptimizer._aggregate_fitness(
            [
                SimpleNamespace(fitness=Fitness.from_dict(dict(record["fitness"])))
                for record in group
            ]
        )
        for genome_key, group in groups.items()
    }
    return tuple(
        SelectionRecord(
            index=int(item["index"]),
            group_key=(str(item["category"]), str(item["genome_key"])),
            objective_key=aggregates[str(item["genome_key"])].sort_key(),
            evidence_count=len(groups[str(item["genome_key"])]),
            candidate_tie_key=str(item["genome_key"]),
            growth_windows=tuple(int(value) for value in item["growth_windows"]),
            absolute_failure=bool(item["absolute_failure"]),
            evidence_mature=bool(item["evidence_mature"]),
        )
        for item in items
    )



def record(
    index: int,
    *,
    group: str,
    success: float,
    evidence_count: int = 4,
    growth_windows: tuple[int, ...] = (),
    absolute_failure: bool = False,
) -> SelectionRecord:
    return SelectionRecord(
        index=index,
        group_key=group,
        objective_key=Fitness(success=success).sort_key(),
        evidence_count=evidence_count,
        candidate_tie_key=group,
        growth_windows=growth_windows,
        absolute_failure=absolute_failure,
        evidence_mature=evidence_count >= 4,
    )


class OuterSearchSelectionTests(unittest.TestCase):
    def test_generic_parent_and_protection_are_within_stratum_and_evidence_gated(self):
        records = (
            record(0, group="a", success=0.9),
            record(1, group="a", success=0.9),
            record(2, group="a", success=0.9),
            record(3, group="a", success=0.9),
            record(4, group="b", success=0.8),
            record(5, group="b", success=0.8),
            record(6, group="b", success=0.8),
            record(7, group="b", success=0.8),
            record(8, group="child", success=1.0, evidence_count=1),
        )

        self.assertEqual(select_parent_index(records, excluded_index=0), 1)
        self.assertNotIn(8, protected_selection_indices(records))
        self.assertIn(0, protected_selection_indices(records))

    def test_generic_promising_parent_preserves_tier_and_evidence_count_order(self):
        records = tuple(
            record(index, group="a", success=0.8, evidence_count=4)
            for index in range(4)
        ) + tuple(
            record(10 + index, group="b", success=0.9, evidence_count=7)
            for index in range(7)
        ) + tuple(
            record(20 + index, group="c", success=0.2, evidence_count=4)
            for index in range(4)
        ) + tuple(
            record(30 + index, group="d", success=0.1, evidence_count=4)
            for index in range(4)
        )

        self.assertEqual(
            promising_group_keys(
                records,
                policy_id="tiered_category_rank",
                minimum_evidence=4,
            ),
            {"a", "b"},
        )
        self.assertEqual(
            select_promising_parent_index(
                records,
                policy_id="tiered_category_rank",
                minimum_evidence=4,
            ),
            0,
        )

    def test_generic_pruning_and_worst_target_match_legacy_growth_rule(self):
        records = (
            record(0, group="a", success=1.0, growth_windows=(15, 15, 15, 15)),
            record(1, group="b", success=0.4, growth_windows=(0, 0, 0, 0)),
            record(2, group="c", success=0.3, growth_windows=(15, 15, 15, 15)),
            record(3, group="d", success=0.2, growth_windows=(15, 15, 15, 15)),
            record(4, group="e", success=0.2, growth_windows=(15, 15, 15, 15)),
            record(5, group="f", success=0.2, growth_windows=(15, 15, 15, 15)),
            record(6, group="g", success=0.2, growth_windows=(8, 8, 8, 8)),
            record(7, group="h", success=0.2, growth_windows=(8, 8, 8, 8)),
            record(8, group="i", success=0.0, absolute_failure=True),
            record(
                9,
                group="immature",
                success=0.0,
                evidence_count=1,
                growth_windows=(0, 0, 0, 0),
            ),
        )
        protected = {0}
        pruned = prune_selection_indices(records, protected=protected)

        self.assertIn(1, pruned)
        self.assertIn(8, pruned)
        self.assertNotIn(0, pruned)
        self.assertNotIn(9, pruned)
        self.assertEqual(select_prune_target_index(records, pruned), 8)

    def test_frozen_generation_1024_selection_matches_phase_a_replacement_evidence(self):
        oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
        checkpoint = oracle["dynamic"]["checkpoints"]["1024"]
        expected_replacements = {
            item["category"]: item
            for item in oracle["dynamic"]["integrated_step"]["replacements"]
        }

        pruned_total = 0
        for category, expected in expected_replacements.items():
            local = [item for item in checkpoint if item["category"] == category]
            records = oracle_selection_records(local)
            protected = protected_selection_indices(records)
            pruning_records = tuple(
                record
                for record in records
                if record.evidence_mature or record.absolute_failure
            )
            pruned = prune_selection_indices(pruning_records, protected=protected)
            pruned_total += len(pruned)
            target_index = select_prune_target_index(records, pruned)
            self.assertEqual(target_index, expected["index"])

            target_group = next(
                record.group_key for record in records if record.index == target_index
            )
            source_items = [item for item in local if int(item["index"]) != target_index]
            source_records = oracle_selection_records(source_items)
            parent_index = select_promising_parent_index(
                source_records,
                policy_id="tiered_category_rank",
                minimum_evidence=4,
                excluded_group=target_group,
            )
            self.assertEqual(parent_index, expected["parent_index"])

        self.assertEqual(pruned_total, oracle["dynamic"]["integrated_step"]["pruned_count"])

    def test_legacy_promising_policy_boundary_order_is_preserved(self):
        disabled = SteadyStateOptimizer.from_defaults(
            base_seed=0,
            promising_policy=None,
        )
        mixed = [disabled.slots[0], disabled.slots[32]]
        self.assertEqual(disabled._promising_group_keys(mixed), set())

        invalid = SteadyStateOptimizer.from_defaults(base_seed=0)
        invalid.scheduler["promising_policy"] = "unsupported-policy"
        with self.assertRaises(ValueError):
            invalid._promising_group_keys([])

    def test_integrated_step_routes_protection_pruning_and_target_through_generic_policy(self):
        protocol = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=202,
            base_config=PhysicsConfig(max_cells=8),
            experiment=protocol,
        )
        optimizer.slots[0].absolute_failure = True
        optimizer.slots[0].absolute_failure_reason = "all_active_cells_gone"

        with (
            patch(
                "search.evolution.protected_selection_indices",
                wraps=protected_selection_indices,
            ) as protected,
            patch(
                "search.evolution.prune_selection_indices",
                wraps=prune_selection_indices,
            ) as prune,
            patch(
                "search.evolution.select_prune_target_index",
                wraps=select_prune_target_index,
            ) as target,
        ):
            summary = optimizer.step()

        self.assertGreaterEqual(protected.call_count, 4)
        self.assertGreaterEqual(prune.call_count, 4)
        target.assert_called()
        self.assertEqual(summary["replacement_count"], 1)
        self.assertEqual(optimizer.prune_history[0]["index"], 0)


if __name__ == "__main__":
    unittest.main()
