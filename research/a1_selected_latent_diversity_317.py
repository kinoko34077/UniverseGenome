"""A1.5 #317: source-native selected latent diversity and population support.

Only prior outcome-exposed original R2 544 (positive)/545 (negative).
Measure native StepMetrics and already-selected original read events only.
Original physics, writer, input, RNG, selection and teacher are untouched.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import json
import sys
import time
from unittest.mock import patch

import research.a1_exposed_reader_pilot_317 as pilot
from core.experiment import IOExperiment
from core.physics import apply_latent_operator
from core.state import Lifecycle
from research.a1_native_bit_support_317 import classify as classify_bit_support, period_for
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import RATE, load_frozen, h0_branches, HORIZONS
from research.phase_g_memory_search_159 import _digest

SCHEMA = "UG_A1_5_NATIVE_LATENT_REACHABILITY_RETROSPECTIVE_V1"
METRIC_FIELDS = ("fusion_count","fragmentation_count","collision_count",
                 "latent_transmission_count","noise_spawn_count")
ALLOWED = (544, 545)
EXPECTED_COUNTS = {544: (764,95,36),545:(966,0,0)}


def active_latent_support(state):
    vals=[int(state.latent[s]) for s in state.active_slots()]
    hist=Counter(vals)
    return {"active":len(vals), "distinct_words":len(hist),
            "not_one":sum(n for v,n in hist.items() if v!=1),
            "words":{str(k):hist[k] for k in sorted(hist)}}


def selected_event_distribution(events):
    counts=Counter()
    stage={label:Counter() for label in ("1-100","101-250","251-500","501-1000")}
    src_words=Counter(); dst_words=Counter(); different_rows=[]
    for e in events:
        src=int(e["source_latent_before"]); dst=int(e["recipient_latent_before"])
        mask=int(e["native_mask"]); after=int(e["recipient_latent_after"])
        if any(not 0<=v<=65535 for v in (src,dst,mask,after)):
            raise ValueError("invalid native 16-bit word in selected event")
        if apply_latent_operator("masked_copy",src,dst,mask)!=after:
            raise ValueError("native selected output/source operator mismatch")
        x=(src ^ dst)
        c=stage[period_for(int(e["native_generation"])-12)]
        for counter in (counts,c):
            counter["selected_source_events"]+=1
            if src!=dst:counter["different_prelatent"]+=1
            if x & mask:counter["native_nonzero_copy_delta"]+=1
            if src!=1:counter["source_not_one"]+=1
            if dst!=1:counter["recipient_not_one"]+=1
        src_words[src]+=1;dst_words[dst]+=1
        if src!=dst:
            different_rows.append([
                int(e["native_generation"]),int(e["address"]),
                int(e["source_slot"]),int(e["recipient_slot"]),
                int(e["source_epoch"]),int(e["recipient_epoch"]),
                src,dst,mask,after,
            ])
    if len(different_rows)>256:
        raise ValueError("retained real diverse selected event limit exceeded")
    return {"counts":dict(sorted(counts.items())),
            "by_original_period":{k:dict(sorted(v.items())) for k,v in stage.items()},
            "source_words":{str(k):v for k,v in sorted(src_words.items())},
            "destination_words":{str(k):v for k,v in sorted(dst_words.items())},
            "all_nonidentical_original_selected_event_rows":different_rows}


def run_observed_branch(seed,label,frozen,start):
    if seed not in ALLOWED or label not in ("b","h"):
        raise ValueError("only frozen old R2 teacher roles allowed")
    snapshots=h0_branches(seed)
    base=int(snapshots[label]["generation"])
    if base!=13:
        raise ValueError("original h0 generation unexpected")
    original=pilot.IOExperiment
    stage={k:Counter() for k in ("1-100","101-250","251-500","501-1000")}
    checkpoint={"0": {"generation":base,
        **_snapshot_active_latent(snapshots[label])}}
    totals=Counter()
    steps=[0]
    class RecordingExperiment(original):
        def _advance(self,anchors=()):
            metrics=super()._advance(anchors)
            rel=int(self.state.generation)-base
            if not 1<=rel<=1000:
                raise ValueError("A1.5 attempted non-original post-h0 step")
            steps[0]+=1
            group=stage[period_for(rel)]
            for key in METRIC_FIELDS:
                value=int(getattr(metrics,key))
                if value<0: raise ValueError("invalid native step metric")
                totals[key]+=value;group[key]+=value
            support=active_latent_support(self.state)
            group["native_steps"]+=1
            if support["distinct_words"]>1: group["multilabel_population_steps"]+=1
            if support["not_one"]>0: group["population_non_one_steps"]+=1
            if rel in HORIZONS[1:]:
                checkpoint[str(rel)]={"generation":int(self.state.generation),**support}
            if rel%25==0:pilot.check_budget(start)
            return metrics
    with patch.object(pilot,"IOExperiment",RecordingExperiment):
        source=pilot.run_branch(seed,label,frozen,start)
    if steps[0]!=1000 or set(checkpoint)!={"0","1","10","100","250","500","1000"}:
        raise ValueError("incomplete original 1000-generation sequence")
    selected=selected_event_distribution(source["events"])
    if selected["counts"].get("selected_source_events",0)!=source["reader_events"]:
        raise ValueError("native original selected event count inconsistent")
    return {
        "original_h0_sha256":source["h0_sha256"],
        "original_r2_checkpoint_sha256":source["checkpoint_digests"],
        "original_native_selected_events_sha256":source["read_events_sha256"],
        "metrics_native_totals":dict(sorted(totals.items())),
        "native_metrics_by_frozen_period":{k:dict(sorted(v.items())) for k,v in stage.items()},
        "population_latent_at_frozen_checkpoints":checkpoint,
        "selected_native_contacts":selected,
        "_original_events":source["events"],
        "physical_steps":steps[0],
    }


def _snapshot_active_latent(snapshot):
    a=snapshot["arrays"]; values=[int(a["latent"][i]) for i,v in enumerate(a["lifecycle"])
                                      if int(v)==int(Lifecycle.ACTIVE)]
    h=Counter(values)
    return {"active":len(values),"distinct_words":len(h),
            "not_one":sum(v for k,v in h.items() if k!=1),
            "words":{str(k):h[k] for k in sorted(h)}}


def run_study(frozen,start):
    studies={}
    for seed in ALLOWED:
        b=run_observed_branch(seed,"b",frozen,start)
        h=run_observed_branch(seed,"h",frozen,start)
        # Existing A1.4 authoritative observations, not learned from this test.
        source_b=b["selected_native_contacts"]["counts"]
        source_h=h["selected_native_contacts"]["counts"]
        original_comparison=classify_bit_support(
            b["_original_events"],h["_original_events"],h0_generation=13,
        )
        cc=original_comparison["counts"]
        if (cc.get("matched",0),cc.get("trace_diff",0),cc.get("changed_mask",0))!=EXPECTED_COUNTS[seed]:
            raise ValueError("A1.5 original A1.4 764/95/36 or 966/0/0 did not reproduce")
        if cc.get("confounded_nontrace",0) or cc.get("unmatched_topology",0):
            raise ValueError("A1.5 matched original native reader topology drift")
        if seed==544 and cc.get("H1_equal_source_recipient_latent",0)!=36:
            raise ValueError("original 36 real selected no-op results not reproduced")
        b.pop("_original_events")
        h.pop("_original_events")
        expected=EXPECTED_COUNTS[seed][0]
        if source_b.get("selected_source_events",0)!=expected or source_h.get("selected_source_events",0)!=expected:
            raise ValueError("original accepted selected-event denominator drift")
        if seed==545 and b!=h:
            raise ValueError("negative control branches differed in native events or population")
        studies[str(seed)]={"role":"exposed_positive" if seed==544 else "exposed_negative",
                            "b":b,"h":h}
        pilot.check_budget(start)
    return studies


def report(*,source_sha):
    if len(source_sha)!=40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("exact head source SHA required")
    frozen=load_frozen()
    if frozen["digest"]!=pilot.R2_FROZEN_DIGEST or profile(RATE).latent_operator!="masked_copy":
        raise ValueError("original R2 source frozen contract changed")
    start=time.perf_counter()
    first=run_study(frozen,start)
    second=run_study(frozen,start)
    if first!=second:
        raise ValueError("native original study observer deterministic replay mismatch")
    result={
        "schema":SCHEMA,"issue":317,"source_sha":source_sha,
        "original_r2_source_sha":pilot.R2_ORIGINAL_SOURCE,
        "original_r2_manifest_digest":pilot.R2_FROZEN_DIGEST,
        "old_original_action_run":37950076024,
        "conditions":{"seeds":{str(s):"exposed_positive" if s==544 else "exposed_negative" for s in ALLOWED},
                      "teacher_values":{"b":66,"h":8},"research_rule":"unit_add",
                      "rate":256,"steps":1000,"original_h0_generation":12,
                      "original_checkpoints":list(HORIZONS[1:]),
                      "no_new_seed":True,"source_native_physics_unmodified":True},
        "studies":first,"native_replay_parity":True,
        "independent_confirmation":False,"learning_claim":False,
        "environment":{"python":sys.implementation.name,"version":sys.version.split()[0],
                       "wall_seconds":round(time.perf_counter()-start,3),
                       "max_rss_mib":pilot.sampled_max_rss_mib()},
    }
    pilot.check_budget(start)
    result["digest"]=_digest(result)
    raw=json.dumps(result,sort_keys=True,separators=(",",":")).encode()
    if len(raw)>pilot.CAP_REPORT_BYTES:
        raise ValueError("A1.5 compact research output over frozen size cap")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=report(source_sha=args.source_sha)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n")
    print(json.dumps({"schema":SCHEMA,
        "selected":{s:{b:x["selected_native_contacts"]["counts"] for b,x in study.items() if b in ("b","h")}
                    for s,study in result["studies"].items()},
        "metrics":{s:{b:x["metrics_native_totals"] for b,x in study.items() if b in ("b","h")}
                   for s,study in result["studies"].items()},
        "learning_claim":False},sort_keys=True),flush=True)

if __name__=="__main__":main()
