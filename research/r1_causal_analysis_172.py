"""R1 #172 exact-head bounded, artifact-authenticated causal run & analysis."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from math import comb
from pathlib import Path

from core.experiment import IOExperiment
from research.phase_g_memory_search_159 import _digest, _load_protocol
from research.r1_causal_isolation_172 import (
    CHECKPOINTS, FACTORS, ISSUE, RATES, evaluate_seed, h0_snapshots,
    load_frozen, profile,
)
from research.transduction_audit_120 import canonical_digest, clone_state

SHARDS = 8
SHARD_SIZE = 4
HORIZON = 1000


def _seeds(frozen):
    return list(frozen["positive_seeds"]) + list(frozen["negative_seeds"])


def raw_checkpoints(snapshot: dict, *, rate: int) -> dict[str, str]:
    config = profile(rate)
    state = clone_state(snapshot, config)
    experiment = IOExperiment(state, experiment=_load_protocol())
    records = {}
    for generation in range(1, HORIZON + 1):
        experiment._advance(())
        if generation in CHECKPOINTS:
            records[str(generation)] = canonical_digest(state.to_snapshot())
    return records


def validated_case(seed: int, rate: int, source_sha: str, frozen: dict) -> dict:
    if seed not in _seeds(frozen) or rate not in RATES:
        raise ValueError("unfrozen seed or rate")
    if len(source_sha) != 40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("exact source SHA required")
    first = evaluate_seed(seed, rate=rate, frozen=frozen)
    if first["digest"] != _digest({k:v for k,v in first.items() if k != "digest"}):
        raise ValueError("R1 internal case digest invalid")
    repeat = evaluate_seed(seed, rate=rate, frozen=frozen)
    if repeat != first:
        raise ValueError("deterministic intervention replay mismatch")
    h0 = h0_snapshots(seed, rate=rate)
    if first["h0"] != {k:canonical_digest(v) for k,v in h0.items()}:
        raise ValueError("h0 snapshot mismatch")
    if rate == frozen["qualification_rate"]:
        old = frozen["h0_evidence"][str(seed)]
        for branch in ("b","h","control"):
            if first["h0"][branch] != old[f"{branch}_digest"]:
                raise ValueError("qualified h0 changed")
    for branch in ("b", "h"):
        raw = raw_checkpoints(h0[branch], rate=rate)
        observed = first["factors"]["sham"]["checkpoints"]
        for k in raw:
            if raw[k] != observed[k][f"{branch}_digest"]:
                raise ValueError("raw/pass-through authoritative-state mismatch")
    for factor in ("sham",)+FACTORS:
        for k, item in first["factors"][factor]["checkpoints"].items():
            if first["role"] == "negative" and item["b_digest"] != item["h_digest"]:
                raise ValueError("negative sentinel became B/H-distinct")
    # A positive is only h0-qualified, NOT guaranteed h1000 success.
    if first["role"] == "positive" and not first["initial_trace_distinct"]:
        raise ValueError("positive lacks h0 trace difference")
    if first["role"] == "negative" and first["initial_global_distinct"]:
        raise ValueError("negative lacks h0 equality")
    output = {
        "schema_version": 1, "issue": ISSUE, "phase": "R1-confirmatory",
        "seed": seed, "role": first["role"], "rate": rate,
        "source_sha": source_sha, "frozen_digest": frozen["digest"],
        "qualification_digest": frozen["qualification_digest"],
        "exact_replay": True, "raw_sham_parity": True,
        "negative_clean": True, "heldout_max_horizon": 0,
        "result": first, "learning_claim": False,
    }
    output["digest"] = _digest(output)
    return output


def shard_cases(frozen: dict, shard: int):
    if not 0 <= shard < SHARDS:
        raise ValueError("invalid R1 shard")
    seeds = _seeds(frozen)[shard*SHARD_SIZE:(shard+1)*SHARD_SIZE]
    if len(seeds)!=SHARD_SIZE:
        raise ValueError("incomplete frozen R1 shard")
    return seeds


def run_shard(shard: int, rate: int, source_sha: str, out: Path):
    frozen = load_frozen()
    if rate not in RATES:
        raise ValueError("invalid R1 rate")
    out.mkdir(parents=True, exist_ok=True)
    for seed in shard_cases(frozen, shard):
        result = validated_case(seed, rate, source_sha, frozen)
        target = out / f"case-{rate}-{seed}.json"
        target.write_text(json.dumps(result, sort_keys=True, separators=(",",":"))+"\n",
                          encoding="utf-8")
        print(json.dumps({
            "seed":seed,"rate":rate,"role":result["role"],
            "sham_h1000":result["result"]["factors"]["sham"]["checkpoints"]["1000"]["trace_distinct"],
            "digest":result["digest"]
        },sort_keys=True), flush=True)


def _mcnemar_one_sided(rescue: int, harm: int) -> float:
    n = rescue + harm
    return sum(comb(n,k) for k in range(rescue,n+1))/(2**n) if n else 1.0


def _wilson95(successes: int, total: int) -> list[float]:
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("invalid Wilson denominator")
    z = 1.959963984540054
    p = successes / total
    denom = 1 + z*z/total
    center = (p + z*z/(2*total)) / denom
    margin = z * ((p*(1-p)/total + z*z/(4*total*total)) ** 0.5) / denom
    return [max(0., center-margin), min(1., center+margin)]


def _holm(pvals: dict[str,float]) -> dict[str,float]:
    ordered = sorted(pvals,key=lambda k:(pvals[k],k))
    adjusted = {}
    current = 0.
    for idx, key in enumerate(ordered):
        current = max(current, min(1., pvals[key] * (len(ordered)-idx)))
        adjusted[key] = current
    return adjusted


def aggregate(out_dir: Path, source_sha: str) -> dict:
    frozen = load_frozen()
    seeds = _seeds(frozen)
    expected = {f"case-{rate}-{seed}.json" for rate in RATES for seed in seeds}
    actual = {p.name for p in out_dir.glob("case-*.json")}
    if actual != expected:
        raise ValueError(f"incomplete/extraneous R1 cohort: missing {len(expected-actual)}, excess {len(actual-expected)}")
    cases = {}
    case_hashes = {}
    for rate in RATES:
        cases[rate] = {}
        for seed in seeds:
            f = out_dir / f"case-{rate}-{seed}.json"
            item = json.loads(f.read_text(encoding="utf-8"))
            recorded = item.pop("digest",None)
            if _digest(item) != recorded:
                raise ValueError("R1 case checksum mismatch")
            item["digest"] = recorded
            role = "positive" if seed in frozen["positive_seeds"] else "negative"
            expected_fields = {
                "source_sha":source_sha,"seed":seed,"rate":rate,
                "role":role,"frozen_digest":frozen["digest"],
                "qualification_digest":frozen["qualification_digest"],
                "exact_replay":True,"raw_sham_parity":True,
                "negative_clean":True,"learning_claim":False,
                "heldout_max_horizon":0
            }
            for key,val in expected_fields.items():
                if item.get(key)!=val:
                    raise ValueError(f"R1 protocol violation {rate}/{seed}/{key}")
            if item["result"].get("digest") != _digest({
                k:v for k,v in item["result"].items() if k!="digest"
            }):
                raise ValueError("R1 nested checksum mismatch")
            cases[rate][seed] = item
            case_hashes[f"{rate}/{seed}"] = recorded
    results = {}
    for rate in RATES:
        outcomes = {}
        for factor in FACTORS:
            positives = [cases[rate][s]["result"]["outcomes"][factor]
                         for s in frozen["positive_seeds"]]
            negatives = [cases[rate][s]["result"] for s in frozen["negative_seeds"]]
            rescues = sum(a["rescue_only"] and a["factor_exposure"] for a in positives)
            harms = sum(a["sham_only"] for a in positives)
            naive_rescues = sum(a["rescue_only"] for a in positives)
            downstream = sum(a["physical_latent_change"] for a in positives)
            teacher_interaction = sum(a["teacher_latent_response_interaction"] and a["factor_exposure"]
                                      for a in positives)
            clean_sentinels = sum(
                all(not x["trace_distinct"] for x in case["factors"][factor]["checkpoints"].values())
                and all(case["factors"][factor]["checkpoints"][k]["b_digest"]
                        == case["factors"][factor]["checkpoints"][k]["h_digest"]
                        for k in case["factors"][factor]["checkpoints"])
                for case in negatives
            )
            outcomes[factor] = {
                "rescue_with_mechanism_exposure":rescues,
                "rescue_regardless_of_exposure":naive_rescues,
                "sham_only_harm":harms,
                "paired_one_sided_p":_mcnemar_one_sided(rescues,harms),
                "latent_affected_cases":downstream,
                "teacher_latent_interaction_with_exposure":teacher_interaction,
                "negative_clean":clean_sentinels,
                "rescue_only_wilson95":_wilson95(naive_rescues,24),
                "sham_only_wilson95":_wilson95(harms,24),
                "positive_denominator":24,"negative_denominator":8,
            }
        if rate == 256:
            family = {factor:outcomes[factor]["paired_one_sided_p"]
                      for factor in FACTORS if factor!="read_bonus_off"}
            holm = _holm(family)
            for factor in family:
                outcomes[factor]["holm_p"] = holm[factor]
                outcomes[factor]["support_gate"] = (
                    outcomes[factor]["rescue_with_mechanism_exposure"]>=8
                    and outcomes[factor]["sham_only_harm"]<=2
                    and holm[factor]<0.05 and outcomes[factor]["negative_clean"]==8
                )
            outcomes["read_bonus_off"]["read_physical_effect_gate"] = (
                outcomes["read_bonus_off"]["teacher_latent_interaction_with_exposure"]>=8
                and outcomes["read_bonus_off"]["negative_clean"]==8
            )
        results[str(rate)] = outcomes
    accepted = [f for f in FACTORS if f!="read_bonus_off" and results["256"][f]["support_gate"]]
    route = ("UNRESOLVED" if not accepted else
             "CAUSE-SUPPORTED" if len(accepted)==1 else "MULTICAUSAL")
    summary = {
        "schema_version":1,"issue":ISSUE,"phase":"R1","source_sha":source_sha,
        "frozen_digest":frozen["digest"],
        "qualification_digest":frozen["qualification_digest"],
        "cases_total":len(case_hashes),"case_hashes":case_hashes,
        "outcomes":results,
        "causal_loss_route":route,
        "cause_supported_factors":accepted,
        "read_coupling_secondary_only":results["256"]["read_bonus_off"]["read_physical_effect_gate"],
        "meaning_limits":[
            "h0 qualified, independently selected from previously unused seeds; no outcome-based inclusion",
            "post-h0 write-off probes all generic writes, not uniquely saturation",
            "free relay adds local legal repair, not proof FREE is unique sufficient cause",
            "read effect is physical latent coupling, NOT L4 input-conditioned recall",
            "validity PASS and scientific success distinct; no learning claim or R2 entry authorization"
        ],
        "heldout_max_horizon":0,"learning_claim":False
    }
    summary["digest"] = _digest(summary)
    return summary


def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run-shard",type=int)
    mode.add_argument("--aggregate-dir",type=Path)
    parser.add_argument("--rate",type=int,default=256)
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--output-dir",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.run_shard is not None:
        if args.output_dir is None:
            parser.error("--output-dir required")
        run_shard(args.run_shard,args.rate,args.source_sha,args.output_dir)
    else:
        if args.output is None:
            parser.error("--output required")
        summary=aggregate(args.aggregate_dir,args.source_sha)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(summary,sort_keys=True, separators=(",",":"))+"\n",
                               encoding="utf-8")
        print(json.dumps(summary,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
