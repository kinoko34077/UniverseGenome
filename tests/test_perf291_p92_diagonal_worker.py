"""P9.2: deterministic worker redistribution preserves original slot identity.

This is a test of a candidate source-only scheduling algorithm, not a study
of new scientific cohorts or a change to original D15 journal ownership.
"""
from __future__ import annotations

import unittest

from research.d15_spawn_workers_226 import SpawnEvaluator
from research.d15_sparse_recovery_213 import JournalIntegrityError


class _Pipe:
    def __init__(self) -> None:
        self.requests: list[tuple] = []

    def send(self, message: tuple) -> None:
        self.requests.append(message)


class BalancedNativeWorkerMapping(unittest.TestCase):
    @staticmethod
    def _make_pool(workers: int) -> SpawnEvaluator:
        pool = object.__new__(SpawnEvaluator)
        pool.workers = workers
        pool._processed = set()
        pool.pipes = [_Pipe() for _ in range(workers)]

        def read_messages(participants, *, expected, timeout_seconds):
            assert expected == "RESULT"
            assert timeout_seconds > 0
            return {
                worker: (
                    "RESULT",
                    [(i, {"index": i}) for i in pool.pipes[worker].requests[-1][1]],
                    1,
                )
                for worker in participants
            }

        pool._read_messages = read_messages
        return pool

    def test_complete_disjoint_ascending_and_diagonal_lane_mix(self):
        for workers in (2, 4):
            for first, count in ((0, 1), (0, 2), (4, 3), (16, 7),
                                 (16, 16), (32, 17), (64, 31), (96, 32)):
                with self.subTest(workers=workers, first=first, count=count):
                    pool = self._make_pool(workers)
                    original = tuple(range(first, first + count))
                    actual = pool.evaluate(original)
                    self.assertEqual(list(actual), sorted(original))
                    self.assertEqual({i: actual[i] for i in original},
                                     {i: {"index": i} for i in original})
                    assigned = [pipe.requests[0][1] if pipe.requests else ()
                                for pipe in pool.pipes]
                    self.assertEqual([len(a) for a in assigned],
                                     [len([k for k in range(count)
                                           if ((k // workers) + (k % workers))
                                           % workers == w])
                                      for w in range(workers)])
                    self.assertEqual(sorted(i for a in assigned for i in a),
                                     list(original))
                    for row in assigned:
                        self.assertEqual(row, tuple(sorted(row)))
                    if count == 16 and workers == 4:
                        self.assertEqual(
                            assigned[0],
                            (first, first + 7, first + 10, first + 13),
                        )
                    with self.assertRaises(JournalIntegrityError):
                        pool.evaluate(original)

    def test_original_bad_indices_fail_before_sending(self):
        pool = self._make_pool(4)
        for invalid in ((), (3, 1), (1, 1), (128,), (0, True),
                        tuple(range(33))):
            with self.subTest(invalid=invalid), self.assertRaises(JournalIntegrityError):
                pool.evaluate(invalid)
        self.assertFalse(any(p.requests for p in pool.pipes))


if __name__ == "__main__":
    unittest.main()
