"""D10 #195: frozen native slow-trace reader gates; synthetic only.

This is not a teacher B/H stimulus experiment or an L3 memory test.
No production physics/optimizer configuration is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from core.physics import (
    PhysicsConfig, _apply_slow_trace_writes, create_universe, transmission_mask,
)
from research.d8_genome_diversity_190 import digest

PROTOCOL={
    "issue":195,
    "source":"accepted core.physics native transmission_mask and generic write function",
    "seed":7,"generation":11,"address":19,"pair":[0,1],
    "research_shift":5,"bond_floor":0,"bond_saturated":255,
    "reader_cases":[[10,18],[31,32],[0,255]],
    "inert_shift":8,
    "generic_write":{"initial":4,"amount":5,"cap":8,"expected":9},
    "qualification":"synthetic physical fixture, not independent teacher-content persistence, learning or overfit",
    "production_mutation":False,
    "learning_claim":False,
}


def _mask(*,trace:int,bond:int,shift:int)->int:
    config=PhysicsConfig(max_cells=8,initial_density=2,trace_bonus_shift=shift)
    state=create_universe(seed=7,config=config)
    state.slow_trace[0]=trace
    return transmission_mask(
        7,11,19,(0,1),bond,participant=state,
        source_trace=trace,
    )


def _generic_write()->dict[str,int|bool]:
    config=PhysicsConfig(max_cells=8,initial_density=2,trace_write_cap=8,trace_bonus_shift=5)
    states=[create_universe(seed=7,config=config) for _ in range(2)]
    # "B" and "H" are only external report names, NEVER physical inputs.
    for state in states:
        state.slow_trace[0]=4
        _apply_slow_trace_writes(state,config,{0:5})
    left,right=(int(state.slow_trace[0]) for state in states)
    if left!=9 or right!=9:
        raise AssertionError("native generic physical writes no longer match frozen hypothesis")
    return {"input_trace":4,"physical_activity_amount":5,"write_cap":8,
            "output_1":left,"output_2":right,
            "same_without_teacher_label":left==right}


def evaluate()->dict[str,Any]:
    same_a,same_b=(_mask(trace=t,bond=0,shift=5) for t in (10,18))
    edge_a,edge_b=(_mask(trace=t,bond=0,shift=5) for t in (31,32))
    saturation_a,saturation_b=(_mask(trace=t,bond=255,shift=5) for t in (0,255))
    inert_a,inert_b=(_mask(trace=t,bond=0,shift=8) for t in (0,255))
    if not (
        same_a==same_b and
        edge_a!=edge_b and edge_a.bit_count()==1 and edge_b.bit_count()==2 and
        (edge_a&edge_b)==edge_a and
        saturation_a==saturation_b and saturation_a.bit_count()==16 and
        inert_a==inert_b and inert_a.bit_count()==1
    ):
        raise AssertionError("frozen native slow-trace mask-width prediction failed")
    results={
        "issue":195,
        "schema_version":1,
        "protocol_digest":digest(PROTOCOL),
        "fixed_native_event":{"seed":7,"generation":11,"address":19,"pair":[0,1]},
        "controls":{
            "same_shift_bucket_10_18":{"masks":[same_a,same_b],"equal":True,
                "trace_bonuses":[0,0],"bond":0,"shift":5},
            "threshold_crossing_31_32":{"masks":[edge_a,edge_b],"different":True,
                "widths":[edge_a.bit_count(),edge_b.bit_count()],"bonuses":[0,1],
                "selected_mask_subset":True,"bond":0,"shift":5},
            "saturated_bond_0_255":{"masks":[saturation_a,saturation_b],"equal":True,
                "width":16,"bond":255,"shift":5},
            "inert_shift_0_255":{"masks":[inert_a,inert_b],"equal":True,
                "width":1,"bond":0,"shift":8},
            "generic_write_equal":_generic_write(),
        },
        "limits":{
            "real_B_vs_H_teacher_paired":False,
            "real_transfer_handoff_observed_here":False,
            "latent_outcome_differential_proven":False,
            "autonomous_output_or_learning_proven":False,
            "independent_heldout_tested":False,
            "genetic_diversity_or_overfit_measured":False,
            "learning_claim":False,
        },
        "interpretation":"trace difference may be in same quantization bucket or mask saturated; threshold creates only latent read opportunity; selected contact and downstream change still necessary",
    }
    results["digest"]=digest(results)
    return results


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if len(args.source_sha)!=40 or any(c not in "0123456789abcdef" for c in args.source_sha):
        p.error("expected exact 40-character source SHA")
    report=evaluate()
    report["source_sha"]=args.source_sha
    report.pop("digest")
    report["digest"]=digest(report)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({"issue":report["issue"],"digest":report["digest"],
                      "threshold_crossing":report["controls"]["threshold_crossing_31_32"],
                      "limits":report["limits"]},sort_keys=True),flush=True)


if __name__=="__main__":
    main()
