"""D13 #204: bounded and deterministic research controls around legacy Outer.

'Native' is the unchanged fixed 128-world optimizer. 'Sampled' is
non-selecting disposable training of initial worlds, never a genetic cohort.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig, create_universe
from core.population import CATEGORY_OPERATORS
from research.d8_genome_diversity_190 import digest
from search.evolution import (
    OPTIMIZER_POPULATION_SIZE, SLOTS_PER_CATEGORY,
    SteadyStateOptimizer, UniverseSlot,
)
from search.genome import UniverseGenome
from search.outer_search import legacy_mutation_plan_for_base_config

MAX_WORLD_ROUNDS = 512
MAX_WORK_UNITS = 10_000_000
MAX_RESIDENT_BYTES = 768 * 1024 * 1024
BYTES_PER_CELL_BOUND = 4096
MAX_BATCH_WORLDS = 16
MAX_CELL_CAPACITY = 1024


@dataclass(frozen=True)
class OuterResearchPlan:
    """Research-only plan. All admission is before creating a Universe."""

    mode: str = "native_selection"
    base_seed: int = 0
    outer_steps: int = 1
    evaluated_worlds: int = OPTIMIZER_POPULATION_SIZE
    worlds_per_batch: int = OPTIMIZER_POPULATION_SIZE
    max_wall_seconds: int = 900

    def validate(
        self, *, physics: PhysicsConfig, experiment: ExperimentConfig
    ) -> dict[str, int]:
        for field in ("base_seed","outer_steps","evaluated_worlds","worlds_per_batch","max_wall_seconds"):
            value=getattr(self,field)
            if type(value) is not int:
                raise ValueError(f"D13 {field} must be an integer")
        if self.mode not in ("native_selection","sampled_evaluation"):
            raise ValueError("D13 unknown mode")
        if self.base_seed<0 or self.base_seed>0x7FFFFFFF:
            raise ValueError("D13 base seed outside bounded signed-32 range")
        if not 0<=self.outer_steps<=64 or not 1<=self.evaluated_worlds<=128:
            raise ValueError("D13 Outer steps/world count exceed safe plan range")
        if not 1<=self.max_wall_seconds<=3600:
            raise ValueError("D13 max wall seconds must be 1..3600")
        if self.mode=="native_selection":
            if self.evaluated_worlds!=128 or self.worlds_per_batch!=128:
                raise ValueError("D13 native selection requires full legacy 128 worlds; batching is not implemented there")
            resident=128
        else:
            if not 1<=self.worlds_per_batch<=min(self.evaluated_worlds,MAX_BATCH_WORLDS):
                raise ValueError("D13 sampled batch must be bounded within 1..16")
            resident=self.worlds_per_batch
        if not 1<=physics.max_cells<=MAX_CELL_CAPACITY:
            raise ValueError("D13 rejects oversized physics cell arrays")
        world_rounds=self.evaluated_worlds*self.outer_steps
        if world_rounds>MAX_WORLD_ROUNDS:
            raise ValueError("D13 estimated world rounds exceed hard limit")
        # A conservative provision for repeated disposable clone evaluation.
        # The count is an admission estimate, not measured native CPU cycles.
        mapping_train=sum(
            (len(m.input_bytes)*experiment.byte_hold_generations
             + (len(m.input_bytes)-1)*experiment.inter_input_generations
             + experiment.byte_gap_generations
             + experiment.teacher_delay_generations
             + len(m.output_bytes if getattr(m,"output_bytes",()) else
                   (m.output_byte,)*experiment.output_event_count)
             + max(0,experiment.output_event_count-1)*
               max(0,experiment.output_event_interval_generations-1)
             + 1)
            for m in experiment.mappings
        )*experiment.teacher_repetitions
        cost=world_rounds*(mapping_train+16*experiment.evaluation_timeout_generations)
        if cost>MAX_WORK_UNITS:
            raise ValueError("D13 estimated physical evaluation work exceeds fixed budget")
        projected_memory=resident*physics.max_cells*BYTES_PER_CELL_BOUND
        if projected_memory>MAX_RESIDENT_BYTES:
            raise ValueError("D13 conservative resident state memory budget exceeded")
        if experiment.retention_enabled or experiment.noise_robustness_enabled or experiment.held_out_mapping is not None:
            raise ValueError("D13 initially disallows auxiliary expensive evaluation branches")
        return {
            "world_rounds":world_rounds,
            "estimated_physics_work":cost,
            "resident_world_limit":resident,
            "resident_memory_estimate_bytes":projected_memory,
            "physical_generations_per_world_round":mapping_train,
        }


def _write_snapshot(path:Path,state:dict[str,Any])->None:
    """Commit a complete optimizer round, never a partially evaluated cohort."""
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    try:
        temp.write_text(json.dumps(state,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
        os.replace(temp,path)
    finally:
        if temp.exists():
            temp.unlink()


def _sample_indices(total:int)->tuple[int,...]:
    """Category-balanced prefix across the same original 128 physical slot IDs."""
    return tuple((position%len(CATEGORY_OPERATORS))*SLOTS_PER_CATEGORY
                 +(position//len(CATEGORY_OPERATORS)) for position in range(total))


def execute(
    plan:OuterResearchPlan,
    *,
    physics:PhysicsConfig|None=None,
    experiment:ExperimentConfig|None=None,
    snapshot_out:Path|None=None,
    resume_snapshot:Path|None=None,
)->dict[str,Any]:
    base=physics or PhysicsConfig()
    protocol=experiment or ExperimentConfig()
    admission=plan.validate(physics=base,experiment=protocol)
    if plan.mode!="native_selection" and (snapshot_out or resume_snapshot):
        raise ValueError("D13 snapshot resume only applies to native full population")
    started=time.monotonic()
    output={
        "issue":204,"mode":plan.mode,"plan":vars(plan),
        "admission":admission,
        "research_only":True,
        "genetic_selection_performed":plan.mode=="native_selection" and plan.outer_steps>0,
        "learning_claim":False,
        "independent_heldout_tested":False,
        "rounds":[],
    }
    if plan.mode=="native_selection":
        if resume_snapshot is not None:
            raw=json.loads(resume_snapshot.read_text(encoding="utf-8"))
            optimizer=SteadyStateOptimizer.from_snapshot(raw)
            if optimizer.experiment.to_dict()!=protocol.to_dict() or optimizer.base_config.to_dict()!=base.to_dict():
                raise ValueError("D13 resume protocol/config mismatches requested plan")
            if optimizer.search_plan.scheduler_base_seed!=plan.base_seed:
                raise ValueError("D13 resume search seed differs from accepted original")
        else:
            optimizer=SteadyStateOptimizer.from_defaults(base_seed=plan.base_seed,
                                                        base_config=base,experiment=protocol)
        output["start_optimizer_generation"]=optimizer.generation
        output["starting_state_digest"]=digest(optimizer.to_snapshot())
        for _ in range(plan.outer_steps):
            if time.monotonic()-started>plan.max_wall_seconds:
                raise TimeoutError("D13 wall budget expired between full native rounds; last complete snapshot retained")
            result=optimizer.step()  # unmodified authoritative selection, 128 worlds
            if snapshot_out is not None:
                _write_snapshot(snapshot_out,optimizer.to_snapshot())
            output["rounds"].append({
                "outer_generation":result["generation"],
                "evaluated_slots":result["evaluated_slots"],
                "replacements":result["replacement_count"],
                "pruned":result["pruned_count"],
                "state_digest":digest(optimizer.to_snapshot()),
            })
        output["final_optimizer_generation"]=optimizer.generation
        output["final_state_digest"]=digest(optimizer.to_snapshot())
        output["scheduler"]=dict(optimizer.scheduler)
    else:
        genomes=UniverseGenome.initial_population()
        shell=SteadyStateOptimizer(
            (),base_config=base,experiment=protocol,
            search_plan=legacy_mutation_plan_for_base_config(base,base_seed=plan.base_seed),
        )
        records=[]
        indexes=_sample_indices(plan.evaluated_worlds)
        for first in range(0,len(indexes),plan.worlds_per_batch):
            if time.monotonic()-started>plan.max_wall_seconds:
                raise TimeoutError("D13 sampled batch budget expired; no genetic state accepted")
            slots=[]
            for index in indexes[first:first+plan.worlds_per_batch]:
                category=CATEGORY_OPERATORS[index//32]
                local_index=index%32
                genome=genomes[local_index//4]
                seed=plan.base_seed+local_index
                config=SteadyStateOptimizer._effective_config(genome,category,base)
                slots.append(UniverseSlot(
                    index=index,category=category,genome=genome,seed=seed,
                    state=create_universe(seed=seed,config=config),
                    evidence_mature=True,
                ))
            for slot in slots:
                for _ in range(plan.outer_steps):
                    shell._evaluate_slot(slot)
                records.append({
                    "index":slot.index,"category":slot.category,
                    "seed":slot.seed,"physical_generation":slot.state.generation,
                    "growth_windows":list(slot.growth_windows),
                    "state_digest":digest(slot.state.to_snapshot()),
                    "fitness":slot.fitness.to_dict(),
                })
            del slots
        output["evaluated_world_ids"]=list(indexes)
        output["sampled_world_results"]=sorted(records,key=lambda x:x["index"])
        output["selection_not_applicable"]=True
    output["digest"]=digest(output)
    return output


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("native_selection","sampled_evaluation"),default="native_selection")
    p.add_argument("--base-seed",type=int,default=0)
    p.add_argument("--outer-steps",type=int,default=1)
    p.add_argument("--evaluated-worlds",type=int,default=128)
    p.add_argument("--worlds-per-batch",type=int,default=128)
    p.add_argument("--max-wall-seconds",type=int,default=900)
    p.add_argument("--snapshot-out",type=Path)
    p.add_argument("--resume-snapshot",type=Path)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    plan=OuterResearchPlan(args.mode,args.base_seed,args.outer_steps,args.evaluated_worlds,
                           args.worlds_per_batch,args.max_wall_seconds)
    report=execute(plan,snapshot_out=args.snapshot_out,resume_snapshot=args.resume_snapshot)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({"issue":204,"mode":plan.mode,"digest":report["digest"],
                      "world_rounds":report["admission"]["world_rounds"],
                      "selection":report["genetic_selection_performed"]},sort_keys=True))


if __name__=="__main__":
    main()
