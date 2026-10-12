"""PERF268 P6.2: source-authentic one-slot same-process ABBA pilot ONLY.

The reference function below is copied verbatim in behavior from accepted
main 91a1a3d712ce34bb0db591225d55f904648aae13 physics._local_revival_slots.
It is not another scientific seed/cohort and never dispatches D16 seed16384.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import time
from statistics import median
from unittest.mock import patch

import core.physics as physics
from core.physics import Lifecycle, destination_footprint
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

ORACLE = "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"
FROZEN_MAIN = "91a1a3d712ce34bb0db591225d55f904648aae13"


def old_index_revival(state):
    """Exact accepted source list.index BLACK_HOLE scan and native revive path."""
    black_holes = []
    start = 0
    while True:
        try:
            slot = state.lifecycle.index(int(Lifecycle.BLACK_HOLE), start)
        except ValueError:
            break
        black_holes.append(slot)
        start = slot + 1
    if not black_holes:
        return physics._RevivalSlots((), black_holes)
    active = state.active_slots()
    revived = set()
    for black_hole in black_holes:
        bh_footprint = destination_footprint(
            state.structure[black_hole], state.x[black_hole], state.y[black_hole]
        )
        for participant in active:
            if not (state.latent[participant] or state.bond_strength[participant]):
                continue
            footprint = destination_footprint(
                state.structure[participant], state.x[participant], state.y[participant]
            )
            if bh_footprint.intersection(footprint):
                revived.add(black_hole)
                break
    return physics._RevivalSlots(revived, black_holes)


def same_host_slot0_abba():
    accepted_native = physics._local_revival_slots
    trials = []
    for mode in ("baseline", "candidate", "candidate", "baseline"):
        optimizer = SteadyStateOptimizer.from_defaults(base_seed=0)
        implementation = old_index_revival if mode == "baseline" else accepted_native
        with patch.object(physics, "_local_revival_slots", implementation):
            started = time.perf_counter()
            optimizer._evaluate_slot(optimizer.slots[0])
            elapsed = time.perf_counter() - started
        result = digest(optimizer.to_snapshot())
        if result != ORACLE:
            raise AssertionError(f"{mode} changed original full-v7 source oracle: {result}")
        trials.append({"mode": mode, "elapsed_seconds": elapsed, "native_v7_sha256": result})
    prior = median(x["elapsed_seconds"] for x in trials if x["mode"] == "baseline")
    new = median(x["elapsed_seconds"] for x in trials if x["mode"] == "candidate")
    ratio = prior / new
    return {
        "kind": "PERF268_P6_NATIVE_ORIGINAL_SLOT0_ABBA_NO_D16_SCIENCE",
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "accepted_parent_main": FROZEN_MAIN,
        "seed": 0,
        "default_experiment_physics": True,
        "actual_original_native_worlds": 1,
        "timeout_generations": 1024,
        "frozen_full_v7": ORACLE,
        "trials": trials,
        "prior_median_seconds": prior,
        "candidate_median_seconds": new,
        "speed_ratio": ratio,
        "speed_gate_1_05": ratio >= 1.05,
        "decision": "CHEAP_SLOT0_GATE_PASS_NEXT_SELECTED128"
                    if ratio >= 1.05 else "REJECT_BELOW_MEASURED_GATE",
        "real_science_seed16384_executed": False,
        "learning_claim": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = same_host_slot0_abba()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
