"""D4 #178: exploratory, observer-only residual contrast loss stage windows.

Outcome-exposed R2 cohort ONLY. NO new candidate tuning, R3, or held-out use.
Operator wrappers delegate once and collect trace bytes; stage association
is observational, NOT physical causation or proven inter-carrier handoff.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
import argparse
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import core.physics as physics
from core.experiment import IOExperiment
from core.state import UniverseState
from research.phase_g_memory_search_159 import _digest, _load_protocol
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import (
    ISSUE as R2_ISSUE, HORIZONS, RATE, PROFILES,
    LocalWriteRule, h0_branches, load_frozen, trajectory,
)
from research.transduction_audit_120 import canonical_digest, clone_state

ISSUE = 178
SHARDS = 8
SHARD_SIZE = 3
STAGES = (
    "before_write", "after_write", "after_transfer",
    "before_decay", "after_decay", "end",
)
HORIZON = 1000
R2_DIGEST = "3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543"
PROTOCOL = {
    "source_r2": "R2 #175 outcome-exposed exploratory 16 positive + 8 negative only",
    "operator": "unit_add",
    "metric": "B/H slow_trace byte-array exact distinction after aligned physical helper boundaries",
    "stages": list(STAGES),
    "checkpoints": list(HORIZONS),
    "horizon": HORIZON,
    "interpretation": "stage-correlated last loss is not unique cause, turnover witness, memory readout or R3 validation",
    "validity": "full 24 records, B/H h0 hashes, deterministic replay, uninstrumented unit_add parity at all checkpoints, 8 negative sentinels identical at every stage, source+payload SHA digest",
    "reserved": "no h>0 outside R2 544..1023 selected seeds; future >=1024 and historic 96..159 untouched",
    "learning_claim": False,
}


def roster(frozen: dict) -> list[int]:
    if frozen["digest"] != R2_DIGEST:
        raise ValueError("D4 immutable R2 roster digest drift")
    return frozen["positive_seeds"] + frozen["negative_seeds"]


def validate_source_sha(source_sha: str) -> None:
    if len(source_sha) != 40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("D4 exact source commit SHA required")


def stage_pair_changes(previous_end: bool, stage_status: list[bool]) -> list[str]:
    if len(stage_status) != len(STAGES):
        raise ValueError("stage count drift")
    names = []
    current = previous_end
    for name, distinguishable in zip(STAGES, stage_status):
        if current and not distinguishable:
            names.append(name)
        current = distinguishable
    return names


def stage_trajectory(snapshot: dict, originals: set[int]) -> dict[str, Any]:
    cfg = profile(RATE)
    state = clone_state(snapshot, cfg)
    experiment = IOExperiment(state, experiment=_load_protocol())
    rule = LocalWriteRule("unit_add", originals)
    timeline = []
    checkpoint_digests: dict[str, str] = {}
    free_events: list[dict[str, int]] = []
    active: dict[str, Any] = {}

    with rule.attach():
        native_write = physics._apply_slow_trace_writes
        native_transfer = physics._transfer_slow_trace
        native_decay = physics._decay_slow_trace
        native_free = UniverseState.free

        def mark(stage: str, state: UniverseState):
            if stage in active:
                raise ValueError("D4 physical stage duplicated within generation")
            active[stage] = bytes(state.slow_trace)

        def observed_write(current, config, amounts):
            mark("before_write", current)
            result = native_write(current, config, amounts)
            mark("after_write", current)
            return result

        def observed_transfer(current, config, pairs):
            result = native_transfer(current, config, pairs)
            mark("after_transfer", current)
            return result

        def observed_decay(*args, **kwargs):
            mark("before_decay", args[0])
            result = native_decay(*args, **kwargs)
            mark("after_decay", args[0])
            return result

        def observed_free(current, slot):
            v = int(current.slow_trace[slot])
            if v:
                free_events.append({
                    "generation": int(current.generation),
                    "trace_mass_erased_gross": v,
                    "original_h0_differential_slot": int(slot in originals),
                })
            return native_free(current, slot)

        with ExitStack() as stack:
            stack.enter_context(patch.object(physics, "_apply_slow_trace_writes", observed_write))
            stack.enter_context(patch.object(physics, "_transfer_slow_trace", observed_transfer))
            stack.enter_context(patch.object(physics, "_decay_slow_trace", observed_decay))
            stack.enter_context(patch.object(UniverseState, "free", observed_free))
            for generation in range(1, HORIZON + 1):
                active = {}
                experiment._advance(())
                mark("end", state)
                if tuple(active) != STAGES:
                    raise ValueError("D4 physical stage order/missing stage drift")
                timeline.append([active[stage] for stage in STAGES])
                if generation in HORIZONS:
                    checkpoint_digests[str(generation)] = canonical_digest(state.to_snapshot())

    return {
        "timeline": timeline,
        "checkpoint_digests": checkpoint_digests,
        "free_events": free_events,
        "write_events": dict(rule.events),
    }


def stage_diagnosis(first: dict, second: dict, *, initial_distinct: bool) -> dict:
    if len(first["timeline"]) != HORIZON or len(second["timeline"]) != HORIZON:
        raise ValueError("D4 timeline length drift")
    previous = initial_distinct
    end_status = [initial_distinct]
    disappearance = []
    reappearance = []
    per_stage_loss = Counter()
    for idx, (b, h) in enumerate(zip(first["timeline"], second["timeline"])):
        status = [a != c for a, c in zip(b, h)]
        steps = stage_pair_changes(previous, status)
        for stage in steps:
            per_stage_loss[stage] += 1
        if previous and not status[-1]:
            disappearance.append(idx+1)
        if not previous and status[-1]:
            reappearance.append(idx+1)
        end_status.append(status[-1])
        previous = status[-1]

    retainer = end_status[-1]
    final_loss = None
    loss_windows = []
    if not retainer and initial_distinct:
        last_distinct = max((k for k,v in enumerate(end_status) if v), default=None)
        if last_distinct is None or last_distinct >= HORIZON:
            raise ValueError("D4 last-distinct classification impossible")
        final_loss = last_distinct + 1
        for stage in stage_pair_changes(
            end_status[final_loss-1],
            [a != c for a,c in zip(first["timeline"][final_loss-1],
                                    second["timeline"][final_loss-1])],
        ):
            loss_windows.append(stage)
    return {
        "h1000_distinct": retainer,
        "h100_distinct": end_status[100],
        "h0_distinct": initial_distinct,
        "first_disappearance": disappearance[0] if disappearance else None,
        "all_end_disappearance_generations": disappearance,
        "all_end_reappearance_generations": reappearance,
        "per_stage_loss_window_count": dict(sorted(per_stage_loss.items())),
        "last_permanent_loss_generation": final_loss,
        "last_permanent_loss_stage_windows": loss_windows,
        "note": "Loss windows are associated transitions across differently evolved B/H trajectories, not causal intervention evidence.",
    }


def evaluate_seed(seed: int, frozen: dict, *, validate: bool = True) -> dict:
    authorized = roster(frozen)
    if seed not in authorized:
        raise ValueError("D4 seed not selected in outcome-exposed R2 manifest")
    h0 = h0_branches(seed)
    for label in ("b", "h", "control"):
        if canonical_digest(h0[label]) != frozen["h0_evidence"][str(seed)][label+"_digest"]:
            raise ValueError("D4 h0 snapshot provenance drift")
    originals = {
        idx for idx, (bv,hv) in enumerate(zip(
            h0["b"]["arrays"]["slow_trace"],h0["h"]["arrays"]["slow_trace"]
        )) if bv != hv
    }
    def compute():
        b = stage_trajectory(h0["b"], originals)
        h = stage_trajectory(h0["h"], originals)
        first=stage_diagnosis(b,h,initial_distinct=bool(originals))
        result={
            "schema_version":1,"issue":ISSUE,"seed":seed,
            "role":"positive" if seed in frozen["positive_seeds"] else "negative",
            "r2_frozen_digest":frozen["digest"],
            "h0_digests":{label:canonical_digest(h0[label]) for label in ("b","h","control")},
            "observation":first,
            "checkpoint_digests":{label:history["checkpoint_digests"] for label,history in (("b",b),("h",h))},
            "free_events":{
                label: {
                    "count_with_trace":len(history["free_events"]),
                    "gross_trace_mass":sum(e["trace_mass_erased_gross"] for e in history["free_events"]),
                    "original_differential_slot_count":sum(e["original_h0_differential_slot"] for e in history["free_events"]),
                } for label,history in (("b",b),("h",h))
            },
            "learning_claim":False,
        }
        return result
    once=compute()
    if validate:
        repeat=compute()
        if once!=repeat:
            raise ValueError("D4 observer determinism replay failed")
        for label in ("b","h"):
            direct=trajectory(h0[label],candidate="unit_add",originals=originals)
            for checkpoint in HORIZONS[1:]:
                if once["checkpoint_digests"][label][str(checkpoint)] != direct["checkpoints"][str(checkpoint)]["digest"]:
                    raise ValueError("D4 observed vs native unit_add authoritative state parity failed")
        if once["role"]=="negative":
            if once["observation"]["h0_distinct"] or any(
                once["checkpoint_digests"]["b"][k]!=once["checkpoint_digests"]["h"][k]
                for k in once["checkpoint_digests"]["b"]
            ):
                raise ValueError("D4 negative sentinels split at measured checkpoints")
            # Beyond measured digests: every physics boundary must remain identical
            if once["observation"]["all_end_disappearance_generations"] or once["observation"]["all_end_reappearance_generations"] or once["observation"]["per_stage_loss_window_count"]:
                raise ValueError("D4 negative stage observer saw anomalous divergence")
        elif not once["observation"]["h0_distinct"]:
            raise ValueError("D4 positive was not h0 trace distinct")
    once["digest"]=_digest(once)
    return once


def shard(index: int, source_sha: str) -> dict:
    validate_source_sha(source_sha)
    if index not in range(SHARDS):
        raise ValueError("D4 predeclared shard index invalid")
    frozen=load_frozen()
    seeds=roster(frozen)[index*SHARD_SIZE:(index+1)*SHARD_SIZE]
    if len(seeds)!=SHARD_SIZE:
        raise ValueError("D4 immutable case roster partition")
    cases=[evaluate_seed(seed,frozen) for seed in seeds]
    result={
        "issue":ISSUE,"schema_version":1,"source_sha":source_sha,
        "r2_frozen_digest":R2_DIGEST,"shard":index,
        "protocol":PROTOCOL,"cases":cases,"learning_claim":False,
    }
    result["digest"]=_digest(result)
    return result


def aggregate(directory: Path,source_sha: str) -> dict:
    validate_source_sha(source_sha)
    frozen=load_frozen()
    paths=sorted(directory.glob("d4-shard-*.json"))
    if len(paths)!=SHARDS:
        raise ValueError("D4 artifact shard count mismatch")
    coll={}
    shard_hashes={}
    for p in paths:
        data=json.loads(p.read_text(encoding="utf-8"))
        checksum=data.pop("digest",None)
        if _digest(data)!=checksum or data["protocol"]!=PROTOCOL or data["source_sha"]!=source_sha or data["r2_frozen_digest"]!=R2_DIGEST:
            raise ValueError("D4 shard provenance or checksum mismatch")
        idx=data["shard"]
        if idx not in range(SHARDS) or idx in shard_hashes:
            raise ValueError("D4 duplicate shard index")
        expected=roster(frozen)[idx*SHARD_SIZE:(idx+1)*SHARD_SIZE]
        if [case["seed"] for case in data["cases"]]!=expected:
            raise ValueError("D4 frozen case ordering invalid")
        shard_hashes[idx]=checksum
        for case in data["cases"]:
            recorded=case.pop("digest",None)
            if _digest(case)!=recorded or case["seed"] in coll:
                raise ValueError("D4 case checksum or seed duplication")
            case["digest"]=recorded
            coll[case["seed"]]=case
    if len(coll)!=24 or sorted(shard_hashes)!=list(range(SHARDS)):
        raise ValueError("D4 missing expected cases")
    positives=[coll[s] for s in frozen["positive_seeds"]]
    negatives=[coll[s] for s in frozen["negative_seeds"]]
    if any(x["role"]!="positive" or not x["observation"]["h0_distinct"] for x in positives):
        raise ValueError("D4 positive role drift")
    if any(x["role"]!="negative" or x["observation"]["h0_distinct"] or x["observation"]["h1000_distinct"] for x in negatives):
        raise ValueError("D4 negative role drift")
    retainers=[x["seed"] for x in positives if x["observation"]["h1000_distinct"]]
    nonretainers=[x for x in positives if not x["observation"]["h1000_distinct"]]
    stats=dict(Counter(
        stage for case in nonretainers for stage in case["observation"]["last_permanent_loss_stage_windows"]
    ))
    if len(retainers)!=10 or len(nonretainers)!=6:
        raise ValueError("D4 fixed R2 source outcome mismatch — no cohort relabeling")
    summary={
        "issue":ISSUE,"schema_version":1,"source_sha":source_sha,
        "r2_frozen_digest":R2_DIGEST,"protocol_digest":_digest(PROTOCOL),
        "shard_digests":[shard_hashes[i] for i in range(SHARDS)],
        "case_digests":[coll[s]["digest"] for s in roster(frozen)],
        "counts":{"positive":16,"negative":8,"valid":24,"unit_add_retained":len(retainers),"unit_add_not_retained":len(nonretainers)},
        "retained_seed_ids":retainers,
        "not_retained":{
            str(case["seed"]):{
                "final_loss_generation":case["observation"]["last_permanent_loss_generation"],
                "loss_stage_windows":case["observation"]["last_permanent_loss_stage_windows"],
                "ever_disappeared":case["observation"]["all_end_disappearance_generations"],
                "ever_reappeared":case["observation"]["all_end_reappearance_generations"],
                "free_events":case["free_events"],
            } for case in nonretainers
        },
        "last_loss_stage_counts":stats,
        "scientific_disposition":"EXPLORATORY_EVENT_STAGE_ONLY_NOT_CAUSAL_NO_R3",
        "learning_claim":False,
    }
    summary["digest"]=_digest(summary)
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--shard",type=int)
    parser.add_argument("--aggregate",type=Path)
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--output",type=Path,required=True)
    arg=parser.parse_args()
    if (arg.shard is None)==(arg.aggregate is None):
        parser.error("select exactly one --shard or --aggregate")
    result=(shard(arg.shard,arg.source_sha) if arg.shard is not None else
            aggregate(arg.aggregate,arg.source_sha))
    arg.output.parent.mkdir(parents=True,exist_ok=True)
    arg.output.write_text(json.dumps(result,separators=(",",":"),sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"issue":ISSUE,"digest":result["digest"],"summary":{
        "counts":result.get("counts"),"retained":result.get("retained_seed_ids"),
        "not_retained":result.get("not_retained"),"stage_counts":result.get("last_loss_stage_counts"),
    }},sort_keys=True),flush=True)


if __name__=="__main__":
    main()
