"""#219: bounded source-bound profile of actual native CPU hot paths.

This is a test-only, disposable study, NOT D16 extended science.
No accepted physics, fitness, optimizer, seed, snapshot, or backend is changed.
"""
from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import os
from pathlib import Path
import platform
import pstats
import subprocess
import sys
import time

from core.experiment import ExperimentConfig, IOExperiment, measure_trained_state
from core.physics import PhysicsConfig, create_universe, step
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

ISSUE = 219
TEST_SEED = 0
SHORT_TIMEOUT = 2


def source_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()


def rss_bytes() -> int | None:
    try:
        with Path("/proc/self/statm").open("r", encoding="ascii") as stream:
            fields = stream.read().split()
        return int(fields[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, AttributeError):
        return None


def profile_call(name: str, fn):
    profiler = cProfile.Profile()
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    profiler.enable()
    result = fn()
    profiler.disable()
    wall = time.perf_counter() - start_wall
    cpu = time.process_time() - start_cpu
    stats = pstats.Stats(profiler)
    ranked = sorted(
        (
            {"file": str(key[0]).replace(chr(92), "/").rsplit("/", 2)[-1],
             "line": key[1], "function": key[2],
             "calls": calls, "primitive_calls": primitive,
             "self_seconds": self_t, "cumulative_seconds": cumulative}
            for key, (primitive, calls, self_t, cumulative, _callers) in stats.stats.items()
        ),
        key=lambda row: row["cumulative_seconds"],
        reverse=True,
    )
    return {"name": name, "wall_seconds": wall, "cpu_seconds": cpu,
            "function_calls": stats.total_calls, "top_cumulative": ranked[:28],
            "rss_after_bytes": rss_bytes()}, result


def physics_case(density: int, generations: int):
    state = create_universe(
        seed=TEST_SEED, config=PhysicsConfig(initial_density=density),
    )
    def work():
        for _ in range(generations):
            step(state)
    measurement, _ = profile_call(f"physical_density_{density}", work)
    measurement.update({"physical_generations": generations,
                        "final_generation": state.generation,
                        "final_state_sha256": digest(state.to_snapshot())})
    return measurement


def active_slots_microbenchmark():
    """Exact-output isolated microbenchmark, NOT claimed optimizer speedup."""
    try:
        import numpy as np
        from numba import njit
    except ImportError as exc:
        return {"status": "UNAVAILABLE", "reason": str(exc)}
    @njit
    def compiled_active_index(array):
        out = []
        for index in range(len(array)):
            if array[index] == 1:
                out.append(index)
        return out
    report = []
    for density in (4, 32, 128):
        state = create_universe(seed=TEST_SEED, config=PhysicsConfig(initial_density=density))
        def list_index_search():
            out = []
            start = 0
            while True:
                try:
                    found = state.lifecycle.index(1, start)
                except ValueError:
                    return out
                out.append(found)
                start = found + 1

        def byte_find_search():
            packed = bytes(state.lifecycle)
            out = []
            start = 0
            while True:
                found = packed.find(b"\\x01", start)
                if found < 0:
                    return out
                out.append(found)
                start = found + 1
        reference = state.active_slots()
        array = np.asarray(state.lifecycle, dtype=np.uint8)
        compile_at = time.perf_counter()
        initial = compiled_active_index(array)
        compilation_wall_s = time.perf_counter() - compile_at
        numpy_indices = np.flatnonzero(array == 1).tolist()
        if reference != list(initial) or reference != numpy_indices:
            raise AssertionError("Numba/NumPy active-slot index parity failure")
        iterations = 1000
        def sample(fn):
            start = time.perf_counter()
            for _ in range(iterations):
                value = fn()
            return {"mean_microseconds": (time.perf_counter() - start) * 1e6 / iterations,
                    "correct": list(value) == reference}
        row = {"density": density, "max_cells": state.max_cells,
               "actual_active_cells": len(reference),
               "numba_first_compile_and_call_seconds": compilation_wall_s,
               "python_list_scan": sample(state.active_slots),
               "python_list_index": sample(list_index_search),
               "python_bytes_find_with_conversion": sample(byte_find_search),
               "numpy_with_per_call_conversion": sample(
                   lambda: np.flatnonzero(np.asarray(state.lifecycle, dtype=np.uint8) == 1).tolist()),
               "numba_with_per_call_conversion": sample(
                   lambda: list(compiled_active_index(np.asarray(state.lifecycle, dtype=np.uint8)))),
               "numba_persistent_array_kernel_only": sample(lambda: list(compiled_active_index(array)))}
        if not all(row[k]["correct"] for k in
                   ("python_list_scan", "python_list_index", "python_bytes_find_with_conversion",
                    "numpy_with_per_call_conversion", "numba_with_per_call_conversion",
                    "numba_persistent_array_kernel_only")):
            raise AssertionError("active slot microbenchmark parity regression")
        report.append(row)
    return {"status": "MEASURED", "isolated_only": True,
            "non_authoritative": True, "not_full_physics_speedup": True,
            "cases": report}


def run(physical_generations: int, run_micro: bool) -> dict:
    protocol = ExperimentConfig(evaluation_timeout_generations=SHORT_TIMEOUT)
    before = time.perf_counter()
    cases = [physics_case(density, physical_generations) for density in (4, 32, 128)]
    training = create_universe(seed=TEST_SEED, config=PhysicsConfig(initial_density=32))
    training_profile, _ = profile_call(
        "single_training_episode", lambda: IOExperiment(training, experiment=protocol).train_mappings(),
    )
    training_profile["final_physical_generation"] = training.generation
    training_profile["state_sha256"] = digest(training.to_snapshot())
    evaluation_profile, _ = profile_call(
        "posttraining_measurement_with_disposable_clones",
        lambda: measure_trained_state(training, experiment=protocol),
    )
    evaluation_profile["state_unchanged"] = training_profile["state_sha256"] == digest(training.to_snapshot())
    if not evaluation_profile["state_unchanged"]:
        raise AssertionError("read-only evaluation mutated authoritative state")
    optimizer = SteadyStateOptimizer.from_defaults(base_seed=TEST_SEED, experiment=protocol)
    native = []
    for index in (0, 32, 64, 96):
        p, _ = profile_call(
            f"native_evaluate_slot_{index}", lambda idx=index: optimizer._evaluate_slot(optimizer.slots[idx]),
        )
        p["slot"] = index
        p["category"] = optimizer.slots[index].category
        p["physical_generation"] = optimizer.slots[index].state.generation
        native.append(p)
    # A single disposable default-timeout evaluation profile to cover the
    # actual 1024-generation clone-evaluation path, never D16 seed16384/selection.
    default_optimizer = SteadyStateOptimizer.from_defaults(base_seed=TEST_SEED)
    full_timeout_slot_profile, _ = profile_call(
        "single_slot_default_timeout1024",
        lambda: default_optimizer._evaluate_slot(default_optimizer.slots[0]),
    )
    full_timeout_slot_profile["slot"] = 0
    full_timeout_slot_profile["timeout_generations"] = 1024
    full_timeout_slot_profile["base_seed"] = TEST_SEED
    return {
        "schema_version": 1, "issue": ISSUE, "kind": "TestOnlyNativeCpuProfiler",
        "source_sha": source_head(), "base_seed": TEST_SEED,
        "experiment_timeout_generations": SHORT_TIMEOUT,
        "physical_default_unchanged": True,
        "native_full128_science_run": False,
        "learning_claim": False, "performance_observations_are_host_specific": True,
        "environment": {"python": platform.python_version(),
                        "machine": platform.machine(), "system": platform.platform(),
                        "cpu_count": os.cpu_count()},
        "report": {"physical_cases": cases, "training": training_profile,
                   "evaluation_clone": evaluation_profile,
                   "native_evaluate_slots": native,
                   "single_default_timeout_slot": full_timeout_slot_profile,
                   "active_slot_kernel_microbenchmark": (
                       active_slots_microbenchmark() if run_micro else {"status": "SKIPPED"})},
        "measured_total_wall_seconds": time.perf_counter() - before,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--physical-generations", type=int, default=96)
    p.add_argument("--without-numba-micro", action="store_true")
    args = p.parse_args(argv)
    if not 1 <= args.physical_generations <= 256:
        p.error("physical generations must be between 1 and 256")
    report = run(args.physical_generations, not args.without_numba_micro)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    measured = report["report"]
    examined = [
        *measured["physical_cases"],
        measured["training"],
        measured["evaluation_clone"],
        *measured["native_evaluate_slots"],
        measured["single_default_timeout_slot"],
    ]
    summary = {
        "issue": ISSUE, "source_sha": report["source_sha"],
        "profiles": {
            row["name"]: {
                "wall_seconds": row["wall_seconds"],
                "cpu_seconds": row["cpu_seconds"],
                "top_self_seconds": sorted(row["top_cumulative"],
                                           key=lambda item: item["self_seconds"],
                                           reverse=True)[:8],
                "top_cumulative_seconds": row["top_cumulative"][:8],
            }
            for row in examined
        },
        "active_slot_kernel_microbenchmark": measured["active_slot_kernel_microbenchmark"],
        "total_wall_seconds": report["measured_total_wall_seconds"],
        "test_only": True,
    }
    print(json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
