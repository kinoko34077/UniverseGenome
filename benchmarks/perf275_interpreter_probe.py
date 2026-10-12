"""PERF #275: frozen seed0 original source native slot0 CPython/PyPy study.

This never runs selected128 or original science seed16384. It checks the exact
native full optimizer-v7 digest for each native default1024 original slot.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import time
from statistics import median
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

SOURCE = "f0954171e912bedbe32dbc6ab221bc9da19cf66f"
GOLDEN = "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--repeats", type=int, default=6)
    args = p.parse_args()
    if not 4 <= args.repeats <= 8:
        raise ValueError("bounded repeats 4..8 only")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=10).strip()
    if actual != SOURCE:
        raise AssertionError("runtime probe must evaluate frozen accepted-science-independent source")
    trials = []
    for i in range(args.repeats):
        before_cpu = time.process_time()
        before_wall = time.perf_counter()
        opt = SteadyStateOptimizer.from_defaults(base_seed=0)
        opt._evaluate_slot(opt.slots[0])
        seconds = time.perf_counter() - before_wall
        cpu_seconds = time.process_time() - before_cpu
        state = digest(opt.to_snapshot())
        if state != GOLDEN:
            raise AssertionError(f"runtime changed original optimizer-v7 digest trial={i}: {state}")
        trials.append({"trial": i + 1, "wall_seconds": seconds, "cpu_seconds": cpu_seconds, "v7": state})
        print(json.dumps({"trial": i + 1, "wall_seconds": seconds,
                          "cpu_seconds": cpu_seconds, "native_v7": state}, sort_keys=True), flush=True)
    peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = {
        "kind": "PERF275_SOURCE_FROZEN_INTERPRETER_TEST_SEED0_SLOT0_ONLY",
        "source_sha": SOURCE, "seed": 0, "native_worlds_each": 1,
        "native_default_timeout_generations": 1024,
        "interpreter": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "warm_last_three_wall_median_seconds": median(v["wall_seconds"] for v in trials[-3:]),
        "cold_first_trial_wall_seconds": trials[0]["wall_seconds"],
        "peak_process_rss_kib": peak_kib,
        "trials": trials, "full_v7": GOLDEN, "original_seed16384_executed": False,
        "learning_claim": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "trials"}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
