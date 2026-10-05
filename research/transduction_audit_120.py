"""Physical I/O transduction capacity and state-write audit for UniverseGenome #120.

Research-only harness. It measures the accepted production transduction path and
must not mutate production physics/defaults or the P6.10+ capability boundary.

Comparator selection is predeclared in #120:
- low contrast: B=66 vs C=67
- high contrast: B=66 vs H=8
H=8 was selected before empirical runs by maximizing idealized receptive-region
symmetric difference from B and breaking ties by the numerically smallest byte.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.experiment import ExperimentConfig, IOExperiment
from core.io_bus import FixedOrgans, OutputEvent
from core.physics import PhysicsConfig, create_universe
from core.runner import load_config
from core.state import Lifecycle, UniverseState

BASE_MAIN = "2045cdff467aabd038e5bdb154da470f368189f0"
DEFAULT_DENSITIES = (4, 32)
DEFAULT_SEEDS = tuple(range(32))
INPUT_A = 65
TEACHER_B = 66
TEACHER_C = 67
TEACHER_H = 8
TEACHER_VALUES = (TEACHER_B, TEACHER_C, TEACHER_H)
FIELDS = (
    "lifecycle",
    "x",
    "y",
    "structure",
    "latent",
    "hp",
    "bond_strength",
    "direction",
    "speed_code",
    "age",
    "black_hole_timer",
)


def canonical_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
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


def receptive_tiles_for_coordinate(
    coordinate: tuple[int, int],
    *,
    radius: int = 1,
    size: int = 32,
) -> frozenset[tuple[int, int]]:
    x, y = coordinate
    return frozenset(
        ((x + dx) % size, (y + dy) % size)
        for dx in range(-radius, radius + 1)
        for dy in range(-radius, radius + 1)
    )


def teacher_coordinates(value: int) -> tuple[tuple[int, int], ...]:
    return IOExperiment._teacher_coordinates(OutputEvent.byte(int(value)))


def idealized_teacher_region(value: int) -> frozenset[tuple[int, int]]:
    region: set[tuple[int, int]] = set()
    for coordinate in teacher_coordinates(value):
        region.update(receptive_tiles_for_coordinate(coordinate))
    return frozenset(region)


def geometry_analysis() -> dict[str, Any]:
    regions = {value: idealized_teacher_region(value) for value in range(256)}
    classes: dict[frozenset[tuple[int, int]], list[int]] = {}
    for value, region in regions.items():
        classes.setdefault(region, []).append(value)

    alias_pair_count = sum(
        len(values) * (len(values) - 1) // 2 for values in classes.values()
    )
    b_region = regions[TEACHER_B]
    c_region = regions[TEACHER_C]
    h_region = regions[TEACHER_H]
    distances_from_b = {
        value: len(b_region.symmetric_difference(region))
        for value, region in regions.items()
        if value != TEACHER_B
    }
    maximum = max(distances_from_b.values())
    maximum_candidates = sorted(
        value for value, distance in distances_from_b.items() if distance == maximum
    )
    selected = maximum_candidates[0]
    distance_distribution = Counter(distances_from_b.values())
    largest_class = max((sorted(values) for values in classes.values()), key=len)

    return {
        "logical_values": 256,
        "distinct_idealized_regions": len(classes),
        "idealized_region_capacity_bits": math.log2(len(classes)),
        "exact_alias_unordered_pairs": alias_pair_count,
        "largest_equivalence_class_size": len(largest_class),
        "largest_equivalence_class_values": largest_class,
        "b_alias_values": sorted(classes[b_region]),
        "b_region_size": len(b_region),
        "c_region_size": len(c_region),
        "h_region_size": len(h_region),
        "b_c_symmetric_difference": len(b_region.symmetric_difference(c_region)),
        "b_h_symmetric_difference": len(b_region.symmetric_difference(h_region)),
        "b_h_b_only": len(b_region - h_region),
        "b_h_h_only": len(h_region - b_region),
        "distance_distribution_from_b": {
            str(key): int(distance_distribution[key])
            for key in sorted(distance_distribution)
        },
        "maximum_distance_from_b": maximum,
        "maximum_distance_candidates": maximum_candidates,
        "selection_rule": (
            "maximize idealized receptive-region symmetric difference from B=66; "
            "break ties by numerically smallest byte"
        ),
        "selected_high_contrast_byte": selected,
        "predeclared_high_contrast_byte": TEACHER_H,
        "selection_matches_predeclared": selected == TEACHER_H,
    }


def snapshot_diff(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_arrays = first["arrays"]
    second_arrays = second["arrays"]
    fields: dict[str, Any] = {}
    changed_union: set[int] = set()
    for name in FIELDS:
        left = first_arrays[name]
        right = second_arrays[name]
        changed = [
            index
            for index, (left_value, right_value) in enumerate(zip(left, right))
            if left_value != right_value
        ]
        changed_union.update(changed)
        fields[name] = {
            "changed_slots": len(changed),
            "slot_ids": changed,
            "absolute_delta_sum": sum(
                abs(int(left[index]) - int(right[index])) for index in changed
            ),
        }
    return {
        "different": bool(changed_union),
        "changed_slots": sorted(changed_union),
        "changed_slot_fields_total": sum(
            item["changed_slots"] for item in fields.values()
        ),
        "fields": fields,
    }


def advance_to_pre_teacher(
    initial_snapshot: dict[str, Any],
    *,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
    instrumented: bool,
) -> dict[str, Any]:
    a_state = clone_state(initial_snapshot, config)
    control_state = clone_state(initial_snapshot, config)
    a_exp = IOExperiment(a_state, experiment=protocol)
    control_exp = IOExperiment(control_state, experiment=protocol)
    input_hit_slots: set[int] = set()
    input_hit_steps = 0
    input_step_probes: list[dict[str, Any]] = []

    for step_index in range(protocol.byte_hold_generations):
        a_exp.drive_input(INPUT_A)
        anchors = a_exp.input_bus.signal_coordinates()
        hits = tuple(sorted(a_exp._nearby_slots(anchors)))
        if hits:
            input_hit_steps += 1
            input_hit_slots.update(hits)

        if instrumented:
            probe_source = a_state.to_snapshot()
            probe_stim_state = clone_state(probe_source, config)
            probe_sham_state = clone_state(probe_source, config)
            probe_stim_exp = IOExperiment(probe_stim_state, experiment=protocol)
            probe_sham_exp = IOExperiment(probe_sham_state, experiment=protocol)
            probe_stim_exp._advance(anchors)
            probe_sham_exp._advance(())
            arrays = probe_source["arrays"]
            hit_state_before = []
            for slot in hits:
                lifecycle = int(arrays["lifecycle"][slot])
                hp = int(arrays["hp"][slot])
                hit_state_before.append(
                    {
                        "slot": int(slot),
                        "lifecycle": lifecycle,
                        "hp": hp,
                        "hp_headroom": 255 - hp,
                        "active_full_hp": (
                            lifecycle == int(Lifecycle.ACTIVE) and hp == 255
                        ),
                    }
                )
            probe_diff = snapshot_diff(
                probe_stim_state.to_snapshot(),
                probe_sham_state.to_snapshot(),
            )
            input_step_probes.append(
                {
                    "step_index": int(step_index),
                    "generation_before": int(probe_source["generation"]),
                    "hits": list(hits),
                    "hit_state_before": hit_state_before,
                    "state_write": bool(probe_diff["different"]),
                    "state_diff": probe_diff,
                }
            )

        a_exp._advance(anchors)
        control_exp._advance(())

    after_input_a = a_state.to_snapshot()
    after_input_control = control_state.to_snapshot()
    a_exp.release_input()
    control_exp.release_input()

    for _ in range(protocol.byte_gap_generations + protocol.teacher_delay_generations):
        a_exp._advance(())
        control_exp._advance(())

    return {
        "a_pre_teacher": a_state.to_snapshot(),
        "control_pre_teacher": control_state.to_snapshot(),
        "input_hit_steps": input_hit_steps,
        "input_hit_slots": sorted(input_hit_slots),
        "input_step_probes": input_step_probes,
        "input_after_input_diff": snapshot_diff(after_input_a, after_input_control),
        "input_pre_teacher_diff": snapshot_diff(
            a_state.to_snapshot(), control_state.to_snapshot()
        ),
    }


def realized_hit_sets(
    pre_teacher_snapshot: dict[str, Any],
    *,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
) -> dict[str, Any]:
    state = clone_state(pre_teacher_snapshot, config)
    experiment = IOExperiment(state, experiment=protocol)
    by_byte: dict[int, tuple[int, ...]] = {}
    for value in range(256):
        hits = experiment._nearby_slots(teacher_coordinates(value))
        by_byte[value] = tuple(sorted(int(slot) for slot in hits))

    pattern_frequencies = Counter(by_byte.values())
    distinct_patterns = set(pattern_frequencies)
    pattern_entropy_bits = -sum(
        (count / 256.0) * math.log2(count / 256.0)
        for count in pattern_frequencies.values()
    )
    return {
        "distinct_hit_pattern_count": len(distinct_patterns),
        "effective_capacity_bits": math.log2(len(distinct_patterns)),
        "pattern_entropy_bits": pattern_entropy_bits,
        "contact_byte_count": sum(bool(hits) for hits in by_byte.values()),
        "b_hits": list(by_byte[TEACHER_B]),
        "c_hits": list(by_byte[TEACHER_C]),
        "h_hits": list(by_byte[TEACHER_H]),
        "b_c_hitset_distinct": by_byte[TEACHER_B] != by_byte[TEACHER_C],
        "b_h_hitset_distinct": by_byte[TEACHER_B] != by_byte[TEACHER_H],
    }


def teacher_step(
    pre_teacher_snapshot: dict[str, Any],
    *,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
    teacher_value: int | None,
    instrumented: bool,
) -> dict[str, Any]:
    state = clone_state(pre_teacher_snapshot, config)
    experiment = IOExperiment(state, experiment=protocol)
    before = state.to_snapshot()
    hits: tuple[int, ...] = ()

    if teacher_value is None:
        experiment._advance(())
    else:
        anchors = teacher_coordinates(teacher_value)
        if instrumented:
            hits = tuple(sorted(experiment._nearby_slots(anchors)))
        experiment._advance(anchors)

    after = state.to_snapshot()
    hit_state: list[dict[str, Any]] = []
    if teacher_value is not None and instrumented:
        arrays = before["arrays"]
        for slot in hits:
            lifecycle = int(arrays["lifecycle"][slot])
            hp = int(arrays["hp"][slot])
            hit_state.append(
                {
                    "slot": int(slot),
                    "lifecycle": lifecycle,
                    "hp": hp,
                    "hp_headroom": 255 - hp,
                    "active_full_hp": (
                        lifecycle == int(Lifecycle.ACTIVE) and hp == 255
                    ),
                }
            )

    return {
        "teacher_value": teacher_value,
        "hits": list(hits),
        "hit_state_before": hit_state,
        "before_digest": canonical_digest(before),
        "after_digest": canonical_digest(after),
        "after_snapshot": after,
    }


def case_once(
    *,
    seed: int,
    density: int,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
    instrumented: bool,
) -> dict[str, Any]:
    config = build_physics_config(config_payload, density)
    protocol = replace(
        ExperimentConfig.from_mapping(experiment_payload),
        teacher_repetitions=1,
    )
    initial_snapshot = create_universe(seed=seed, config=config).to_snapshot()
    prepared = advance_to_pre_teacher(
        initial_snapshot,
        config=config,
        protocol=protocol,
        instrumented=instrumented,
    )
    pre_teacher = prepared["a_pre_teacher"]
    hit_capacity = (
        realized_hit_sets(pre_teacher, config=config, protocol=protocol)
        if instrumented
        else None
    )

    branches = {
        "control": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=None,
            instrumented=instrumented,
        ),
        "control_repeat": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=None,
            instrumented=instrumented,
        ),
        "b": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=TEACHER_B,
            instrumented=instrumented,
        ),
        "c": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=TEACHER_C,
            instrumented=instrumented,
        ),
        "h": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=TEACHER_H,
            instrumented=instrumented,
        ),
    }
    control_after = branches["control"]["after_snapshot"]
    comparisons = {
        "control_vs_control_repeat": snapshot_diff(
            control_after, branches["control_repeat"]["after_snapshot"]
        ),
        "b_vs_control": snapshot_diff(branches["b"]["after_snapshot"], control_after),
        "c_vs_control": snapshot_diff(branches["c"]["after_snapshot"], control_after),
        "h_vs_control": snapshot_diff(branches["h"]["after_snapshot"], control_after),
        "b_vs_c": snapshot_diff(
            branches["b"]["after_snapshot"], branches["c"]["after_snapshot"]
        ),
        "b_vs_h": snapshot_diff(
            branches["b"]["after_snapshot"], branches["h"]["after_snapshot"]
        ),
    }

    symmetric_hit_slots_bh = sorted(
        set(branches["b"]["hits"]).symmetric_difference(branches["h"]["hits"])
    )
    traceable_bh_slots = sorted(
        set(symmetric_hit_slots_bh).intersection(comparisons["b_vs_h"]["changed_slots"])
    )
    all_hit_slots = sorted(
        set(branches["b"]["hits"])
        | set(branches["c"]["hits"])
        | set(branches["h"]["hits"])
    )

    result = {
        "status": "complete",
        "seed": int(seed),
        "initial_density": int(density),
        "initial_snapshot_digest": canonical_digest(initial_snapshot),
        "pre_teacher_snapshot_digest": canonical_digest(pre_teacher),
        "input": {
            "hit_steps": int(prepared["input_hit_steps"]),
            "hit_slots": prepared["input_hit_slots"],
            "step_probes": prepared["input_step_probes"],
            "after_input_diff": prepared["input_after_input_diff"],
            "pre_teacher_diff": prepared["input_pre_teacher_diff"],
        },
        "hit_capacity": hit_capacity,
        "branches": {
            name: {
                "teacher_value": value["teacher_value"],
                "hits": value["hits"],
                "hit_state_before": value["hit_state_before"],
                "before_digest": value["before_digest"],
                "after_digest": value["after_digest"],
            }
            for name, value in branches.items()
        },
        "comparisons": comparisons,
        "trace": {
            "all_teacher_hit_slots": all_hit_slots,
            "b_h_symmetric_hit_slots": symmetric_hit_slots_bh,
            "b_h_traceable_changed_slots": traceable_bh_slots,
            "b_h_traceable": bool(traceable_bh_slots),
        },
    }
    return result


def deterministic_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": case["seed"],
        "initial_density": case["initial_density"],
        "initial_snapshot_digest": case["initial_snapshot_digest"],
        "pre_teacher_snapshot_digest": case["pre_teacher_snapshot_digest"],
        "input": case["input"],
        "hit_capacity": case["hit_capacity"],
        "branches": case["branches"],
        "comparisons": case["comparisons"],
        "trace": case["trace"],
    }


def raw_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": case["seed"],
        "initial_density": case["initial_density"],
        "initial_snapshot_digest": case["initial_snapshot_digest"],
        "pre_teacher_snapshot_digest": case["pre_teacher_snapshot_digest"],
        "branch_after_digests": {
            name: value["after_digest"] for name, value in case["branches"].items()
        },
    }


def run_case(
    *,
    seed: int,
    density: int,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
) -> dict[str, Any]:
    first = case_once(
        seed=seed,
        density=density,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
    )
    second = case_once(
        seed=seed,
        density=density,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
    )
    raw = case_once(
        seed=seed,
        density=density,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=False,
    )

    first_digest = canonical_digest(deterministic_projection(first))
    second_digest = canonical_digest(deterministic_projection(second))
    if first_digest != second_digest:
        raise RuntimeError(
            f"non-deterministic #120 case density={density} seed={seed}"
        )

    raw_match = (
        first["initial_snapshot_digest"] == raw["initial_snapshot_digest"]
        and first["pre_teacher_snapshot_digest"] == raw["pre_teacher_snapshot_digest"]
        and all(
            first["branches"][name]["after_digest"]
            == raw["branches"][name]["after_digest"]
            for name in ("control", "control_repeat", "b", "c", "h")
        )
    )
    if not raw_match:
        raise RuntimeError(
            f"instrumentation perturbs #120 state density={density} seed={seed}"
        )

    first["replay_digest"] = first_digest
    first["replay_match"] = True
    first["raw_instrumented_match"] = True
    return first


def mean(values: Iterable[float]) -> float:
    material = list(values)
    return sum(material) / len(material) if material else 0.0


def summarize_density(cases: list[dict[str, Any]]) -> dict[str, Any]:
    pattern_counts = [
        int(case["hit_capacity"]["distinct_hit_pattern_count"]) for case in cases
    ]
    capacities = [
        float(case["hit_capacity"]["effective_capacity_bits"]) for case in cases
    ]
    pattern_entropies = [
        float(case["hit_capacity"]["pattern_entropy_bits"]) for case in cases
    ]

    teacher_stats: dict[str, Any] = {}
    for branch in ("b", "c", "h"):
        comparison = f"{branch}_vs_control"
        contact_count = sum(bool(case["branches"][branch]["hits"]) for case in cases)
        write_count = sum(
            bool(case["comparisons"][comparison]["different"]) for case in cases
        )
        contact_and_write = sum(
            bool(case["branches"][branch]["hits"])
            and bool(case["comparisons"][comparison]["different"])
            for case in cases
        )
        teacher_stats[branch] = {
            "contact_count": contact_count,
            "write_count": write_count,
            "contact_and_write_count": contact_and_write,
            "write_given_contact": (
                contact_and_write / contact_count if contact_count else None
            ),
            "full_hp_contact_case_count": sum(
                bool(case["branches"][branch]["hit_state_before"])
                and all(
                    bool(item["active_full_hp"])
                    for item in case["branches"][branch]["hit_state_before"]
                )
                for case in cases
            ),
        }

    bh_writes = [
        case for case in cases if case["comparisons"]["b_vs_h"]["different"]
    ]
    input_contact_probes = [
        probe
        for case in cases
        for probe in case["input"]["step_probes"]
        if probe["hits"]
    ]
    input_contact_write_probes = [
        probe for probe in input_contact_probes if probe["state_write"]
    ]
    input_contact_without_write_probes = [
        probe for probe in input_contact_probes if not probe["state_write"]
    ]
    input_saturated_without_write_probes = [
        probe
        for probe in input_contact_without_write_probes
        if probe["hit_state_before"]
        and all(item["active_full_hp"] for item in probe["hit_state_before"])
    ]
    bh_changed_field_case_counts = {
        name: sum(
            int(case["comparisons"]["b_vs_h"]["fields"][name]["changed_slots"]) > 0
            for case in cases
        )
        for name in FIELDS
    }
    bc_writes = [
        case for case in cases if case["comparisons"]["b_vs_c"]["different"]
    ]
    return {
        "case_count": len(cases),
        "input_contact_case_count": sum(
            int(case["input"]["hit_steps"]) > 0 for case in cases
        ),
        "input_contact_step_count": len(input_contact_probes),
        "input_contact_write_probe_step_count": len(input_contact_write_probes),
        "input_contact_without_write_probe_step_count": len(
            input_contact_without_write_probes
        ),
        "input_saturated_without_write_probe_step_count": len(
            input_saturated_without_write_probes
        ),
        "input_write_given_contact_probe": (
            len(input_contact_write_probes) / len(input_contact_probes)
            if input_contact_probes
            else None
        ),
        "input_after_input_write_case_count": sum(
            bool(case["input"]["after_input_diff"]["different"]) for case in cases
        ),
        "input_pre_teacher_difference_case_count": sum(
            bool(case["input"]["pre_teacher_diff"]["different"]) for case in cases
        ),
        "distinct_hit_pattern_count": {
            "median": statistics.median(pattern_counts) if pattern_counts else 0,
            "mean": mean(pattern_counts),
            "maximum": max(pattern_counts) if pattern_counts else 0,
            "distribution": {
                str(key): int(value)
                for key, value in sorted(Counter(pattern_counts).items())
            },
        },
        "effective_capacity_bits": {
            "median": statistics.median(capacities) if capacities else 0.0,
            "mean": mean(capacities),
            "maximum": max(capacities) if capacities else 0.0,
        },
        "pattern_entropy_bits": {
            "median": statistics.median(pattern_entropies) if pattern_entropies else 0.0,
            "mean": mean(pattern_entropies),
            "maximum": max(pattern_entropies) if pattern_entropies else 0.0,
        },
        "b_c_hitset_distinct_case_count": sum(
            bool(case["hit_capacity"]["b_c_hitset_distinct"]) for case in cases
        ),
        "b_h_hitset_distinct_case_count": sum(
            bool(case["hit_capacity"]["b_h_hitset_distinct"]) for case in cases
        ),
        "b_c_teacher_specific_write_case_count": len(bc_writes),
        "b_h_teacher_specific_write_case_count": len(bh_writes),
        "b_h_changed_field_case_counts": bh_changed_field_case_counts,
        "b_h_traceable_write_case_count": sum(
            bool(case["trace"]["b_h_traceable"]) for case in bh_writes
        ),
        "teacher_vs_control": teacher_stats,
        "no_teacher_control_repeat_match_count": sum(
            not case["comparisons"]["control_vs_control_repeat"]["different"]
            for case in cases
        ),
        "replay_match_count": sum(case["replay_match"] is True for case in cases),
        "raw_instrumented_match_count": sum(
            case["raw_instrumented_match"] is True for case in cases
        ),
    }


def build_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    geometry = geometry_analysis()
    by_density: dict[str, Any] = {}
    for density in DEFAULT_DENSITIES:
        density_cases = [
            case for case in cases if int(case["initial_density"]) == int(density)
        ]
        by_density[str(density)] = summarize_density(density_cases)

    density32 = by_density["32"]
    deterministic_ok = all(
        value["replay_match_count"] == value["case_count"]
        and value["raw_instrumented_match_count"] == value["case_count"]
        for value in by_density.values()
    )
    no_teacher_clean = all(
        value["no_teacher_control_repeat_match_count"] == value["case_count"]
        for value in by_density.values()
    )
    high_write_count = int(density32["b_h_teacher_specific_write_case_count"])
    traceable_count = int(density32["b_h_traceable_write_case_count"])
    route_memory = (
        deterministic_ok
        and no_teacher_clean
        and high_write_count >= 8
        and traceable_count >= 1
    )

    return {
        "issue": 120,
        "base_main": BASE_MAIN,
        "learning_claim": False,
        "p6_10_plus": "frozen",
        "geometry": geometry,
        "matrix": {
            "densities": list(DEFAULT_DENSITIES),
            "seeds": list(DEFAULT_SEEDS),
            "case_count": len(cases),
        },
        "by_density": by_density,
        "route_gate": {
            "required_density32_teacher_specific_writes": 8,
            "observed_density32_teacher_specific_writes": high_write_count,
            "required_traceable_write_cases": 1,
            "observed_traceable_write_cases": traceable_count,
            "deterministic_and_raw_equivalent": deterministic_ok,
            "no_teacher_control_repeat_match": no_teacher_clean,
            "route": "ROUTE-MEMORY" if route_memory else "ROUTE-CHANNEL-ARENA",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/default.json"))
    parser.add_argument(
        "--experiment", type=Path, default=Path("config/experiment_v0_1.json")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/artifacts/transduction_audit_120.jsonl"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("research/artifacts/transduction_audit_120_summary.json"),
    )
    parser.add_argument(
        "--geometry-only",
        action="store_true",
        help="emit only TX1 geometry analysis and do not run matched states",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    geometry = geometry_analysis()
    if not geometry["selection_matches_predeclared"]:
        raise SystemExit(
            "predeclared high-contrast comparator no longer matches current geometry"
        )

    if args.geometry_only:
        print(json.dumps(geometry, indent=2, sort_keys=True))
        return 0

    config_payload = load_config(args.config)
    experiment_payload = json.loads(args.experiment.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for density in DEFAULT_DENSITIES:
        for seed in DEFAULT_SEEDS:
            case = run_case(
                seed=seed,
                density=density,
                config_payload=config_payload,
                experiment_payload=experiment_payload,
            )
            cases.append(case)
            print(
                f"#120 density={density} seed={seed} "
                f"patterns={case['hit_capacity']['distinct_hit_pattern_count']} "
                f"bc_write={case['comparisons']['b_vs_c']['different']} "
                f"bh_write={case['comparisons']['b_vs_h']['different']}",
                file=sys.stderr,
                flush=True,
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(case, sort_keys=True) + "\n" for case in cases),
        encoding="utf-8",
    )
    summary = build_summary(cases)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
