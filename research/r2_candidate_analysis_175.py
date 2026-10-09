"""R2 #175 sealed exact-source shard execution and predeclared 24-case analysis."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from math import comb
from pathlib import Path

from research.phase_g_memory_search_159 import _digest
from research.r2_write_rules_175 import (
    ISSUE, MANIFEST, NEGATIVE_COUNT, POSITIVE_COUNT, PROFILES,
    RATE, HORIZONS, load_frozen, validated_seed,
)

SHARDS = 8
PER_SHARD = 3


def roster(frozen: dict) -> list[int]:
    return frozen["positive_seeds"] + frozen["negative_seeds"]


def validate_source(source_sha: str):
    if len(source_sha) != 40 or any(ch not in "0123456789abcdef" for ch in source_sha):
        raise ValueError("R2 exact source SHA required")


def produce_shard(index: int, source_sha: str) -> dict:
    validate_source(source_sha)
    frozen = load_frozen()
    if index not in range(SHARDS):
        raise ValueError("R2 predeclared shard outside 0..7")
    seeds = roster(frozen)[index*PER_SHARD:(index+1)*PER_SHARD]
    if len(seeds) != PER_SHARD:
        raise ValueError("R2 frozen case allocation mismatch")
    cases = [validated_seed(seed, frozen) for seed in seeds]
    result = {
        "schema_version": 1, "issue": ISSUE, "source_sha": source_sha,
        "shard": index, "frozen_digest": frozen["digest"], "cases": cases,
        "case_count": len(cases), "learning_claim": False,
    }
    result["digest"] = _digest(result)
    return result


def exact_one_sided(rescues: int, harms: int) -> float:
    discordant = rescues + harms
    if not discordant:
        return 1.0
    return sum(comb(discordant,k) for k in range(rescues,discordant+1))/(2**discordant)


def aggregate(folder: Path, source_sha: str) -> dict:
    validate_source(source_sha)
    frozen = load_frozen()
    shards: dict[int, dict] = {}
    observed: dict[int, dict] = {}
    paths = sorted(folder.glob("shard-*.json"))
    if len(paths) != SHARDS:
        raise ValueError(f"missing or extra R2 shard artifacts: {len(paths)} != {SHARDS}")
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        checksum = report.pop("digest",None)
        if _digest(report) != checksum:
            raise ValueError("R2 shard checksum mismatch")
        report["digest"] = checksum
        if (report.get("issue") != ISSUE or report.get("source_sha") != source_sha
                or report.get("frozen_digest") != frozen["digest"]
                or report.get("shard") in shards or report.get("case_count") != PER_SHARD):
            raise ValueError("R2 shard metadata/partition drift")
        idx = report["shard"]
        if idx not in range(SHARDS):
            raise ValueError("R2 shard outside preregistered range")
        expected = roster(frozen)[idx*PER_SHARD:(idx+1)*PER_SHARD]
        if [case.get("seed") for case in report["cases"]] != expected:
            raise ValueError("R2 shard roster mismatch")
        shards[idx] = report
        for case in report["cases"]:
            sha = case.pop("digest",None)
            if _digest(case) != sha or case.get("frozen_digest") != frozen["digest"]:
                raise ValueError("R2 case checksum or provenance mismatch")
            case["digest"] = sha
            if case["seed"] in observed:
                raise ValueError("R2 duplicate frozen seed")
            observed[case["seed"]] = case

    if len(observed) != POSITIVE_COUNT + NEGATIVE_COUNT or list(
        seed for idx in sorted(shards) for seed in (c["seed"] for c in shards[idx]["cases"])
    ) != roster(frozen):
        raise ValueError("R2 exact cohort incomplete or reordered")
    positive = [observed[s] for s in frozen["positive_seeds"]]
    negative = [observed[s] for s in frozen["negative_seeds"]]
    for case in positive:
        if case["role"] != "positive" or not case["h0_trace_distinct"]:
            raise ValueError("R2 positive role corrupted")
    for case in negative:
        if case["role"] != "negative" or case["h0_trace_distinct"]:
            raise ValueError("R2 negative role corrupted")
        for candidate in PROFILES:
            for ck in case["candidates"][candidate]["checkpoints"].values():
                if ck["b_digest"] != ck["h_digest"]:
                    raise ValueError("R2 negative sentinel failed")

    by_candidate: dict[str,dict] = {}
    for candidate in PROFILES:
        primary = [case["candidates"][candidate]["checkpoints"]["1000"]["trace_distinct"] for case in positive]
        reference = [case["candidates"]["baseline"]["checkpoints"]["1000"]["trace_distinct"] for case in positive]
        n_persist = sum(primary)
        rescue = sum(x and not y for x,y in zip(primary,reference))
        harm = sum(y and not x for x,y in zip(primary,reference))
        possible_turnovers = sum(case["candidates"][candidate]["turnover_possible_but_unproven"] for case in positive)
        certified = sum(case["candidates"][candidate]["turnover_certified"] for case in positive)
        diagnostic = {
            "h100": sum(case["candidates"][candidate]["checkpoints"]["100"]["trace_distinct"] for case in positive),
            "h1000": n_persist,
            "paired_rescue_only": rescue,
            "paired_baseline_only": harm,
            "paired_net_uplift": rescue - harm,
            "paired_exact_one_sided_p_exploratory": exact_one_sided(rescue,harm),
            "possible_not_proven_turnover_cases": possible_turnovers,
            "certified_carrier_turnover_cases": certified,
            "negative_clean": NEGATIVE_COUNT,
            "latent_changed_vs_baseline_at_any_checkpoint": sum(
                any(k["latent_intervention_delta_b"] or k["latent_intervention_delta_h"]
                    for k in case["candidates"][candidate]["checkpoints"].values())
                for case in positive
            ),
        }
        diagnostic["r2_numerical_gate"] = (
            n_persist >= 12 and rescue - harm >= 4
        )
        diagnostic["r2_advance_gate"] = (
            candidate != "baseline" and diagnostic["r2_numerical_gate"]
            and certified >= 1 and diagnostic["negative_clean"] == NEGATIVE_COUNT
        )
        by_candidate[candidate] = diagnostic

    shortlisted = [x for x in PROFILES if by_candidate[x]["r2_advance_gate"]]
    if len(shortlisted) > 1:
        shortlisted.sort(key=lambda x:(-by_candidate[x]["h1000"], -by_candidate[x]["paired_net_uplift"], x))
    result = {
        "schema_version": 1, "issue": ISSUE,
        "source_sha": source_sha, "frozen_digest": frozen["digest"],
        "manifest_engine_sha256": frozen["engine_sha256"],
        "shard_digests": [shards[i]["digest"] for i in range(SHARDS)],
        "case_digests": [observed[s]["digest"] for s in roster(frozen)],
        "counts": {"positive": len(positive), "negative": len(negative), "total":len(observed)},
        "candidate_scores": by_candidate,
        "research_decision": (
            "CANDIDATE_PENDING_FULL_LIFETIME_AND_TURNOVER_CONFIRMATION"
            if shortlisted else "CHANGE_PATH_NO_R2_FULL_ACCEPTANCE"
        ),
        "first_shortlist_only": (shortlisted[0] if shortlisted else None),
        "gating_notes": (
            "A freed original carrier and non-origin trace contrast are only a diagnostic necessary condition; "
            "no certified content provenance and no R3 progression without full-gate evidence. "
            "Candidates tested only in matched post-h0 continuations; pre-h0 lifetime behavior is unverified."
        ),
        "unexposed_future_heldout_seed_floor":1024,
        "learning_claim": False,
    }
    result["digest"] = _digest(result)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shard",type=int)
    p.add_argument("--aggregate",type=Path)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if (args.shard is None) == (args.aggregate is None):
        p.error("exactly one of --shard or --aggregate")
    result=(produce_shard(args.shard,args.source_sha) if args.shard is not None
            else aggregate(args.aggregate,args.source_sha))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({"issue":ISSUE, "digest":result["digest"],
                      "decision":result.get("research_decision"),
                      "scores":result.get("candidate_scores")},
                     sort_keys=True),flush=True)


if __name__=="__main__":
    main()
