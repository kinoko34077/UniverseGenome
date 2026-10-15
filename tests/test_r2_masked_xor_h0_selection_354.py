"""#354: synthetic h0 qualification rule checks; no genuine native seed run."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

SPEC = Path("docs/research/r2_masked_xor_h0_selection_proposal_354.json")
INVALID = "NOT_EVALUABLE_NO_POSTHOC_SEED_REPLACEMENT"


def select_synthetic_h0_cases(cases, *, start=2048, end=2559,
                              positive_quota=16, negative_quota=8):
    """Pure validation of a prospective scan; never generate an h0 snapshot."""
    if type(positive_quota) is not int or type(negative_quota) is not int:
        raise ValueError(INVALID)
    if min(positive_quota, negative_quota) < 1:
        raise ValueError(INVALID)
    if not isinstance(cases, list) or not cases or len(cases) > end - start + 1:
        raise ValueError(INVALID)
    positive, negative, seen = [], [], []
    for i, row in enumerate(cases):
        if not isinstance(row, dict) or set(row) != {
            "seed", "max_horizon", "bh_trace_diff",
            "bh_full_state_equal", "same_teacher_repeat_equal"
        }:
            raise ValueError(INVALID)
        seed = row["seed"]
        if type(seed) is not int or seed != start + i or seed > end:
            raise ValueError(INVALID)
        if row["max_horizon"] != 0 or type(row["max_horizon"]) is not int:
            raise ValueError(INVALID)
        for name in ("bh_trace_diff", "bh_full_state_equal", "same_teacher_repeat_equal"):
            if type(row[name]) is not bool:
                raise ValueError(INVALID)
        if not row["same_teacher_repeat_equal"]:
            raise ValueError(INVALID)
        if len(positive) == positive_quota and len(negative) == negative_quota:
            raise ValueError(INVALID)  # Do not inspect h0 beyond first complete quota.
        if row["bh_trace_diff"] and not row["bh_full_state_equal"]:
            if len(positive) < positive_quota:
                positive.append(seed)
            role = "positive"
        elif not row["bh_trace_diff"] and row["bh_full_state_equal"]:
            if len(negative) < negative_quota:
                negative.append(seed)
            role = "negative"
        else:
            role = "indeterminate"
        seen.append((seed, role))
    if len(positive) != positive_quota or len(negative) != negative_quota:
        raise ValueError(INVALID)
    return {"positive": positive, "negative": negative, "inspected": seen}


class SyntheticH0RuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(SPEC.read_text(encoding="utf-8"))

    def case(self, seed, kind):
        return {
            "seed": seed, "max_horizon": 0,
            "bh_trace_diff": kind == "positive",
            "bh_full_state_equal": kind == "negative",
            "same_teacher_repeat_equal": True,
        }

    def test_proposal_no_seed_and_no_execution(self):
        d = self.doc
        self.assertEqual(d["status"], "SOURCE_ONLY_PROPOSAL_UNREVIEWED_ROSTER_AND_POOL")
        self.assertEqual(d["source_main_after_pr355"],
                         "783820ce4ab3f19996712e6cc6d86f3ca85b2462")
        self.assertEqual(d["max_qualification_horizon"], 0)
        self.assertTrue(d["only_h0_input_allowed"])
        self.assertEqual(d["teacher_values"], [66, 8])
        self.assertEqual(d["selected_seed_ids"], [])
        self.assertEqual(d["new_h0_examined"], 0)
        self.assertEqual(d["experimental_runs_performed_here"], 0)
        for key in ("approved_to_qualify", "approved_to_run_native_posth0",
                    "source_native_action_or_marker_change", "production_default_change",
                    "learning_claim"):
            self.assertIs(d[key], False)
        q = d["proposed_quota"]
        self.assertEqual((q["positives"], q["negative_sentinels"]), (16, 8))

    def test_role_bands_separate_old_and_future_holdout(self):
        d = self.doc
        exploratory = d["candidate_exploratory_pool_provisional"]
        reserve = d["independent_future_pool_reserved"]
        self.assertEqual((exploratory["start_inclusive"],
                          exploratory["end_inclusive"]), (2048, 2559))
        self.assertEqual((reserve["start_inclusive"],
                          reserve["end_inclusive"]), (1024, 2047))
        self.assertLess(d["all_previous_outcome_exposure_excluded_end_inclusive"],
                        reserve["start_inclusive"])
        self.assertLess(reserve["end_inclusive"], exploratory["start_inclusive"])
        self.assertEqual(d["legacy_phase_h_reserved_inclusive"], [96, 159])
        self.assertTrue(reserve["never_scan_for_candidate_selection"])

    def test_first_ascending_fixed_quota_synthetic_only(self):
        kinds = ["positive"] * 16 + ["negative"] * 8
        cases = [self.case(2048 + i, kind) for i,kind in enumerate(kinds)]
        got = select_synthetic_h0_cases(cases)
        self.assertEqual(got["positive"], list(range(2048,2064)))
        self.assertEqual(got["negative"], list(range(2064,2072)))
        self.assertEqual(len(got["inspected"]), 24)
        with self.assertRaisesRegex(ValueError, INVALID):
            select_synthetic_h0_cases(cases + [self.case(2072,"positive")])

    def test_reject_missing_quota_dirty_h0_and_skipped_seeds(self):
        correct=[self.case(2048+i,"positive" if i<16 else "negative")
                 for i in range(24)]
        bad=[correct[:-1], correct[1:], correct[:1]+correct[2:]]
        for cases in bad:
            with self.subTest(size=len(cases)):
                with self.assertRaisesRegex(ValueError, INVALID):
                    select_synthetic_h0_cases(cases)
        tamper=dict(correct[0], max_horizon=1)
        with self.assertRaisesRegex(ValueError, INVALID):
            select_synthetic_h0_cases([tamper]+correct[1:])
        tamper=dict(correct[0],same_teacher_repeat_equal=False)
        with self.assertRaisesRegex(ValueError, INVALID):
            select_synthetic_h0_cases([tamper]+correct[1:])

    def test_indeterminate_is_not_negative(self):
        cases=[self.case(2048,"indeterminate")]
        cases+= [self.case(2049+i, "positive" if i<16 else "negative")
                  for i in range(24)]
        out=select_synthetic_h0_cases(cases)
        self.assertEqual(out["inspected"][0], (2048, "indeterminate"))
        self.assertEqual(len(out["positive"]), 16)
        self.assertEqual(len(out["negative"]), 8)


if __name__ == "__main__":
    unittest.main()
