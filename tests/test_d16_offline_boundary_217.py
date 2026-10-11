"""D16 offline structural guard tests: entirely synthetic metadata, NO original science."""
from dataclasses import replace
import unittest

from research.d16_offline_boundary_217 import (
    EvidenceError, Patch, Protocol, Round, classify, validate,
)


def protocol():
    return Protocol("a" * 40, "b" * 64, "c" * 64, "d" * 64,
                    ("nativeA", "nativeB", "nativeC", "nativeD"))


def record(p, n=1, previous=None, *, job=None, sizes=None):
    group = job if job is not None else (n - 1) // 20 + 1
    if sizes is None:
        sizes = (16,) * 8
    pos = 0
    patches = []
    for size in sizes:
        patches.append(Patch(pos, pos + size, "e" * 64))
        pos += size
    return Round(
        number=n, job=group, source=p.source, seed=p.seed,
        experiment_sha=p.experiment_sha, physics_sha=p.physics_sha,
        predecessor_sha=previous.selected_sha if previous else p.initial_selected_sha,
        evaluated_preselect_sha="f" * 64, observer_preselect_sha="f" * 64,
        selected_sha=("%064x" % n), evaluated_worlds=128, selection_count=1,
        categories={name: 32 for name in p.category_names},
        patches=tuple(patches), journal_bytes=10453787, retained_bytes=11000000,
        peak_sampled_rss_bytes=350000000, global_seconds=float(n * 20),
        local_seconds=float(((n - 1) % 20 + 1) * 20),
        prunable_count=0, replacement_count=0,
        completed_growth_nonfailed=0, absolute_failure_count=0
    )


def history(p, count):
    rows = []
    for i in range(1, count + 1):
        rows.append(record(p, i, rows[-1] if rows else None))
    return tuple(rows)


class OfflineBoundaryTests(unittest.TestCase):
    def test_two_contiguous_original_selected_rounds(self):
        p = protocol()
        rows = history(p, 2)
        validate(p, rows)
        self.assertEqual(classify(p, rows)["outcome"], "IN_PROGRESS")

    def test_adaptive_d15_patches_need_contiguity_not_exact_eight(self):
        p = protocol()
        valid = record(p, sizes=(1, 15) + (16,) * 7)
        validate(p, (valid,))
        for broken in ((16,) * 7, (17,) + (16,) * 7):
            with self.assertRaises(EvidenceError):
                validate(p, (record(p, sizes=broken),))

    def test_wrong_seed_source_config_and_preselect_observer(self):
        p = protocol()
        original = record(p)
        for v in (
            replace(original, seed=0),
            replace(original, source="1" * 40),
            replace(original, experiment_sha="0" * 64),
            replace(original, observer_preselect_sha="a" * 64),
            replace(original, selection_count=0),
            replace(original, evaluated_worlds=127),
        ):
            with self.subTest(v=v), self.assertRaises(EvidenceError):
                validate(p, (v,))

    def test_selected_snapshot_handoff_chain_fails_closed(self):
        p = protocol()
        one, two = history(p, 2)
        with self.assertRaises(EvidenceError):
            validate(p, (one, replace(two, predecessor_sha="1" * 64)))
        with self.assertRaises(EvidenceError):
            validate(p, (one, replace(two, number=4)))

    def test_native_one_replacement_per_category_many_prunable(self):
        p = protocol()
        candidate = replace(record(p), prunable_count=90, replacement_count=4)
        validate(p, (candidate,))
        with self.assertRaises(EvidenceError):
            validate(p, (replace(candidate, replacement_count=5),))

    def test_frozen_exact_two_job_20_plus_20_partition(self):
        p = protocol()
        twenty = history(p, 20)
        validate(p, twenty)
        with self.assertRaises(EvidenceError):
            validate(p, twenty + (record(p, 21, twenty[-1], job=1),))
        with self.assertRaises(EvidenceError):
            validate(p, twenty + (record(p, 21, twenty[-1], job=3),))
        with self.assertRaises(EvidenceError):
            validate(p, (record(p, 1, job=2),))
        with self.assertRaises(EvidenceError):
            validate(p, history(p, 19) + (record(p, 20, history(p, 19)[-1], job=2),))
        validate(p, twenty + (record(p, 21, twenty[-1], job=2),))

    def test_global_and_local_caps_not_reset_by_job(self):
        p = protocol()
        two = history(p, 11)
        with self.assertRaises(EvidenceError):
            validate(p, two[:-1] + (replace(two[-1], global_seconds=1801),))
        with self.assertRaises(EvidenceError):
            validate(p, (replace(two[0], local_seconds=1081),))
        with self.assertRaises(EvidenceError):
            validate(p, (two[0], replace(two[1], global_seconds=10),))

    def test_growth_before_round37_rejected(self):
        p = protocol()
        with self.assertRaises(EvidenceError):
            validate(p, (replace(record(p), completed_growth_nonfailed=1),))
        rows = list(history(p, 37))
        rows[-1] = replace(rows[-1], prunable_count=1, replacement_count=1,
                           completed_growth_nonfailed=1)
        self.assertEqual(classify(p, tuple(rows))["outcome"],
                         "GROWTH_AND_REPLACEMENT_COOBSERVED_NO_CAUSAL_CLAIM")
        self.assertFalse(classify(p, tuple(rows))["provenance_authenticated"])

    def test_bound_incomplete_does_not_claim_success(self):
        p = protocol()
        rows = history(p, 12)
        result = classify(p, rows, budget_bound=True)
        self.assertEqual(result["outcome"], "BUDGET_BOUND_INCOMPLETE")
        self.assertFalse(result["target_1200_met"])
        self.assertFalse(result["learning_claim"])

    def test_frozen_protocol_rejects_study_parameter_drift(self):
        p = protocol()
        for kw in ({"seed": 0}, {"max_rounds": 36}, {"preferred_seconds": 1800},
                   {"max_jobs": 4}, {"rounds_per_job": 10},
                   {"category_names": ("nativeA",) * 4}):
            with self.assertRaises(EvidenceError):
                Protocol(**{**p.__dict__, **kw})


if __name__ == "__main__":
    unittest.main()
