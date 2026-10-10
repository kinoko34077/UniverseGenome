"""PERF5 #219 disposable CPU multi-world and typed-array A/B, not a runtime backend.

Frozen science: seed0 only, selected128 uses timeout=2, at most 16 slots at
default timeout=1024. No D16 seed16384, no 37-step growth-window observation.
Only the parent process may invoke authoritative native selection.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from multiprocessing import get_context, get_all_start_methods
import os
from pathlib import Path
import platform
import resource
import subprocess
import time
from typing import Any

from core.experiment import ExperimentConfig
from core.state import Lifecycle
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer, UniverseSlot

SHORT_GOLDEN = "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321"
DEFAULT_SLOT_GOLDEN = "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"
DEFAULT_INDICES = tuple(i + j for i in (0, 32, 64, 96) for j in range(4))
_FORK_OPT: SteadyStateOptimizer | None = None


def _rss_bytes() -> int | None:
    try:
        with open("/proc/self/statm", encoding="ascii") as stream:
            resident = int(stream.read().split()[1])
        return resident * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, AttributeError, IndexError):
        return None


def _child_evaluate_indices(indices: tuple[int, ...]) -> dict[str, Any]:
    # This module global is a snapshot inherited via Linux fork, NOT an
    # authorized shared-writer or a production persistent execution service.
    opt = _FORK_OPT
    if opt is None:
        raise RuntimeError("PERF5 fork optimizer was not initialized")
    out = []
    for index in indices:
        slot = opt.slots[index]
        if slot.index != index:
            raise AssertionError("native positional identity changed")
        opt._evaluate_slot(slot)
        out.append((index, slot.to_dict()))
    return {"slots": out, "pid": os.getpid(),
            "rss_after_bytes": _rss_bytes(),
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def _reference(indices: tuple[int, ...], *, full_selection: bool, short: bool) -> dict:
    protocol = ExperimentConfig(evaluation_timeout_generations=2) if short else None
    opt = SteadyStateOptimizer.from_defaults(base_seed=0, experiment=protocol)
    begin = time.perf_counter()
    for idx in indices:
        opt._evaluate_slot(opt.slots[idx])
    if full_selection:
        if len(indices) != 128:
            raise ValueError("full selection requires exactly 128 original slots")
        opt._finalize_evaluated_step(evaluated_slots=128, started=begin)
    elapsed = time.perf_counter() - begin
    sha = digest(opt.to_snapshot())
    return {"wall_seconds": elapsed, "sha256": sha, "rss_bytes": _rss_bytes(),
            "selection_commits": int(full_selection), "results": len(indices),
            "generation": opt.generation}


def _parallel(indices: tuple[int, ...], *, full_selection: bool,
              short: bool, workers: int, batch_size: int) -> dict:
    if workers not in (2, 4) or batch_size < 1:
        raise ValueError("bounded worker count/batch required")
    if "fork" not in get_all_start_methods() or os.name != "posix":
        raise RuntimeError("PERF5 fork method only supported on POSIX Linux")
    protocol = ExperimentConfig(evaluation_timeout_generations=2) if short else None
    opt = SteadyStateOptimizer.from_defaults(base_seed=0, experiment=protocol)
    batches = tuple(tuple(indices[i:i + batch_size])
                    for i in range(0, len(indices), batch_size))
    global _FORK_OPT
    if _FORK_OPT is not None:
        raise RuntimeError("nested PERF5 reference state")
    _FORK_OPT = opt
    begin = time.perf_counter()
    try:
        # The entire pool is instantiated AFTER read-only full 128-world
        # default optimizer creation, so Linux fork shares immutable pages.
        # Child instances mutate copy-on-write private states, never parent.
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("fork")) as pool:
            results = list(pool.map(_child_evaluate_indices, batches))
    finally:
        _FORK_OPT = None

    result_by_index: dict[int, dict] = {}
    for group in results:
        for index, payload in group["slots"]:
            if index in result_by_index or index not in indices:
                raise AssertionError("duplicate or unauthorized slot result")
            result_by_index[index] = payload
    if set(result_by_index) != set(indices):
        raise AssertionError("missing evaluated slot cannot commit selection")
    # Fail closed on original slot order, category and seed provenance.
    for index in indices:
        old = opt.slots[index]
        reconstructed = UniverseSlot.from_dict(result_by_index[index],
                                                base_config=opt.base_config)
        if (reconstructed.index != index or reconstructed.seed != old.seed
                or reconstructed.category != old.category or
                reconstructed.genome_key != old.genome_key):
            raise AssertionError("worker altered preselection slot identity")
        opt.slots[index] = reconstructed
    # Exactly one native selection in PARENT, after all 128 authenticated
    # ordered results. This standalone benchmark does not use/write D15
    # journal, and therefore is NOT D15 crash/resume integration evidence.
    if full_selection:
        if len(indices) != 128:
            raise ValueError("full selection requires exactly 128")
        opt._finalize_evaluated_step(evaluated_slots=128, started=begin)
    elapsed = time.perf_counter() - begin
    return {"wall_seconds": elapsed, "sha256": digest(opt.to_snapshot()),
            "results":len(indices), "selection_commits":int(full_selection),
            "generation":opt.generation, "workers":workers,
            "batch_size":batch_size, "worker_tasks":len(batches),
            "worker_pids":sorted(set(g["pid"] for g in results)),
            "worker_rss_after_bytes":[g["rss_after_bytes"] for g in results],
            "worker_peak_rss_bytes":[g["peak_rss_bytes"] for g in results],
            "parent_rss_bytes":_rss_bytes()}


def measure_process_scaling(*, default_slots: int = 16) -> dict:
    if default_slots != 16:
        raise ValueError("PERF5 freeze requires exactly 16 default slots")
    out = {}
    for name, indices, selection, short in (
        ("selected128_timeout2", tuple(range(128)), True, True),
        ("default1024_16slot_mixed_categories", DEFAULT_INDICES, False, False),
    ):
        reference = _reference(indices, full_selection=selection, short=short)
        if selection and reference["sha256"] != SHORT_GOLDEN:
            raise AssertionError("accepted native128 selected golden mismatch")
        if not selection:
            check = _reference((0,), full_selection=False, short=False)
            if check["sha256"] != DEFAULT_SLOT_GOLDEN:
                raise AssertionError("accepted native default slot0 state drift")
        tests = []
        for workers in (2, 4):
            candidate = _parallel(indices, full_selection=selection, short=short,
                                  workers=workers, batch_size=4)
            if (candidate["sha256"] != reference["sha256"]
                    or candidate["generation"] != reference["generation"]
                    or candidate["results"] != reference["results"]
                    or candidate["selection_commits"] != reference["selection_commits"]):
                raise AssertionError("parallel full optimizer selected-state divergence")
            candidate["strict_whole_optimizer_parity"] = True
            candidate["relative_speedup"] = reference["wall_seconds"] / candidate["wall_seconds"]
            tests.append(candidate)
        out[name] = {"reference": reference, "parallel": tests,
                     "seed":0, "time_limit_generations":2 if short else 1024,
                     "selected_worlds":128 if selection else 0}
    return out


def scan_kernel_trial(iterations: int = 2000) -> dict:
    if not 1 <= iterations <= 10000:
        raise ValueError("iterations outside test-only bound")
    import numpy as np
    from numba import njit

    @njit
    def collect_typed(arr):
        active = np.empty(len(arr), dtype=np.int32)
        holes = np.empty(len(arr), dtype=np.int32)
        a = 0
        h = 0
        for i in range(len(arr)):
            v = arr[i]
            if v == 1:
                active[a] = i
                a += 1
            elif v == 2:
                holes[h] = i
                h += 1
        return active[:a], holes[:h]

    def reference_collect(lifecycle):
        active, holes = [], []
        for status, dest in ((1, active), (2, holes)):
            start = 0
            while True:
                try:
                    i = lifecycle.index(status, start)
                except ValueError:
                    break
                dest.append(i)
                start = i + 1
        return active, holes

    trials = []
    for density in (0, 8, 128, 512):
        # Fixed in-range integer lifecycle labels for deterministic parity,
        # independent of actual source mutation/state execution.
        lifecycle = ([2 if i % 193 == 0 else 1 if i % 1024 < density else 0
                      for i in range(1024)])
        expected = reference_collect(lifecycle)
        typed = np.asarray(lifecycle, dtype=np.uint8)
        at = time.perf_counter()
        first = collect_typed(typed)
        compile_seconds = time.perf_counter() - at
        if (first[0].tolist(), first[1].tolist()) != expected:
            raise AssertionError("persistent typed kernel classification differs")
        if (np.flatnonzero(typed == 1).tolist(),
                np.flatnonzero(typed == 2).tolist()) != expected:
            raise AssertionError("NumPy vector classification differs")

        def sample(fn):
            start = time.perf_counter()
            for _ in range(iterations):
                result = fn()
            elapsed = time.perf_counter() - start
            if (list(result[0]), list(result[1])) != expected:
                raise AssertionError("backend output drift")
            return elapsed * 1e6 / iterations

        trials.append({
            "active_cells":len(expected[0]), "blackholes":len(expected[1]),
            "numba_first_compile_plus_call_seconds":compile_seconds,
            "reference_python_index_us":sample(lambda:reference_collect(lifecycle)),
            "numpy_conversion_per_call_us":sample(
                lambda:(np.flatnonzero(np.asarray(lifecycle,dtype=np.uint8)==1),
                        np.flatnonzero(np.asarray(lifecycle,dtype=np.uint8)==2))),
            "numba_conversion_per_call_us":sample(
                lambda:collect_typed(np.asarray(lifecycle,dtype=np.uint8))),
            "numba_persistent_array_us":sample(lambda:collect_typed(typed)),
        })
    return {
        "status":"ISOLATED_CLASSIFICATION_ONLY",
        "no_physics_step_replacement":True,
        "no_state_mutation_mirroring_proven":True,
        "iterations_each": iterations,
        "cases":trials,
    }


def run_all() -> dict:
    if not sys_platform_linux():
        raise RuntimeError("PERF5 Linux/fork-only benchmark")
    source = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    return {
        "schema":1, "issue":219, "source_sha":source,
        "kind":"PERF5_test_only_128world_fork_and_numba_classification",
        "environment":{"python":platform.python_version(),"platform":platform.platform(),
                       "cpu_count":os.cpu_count(),"pid":os.getpid()},
        "numba":scan_kernel_trial(),
        "process_scaling":measure_process_scaling(),
        "learning_claim":False, "D16_seed16384_extended_science":False,
        "D15_journal_integrated":False, "production_backend_changed":False,
    }


def sys_platform_linux() -> bool:
    return platform.system()=="Linux"


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    result = run_all()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    short = result["process_scaling"]["selected128_timeout2"]
    default = result["process_scaling"]["default1024_16slot_mixed_categories"]
    print(json.dumps({
        "source_sha":result["source_sha"], "kind":result["kind"],
        "host_cpu_count":result["environment"]["cpu_count"],
        "numba":result["numba"],
        "short_native128":{"serial_s":short["reference"]["wall_seconds"],
                           "parallel":[{"workers":x["workers"],"wall_s":x["wall_seconds"],
                                        "ratio":x["relative_speedup"],
                                        "digest":x["sha256"]} for x in short["parallel"]],
                           "digest":short["reference"]["sha256"]},
        "default1024_16":{"serial_s":default["reference"]["wall_seconds"],
                          "parallel":[{"workers":x["workers"],"wall_s":x["wall_seconds"],
                                       "ratio":x["relative_speedup"]} for x in default["parallel"]],
                          "digest":default["reference"]["sha256"]},
        "science":False,
    },sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
