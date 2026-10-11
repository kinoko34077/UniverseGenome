"""D16 #217 dormant transfer/clock tests; SYNTHETIC optimizer only.

These tests never run original seed16384 or any complete 37-round study.
Authentic D15 journal/selected-state source evidence belongs to PR#246/#249.
"""
from dataclasses import replace
import unittest

from research.d16_twojob_run_control_217 import (
    ABSOLUTE_GLOBAL_SECONDS, D16BoundaryError, GlobalClock,
    accept_transfer, classify_stop, make_transfer, native_state_checked,
    plan_for_round,
)
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

SOURCE = "a" * 40
START_MS = 1780000000000


def synthetic_state(*, seed=0, generation=1):
    opt = SteadyStateOptimizer.from_defaults(base_seed=seed)
    opt.generation = generation  # metadata fixture, NOT completed native selection
    return opt.to_snapshot()


class D16ProspectiveTransferTests(unittest.TestCase):
    def test_original_two_job_partition_not_negotiable(self):
        for n in (1, 10, 20):
            self.assertEqual(plan_for_round(n), 1)
        for n in (21, 37, 40):
            self.assertEqual(plan_for_round(n), 2)
        for n in (0, 41, True, 1.0):
            with self.subTest(n=n), self.assertRaises(D16BoundaryError):
                plan_for_round(n)

    def test_complete_frozen_four_window_stop_only(self):
        mature = {c: True for c in "ABCD"}
        immature = {**mature, "C": False}
        self.assertEqual(classify_stop(36, mature_categories=mature,
                                       actual_replacements=2), "CONTINUE")
        self.assertEqual(classify_stop(37, mature_categories=immature,
                                       actual_replacements=2), "CONTINUE")
        self.assertEqual(classify_stop(37, mature_categories=mature,
                                       actual_replacements=0), "CONTINUE")
        self.assertEqual(classify_stop(37, mature_categories=mature,
                                       actual_replacements=1), "OBSERVED_FINAL")
        self.assertEqual(classify_stop(40, mature_categories=immature,
                                       actual_replacements=0), "NOT_OBSERVED_FINAL")
        with self.assertRaises(D16BoundaryError):
            classify_stop(38, mature_categories={"A": True}, actual_replacements=1)

    def test_global_elapsed_crosses_job_queue_and_cannot_reset(self):
        c = GlobalClock(START_MS, prior_elapsed_ms=450000)
        self.assertEqual(c.check(now_unix_ms=START_MS + 650000,
                                 local_elapsed_ms=30000), 650000)
        for now, local in (
            (START_MS + 449999, 1),
            (START_MS + ABSOLUTE_GLOBAL_SECONDS * 1000 + 1, 1),
            (START_MS + 800000, 1080001),
        ):
            with self.subTest(now=now), self.assertRaises(D16BoundaryError):
                c.check(now_unix_ms=now, local_elapsed_ms=local)

    def test_synthetic_seed0_completed_state_checksum_and_source_handoff(self):
        # A synthetic round1 state verifies structure, not an actual evolution.
        snapshot = synthetic_state()
        selected = native_state_checked(snapshot, expected_seed=0,
                                         expected_generation=1)
        c = GlobalClock(START_MS)
        m = make_transfer(source_sha=SOURCE, selected_snapshot=snapshot,
                          seed=0, selected_round=1, clock=c,
                          now_unix_ms=START_MS + 62000,
                          local_elapsed_ms=62000,
                          observer_selected_digest=selected,
                          ledger_sha="b"*64)
        restored = accept_transfer(
            manifest=m, snapshot=snapshot, actual_source=SOURCE,
            expected_seed=0, expected_selected_round=1,
            now_unix_ms=START_MS + 68000,
        )
        self.assertEqual(restored.prior_elapsed_ms, 62000)
        self.assertEqual(restored.check(now_unix_ms=START_MS+68000,
                                        local_elapsed_ms=0), 68000)

    def test_cross_job_tamper_source_seed_snapshot_clock_rejected(self):
        snap = synthetic_state()
        m = make_transfer(source_sha=SOURCE, selected_snapshot=snap,
                          seed=0, selected_round=1,
                          clock=GlobalClock(START_MS),
                          now_unix_ms=START_MS + 10000,
                          local_elapsed_ms=10000,
                          observer_selected_digest=digest(snap),
                          ledger_sha="b"*64)
        for changed in (
            {"source_sha": "b"*40},
            {"seed": 16384},
            {"selected_round": 2},
            {"selected_snapshot_sha256": "c"*64},
            {"first_job_start_unix_ms": START_MS + 50000},
            {"elapsed_global_ms": 1900000},
            {"physics_sha256": "a"*64},
            {"learning_claim": True},
        ):
            with self.subTest(changed=changed), self.assertRaises(D16BoundaryError):
                accept_transfer(manifest={**m, **changed}, snapshot=snap,
                                actual_source=SOURCE, expected_seed=0,
                                expected_selected_round=1,
                                now_unix_ms=START_MS + 13000)
        copy = {**snap, "generation": 2}
        with self.assertRaises(D16BoundaryError):
            accept_transfer(manifest=m,snapshot=copy,actual_source=SOURCE,
                            expected_seed=0,expected_selected_round=1,
                            now_unix_ms=START_MS + 13000)

    def test_original_science_seed_only_allows_round20_handoff(self):
        # This is a SYNTHETIC structural native snapshot; real original seed
        # must not be executed by this test suite.
        snap = synthetic_state(seed=16384, generation=20)
        selected = native_state_checked(snap, expected_seed=16384,
                                        expected_generation=20)
        correct = make_transfer(source_sha=SOURCE, selected_snapshot=snap,
                                seed=16384, selected_round=20,
                                clock=GlobalClock(START_MS),
                                now_unix_ms=START_MS + 700000,
                                local_elapsed_ms=700000,
                                observer_selected_digest=selected,
                                ledger_sha="c"*64)
        accept_transfer(manifest=correct, snapshot=snap,actual_source=SOURCE,
                        expected_seed=16384,expected_selected_round=20,
                        now_unix_ms=START_MS + 725000)
        with self.assertRaises(D16BoundaryError):
            make_transfer(source_sha=SOURCE,
                          selected_snapshot=synthetic_state(seed=16384,generation=19),
                          seed=16384, selected_round=19,
                          clock=GlobalClock(START_MS),
                          now_unix_ms=START_MS + 500000,
                          local_elapsed_ms=500000,
                          observer_selected_digest="f"*64,
                          ledger_sha="c"*64)
        with self.assertRaises(D16BoundaryError):
            accept_transfer(manifest=correct,snapshot=snap,actual_source=SOURCE,
                            expected_seed=16384,expected_selected_round=19,
                            now_unix_ms=START_MS + 720000)


if __name__ == "__main__":
    unittest.main()
