"""D16 offline stage FSM: synthetic metadata only; never execute original seed."""
import unittest
from dataclasses import replace

from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock,
)
from research.d16_twojob_stage_fsm_217 import StageState, FULL_KIND
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

START = 1780000000000
SRC = "d"*40
SEED = 16384


def synthetic_case(opt, number, *, mature=False, retirements=0):
    # Metadata-only test. Setting optimizer.generation does not run physics,
    # selection, D15, or any original D16 reserved seed experiment.
    opt.generation = number
    snap = opt.to_snapshot()
    categories = {name: {
        "complete_nonfailure_count": 1 if mature else 0,
        "native_replacement_count": retirements if i == 0 else 0,
    } for i,name in enumerate(sorted(set(s.category for s in opt.slots)))}
    return {
        "kind": FULL_KIND,
        "source_sha": SRC, "seed": SEED, "ordinal": number,
        "selected_snapshot": snap, "selected_v7_sha256": digest(snap),
        "learning_claim": False,
        "d15_verified_observer": {
            "source_commit": SRC, "base_seed": SEED,
            "before_optimizer_generation": number-1,
            "selected_optimizer_generation": number,
            "selected_post_v7_sha256": digest(snap),
            "evaluated_native_worlds": 128, "selected_native_worlds": 128,
            "d15_journal_chain_verified": True,
            "original_selected_once_proven_by_D15_final": True,
            "categories": categories,
            "actual_native_replacement_count": retirements,
        },
    }


def initial():
    opt = SteadyStateOptimizer.from_defaults(base_seed=SEED)
    return opt, StageState.start(source_sha=SRC, seed=SEED,
                                  original_genesis=opt.to_snapshot(),
                                  job1_start_unix_ms=START)


class D16StageFSMTests(unittest.TestCase):
    def test_original_twenty_handoff_and_thirty_seven_terminal(self):
        opt, state = initial()
        for ordinal in range(1,21):
            state = state.append(complete=synthetic_case(opt,ordinal),
                                 now_unix_ms=START+ordinal*1000,
                                 local_elapsed_ms=ordinal*1000)
        self.assertEqual(state.result,"HANDOFF_READY")
        self.assertEqual(state.selected_round,20)
        with self.assertRaises(D16BoundaryError):
            state.append(complete=synthetic_case(opt,21),
                         now_unix_ms=START+21000,local_elapsed_ms=21000)
        state = state.accept_second_job(
            verified_selected20_v7=state.selected_v7_sha256,
            clock_from_immutable_manifest=GlobalClock(START,20000),
            now_unix_ms=START+21000)
        for ordinal in range(21,38):
            state = state.append(
                complete=synthetic_case(opt,ordinal, mature=ordinal>=37,
                                        retirements=1 if ordinal==37 else 0),
                now_unix_ms=START+ordinal*1000,
                local_elapsed_ms=(ordinal-20)*1000)
        self.assertEqual(state.result,"OBSERVED_FINAL")
        self.assertEqual(state.selected_round,37)
        with self.assertRaises(D16BoundaryError):
            state.append(complete=synthetic_case(opt,38),
                         now_unix_ms=START+38000,local_elapsed_ms=18000)

    def test_no_false_success_after37_and_terminal_negative40(self):
        opt,state=initial()
        for n in range(1,21):
            state=state.append(complete=synthetic_case(opt,n),
                               now_unix_ms=START+n*1000,local_elapsed_ms=n*1000)
        state=state.accept_second_job(verified_selected20_v7=state.selected_v7_sha256,
                                      clock_from_immutable_manifest=GlobalClock(START,20000),
                                      now_unix_ms=START+21000)
        for n in range(21,41):
            state=state.append(complete=synthetic_case(opt,n),
                               now_unix_ms=START+n*1000,
                               local_elapsed_ms=(n-20)*1000)
            if n==37:
                self.assertEqual(state.result,"IN_PROGRESS")
        self.assertEqual(state.result,"NOT_OBSERVED_FINAL")

    def test_reject_source_generation_and_missing_journal_proof(self):
        opt,state=initial()
        rec=synthetic_case(opt,1)
        for variant in (
            {**rec,"source_sha":"a"*40},
            {**rec,"ordinal":2},
            {**rec,"selected_v7_sha256":"f"*64},
            {**rec,"d15_verified_observer":{**rec["d15_verified_observer"],
                                           "d15_journal_chain_verified":False}},
        ):
            with self.assertRaises(D16BoundaryError):
                state.append(complete=variant,
                             now_unix_ms=START+1000,local_elapsed_ms=1000)

    def test_early_retirement_does_not_count_as_mature_science_result(self):
        opt,state=initial()
        for n in range(1,21):
            state=state.append(complete=synthetic_case(
                opt,n,retirements=1 if n==15 else 0),
                now_unix_ms=START+n*1000,local_elapsed_ms=n*1000)
        self.assertEqual(state.observed_native_retirements,0)
        state=state.accept_second_job(
            verified_selected20_v7=state.selected_v7_sha256,
            clock_from_immutable_manifest=GlobalClock(START,20000),
            now_unix_ms=START+21000)
        for n in range(21,38):
            state=state.append(complete=synthetic_case(
                opt,n,mature=n>=37),
                now_unix_ms=START+n*1000,
                local_elapsed_ms=(n-20)*1000)
        self.assertEqual(state.result,"IN_PROGRESS")

    def test_retirement_in_other_immature_category_is_not_positive(self):
        opt,state=initial()
        for n in range(1,21):
            state=state.append(complete=synthetic_case(opt,n),
                               now_unix_ms=START+n*1000,local_elapsed_ms=n*1000)
        state=state.accept_second_job(
            verified_selected20_v7=state.selected_v7_sha256,
            clock_from_immutable_manifest=GlobalClock(START,20000),
            now_unix_ms=START+21000)
        for n in range(21,37):
            state=state.append(complete=synthetic_case(opt,n),
                               now_unix_ms=START+n*1000,
                               local_elapsed_ms=(n-20)*1000)
        record=synthetic_case(opt,37,retirements=1)
        cats=dict(record["d15_verified_observer"]["categories"])
        keys=sorted(cats)
        # Retirement occurs in keys[0]; growth history is mature only in
        # keys[1], so the same-category mature event is NOT demonstrated.
        cats[keys[1]]={**cats[keys[1]],"complete_nonfailure_count":1}
        record={**record,"d15_verified_observer":{
            **record["d15_verified_observer"],"categories":cats,
        }}
        state=state.append(complete=record,now_unix_ms=START+37000,
                           local_elapsed_ms=17000)
        self.assertEqual(state.result,"IN_PROGRESS")
        self.assertEqual(state.observed_native_retirements,0)
        state=state.append(complete=synthetic_case(opt,38,mature=True),
                           now_unix_ms=START+38000,local_elapsed_ms=18000)
        self.assertEqual(state.result,"IN_PROGRESS")
        state=state.append(complete=synthetic_case(opt,39,mature=True,retirements=1),
                           now_unix_ms=START+39000,local_elapsed_ms=19000)
        self.assertEqual(state.result,"OBSERVED_FINAL")

    def test_category_name_spoofing_rejected(self):
        opt,state=initial()
        rec=synthetic_case(opt,1)
        cats=dict(rec["d15_verified_observer"]["categories"])
        cats["FAKE"]=cats.pop(next(iter(cats)))
        modified={**rec,"d15_verified_observer":{
            **rec["d15_verified_observer"],"categories":cats,
        }}
        with self.assertRaises(D16BoundaryError):
            state.append(complete=modified,
                         now_unix_ms=START+1000,local_elapsed_ms=1000)

    def test_reject_global_time_exhaustion(self):
        opt,state=initial()
        with self.assertRaises(D16BoundaryError):
            state.append(complete=synthetic_case(opt,1),
                         now_unix_ms=START+1800001,local_elapsed_ms=1)

    def test_seed0_has_strict_test_only_one_plus_one_no_science(self):
        # Performance fixture is intentionally tiny. The original science
        # remains exact 20+20 and can never use this benchmark-only split.
        opt=SteadyStateOptimizer.from_defaults(base_seed=0)
        state=StageState.start(source_sha=SRC,seed=0,
                               original_genesis=opt.to_snapshot(),
                               job1_start_unix_ms=START)
        def fixture(n):
            opt.generation=n
            snap=opt.to_snapshot()
            cats={name:{"complete_nonfailure_count":0,
                        "native_replacement_count":0}
                  for name in sorted(set(s.category for s in opt.slots))}
            return {
                "kind":FULL_KIND,"source_sha":SRC,"seed":0,"ordinal":n,
                "selected_snapshot":snap,"selected_v7_sha256":digest(snap),
                "learning_claim":False,"d15_verified_observer":{
                    "source_commit":SRC,"base_seed":0,
                    "before_optimizer_generation":n-1,
                    "selected_optimizer_generation":n,
                    "selected_post_v7_sha256":digest(snap),
                    "evaluated_native_worlds":128,"selected_native_worlds":128,
                    "d15_journal_chain_verified":True,
                    "original_selected_once_proven_by_D15_final":True,
                    "categories":cats,"actual_native_replacement_count":0,
                },
            }
        state=state.append(complete=fixture(1),
                           now_unix_ms=START+1000,local_elapsed_ms=1000)
        self.assertEqual(state.result,"HANDOFF_READY")
        state=state.accept_second_job(
            verified_selected20_v7=state.selected_v7_sha256,
            clock_from_immutable_manifest=GlobalClock(START,1000),
            now_unix_ms=START+2000)
        state=state.append(complete=fixture(2),
                           now_unix_ms=START+3000,local_elapsed_ms=1000)
        self.assertEqual(state.result,"FIXTURE_COMPLETE_NO_SCIENCE")
        with self.assertRaises(D16BoundaryError):
            state.append(complete=fixture(3),
                         now_unix_ms=START+4000,local_elapsed_ms=2000)

    def test_reject_stage2_without_exact_selected20_handoff(self):
        opt,state=initial()
        for n in range(1,21):
            state=state.append(complete=synthetic_case(opt,n),
                               now_unix_ms=START+n*1000,local_elapsed_ms=n*1000)
        for wrong_sha,wrong_clock in (
            ("a"*64, GlobalClock(START,20000)),
            (state.selected_v7_sha256, GlobalClock(START-1000,20000)),
            (state.selected_v7_sha256, GlobalClock(START,19000)),
        ):
            with self.assertRaises(D16BoundaryError):
                state.accept_second_job(
                    verified_selected20_v7=wrong_sha,
                    clock_from_immutable_manifest=wrong_clock,
                    now_unix_ms=START+21000)


if __name__ == "__main__":
    unittest.main()
