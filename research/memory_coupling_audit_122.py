"""Memory coupling / persistence audit for UniverseGenome #122.

Research-only harness. It reuses the accepted #120 B=66 versus H=8 immediate
write condition and measures persistence under unchanged production physics.

The protocol, cohorts, horizons and terminal routing threshold were frozen in
UniverseGenome#122 before any new persistence outcome was inspected.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.experiment import ExperimentConfig, IOExperiment
from core.physics import create_universe
from core.runner import load_config
from research.transduction_audit_120 import (
    FIELDS,
    TEACHER_B,
    TEACHER_H,
    advance_to_pre_teacher,
    build_physics_config,
    canonical_digest,
    clone_state,
    snapshot_diff,
    teacher_step,
)

BASE_MAIN = "2783b7fa16e8e266432ae0d6231a9a87cf35e51a"
HORIZONS = (0, 1, 10, 100, 1000)
PRIMARY_DENSITY32_SEEDS = (0, 5, 8, 9, 12, 14, 18, 19, 20, 22, 24, 29)
NEGATIVE_DENSITY32_SEEDS = (
    1, 2, 3, 4, 6, 7, 10, 11, 13, 15,
    16, 17, 21, 23, 25, 26, 27, 28, 30, 31,
)
NEGATIVE_DENSITY32_SENTINELS = (1, 2, 3, 4)
DENSITY4_SEEDS = tuple(range(32))
DENSITY4_WRITE_POSITIVE_SEEDS = (9,)
DENSITY4_NEGATIVE_SENTINELS = (0, 1, 2, 3)
ROUTE_RECALL_REQUIRED_PRIMARY_PERSISTENT = 8

NETWORK_FIELDS = frozenset(("latent", "bond_strength", "structure"))
LIFECYCLE_KINEMATIC_FIELDS = frozenset(
    ("lifecycle", "x", "y", "direction", "speed_code", "age", "black_hole_timer")
)


def changed_field_names(diff: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        name for name in FIELDS
        if int(diff["fields"][name]["changed_slots"]) > 0
    )


def classify_diff(diff: dict[str, Any]) -> str:
    if not bool(diff["different"]):
        return "RECONVERGED"
    changed = set(changed_field_names(diff))
    if changed <= {"hp"}:
        return "HP_ONLY"
    if changed.intersection(NETWORK_FIELDS):
        return "NETWORK_COUPLED"
    return "LIFECYCLE_KINEMATIC"


def branch_checkpoint(snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    b = snapshots["b"]
    h = snapshots["h"]
    control = snapshots["control"]
    control_repeat = snapshots["control_repeat"]
    return {
        "branch_digests": {
            name: canonical_digest(snapshot)
            for name, snapshot in snapshots.items()
        },
        "comparisons": {
            "b_vs_h": snapshot_diff(b, h),
            "b_vs_control": snapshot_diff(b, control),
            "h_vs_control": snapshot_diff(h, control),
            "control_vs_control_repeat": snapshot_diff(
                control, control_repeat
            ),
        },
    }


def case_once(
    *,
    seed: int,
    density: int,
    role: str,
    long_horizon: bool,
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
        instrumented=False,
    )
    pre_teacher = prepared["a_pre_teacher"]

    teacher_branches = {
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
        "h": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=TEACHER_H,
            instrumented=instrumented,
        ),
    }

    h0_snapshots = {
        name: value["after_snapshot"] for name, value in teacher_branches.items()
    }
    checkpoints: dict[str, Any] = {"0": branch_checkpoint(h0_snapshots)}

    h0_diff = checkpoints["0"]["comparisons"]["b_vs_h"]
    first_reconvergence_generation: int | None = (
        0 if not h0_diff["different"] else None
    )
    first_non_hp_generation: int | None = None
    first_network_coupled_generation: int | None = None
    first_lifecycle_kinematic_generation: int | None = None
    first_field_generation: dict[str, int] = {}
    classification_events: list[dict[str, Any]] = []

    if instrumented:
        h0_classification = classify_diff(h0_diff)
        h0_fields = changed_field_names(h0_diff)
        classification_events.append(
            {
                "generation": 0,
                "classification": h0_classification,
                "changed_fields": list(h0_fields),
                "changed_slot_count": len(h0_diff["changed_slots"]),
            }
        )
        for field in h0_fields:
            first_field_generation[field] = 0
        if any(field != "hp" for field in h0_fields):
            first_non_hp_generation = 0
        if set(h0_fields).intersection(NETWORK_FIELDS):
            first_network_coupled_generation = 0
        if set(h0_fields).intersection(LIFECYCLE_KINEMATIC_FIELDS):
            first_lifecycle_kinematic_generation = 0

    if long_horizon:
        states = {
            name: clone_state(snapshot, config)
            for name, snapshot in h0_snapshots.items()
        }
        experiments = {
            name: IOExperiment(state, experiment=protocol)
            for name, state in states.items()
        }
        last_event_signature: tuple[Any, ...] | None = None
        if instrumented and classification_events:
            first_event = classification_events[-1]
            last_event_signature = (
                first_event["classification"],
                tuple(first_event["changed_fields"]),
                int(first_event["changed_slot_count"]),
            )

        for generation in range(1, max(HORIZONS) + 1):
            for experiment in experiments.values():
                experiment._advance(())

            b_snapshot: dict[str, Any] | None = None
            h_snapshot: dict[str, Any] | None = None
            if instrumented:
                b_snapshot = states["b"].to_snapshot()
                h_snapshot = states["h"].to_snapshot()
                bh_diff = snapshot_diff(b_snapshot, h_snapshot)
                classification = classify_diff(bh_diff)
                fields = changed_field_names(bh_diff)

                if (
                    first_reconvergence_generation is None
                    and not bool(bh_diff["different"])
                ):
                    first_reconvergence_generation = generation
                if (
                    first_non_hp_generation is None
                    and any(field != "hp" for field in fields)
                ):
                    first_non_hp_generation = generation
                if (
                    first_network_coupled_generation is None
                    and set(fields).intersection(NETWORK_FIELDS)
                ):
                    first_network_coupled_generation = generation
                if (
                    first_lifecycle_kinematic_generation is None
                    and set(fields).intersection(LIFECYCLE_KINEMATIC_FIELDS)
                ):
                    first_lifecycle_kinematic_generation = generation
                for field in fields:
                    first_field_generation.setdefault(field, generation)

                signature = (
                    classification,
                    tuple(fields),
                    len(bh_diff["changed_slots"]),
                )
                if signature != last_event_signature:
                    classification_events.append(
                        {
                            "generation": generation,
                            "classification": classification,
                            "changed_fields": list(fields),
                            "changed_slot_count": len(bh_diff["changed_slots"]),
                        }
                    )
                    last_event_signature = signature

            if generation in HORIZONS:
                snapshots: dict[str, dict[str, Any]] = {}
                for name, state in states.items():
                    if name == "b" and b_snapshot is not None:
                        snapshots[name] = b_snapshot
                    elif name == "h" and h_snapshot is not None:
                        snapshots[name] = h_snapshot
                    else:
                        snapshots[name] = state.to_snapshot()
                checkpoints[str(generation)] = branch_checkpoint(snapshots)

    return {
        "status": "complete",
        "seed": int(seed),
        "initial_density": int(density),
        "role": role,
        "long_horizon": bool(long_horizon),
        "initial_snapshot_digest": canonical_digest(initial_snapshot),
        "pre_teacher_snapshot_digest": canonical_digest(pre_teacher),
        "teacher_hits": {
            name: value["hits"]
            for name, value in teacher_branches.items()
            if name in ("b", "h")
        },
        "horizons": checkpoints,
        "trace": {
            "first_reconvergence_generation": first_reconvergence_generation,
            "first_non_hp_generation": first_non_hp_generation,
            "first_network_coupled_generation": first_network_coupled_generation,
            "first_lifecycle_kinematic_generation": (
                first_lifecycle_kinematic_generation
            ),
            "first_field_generation": first_field_generation,
            "classification_events": classification_events,
        },
    }


def deterministic_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": case["seed"],
        "initial_density": case["initial_density"],
        "role": case["role"],
        "long_horizon": case["long_horizon"],
        "initial_snapshot_digest": case["initial_snapshot_digest"],
        "pre_teacher_snapshot_digest": case["pre_teacher_snapshot_digest"],
        "teacher_hits": case["teacher_hits"],
        "horizons": case["horizons"],
        "trace": case["trace"],
    }


def raw_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": case["seed"],
        "initial_density": case["initial_density"],
        "role": case["role"],
        "long_horizon": case["long_horizon"],
        "initial_snapshot_digest": case["initial_snapshot_digest"],
        "pre_teacher_snapshot_digest": case["pre_teacher_snapshot_digest"],
        "horizon_branch_digests": {
            horizon: checkpoint["branch_digests"]
            for horizon, checkpoint in case["horizons"].items()
        },
    }


def run_case(
    *,
    seed: int,
    density: int,
    role: str,
    long_horizon: bool,
    verify: bool,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
) -> dict[str, Any]:
    first = case_once(
        seed=seed,
        density=density,
        role=role,
        long_horizon=long_horizon,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
    )
    first["replay_match"] = None
    first["raw_instrumented_match"] = None
    if not verify:
        return first

    second = case_once(
        seed=seed,
        density=density,
        role=role,
        long_horizon=long_horizon,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
    )
    raw = case_once(
        seed=seed,
        density=density,
        role=role,
        long_horizon=long_horizon,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=False,
    )

    first_digest = canonical_digest(deterministic_projection(first))
    second_digest = canonical_digest(deterministic_projection(second))
    replay_match = first_digest == second_digest
    raw_match = raw_projection(first) == raw_projection(raw)
    first["replay_match"] = replay_match
    first["raw_instrumented_match"] = raw_match

    if not replay_match:
        raise RuntimeError(
            f"non-deterministic #122 case density={density} seed={seed}"
        )
    if not raw_match:
        raise RuntimeError(
            f"instrumentation perturbs #122 case density={density} seed={seed}"
        )
    return first


def case_plan() -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    primary = set(PRIMARY_DENSITY32_SEEDS)
    negative_sentinels = set(NEGATIVE_DENSITY32_SENTINELS)
    for seed in range(32):
        if seed in primary:
            role = "density32_primary_write_positive"
            long_horizon = True
            verify = True
        else:
            role = "density32_immediate_no_write"
            long_horizon = seed in negative_sentinels
            verify = False
        plan.append(
            {
                "seed": seed,
                "density": 32,
                "role": role,
                "long_horizon": long_horizon,
                "verify": verify,
            }
        )

    d4_long = set(DENSITY4_WRITE_POSITIVE_SEEDS).union(
        DENSITY4_NEGATIVE_SENTINELS
    )
    for seed in DENSITY4_SEEDS:
        role = (
            "density4_write_positive_control"
            if seed in DENSITY4_WRITE_POSITIVE_SEEDS
            else "density4_default_control"
        )
        plan.append(
            {
                "seed": seed,
                "density": 4,
                "role": role,
                "long_horizon": seed in d4_long,
                "verify": seed in DENSITY4_WRITE_POSITIVE_SEEDS,
            }
        )
    return plan


def hdiff(case: dict[str, Any], horizon: int) -> dict[str, Any] | None:
    checkpoint = case["horizons"].get(str(horizon))
    if checkpoint is None:
        return None
    return checkpoint["comparisons"]["b_vs_h"]


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    primary = [
        case
        for case in cases
        if case["role"] == "density32_primary_write_positive"
    ]
    negative32 = [
        case for case in cases if case["role"] == "density32_immediate_no_write"
    ]
    negative_sentinels = [
        case
        for case in negative32
        if case["seed"] in NEGATIVE_DENSITY32_SENTINELS
    ]
    density4 = [case for case in cases if case["initial_density"] == 4]

    primary_h0 = sum(bool(hdiff(case, 0)["different"]) for case in primary)
    primary_h1000 = sum(bool(hdiff(case, 1000)["different"]) for case in primary)
    primary_classification_h1000 = Counter(
        classify_diff(hdiff(case, 1000)) for case in primary
    )
    primary_network_ever = sum(
        case["trace"]["first_network_coupled_generation"] is not None
        for case in primary
    )
    primary_non_hp_ever = sum(
        case["trace"]["first_non_hp_generation"] is not None
        for case in primary
    )
    primary_reconverged_by_1000 = sum(
        case["trace"]["first_reconvergence_generation"] is not None
        and int(case["trace"]["first_reconvergence_generation"]) <= 1000
        for case in primary
    )

    primary_replay_clean = all(case["replay_match"] is True for case in primary)
    primary_raw_clean = all(
        case["raw_instrumented_match"] is True for case in primary
    )

    long_cases = [case for case in cases if case["long_horizon"]]
    control_repeat_clean = all(
        not checkpoint["comparisons"]["control_vs_control_repeat"]["different"]
        for case in cases
        for checkpoint in case["horizons"].values()
    )

    negative_sentinel_emergent = sum(
        bool(hdiff(case, 1000)["different"]) for case in negative_sentinels
    )
    density32_negative_h0_write = sum(
        bool(hdiff(case, 0)["different"]) for case in negative32
    )

    density4_h0_write = sum(bool(hdiff(case, 0)["different"]) for case in density4)
    density4_long_persistent = {
        str(case["seed"]): bool(hdiff(case, 1000)["different"])
        for case in density4
        if case["long_horizon"]
    }

    route_recall = (
        primary_h0 == len(PRIMARY_DENSITY32_SEEDS)
        and primary_h1000 >= ROUTE_RECALL_REQUIRED_PRIMARY_PERSISTENT
        and primary_replay_clean
        and primary_raw_clean
        and control_repeat_clean
        and negative_sentinel_emergent == 0
    )
    route = "ROUTE-RECALL" if route_recall else "ROUTE-MEMORY-ARENA"

    return {
        "issue": 122,
        "base_main": BASE_MAIN,
        "learning_claim": False,
        "p6_10_plus": "frozen",
        "physics_change": False,
        "protocol": {
            "teacher_b": TEACHER_B,
            "teacher_h": TEACHER_H,
            "horizons": list(HORIZONS),
            "no_further_external_stimulation_after_h0": True,
            "route_recall_required_primary_persistent": (
                ROUTE_RECALL_REQUIRED_PRIMARY_PERSISTENT
            ),
        },
        "cohorts": {
            "density32_primary": list(PRIMARY_DENSITY32_SEEDS),
            "density32_negative": list(NEGATIVE_DENSITY32_SEEDS),
            "density32_negative_sentinels": list(
                NEGATIVE_DENSITY32_SENTINELS
            ),
            "density4_all": list(DENSITY4_SEEDS),
            "density4_write_positive": list(DENSITY4_WRITE_POSITIVE_SEEDS),
            "density4_negative_sentinels": list(DENSITY4_NEGATIVE_SENTINELS),
        },
        "matrix": {
            "case_count": len(cases),
            "long_horizon_case_count": len(long_cases),
            "verified_primary_case_count": sum(
                case["replay_match"] is not None for case in primary
            ),
        },
        "primary_density32": {
            "case_count": len(primary),
            "h0_write_count": primary_h0,
            "h1000_persistent_count": primary_h1000,
            "h1000_classification_counts": dict(primary_classification_h1000),
            "network_coupled_ever_count": primary_network_ever,
            "non_hp_ever_count": primary_non_hp_ever,
            "reconverged_by_1000_count": primary_reconverged_by_1000,
            "replay_clean": primary_replay_clean,
            "raw_instrumented_clean": primary_raw_clean,
        },
        "controls": {
            "density32_negative_h0_write_count": density32_negative_h0_write,
            "density32_negative_sentinel_h1000_emergent_count": (
                negative_sentinel_emergent
            ),
            "density4_h0_write_count": density4_h0_write,
            "density4_long_h1000_persistent": density4_long_persistent,
            "duplicate_no_teacher_control_clean": control_repeat_clean,
        },
        "route_gate": {
            "required_primary_h1000_persistent": (
                ROUTE_RECALL_REQUIRED_PRIMARY_PERSISTENT
            ),
            "observed_primary_h1000_persistent": primary_h1000,
            "primary_h0_reproduced": primary_h0 == len(PRIMARY_DENSITY32_SEEDS),
            "primary_replay_clean": primary_replay_clean,
            "primary_raw_instrumented_clean": primary_raw_clean,
            "negative_sentinels_clean": negative_sentinel_emergent == 0,
            "duplicate_no_teacher_control_clean": control_repeat_clean,
            "route": route,
        },
    }


def case_key(density: int, seed: int) -> str:
    return f"{int(density)}:{int(seed)}"


def read_completed(path: Path) -> dict[str, dict[str, Any]]:
    completed: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return completed
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            material = line.strip()
            if not material:
                continue
            item = json.loads(material)
            if item.get("status") != "complete":
                continue
            try:
                key = case_key(
                    int(item["initial_density"]),
                    int(item["seed"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid #122 JSONL case at line {line_number}"
                ) from exc
            completed[key] = item
    return completed


def append_case(handle: Any, case: dict[str, Any]) -> None:
    handle.write(json.dumps(case, sort_keys=True, separators=(",", ":")))
    handle.write("\n")
    handle.flush()


def write_summary(summary: dict[str, Any], *, summary_path: Path) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/default.json"))
    parser.add_argument(
        "--experiment",
        type=Path,
        default=Path("config/experiment_v0_1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/artifacts/memory_coupling_audit_122.jsonl"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("research/artifacts/memory_coupling_audit_122_summary.json"),
    )
    args = parser.parse_args()

    config_payload = load_config(args.config)
    experiment_payload = json.loads(args.experiment.read_text(encoding="utf-8"))
    plan = case_plan()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    completed = read_completed(args.output)
    pending = [
        spec
        for spec in plan
        if case_key(int(spec["density"]), int(spec["seed"])) not in completed
    ]
    if pending and args.summary.exists():
        args.summary.unlink()

    print(
        f"#122 resume: completed={len(completed)} pending={len(pending)}",
        file=sys.stderr,
        flush=True,
    )

    with args.output.open("a", encoding="utf-8", newline="\n") as handle:
        for spec in pending:
            case = run_case(
                seed=int(spec["seed"]),
                density=int(spec["density"]),
                role=str(spec["role"]),
                long_horizon=bool(spec["long_horizon"]),
                verify=bool(spec["verify"]),
                config_payload=config_payload,
                experiment_payload=experiment_payload,
            )
            append_case(handle, case)
            completed[case_key(case["initial_density"], case["seed"])] = case
            print(
                "#122 "
                f"density={case['initial_density']} seed={case['seed']} "
                f"role={case['role']} long={case['long_horizon']} "
                f"h0={bool(hdiff(case, 0)['different'])} "
                f"h1000={None if hdiff(case, 1000) is None else bool(hdiff(case, 1000)['different'])}",
                file=sys.stderr,
                flush=True,
            )

    missing = [
        case_key(int(spec["density"]), int(spec["seed"]))
        for spec in plan
        if case_key(int(spec["density"]), int(spec["seed"])) not in completed
    ]
    if missing:
        raise RuntimeError(f"incomplete #122 matrix after run: {missing}")

    cases = [
        completed[case_key(int(spec["density"]), int(spec["seed"]))]
        for spec in plan
    ]
    result = summarize(cases)
    write_summary(result, summary_path=args.summary)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
