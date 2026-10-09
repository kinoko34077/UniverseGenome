"""D7 #187 read-only microscopic trace fate of real surviving receiver, seed575.

All seed/cell/event selection is ALREADY OUTCOME-EXPOSED. NOT independent
memory learning evidence. No physical mutation beyond accepted R2 unit_add.
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

ISSUE=187
PRIMARY=575
SENTINEL=545
RECIPIENT=6
DONOR=15
TRANSFER_GEN=61
DONOR_FREE_GEN=724
HORIZON=1000
R2_DIGEST="3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543"
STAGES=("before_write","after_write","before_transfer","after_transfer","after_decay","end")
TARGET_CHECKS=(0,60,61,62,100,500,723,724,725,1000)
PROTOCOL={
    "issue":ISSUE,
    "seed_roles":{"575":["b","h","control"],"545":["b","h"]},
    "data_role":"already outcome-exposed R2/D6 microcase and negative sentinel, NOT independently confirmatory",
    "operator":"accepted research-only unit_add, rate256, no teacher after h0",
    "recipient":{"slot":6,"epoch":0,"donor_slot":15,"donor_epoch":0,"native_transfer_gen":61,"donor_free_gen":724,"survive_to":1000},
    "stages":list(STAGES),"checks":list(TARGET_CHECKS),
    "horizon":HORIZON,
    "endpoints":"receiver exact B/H trace-content contrast vs identical 3-unit donor transfer; event stage of first/last difference, lifetime, paired global contrast, latent observation and reader source exposure only",
    "validity":"R2 exact frozen h0, deterministic doubled replay, original uninstrumented unit_add authoritative checkpoint parity, negative 545 branch physics/stage/read events identical, transfer3 per B/H at 61, donor FREE724, receiver epoch0 survives to 1000",
    "claims":"trace byte contrast and read width opportunity are not causal teacher-specific memory, A-probe readout, L3/R3 or learning",
    "no_future_seeds":"no Phase H 96..159, R3 1024..4095 or D5 4096..8191 used above h0",
    "learning_claim":False,
}


def validate_seed(seed:int)->None:
    if seed not in (PRIMARY,SENTINEL):
        raise ValueError("D7 seed not frozen historical microcase or sentinel")


def stage_transitions(previous:bool,values:list[bool])->list[tuple[str,str]]:
    if len(values)!=len(STAGES):
        raise ValueError("D7 stages drift")
    result=[]
    current=previous
    for name,changed in zip(STAGES,values):
        if current!=changed:
            result.append((name,"appear" if changed else "disappear"))
        current=changed
    return result


def observed_branch(snapshot:dict,originals:set[int],*,seed:int)->dict[str,Any]:
    validate_seed(seed)
    cfg=profile(RATE)
    state=clone_state(snapshot,cfg)
    experiment=IOExperiment(state,experiment=_load_protocol())
    rule=LocalWriteRule("unit_add",originals)
    epochs=[0 if life!=Lifecycle.FREE else -1 for life in state.lifecycle]
    timeline=[]
    global_end=[]
    checkpoints={}
    transfer_events=[]
    targeted_free=[]
    read_sites=[]
    stage={}
    generation=-1

    def mark(name:str,current:UniverseState):
        if name in stage:
            raise ValueError("D7 duplicate operator stage")
        stage[name]={
            "receiver_trace":int(current.slow_trace[RECIPIENT]),
            "receiver_latent":int(current.latent[RECIPIENT]),
            "receiver_lifecycle":int(current.lifecycle[RECIPIENT]),
            "receiver_epoch":int(epochs[RECIPIENT]),
            "donor_trace":int(current.slow_trace[DONOR]),
            "donor_lifecycle":int(current.lifecycle[DONOR]),
            "donor_epoch":int(epochs[DONOR]),
        }

    with rule.attach():
        native_write=physics._apply_slow_trace_writes
        native_transfer=physics._transfer_slow_trace
        native_decay=physics._decay_slow_trace
        native_read=physics.transmission_mask
        native_free=UniverseState.free
        native_spawn=UniverseState.spawn

        def observed_write(current,config,amounts):
            mark("before_write",current)
            result=native_write(current,config,amounts)
            mark("after_write",current)
            return result

        def observed_transfer(current,config,pairs):
            pairset=tuple(pairs)
            mark("before_transfer",current)
            pair=[p for p in pairset if set(p)=={RECIPIENT,DONOR}]
            old_donor=int(current.slow_trace[DONOR])
            old_receiver=int(current.slow_trace[RECIPIENT])
            result=native_transfer(current,config,pairset)
            mark("after_transfer",current)
            if pair:
                transfer_events.append({
                    "generation":generation,
                    "pair":list(pair[0]),
                    "donor_before":old_donor,
                    "donor_after":int(current.slow_trace[DONOR]),
                    "receiver_before":old_receiver,
                    "receiver_after":int(current.slow_trace[RECIPIENT]),
                    "outbound_units":max(0,old_donor-int(current.slow_trace[DONOR])),
                    "donor_epoch":epochs[DONOR],
                    "receiver_epoch":epochs[RECIPIENT],
                })
            return result

        def observed_decay(*args,**kwargs):
            result=native_decay(*args,**kwargs)
            mark("after_decay",args[0])
            return result

        def observed_free(current,slot):
            if slot in (DONOR,RECIPIENT):
                targeted_free.append({
                    "generation":generation,"slot":int(slot),
                    "epoch":int(epochs[slot]),
                    "trace_before_free":int(current.slow_trace[slot]),
                })
            return native_free(current,slot)

        def observed_spawn(current,*args,**kwargs):
            slot=native_spawn(current,*args,**kwargs)
            epochs[slot]+=1
            return slot

        def observed_read(seedarg,gen,address,pair,bond_strength,participant=None,*,source_trace=None):
            result=native_read(
                seedarg,gen,address,pair,bond_strength,
                participant=participant,source_trace=source_trace
            )
            if participant is not None and pair[0]==RECIPIENT:
                physical_trace=int(
                    participant.slow_trace[RECIPIENT] if source_trace is None else source_trace
                )
                base=1+(int(bond_strength)>>4)
                shift=int(participant.config.trace_bonus_shift)
                read_sites.append({
                    "generation":generation,"source_epoch":epochs[RECIPIENT],
                    "source_trace":physical_trace,"bonus":physical_trace>>shift,
                    "effective_width":min(16,base+(physical_trace>>shift)),
                    "physical_pair":list(pair),
                })
            return result

        with ExitStack() as stack:
            stack.enter_context(patch.object(physics,"_apply_slow_trace_writes",observed_write))
            stack.enter_context(patch.object(physics,"_transfer_slow_trace",observed_transfer))
            stack.enter_context(patch.object(physics,"_decay_slow_trace",observed_decay))
            stack.enter_context(patch.object(physics,"transmission_mask",observed_read))
            stack.enter_context(patch.object(UniverseState,"free",observed_free))
            stack.enter_context(patch.object(UniverseState,"spawn",observed_spawn))
            for generation in range(1,HORIZON+1):
                stage={}
                experiment._advance(())
                mark("end",state)
                if tuple(stage)!=STAGES:
                    raise ValueError("D7 actual physical step operator order drift")
                timeline.append(stage)
                global_end.append(bytes(state.slow_trace))
                if generation in HORIZONS:
                    checkpoints[str(generation)]=canonical_digest(state.to_snapshot())

    return {
        "timeline":timeline,"global_end":global_end,
        "transfer_events":transfer_events,"targeted_free":targeted_free,
        "read_sites":read_sites,
        "checkpoints":checkpoints,
    }


def case_once(frozen:dict)->dict:
    if frozen["digest"]!=R2_DIGEST:
        raise ValueError("D7 source frozen R2 manifest changed")
    data={}
    snapshots={}
    for seed,labels in ((PRIMARY,("b","h","control")),(SENTINEL,("b","h"))):
        validate_seed(seed)
        h0=h0_branches(seed)
        if any(canonical_digest(h0[key])!=frozen["h0_evidence"][str(seed)][key+"_digest"]
               for key in ("b","h","control")):
            raise ValueError("D7 R2 h0 mismatch")
        initials=h0["b"]["arrays"]["slow_trace"],h0["h"]["arrays"]["slow_trace"]
        originals={i for i,(b,h) in enumerate(zip(*initials)) if b!=h}
        if seed==SENTINEL and originals:
            raise ValueError("D7 sentinel h0 not negative")
        for label in labels:
            data[(seed,label)]=observed_branch(h0[label],originals,seed=seed)
        snapshots[seed]=(h0,originals)

    b=data[(PRIMARY,"b")];h=data[(PRIMARY,"h")];c=data[(PRIMARY,"control")]
    nb=data[(SENTINEL,"b")];nh=data[(SENTINEL,"h")]
    if nb!=nh:
        raise ValueError("D7 negative B/H diverged at stage, read, free or snapshot")
    for label,history in (("b",b),("h",h)):
        real=[x for x in history["transfer_events"] if x["generation"]==TRANSFER_GEN
              and x["donor_epoch"]==0 and x["receiver_epoch"]==0]
        if len(real)!=1 or real[0]["outbound_units"]!=3:
            raise ValueError("D7 D6 physical recipient transfer of three units at +61 missing")
        donor_frees=[x for x in history["targeted_free"] if x["slot"]==DONOR
                     and x["generation"]==DONOR_FREE_GEN and x["epoch"]==0]
        if len(donor_frees)!=1:
            raise ValueError("D7 donor FREE previous lineage drift")
        if any(record["end"]["receiver_epoch"]!=0 or
               record["end"]["receiver_lifecycle"]==Lifecycle.FREE
               for record in history["timeline"]):
            raise ValueError("D7 expected uninterrupted recipient epoch0 was not preserved")
    status=[b["timeline"][i]["end"]["receiver_trace"]!=h["timeline"][i]["end"]["receiver_trace"]
            for i in range(HORIZON)]
    initial_diff=snapshots[PRIMARY][0]["b"]["arrays"]["slow_trace"][RECIPIENT]!=snapshots[PRIMARY][0]["h"]["arrays"]["slow_trace"][RECIPIENT]
    epoch_diff=[initial_diff]+status
    stage_windows=[]
    for idx in range(HORIZON):
        bs=b["timeline"][idx];hs=h["timeline"][idx]
        for name,change in stage_transitions(
            epoch_diff[idx],
            [bs[key]["receiver_trace"]!=hs[key]["receiver_trace"] for key in STAGES],
        ):
            stage_windows.append({
                "generation":idx+1,"stage":name,"event":change,
                "b":bs[name]["receiver_trace"],
                "h":hs[name]["receiver_trace"],
            })
    # Global trace difference is frozen R2/D4: last positive at +723, gone +724.
    glob=[b["global_end"][i]!=h["global_end"][i] for i in range(HORIZON)]
    if not glob[722] or glob[723] or any(glob[723:]):
        raise ValueError("D7 D4/R2 global last contrast loss drift")
    check={}
    check["0"]={
        label:{
            "recipient_trace":int(snapshots[PRIMARY][0][label]["arrays"]["slow_trace"][RECIPIENT]),
            "donor_trace":int(snapshots[PRIMARY][0][label]["arrays"]["slow_trace"][DONOR])
        } for label in ("b","h","control")
    }
    for gen in TARGET_CHECKS[1:]:
        check[str(gen)]={
            label:{
                "receiver_stage_trace":{name:history["timeline"][gen-1][name]["receiver_trace"]
                                        for name in STAGES},
                "receiver_latent":history["timeline"][gen-1]["end"]["receiver_latent"],
                "receiver_epoch":history["timeline"][gen-1]["end"]["receiver_epoch"],
                "donor_lifecycle":history["timeline"][gen-1]["end"]["donor_lifecycle"],
                "global_BH_distinct":glob[gen-1],
            } for label,history in (("b",b),("h",h),("control",c))
        }
    obj={
        "issue":ISSUE,"schema_version":1,
        "r2_digest":R2_DIGEST,
        "protocol":PROTOCOL,
        "checkpoints":check,
        "recipient_BH_diff_first_at_end":next((i+1 for i,x in enumerate(status) if x),None),
        "recipient_BH_diff_last_at_end":max((i+1 for i,x in enumerate(status) if x),default=None),
        "recipient_BH_end_distinct_generation_count":sum(status),
        "recipient_BH_stage_transition_windows":stage_windows,
        "recipient_BH_different_at_transfer_after":(
            b["timeline"][TRANSFER_GEN-1]["after_transfer"]["receiver_trace"]
            !=h["timeline"][TRANSFER_GEN-1]["after_transfer"]["receiver_trace"]),
        "recipient_BH_different_at_donor_free":status[DONOR_FREE_GEN-1],
        "recipient_BH_different_at_h1000":status[-1],
        "receiver_native_read_source_events":{"b":b["read_sites"],"h":h["read_sites"]},
        "original_checkpoint_digests":{
            str(seed):{label:history["checkpoints"] for label,history in
                ((lbl,data[(seed,lbl)]) for lbl in (("b","h","control") if seed==PRIMARY else ("b","h")))}
            for seed in (PRIMARY,SENTINEL)
        },
        "causal_teacher_content_readout_proven":False,
        "independent_validation":False,
        "learning_claim":False,
    }
    obj["digest"]=_digest(obj)
    return obj


def validated_case()->dict:
    frozen=load_frozen()
    case=case_once(frozen)
    if case!=case_once(frozen):
        raise ValueError("D7 instrumented deterministic repeat failed")
    for seed,labels in ((PRIMARY,("b","h","control")),(SENTINEL,("b","h"))):
        h0=h0_branches(seed)
        originals={i for i,(b,h) in enumerate(zip(
            h0["b"]["arrays"]["slow_trace"],h0["h"]["arrays"]["slow_trace"]
        )) if b!=h}
        for label in labels:
            native=trajectory(h0[label],candidate="unit_add",originals=originals)
            for gen in HORIZONS[1:]:
                k=str(gen)
                if case["original_checkpoint_digests"][str(seed)][label][k]!=native["checkpoints"][k]["digest"]:
                    raise ValueError("D7 native uninstrumented physical parity failed")
    return case


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    sha=args.source_sha
    if len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("D7 exact source SHA required")
    obj=validated_case()
    obj["source_sha"]=sha
    obj["digest"]=_digest({k:v for k,v in obj.items() if k!="digest"})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({
        "issue":ISSUE,"digest":obj["digest"],
        "receiver_first":obj["recipient_BH_diff_first_at_end"],
        "receiver_last":obj["recipient_BH_diff_last_at_end"],
        "receiver_diff_generations":obj["recipient_BH_end_distinct_generation_count"],
        "at_transfer":obj["recipient_BH_different_at_transfer_after"],
        "at_donor_free":obj["recipient_BH_different_at_donor_free"],
        "at_h1000":obj["recipient_BH_different_at_h1000"],
        "checkpoints":obj["checkpoints"],
        "stage_windows":obj["recipient_BH_stage_transition_windows"],
    },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
