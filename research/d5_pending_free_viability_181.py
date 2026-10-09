"""D5 #181: exposed-cohort-only read-only test of final pending-FREE recipient viability.

First answer topology/physical exposure before designing any new intervention.
R1 free_local_relay was 0/24; native discharge already occurs before final
pending FREE. NEVER use these outcome-exposed seeds as new causal confirmation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import core.physics as physics
from core.experiment import IOExperiment
from core.state import Lifecycle, UniverseState
from research.phase_g_memory_search_159 import _digest, _load_protocol
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import (
    LocalWriteRule, RATE, HORIZONS, h0_branches, load_frozen, trajectory,
)
from research.transduction_audit_120 import canonical_digest, clone_state

ISSUE = 181
SHARDS = 8
CASES_PER_SHARD = 3
HORIZON = 1000
R2_MANIFEST_DIGEST = "3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543"
EXPOSED_LOSS_GENERATIONS = {
    555: 499, 556: 320, 560: 256, 563: 762, 575: 724, 582: 576,
}
PROTOCOL = {
    "issue": ISSUE,
    "role": "EXPLORATORY outcome-exposed R2 16 positive+8 negative, no prospective D5 cohort used",
    "operator": "R2 unit_add unchanged and physics native final pending_free",
    "stages": ["after_native_decay", "before_pending_free", "after_pending_free_end"],
    "recipient_definition": "ACTIVE overlapping donor physical destination footprint and uint8 headroom; exclude self/FREE/BLACK_HOLE; cap=min(16,donor_trace,receiver_headroom)",
    "epochs": "1000 post-h0 teacher-free matched generations at decay256",
    "primary": "at each of six frozen D4 end-only last loss generations, are any B/H differential donor pending-FREE events locally relay-eligible?",
    "result": "topology feasibility or inapplicability only; not physical transfer cause or independent confirmation",
    "validation": "exact h0 R2 digest, twice-deterministic observer, native unit_add checkpoint authoritative parity, 8 negative B/H identical at every generation and before/end stage, exact all 24 cases and original fixed six windows",
    "forward": "no R3/Phase H; no production defaults, no learning, future new h0 cohort only if separate prospective causal hypothesis remains physically viable",
}


def authorized_seeds(frozen: dict) -> list[int]:
    if frozen["digest"] != R2_MANIFEST_DIGEST:
        raise ValueError("D5 source R2 frozen cohort drift")
    a = frozen["positive_seeds"] + frozen["negative_seeds"]
    if len(a) != 24 or len(set(a)) != 24 or any(s < 544 or s > 1023 for s in a):
        raise ValueError("D5 source R2 cohort unsafe")
    return a


def eligible_recipients(state: UniverseState, slot: int) -> dict[str, Any]:
    """Non-mutating snapshot of exactly the accepted physical discharge locality."""
    if state.lifecycle[slot] != Lifecycle.BLACK_HOLE:
        raise ValueError("D5 donor must be native BLACK_HOLE pending-FREE")
    donor = int(state.slow_trace[slot])
    cfg = state.config
    cap = max(0, min(int(cfg.trace_discharge_cap), donor))
    footprint = physics.destination_footprint(
        state.structure[slot], state.x[slot], state.y[slot]
    )
    occupancy = physics._active_occupancy(state)
    recipients = sorted({
        target for tile in footprint for target in occupancy.get(tile, ())
        if target != slot and state.lifecycle[target] == Lifecycle.ACTIVE
    }, key=lambda target: physics._trace_physical_order_key(state, target))
    choices = [{
        "slot": target,
        "headroom": 255 - int(state.slow_trace[target]),
        "potential_units": min(cap, 255 - int(state.slow_trace[target])),
        "x": int(state.x[target]), "y": int(state.y[target]),
    } for target in recipients]
    return {
        "source_slot":slot, "donor_trace":donor,
        "source_x":int(state.x[slot]), "source_y":int(state.y[slot]),
        "donor_lifecycle":"BLACK_HOLE",
        "footprint": sorted([list(tile) for tile in footprint]),
        "native_discharge_cap":int(cfg.trace_discharge_cap),
        "local_active_count":len(choices),
        "local_available_headroom":sum(max(0,x["headroom"]) for x in choices),
        "potential_units_total_at_most":min(cap,sum(max(0,x["headroom"]) for x in choices)),
        "recipients":choices,
    }


def observed_branch(snapshot: dict, originals: set[int]) -> dict:
    cfg = profile(RATE)
    state = clone_state(snapshot, cfg)
    experiment = IOExperiment(state, experiment=_load_protocol())
    rule = LocalWriteRule("unit_add", originals)
    after_decay: list[bytes] = []
    after_free: list[bytes] = []
    events: list[dict[str,Any]] = []
    checkpoints: dict[str,str] = {}
    phase: str = "before"
    relative_generation = -1

    with rule.attach():
        native_decay = physics._decay_slow_trace
        native_free = UniverseState.free

        def wrapped_decay(*args, **kwargs):
            nonlocal phase
            if phase != "before":
                raise ValueError("D5 native decay unexpectedly duplicated/out of order")
            result = native_decay(*args, **kwargs)
            phase = "after_decay"
            after_decay.append(bytes(args[0].slow_trace))
            return result

        def wrapped_free(current:UniverseState, slot:int):
            if phase == "after_decay":
                item = eligible_recipients(current,slot)
                item["relative_generation"] = relative_generation
                item["is_original_h0_differing_slot"] = slot in originals
                events.append(item)
            return native_free(current,slot)

        with ExitStack() as stack:
            stack.enter_context(patch.object(physics,"_decay_slow_trace",wrapped_decay))
            stack.enter_context(patch.object(UniverseState,"free",wrapped_free))
            for relative_generation in range(1,HORIZON+1):
                phase = "before"
                before_count = len(after_decay)
                experiment._advance(())
                if phase != "after_decay" or len(after_decay) != before_count+1:
                    raise ValueError("D5 after-native-decay stage missing")
                after_free.append(bytes(state.slow_trace))
                if relative_generation in HORIZONS:
                    checkpoints[str(relative_generation)] = canonical_digest(state.to_snapshot())

    return {
        "after_decay":after_decay, "after_free":after_free,
        "pending_free_events":events,"checkpoints":checkpoints,
    }


def observed_case(seed:int, frozen:dict, *, validate:bool=True)->dict:
    if seed not in authorized_seeds(frozen):
        raise ValueError("D5 no novel or reserved seed allowed")
    h0 = h0_branches(seed)
    if any(canonical_digest(h0[label]) != frozen["h0_evidence"][str(seed)][label+"_digest"]
           for label in ("b","h","control")):
        raise ValueError("D5 h0 drift from R2 frozen")
    originals={
        slot for slot,(b,h) in enumerate(zip(
            h0["b"]["arrays"]["slow_trace"],h0["h"]["arrays"]["slow_trace"]
        )) if b!=h
    }
    def one():
        return {label:observed_branch(h0[label],originals) for label in ("b","h")}
    data=one()
    if validate:
        if data!=one():
            raise ValueError("D5 observational repeat non-deterministic")
        for label in ("b","h"):
            original=trajectory(h0[label],candidate="unit_add",originals=originals)
            for checkpoint in HORIZONS[1:]:
                k=str(checkpoint)
                if data[label]["checkpoints"][k] != original["checkpoints"][k]["digest"]:
                    raise ValueError("D5 observer changed underlying native physical continuation")

    b=data["b"];h=data["h"]
    if len(b["after_decay"])!=HORIZON or len(h["after_decay"])!=HORIZON:
        raise ValueError("D5 stage list incomplete")
    if not originals:
        for index in range(HORIZON):
            if (b["after_decay"][index]!=h["after_decay"][index] or
                b["after_free"][index]!=h["after_free"][index]):
                raise ValueError("D5 negative B/H split at physical stage")

    differences=[b["after_free"][k]!=h["after_free"][k] for k in range(HORIZON)]
    last_loss=None
    if originals and not differences[-1]:
        still=[k+1 for k,different in enumerate(differences) if different]
        last_loss=max(still)+1 if still else 1
        if last_loss not in range(1,HORIZON+1):
            raise ValueError("D5 impossible final loss epoch")
    known=EXPOSED_LOSS_GENERATIONS.get(seed)
    if known is not None and last_loss!=known:
        raise ValueError("D5 D4 final loss epoch changed")
    if originals and seed not in EXPOSED_LOSS_GENERATIONS and not differences[-1]:
        raise ValueError("D5 R2 retainer classification drift")
    if not originals and (any(differences) or last_loss is not None):
        raise ValueError("D5 negative role became trace-positive")

    last_events={}
    if last_loss is not None:
        k=last_loss-1
        donor_difference_slots={i for i,(v,w) in enumerate(zip(
            b["after_decay"][k],h["after_decay"][k]
        )) if v!=w}
        if not donor_difference_slots or b["after_free"][k]!=h["after_free"][k]:
            raise ValueError("D5 target last-loss generation not end-only")
        for label,history in (("b",b),("h",h)):
            entries=[e for e in history["pending_free_events"]
                     if e["relative_generation"]==last_loss]
            for entry in entries:
                entry["donor_content_distinct_at_this_stage"] = entry["source_slot"] in donor_difference_slots
            last_events[label]=entries
        if not any(last_events.values()):
            raise ValueError("D5 loss event had no pending-FREE cleanup")

    record={
        "issue":ISSUE,"seed":seed,
        "role":"positive" if originals else "negative",
        "r2_digest":frozen["digest"],
        "last_loss_generation":last_loss,
        "h1000_distinct":bool(differences[-1]),
        "last_loss_events":last_events,
        "final_loss_observed_as_pending_free":bool(last_events),
        "pending_free_counts":{label:len(data[label]["pending_free_events"]) for label in ("b","h")},
        "recipient_eligible_pending_free_counts":{label:sum(
            bool(e["potential_units_total_at_most"])
            for e in data[label]["pending_free_events"]
        ) for label in ("b","h")},
        "checkpoints":{label:data[label]["checkpoints"] for label in ("b","h")},
        "learning_claim":False,
    }
    record["digest"]=_digest(record)
    return record


def validated_shard(index:int,source_sha:str)->dict:
    if len(source_sha)!=40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("D5 exact-head source SHA required")
    if index not in range(SHARDS):
        raise ValueError("D5 invalid shard index")
    frozen=load_frozen()
    seeds=authorized_seeds(frozen)[index*CASES_PER_SHARD:(index+1)*CASES_PER_SHARD]
    if len(seeds)!=CASES_PER_SHARD:
        raise ValueError("D5 predeclared cohort assignment mismatch")
    records=[observed_case(seed,frozen) for seed in seeds]
    result={
        "issue":ISSUE,"schema_version":1,"source_sha":source_sha,
        "protocol":PROTOCOL,"r2_digest":R2_MANIFEST_DIGEST,
        "shard":index,"records":records,"learning_claim":False,
    }
    result["digest"]=_digest(result)
    return result


def aggregate(directory:Path,source_sha:str)->dict:
    if len(source_sha)!=40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("D5 exact-head source SHA required")
    frozen=load_frozen()
    paths=sorted(directory.glob("d5-shard-*.json"))
    if len(paths)!=SHARDS:
        raise ValueError("D5 not exactly 8 complete shards")
    records={}
    shard_digests={}
    for path in paths:
        shard=json.loads(path.read_text(encoding="utf-8"))
        dig=shard.pop("digest",None)
        if _digest(shard)!=dig or shard.get("source_sha")!=source_sha or shard.get("protocol")!=PROTOCOL or shard.get("r2_digest")!=R2_MANIFEST_DIGEST:
            raise ValueError("D5 shard source/protocol/integrity mismatch")
        ix=shard["shard"]
        if ix not in range(SHARDS) or ix in shard_digests:
            raise ValueError("D5 duplicate/invalid shard")
        if [c["seed"] for c in shard["records"]] != authorized_seeds(frozen)[ix*CASES_PER_SHARD:(ix+1)*CASES_PER_SHARD]:
            raise ValueError("D5 cohort partition changed")
        shard_digests[ix]=dig
        for record in shard["records"]:
            case_digest=record.pop("digest",None)
            if _digest(record)!=case_digest or record["seed"] in records:
                raise ValueError("D5 per-case digest or seed mismatch")
            record["digest"]=case_digest
            records[record["seed"]]=record
    if len(records)!=24 or sorted(shard_digests)!=list(range(SHARDS)):
        raise ValueError("D5 missing 24/24")
    positives=[records[s] for s in frozen["positive_seeds"]]
    negatives=[records[s] for s in frozen["negative_seeds"]]
    if any(v["role"]!="positive" for v in positives) or any(v["role"]!="negative" for v in negatives):
        raise ValueError("D5 positive/negative cohort mismatch")
    losers=[x for x in positives if x["last_loss_generation"] is not None]
    if set(v["seed"] for v in losers)!=set(EXPOSED_LOSS_GENERATIONS):
        raise ValueError("D5 pre-existing 6/16 loss cohort changed")
    if any(v["last_loss_generation"] is not None or v["h1000_distinct"] for v in negatives):
        raise ValueError("D5 negative became distinct")
    source_entries=[]
    all_entries=[]
    for item in losers:
        for label in ("b","h"):
            for e in item["last_loss_events"][label]:
                all_entries.append((item["seed"],label,e))
                if e["donor_content_distinct_at_this_stage"] and e["donor_trace"]>0:
                    source_entries.append((item["seed"],label,e))
    eligible=[(s,label,e) for s,label,e in source_entries if e["potential_units_total_at_most"]>0]
    cases_with_eligible=sorted(set(s for s,_,_ in eligible))
    summary={
        "issue":ISSUE,"schema_version":1,"source_sha":source_sha,
        "r2_digest":R2_MANIFEST_DIGEST,
        "protocol_digest":_digest(PROTOCOL),
        "shard_digests":[shard_digests[i] for i in range(SHARDS)],
        "case_digests":[records[s]["digest"] for s in authorized_seeds(frozen)],
        "counts":{"positive":len(positives),"negative":len(negatives),"valid":len(records),"terminal_losses":len(losers)},
        "terminal_loss_records":{
            str(item["seed"]):{
                "generation":item["last_loss_generation"],
                "b_events":item["last_loss_events"].get("b",[]),
                "h_events":item["last_loss_events"].get("h",[]),
            } for item in losers
        },
        "all_last_loss_pending_free_events":len(all_entries),
        "last_loss_differential_trace_donors":len(source_entries),
        "last_loss_differential_donors_with_eligible_recipient":len(eligible),
        "last_loss_cases_with_eligible_differential_donor":cases_with_eligible,
        "all_generation_eligible_pending_free_counts":{
            str(item["seed"]):item["recipient_eligible_pending_free_counts"] for item in positives
        },
        "classification":(
            "FINAL_FREE_LOCAL_RELAY_PHYSICALLY_EXPOSED_EXPLORATORY_ONLY"
            if eligible else
            "FINAL_FREE_LOCAL_RELAY_NO_ELIGIBLE_DIFFERENTIAL_DONOR_IN_SIX_LOSS_CASES"
        ),
        "causal_effect_supported":False,
        "prospective_D5_cohort_untouched":True,
        "learning_claim":False,
    }
    summary["digest"]=_digest(summary)
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shard",type=int)
    p.add_argument("--aggregate",type=Path)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if (args.shard is None)==(args.aggregate is None):
        p.error("select exactly one mode")
    out=(validated_shard(args.shard,args.source_sha) if args.shard is not None
         else aggregate(args.aggregate,args.source_sha))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,separators=(",",":"),sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "issue":ISSUE,"digest":out["digest"],
        "classification":out.get("classification"),
        "counts":out.get("counts"),
        "eligible_sources":out.get("last_loss_differential_donors_with_eligible_recipient"),
        "eligible_cases":out.get("last_loss_cases_with_eligible_differential_donor"),
    },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
