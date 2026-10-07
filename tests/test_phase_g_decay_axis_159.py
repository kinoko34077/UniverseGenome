"""G1 frozen-decay candidate evaluator and non-contamination guards."""
import json
from pathlib import Path
import tempfile
import unittest

from core.runner import load_config
from research.phase_g_decay_axis_159 import (
    DECAY_DOMAIN,
    FROZEN_G0_DIGEST,
    FROZEN_PROTOCOL_DIGEST,
    _digest,
    aggregate_candidates,
    case_once,
    evaluate_case,
    load_frozen_contract,
    resolve_decay_candidate,
)
from research.slow_trace_persistence_140 import case_once as historical_case_once


class PhaseGDecayAxis159Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = load_frozen_contract()

    def test_contract_is_complete_and_disjoint(self):
        self.assertEqual(self.frozen["artifact_digest"], FROZEN_G0_DIGEST)
        self.assertEqual(self.frozen["protocol_digest"], FROZEN_PROTOCOL_DIGEST)
        self.assertEqual(self.frozen["protocol"]["teacher_pair"], [66, 8])
        self.assertEqual(self.frozen["protocol"]["adaptive_horizons"], [100, 1000])
        self.assertEqual(len(self.frozen["search_cohort"]), 16)
        self.assertEqual(len(self.frozen["search_negative_sentinels"]), 4)

    def test_historical_256_observation_parity_at_short_horizon(self):
        seed = self.frozen["search_cohort"][0]
        observed = case_once(
            seed=seed, role="search", decay_rate=256, frozen=self.frozen,
            instrumented=True, max_horizon=10,
        )
        accepted = historical_case_once(
            seed=seed, role="search",
            config_payload=load_config("config/default.json"),
            experiment_payload=json.loads(
                Path("config/experiment_v0_1.json").read_text(encoding="utf-8")
            ),
            instrumented=True, max_horizon=10,
        )
        self.assertEqual(observed["checkpoints"], accepted["checkpoints"])
        self.assertEqual(observed["original_trace_carriers"], accepted["original_trace_carriers"])
        self.assertEqual(observed["turnover_witness"], accepted["turnover_witness"])

    def test_replay_and_raw_instrumentation_parity(self):
        result = evaluate_case(
            seed=self.frozen["search_cohort"][0], role="search",
            decay_rate=256, frozen=self.frozen,
            verify=True, max_horizon=1,
        )
        self.assertTrue(result["replay_clean"])
        self.assertTrue(result["raw_instrumented_clean"])
        self.assertTrue(all(item["control_clean"] for item in result["checkpoints"].values()))

    def test_heldout_historical_and_arbitrary_seeds_are_rejected(self):
        for seed in (
            self.frozen["heldout_validation_cohort"][0],
            self.frozen["heldout_negative_sentinels"][0],
            self.frozen["old_140_primary_seeds_excluded"][0],
            99999,
        ):
            with self.subTest(seed=seed):
                with self.assertRaisesRegex(ValueError, "not in frozen adaptive-search evidence"):
                    case_once(
                        seed=seed, role="search", decay_rate=256,
                        frozen=self.frozen, instrumented=False, max_horizon=1,
                    )

    def test_unregistered_decay_and_horizon_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside frozen domain"):
            case_once(
                seed=self.frozen["search_cohort"][0], role="search",
                decay_rate=999, frozen=self.frozen,
                instrumented=False, max_horizon=1,
            )
        with self.assertRaisesRegex(ValueError, "only frozen observation horizons"):
            case_once(
                seed=self.frozen["search_cohort"][0], role="search",
                decay_rate=256, frozen=self.frozen,
                instrumented=False, max_horizon=9999,
            )

    def _synthetic_results(self, path: Path, *, reference_valid=True,
                           improved=True, tamper=False):
        for rate in DECAY_DOMAIN:
            h1000 = 4 if rate == 0 and improved else 3
            result = {
                "schema_version": 1,
                "issue": 159,
                "phase": "G1",
                "horizon": 1000,
                "decay_rate": rate,
                "candidate_identity": resolve_decay_candidate(rate).candidate_identity,
                "g0_artifact_digest": FROZEN_G0_DIGEST,
                "protocol_digest": FROZEN_PROTOCOL_DIGEST,
                "search_plan_digest": self.frozen["search_plan_digest"],
                "search_seeds": self.frozen["search_cohort"],
                "sentinel_seeds": self.frozen["search_negative_sentinels"],
                "heldout_max_horizon": 0,
                "validity": {
                    "duplicate_control_clean": True,
                    "negative_sentinels_clean": True,
                    "replay_clean": True,
                    "raw_instrumented_clean": True,
                },
                "valid": reference_valid if rate == 256 else True,
                "scores": {
                    "h1000_distinct_count": h1000,
                    "h100_distinct_count": 8,
                    "turnover_witness_count": 1,
                },
                "cases": [
                    {"seed": seed} for seed in
                    self.frozen["search_cohort"] + self.frozen["search_negative_sentinels"]
                ],
            }
            result["artifact_digest"] = _digest(result)
            if tamper and rate == 0:
                result["scores"]["h1000_distinct_count"] = 15
            (path / f"candidate-{rate}.json").write_text(
                json.dumps(result), encoding="utf-8"
            )

    def test_routing_and_strict_reference_improvement(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            self._synthetic_results(path, improved=True)
            result = aggregate_candidates(list(path.glob("candidate-*.json")))
            self.assertEqual(result["selected_rate"], 0)
            self.assertEqual(result["terminal_route"], "ROUTE-PHASE-H")
            self._synthetic_results(path, improved=False)
            result = aggregate_candidates(list(path.glob("candidate-*.json")))
            self.assertEqual(result["terminal_route"], "CHANGE_PATH")
            self._synthetic_results(path, reference_valid=False)
            result = aggregate_candidates(list(path.glob("candidate-*.json")))
            self.assertEqual(result["terminal_route"], "ROUTE-G1-FIX")

    def test_tampered_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            self._synthetic_results(path, tamper=True)
            with self.assertRaisesRegex(ValueError, "tampered G1 candidate artifact"):
                aggregate_candidates(list(path.glob("candidate-*.json")))


if __name__ == "__main__":
    unittest.main()
