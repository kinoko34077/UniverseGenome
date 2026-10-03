from __future__ import annotations

import json
from pathlib import Path
import unittest

from core.runner import build_status, load_config
from search.evolution import CandidateSlot, SteadyStateOptimizer, seed_escalation
from search.fitness import Fitness, compare_fitness
from search.genome import UniverseGenome
from search.pruning import GrowthHistory, growth_flags, prune_candidates, protected_indices


ROOT = Path(__file__).resolve().parents[1]


class Phase5OptimizerTests(unittest.TestCase):
    def test_p5_001_genome_excludes_seed_and_mutates_one_binary_step(self):
        genome = UniverseGenome.default()
        mutated = genome.mutate("hp_decay", direction=1)
        self.assertNotIn("seed", genome.to_dict())
        changed = [key for key in genome.to_dict() if genome.to_dict()[key] != mutated.to_dict()[key]]
        self.assertEqual(changed, ["hp_decay"])
        self.assertEqual(mutated.hp_decay, 2)
        with self.assertRaises(ValueError):
            genome.mutate("seed", direction=1)

    def test_p5_002_fitness_is_lexicographic_and_not_complexity(self):
        winner = Fitness(success=1, wrong_outputs=9, timeouts=9, response_latency=99, activity_cost=999)
        loser = Fitness(success=0, wrong_outputs=0, timeouts=0, response_latency=0, activity_cost=0)
        self.assertEqual(compare_fitness(winner, loser), 1)
        self.assertEqual(compare_fitness(winner, winner), 0)
        self.assertLess(Fitness(1, 0, 0, 1, 1).sort_key(), Fitness(1, 0, 0, 2, 1).sort_key())

    def test_p5_003_growth_flags_and_history_are_bounded(self):
        before = Fitness(0, 4, 3, 8, 10)
        after = Fitness(1, 3, 2, 7, 9)
        flags = growth_flags(before, after)
        self.assertEqual(flags & 0b11111, 0b11111)
        history = GrowthHistory()
        for _ in range(5):
            history.push(flags)
        self.assertEqual(history.window_count, 4)
        self.assertLessEqual(history.value, 0xFFFFFFFF)
        self.assertEqual(history.score, 20)

    def test_p5_004_pruning_protects_absolute_top_eighth(self):
        records = [
            CandidateSlot(index=index, category="masked_copy", genome=UniverseGenome.default(), seed=index, fitness=Fitness(1 if index == 0 else 0, 0, 0, index, index), growth_windows=((4, 4, 4, 4) if index in (0, 4, 5, 6) else (0, 0, 0, 0)))
            for index in range(8)
        ]
        self.assertIn(0, protected_indices(records))
        self.assertNotIn(0, prune_candidates(records))
        self.assertIn(1, prune_candidates(records))

    def test_p5_005_seed_escalation_and_replacement_are_deterministic(self):
        self.assertEqual([seed_escalation(value) for value in (4, 8, 16, 32, 64)], [8, 16, 32, 32, 32])
        parent = CandidateSlot(index=0, category="masked_copy", genome=UniverseGenome.default(), seed=41, fitness=Fitness(0, 0, 0, 0, 0), growth_windows=(1,))
        optimizer = SteadyStateOptimizer()
        replacement = optimizer.replace_free_slot(free_index=12, parent=parent, direction=1)
        self.assertEqual(replacement.index, 12)
        self.assertEqual(replacement.category, parent.category)
        self.assertEqual(replacement.seed, 42)
        self.assertNotIn("seed", replacement.genome.to_dict())

    def test_p5_006_status_and_flags(self):
        raw = load_config(ROOT / "config" / "default.json")
        status = build_status(raw)
        self.assertTrue(status["phase5_optimizer_implemented"])
        self.assertEqual(status["next_phase"], "Phase 6+ capability ladder (handoff only)")
        self.assertTrue(raw["features"]["multi_universe_search"])
        self.assertTrue(raw["features"]["evolution"])
        self.assertFalse(raw["features"]["phase6_capabilities"])
        with (ROOT / "config" / "experiment_v0_1.json").open(encoding="utf-8") as handle:
            experiment = json.load(handle)
        self.assertEqual(experiment["learning_claim"], False)
        handoff = (ROOT / "docs" / "PHASE6_HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("No Phase 6+ capability has been implemented", handoff)


if __name__ == "__main__":
    unittest.main()
