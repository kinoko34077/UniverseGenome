"""Issue #110 research-only single-event floor scan.

Temporary harness: fixed accepted physics; no canonical learning semantics changed.
Each shard scans a deterministic seed interval for:
- A -> byte 0 (single event)
- A -> NULL (single event)

A precursor requires:
- baseline A-input evaluation is not already successful;
- post-training A-input evaluation succeeds;
- post-training no-input counterfactual does not succeed.
"""

from __future__ import annotations

import argparse
import json
import time

from core.experiment import ExperimentConfig, IOExperiment
from core.io_bus import OutputEdgeDetector, OutputEvent, read_output_signal
from core.physics import PhysicsConfig, create_universe


def load_protocol() -> tuple[PhysicsConfig, ExperimentConfig]:
    with open("config/default.json", encoding="utf-8") as handle:
        physics = PhysicsConfig.from_mapping(json.load(handle))
    with open("config/experiment_v0_1.json", encoding="utf-8") as handle:
        protocol = ExperimentConfig.from_mapping(json.load(handle))
    return physics, protocol


def event_for(task: str) -> OutputEvent:
    if task == "byte0":
        return OutputEvent.byte(0)
    if task == "null":
        return OutputEvent.null()
    raise ValueError(task)


def evaluate(state, protocol: ExperimentConfig, task: str, input_valid: bool) -> dict:
    result = IOExperiment(state, experiment=protocol).evaluate_autonomous(
        input_byte=65,
        input_valid=input_valid,
        expected=(event_for(task),),
    )
    return {
        "success": result.success,
        "event_count": len(result.autonomous_events),
        "bytes": [
            event.value
            for event in result.autonomous_events
            if event.kind == "byte"
        ],
        "null_count": sum(
            event.kind == "null" for event in result.autonomous_events
        ),
        "wrong_output_count": result.wrong_output_count,
        "timed_out": result.timed_out,
        "response_latency": result.response_latency,
    }


def train_single(
    experiment: IOExperiment,
    task: str,
    on_step,
) -> None:
    protocol = experiment.experiment
    for _ in range(protocol.byte_hold_generations):
        experiment.drive_input(65)
        metrics = experiment._advance(experiment.input_bus.signal_coordinates())
        on_step(experiment.state.generation, metrics)
    experiment.release_input()
    for _ in range(protocol.byte_gap_generations):
        metrics = experiment._advance(())
        on_step(experiment.state.generation, metrics)
    for _ in range(protocol.teacher_delay_generations):
        metrics = experiment._advance(())
        on_step(experiment.state.generation, metrics)
    experiment.teacher_output(event_for(task), on_step=on_step)


def run_case(seed: int, task: str, target_generation: int) -> dict:
    physics, protocol = load_protocol()
    state = create_universe(seed=seed, config=physics)
    experiment = IOExperiment(state, experiment=protocol)
    detector = OutputEdgeDetector()
    detector.prime_signal(read_output_signal(state))

    baseline_input = evaluate(state, protocol, task, True)
    baseline_no_input = evaluate(state, protocol, task, False)

    totals = {
        "collisions": 0,
        "bond_contacts": 0,
        "latent_transmissions": 0,
        "training_output_events": 0,
        "training_target_events": 0,
        "training_wrong_events": 0,
    }

    def on_step(_generation, metrics):
        totals["collisions"] += metrics.collision_count
        totals["bond_contacts"] += metrics.bond_contact_count
        totals["latent_transmissions"] += metrics.latent_transmission_count
        for output in detector.observe_signal(read_output_signal(state)):
            totals["training_output_events"] += 1
            if output == event_for(task):
                totals["training_target_events"] += 1
            else:
                totals["training_wrong_events"] += 1

    started = time.perf_counter()
    episodes = 0
    extinct_at = None
    while state.generation < target_generation:
        train_single(experiment, task, on_step)
        episodes += 1
        if not state.active_slots() and physics.noise_rate == 0:
            extinct_at = state.generation
            break

    trained_input = evaluate(state, protocol, task, True)
    trained_no_input = evaluate(state, protocol, task, False)
    wall = time.perf_counter() - started
    precursor = (
        not baseline_input["success"]
        and trained_input["success"]
        and not trained_no_input["success"]
    )

    return {
        "seed": seed,
        "task": task,
        "generation": state.generation,
        "episodes": episodes,
        "extinct_at": extinct_at,
        "active_cells": len(state.active_slots()),
        "baseline_input": baseline_input,
        "baseline_no_input": baseline_no_input,
        "trained_input": trained_input,
        "trained_no_input": trained_no_input,
        "precursor": precursor,
        "wall_seconds": wall,
        **totals,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-seed", type=int, required=True)
    parser.add_argument("--end-seed", type=int, required=True)
    parser.add_argument("--target-generation", type=int, default=2000)
    args = parser.parse_args()

    results = []
    for seed in range(args.start_seed, args.end_seed + 1):
        for task in ("byte0", "null"):
            results.append(run_case(seed, task, args.target_generation))

    summary = {}
    for task in ("byte0", "null"):
        cases = [item for item in results if item["task"] == task]
        summary[task] = {
            "cases": len(cases),
            "baseline_input_successes": sum(
                item["baseline_input"]["success"] for item in cases
            ),
            "baseline_no_input_successes": sum(
                item["baseline_no_input"]["success"] for item in cases
            ),
            "trained_input_successes": sum(
                item["trained_input"]["success"] for item in cases
            ),
            "trained_no_input_successes": sum(
                item["trained_no_input"]["success"] for item in cases
            ),
            "precursor_count": sum(item["precursor"] for item in cases),
            "precursor_seeds": [
                item["seed"] for item in cases if item["precursor"]
            ],
            "training_target_event_cases": sum(
                item["training_target_events"] > 0 for item in cases
            ),
            "training_target_events": sum(
                item["training_target_events"] for item in cases
            ),
            "survived_to_target": sum(
                item["extinct_at"] is None for item in cases
            ),
        }

    print(
        "ISSUE110_SINGLE_EVENT_RESULT="
        + json.dumps(
            {
                "seed_range": [args.start_seed, args.end_seed],
                "target_generation": args.target_generation,
                "summary": summary,
                "results": results,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
