"""Issue #113 matched-snapshot learning-channel causal audit.

This module is intentionally research-only. It imports the authoritative
physics and I/O layers but does not change their defaults or implementation.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Iterable, Mapping

from core.experiment import ExperimentConfig, IOExperiment
from core.io_bus import FixedOrgans, OutputEvent, read_output_signal
from core.physics import PhysicsConfig, create_universe
from core.state import UniverseState


BRANCHES = ("control", "a_only", "ab", "ac")
CHECKPOINT_LABELS = (
    "pre_stimulus",
    "teacher_byte",
    "teacher_sequence_complete",
    "plus_10",
    "plus_100",
    "plus_1000",
)
TRACKED_ARRAYS = (
    "hp",
    "latent",
    "bond_strength",
    "structure",
    "x",
    "y",
    "lifecycle",
)
DIAGNOSTIC_DENSITIES = (4, 32)
SEEDS = tuple(range(32))
INPUT_A = 65
TEACHER_B = 66
TEACHER_C = 67
TEACHER_HOLD_GENERATIONS = 4
BYTE_GAP_GENERATIONS = 4
TEACHER_DELAY_GENERATIONS = 4

AUDIT_PROTOCOL = ExperimentConfig(
    byte_hold_generations=TEACHER_HOLD_GENERATIONS,
    byte_gap_generations=BYTE_GAP_GENERATIONS,
    teacher_delay_generations=TEACHER_DELAY_GENERATIONS,
    teacher_repetitions=1,
    evaluation_timeout_generations=1024,
    counterfactual_input_byte=TEACHER_C,
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def snapshot_digest(snapshot: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()


def compare_state_snapshots(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare the physical state arrays and expose exact changed slots."""
    before_arrays = before.get("arrays", {})
    after_arrays = after.get("arrays", {})
    changed_fields: list[str] = []
    changed_slots: dict[str, list[int]] = {}
    for field in TRACKED_ARRAYS:
        first = list(before_arrays.get(field, ()))
        second = list(after_arrays.get(field, ()))
        if first == second:
            continue
        changed_fields.append(field)
        changed_slots[field] = [
            index
            for index, (left, right) in enumerate(zip(first, second))
            if left != right
        ]
        if len(first) != len(second):
            changed_slots[field].extend(
                range(min(len(first), len(second)), max(len(first), len(second)))
            )
    return {
        "identical": not changed_fields,
        "changed_fields": changed_fields,
        "changed_slots": changed_slots,
        "before_digest": snapshot_digest(before),
        "after_digest": snapshot_digest(after),
        "before_generation": int(before.get("generation", 0)),
        "after_generation": int(after.get("generation", 0)),
    }


def _active_count(snapshot: Mapping[str, Any]) -> int:
    lifecycle = snapshot.get("arrays", {}).get("lifecycle", ())
    return sum(int(value) == 1 for value in lifecycle)


def _output_neighborhood(state: UniverseState) -> tuple[int, ...]:
    experiment = IOExperiment(state, experiment=AUDIT_PROTOCOL)
    coordinates = FixedOrgans.coordinates()
    anchors = tuple(
        coordinates[name]
        for name in (
            FixedOrgans.output_valid,
            FixedOrgans.output_null,
            *FixedOrgans.output_data,
        )
    )
    return experiment._nearby_slots(anchors)


def _checkpoint(state: UniverseState, *, label: str) -> dict[str, Any]:
    snapshot = state.to_snapshot()
    signal = read_output_signal(state)
    return {
        "label": label,
        "generation": int(state.generation),
        "snapshot_digest": snapshot_digest(snapshot),
        "active_cells": _active_count(snapshot),
        "output_signal": {
            "value": int(signal.value),
            "valid": bool(signal.valid),
            "null": bool(signal.null),
        },
        "output_neighborhood_slots": list(_output_neighborhood(state)),
        "snapshot": snapshot,
    }


def _advance(
    experiment: IOExperiment,
    *,
    value: int | None = None,
    stimulus_kind: str = "none",
) -> tuple[Any, bool]:
    if value is None:
        experiment.release_input()
        anchors: tuple[tuple[int, int], ...] = ()
    else:
        experiment.drive_input(value)
        anchors = experiment.input_bus.signal_coordinates()
    contact_slots = experiment._nearby_slots(anchors)
    metrics = experiment._advance(anchors)
    return metrics, bool(contact_slots) if stimulus_kind != "none" else False


def _teacher_step(experiment: IOExperiment, event: OutputEvent) -> tuple[Any, bool]:
    anchors = experiment._teacher_coordinates(event)
    contact_slots = experiment._nearby_slots(anchors)
    metrics = experiment._advance(anchors)
    experiment.teacher_events.append(event)
    return metrics, bool(contact_slots)


def _run_branch(
    source_snapshot: Mapping[str, Any],
    *,
    branch: str,
    post_teacher_generations: int,
    capture: bool,
) -> dict[str, Any]:
    if branch not in BRANCHES:
        raise ValueError(f"unsupported branch: {branch}")
    state = UniverseState.from_snapshot(
        dict(source_snapshot),
        config=PhysicsConfig.from_mapping(source_snapshot["config"]),
    )
    experiment = IOExperiment(state, experiment=AUDIT_PROTOCOL)
    checkpoints: dict[str, dict[str, Any]] = {}
    input_contacts = 0
    teacher_contacts = 0
    activity_cost = 0
    started = time.perf_counter()

    def save(label: str) -> None:
        if capture:
            checkpoints[label] = _checkpoint(state, label=label)

    def idle(count: int) -> None:
        nonlocal activity_cost
        for _ in range(count):
            metrics, _ = _advance(experiment)
            activity_cost += metrics.activity_cost

    save("pre_stimulus")
    if branch != "control":
        for _ in range(TEACHER_HOLD_GENERATIONS):
            metrics, contact = _advance(
                experiment,
                value=INPUT_A,
                stimulus_kind="input",
            )
            activity_cost += metrics.activity_cost
            input_contacts += int(contact)
        idle(BYTE_GAP_GENERATIONS + TEACHER_DELAY_GENERATIONS)
    else:
        idle(TEACHER_HOLD_GENERATIONS + BYTE_GAP_GENERATIONS + TEACHER_DELAY_GENERATIONS)

    if branch in ("ab", "ac"):
        teacher_value = TEACHER_B if branch == "ab" else TEACHER_C
        metrics, contact = _teacher_step(experiment, OutputEvent.byte(teacher_value))
        activity_cost += metrics.activity_cost
        teacher_contacts += int(contact)
    else:
        metrics, _ = _advance(experiment)
        activity_cost += metrics.activity_cost
    save("teacher_byte")

    if branch in ("ab", "ac"):
        metrics, contact = _teacher_step(experiment, OutputEvent.null())
        activity_cost += metrics.activity_cost
        teacher_contacts += int(contact)
    else:
        metrics, _ = _advance(experiment)
        activity_cost += metrics.activity_cost
    save("teacher_sequence_complete")

    for count, label in (
        (10, "plus_10"),
        (100, "plus_100"),
        (post_teacher_generations, "plus_1000"),
    ):
        idle(count)
        save(label)

    elapsed = max(time.perf_counter() - started, 1e-12)
    final_snapshot = state.to_snapshot()
    return {
        "branch": branch,
        "source_digest": snapshot_digest(source_snapshot),
        "final_digest": snapshot_digest(final_snapshot),
        "final_snapshot": final_snapshot if capture else None,
        "checkpoint_digests": {
            label: record["snapshot_digest"]
            for label, record in checkpoints.items()
        },
        "checkpoints": checkpoints,
        "input_contacts": input_contacts,
        "teacher_contacts": teacher_contacts,
        "activity_cost": activity_cost,
        "generations": int(state.generation),
        "generations_per_second": int(state.generation) / elapsed,
        "elapsed_seconds": elapsed,
    }


def _event_to_dict(event: OutputEvent) -> dict[str, Any]:
    return {"kind": event.kind, "value": event.value}


def _evaluation_to_dict(result: Any) -> dict[str, Any]:
    return {
        "success": bool(result.success),
        "autonomous_events": [_event_to_dict(event) for event in result.autonomous_events],
        "event_generations": list(result.event_generations),
        "evaluation_generations": int(result.evaluation_generations),
        "timed_out": bool(result.timed_out),
        "activity_cost": int(result.activity_cost),
    }


def _evaluate_branch(record: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = record["final_snapshot"]
    state = UniverseState.from_snapshot(
        dict(snapshot),
        config=PhysicsConfig.from_mapping(snapshot["config"]),
    )
    experiment = IOExperiment(state, experiment=AUDIT_PROTOCOL)
    expected = (OutputEvent.byte(TEACHER_B), OutputEvent.null())
    canonical = experiment.evaluate_autonomous(input_byte=INPUT_A, expected=expected)
    no_input = experiment.evaluate_autonomous(
        input_byte=INPUT_A,
        input_valid=False,
        expected=(),
    )
    alternate = experiment.evaluate_autonomous(input_byte=TEACHER_C, expected=())
    return {
        "canonical": _evaluation_to_dict(canonical),
        "no_input": _evaluation_to_dict(no_input),
        "alternate": _evaluation_to_dict(alternate),
    }


def _has_state_delta(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    return not compare_state_snapshots(first["snapshot"], second["snapshot"])["identical"]


def _events_signature(evaluation: Mapping[str, Any]) -> tuple[tuple[str, int | None], ...]:
    return tuple(
        (str(event["kind"]), event.get("value"))
        for event in evaluation["canonical"]["autonomous_events"]
    )


def _count_target_events(evaluation: Mapping[str, Any]) -> int:
    return sum(
        event["kind"] == "byte" and int(event.get("value", -1)) == TEACHER_B
        for event in evaluation["canonical"]["autonomous_events"]
    )


def _causal_levels(
    branches: Mapping[str, Mapping[str, Any]],
    evaluations: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    control = branches["control"]["checkpoints"]
    a_only = branches["a_only"]["checkpoints"]
    ab = branches["ab"]["checkpoints"]
    ac = branches["ac"]["checkpoints"]

    l0 = all(
        branches[name]["input_contacts"] > 0
        for name in ("a_only", "ab", "ac")
    ) and all(branches[name]["teacher_contacts"] > 0 for name in ("ab", "ac"))
    l1 = _has_state_delta(a_only["teacher_byte"], control["teacher_byte"])
    l2 = (
        _has_state_delta(ab["teacher_byte"], ac["teacher_byte"])
        and _has_state_delta(ab["plus_10"], ac["plus_10"])
    )
    l3 = (
        _has_state_delta(ab["plus_100"], ac["plus_100"])
        and _has_state_delta(ab["plus_1000"], ac["plus_1000"])
    )
    l4 = _events_signature(evaluations["ab"]) != _events_signature(evaluations["ac"])
    l5 = (
        bool(evaluations["ab"]["canonical"]["autonomous_events"])
        or bool(evaluations["ac"]["canonical"]["autonomous_events"])
    ) and (
        bool(ab["plus_1000"]["output_neighborhood_slots"])
        or bool(ac["plus_1000"]["output_neighborhood_slots"])
    )
    target_counts = {
        name: _count_target_events(evaluations[name])
        for name in BRANCHES
    }
    l6 = target_counts["ab"] > max(
        target_counts["ac"], target_counts["control"], target_counts["a_only"]
    )
    controls_clean = all(
        evaluations[name][control_name]["success"]
        for name in BRANCHES
        for control_name in ("no_input", "alternate")
    )
    l7 = bool(evaluations["ab"]["canonical"]["success"] and controls_clean)
    levels = {
        "L0": l0,
        "L1": l1,
        "L2": l2,
        "L3": l3,
        "L4": l4,
        "L5": l5,
        "L6": l6,
        "L7": l7,
    }
    first_failed = next((level for level, passed in levels.items() if not passed), None)
    return {
        "levels": levels,
        "first_failed_level": first_failed,
        "target_b_counts": target_counts,
        "controls_clean": controls_clean,
        "learning_claim": l7,
    }


def run_case(seed: int, density: int, *, generations: int = 1000) -> dict[str, Any]:
    """Run one deterministic density/seed case and its replay evidence."""
    config = PhysicsConfig(initial_density=int(density))
    source = create_universe(seed=int(seed), config=config)
    source_snapshot = source.to_snapshot()
    source_digest = snapshot_digest(source_snapshot)

    instrumented: dict[str, dict[str, Any]] = {}
    for branch in BRANCHES:
        instrumented[branch] = _run_branch(
            source_snapshot,
            branch=branch,
            post_teacher_generations=int(generations),
            capture=True,
        )

    replay = {
        branch: _run_branch(
            source_snapshot,
            branch=branch,
            post_teacher_generations=int(generations),
            capture=True,
        )
        for branch in BRANCHES
    }
    replay_equal = all(
        instrumented[branch]["checkpoint_digests"] == replay[branch]["checkpoint_digests"]
        for branch in BRANCHES
    )

    raw_started = time.perf_counter()
    raw_ab = _run_branch(
        source_snapshot,
        branch="ab",
        post_teacher_generations=int(generations),
        capture=False,
    )
    raw_elapsed = max(time.perf_counter() - raw_started, 1e-12)
    instrumented_elapsed = instrumented["ab"]["elapsed_seconds"]
    raw_instrumented_equal = raw_ab["final_digest"] == instrumented["ab"]["final_digest"]
    overhead_percent = ((instrumented_elapsed / raw_elapsed) - 1.0) * 100.0

    evaluations = {
        branch: _evaluate_branch(instrumented[branch])
        for branch in BRANCHES
    }
    causal = _causal_levels(instrumented, evaluations)
    return {
        "status": "complete",
        "seed": int(seed),
        "density": int(density),
        "source_digest": source_digest,
        "source_generation": int(source_snapshot["generation"]),
        "branches": instrumented,
        "evaluations": evaluations,
        "causal": causal,
        "replay_equal": replay_equal,
        "raw_instrumented_equal": raw_instrumented_equal,
        "raw_generations_per_second": int(raw_ab["generations"]) / raw_elapsed,
        "instrumented_generations_per_second": int(instrumented["ab"]["generations"]) / max(instrumented_elapsed, 1e-12),
        "instrumentation_overhead_percent": overhead_percent,
    }


def _read_rows(path: Path) -> dict[tuple[int, int], dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[tuple[int, int], dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[(int(row["density"]), int(row["seed"]))] = row
    return rows


def summarize(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    values = list(rows)
    by_density: dict[str, Any] = {}
    for density in sorted({int(row["density"]) for row in values}):
        group = [row for row in values if int(row["density"]) == density]
        by_density[str(density)] = {
            "cases": len(group),
            "replay_equal": sum(bool(row["replay_equal"]) for row in group),
            "raw_instrumented_equal": sum(bool(row["raw_instrumented_equal"]) for row in group),
            "learning_claims": sum(bool(row["causal"]["learning_claim"]) for row in group),
            "first_failed_level_counts": {
                str(level): sum(row["causal"]["first_failed_level"] == level for row in group)
                for level in ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", None)
            },
            "mean_instrumentation_overhead_percent": (
                sum(float(row["instrumentation_overhead_percent"]) for row in group) / len(group)
                if group else 0.0
            ),
        }
    return {
        "kind": "UniverseGenomeIssue113CausalAudit",
        "status": "complete" if values and all(row["status"] == "complete" for row in values) else "incomplete",
        "matrix": {
            "densities": sorted({int(row["density"]) for row in values}),
            "seeds": sorted({int(row["seed"]) for row in values}),
            "cases": len(values),
            "branches": list(BRANCHES),
            "checkpoints": list(CHECKPOINT_LABELS),
        },
        "replay_mismatch_count": sum(not row["replay_equal"] for row in values),
        "raw_instrumented_mismatch_count": sum(not row["raw_instrumented_equal"] for row in values),
        "learning_claim": any(row["causal"]["learning_claim"] for row in values),
        "by_density": by_density,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--densities", nargs="+", type=int, default=list(DIAGNOSTIC_DENSITIES))
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--generations", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)

    rows = _read_rows(args.output)
    pending = [
        (density, seed)
        for density in args.densities
        for seed in args.seeds
        if (int(density), int(seed)) not in rows
    ]
    if args.workers > 1 and pending:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            results = executor.map(
                _run_case_args,
                ((seed, density, args.generations) for density, seed in pending),
            )
            for row in results:
                rows[(int(row["density"]), int(row["seed"]))] = row
                _append_row(args.output, row)
    else:
        for density, seed in pending:
            row = run_case(seed, density, generations=args.generations)
            rows[(int(row["density"]), int(row["seed"]))] = row
            _append_row(args.output, row)
    summary = summarize(rows.values())
    args.summary.write_text(_canonical_json(summary) + "\n", encoding="utf-8")
    print(_canonical_json(summary))
    return 0


def _run_case_args(arguments: tuple[int, int, int]) -> dict[str, Any]:
    seed, density, generations = arguments
    return run_case(seed, density, generations=generations)


def _append_row(path: Path, row: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical_json(row) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
