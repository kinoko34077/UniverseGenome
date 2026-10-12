"""P8: fixed-source optional compiled physics, genuine original native slot0.

Pure performance seed0 only. Never execute original reserved seed16384.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import json
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import time

from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer
import core.physics as physics

FROZEN = "d78122f5ef51916b9e0a5d1ea40fd02c38d2021b"
GOLDEN = "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backend", choices=("native", "compiled"), required=True)
    p.add_argument("--output", type=Path, required=True)
    opts = p.parse_args()
    git = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=10).strip()
    if git != FROZEN:
        raise AssertionError(f"source moved: {git}")
    module_file = str(Path(physics.__file__).resolve())
    is_compiled = any(module_file.endswith(s) for s in importlib.machinery.EXTENSION_SUFFIXES)
    if is_compiled != (opts.backend == "compiled"):
        raise AssertionError("wrong optional backend was loaded")
    physics_source = Path("core/physics.py")
    physics_sha256 = hashlib.sha256(physics_source.read_bytes()).hexdigest()
    trials = []
    for i in range(6):
        start = time.perf_counter()
        cstart = time.process_time()
        opt = SteadyStateOptimizer.from_defaults(base_seed=0)
        opt._evaluate_slot(opt.slots[0])
        elapsed = time.perf_counter() - start
        cpu = time.process_time() - cstart
        oracle = digest(opt.to_snapshot())
        if oracle != GOLDEN:
            raise AssertionError(f"original entire optimizer-v7 drift on trial {i}: {oracle}")
        trials.append({"wall_seconds": elapsed, "cpu_seconds": cpu})
    out = {
        "kind": "PERF287_P80_SOURCE_FROZEN_OPTIONAL_CYTHON_PHYSICS",
        "source_sha": git, "physics_source_sha256": physics_sha256,
        "module_file": module_file, "backend": opts.backend,
        "python_version": platform.python_version(), "implementation": platform.python_implementation(),
        "default_timeout_generations": 1024, "seed": 0, "original_worlds": 1,
        "full_optimizer_v7": GOLDEN, "original_seed16384_executed": False,
        "first_cold_wall_seconds": trials[0]["wall_seconds"],
        "warm_last_three_median_s": statistics.median(t["wall_seconds"] for t in trials[-3:]),
        "maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "trials": trials,
    }
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: v for k,v in out.items() if k != "trials"}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
