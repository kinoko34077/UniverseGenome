"""P6.9 verify zero-ACTIVE packed-scan fastpath preserves all old return values."""
import unittest

from core.state import Lifecycle, UniverseState
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

GOLDEN = "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"


def old_active_slots(values):
    found = []
    start = 0
    while True:
        try:
            slot = values.index(int(Lifecycle.ACTIVE), start)
        except ValueError:
            return found
        found.append(slot)
        start = slot + 1


class P69EmptyActiveNativeParity(unittest.TestCase):
    def test_original_mutable_lifecycle_ascending_order_and_exact_snapshots(self):
        for capacity in (1, 2, 7, 32, 1024):
            patterns = [
                [0] * capacity,
                [2] * capacity,
                [1] * capacity,
                [i % 3 for i in range(capacity)],
                [1 if i == capacity - 1 else 2 for i in range(capacity)],
                [1 if i == 0 else 0 for i in range(capacity)],
            ]
            for lifecycle in patterns:
                state = UniverseState(seed=4, max_cells=capacity)
                state.lifecycle[:] = lifecycle
                before = state.to_snapshot()
                self.assertEqual(state.active_slots(), old_active_slots(lifecycle))
                self.assertEqual(state.to_snapshot(), before)
                if lifecycle and lifecycle[0] != 1:
                    state.lifecycle[0] = 1
                    self.assertEqual(state.active_slots(), old_active_slots(state.lifecycle))
                    state.lifecycle[0] = 2
                    self.assertEqual(state.active_slots(), old_active_slots(state.lifecycle))

    def test_unusual_legacy_list_values_continue_original_index_semantics(self):
        for unusual in (-1, 256, 1.5, "legacy", None):
            state = UniverseState(seed=7, max_cells=8)
            state.lifecycle = [0, 2, unusual, 0, 2, 0, 2, 0]
            self.assertEqual(state.active_slots(), old_active_slots(state.lifecycle))
            state.lifecycle[6] = 1
            self.assertEqual(state.active_slots(), old_active_slots(state.lifecycle))

    def test_unchanged_real_native_default1024_seed0_full_v7(self):
        opt = SteadyStateOptimizer.from_defaults(base_seed=0)
        opt._evaluate_slot(opt.slots[0])
        self.assertEqual(digest(opt.to_snapshot()), GOLDEN)


if __name__ == "__main__":
    unittest.main()
