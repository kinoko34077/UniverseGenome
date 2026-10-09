"""D12 #202: D9 source-parity real Outer search eligibility witness.

This replays ONE already outcome-exposed D9 *search/training* seed.
Every source, schedule, 128 real slots and 4 native optimizer steps are
unchanged. Eligibility observer only reads accepted state after each step.
No independent heldout or genetic/teacher-learning claim.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from core.population import CATEGORY_OPERATORS
from search.evolution import SteadyStateOptimizer
from search.outer_search import prune_selection_indices
from research.d8_genome_diversity_190 import digest
from research import d9_real_evolved_diversity_193 as d9

ISSUE=202
FROZEN_BASE_SEED=16384
FROZEN_STEPS=4
D9_SOURCE_SHA="6c51b7006b673e7d38facfde82f6ce9e9363d28e"
D9_CASE_SHA256="3e6162f8af56d0c802b02fa7e73df567dd7365bafc09fb42917ceb1815caf721"
PROTOCOL={
    "issue":ISSUE,
    "outcome_exposed_original_seed":FROZEN_BASE_SEED,
    "exact_steps":FROZEN_STEPS,
    "D9_source_sha":D9_SOURCE_SHA,
    "D9_original_full_case_sha256":D9_CASE_SHA256,
    "gen_marks":[0,1,2,3,4],
    "native": "SteadyStateOptimizer.from_defaults and step; existing native SelectionRecord/prune helper",
    "source_immutable":True,
    "report_is_read_only":True,
    "independent_heldout_or_new_seeds":False,
    "learning_claim":False,
}


def classify_category(item:Mapping[str,Any])->str:
    if item["pruned_indices"]:
        return "ELIGIBLE_AT_CHECKPOINT"
    if item["absolute_failure_count"]:
        return "ABSOLUTE_FAILURE_WITHOUT_NATIVE_PRUNE_UNEXPECTED"
    if item["complete_nonfailure_count"]==0:
        return "GROWTH_HISTORY_INCOMPLETE"
    if all(value==0 for value in item["median_thresholds"]):
        return "ZERO_MEDIAN_OR_TOO_SMALL_THRESHOLD"
    return "NO_WEAK_CANDIDATE_DESPITE_NONZERO_THRESHOLD"


def eligibility_snapshot(opt:SteadyStateOptimizer)->dict[str,Any]:
    """Read exact native prune helpers without advancing state/scheduler."""
    before=digest(opt.to_snapshot())
    by_cat={}
    for _stratum,local in opt._comparison_strata():
        if not local:
            raise ValueError("D12 missing comparison stratum")
        category=local[0].category
        native=opt._selection_records(local)
        protected=opt._protected_indices(local)
        pruned=prune_selection_indices(native,protected=protected)
        eligible=[r for r in native if r.evidence_mature or r.absolute_failure]
        active=[r for r in eligible if not r.absolute_failure]
        complete=[r for r in active if len(r.growth_windows[-4:])==4]
        medians=(
            [median(int(x.growth_windows[-4+i]).bit_count() for x in complete)
             for i in range(4)]
            if complete else None
        )
        thresholds=([int(m)>>1 for m in medians] if medians is not None else [])
        rows=[]
        for rec,slot in zip(native,local):
            if rec.index!=slot.index:
                raise ValueError("native candidate order mismatch")
            rows.append({
                "index":rec.index,
                "growth_windows":list(rec.growth_windows),
                "evidence_count":rec.evidence_count,
                "evidence_mature":rec.evidence_mature,
                "absolute_failure":rec.absolute_failure,
                "absolute_failure_reason":slot.absolute_failure_reason,
                "response_windows":list(slot.response_windows),
                "short_health_windows":list(slot.short_health_windows),
            })
        item={
            "occupied":len(local),
            "qualified_or_failed_count":len(eligible),
            "complete_nonfailure_count":len(complete),
            "absolute_failure_count":sum(x.absolute_failure for x in native),
            "growth_window_length_histogram":dict(sorted(Counter(
                len(x.growth_windows) for x in native
            ).items())),
            "native_protected_indices":sorted(protected),
            "native_pruned_indices":sorted(pruned),
            "pruned_indices":sorted(pruned),
            "median_bitcounts":medians,
            "median_thresholds":thresholds,
            "slot_growth_and_failure_evidence":rows,
        }
        item["gate"]=classify_category(item)
        by_cat[category]=item
    if set(by_cat)!=set(CATEGORY_OPERATORS) or any(c["occupied"]!=32 for c in by_cat.values()):
        raise ValueError("D12 native 4x32 category invariant failed")
    after=digest(opt.to_snapshot())
    if before!=after:
        raise AssertionError("D12 observer changed authoritative optimizer")
    return {"generation":opt.generation,"state_digest":before,"strata":by_cat}


def real_replay()->dict[str,Any]:
    opt=SteadyStateOptimizer.from_defaults(base_seed=FROZEN_BASE_SEED)
    source_records=[]
    eligibility=[]
    previous=None
    for index in range(FROZEN_STEPS+1):
        step=None if index==0 else opt.step()
        if opt.generation!=index or (step is not None and step["generation"]!=index):
            raise ValueError("D12 real native step count drift")
        # D9 _checkpoint and group keys must remain byte-for-byte unchanged.
        d9_record=d9._checkpoint(opt,step_data=step,previous=previous)
        source_records.append(d9_record)
        previous=d9._group_keys(opt)
        sel=eligibility_snapshot(opt)
        if sel["state_digest"]!=d9_record["optimizer_state_sha256"]:
            raise AssertionError("D12 read-only observer diverged from native D9 checkpoint")
        if step is not None:
            if step["replacement_count"]!=0 or step["pruned_count"]!=0:
                raise AssertionError("D9 parity unexpectedly introduced native replacement/prune")
            if any(v["pruned_indices"] for v in sel["strata"].values()):
                raise AssertionError("post-evaluation eligibility differs from frozen zero-prune D9")
        eligibility.append(sel)
    d9_report={
        "issue":d9.ISSUE,"schema_version":1,
        "base_seed":FROZEN_BASE_SEED,
        "protocol_digest":digest(d9.PROTOCOL),
        "records":source_records,
        "risk":d9.classify_trajectory(source_records),
        "learning_claim":False,
        "source_sha":D9_SOURCE_SHA,
    }
    matched_digest=digest(d9_report)
    if matched_digest!=D9_CASE_SHA256:
        raise AssertionError(
            f"D12 real replay NOT identical to original D9: {matched_digest} != {D9_CASE_SHA256}"
        )
    result={
        "issue":ISSUE,"schema_version":1,"protocol_digest":digest(PROTOCOL),
        "D9_source_sha":D9_SOURCE_SHA,
        "D9_exact_original_case_sha256":D9_CASE_SHA256,
        "D9_parity_verified":True,
        "exposed_search_seed":FROZEN_BASE_SEED,
        "generations":[x["generation"] for x in eligibility],
        "observed_selection_eligibility":eligibility,
        "summary":{
            "observed_native_replacements":0,
            "observed_native_pruned":0,
            "native_gate_by_category":{
                cat:[point["strata"][cat]["gate"] for point in eligibility]
                for cat in CATEGORY_OPERATORS
            },
            "D9_real_no_prune_causal_conditions_observed":True,
            "generalizes_across_seeds":False,
            "independent_validation_or_heldout":False,
            "learning_claim":False,
        },
    }
    result["digest"]=digest(result)
    return result


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if len(args.source_sha)!=40 or any(ch not in "0123456789abcdef" for ch in args.source_sha):
        p.error("source-sha must be exact 40 hex")
    result=real_replay()
    result["source_sha"]=args.source_sha
    result.pop("digest")
    result["digest"]=digest(result)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({"digest":result["digest"],"D9_parity_verified":True,
        "native_gate_by_category":result["summary"]["native_gate_by_category"],
        "full_native_gen0_to4":result["generations"],
        "independent_heldout":False,"learning_claim":False},
        sort_keys=True),flush=True)


if __name__=="__main__":
    main()
