import unittest
from unittest.mock import patch

from research import phase_g_decay_search_159 as g1
from research.phase_g_memory_search_159 import DECAY_DOMAIN


class PhaseGDecaySearch159Tests(unittest.TestCase):
    def test_frozen_g0_provenance_and_cohort_boundary(self) -> None:
        frozen = g1.load_frozen_g0()
        search = set(frozen["search_cohort"])
        sentinels = set(frozen["search_negative_sentinels"])
        heldout = set(frozen["heldout_validation_cohort"])
        heldout_sentinels = set(frozen["heldout_negative_sentinels"])
        self.assertEqual(frozen["held_out_max_horizon"], 0)
        self.assertTrue((search | sentinels).isdisjoint(heldout | heldout_sentinels))
        self.assertEqual(frozen["protocol"]["adaptive_horizons"], [100, 1000])
        self.assertEqual(frozen["protocol"]["teacher_pair"], [66, 8])

    def test_actual_search_case_smoke_is_deterministic_through_h100(self) -> None:
        frozen = g1.load_frozen_g0()
        case = g1.run_case(
            decay_rate=256,
            seed=int(frozen["search_cohort"][0]),
            role="adaptive_search_smoke",
            verify=True,
            max_horizon=100,
        )
        self.assertTrue(case["replay_match"])
        self.assertTrue(case["raw_instrumented_match"])
        self.assertEqual(set(case["checkpoints"]), {"0", "100"})

    def test_evaluate_candidate_uses_only_adaptive_search_and_sentinel_seeds(self) -> None:
        frozen = g1.load_frozen_g0()
        calls: list[tuple[int, str]] = []

        def fake_run_case(*, decay_rate, seed, role, verify, max_horizon):
            calls.append((int(seed), str(role)))
            distinct = role == "adaptive_search"
            checkpoints = {
                "0": {
                    "branch_digests": {"b": "b0", "h": "h0", "control": "c0", "control_repeat": "c0"},
                    "b_vs_h_distinct": distinct,
                    "b_vs_h_changed_slots": 1 if distinct else 0,
                    "control_repeat_clean": True,
                },
                "100": {
                    "branch_digests": {"b": "b1", "h": "h1", "control": "c1", "control_repeat": "c1"},
                    "b_vs_h_distinct": distinct,
                    "b_vs_h_changed_slots": 1 if distinct else 0,
                    "control_repeat_clean": True,
                },
                "1000": {
                    "branch_digests": {"b": "b2", "h": "h2", "control": "c2", "control_repeat": "c2"},
                    "b_vs_h_distinct": distinct,
                    "b_vs_h_changed_slots": 1 if distinct else 0,
                    "control_repeat_clean": True,
                },
            }
            return {
                "seed": int(seed),
                "role": role,
                "decay_rate": decay_rate,
                "candidate_identity": "fake",
                "checkpoints": checkpoints,
                "turnover_witness": False,
                "replay_match": True if verify else None,
                "raw_instrumented_match": True if verify else None,
            }

        with patch.object(g1, "run_case", side_effect=fake_run_case):
            record = g1.evaluate_candidate(256)

        expected = {
            *(int(seed) for seed in frozen["search_cohort"]),
            *(int(seed) for seed in frozen["search_negative_sentinels"]),
        }
        observed = {seed for seed, _ in calls}
        heldout = {
            *(int(seed) for seed in frozen["heldout_validation_cohort"]),
            *(int(seed) for seed in frozen["heldout_negative_sentinels"]),
        }
        self.assertEqual(observed, expected)
        self.assertTrue(observed.isdisjoint(heldout))
        self.assertFalse(record["heldout_post_h0_executed"])

    def _records(self, *, best_h1000: int, reference_h1000: int = 1):
        frozen = g1.load_frozen_g0()
        records = []
        for decay in DECAY_DOMAIN:
            h1000 = best_h1000 if decay == 0 else (reference_h1000 if decay == 256 else 0)
            records.append(
                {
                    "decay_rate": decay,
                    "candidate_identity": f"{decay:05d}",
                    "g0_artifact_digest": frozen["artifact_digest"],
                    "search_plan_digest": frozen["search_plan_digest"],
                    "registry_digest": frozen["registry_digest"],
                    "objective_profile_digest": frozen["objective_profile_digest"],
                    "protocol_digest": frozen["protocol_digest"],
                    "heldout_post_h0_executed": False,
                    "evidence": {
                        "h1000_distinct_count": h1000,
                        "h100_distinct_count": 16,
                        "turnover_witness_count": 1,
                    },
                    "validity": {
                        "replay_clean": True,
                        "raw_instrumented_clean": True,
                        "duplicate_controls_clean": True,
                        "negative_sentinels_clean": True,
                        "validity_clean": True,
                        "eligible": True,
                    },
                    "search_cases": [],
                    "negative_cases": [],
                }
            )
        return records

    def test_route_phase_h_requires_two_thirds_and_strict_reference_improvement(self) -> None:
        result = g1.aggregate_candidates(
            self._records(best_h1000=11, reference_h1000=10)
        )
        self.assertEqual(result["terminal_route"], "ROUTE-PHASE-H")
        self.assertEqual(result["selected"]["decay_rate"], 0)

    def test_route_change_path_when_best_is_below_frozen_threshold(self) -> None:
        result = g1.aggregate_candidates(
            self._records(best_h1000=10, reference_h1000=1)
        )
        self.assertEqual(result["terminal_route"], "CHANGE_PATH")

    def test_route_change_path_when_best_does_not_beat_reference(self) -> None:
        result = g1.aggregate_candidates(
            self._records(best_h1000=11, reference_h1000=11)
        )
        self.assertEqual(result["terminal_route"], "CHANGE_PATH")

    def test_route_fix_when_validity_is_broken(self) -> None:
        records = self._records(best_h1000=11, reference_h1000=1)
        records[0]["validity"]["validity_clean"] = False
        records[0]["validity"]["eligible"] = False
        result = g1.aggregate_candidates(records)
        self.assertEqual(result["terminal_route"], "ROUTE-G1-FIX")


if __name__ == "__main__":
    unittest.main()
