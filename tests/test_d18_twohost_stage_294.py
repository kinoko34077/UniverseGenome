"""D18 #294 synthetic two-host boundary tests. No native worlds evaluated."""
from dataclasses import replace
import unittest

from research.d18_twohost_stage_294 import (
    D18TwoHostState, SEARCH_SEED, SEED, FIRST_LAST, GENESIS_CHAIN,
    hash_receipt,
)

SOURCE = "a" * 40
SELECTED = "b" * 64


def fake_admitted(ordinal, job, *, e1=0, e2=0, elapsed=None):
    if elapsed is None:
        elapsed = ordinal * 20000
    status = (
        "OBSERVED_E2_FINAL" if ordinal >= 37 and e2
        else "E2_NOT_OBSERVED_FINAL" if ordinal == 40
        else "CONTINUE"
    )
    return {
        "schema": "D18_NEW_SEED_NATIVE_JOURNAL_ADMISSION_V1",
        "source_sha": SOURCE,
        "seed": SEED,
        "ordinal": ordinal,
        "job": job,
        "selected_post_v7_sha256": SELECTED,
        "global_elapsed_ms": elapsed,
        "journal_bytes": 11_000_000,
        "E1_count": e1,
        "E2_count": e2,
        "status": status,
        "read_only": True,
        "learning_claim": False,
    }


def first_stage(*, at_early_e1=False):
    state = D18TwoHostState.first_host(
        source_sha=SOURCE, started_unix_ms=1_800_000_000_000
    )
    for i in range(1, 21):
        state = state.append(fake_admitted(i, 1, e1=int(i == 9 and at_early_e1)))
    return state


class D18TwoHostStudyTests(unittest.TestCase):
    def test_frozen_new_seed_nonlaunch_and_exact_first20(self):
        self.assertEqual(SEED, 49152)
        self.assertEqual(FIRST_LAST, 20)
        state = first_stage()
        self.assertEqual(state.ordinal, 20)
        self.assertEqual(state.job, 1)
        self.assertEqual(state.status, "HANDOFF_READY")
        self.assertEqual(len(state.receipt_chain_sha256), 64)
        self.assertNotEqual(state.receipt_chain_sha256, GENESIS_CHAIN)
        with self.assertRaises(ValueError):
            state.append(fake_admitted(21, 1))

    def test_full40_uses_all_rounds_for_prior_e1_never_e2(self):
        first = first_stage(at_early_e1=True)
        second = D18TwoHostState.from_verified_handoff(
            first.transfer_manifest(), expected_source_sha=SOURCE
        )
        self.assertTrue(second.saw_growth_candidate_E1)
        for ordinal in range(21, 41):
            second = second.append(fake_admitted(ordinal, 2))
        self.assertEqual(second.ordinal, 40)
        self.assertEqual(second.status, "E1_ONLY_FINAL")
        self.assertFalse(second.saw_real_growth_retirement_E2)
        with self.assertRaises(ValueError):
            second.append(fake_admitted(41, 2))

    def test_complete40_with_no_e1_classifies_not_observed(self):
        first = first_stage()
        second = D18TwoHostState.from_verified_handoff(
            first.transfer_manifest(), expected_source_sha=SOURCE
        )
        for ordinal in range(21, 41):
            second = second.append(fake_admitted(ordinal, 2))
        self.assertEqual(second.status, "NO_E1_FINAL")

    def test_actual_native_e2_cumulative_stops_at37(self):
        first = first_stage()
        second = D18TwoHostState.from_verified_handoff(
            first.transfer_manifest(), expected_source_sha=SOURCE
        )
        for ordinal in range(21, 38):
            second = second.append(fake_admitted(
                ordinal, 2, e1=int(ordinal == 36),
                e2=int(ordinal == 36),
            ))
        self.assertEqual(second.ordinal, 37)
        self.assertEqual(second.status, "E2_CONFIRMED_FINAL")
        self.assertTrue(second.saw_real_growth_retirement_E2)
        with self.assertRaises(ValueError):
            second.append(fake_admitted(38, 2))

    def test_bad_handoff_never_produces_implicit_second_job(self):
        first = first_stage()
        manifest = first.transfer_manifest()
        for change in (
            {"seed": 16384}, {"seed": 0}, {"selected_round": 19},
            {"source_sha": "c" * 40},
            {"receipt_chain_sha256": "bad"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                D18TwoHostState.from_verified_handoff(
                    {**manifest, **change}, expected_source_sha=SOURCE
                )

    def test_wrong_source_seed_third_job_and_skipped_round_refused(self):
        first = D18TwoHostState.first_host(
            source_sha=SOURCE, started_unix_ms=1_800_000_000_000
        )
        for alteration in (
            {"seed": 0}, {"seed": 16384}, {"source_sha": "c" * 40},
            {"job": 2}, {"job": 3}, {"ordinal": 2},
            {"E1_count": 0, "E2_count": 1}, {"learning_claim": True},
        ):
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                first.append({**fake_admitted(1, 1), **alteration})

    def test_global_clock_regression_missing_digest_bad_budget(self):
        first = D18TwoHostState.first_host(
            source_sha=SOURCE, started_unix_ms=1_800_000_000_000
        )
        first = first.append(fake_admitted(1, 1))
        for change in (
            {"global_elapsed_ms": 1}, {"global_elapsed_ms": 1800001},
            {"journal_bytes": 128 * 1024 * 1024 + 1},
            {"selected_post_v7_sha256": "bad"}, {"E1_count": -1},
            {"read_only": False},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                first.append({**fake_admitted(2, 1), **change})


if __name__ == "__main__":
    unittest.main()
