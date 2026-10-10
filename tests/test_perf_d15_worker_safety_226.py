"""#226 P0 RED/GREEN test-only child-process/one-writer safety observations."""
import os
import sys
import unittest
from unittest.mock import patch

from benchmarks.perf_d15_worker_safety_226 import (
    conservative_admit, witness,
)


@unittest.skipUnless(sys.platform == "linux", "Linux POSIX lock required")
class P0LockInheritanceTests(unittest.TestCase):
    def test_fork_after_lock_holds_parent_flock_even_after_parent_sigkill(self):
        r = witness("fork")
        self.assertTrue(r["parent_killed"])
        self.assertTrue(r["child_alive_during_test"])
        self.assertFalse(r["new_writer_acquired_while_child_alive"])

    def test_spawn_worker_not_inherit_parent_writer_flock_after_sigkill(self):
        r = witness("spawn")
        self.assertTrue(r["parent_killed"])
        self.assertTrue(r["child_alive_during_test"])
        self.assertTrue(r["new_writer_acquired_while_child_alive"])


class AggregateResourceAdmissionTests(unittest.TestCase):
    @patch("benchmarks.perf_d15_worker_safety_226.cgroup_v2_memory")
    @patch("benchmarks.perf_d15_worker_safety_226._rss")
    def test_aggregate_rss_including_workers_rejects_oversubscription(
        self, rss, cgroup
    ):
        rss.side_effect = lambda pid: {
            10: 400 * 1024 * 1024,
            11: 700 * 1024 * 1024,
            12: 400 * 1024 * 1024,
        }[pid]
        cgroup.return_value = {
            "current_bytes": 1800 * 1024 * 1024,
            "max_bytes": 4000 * 1024 * 1024,
            "remaining_bytes": 2200 * 1024 * 1024,
        }
        with self.assertRaises(MemoryError):
            conservative_admit(10, [11, 12], limit_mib=1536)
        with self.assertRaises(ValueError):
            conservative_admit(10, [11, 11])
        result = conservative_admit(10, [11], limit_mib=1536)
        self.assertEqual(result["conservative_rss_bytes"], 1100*1024*1024)

    @patch("benchmarks.perf_d15_worker_safety_226.cgroup_v2_memory")
    @patch("benchmarks.perf_d15_worker_safety_226._rss")
    def test_fails_closed_missing_or_exhausted_cgroup_headroom(self, rss, cgroup):
        rss.return_value = 32 * 1024 * 1024
        cgroup.return_value = {
            "current_bytes": None, "max_bytes": None,
            "remaining_bytes": None,
        }
        with self.assertRaises(RuntimeError):
            conservative_admit(10, [11])
        cgroup.return_value = {
            "current_bytes": 100, "max_bytes": 100,
            "remaining_bytes": 0,
        }
        with self.assertRaises(MemoryError):
            conservative_admit(10, [11])


if __name__ == "__main__":
    unittest.main()
