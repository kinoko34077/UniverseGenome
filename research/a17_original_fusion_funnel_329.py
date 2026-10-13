"""A1.7 #329: read-only natural fusion-eligibility funnel on original R2 cases.

Predeclared previously EXPOSED seeds 544,545 only. No new physical law,
learning claim, new scientific cohort, heldout, or changing original h0.
Native source is called unchanged; the observer only counts its gate predicates.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

from core import physics
import research.a1_exposed_reader_pilot_317 as pilot
from research.a1_native_bit_support_317 import classify as paired_classify
from research.a16_fusion_eligibility_funnel_326 import (
    STAGES,
    native_fusion_eligibility_funnel,
)
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import RATE, load_frozen
from research.phase_g_memory_search_159 import _digest


SCHEMA = "UG_A17_REAL_ORIGINAL_EXPOSED_FUSION_FUNNEL_V1"
SEEDS = (544, 545)
H0_GENERATION = 13
PERIODS = ((1, 100), (101, 250), (251, 500), (501, 1000))
EXPECTED = {544: (764, 95, 36), 545: (966, 0, 0)}
MAX_CASE_REPORT_BYTES = 128 * 1024


def period_of(relative: int) -> str:
    for a,b in PERIODS:
        if a<=relative<=b:
            return f"{a}-{b}"
    raise ValueError("A1.7 native event outside original post-h0 1000 steps")


def empty_count_record():
    return {"native_steps": 0, "candidate_groups": 0, "actual_fusions": 0,
            "gate_counts": {k:0 for k in STAGES},
            "steps_any_gate": {k:0 for k in STAGES}}


def count_one(record: dict, funnel: dict) -> None:
    record["native_steps"] += 1
    record["candidate_groups"] += int(funnel["original_native_candidate_count"])
    for key in STAGES:
        count = int(funnel["gate_counts"][key])
        if count < 0:
            raise ValueError("negative native eligibility count")
        record["gate_counts"][key] += count
        record["steps_any_gate"][key] += int(count > 0)
    if record["candidate_groups"] > 10000000:
        raise ValueError("A1.7 excessive original candidate count")


def run_original_branch(seed:int, label:str, frozen:dict, started:float) -> dict:
    if seed not in SEEDS or label not in ("b","h"):
        raise ValueError("only original exposed 544/545 B/H accepted")
    originals = physics._fusion_candidates
    original_experiment = pilot.IOExperiment
    aggregate = empty_count_record()
    per_period = {f"{a}-{b}":empty_count_record() for a,b in PERIODS}
    native_fusion_steps=[0]
    report_steps=[0]

    def native_hook(state, occupancy, config):
        rel=int(state.generation)-H0_GENERATION+1
        window=period_of(rel)
        result=native_fusion_eligibility_funnel(state,occupancy,config)
        if not result["fuse_flag_enabled"]:
            raise ValueError("original R2 unexpectedly disabled fusion")
        count_one(aggregate,result)
        count_one(per_period[window],result)
        # Always invoke ORIGINAL function and return its ORIGINAL list.
        output=originals(state,occupancy,config)
        if len(output)!=result["original_native_candidate_count"]:
            raise ValueError("original native candidate count mismatch")
        return output

    class NativeReplay(original_experiment):
        def _advance(self, anchors=()):
            m=super()._advance(anchors)
            rel=int(self.state.generation)-H0_GENERATION
            if not 1<=rel<=1000:
                raise ValueError("original R2 run escaped fixed horizon")
            native_fusion_steps[0]+=int(m.fusion_count)
            per_period[period_of(rel)]["actual_fusions"]+=int(m.fusion_count)
            aggregate["actual_fusions"]+=int(m.fusion_count)
            report_steps[0]+=1
            if rel%25==0:
                pilot.check_budget(started)
            return m

    with patch.object(physics,"_fusion_candidates",native_hook), patch.object(
        pilot,"IOExperiment",NativeReplay
    ):
        original=pilot.run_branch(seed,label,frozen,started)

    if report_steps[0]!=1000 or aggregate["native_steps"]!=1000:
        raise ValueError("native fusion observer did not cover every original physical step")
    if sum(p["actual_fusions"] for p in per_period.values())!=native_fusion_steps[0]:
        raise ValueError("native fusion metrics period accounting mismatch")
    if native_fusion_steps[0]!=0:
        raise ValueError("original accepted R2 A1.5 fusion=0 no longer reproduced")
    if original["reader_events"]!=EXPECTED[seed][0]:
        raise ValueError("original accepted selected-reader denominator changed")
    return {
        "original_h0_sha256":original["h0_sha256"],
        "original_r2_checkpoint_sha256":original["checkpoint_digests"],
        "native_selected_events_sha256":original["read_events_sha256"],
        "native_selected_free_events_sha256":original["free_events_sha256"],
        "funnel_whole_horizon":aggregate,
        "funnel_by_original_period":per_period,
        "_raw_reader_events":original["events"],
    }


def original_study(frozen:dict,started:float) -> dict:
    studies={}
    for seed in SEEDS:
        b=run_original_branch(seed,"b",frozen,started)
        h=run_original_branch(seed,"h",frozen,started)
        paired=paired_classify(b["_raw_reader_events"],h["_raw_reader_events"],
                               h0_generation=H0_GENERATION)
        counts=paired["counts"]
        if (counts.get("matched",0),counts.get("trace_diff",0),
            counts.get("changed_mask",0))!=EXPECTED[seed]:
            raise ValueError("native R2 original B/H paired event baseline changed")
        if counts.get("unmatched_topology",0) or counts.get("confounded_nontrace",0):
            raise ValueError("original source-nontrace topology is now confounded")
        if seed==544 and counts.get("H1_equal_source_recipient_latent",0)!=36:
            raise ValueError("original selected-mask no-op baseline changed")
        b.pop("_raw_reader_events")
        h.pop("_raw_reader_events")
        if seed==545 and b!=h:
            raise ValueError("original negative R2 B/H funnel or reader trace diverged")
        studies[str(seed)]={"role":"original_exposed_positive" if seed==544
                               else "original_exposed_negative",
                           "b":b,"h":h,"original_paired_reader_counts":{
                               k:int(counts.get(k,0)) for k in (
                                   "matched","trace_diff","changed_mask"
                               )}}
        pilot.check_budget(started)
    return studies


def report(*,source_sha:str) -> dict:
    if len(source_sha)!=40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("full PR source commit SHA required")
    frozen=load_frozen()
    if frozen["digest"]!=pilot.R2_FROZEN_DIGEST:
        raise ValueError("original R2 manifest SHA mismatch")
    original_config=profile(RATE)
    if (original_config.latent_operator!="masked_copy"
            or not original_config.fusion_enabled
            or original_config.fusion_bond_threshold!=32
            or original_config.fusion_velocity_threshold!=8):
        raise ValueError("original R2 source/native fusion physics conditions changed")
    started=time.perf_counter()
    first=original_study(frozen,started)
    second=original_study(frozen,started)
    if first!=second:
        raise ValueError("original native fusion funnel deterministic replay mismatch")
    result={
        "schema":SCHEMA,
        "issue":329,
        "source_sha":source_sha,
        "original_R2_engine_source_sha":pilot.R2_ORIGINAL_SOURCE,
        "original_R2_manifest_digest":pilot.R2_FROZEN_DIGEST,
        "original_R2_run":37950076024,
        "conditions":{"h0_native_generation":H0_GENERATION,
                      "positive_exposed":544,"negative_exposed":545,
                      "input_values_B_H":[66,8],"research_only_writer":"unit_add",
                      "trace_rate":RATE,"native_steps_after_h0":1000,
                      "snapshots":[1,10,100,250,500,1000],
                      "fusion_bond_threshold":32,"fusion_velocity_threshold":8,
                      "periods":[list(x) for x in PERIODS],
                      "original_physics_unchanged":True},
        "studies":first,
        "identical_replay":True,
        "independent_confirmation":False,"learning_claim":False,
        "environment":{"python":sys.implementation.name,
                       "version":sys.version.split()[0],
                       "max_rss_mib":pilot.sampled_max_rss_mib(),
                       "wall_seconds":round(time.perf_counter()-started,3)}
    }
    pilot.check_budget(started)
    result["digest"]=_digest(result)
    if len(json.dumps(result,sort_keys=True,separators=(",",":")).encode())>MAX_CASE_REPORT_BYTES:
        raise ValueError("A1.7 source evidence report exceeds retained size cap")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    value=report(source_sha=args.source_sha)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({
        "schema":SCHEMA,
        "source_sha":value["source_sha"],
        "totals":{seed:case["b"]["funnel_whole_horizon"]
                  for seed,case in value["studies"].items()},
        "learning_claim":False,
    },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
