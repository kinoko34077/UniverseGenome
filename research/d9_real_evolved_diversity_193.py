"""D9 #193: four actual default Outer search steps, diagnostic-only time series.

Evidence is two exploratory search/training seeds, not independent held-out
generalization, and not validation for any physical slow-memory candidate.
Never change accepted optimizer fitness/selection/pruning or production world.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from search.evolution import SteadyStateOptimizer
from core.population import CATEGORY_OPERATORS
from research.d8_genome_diversity_190 import analyze, digest, optimizer_rows

ISSUE=193
START_SEEDS=(16384,32768)
STEPS=4
GENERATION_MARKERS=(0,1,2,3,4)
PROTOCOL={
    "issue":ISSUE,
    "base_seeds":list(START_SEEDS),
    "optimizer_default":"accepted SteadyStateOptimizer.from_defaults; no adjusted physics, experiment or selection",
    "real_optimizer_steps":STEPS,
    "generation_markers":list(GENERATION_MARKERS),
    "strata":list(CATEGORY_OPERATORS),
    "metrics":"D8 per-category 11-field genotype distribution and effective counts",
    "source":"disposable in-process optimizer only",
    "replay":"full deterministic second run for base seed16384; exclude throughput timer",
    "classification":"four steps cannot prove long-term genetics or unseen teacher/input generalization",
    "role":"exploratory search/training, never heldout",
    "heldout_generalization_measured":False,
    "learning_claim":False,
}


def _group_keys(opt:SteadyStateOptimizer)->dict[str,set[str]]:
    result={cat:set() for cat in CATEGORY_OPERATORS}
    for slot in opt.slots:
        result[slot.category].add(slot.genome_key)
    return result


def _checkpoint(opt:SteadyStateOptimizer, *, step_data:dict[str,Any]|None, previous:dict[str,set[str]]|None)->dict[str,Any]:
    pre=optimizer_rows(opt)
    stat=analyze(opt)
    if pre!=optimizer_rows(opt):
        raise ValueError("D9 diagnostic mutated optimizer metadata")
    if stat["total_authoritative_slots"]!=128 or any(v["occupied_slots"]!=32 for v in stat["strata"].values()):
        raise ValueError("D9 corrupted canonical four-stratum population")
    now=_group_keys(opt)
    births={cat:len(now[cat]-(previous[cat] if previous is not None else now[cat])) for cat in CATEGORY_OPERATORS}
    losses={cat:len((previous[cat] if previous is not None else now[cat])-now[cat]) for cat in CATEGORY_OPERATORS}
    replacement_count=0 if step_data is None else step_data["replacement_count"]
    replacements=[] if step_data is None else [{
        "index":r["index"],"category":r["category"],"reason":r["reason"],
        "mutation_field":r["mutation_field"],"allocation_reason":r["allocation_reason"],
        "group_count":r["group_count"],
    } for r in step_data["replacements"]]
    if replacement_count!=len(replacements):
        raise ValueError("D9 real mutation/replacement event count mismatch")
    if any(r["category"] not in CATEGORY_OPERATORS for r in replacements):
        raise ValueError("D9 cross-stratum replacement")
    return {
        "generation":opt.generation,
        "optimizer_state_sha256":digest(opt.to_snapshot()),
        "strata":stat["strata"],
        "global_pooled_unique_genomes":stat["global_pooled_unique_genomes"],
        "births":births,"losses":losses,
        "replacement_count":replacement_count,
        "pruned_count":0 if step_data is None else step_data["pruned_count"],
        "mutation_fields":dict(sorted(Counter(
            r["mutation_field"] for r in replacements if r["mutation_field"] is not None
        ).items())),
        "allocation_reasons":dict(sorted(Counter(r["allocation_reason"] for r in replacements).items())),
        "replacements":replacements,
    }


def classify_trajectory(records:list[dict[str,Any]])->dict[str,Any]:
    if len(records)!=STEPS+1 or [r["generation"] for r in records]!=list(GENERATION_MARKERS):
        raise ValueError("D9 actual generation record incomplete")
    total=sum(r["replacement_count"] for r in records)
    mutation=sum(sum(1 for v in r["replacements"] if v["allocation_reason"]=="mutation_child") for r in records)
    fixed=[(r["generation"],cat) for r in records[1:] for cat,v in r["strata"].items()
           if v["unique_genomes"]==1]
    concentration=[(r["generation"],cat) for r in records[1:] for cat,v in r["strata"].items()
                   if v["dominant_genome_share"]>records[0]["strata"][cat]["dominant_genome_share"]]
    label=("SELECTION_NOT_EXPOSED" if total==0 else
           "FIXATION_OBSERVED_IN_SHORT_RUN" if fixed else
           "CONCENTRATION_OBSERVED_IN_SHORT_RUN" if concentration else
           "NO_CONCENTRATION_OBSERVED_IN_BOUNDED_STEPS")
    return {
        "observed_replacements":total,
        "observed_mutation_child_allocations":mutation,
        "genotype_fixation_windows":fixed,
        "increased_dominance_windows":concentration,
        "classification":label,
        "long_term_diversity_guaranteed":False,
        "overfitting_measured":False,
        "independent_heldout_tested":False,
    }


def trajectory(base_seed:int)->dict[str,Any]:
    if base_seed not in START_SEEDS:
        raise ValueError("D9 seed not preregistered")
    opt=SteadyStateOptimizer.from_defaults(base_seed=base_seed)
    records=[]
    previous=None
    for index in range(STEPS+1):
        step=None if index==0 else opt.step()
        if opt.generation!=index or (step is not None and step["generation"]!=index):
            raise ValueError("D9 actual optimizer step sequence drift")
        record=_checkpoint(opt,step_data=step,previous=previous)
        records.append(record)
        previous=_group_keys(opt)
    result={
        "issue":ISSUE,
        "schema_version":1,
        "base_seed":base_seed,
        "protocol_digest":digest(PROTOCOL),
        "records":records,
        "risk":classify_trajectory(records),
        "learning_claim":False,
    }
    result["digest"]=digest(result)
    return result



def aggregate(folder:Path,source_sha:str)->dict[str,Any]:
    if len(source_sha)!=40 or any(ch not in "0123456789abcdef" for ch in source_sha):
        raise ValueError("D9 invalid source SHA")
    expected=("run-16384-1.json","run-16384-2.json","run-32768-1.json")
    paths=sorted(p.name for p in folder.glob("run-*.json"))
    if paths!=sorted(expected):
        raise ValueError("D9 exactly three frozen runs required")
    runs={}
    for name in expected:
        case=json.loads((folder/name).read_text(encoding="utf-8"))
        checksum=case.pop("digest",None)
        if digest(case)!=checksum or case["source_sha"]!=source_sha or case["protocol_digest"]!=digest(PROTOCOL):
            raise ValueError("D9 source/frozen protocol/report checksum drift")
        if case["base_seed"]!=int(name.split("-")[1]) or case["risk"]["overfitting_measured"] or case["learning_claim"]:
            raise ValueError("D9 roles or overfit classification drift")
        if len(case["records"])!=5 or [c["generation"] for c in case["records"]]!=[0,1,2,3,4]:
            raise ValueError("D9 incomplete actual four-step optimizer")
        case["digest"]=checksum
        runs[name]=case
    if runs["run-16384-1.json"]!=runs["run-16384-2.json"]:
        raise ValueError("D9 duplicate native optimizer replay mismatch")
    scores={str(seed):runs["run-"+str(seed)+"-1.json"]["risk"]
            for seed in START_SEEDS}
    out={
        "schema_version":1,"issue":ISSUE,"source_sha":source_sha,
        "protocol_digest":digest(PROTOCOL),
        "cases":{name:case["digest"] for name,case in runs.items()},
        "exact_duplicate_replay":True,
        "outcomes":scores,
        "classification":"EXPLORATORY_SHORT_EVOLVED_SERIES_NO_HELDOUT_INFERENCE",
        "overfitting_measured":False,
        "long_term_diversity_guaranteed":False,
        "learning_claim":False,
    }
    out["digest"]=digest(out)
    return out


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--base-seed",type=int)
    p.add_argument("--aggregate",type=Path)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if len(args.source_sha)!=40 or any(ch not in "0123456789abcdef" for ch in args.source_sha):
        p.error("source-sha must be 40 hex characters")
    if (args.base_seed is None)==(args.aggregate is None):
        p.error("exactly one of --base-seed or --aggregate")
    if args.aggregate is not None:
        report=aggregate(args.aggregate,args.source_sha)
        output={"digest":report["digest"],"outcomes":report["outcomes"],
                "replay":report["exact_duplicate_replay"],
                "classification":report["classification"]}
    else:
        report=trajectory(args.base_seed)
        report["source_sha"]=args.source_sha
        report.pop("digest")
        report["digest"]=digest(report)
        output={"base_seed":args.base_seed,"digest":report["digest"],
                "risk":report["risk"],
                "per_category":{k:[{"generation":r["generation"],
                                    "unique":r["strata"][k]["unique_genomes"],
                                    "dominant":r["strata"][k]["dominant_genome_share"],
                                    "effective":r["strata"][k]["shannon_effective_genomes"]}
                                   for r in report["records"]]
                                for k in CATEGORY_OPERATORS}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps(output,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
