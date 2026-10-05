"""Bounded, resumable Stage 1 density arena for UniverseGenome #111.

This is a one-off research harness. It does not modify production source or
the accepted default configuration. Results are written case-by-case so an
interrupted host can resume without treating missing cases as evidence.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.experiment import (
    ExperimentConfig,
    IOExperiment,
    OutputEvent,
    load_experiment_config,
    measure_trained_state,
)
from core.io_bus import read_output_signal
from core.physics import PhysicsConfig, StepMetrics, create_universe
from core.runner import load_config


DEFAULT_DENSITIES = (4, 8, 16, 32)
DEFAULT_SEEDS = tuple(range(32))
PROTOCOL_REPETITION_GENERATIONS = 14


def digest_snapshot(snapshot: dict[str, Any]) -> str:
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def event_dict(event: OutputEvent) -> dict[str, Any]:
    return {"kind": event.kind, "value": event.value}


def result_dict(result: Any) -> dict[str, Any]:
    return {
        "success": bool(result.success),
        "clone_generation": int(result.clone_generation),
        "evaluation_generations": int(result.evaluation_generations),
        "activity_cost": int(result.activity_cost),
        "timed_out": bool(result.timed_out),
        "wrong_output_count": int(result.wrong_output_count),
        "response_latency": int(result.response_latency),
        "autonomous_events": [event_dict(event) for event in result.autonomous_events],
        "event_generations": [int(value) for value in result.event_generations],
    }


def build_physics_config(base_config: dict[str, Any], density: int) -> PhysicsConfig:
    values = dict(base_config)
    physics = dict(values.get("physics", {}))
    physics["initial_density"] = int(density)
    values["physics"] = physics
    return PhysicsConfig.from_mapping(values)


def checkpoint_record(state: Any, metrics: StepMetrics) -> dict[str, Any]:
    return {
        "generation": int(state.generation),
        "active_cells": int(metrics.active_cells),
        "collision_count": int(metrics.collision_count),
        "bond_contact_count": int(metrics.bond_contact_count),
        "latent_transmission_count": int(metrics.latent_transmission_count),
        "fusion_count": int(metrics.fusion_count),
        "fragmentation_count": int(metrics.fragmentation_count),
        "activity_cost": int(metrics.activity_cost),
        "state_digest": digest_snapshot(state.to_snapshot()),
    }


def run_uninstrumented_training(
    *,
    seed: int,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
) -> tuple[Any, float]:
    state = create_universe(seed=seed, config=config)
    experiment = IOExperiment(state, experiment=protocol)
    started = time.perf_counter()
    experiment.train_a_to_b_null()
    return state, time.perf_counter() - started


def run_instrumented_training(
    *,
    seed: int,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
    checkpoints: set[int],
) -> tuple[Any, dict[str, Any], float]:
    state = create_universe(seed=seed, config=config)
    experiment = IOExperiment(state, experiment=protocol)
    experiment.output_detector.prime_signal(read_output_signal(state))
    started = time.perf_counter()
    active_values: list[int] = []
    counters = Counter()
    input_hit_steps = 0
    teacher_hit_steps = 0
    input_hit_slots: set[int] = set()
    teacher_hit_slots: set[int] = set()
    autonomous_events: list[dict[str, Any]] = []
    checkpoint_values: dict[str, dict[str, Any]] = {}

    def record_step(metrics: StepMetrics) -> None:
        active_values.append(int(metrics.active_cells))
        counters["collision_count"] += int(metrics.collision_count)
        counters["bond_contact_count"] += int(metrics.bond_contact_count)
        counters["latent_transmission_count"] += int(metrics.latent_transmission_count)
        counters["fusion_count"] += int(metrics.fusion_count)
        counters["fragmentation_count"] += int(metrics.fragmentation_count)
        counters["noise_spawn_count"] += int(metrics.noise_spawn_count)
        if state.generation in checkpoints:
            checkpoint_values[str(state.generation)] = checkpoint_record(state, metrics)

    def autonomous_advance(anchors: Iterable[tuple[int, int]]) -> None:
        nonlocal input_hit_steps
        hits = experiment._nearby_slots(anchors)
        if hits:
            input_hit_steps += 1
            input_hit_slots.update(hits)
        metrics = experiment._advance(anchors)
        record_step(metrics)
        for event in experiment.observe_output_state():
            autonomous_events.append(
                {"generation": int(state.generation), **event_dict(event)}
            )

    def teacher_advance(event: OutputEvent) -> None:
        nonlocal teacher_hit_steps
        anchors = experiment._teacher_coordinates(event)
        hits = experiment._nearby_slots(anchors)
        if hits:
            teacher_hit_steps += 1
            teacher_hit_slots.update(hits)
        metrics = experiment._advance(anchors)
        record_step(metrics)
        # Teacher stimulation is not autonomous output evidence. Prime after
        # the teacher step so its output edge is not counted on the next step.
        experiment.output_detector.prime_signal(read_output_signal(state))

    for _ in range(protocol.teacher_repetitions):
        for _ in range(protocol.byte_hold_generations):
            experiment.drive_input(65)
            autonomous_advance(experiment.input_bus.signal_coordinates())
        for _ in range(protocol.byte_gap_generations):
            experiment.release_input()
            autonomous_advance(())
        for _ in range(protocol.teacher_delay_generations):
            experiment.release_input()
            autonomous_advance(())
        teacher_advance(OutputEvent.byte(66))
        teacher_advance(OutputEvent.null())

    elapsed = time.perf_counter() - started
    distribution = Counter(
        str(item["value"]) for item in autonomous_events if item["kind"] == "byte"
    )
    return state, {
        "physical_generations": int(state.generation),
        "active_cells_min": min(active_values, default=0),
        "active_cells_max": max(active_values, default=0),
        "active_cells_final": len(state.active_slots()),
        "collision_count": int(counters["collision_count"]),
        "bond_contact_count": int(counters["bond_contact_count"]),
        "latent_transmission_count": int(counters["latent_transmission_count"]),
        "fusion_count": int(counters["fusion_count"]),
        "fragmentation_count": int(counters["fragmentation_count"]),
        "noise_spawn_count": int(counters["noise_spawn_count"]),
        "input_hit_steps": input_hit_steps,
        "input_hit_slot_count": len(input_hit_slots),
        "teacher_hit_steps": teacher_hit_steps,
        "teacher_hit_slot_count": len(teacher_hit_slots),
        "autonomous_event_count": len(autonomous_events),
        "autonomous_byte_distribution": dict(sorted(distribution.items())),
        "autonomous_b_count": sum(
            item["kind"] == "byte" and item["value"] == 66
            for item in autonomous_events
        ),
        "autonomous_null_count": sum(
            item["kind"] == "null" for item in autonomous_events
        ),
        "autonomous_events": autonomous_events,
        "checkpoints": checkpoint_values,
        "instrumented_wall_seconds": elapsed,
        "instrumented_generations_per_second": state.generation / elapsed if elapsed else 0.0,
    }, elapsed


def run_case(
    *,
    seed: int,
    density: int,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
    target_generations: int,
) -> dict[str, Any]:
    config = build_physics_config(config_payload, density)
    repetitions = (target_generations + PROTOCOL_REPETITION_GENERATIONS - 1) // PROTOCOL_REPETITION_GENERATIONS
    protocol = replace(
        ExperimentConfig.from_mapping(experiment_payload),
        teacher_repetitions=repetitions,
    )
    initial_state = create_universe(seed=seed, config=config)
    initial_digest = digest_snapshot(initial_state.to_snapshot())
    checkpoints = {0, 16, 128, 256, 512, 1024, 2000, repetitions * PROTOCOL_REPETITION_GENERATIONS}

    raw_state, raw_elapsed = run_uninstrumented_training(
        seed=seed, config=config, protocol=protocol
    )
    trained_state, training, instrumented_elapsed = run_instrumented_training(
        seed=seed,
        config=config,
        protocol=protocol,
        checkpoints=checkpoints,
    )
    raw_digest = digest_snapshot(raw_state.to_snapshot())
    trained_digest = digest_snapshot(trained_state.to_snapshot())
    if raw_digest != trained_digest:
        raise RuntimeError("instrumentation changed the authoritative training state")

    evaluation_started = time.perf_counter()
    measurement = measure_trained_state(
        trained_state,
        experiment=replace(protocol, teacher_repetitions=1),
    )
    evaluation_elapsed = time.perf_counter() - evaluation_started
    serialization_started = time.perf_counter()
    serialized_snapshot = json.dumps(
        trained_state.to_snapshot(), sort_keys=True, separators=(",", ":")
    )
    serialization_elapsed = time.perf_counter() - serialization_started
    del serialized_snapshot
    record = measurement.per_seed[0]
    expected = {
        "baseline": result_dict(record.baseline),
        "trained": result_dict(record.trained),
        "baseline_no_input": result_dict(record.baseline_no_input),
        "trained_no_input": result_dict(record.trained_no_input),
        "baseline_alternate": result_dict(record.baseline_alternate),
        "trained_alternate": result_dict(record.trained_alternate),
    }
    return {
        "status": "complete",
        "seed": int(seed),
        "initial_density": int(density),
        "target_generations": int(target_generations),
        "teacher_repetitions": int(repetitions),
        "protocol_generations_per_repetition": PROTOCOL_REPETITION_GENERATIONS,
        "physics_config": config.to_dict(),
        "initial_state_digest": initial_digest,
        "trained_state_digest": trained_digest,
        "raw_training_wall_seconds": raw_elapsed,
        "raw_training_generations_per_second": raw_state.generation / raw_elapsed if raw_elapsed else 0.0,
        "instrumented_training_wall_seconds": instrumented_elapsed,
        "instrumentation_overhead_seconds": instrumented_elapsed - raw_elapsed,
        "evaluation_wall_seconds": evaluation_elapsed,
        "serialization_wall_seconds": serialization_elapsed,
        "training": training,
        "evaluation": expected,
        "learning_claim": bool(measurement.learning_claim),
        "baseline_successes": int(measurement.baseline_successes),
        "trained_successes": int(measurement.trained_successes),
        "trained_no_input_clean": int(measurement.trained_no_input_clean),
        "trained_alternate_input_clean": int(measurement.trained_alternate_input_clean),
    }


def case_key(seed: int, density: int) -> str:
    return f"{int(density)}:{int(seed)}"


def read_completed(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    completed: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("status") == "complete":
            completed[case_key(record["seed"], record["initial_density"])] = record
    return completed


def write_summary(path: Path, records: Iterable[dict[str, Any]], *, args: argparse.Namespace) -> None:
    values = tuple(records)
    by_density: dict[str, dict[str, Any]] = {}
    for density in args.densities:
        group = [item for item in values if item["initial_density"] == density]
        by_density[str(density)] = {
            "case_count": len(group),
            "learning_claim_count": sum(item["learning_claim"] for item in group),
            "trained_success_count": sum(item["trained_successes"] for item in group),
            "baseline_success_count": sum(item["baseline_successes"] for item in group),
            "mean_final_active_cells": (
                sum(item["training"]["active_cells_final"] for item in group) / len(group)
                if group else None
            ),
            "mean_raw_generations_per_second": (
                sum(item["raw_training_generations_per_second"] for item in group) / len(group)
                if group else None
            ),
            "mean_training_collision_count": (
                sum(item["training"]["collision_count"] for item in group) / len(group)
                if group else None
            ),
        }
    summary = {
        "schema_version": 1,
        "issue": 111,
        "status": "complete" if len(values) == len(args.densities) * len(args.seeds) else "incomplete",
        "base_main": args.base_main,
        "worker_count": args.workers,
        "densities": list(args.densities),
        "seeds": list(args.seeds),
        "target_generations": args.generations,
        "completed_case_count": len(values),
        "expected_case_count": len(args.densities) * len(args.seeds),
        "by_density": by_density,
        "learning_claim": False,
        "records": sorted(
            (case_key(item["seed"], item["initial_density"]) for item in values)
        ),
    }
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/default.json"))
    parser.add_argument("--experiment", type=Path, default=Path("config/experiment_v0_1.json"))
    parser.add_argument("--output", type=Path, default=Path("research/artifacts/density_sweep_stage1.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("research/artifacts/density_sweep_summary.json"))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--generations", type=int, default=2000)
    parser.add_argument("--base-main", default="dd0b35a02e3ecb9c0470c44e8fd604e5ea87d8ea")
    parser.add_argument("--densities", nargs="+", type=int, default=list(DEFAULT_DENSITIES))
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    if args.generations < 1:
        raise SystemExit("--generations must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    config_payload = load_config(args.config)
    experiment_payload = json.loads(args.experiment.read_text(encoding="utf-8"))
    completed = read_completed(args.output)
    cases = [
        (seed, density)
        for density in args.densities
        for seed in args.seeds
        if case_key(seed, density) not in completed
    ]
    print(
        f"density sweep: completed={len(completed)} pending={len(cases)} workers={args.workers}",
        file=sys.stderr,
        flush=True,
    )
    with args.output.open("a", encoding="utf-8") as handle:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(
                    run_case,
                    seed=seed,
                    density=density,
                    config_payload=config_payload,
                    experiment_payload=experiment_payload,
                    target_generations=args.generations,
                ): (seed, density)
                for seed, density in cases
            }
            for index, future in enumerate(as_completed(futures), start=1):
                seed, density = futures[future]
                try:
                    record = future.result()
                except Exception as error:  # keep a diagnostic, not evidence
                    record = {
                        "status": "error",
                        "seed": seed,
                        "initial_density": density,
                        "error": repr(error),
                    }
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                if record.get("status") == "complete":
                    completed[case_key(seed, density)] = record
                print(
                    f"case {index}/{len(cases)} density={density} seed={seed} status={record['status']}",
                    file=sys.stderr,
                    flush=True,
                )
    write_summary(args.summary, completed.values(), args=args)
    print(f"summary={args.summary} completed={len(completed)}", file=sys.stderr)
    return 0 if len(completed) == len(args.densities) * len(args.seeds) else 2


if __name__ == "__main__":
    raise SystemExit(main())
