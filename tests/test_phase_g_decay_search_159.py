"""G1 frozen-evidence and no-held-out guards for UniverseGenome #159."""
import json
from pathlib import Path
import tempfile
import unittest

from research import phase_g_memory_search_159 as g0
from research import phase_g_decay_search_159 as g1
from research import slow_trace_persistence_140 as historical
from core.runner import load_config


class PhaseGDecayG1Tests(unittest.TestCase):
    def test_frozen_plan_and_cohorts_unmodified(self):
        frozen = g1.frozen_contract()
        self.assertEqual(frozen["search_cohort"], [32,36,37,40,42,45,46,47,49,50,53,54,55,62,65,67])
        self.assertEqual(frozen["search_negative_sentinels"], [33,34,35,38])
        self.assertEqual(frozen["held_out_max_horizon"], 0)
        self.assertEqual(frozen["protocol"]["teacher_pair"], [66,8])
        self.assertEqual(frozen["protocol"]["adaptive_horizons"], [100,1000])
        self.assertEqual(tuple(frozen["search_plan"]["search"]), ("trace_decay_rate",))

    def test_heldout_and_nonqualified_seeds_fail_closed(self):
        frozen = g1.frozen_contract()
        for seed in (103, 140, 96, 0, 22, 72):
            with self.subTest(seed=seed):
                with self.assertRaisesRegex(ValueError, "rejects"):
                    g1.case_once(seed=seed, role="adaptive_search", decay_rate=256,
                                 instrumented=False, frozen=frozen)
        with self.assertRaisesRegex(ValueError, "rejects"):
            g1.case_once(seed=32, role="negative_sentinel", decay_rate=256,
                         instrumented=False, frozen=frozen)
        with self.assertRaisesRegex(ValueError, "domain"):
            g1.case_once(seed=32, role="adaptive_search", decay_rate=2048,
                         instrumented=False, frozen=frozen)

    def test_h1_matches_historical_140_observation_semantics(self):
        frozen = g1.frozen_contract()
        actual = g1.case_once(seed=32, role="adaptive_search", decay_rate=256,
                              instrumented=True, max_horizon=1, frozen=frozen)
        expected = historical.case_once(
            seed=32, role="adaptive_search",
            config_payload=load_config("config/default.json"),
            experiment_payload=json.loads(Path("config/experiment_v0_1.json").read_text(encoding="utf-8")),
            instrumented=True, max_horizon=1
        )
        self.assertEqual(actual["checkpoints"], expected["checkpoints"])
        self.assertEqual(actual["original_trace_carriers"], expected["original_trace_carriers"])
        self.assertEqual(actual["turnover_witness"], expected["turnover_witness"])

    def test_assessment_rejects_unmatched_evidence(self):
        f = g1.frozen_contract()
        self.assertRaises(RuntimeError, g1.assess_candidate, [], f)

    def _synthetic_evidence(self, directory: Path, winner_count: int):
        f = g1.frozen_contract()
        for decay in g0.DECAY_DOMAIN:
            identity = g0.resolve_decay_candidate(decay).candidate_identity
            count = winner_count if decay == 0 else 3
            cases = []
            for index, seed in enumerate(f["search_cohort"]):
                cases.append({
                    "seed": seed, "role": "adaptive_search", "candidate_identity": identity,
                    "distinct": {str(h): (index < count if h == 1000 else True)
                                 for h in g1.HORIZONS},
                    "turnover_witness": False,
                    "duplicate_control_clean": True, "replay_match": True,
                    "raw_instrumented_match": True,
                })
            for seed in f["search_negative_sentinels"]:
                cases.append({
                    "seed": seed, "role": "negative_sentinel", "candidate_identity": identity,
                    "distinct": {str(h): False for h in g1.HORIZONS},
                    "turnover_witness": False,
                    "duplicate_control_clean": True,
                    "replay_match": None, "raw_instrumented_match": None,
                })
            record = {
                "schema_version": 1, "issue": 159, "phase": "G1",
                "scope": "adaptive_search_only", "learning_claim": False,
                "decay_rate": decay, "candidate_identity": identity,
                "G0_artifact_digest": f["artifact_digest"],
                "search_plan_digest": f["search_plan_digest"],
                "registry_digest": f["registry_digest"],
                "objective_profile_digest": f["objective_profile_digest"],
                "protocol_digest": f["protocol_digest"],
                "held_out_max_horizon": 0,
                "cases": cases, "summary": g1.assess_candidate(cases, f),
            }
            record["result_digest"] = g0._digest(record)
            (directory / f"candidate-{decay}.json").write_text(json.dumps(record), encoding="utf-8")

    def test_predeclared_routing_requires_11_of_16(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self._synthetic_evidence(directory, winner_count=11)
            self.assertEqual(g1.aggregate(directory)["terminal_route"], "ROUTE-PHASE-H")
            self._synthetic_evidence(directory, winner_count=10)
            self.assertEqual(g1.aggregate(directory)["terminal_route"], "CHANGE_PATH")

    def test_negative_cleanliness_can_invalidate_candidate(self):
        f=g1.frozen_contract()
        cases=[
            {"seed":seed,"role":"adaptive_search","distinct":{str(h):True for h in g1.HORIZONS},
             "replay_match":True,"raw_instrumented_match":True,"turnover_witness":False,
             "duplicate_control_clean":True}
            for seed in f["search_cohort"]
        ] + [
            {"seed":seed,"role":"negative_sentinel","distinct":{str(h):h==1000 for h in g1.HORIZONS},
             "turnover_witness":False,"duplicate_control_clean":True}
            for seed in f["search_negative_sentinels"]
        ]
        self.assertFalse(g1.assess_candidate(cases,f)["valid"])


if __name__ == "__main__":
    unittest.main()
