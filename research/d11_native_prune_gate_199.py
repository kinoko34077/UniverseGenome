"""D11 #199: native Outer pruning gate conditions on frozen synthetic evidence.

No actual optimizer stepping, new seed search, selection-policy alteration,
heldout generalization, or teacher-content/memory claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from core.population import CATEGORY_OPERATORS
from search.outer_search import (
    SelectionRecord, protected_selection_indices, prune_selection_indices,
    select_prune_target_index, select_parent_index,
)
from research.d8_genome_diversity_190 import digest

ISSUE=199
CATEGORY_SIZE=32
GROUP_SIZE=4
PREDECLARED={
    "issue":ISSUE,
    "mode":"synthetic SelectionRecord fixtures for native prune eligibility; NOT evolved trajectory",
    "strata":list(CATEGORY_OPERATORS),
    "slots_per_stratum":CATEGORY_SIZE,
    "genotype_evidence_groups":8,
    "slots_per_group":GROUP_SIZE,
    "zero_window":0,
    "positive_window":3,
    "cases":["F0_flat_complete","F1_flat_incomplete","F2_skew_positive_median","F3_absolute_failure"],
    "learning_claim":False,
    "genetic_diversity_under_selection_measured":False,
    "overfitting_measured":False,
}


def _records(category:str,mode:str)->tuple[SelectionRecord,...]:
    if category not in CATEGORY_OPERATORS:
        raise ValueError("unexpected category")
    if mode not in PREDECLARED["cases"]:
        raise ValueError("unfrozen scenario")
    offset=CATEGORY_OPERATORS.index(category)*CATEGORY_SIZE
    records=[]
    for local in range(CATEGORY_SIZE):
        group=local//GROUP_SIZE
        absolute=(mode=="F3_absolute_failure" and category==CATEGORY_OPERATORS[0] and local==31)
        if mode=="F1_flat_incomplete":
            windows=(0,0,0)
        elif mode=="F2_skew_positive_median" and category==CATEGORY_OPERATORS[0] and local!=31:
            windows=(3,3,3,3)
        else:
            windows=(0,0,0,0)
        records.append(SelectionRecord(
            index=offset+local,
            group_key=(category,group),
            objective_key=(group,),
            evidence_count=4,
            candidate_tie_key=f"genome-{group}",
            growth_windows=windows,
            absolute_failure=absolute,
            evidence_mature=True,
        ))
    return tuple(records)


def _case(mode:str)->dict[str,Any]:
    by_cat={}
    for category in CATEGORY_OPERATORS:
        records=_records(category,mode)
        protected=protected_selection_indices(records,minimum_evidence=4)
        pruned=prune_selection_indices(records,protected=protected)
        target=select_prune_target_index(records,pruned) if pruned else None
        parent=(select_parent_index(records,excluded_index=target,minimum_evidence=4)
                if target is not None else None)
        by_cat[category]={
            "protected_indices":sorted(protected),
            "pruned_indices":sorted(pruned),
            "target_index":target,
            "parent_index":parent,
            "four_window_evidence_count":sum(len(x.growth_windows)==4 for x in records),
            "absolute_failures":sum(x.absolute_failure for x in records),
            "medians_flagbit_count":(
                0 if mode!="F2_skew_positive_median" or category!=CATEGORY_OPERATORS[0]
                else 2
            ),
        }
    return by_cat


def evaluate()->dict[str,Any]:
    results={mode:_case(mode) for mode in PREDECLARED["cases"]}
    first=CATEGORY_OPERATORS[0]
    for mode,details in results.items():
        for category,record in details.items():
            if len(record["protected_indices"])!=4:
                raise AssertionError("accepted native top 1/8 protection drift")
            expected=([31] if category==first and mode in (
                "F2_skew_positive_median","F3_absolute_failure"
            ) else [])
            if record["pruned_indices"]!=expected:
                raise AssertionError(f"{mode}/{category}: frozen native pruning eligibility unexpectedly changed")
            if expected:
                if record["target_index"]!=31 or record["parent_index"]!=0:
                    raise AssertionError("native within-category target/parent selection drift")
            elif record["target_index"] is not None or record["parent_index"] is not None:
                raise AssertionError("no-prune fixture fabricated a real replacement")
    result={
        "issue":ISSUE,"schema_version":1,
        "protocol_digest":digest(PREDECLARED),
        "native_selection_cases":results,
        "classification":"CONDITIONAL_ZERO_MEDIAN_PRUNE_GATE_CONFIRMED_D9_ACTUAL_CAUSE_NOT_IDENTIFIED",
        "limits":{
            "synthetic_fixtures_only":True,
            "D9_actual_growth_windows_observed":False,
            "D9_no_replacement_unique_cause_proven":False,
            "actual_genetic_selection_pressure_observed_here":False,
            "real_overfit_or_heldout_measured":False,
            "learning_claim":False,
        },
        "source_semantics":{
            "complete_flat_median_zero_prevents_growth_only_prune":True,
            "three_growth_windows_insufficient":True,
            "positive_category_median_exposes_worse_unprotected_candidate":True,
            "absolute_failure_exposes_candidate_even_when_growth_flat":True,
        },
    }
    result["digest"]=digest(result)
    return result


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if len(args.source_sha)!=40 or any(c not in "0123456789abcdef" for c in args.source_sha):
        p.error("source-sha must be exact SHA-40")
    result=evaluate()
    result["source_sha"]=args.source_sha
    result.pop("digest")
    result["digest"]=digest(result)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({
        "digest":result["digest"],"classification":result["classification"],
        "case_targets":{name:{cat:v["target_index"] for cat,v in by_cat.items()}
                        for name,by_cat in result["native_selection_cases"].items()},
        "limits":result["limits"],
    },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
