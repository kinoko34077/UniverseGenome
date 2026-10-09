"""D15 #213 native per-world CPU process probe (research only; NO selection).

Never modifies native physics, source v7 or production search. Investigates
real CPU process/IPC/RSS costs of independent physical world evaluations.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import gc
import json
import multiprocessing
from pathlib import Path
import time
from typing import Any

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d8_genome_diversity_190 import digest
from research.d15_sparse_recovery_213 import ResourceBudget
from search.evolution import SteadyStateOptimizer, UniverseSlot


PROBE_INDICES=(0,1,32,33,64,65,96,97)


def evaluate_world(request:dict[str,Any])->dict[str,Any]:
    """A complete private Universe per worker, never shared mutation."""
    physics=PhysicsConfig.from_mapping(request["base_config"])
    protocol=ExperimentConfig.from_mapping(request["experiment"])
    slot=UniverseSlot.from_dict(request["slot"],base_config=physics)
    evaluator=SteadyStateOptimizer((),base_config=physics,experiment=protocol)
    evaluator._evaluate_slot(slot)
    return {"index":slot.index,"slot":slot.to_dict(),
            "worker_rss_bytes":ResourceBudget.current_rss_bytes()}


def _canonical_results(results:list[dict[str,Any]])->list[dict[str,Any]]:
    return [dict(index=value["index"],slot=value["slot"])
            for value in sorted(results,key=lambda r:r["index"])]


def run_probe()->dict[str,Any]:
    physics=PhysicsConfig()
    protocol=ExperimentConfig(evaluation_timeout_generations=2)
    budget=ResourceBudget(memory_mib=1536)
    initial=SteadyStateOptimizer.from_defaults(
        base_seed=0,base_config=physics,experiment=protocol)
    requests=[
        {"slot":initial.slots[index].to_dict(),
         "base_config":physics.to_dict(),
         "experiment":protocol.to_dict()}
        for index in PROBE_INDICES
    ]
    del initial
    gc.collect()
    input_bytes=sum(len(json.dumps(request,separators=(",",":"))) for request in requests)
    parent_rss=ResourceBudget.current_rss_bytes()
    host=ResourceBudget.available_host_bytes()
    # Keep at least 25% host headroom; no more than two workers.
    budget.admit(estimated_additional_bytes=2*384*1024*1024,
                 current_rss_bytes=parent_rss,available_host_bytes=host)
    t=time.perf_counter()
    sequential=[evaluate_world(request) for request in requests]
    serial_seconds=time.perf_counter()-t
    t=time.perf_counter()
    with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context("spawn")) as executor:
        parallel=list(executor.map(evaluate_world,requests,timeout=120))
    two_worker_seconds=time.perf_counter()-t
    serial_state=_canonical_results(sequential)
    parallel_state=_canonical_results(parallel)
    assert serial_state==parallel_state,"D15 CPU process path changed authoritative world state"
    measured_worker_rss=sum(sorted(
        [int(r["worker_rss_bytes"]) for r in parallel],reverse=True)[:2])
    if measured_worker_rss+parent_rss>budget.limit_bytes:
        decision="REJECT_PARALLEL_MEMORY"
    elif two_worker_seconds < serial_seconds*0.9:
        decision="PARALLEL_CANDIDATE_ONLY_REQUIRES_REPLICATE"
    else:
        decision="NO_PARALLEL_ADOPTION_FOR_THIS_FIXTURE"
    return {
        "issue":213,
        "mode":"independent_nonselecting_world_evaluation",
        "worlds":len(PROBE_INDICES),
        "world_indices":list(PROBE_INDICES),
        "native_state_sha256":digest(serial_state),
        "serial_seconds":round(serial_seconds,5),
        "parallel_two_workers_seconds":round(two_worker_seconds,5),
        "input_json_bytes":input_bytes,
        "output_json_bytes":sum(len(json.dumps(x,separators=(",",":"))) for x in parallel_state),
        "measured_parent_rss_bytes":parent_rss,
        "max_two_worker_reported_rss_bytes":measured_worker_rss,
        "budget_mib":budget.memory_mib,
        "decision":decision,
        "genetic_selection_performed":False,
        "learning_claim":False,
        "independent_heldout_tested":False,
    }


def main()->None:
    result=run_probe()
    output=Path("d15-cpu-worker-probe-213.json")
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
