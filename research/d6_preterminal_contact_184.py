"""D6 #184 — read-only selected-contact and actual trace-unit transfer histories.

This is an exploratory source/recipient lifetime-epoch audit on frozen,
OUTCOME-EXPOSED R2 cases. It is not new independent causal or L3 evidence.
All patches delegate native physics exactly once; no production changes.
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
from research.r2_write_rules_175 import LocalWriteRule, h0_branches, load_frozen, trajectory, HORIZONS, RATE
from research.transduction_audit_120 import canonical_digest, clone_state

ISSUE = 184
FROZEN_R2_DIGEST = "3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543"
EXPOSED_TERMINAL_LOSS = {555:499,556:320,560:256,563:762,575:724,582:576}
SHARDS, SHARD_SIZE, HORIZON = 8, 3, 1000
PROTOCOL = {
    "issue": ISSUE, "mode":"observational_preterminal_transfer_in_exposed_R2",
    "teacher_branches":["b","h"], "rate":256, "operator":"unit_add",
    "horizon":1000,"checkpoint_horizons":list(HORIZONS),
    "transfer":"native selected_pairs -> physically actual conservative _transfer_slow_trace, no policy change",
    "lifetime":"slot epoch starts at 0 if h0 nonfree, -1 if h0 free; each native spawn increments; native free ends epoch",
    "target":"ten fixed exposed D5 terminal differential positive trace donors across six last loss generations, current slot epoch ONLY",
    "endpoint":"number with preterminal physically selected contact, actual positive outward trace units, recipient nonfree in same epoch after donor freed and at +1000",
    "inference":"physical trace-unit passage is not proof of teacher-content information lineage, latent readout, or learning",
    "invalid":"any h0, byte-state parity, deterministic replay, negative sentinel drift, missing case or source digest -> INVALID, no seed replacement",
    "seed_boundary":"only R2 544..1023 selected positives16+negative8; 1024..4095/4096..8191 and Phase H96..159 untouched post-h0",
    "learning_claim":False,
}


def roster(frozen:dict)->list[int]:
    if frozen.get("digest") != FROZEN_R2_DIGEST:
        raise ValueError("D6 R2 immutable manifest digest drift")
    seeds=frozen["positive_seeds"]+frozen["negative_seeds"]
    if len(seeds)!=24 or len(set(seeds))!=24 or any(s<544 or s>1023 for s in seeds):
        raise ValueError("D6 exposed cohort invalid")
    return seeds


def epoch_for_slot(initial_lifecycle:list[int]) -> list[int]:
    return [0 if x!=Lifecycle.FREE else -1 for x in initial_lifecycle]


def same_epoch_contact(event:dict, *, slot:int, epoch:int) -> bool:
    return ((event["slot_a"]==slot and event["epoch_a"]==epoch)
         or (event["slot_b"]==slot and event["epoch_b"]==epoch))


def outbound_units(event:dict, *, slot:int)->int:
    if event["slot_a"]==slot:
        return max(0,event["before_a"]-event["after_a"])
    if event["slot_b"]==slot:
        return max(0,event["before_b"]-event["after_b"])
    raise ValueError("slot absent from physically selected transfer")


def recipient_pair(event:dict, *, donor_slot:int) -> tuple[int,int]:
    if event["slot_a"]==donor_slot:
        return event["slot_b"],event["epoch_b"]
    if event["slot_b"]==donor_slot:
        return event["slot_a"],event["epoch_a"]
    raise ValueError("slot absent from pair")


def observe_branch(snapshot:dict, originals:set[int], *,loss_gen:int|None)->dict:
    cfg=profile(RATE)
    state=clone_state(snapshot,cfg)
    experiment=IOExperiment(state,experiment=_load_protocol())
    rule=LocalWriteRule("unit_add",originals)
    epochs=epoch_for_slot(state.lifecycle)
    transfers=[]
    free_events=[]
    checkpoints={}
    before_pending={}
    post_pending={}
    epoch_at_loss=None
    lifecycle_at_loss=None
    phase="before"
    rel=-1
    with rule.attach():
        native_transfer=physics._transfer_slow_trace
        native_spawn=UniverseState.spawn
        native_free=UniverseState.free
        native_decay=physics._decay_slow_trace

        def observed_transfer(current,config,pairs):
            pairset=tuple(pairs)
            before=bytes(current.slow_trace)
            metadata=[(
                int(a),int(b),int(epochs[a]),int(epochs[b]),
                int(current.lifecycle[a]),int(current.lifecycle[b])
            ) for a,b in pairset]
            result=native_transfer(current,config,pairset)
            for a,b,ea,eb,la,lb in metadata:
                if a==b:
                    raise ValueError("D6 invalid self-pair")
                if la==Lifecycle.FREE or lb==Lifecycle.FREE:
                    continue
                ba,bb=int(before[a]),int(before[b])
                aa,ab=int(current.slow_trace[a]),int(current.slow_trace[b])
                if ba+bb!=aa+ab:
                    raise ValueError("D6 selected transfer nonconservative")
                transfers.append({
                    "relative_generation":rel,
                    "slot_a":a,"slot_b":b,"epoch_a":ea,"epoch_b":eb,
                    "before_a":ba,"before_b":bb,"after_a":aa,"after_b":ab,
                    "actual_units":abs(ba-aa),
                })
            return result

        def observed_spawn(current,*args,**kwargs):
            slot=native_spawn(current,*args,**kwargs)
            epochs[slot]+=1
            return slot

        def observed_free(current,slot):
            if phase=="after_decay" and rel==loss_gen:
                free_events.append({
                    "relative_generation":rel,"slot":int(slot),
                    "epoch":int(epochs[slot]),
                    "donor_trace":int(current.slow_trace[slot]),
                    "lifecycle":int(current.lifecycle[slot]),
                })
            return native_free(current,slot)

        def observed_decay(*args,**kwargs):
            nonlocal phase
            result=native_decay(*args,**kwargs)
            phase="after_decay"
            if rel==loss_gen:
                before_pending[rel]=bytes(args[0].slow_trace)
            return result

        with ExitStack() as stack:
            stack.enter_context(patch.object(physics,"_transfer_slow_trace",observed_transfer))
            stack.enter_context(patch.object(UniverseState,"spawn",observed_spawn))
            stack.enter_context(patch.object(UniverseState,"free",observed_free))
            stack.enter_context(patch.object(physics,"_decay_slow_trace",observed_decay))
            for rel in range(1,HORIZON+1):
                phase="before"
                experiment._advance(())
                if phase!="after_decay":
                    raise ValueError("D6 missing decay stage")
                if rel==loss_gen:
                    post_pending[rel]=bytes(state.slow_trace)
                    epoch_at_loss=list(epochs)
                    lifecycle_at_loss=list(state.lifecycle)
                if rel in HORIZONS:
                    checkpoints[str(rel)]=canonical_digest(state.to_snapshot())

    return {
        "transfers":transfers,"free_events":free_events,
        "before_pending":before_pending,"post_pending":post_pending,
        "epoch_at_loss":epoch_at_loss,"lifecycle_at_loss":lifecycle_at_loss,
        "epoch_at_1000":list(epochs),"lifecycle_at_1000":list(state.lifecycle),
        "checkpoints":checkpoints,
    }


def summarize_donor(history:dict, event:dict, *,loss_gen:int)->dict:
    slot,epoch=event["slot"],event["epoch"]
    matches=[e for e in history["transfers"] if e["relative_generation"]<=loss_gen
             and same_epoch_contact(e,slot=slot,epoch=epoch)]
    outbound=[e for e in matches if outbound_units(e,slot=slot)>0]
    witnessed=[]
    for e in outbound:
        target,t_epoch=recipient_pair(e,donor_slot=slot)
        surviving=(
            history["epoch_at_loss"][target]==t_epoch
            and history["lifecycle_at_loss"][target]!=Lifecycle.FREE
        )
        terminal=(
            history["epoch_at_1000"][target]==t_epoch
            and history["lifecycle_at_1000"][target]!=Lifecycle.FREE
        )
        witnessed.append({
            "generation":e["relative_generation"],
            "recipient_slot":target,"recipient_epoch":t_epoch,
            "outbound_units":outbound_units(e,slot=slot),
            "recipient_survives_donor_free_epoch":bool(surviving),
            "recipient_survives_to_h1000_same_epoch":bool(terminal),
        })
    return {
        "source_slot":slot,"source_epoch":epoch,
        "relative_free_generation":loss_gen,
        "source_trace_before_free":event["donor_trace"],
        "selected_contacts_current_lifetime":len(matches),
        "actual_outbound_transfer_events":len(outbound),
        "actual_outbound_trace_units":sum(outbound_units(e,slot=slot) for e in outbound),
        "transfer_recipients":witnessed,
    }


def case_once(seed:int,frozen:dict)->dict:
    if seed not in roster(frozen):
        raise ValueError("D6 seed not authorized by R2 exposed roster")
    h0=h0_branches(seed)
    for key in ("b","h","control"):
        if canonical_digest(h0[key])!=frozen["h0_evidence"][str(seed)][key+"_digest"]:
            raise ValueError("D6 h0 mismatch")
    originals={
        slot for slot,(b,h) in enumerate(zip(
            h0["b"]["arrays"]["slow_trace"],h0["h"]["arrays"]["slow_trace"]
        )) if b!=h
    }
    known=EXPOSED_TERMINAL_LOSS.get(seed)
    data={key:observe_branch(h0[key],originals,loss_gen=known) for key in ("b","h")}
    if not originals:
        if (data["b"]["transfers"]!=data["h"]["transfers"]
            or data["b"]["checkpoints"]!=data["h"]["checkpoints"]):
            raise ValueError("D6 frozen negative physically diverged")

    donors={}
    if known is not None:
        pre_b=data["b"]["before_pending"].get(known)
        pre_h=data["h"]["before_pending"].get(known)
        if pre_b is None or pre_h is None:
            raise ValueError("D6 missing known last-loss stage")
        different={i for i,(b,h) in enumerate(zip(pre_b,pre_h)) if b!=h}
        if not different or data["b"]["post_pending"][known]!=data["h"]["post_pending"][known]:
            raise ValueError("D6 prior D4 final-loss stage drift")
        for key in ("b","h"):
            observed=data[key]["free_events"]
            matching=[e for e in observed if e["slot"] in different and e["donor_trace"]>0]
            donors[key]=[summarize_donor(data[key],e,loss_gen=known) for e in matching]
    item={
        "schema_version":1,"issue":ISSUE,
        "seed":seed,"role":"positive" if originals else "negative",
        "known_exposed_last_loss":known,"r2_digest":frozen["digest"],
        "checkpoints":{key:data[key]["checkpoints"] for key in ("b","h")},
        "selected_contact_events":{key:len(data[key]["transfers"]) for key in ("b","h")},
        "actual_transfer_events":{key:sum(x["actual_units"]>0 for x in data[key]["transfers"]) for key in ("b","h")},
        "final_loss_donor_lifetimes":donors,
        "learning_claim":False,
    }
    item["digest"]=_digest(item)
    return item


def validated_case(seed:int,frozen:dict)->dict:
    first=case_once(seed,frozen)
    if first!=case_once(seed,frozen):
        raise ValueError("D6 repeat observer non-deterministic")
    h0=h0_branches(seed)
    originals={
        slot for slot,(b,h) in enumerate(zip(
            h0["b"]["arrays"]["slow_trace"],h0["h"]["arrays"]["slow_trace"]
        )) if b!=h
    }
    for label in ("b","h"):
        raw=trajectory(h0[label],candidate="unit_add",originals=originals)
        for checkpoint in HORIZONS[1:]:
            k=str(checkpoint)
            if first["checkpoints"][label][k]!=raw["checkpoints"][k]["digest"]:
                raise ValueError("D6 selected-contact observer mutated physics")
    if first["role"]=="negative" and first["final_loss_donor_lifetimes"]:
        raise ValueError("D6 negative fabricated donor history")
    return first


def shard(index:int,source_sha:str)->dict:
    if len(source_sha)!=40 or any(x not in "0123456789abcdef" for x in source_sha):
        raise ValueError("D6 exact source SHA required")
    if index not in range(SHARDS):
        raise ValueError("D6 invalid shard")
    frozen=load_frozen()
    selected=roster(frozen)[index*SHARD_SIZE:(index+1)*SHARD_SIZE]
    if len(selected)!=SHARD_SIZE:
        raise ValueError("D6 incomplete frozen shard")
    rows=[validated_case(s,frozen) for s in selected]
    obj={"schema_version":1,"issue":ISSUE,"source_sha":source_sha,
         "r2_digest":FROZEN_R2_DIGEST,"protocol":PROTOCOL,
         "shard":index,"cases":rows,"learning_claim":False}
    obj["digest"]=_digest(obj)
    return obj


def aggregate(folder:Path,source_sha:str)->dict:
    if len(source_sha)!=40 or any(x not in "0123456789abcdef" for x in source_sha):
        raise ValueError("D6 source SHA invalid")
    frozen=load_frozen()
    paths=sorted(folder.glob("d6-shard-*.json"))
    if len(paths)!=SHARDS:
        raise ValueError("D6 expected exactly 8 artifacts")
    hashes={}
    cases={}
    for path in paths:
        record=json.loads(path.read_text(encoding="utf-8"))
        chk=record.pop("digest",None)
        if (_digest(record)!=chk or record["source_sha"]!=source_sha
            or record["r2_digest"]!=FROZEN_R2_DIGEST or record["protocol"]!=PROTOCOL):
            raise ValueError("D6 shard source/protocol/digest mismatch")
        index=record["shard"]
        if index not in range(SHARDS) or index in hashes:
            raise ValueError("D6 duplicate/invalid shard")
        expected=roster(frozen)[index*SHARD_SIZE:(index+1)*SHARD_SIZE]
        if [x["seed"] for x in record["cases"]]!=expected:
            raise ValueError("D6 cohort ordering drift")
        hashes[index]=chk
        for row in record["cases"]:
            digest=row.pop("digest",None)
            if _digest(row)!=digest or row["seed"] in cases:
                raise ValueError("D6 case checksum/double seed")
            row["digest"]=digest
            cases[row["seed"]]=row
    if len(cases)!=24 or sorted(hashes)!=list(range(SHARDS)):
        raise ValueError("D6 incomplete exact frozen cohort")
    positives=[cases[s] for s in frozen["positive_seeds"]]
    negatives=[cases[s] for s in frozen["negative_seeds"]]
    if any(r["role"]!="positive" for r in positives) or any(r["role"]!="negative" for r in negatives):
        raise ValueError("D6 roles drift")
    donors=[
        (x["seed"],branch,d)
        for x in positives if x["known_exposed_last_loss"] is not None
        for branch in ("b","h") for d in x["final_loss_donor_lifetimes"][branch]
    ]
    if len(donors)!=10:
        raise ValueError("D6 failed to reproduce ten D5 differential final donors")
    with_contact=[(s,branch,d) for s,branch,d in donors if d["selected_contacts_current_lifetime"]>0]
    with_outflow=[(s,branch,d) for s,branch,d in donors if d["actual_outbound_transfer_events"]>0]
    lasting=[(s,branch,d) for s,branch,d in with_outflow if any(w["recipient_survives_donor_free_epoch"] for w in d["transfer_recipients"])]
    result={
        "schema_version":1,"issue":ISSUE,"source_sha":source_sha,
        "r2_digest":FROZEN_R2_DIGEST,"protocol_digest":_digest(PROTOCOL),
        "case_digests":[cases[s]["digest"] for s in roster(frozen)],
        "shard_digests":[hashes[i] for i in range(SHARDS)],
        "counts":{
            "valid_cases":len(cases),"positive":len(positives),"negative":len(negatives),
            "d5_terminal_differential_donors":len(donors),
            "donors_with_selected_lifetime_contact":len(with_contact),
            "donors_with_actual_outward_trace_transfer":len(with_outflow),
            "donors_with_trace_recipient_surviving_donor_free":len(lasting),
        },
        "donor_histories":{
            str(s)+":"+branch+":"+str(d["source_slot"])+":"+str(d["source_epoch"]):d
            for s,branch,d in donors
        },
        "classification":(
            "OBSERVED_PRETERMINAL_REAL_TRACE_OUTFLOW_EXPLORATORY_ONLY"
            if with_outflow else
            "NO_ACTUAL_PRETERMINAL_OUTFLOW_IN_D5_LOSS_DONOR_LIFETIMES"
        ),
        "causal_teacher_content_handoff_proven":False,
        "independent_validation":False,
        "learning_claim":False,
    }
    result["digest"]=_digest(result)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shard",type=int)
    p.add_argument("--aggregate",type=Path)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if (args.shard is None)==(args.aggregate is None):
        p.error("select exactly one mode")
    obj=(shard(args.shard,args.source_sha) if args.shard is not None
         else aggregate(args.aggregate,args.source_sha))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(obj,separators=(",",":"),sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"issue":ISSUE,"digest":obj["digest"],
                      "counts":obj.get("counts"),"classification":obj.get("classification")},
                     sort_keys=True),flush=True)


if __name__=="__main__":
    main()
