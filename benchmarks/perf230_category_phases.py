"""PERF230: source-bound per-category native default1024 CPU phase profile.

Test-only performance observation of the four original category strata, one
existing seed0 identity each (slot 0/32/64/96), NO 128-world selection, NO
D16 seed16384 or science, and NO modification to runtime physics/RNG state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import subprocess
import time

from benchmarks.perf_residual_219 import (
    ORACLE_SLOT0_DEFAULT_1024, run_profile,
)
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

INDICES = (0, 32, 64, 96)


def run(indices: tuple[int, ...] = INDICES) -> dict:
    if indices != INDICES:
        raise ValueError("frozen PERF230 representatives must be (0,32,64,96)")
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()
    if len(source) != 40:
        raise ValueError("source SHA must be full 40 characters")
    result = {
        "kind": "PERF230_representative_category_native_CPU_and_clone_profile",
        "source_sha": source,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "seed": 0,
        "default_experiment": True,
        "default_physics": True,
        "default_timeout_generations": 1024,
        "evaluated_original_indices": list(indices),
        "full128_selection_performed": False,
        "D16_seed16384_outcomes": False,
        "learning_claim": False,
        "entries": [],
    }
    for index in indices:
        profiled = SteadyStateOptimizer.from_defaults(base_seed=0)
        original_slot = profiled.slots[index]
        measured, _ = run_profile(
            lambda: profiled._evaluate_slot(original_slot), top=65,
        )
        profiled_digest = digest(profiled.to_snapshot())
        if index == 0 and profiled_digest != ORACLE_SLOT0_DEFAULT_1024:
            raise AssertionError("original prior PERF219 native slot0 oracle drift")
        direct = SteadyStateOptimizer.from_defaults(base_seed=0)
        started = time.perf_counter()
        direct._evaluate_slot(direct.slots[index])
        unprofiled = time.perf_counter() - started
        if digest(direct.to_snapshot()) != profiled_digest:
            raise AssertionError("source-bound profiled/unprofiled v7 state mismatch")

        names = {
            "step", "active_slots", "_local_revival_slots", "_measure_slot",
            "_evaluate_slot", "measure_trained_state", "train_mappings",
            "_train_mapping_once", "_clone_state", "from_snapshot",
            "to_snapshot", "_evaluate_input_sequence", "_advance",
            "read_output_signal", "index", "_fusion_candidates",
        }
        cpu_sections = [
            x for x in measured["top_cumulative"]
            if x["function"] in names
        ]
        result["entries"].append({
            "slot_index": index,
            "category": original_slot.category,
            "profiler_wall_seconds": measured["wall_s"],
            "unprofiled_wall_seconds": unprofiled,
            "whole_optimizer_v7_digest": profiled_digest,
            "source_preserving_exact_state": True,
            "top_self": measured["top_self"][:25],
            "top_cumulative": measured["top_cumulative"][:35],
            "source_method_cpu_sections": cpu_sections,
        })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "source_sha": result["source_sha"],
        "entries": [
            {
                "index": e["slot_index"],
                "category": e["category"],
                "profiled_s": e["profiler_wall_seconds"],
                "unprofiled_s": e["unprofiled_wall_seconds"],
                "digest": e["whole_optimizer_v7_digest"],
                "top_self": e["top_self"][:10],
                "cpu_sections": e["source_method_cpu_sections"][:22],
            } for e in result["entries"]
        ],
        "D16_seed16384_outcomes": False,
        "learning_claim": False,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
