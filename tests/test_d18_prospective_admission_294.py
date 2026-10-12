"""D18.1 prospective source-only gate — all fixtures synthetic, no actual seed49152 run."""
from pathlib import Path
import tempfile
import unittest

from research.d18_prospective_admission_294 import (
    SEARCH_SEED, MAX_JOBS, stage_for_round, interpret_genuine_e1_e2,
    admit_completed_native_journal,
)


def synthetic(ordinal, *, e1=False, e2=False):
    categories = {}
    for i, category in enumerate(("masked_and", "masked_copy", "masked_xor", "rotate_copy")):
        growth = [i] if i == 1 and e1 else []
        evt = ({"index": i, "retirement_reason": "growth_pruned"}
               if i == 1 and e2 else None)
        categories[category] = {
            "growth_only_candidate_indices_E1": growth,
            "authentic_growth_pruned_E2": evt is not None,
            "actual_native_retirement_E2": evt,
            "native_predicted_target_index": i if evt is not None else None,
        }
    return {
        "schema": "D18_ORIGINAL_D15_ACTUAL_SELECTED_E1_E2_OBSERVER_V1",
        "seed": SEARCH_SEED,
        "original_selected_round": ordinal,
        "original_native_evaluated_worlds": 128,
        "read_only": True,
        "learning_claim": False,
        "categories": categories,
        "E1_growth_only_candidate_count": int(e1),
        "E2_actual_growth_pruned_count": int(e2),
    }


class D18ProspectiveStudyGateTests(unittest.TestCase):
    def test_frozen_new_seed_and_two_job_partition(self):
        self.assertEqual(SEARCH_SEED, 49152)
        self.assertEqual(MAX_JOBS, 2)
        self.assertEqual(stage_for_round(1), 1)
        self.assertEqual(stage_for_round(20), 1)
        self.assertEqual(stage_for_round(21), 2)
        self.assertEqual(stage_for_round(40), 2)
        for ordinal in (0, 41, True, 1.0):
            with self.subTest(ordinal=ordinal), self.assertRaises(ValueError):
                stage_for_round(ordinal)

    def test_e1_candidate_does_not_imply_actual_e2(self):
        self.assertEqual(interpret_genuine_e1_e2(37, synthetic(37, e1=True)),
                         "CONTINUE")
        self.assertEqual(interpret_genuine_e1_e2(40, synthetic(40, e1=True)),
                         "E2_NOT_OBSERVED_FINAL")
        self.assertEqual(interpret_genuine_e1_e2(40, synthetic(40)),
                         "E2_NOT_OBSERVED_FINAL")

    def test_genuine_source_e2_only_when_source_retired_e1(self):
        self.assertEqual(interpret_genuine_e1_e2(37, synthetic(37, e1=True, e2=True)),
                         "OBSERVED_E2_FINAL")
        self.assertEqual(interpret_genuine_e1_e2(10, synthetic(10, e1=True, e2=True)),
                         "CONTINUE")

    def test_forged_retirement_and_summary_fail_closed(self):
        a = synthetic(37, e1=True, e2=True)
        a["categories"]["masked_copy"]["actual_native_retirement_E2"] = {
            "index": 1, "retirement_reason": "persistent_non_response"
        }
        with self.assertRaises(ValueError):
            interpret_genuine_e1_e2(37, a)
        b = synthetic(37, e1=True, e2=True)
        b["E1_growth_only_candidate_count"] = 0
        with self.assertRaises(ValueError):
            interpret_genuine_e1_e2(37, b)
        c = synthetic(37, e1=True, e2=True)
        c["categories"]["masked_copy"]["native_predicted_target_index"] = 0
        with self.assertRaises(ValueError):
            interpret_genuine_e1_e2(37, c)
        d = synthetic(37, e1=True, e2=True)
        d["categories"]["masked_copy"]["authentic_growth_pruned_E2"] = False
        d["E2_actual_growth_pruned_count"] = 0
        with self.assertRaises(ValueError):
            interpret_genuine_e1_e2(37, d)

    def test_outcome_requires_exact_role_and_original_four_categories(self):
        for change in ({"seed": 16384}, {"seed": 0}, {"original_selected_round": 36},
                       {"learning_claim": True}, {"read_only": False}):
            a = {**synthetic(37), **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                interpret_genuine_e1_e2(37, a)
        c = synthetic(37)
        del c["categories"]["masked_and"]
        with self.assertRaises(ValueError):
            interpret_genuine_e1_e2(37, c)

    def test_missing_actual_journal_rejected_without_evolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "not-run"
            kwargs = {
                "source_sha": "a" * 40, "ordinal": 1, "job": 1,
                "study_started_unix_ms": 1800000000000,
                "prior_elapsed_ms": 0,
                "now_unix_ms": 1800000001000,
                "local_elapsed_ms": 1000,
            }
            with self.assertRaises(Exception):
                admit_completed_native_journal(path, **kwargs)
            with self.assertRaises(ValueError):
                admit_completed_native_journal(path, **{**kwargs, "source_sha": "short"})
            with self.assertRaises(ValueError):
                admit_completed_native_journal(path, **{**kwargs, "job": 2})
            with self.assertRaises(ValueError):
                admit_completed_native_journal(path, **{**kwargs, "job": 3})

    def test_global_cross_host_clock_checked_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            kwargs = {
                "source_sha": "a" * 40, "ordinal": 21, "job": 2,
                "study_started_unix_ms": 1800000000000,
                "prior_elapsed_ms": 1200000,
                "now_unix_ms": 1800000001000,
                "local_elapsed_ms": 1000,
            }
            with self.assertRaises(ValueError):
                admit_completed_native_journal(Path(tmp) / "unused", **kwargs)


if __name__ == "__main__":
    unittest.main()
