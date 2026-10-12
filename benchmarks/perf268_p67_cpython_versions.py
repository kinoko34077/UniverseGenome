"""PERF #268 P6.7 source-frozen CPython 3.12/3.13/3.14 comparison.

Strictly a disposable performance seed0 one-original-world test; never D16 science.
"""
from __future__ import annotations
import argparse
import json
import platform
import resource
import subprocess
import sys
from pathlib import Path
from statistics import median
import time
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

FROZEN_SHA = "e7f2efd0c9ec49afc53b9265ec4b17e936798160"
GOLDEN = "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--repeats", type=int, default=6)
    args = p.parse_args()
    if not 4 <= args.repeats <= 8:
        raise ValueError("only 4..8 bounded repeats")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=10).strip()
    if source != FROZEN_SHA or platform.python_implementation() != "CPython":
        raise AssertionError("wrong source/runtime")
    trials = []
    for i in range(args.repeats):
        started = time.perf_counter()
        cpu_started = time.process_time()
        opt = SteadyStateOptimizer.from_defaults(base_seed=0)
        opt._evaluate_slot(opt.slots[0])
        wall = time.perf_counter() - started
        cpu = time.process_time() - cpu_started
        full_v7 = digest(opt.to_snapshot())
        if full_v7 != GOLDEN:
            raise AssertionError(f"native default1024 full-v7 mismatch: {full_v7}")
        trials.append({"index": i + 1, "wall_seconds": wall, "cpu_seconds": cpu})
    report = {
        "kind": "PERF268_P67_CPYTHON_STANDARD_INTERPRETER_SOURCE_FROZEN",
        "source_sha": source, "python_version": platform.python_version(),
        "executable": sys.executable, "implementation": platform.python_implementation(),
        "seed": 0, "worlds": 1, "default_timeout_generations": 1024,
        "original_full_optimizer_v7": GOLDEN,
        "first_cold_wall_seconds": trials[0]["wall_seconds"],
        "last_three_wall_median_seconds": median(x["wall_seconds"] for x in trials[-3:]),
        "maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "trials": trials, "original_science_seed16384_executed": False,
        "learning_claim": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "trials"},
                     sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
