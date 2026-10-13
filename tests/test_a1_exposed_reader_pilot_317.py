"""Frozen retrospective A1.2 R2 case provenance contract (source-only tests)."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from research import a1_exposed_reader_pilot_317 as pilot


class A1PilotProtocolTests(unittest.TestCase):
    def test_exact_historical_exposed_seed_roles_and_horizons(self):
        self.assertEqual(pilot.SEEDS, (544, 545))
        self.assertEqual(pilot.ROLES, {544: "positive", 545: "negative"})
        self.assertEqual(pilot.HORIZON, 1000)
        self.assertEqual(tuple(pilot.HORIZONS[1:]), (1, 10, 100, 250, 500, 1000))
        self.assertEqual(pilot.R2_FROZEN_DIGEST,
            "3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543")
        self.assertEqual(pilot.CAP_RSS_MIB, 1536.0)
        self.assertEqual(pilot.CAP_EVENTS, 200000)
        self.assertEqual(set(pilot.GOLDEN), set(pilot.SEEDS))
        self.assertEqual(pilot.GOLDEN[545]["b"], pilot.GOLDEN[545]["h"])
        self.assertNotEqual(pilot.GOLDEN[544]["b"], pilot.GOLDEN[544]["h"])
        for seed in pilot.SEEDS:
            for label in pilot.BRANCHES:
                self.assertEqual(set(pilot.GOLDEN[seed][label]),
                    {str(h) for h in pilot.HORIZONS[1:]})
                for digest in pilot.GOLDEN[seed][label].values():
                    self.assertEqual(len(digest), 64)
                    self.assertTrue(all(c in "0123456789abcdef" for c in digest))

    def test_source_identity_and_h0_original_digest_are_frozen(self):
        frozen = pilot.load_frozen()
        self.assertEqual(frozen["digest"], pilot.R2_FROZEN_DIGEST)
        self.assertIn(544, frozen["positive_seeds"])
        self.assertIn(545, frozen["negative_seeds"])
        self.assertEqual(frozen["h0_evidence"]["545"]["b_digest"],
                         frozen["h0_evidence"]["545"]["h_digest"])
        self.assertNotEqual(frozen["h0_evidence"]["544"]["b_digest"],
                            frozen["h0_evidence"]["544"]["h_digest"])

    def test_reject_unsupported_source_event_payload(self):
        self.assertEqual(
            pilot.source_event_digest([]),
            hashlib.sha256(b"[]").hexdigest(),
        )
        original = {"native_generation": 3, "source_slot": 1}
        self.assertEqual(
            pilot.source_event_digest([copy.deepcopy(original)]),
            hashlib.sha256(json.dumps([original], sort_keys=True,
                separators=(",", ":")).encode()).hexdigest(),
        )

    def test_fail_closed_budget_and_seed_reuse_boundary(self):
        with patch.object(pilot, "sampled_max_rss_mib", return_value=1537):
            with self.assertRaises(MemoryError):
                pilot.check_budget(pilot.time.perf_counter())
        with self.assertRaises(TimeoutError):
            pilot.check_budget(pilot.time.perf_counter() - pilot.CAP_SECONDS - 1)
        with self.assertRaises(ValueError):
            pilot.run_branch(1024, "b", {}, pilot.time.perf_counter())
        with self.assertRaises(ValueError):
            pilot.run_branch(544, "a", {}, pilot.time.perf_counter())
        with self.assertRaises(ValueError):
            pilot.report(source_sha="bad")


if __name__ == "__main__":
    unittest.main()
