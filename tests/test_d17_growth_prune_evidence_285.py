"""D17 original science archive analyzer: synthetic safety guards only.

Never invokes selected native evolution or reserved seed16384 research.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from research.d16_twojob_run_control_217 import D16BoundaryError
from research.d17_growth_prune_evidence_285 import (
    ORIGINAL_SOURCE, ORIGINAL_SEED, ORIGINAL_ROUNDS,
    ORIGINAL_ZIP_SHA256, CATEGORIES,
    category_candidate_counts, growth_thresholds, audit_archive,
)


class D17OfflineOriginalAuditTests(unittest.TestCase):
    def test_frozen_original_provenance(self):
        self.assertEqual(len(ORIGINAL_SOURCE), 40)
        self.assertEqual(ORIGINAL_SEED, 16384)
        self.assertEqual(ORIGINAL_ROUNDS, 37)
        self.assertEqual(len(ORIGINAL_ZIP_SHA256), 64)
        self.assertEqual(len(CATEGORIES), 4)

    def test_zero_additional_growth_candidates(self):
        x = category_candidate_counts({
            "native_eligible_prune_indices": list(range(16)),
            "absolute_failure_count": 16,
            "complete_nonfailure_count": 3,
            "native_replacement_count": 1,
        })
        self.assertEqual(x["growth_only_candidate_count"], 0)
        self.assertEqual(x["native_replacement_count"], 1)

    def test_nonzero_growth_candidate_kept_distinct_from_abs_failure(self):
        x = category_candidate_counts({
            "native_eligible_prune_indices": [1, 5, 7],
            "absolute_failure_count": 2,
            "complete_nonfailure_count": 3,
            "native_replacement_count": 1,
        })
        self.assertEqual(x["growth_only_candidate_count"], 1)

    def test_corrupt_original_pruned_subset_refused(self):
        for row in (
            {"native_eligible_prune_indices": [1], "absolute_failure_count": 2,
             "complete_nonfailure_count": 3, "native_replacement_count": 1},
            {"native_eligible_prune_indices": [1, 1], "absolute_failure_count": 1,
             "complete_nonfailure_count": 3, "native_replacement_count": 1},
        ):
            with self.assertRaises(D16BoundaryError):
                category_candidate_counts(row)

    def test_actual_original_round37_growth_vectors_have_zero_threshold(self):
        slots = [
            {"category": "masked_copy", "index": 9, "absolute_failure": False,
             "growth_windows": [0, 1, 0, 0]},
            {"category": "masked_copy", "index": 19, "absolute_failure": False,
             "growth_windows": [0, 1, 0, 1]},
            {"category": "masked_copy", "index": 23, "absolute_failure": False,
             "growth_windows": [1, 0, 1, 0]},
        ]
        x = growth_thresholds({"slots": slots}, "masked_copy")
        self.assertEqual(x["median_bitcounts"], [0, 1, 0, 0])
        self.assertEqual(x["native_half_median_thresholds"], [0, 0, 0, 0])
        self.assertEqual(x["underthreshold_selected_healthy_count"], 0)

    def test_forged_input_zip_rejected_before_json_or_any_physics(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "not-original.zip"
            path.write_bytes(b"forged evidence")
            with self.assertRaisesRegex(D16BoundaryError, "artifact ZIP"):
                audit_archive(path)

    def test_absent_input_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(D16BoundaryError):
                audit_archive(Path(tmp) / "missing.zip")


if __name__ == "__main__":
    unittest.main()
