"""Matched-snapshot learning-channel causal audit for UniverseGenome #113.

Research-only harness. It does not mutate production physics, accepted defaults,
or the P6.10+ capability boundary.
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

from core.experiment import ExperimentConfig, IOExperiment
from core.io_bus import FixedOrgans, OutputEvent, read_output_signal
from core.physics import PhysicsConfig, StepMetrics, create_universe, destination_footprint
from core.runner import load_config
from core.state import Lifecycle, UniverseState

DEFAULT_DENSITIES = (32, 4)
DEFAULT_SEEDS = tuple(range(32))
BRANCHES = ("control", "a_only", "ab", "ac")
FIELDS = (
    "lifecycle", "x", "y", "structure", "latent", "hp",
    "bond_strength", "direction", "speed_code", "age", "black_hole_timer",
)


def canonical_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def build_physics_config(base_config: dict[str, Any], density: int) -> PhysicsConfig:
    values = dict(base_config)
    physics = dict(values.get("physics", {}))
    physics["initial_density"] = int(density)
    values["physics"] = physics
    return PhysicsConfig.from_mapping(values)


def clone_state(snapshot: dict[str, Any], config: PhysicsConfig) -> UniverseState:
    return UniverseState.from_snapshot(snapshot, config=config)


def torus_distance(first: int, second: int, size: int = 32) -> int:
    delta = abs(int(first) - int(second)) % size
    return min(delta, size - delta)


def snapshot_metrics(state: UniverseState) -> dict[str, Any]:
    snapshot = state.to_snapshot()
    arrays = snapshot["arrays"]
    counts = Counter(int(value) for value in arrays["lifecycle"])
    output_coords = tuple(
        value
        for key, value in FixedOrgans.coordinates().items()
        if key.startswith("OUT")
    )
    output_near_slots: list[int] = []
    minimum_output_distance: int | None = None
    for slot in state.active_slots():
        footprint = destination_footprint(
            state.structure[slot], state.x[slot], state.y[slot]
        )
        slot_distance = min(
            max(torus_distance(x, ox), torus_distance(y, oy))
            for x, y in footprint
            for ox, oy in output_coords
        )
        if minimum_output_distance is None or slot_distance < minimum_output_distance:
            minimum_output_distance = slot_distance
        if slot_distance <= 1:
            output_near_slots.append(slot)
    signal = read_output_signal(state)
    return {
        "generation": int(state.generation),
        "snapshot_digest": canonical_digest(snapshot),
        "active_cells": int(counts[int(Lifecycle.ACTIVE)]),
        "black_holes": int(counts[int(Lifecycle.BLACK_HOLE)]),
        "free_cells": int(counts[int(Lifecycle.FREE)]),
        "field_digests": {
            name: canonical_digest(arrays[name]) for name in FIELDS
        },
        "output_neighborhood_occupancy": len(output_near_slots),
        "minimum_output_distance": minimum_output_distance,
        "output_signal": {
            "valid": bool(signal.valid),
            "null": bool(signal.null),
            "value": int(signal.value),
        },
    }


def snapshot_diff(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_arrays = first["arrays"]
    second_arrays = second["arrays"]
    fields: dict[str, Any] = {}
    changed_total = 0
    for name in FIELDS:
        left = first_arrays[name]
        right = second_arrays[name]
        changed = [index for index, pair in enumerate(zip(left, right)) if pair[0] != pair[1]]
        changed_total += len(changed)
        material = [[index, int(left[index]), int(right[index])] for index in changed]
        fields[name] = {
            "changed_slots": len(changed),
            "absolute_delta_sum": sum(abs(int(left[i]) - int(right[i])) for i in changed),
            "delta_digest": canonical_digest(material),
        }
    return {
        "different": changed_total > 0,
        "changed_slot_fields_total": changed_total,
        "fields": fields,
    }


def add_metrics(total: Counter[str], metrics: StepMetrics) -> None:
    total["collision_count"] += int(metrics.collision_count)
    total["bond_contact_count"] += int(metrics.bond_contact_count)
    total["latent_transmission_count"] += int(metrics.latent_transmission_count)
    total["fusion_count"] += int(metrics.fusion_count)
    total["fragmentation_count"] += int(metrics.fragmentation_count)
    total["noise_spawn_count"] += int(metrics.noise_spawn_count)


def run_branch(
    initial_snapshot: dict[str, Any],
    *,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
    branch: str,
) -> dict[str, Any]:
    if branch not in BRANCHES:
        raise ValueError(f"unknown branch: {branch}")
    state = clone_state(initial_snapshot, config)
    experiment = IOExperiment(state, experiment=protocol)
    experiment.output_detector.prime_signal(read_output_signal(state))
    activity: Counter[str] = Counter()
    autonomous_events: list[dict[str, Any]] = []
    contacts = {
        "input_hit_steps": 0,
        "input_hit_slots": set(),
        "teacher_byte_hit_steps": 0,
        "teacher_byte_hit_slots": set(),
        "teacher_null_hit_steps": 0,
        "teacher_null_hit_slots": set(),
    }
    checkpoints: dict[str, dict[str, Any]] = {}
    snapshots: dict[str, dict[str, Any]] = {}

    def record(name: str) -> None:
        snapshots[name] = state.to_snapshot()
        checkpoints[name] = snapshot_metrics(state)

    def advance(
        anchors: Iterable[tuple[int, int]] = (),
        *,
        contact_kind: str | None = None,
        observe_output: bool = True,
    ) -> None:
        anchor_values = tuple(anchors)
        hits = experiment._nearby_slots(anchor_values)
        if contact_kind == "input" and hits:
            contacts["input_hit_steps"] += 1
            contacts["input_hit_slots"].update(hits)
        elif contact_kind == "teacher_byte" and hits:
            contacts["teacher_byte_hit_steps"] += 1
            contacts["teacher_byte_hit_slots"].update(hits)
        elif contact_kind == "teacher_null" and hits:
            contacts["teacher_null_hit_steps"] += 1
            contacts["teacher_null_hit_slots"].update(hits)
        metrics = experiment._advance(anchor_values)
        add_metrics(activity, metrics)
        if observe_output:
            for event in experiment.observe_output_state():
                autonomous_events.append({
                    "generation": int(state.generation),
                    "kind": event.kind,
                    "value": event.value,
                })
        else:
            experiment.output_detector.prime_signal(read_output_signal(state))

    record("initial")

    # Matched input window. Control receives the same physical steps with no
    # stimulus; A-only/AB/AC receive identical A stimulation.
    for _ in range(protocol.byte_hold_generations):
        if branch == "control":
            advance(())
        else:
            experiment.drive_input(65)
            advance(experiment.input_bus.signal_coordinates(), contact_kind="input")
    experiment.release_input()
    record("after_input")

    for _ in range(protocol.byte_gap_generations + protocol.teacher_delay_generations):
        advance(())
    record("pre_teacher")

    # The B/C teacher byte is the only L2 branch difference. Control and A-only
    # take a sham physical step so all branches stay generation-aligned.
    if branch in {"ab", "ac"}:
        teacher = OutputEvent.byte(66 if branch == "ab" else 67)
        advance(
            experiment._teacher_coordinates(teacher),
            contact_kind="teacher_byte",
            observe_output=False,
        )
    else:
        advance((), observe_output=False)
    record("teacher_immediate")

    # AB and AC both receive the same terminal NULL teacher event. Control and
    # A-only take one matched sham step. This preserves B-vs-C isolation.
    if branch in {"ab", "ac"}:
        null_event = OutputEvent.null()
        advance(
            experiment._teacher_coordinates(null_event),
            contact_kind="teacher_null",
            observe_output=False,
        )
    else:
        advance((), observe_output=False)

    # Horizons are measured from the byte-teacher step. One step has already
    # elapsed for the common NULL/sham transition.
    for _ in range(9):
        advance(())
    record("plus_10")
    for _ in range(90):
        advance(())
    record("plus_100")
    for _ in range(900):
        advance(())
    record("plus_1000")

    return {
        "branch": branch,
        "contacts": {
            key: sorted(value) if isinstance(value, set) else int(value)
            for key, value in contacts.items()
        },
        "activity": dict(activity),
        "autonomous_events": autonomous_events,
        "checkpoints": checkpoints,
        "_snapshots": snapshots,
    }



def run_branch_raw(
    initial_snapshot: dict[str, Any],
    *,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
    branch: str,
) -> dict[str, dict[str, Any]]:
    """Execute the same physical schedule without diagnostic reads/metrics."""
    if branch not in BRANCHES:
        raise ValueError(f"unknown branch: {branch}")
    state = clone_state(initial_snapshot, config)
    experiment = IOExperiment(state, experiment=protocol)
    snapshots: dict[str, dict[str, Any]] = {}

    def record(name: str) -> None:
        snapshots[name] = state.to_snapshot()

    def advance(anchors: Iterable[tuple[int, int]] = ()) -> None:
        experiment._advance(tuple(anchors))

    record("initial")
    for _ in range(protocol.byte_hold_generations):
        if branch == "control":
            advance(())
        else:
            experiment.drive_input(65)
            advance(experiment.input_bus.signal_coordinates())
    experiment.release_input()
    record("after_input")

    for _ in range(protocol.byte_gap_generations + protocol.teacher_delay_generations):
        advance(())
    record("pre_teacher")

    if branch in {"ab", "ac"}:
        teacher = OutputEvent.byte(66 if branch == "ab" else 67)
        advance(experiment._teacher_coordinates(teacher))
    else:
        advance(())
    record("teacher_immediate")

    if branch in {"ab", "ac"}:
        advance(experiment._teacher_coordinates(OutputEvent.null()))
    else:
        advance(())

    for _ in range(9):
        advance(())
    record("plus_10")
    for _ in range(90):
        advance(())
    record("plus_100")
    for _ in range(900):
        advance(())
    record("plus_1000")
    return snapshots


def run_case_raw(
    *,
    seed: int,
    density: int,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
) -> dict[str, Any]:
    config = build_physics_config(config_payload, density)
    protocol = replace(
        ExperimentConfig.from_mapping(experiment_payload),
        teacher_repetitions=1,
    )
    initial = create_universe(seed=seed, config=config).to_snapshot()
    branches = {
        name: run_branch_raw(initial, config=config, protocol=protocol, branch=name)
        for name in BRANCHES
    }
    return {
        "initial_snapshot_digest": canonical_digest(initial),
        "branches": {
            name: {
                checkpoint: {
                    "snapshot_digest": canonical_digest(snapshot),
                    "generation": int(snapshot["generation"]),
                }
                for checkpoint, snapshot in snapshots.items()
            }
            for name, snapshots in branches.items()
        },
    }


def run_case_once(
    *,
    seed: int,
    density: int,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
) -> dict[str, Any]:
    config = build_physics_config(config_payload, density)
    protocol = replace(
        ExperimentConfig.from_mapping(experiment_payload),
        teacher_repetitions=1,
    )
    initial = create_universe(seed=seed, config=config).to_snapshot()
    branches = {
        name: run_branch(initial, config=config, protocol=protocol, branch=name)
        for name in BRANCHES
    }

    control = branches["control"]["_snapshots"]
    a_only = branches["a_only"]["_snapshots"]
    ab = branches["ab"]["_snapshots"]
    ac = branches["ac"]["_snapshots"]

    comparisons = {
        "l1_a_vs_control_after_input": snapshot_diff(
            a_only["after_input"], control["after_input"]
        ),
        "l2_ab_vs_ac_immediate": snapshot_diff(
            ab["teacher_immediate"], ac["teacher_immediate"]
        ),
        "l2_ab_vs_ac_plus_10": snapshot_diff(ab["plus_10"], ac["plus_10"]),
        "l3_ab_vs_ac_plus_100": snapshot_diff(ab["plus_100"], ac["plus_100"]),
        "l3_ab_vs_ac_plus_1000": snapshot_diff(ab["plus_1000"], ac["plus_1000"]),
    }

    for value in branches.values():
        value.pop("_snapshots", None)

    contacts = {
        name: {
            "input": int(value["contacts"]["input_hit_steps"]) > 0,
            "teacher_byte": int(value["contacts"]["teacher_byte_hit_steps"]) > 0,
            "teacher_null": int(value["contacts"]["teacher_null_hit_steps"]) > 0,
        }
        for name, value in branches.items()
    }
    gates = {
        "l0_input_contact": any(
            contacts[name]["input"] for name in ("a_only", "ab", "ac")
        ),
        "l0_teacher_b_contact": contacts["ab"]["teacher_byte"],
        "l0_teacher_c_contact": contacts["ac"]["teacher_byte"],
        "l1_immediate_state_delta": comparisons[
            "l1_a_vs_control_after_input"
        ]["different"],
        "l2_teacher_specific_immediate": comparisons[
            "l2_ab_vs_ac_immediate"
        ]["different"],
        "l2_teacher_specific_plus_10": comparisons[
            "l2_ab_vs_ac_plus_10"
        ]["different"],
        "l3_persistent_plus_100": comparisons[
            "l3_ab_vs_ac_plus_100"
        ]["different"],
        "l3_persistent_plus_1000": comparisons[
            "l3_ab_vs_ac_plus_1000"
        ]["different"],
    }
    return {
        "status": "complete",
        "seed": int(seed),
        "initial_density": int(density),
        "initial_snapshot_digest": canonical_digest(initial),
        "physics_config": config.to_dict(),
        "protocol": protocol.to_dict(),
        "branches": branches,
        "comparisons": comparisons,
        "gates": gates,
    }


def deterministic_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": case["seed"],
        "initial_density": case["initial_density"],
        "initial_snapshot_digest": case["initial_snapshot_digest"],
        "branches": case["branches"],
        "comparisons": case["comparisons"],
        "gates": case["gates"],
    }


def run_case(**kwargs: Any) -> dict[str, Any]:
    started = time.perf_counter()
    first_started = time.perf_counter()
    first = run_case_once(**kwargs)
    instrumented_wall = time.perf_counter() - first_started

    replay_started = time.perf_counter()
    second = run_case_once(**kwargs)
    replay_wall = time.perf_counter() - replay_started

    raw_started = time.perf_counter()
    raw = run_case_raw(**kwargs)
    raw_wall = time.perf_counter() - raw_started

    first_digest = canonical_digest(deterministic_projection(first))
    second_digest = canonical_digest(deterministic_projection(second))
    if first_digest != second_digest:
        raise RuntimeError("matched causal audit is not deterministic under replay")

    raw_match = first["initial_snapshot_digest"] == raw["initial_snapshot_digest"]
    for branch in BRANCHES:
        for checkpoint, metrics in first["branches"][branch]["checkpoints"].items():
            raw_metrics = raw["branches"][branch][checkpoint]
            if metrics["snapshot_digest"] != raw_metrics["snapshot_digest"]:
                raw_match = False
                break
        if not raw_match:
            break
    if not raw_match:
        raise RuntimeError("instrumented causal audit perturbs authoritative state")

    instrumented_generations = sum(
        int(value["checkpoints"]["plus_1000"]["generation"])
        - int(value["checkpoints"]["initial"]["generation"])
        for value in first["branches"].values()
    )
    raw_generations = sum(
        int(value["plus_1000"]["generation"]) - int(value["initial"]["generation"])
        for value in raw["branches"].values()
    )
    first["replay_digest"] = first_digest
    first["replay_match"] = True
    first["raw_instrumented_match"] = True
    first["performance"] = {
        "instrumented_wall_seconds": instrumented_wall,
        "instrumented_replay_wall_seconds": replay_wall,
        "raw_wall_seconds": raw_wall,
        "instrumented_generations": instrumented_generations,
        "raw_generations": raw_generations,
        "instrumented_generations_per_second": (
            instrumented_generations / instrumented_wall if instrumented_wall else 0.0
        ),
        "raw_generations_per_second": (
            raw_generations / raw_wall if raw_wall else 0.0
        ),
        "instrumentation_overhead_wall_seconds": instrumented_wall - raw_wall,
        "instrumentation_overhead_ratio": (
            (instrumented_wall - raw_wall) / raw_wall if raw_wall else 0.0
        ),
        "clone_evaluation_wall_seconds": 0.0,
        "case_total_wall_seconds": time.perf_counter() - started,
    }
    return first


def case_key(seed: int, density: int) -> str:
    return f"{int(density)}:{int(seed)}"


def read_completed(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if (
            item.get("status") == "complete"
            and item.get("replay_match") is True
            and item.get("raw_instrumented_match") is True
        ):
            out[case_key(item["seed"], item["initial_density"])] = item
    return out


def classify_case(item: dict[str, Any]) -> dict[str, str | None]:
    gates = item["gates"]
    levels: dict[str, str] = {}
    l0 = (
        gates["l0_input_contact"]
        and gates["l0_teacher_b_contact"]
        and gates["l0_teacher_c_contact"]
    )
    levels["L0"] = "PASS" if l0 else "FAIL"
    if not l0:
        for level in ("L1", "L2", "L3", "L4", "L5", "L6", "L7"):
            levels[level] = "NOT_EVALUABLE"
        return {"first_failed": "L0", **levels}

    l1 = bool(gates["l1_immediate_state_delta"])
    levels["L1"] = "PASS" if l1 else "FAIL"
    if not l1:
        for level in ("L2", "L3", "L4", "L5", "L6", "L7"):
            levels[level] = "NOT_EVALUABLE"
        return {"first_failed": "L1", **levels}

    l2 = bool(
        gates["l2_teacher_specific_immediate"]
        and gates["l2_teacher_specific_plus_10"]
    )
    levels["L2"] = "PASS" if l2 else "FAIL"
    if not l2:
        for level in ("L3", "L4", "L5", "L6", "L7"):
            levels[level] = "NOT_EVALUABLE"
        return {"first_failed": "L2", **levels}

    l3 = bool(
        gates["l3_persistent_plus_100"]
        and gates["l3_persistent_plus_1000"]
    )
    levels["L3"] = "PASS" if l3 else "FAIL"
    if not l3:
        for level in ("L4", "L5", "L6", "L7"):
            levels[level] = "NOT_EVALUABLE"
        return {"first_failed": "L3", **levels}
    for level in ("L4", "L5", "L6", "L7"):
        levels[level] = "NOT_EVALUATED"
    return {"first_failed": None, **levels}


def write_summary(
    path: Path,
    records: Iterable[dict[str, Any]],
    *,
    densities: tuple[int, ...],
    seeds: tuple[int, ...],
    workers: int,
    base_main: str,
    runner_wall_seconds: float,
    serialization_probe_wall_seconds: float,
    jsonl_write_flush_wall_seconds: float,
) -> None:
    values = tuple(records)
    by_density: dict[str, Any] = {}
    gate_names = (
        "l0_input_contact", "l0_teacher_b_contact", "l0_teacher_c_contact",
        "l1_immediate_state_delta", "l2_teacher_specific_immediate",
        "l2_teacher_specific_plus_10", "l3_persistent_plus_100",
        "l3_persistent_plus_1000",
    )
    for density in densities:
        group = [item for item in values if item["initial_density"] == density]
        classifications = [classify_case(item) for item in group]
        teacher_hit_set_difference_count = sum(
            item["branches"]["ab"]["contacts"]["teacher_byte_hit_slots"]
            != item["branches"]["ac"]["contacts"]["teacher_byte_hit_slots"]
            for item in group
        )
        by_density[str(density)] = {
            "case_count": len(group),
            "gate_pass_counts": {
                name: sum(bool(item["gates"][name]) for item in group)
                for name in gate_names
            },
            "first_failed_counts": dict(
                Counter(value["first_failed"] or "NONE" for value in classifications)
            ),
            "level_status_counts": {
                level: dict(Counter(value[level] for value in classifications))
                for level in ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7")
            },
            "teacher_hit_set_difference_count": teacher_hit_set_difference_count,
            "first_failed_by_seed": {
                str(item["seed"]): classify_case(item)["first_failed"]
                for item in group
            },
        }

    l0_any = any(
        item["gates"]["l0_input_contact"]
        and item["gates"]["l0_teacher_b_contact"]
        and item["gates"]["l0_teacher_c_contact"]
        for item in values
    )
    l1_any = any(item["gates"]["l1_immediate_state_delta"] for item in values)
    l2_any = any(
        item["gates"]["l2_teacher_specific_immediate"]
        and item["gates"]["l2_teacher_specific_plus_10"]
        for item in values
    )
    l3_any = any(
        item["gates"]["l3_persistent_plus_100"]
        and item["gates"]["l3_persistent_plus_1000"]
        for item in values
    )
    if not l0_any:
        first_failed = "L0"
    elif not l1_any:
        first_failed = "L1"
    elif not l2_any:
        first_failed = "L2"
    elif not l3_any:
        first_failed = "L3"
    else:
        first_failed = None

    expected = len(densities) * len(seeds)
    instrumented_wall = sum(
        float(item.get("performance", {}).get("instrumented_wall_seconds", 0.0))
        for item in values
    )
    raw_wall = sum(
        float(item.get("performance", {}).get("raw_wall_seconds", 0.0))
        for item in values
    )
    instrumented_generations = sum(
        int(item.get("performance", {}).get("instrumented_generations", 0))
        for item in values
    )
    raw_generations = sum(
        int(item.get("performance", {}).get("raw_generations", 0))
        for item in values
    )
    performance = {
        "runner_wall_seconds": runner_wall_seconds,
        "instrumented_wall_seconds_total": instrumented_wall,
        "raw_wall_seconds_total": raw_wall,
        "instrumented_generations_total": instrumented_generations,
        "raw_generations_total": raw_generations,
        "instrumented_generations_per_second": (
            instrumented_generations / instrumented_wall if instrumented_wall else 0.0
        ),
        "raw_generations_per_second": (
            raw_generations / raw_wall if raw_wall else 0.0
        ),
        "instrumentation_overhead_wall_seconds": instrumented_wall - raw_wall,
        "instrumentation_overhead_ratio": (
            (instrumented_wall - raw_wall) / raw_wall if raw_wall else 0.0
        ),
        "clone_evaluation_wall_seconds_total": sum(
            float(item.get("performance", {}).get("clone_evaluation_wall_seconds", 0.0))
            for item in values
        ),
        "serialization_probe_wall_seconds_total": serialization_probe_wall_seconds,
        "jsonl_write_flush_wall_seconds_total": jsonl_write_flush_wall_seconds,
    }
    summary = {
        "schema_version": 1,
        "issue": 113,
        "status": "complete" if len(values) == expected else "incomplete",
        "base_main": base_main,
        "workers": workers,
        "densities": list(densities),
        "seeds": list(seeds),
        "expected_case_count": expected,
        "completed_case_count": len(values),
        "replay_match_count": sum(item.get("replay_match") is True for item in values),
        "raw_instrumented_match_count": sum(
            item.get("raw_instrumented_match") is True for item in values
        ),
        "performance": performance,
        "by_density": by_density,
        "first_failed_level_if_no_case_passes": first_failed,
        "first_failed_counts_all_cases": dict(
            Counter(
                (classify_case(item)["first_failed"] or "NONE")
                for item in values
            )
        ),
        "l0_any_complete_contact_case": l0_any,
        "l1_any_state_delta_case": l1_any,
        "l2_any_teacher_specific_case": l2_any,
        "l3_any_persistent_case": l3_any,
        "canonical_learning_claim": False,
        "p6_10_plus": "frozen",
    }
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/default.json"))
    parser.add_argument("--experiment", type=Path, default=Path("config/experiment_v0_1.json"))
    parser.add_argument("--output", type=Path, default=Path("research/artifacts/causal_audit_113.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("research/artifacts/causal_audit_113_summary.json"))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--densities", nargs="+", type=int, default=list(DEFAULT_DENSITIES))
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--base-main", default="a8c3685939c3e9779fae6511b81c75f0f638b888")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    densities = tuple(args.densities)
    seeds = tuple(args.seeds)
    config_payload = load_config(args.config)
    experiment_payload = json.loads(args.experiment.read_text(encoding="utf-8"))
    runner_started = time.perf_counter()
    serialization_probe_wall_seconds = 0.0
    jsonl_write_flush_wall_seconds = 0.0
    completed = read_completed(args.output)
    pending = [
        (seed, density)
        for density in densities
        for seed in seeds
        if case_key(seed, density) not in completed
    ]
    print(
        f"causal audit: completed={len(completed)} pending={len(pending)} workers={args.workers}",
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
                ): (seed, density)
                for seed, density in pending
            }
            for index, future in enumerate(as_completed(futures), start=1):
                seed, density = futures[future]
                try:
                    item = future.result()
                except Exception as exc:
                    item = {
                        "status": "error",
                        "seed": seed,
                        "initial_density": density,
                        "error": repr(exc),
                    }
                serialization_started = time.perf_counter()
                json.dumps(item, sort_keys=True)
                serialization_elapsed = time.perf_counter() - serialization_started
                serialization_probe_wall_seconds += serialization_elapsed
                if item.get("status") == "complete":
                    item.setdefault("performance", {})[
                        "serialization_probe_wall_seconds"
                    ] = serialization_elapsed
                payload = json.dumps(item, sort_keys=True)
                write_started = time.perf_counter()
                handle.write(payload + "\n")
                handle.flush()
                jsonl_write_flush_wall_seconds += time.perf_counter() - write_started
                if (
                    item.get("status") == "complete"
                    and item.get("replay_match") is True
                    and item.get("raw_instrumented_match") is True
                ):
                    completed[case_key(seed, density)] = item
                print(
                    f"case {index}/{len(pending)} density={density} seed={seed} status={item['status']}",
                    file=sys.stderr,
                    flush=True,
                )

    write_summary(
        args.summary,
        completed.values(),
        densities=densities,
        seeds=seeds,
        workers=args.workers,
        base_main=args.base_main,
        runner_wall_seconds=time.perf_counter() - runner_started,
        serialization_probe_wall_seconds=serialization_probe_wall_seconds,
        jsonl_write_flush_wall_seconds=jsonl_write_flush_wall_seconds,
    )
    expected = len(densities) * len(seeds)
    print(f"summary={args.summary} completed={len(completed)}/{expected}", file=sys.stderr)
    return 0 if len(completed) == expected else 2


if __name__ == "__main__":
    raise SystemExit(main())
