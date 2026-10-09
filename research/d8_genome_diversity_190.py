"""D8 #190: non-mutating genome-diversity diagnostics; NOT selection policy.

A 128-slot population has 4 comparison strata. Same-genome seed evidence
increases slot count but never distinct-genome count. This module deliberately
does not call optimizer.step(), mutate selection, or read held-out results.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from math import exp, log
from pathlib import Path
from typing import Any, Iterable, Mapping

from search.evolution import SteadyStateOptimizer
from search.genome import UNIVERSE_GENOME_FIELDS
from core.population import CATEGORY_OPERATORS

ISSUE = 190
PER_CATEGORY = 32
TOTAL_SLOTS = 128
FIELDS = tuple(UNIVERSE_GENOME_FIELDS)
PROTOCOL = {
    "issue": ISSUE,
    "mode": "read_only_genotype_concentration_and_cohort_guard",
    "strata": list(CATEGORY_OPERATORS),
    "units": "per-category occupied authoritative slots, NOT independent seed tests",
    "genotype_key": "complete 11-field UniverseGenome only; category and seed are not genome fields",
    "metrics": ["unique_genomes", "dominant_genome_share", "shannon_effective_genomes",
                "inverse_simpson_effective_genomes", "mean_distinct_genome_field_mismatch",
                "fixed_fields", "allocation_reasons", "seed_count_within_genome"],
    "limitations": "single-time diversity != longitudinal collapse; no held-out efficacy, no overfit classification",
    "normal_role_constraints": "validation and heldout must be unselected and disjoint from training",
    "production_mutation": False,
    "learning_claim": False,
}


def digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def enforce_cohort_roles(roles: Mapping[str, Iterable[int]]) -> dict[str, Any]:
    """Check historical role leakage without claiming unseen evaluation."""
    allowed = ("training", "validation", "heldout")
    if set(roles) - set(allowed):
        raise ValueError("unrecognized evidence cohort role")
    sets: dict[str, set[int]] = {}
    for role in allowed:
        seeds = list(roles.get(role, ()))
        if any(type(value) is not int or value < 0 for value in seeds):
            raise ValueError("cohort seed must be a non-negative integer")
        if len(seeds) != len(set(seeds)):
            raise ValueError("duplicate seed within evidence role")
        sets[role] = set(seeds)
    for i, first in enumerate(allowed):
        for other in allowed[i+1:]:
            if sets[first] & sets[other]:
                raise ValueError("training/validation/heldout cohort leakage")
    return {
        "role_counts": {role:len(sets[role]) for role in allowed},
        "role_disjoint":True,
        "heldout_evaluable":bool(sets["heldout"]),
        "generalization_result":None,
    }


def _genotype(values: Mapping[str, Any]) -> tuple[int,...]:
    if set(values) != set(FIELDS):
        raise ValueError("genome keys must be exactly all 11 declared fields")
    if any(type(values[k]) is not int for k in FIELDS):
        raise ValueError("genome values must be integers")
    return tuple(values[k] for k in FIELDS)


def _entries(rows: Iterable[Mapping[str,Any]]) -> dict[str,list[dict]]:
    groups: dict[str,list[dict]]=defaultdict(list)
    for raw in rows:
        category = raw["category"]
        if category not in CATEGORY_OPERATORS:
            raise ValueError("unsupported category in diversity diagnostic")
        genome = _genotype(raw["genome"])
        seed=raw["seed"]
        if type(seed) is not int or seed < 0:
            raise ValueError("invalid real evidence seed")
        groups[category].append({
            "index":int(raw["index"]), "genome":genome, "seed":seed,
            "reason":str(raw.get("allocation_reason","unknown")),
            "parent":raw.get("parent_genome_key"),
        })
    if set(groups)!=set(CATEGORY_OPERATORS):
        raise ValueError("must have every declared comparison stratum")
    indexes=[x["index"] for members in groups.values() for x in members]
    if len(indexes)!=TOTAL_SLOTS or sorted(indexes)!=list(range(TOTAL_SLOTS)):
        raise ValueError("expected 128 distinct authoritative optimizer indices")
    for cat,members in groups.items():
        if len(members)!=PER_CATEGORY:
            raise ValueError(f"category {cat} must have 32 occupied slots")
    return groups


def report_rows(rows:Iterable[Mapping[str,Any]], *,optimizer_generation:int) -> dict[str,Any]:
    if type(optimizer_generation) is not int or optimizer_generation<0:
        raise ValueError("optimizer generation must be non-negative integer")
    groups=_entries(rows)
    category_results={}
    all_genomes=set()
    for cat in CATEGORY_OPERATORS:
        records=groups[cat]
        counts=Counter(item["genome"] for item in records)
        distinct=sorted(counts)
        all_genomes.update(distinct)
        n=len(records)
        weights=[v/n for v in counts.values()]
        shannon=round(exp(-sum(w*log(w) for w in weights)),10)
        simpson=round(1/sum(w*w for w in weights),10)
        frequencies=sorted(counts.values(),reverse=True)
        if len(distinct)>1:
            pairs=[
                sum(a!=b for a,b in zip(x,y))/len(FIELDS)
                for i,x in enumerate(distinct) for y in distinct[i+1:]
            ]
            mean_hamming=round(sum(pairs)/len(pairs),10)
        else:
            mean_hamming=None  # No distinct-genome pair exists; NOT distance 0.
        fixed=[field for field,values in zip(FIELDS,zip(*distinct))
               if len(set(values))==1]
        seed_counts = defaultdict(set)
        for x in records:
            seed_counts[x["genome"]].add(x["seed"])
        category_results[cat]={
            "occupied_slots":n,
            "unique_genomes":len(distinct),
            "genome_slot_frequencies":frequencies,
            "dominant_genome_share":round(frequencies[0]/n,10),
            "shannon_effective_genomes":shannon,
            "inverse_simpson_effective_genomes":simpson,
            "mean_distinct_genome_field_mismatch":mean_hamming,
            "fixed_fields":fixed,
            "fixed_field_count":len(fixed),
            "allocation_reasons":dict(sorted(Counter(x["reason"] for x in records).items())),
            "parent_provenance_present_slots":sum(x["parent"] is not None for x in records),
            "distinct_real_seeds_per_genome":sorted((len(x) for x in seed_counts.values()),reverse=True),
            "seed_reused_within_genome_count":sum(counts[key]-len(seeds) for key,seeds in seed_counts.items()),
        }
    out={
        "issue":ISSUE,"schema_version":1,"optimizer_generation":optimizer_generation,
        "strata":category_results,"global_pooled_unique_genomes":len(all_genomes),
        "total_authoritative_slots":TOTAL_SLOTS,
        "limitations":{
            "genetic_diversity_collapse_proven":False,
            "longitudinal_trend_measured":False,
            "overfitting_measured":False,
            "independent_heldout_tested":False,
            "interpretation":"read-only single-generation concentration; no generalization/learning inference",
        },
        "learning_claim":False,
    }
    out["digest"]=digest(out)
    return out


def optimizer_rows(opt:SteadyStateOptimizer)->list[dict[str,Any]]:
    return [{
        "index":s.index,"category":s.category,
        "genome":s.genome.to_dict(),"seed":s.seed,
        "allocation_reason":s.allocation_reason,
        "parent_genome_key":s.parent_genome_key,
    } for s in opt.slots]


def analyze(opt:SteadyStateOptimizer)->dict[str,Any]:
    # Pure view: no optimizer RNG, authoritative Universe or scheduling calls.
    return report_rows(optimizer_rows(opt), optimizer_generation=opt.generation)


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--base-seed",type=int,default=0)
    p.add_argument("--snapshot",type=Path,
                   help="optional real optimizer snapshot; no training or selected outcome is run")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if len(args.source_sha)!=40 or any(c not in "0123456789abcdef" for c in args.source_sha):
        p.error("source-sha must be an exact commit SHA")
    opt=(SteadyStateOptimizer.from_defaults(base_seed=args.base_seed) if args.snapshot is None
         else SteadyStateOptimizer.from_snapshot(json.loads(args.snapshot.read_text(encoding="utf-8"))))
    before=optimizer_rows(opt)
    result=analyze(opt)
    if before!=optimizer_rows(opt):
        raise ValueError("D8 observer mutated authoritative optimizer slot metadata")
    result["source_sha"]=args.source_sha
    result["source_kind"]="fresh_initial_population" if args.snapshot is None else "provided_existing_snapshot"
    result["protocol_digest"]=digest(PROTOCOL)
    result["evidence_role_validation"]=enforce_cohort_roles({})
    result.pop("digest")
    result["digest"]=digest(result)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({
        "digest":result["digest"],"generation":result["optimizer_generation"],
        "per_category":{cat:{"unique":v["unique_genomes"],
                             "dominant_share":v["dominant_genome_share"],
                             "effective":v["shannon_effective_genomes"]}
                        for cat,v in result["strata"].items()},
        "generalization_measured":False,
        "learning_claim":False,
    },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
