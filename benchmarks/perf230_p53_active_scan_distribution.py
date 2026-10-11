"""PERF230 P5.3: measure ORIGINAL empty-ACTIVE scan frequency, no speed claim.

Read-only wrapper samples return lengths of the same core.state.UniverseState
active_slots() used by native original default1024 source evaluator.
Already exposed benchmark seed0 only; four native category representatives.
No actual D16 seed16384 scientific execution or physical source mutation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from core.state import UniverseState
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

FROZEN_SLOT0="e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"
CATEGORY_REPRESENTATIVES=(0,32,64,96)
SEED=0


def run(output:Path)->dict:
    source=subprocess.check_output(
        ["git","rev-parse","HEAD"],text=True,timeout=10,
    ).strip()
    if len(source)!=40 or any(c not in "0123456789abcdef" for c in source):
        raise ValueError("source cannot be pinned")
    results=[]
    original=UniverseState.active_slots
    for index in CATEGORY_REPRESENTATIVES:
        # One independent unchanged original reference before instrumentation
        baseline=SteadyStateOptimizer.from_defaults(base_seed=SEED)
        baseline._evaluate_slot(baseline.slots[index])
        original_sha=digest(baseline.to_snapshot())
        if index==0 and original_sha!=FROZEN_SLOT0:
            raise AssertionError("historical original slot0 source-v7 drift")
        profiled=SteadyStateOptimizer.from_defaults(base_seed=SEED)
        calls=0
        empty=0
        live_slots_sum=0
        max_live=0

        def wrapped(state:UniverseState)->list[int]:
            nonlocal calls,empty,live_slots_sum,max_live
            result=original(state)
            calls+=1
            empty+=len(result)==0
            live_slots_sum+=len(result)
            max_live=max(max_live,len(result))
            return result

        with patch.object(UniverseState,"active_slots",wrapped):
            profiled._evaluate_slot(profiled.slots[index])
        candidate_sha=digest(profiled.to_snapshot())
        if candidate_sha!=original_sha:
            raise AssertionError("count-only wrapper changed full native optimizer")
        if calls<=0:
            raise AssertionError("no real native physical/observer scans observed")
        row={
            "original_native_category_slot":index,
            "native_active_slots_calls":calls,
            "empty_active_calls":empty,
            "nonempty_active_calls":calls-empty,
            "zero_fraction":empty/calls,
            "mean_returned_active_cells":live_slots_sum/calls,
            "max_returned_active_cells":max_live,
            "whole_optimizer_v7_sha256":original_sha,
            "read_only_profiling":True,
        }
        print(json.dumps(row,sort_keys=True),flush=True)
        results.append(row)
    out={
        "kind":"PERF230_P53_SOURCE_NATIVE_ACTIVE_SCAN_DISTRIBUTION_ONLY",
        "source_sha":source,"seed":SEED,
        "original_default1024":True,
        "native_category_indices":list(CATEGORY_REPRESENTATIVES),
        "read_only_sample":True,
        "scientific_original_seed16384_run":False,
        "claim_900_seconds_achieved":False,
        "learning_claim":False,
        "rows":results,
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    return out


def main()->None:
    p=argparse.ArgumentParser(description="Native original four categories, count ACTIVE scans")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    run(args.output)


if __name__=="__main__":
    main()
