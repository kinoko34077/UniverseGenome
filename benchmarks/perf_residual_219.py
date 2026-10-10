"""PERF #219 after two accepted C-backed index refactors: residual CPU profile.

Disposable native seed0 one-slot default ExperimentConfig (timeout1024).
No D16 extended selected128 default seed16384 or learning evidence.
"""
from __future__ import annotations

import argparse
import cProfile
from dataclasses import dataclass
import json
from pathlib import Path
import platform
import pstats
import subprocess
import time
from typing import Callable, TypeVar

from core.physics import PhysicsConfig, create_universe, step
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

ORACLE_SLOT0_DEFAULT_1024 = "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"
T = TypeVar("T")


def run_profile(operation: Callable[[], T], *, top: int = 30) -> tuple[dict, T]:
    profiler = cProfile.Profile()
    begin_cpu = time.process_time()
    begin_wall = time.perf_counter()
    profiler.enable()
    result = operation()
    profiler.disable()
    wall = time.perf_counter() - begin_wall
    cpu = time.process_time() - begin_cpu
    rows = []
    for (path, line, fn), (primitive, calls, self_s, cumulative_s, _) in pstats.Stats(profiler).stats.items():
        rows.append({
            "file": path.replace(chr(92), "/").split("/")[-1],
            "line": line, "function": fn,
            "calls": calls, "primitive_calls": primitive,
            "self_s": self_s, "cumulative_s": cumulative_s,
        })
    return {
        "wall_s": wall, "process_cpu_s": cpu,
        "top_self": sorted(rows, key=lambda item: item["self_s"], reverse=True)[:top],
        "top_cumulative": sorted(rows, key=lambda item: item["cumulative_s"], reverse=True)[:top],
    }, result


def profile_native_default_slot() -> dict:
    profiler_optimizer = SteadyStateOptimizer.from_defaults(base_seed=0)
    timing, _ = run_profile(
        lambda: profiler_optimizer._evaluate_slot(profiler_optimizer.slots[0])
    )
    current = digest(profiler_optimizer.to_snapshot())
    if current != ORACLE_SLOT0_DEFAULT_1024:
        raise AssertionError("post-refactor exact default1024 native slot0 snapshot changed")
    unprofiled_optimizer = SteadyStateOptimizer.from_defaults(base_seed=0)
    begin = time.perf_counter()
    unprofiled_optimizer._evaluate_slot(unprofiled_optimizer.slots[0])
    unprofiled_wall = time.perf_counter() - begin
    if digest(unprofiled_optimizer.to_snapshot()) != current:
        raise AssertionError("instrumentation changed original optimizer state")
    return {
        "cprofile": timing,
        "uninstrumented_wall_s": unprofiled_wall,
        "whole_optimizer_state_sha256": current,
        "full_native_selected128": False,
        "slots_evaluated": 1,
        "default_timeout_generations": 1024,
        "seed": 0,
    }


def profile_raw_physics(seed: int, density: int, generations: int) -> dict:
    state = create_universe(seed=seed, config=PhysicsConfig(initial_density=density))
    def work() -> None:
        for _ in range(generations):
            step(state)
    timing, _ = run_profile(work, top=12)
    return {
        "density": density, "generations": generations,
        "profile": timing, "digest": digest(state.to_snapshot()),
    }


def report(generations: int = 96) -> dict:
    if not 1 <= generations <= 256:
        raise ValueError("profile physical generations must be 1..256")
    source = subprocess.check_output(["git","rev-parse","HEAD"],text=True,timeout=10).strip()
    if len(source) != 40:
        raise ValueError("source SHA is not 40 hex")
    return {
        "schema_version": 1,
        "issue": 219,
        "source_sha": source,
        "kind": "PostTwoHotloopRefactorsResidualCpuProfiler",
        "provenance": {"python": platform.python_version(), "platform": platform.platform(),
                       "machine": platform.machine()},
        "native_default_slot0": profile_native_default_slot(),
        "raw_physics": [profile_raw_physics(0, density, generations) for density in (4,32,128)],
        "science_cohort": "disposable_existing_test_seed0_only",
        "D16_default_seed16384_long_science": False,
        "learning_claim": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--physical-generations", type=int, default=96)
    args = p.parse_args()
    result = report(args.physical_generations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    run = result["native_default_slot0"]
    profile = run["cprofile"]
    summary = {
        "source_sha": result["source_sha"],
        "native_one_slot_unprofiled_wall_s": run["uninstrumented_wall_s"],
        "native_one_slot_cprofile_wall_s": profile["wall_s"],
        "snapshot_sha256": run["whole_optimizer_state_sha256"],
        "top_self": profile["top_self"][:18],
        "top_cumulative": profile["top_cumulative"][:15],
        "raw_physics": [
            {"density": row["density"], "wall_s":row["profile"]["wall_s"],
             "top_self":row["profile"]["top_self"][:5]}
            for row in result["raw_physics"]
        ],
        "learning_claim": False,
    }
    print(json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
