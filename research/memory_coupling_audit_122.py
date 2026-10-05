"""Teacher-specific memory coupling / persistence audit for UniverseGenome #122.

Research-only harness. It starts from the accepted #120 B=66/H=8 immediate-write
condition and observes ordinary physics after the teacher-byte commit. It must not
mutate production physics/defaults or the P6.10+ capability boundary.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.experiment import ExperimentConfig, IOExperiment
from core.physics import PhysicsConfig, StepMetrics, create_universe
from core.runner import load_config
from core.state import UniverseState
from research.transduction_audit_120 import (
    FIELDS,
    TEACHER_B,
    TEACHER_H,
    advance_to_pre_teacher,
    build_physics_config,
    canonical_digest,
    clone_state,
    teacher_coordinates,
)

BASE_MAIN = "2783b7fa16e8e266432ae0d6231a9a87cf35e51a"
DEFAULT_DENSITIES = (4, 32)
DEFAULT_SEEDS = tuple(range(32))
PRIMARY_DENSITY32_SEEDS = (0, 5, 8, 9, 12, 14, 18, 19, 20, 22, 24, 29)
NO_WRITE_DENSITY32_SEEDS = tuple(
    seed for seed in DEFAULT_SEEDS if seed not in set(PRIMARY_DENSITY32_SEEDS)
)
CHECKPOINT_GENERATIONS = (0, 1, 10, 100, 1000)
BRANCHES = ("control", "control_repeat", "b", "h")
NETWORK_COUPLING_FIELDS = frozenset(
    {"latent", "bond_strength", "structure", "x", "y", "direction", "speed_code"}
)
PASSIVE_LIFETIME_FIELDS = frozenset({"hp", "lifecycle", "age", "black_hole_timer"})


def live_state_diff(first: UniverseState, second: UniverseState) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    changed_union: set[int] = set()
    for name in FIELDS:
        left = getattr(first, name)
        right = getattr(second, name)
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


def changed_field_names(diff: dict[str, Any]) -> list[str]:
    return [
        name
        for name in FIELDS
        if int(diff["fields"][name]["changed_slots"]) > 0
    ]


def classify_difference(
    diff: dict[str, Any],
    *,
    t0_changed_slots: Iterable[int],
) -> dict[str, Any]:
    if not diff["different"]:
        return {
            "class": "RECONVERGED",
            "changed_fields": [],
            "new_changed_slots": [],
        }
    changed_fields = changed_field_names(diff)
    t0_slots = set(int(slot) for slot in t0_changed_slots)
    new_slots = sorted(set(int(slot) for slot in diff["changed_slots"]) - t0_slots)
    if new_slots or NETWORK_COUPLING_FIELDS.intersection(changed_fields):
        classification = "COUPLED_NON_HP"
    elif set(changed_fields).issubset({"hp"}):
        classification = "HP_ONLY"
    elif set(changed_fields).issubset(PASSIVE_LIFETIME_FIELDS):
        classification = "PASSIVE_LIFETIME"
    else:
        classification = "COUPLED_NON_HP"
    return {
        "class": classification,
        "changed_fields": changed_fields,
        "new_changed_slots": new_slots,
    }


def add_activity(total: Counter[str], metrics: StepMetrics) -> None:
    total["collision_count"] += int(metrics.collision_count)
    total["bond_contact_count"] += int(metrics.bond_contact_count)
    total["latent_transmission_count"] += int(metrics.latent_transmission_count)
    total["fusion_count"] += int(metrics.fusion_count)
    total["fragmentation_count"] += int(metrics.fragmentation_count)
    total["noise_spawn_count"] += int(metrics.noise_spawn_count)


def activity_delta(first: Counter[str], second: Counter[str]) -> dict[str, int]:
    keys = sorted(set(first) | set(second))
    return {key: int(first[key]) - int(second[key]) for key in keys}


def _make_branch(
    pre_teacher_snapshot: dict[str, Any],
    *,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
    teacher_value: int | None,
    instrumented: bool,
) -> dict[str, Any]:
    state = clone_state(pre_teacher_snapshot, config)
    experiment = IOExperiment(state, experiment=protocol)
    hits: tuple[int, ...] = ()
    if teacher_value is None:
        metrics = experiment._advance(())
    else:
        anchors = teacher_coordinates(teacher_value)
        if instrumented:
            hits = tuple(sorted(experiment._nearby_slots(anchors)))
        metrics = experiment._advance(anchors)
    return {
        "teacher_value": teacher_value,
        "state": state,
        "experiment": experiment,
        "hits": list(hits),
        "teacher_step_metrics": {
            "collision_count": int(metrics.collision_count),
            "bond_contact_count": int(metrics.bond_contact_count),
            "latent_transmission_count": int(metrics.latent_transmission_count),
            "fusion_count": int(metrics.fusion_count),
            "fragmentation_count": int(metrics.fragmentation_count),
            "noise_spawn_count": int(metrics.noise_spawn_count),
        },
        "activity": Counter(),
    }


def _checkpoint_record(
    branches: dict[str, dict[str, Any]],
    *,
    t0_changed_slots: Iterable[int],
) -> dict[str, Any]:
    b_state = branches["b"]["state"]
    h_state = branches["h"]["state"]
    control_state = branches["control"]["state"]
    control_repeat_state = branches["control_repeat"]["state"]
    bh_diff = live_state_diff(b_state, h_state)
    control_diff = live_state_diff(control_state, control_repeat_state)
    b_control_diff = live_state_diff(b_state, control_state)
    h_control_diff = live_state_diff(h_state, control_state)
    classification = classify_difference(
        bh_diff,
        t0_changed_slots=t0_changed_slots,
    )
    return {
        "generation": int(b_state.generation),
        "branch_digests": {
            name: canonical_digest(branch["state"].to_snapshot())
            for name, branch in branches.items()
        },
        "b_vs_h": bh_diff,
        "b_vs_control": b_control_diff,
        "h_vs_control": h_control_diff,
        "control_vs_control_repeat": control_diff,
        "classification": classification,
        "post_t0_activity": {
            name: dict(branch["activity"])
            for name, branch in branches.items()
        },
        "b_h_activity_delta": activity_delta(
            branches["b"]["activity"], branches["h"]["activity"]
        ),
    }


def case_once(
    *,
    seed: int,
    density: int,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
    instrumented: bool,
    checkpoint_generations: tuple[int, ...] = CHECKPOINT_GENERATIONS,
) -> dict[str, Any]:
    if not checkpoint_generations or checkpoint_generations[0] != 0:
        raise ValueError("checkpoint_generations must start at 0")
    if tuple(sorted(set(checkpoint_generations))) != checkpoint_generations:
        raise ValueError("checkpoint_generations must be strictly increasing")
    max_generation = checkpoint_generations[-1]

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

    branches = {
        "control": _make_branch(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=None,
            instrumented=instrumented,
        ),
        "control_repeat": _make_branch(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=None,
            instrumented=instrumented,
        ),
        "b": _make_branch(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=TEACHER_B,
            instrumented=instrumented,
        ),
        "h": _make_branch(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=TEACHER_H,
            instrumented=instrumented,
        ),
    }

    t0_diff = live_state_diff(branches["b"]["state"], branches["h"]["state"])
    t0_changed_slots = tuple(int(slot) for slot in t0_diff["changed_slots"])
    expected_primary = density == 32 and seed in PRIMARY_DENSITY32_SEEDS
    expected_no_write = density == 32 and seed in NO_WRITE_DENSITY32_SEEDS

    checkpoints: dict[str, Any] = {}
    if instrumented:
        checkpoints["t0"] = _checkpoint_record(
            branches,
            t0_changed_slots=t0_changed_slots,
        )
    else:
        checkpoints["t0"] = {
            "generation": int(branches["b"]["state"].generation),
            "branch_digests": {
                name: canonical_digest(branch["state"].to_snapshot())
                for name, branch in branches.items()
            },
        }

    trace_every_generation = bool(expected_primary and instrumented)
    trace = {
        "enabled": trace_every_generation,
        "t0_changed_slots": list(t0_changed_slots),
        "first_non_hp_generation": None,
        "first_spread_generation": None,
        "first_passive_lifetime_generation": None,
        "first_reconvergence_generation": None,
        "last_different_generation": 0 if t0_diff["different"] else None,
    }
    if trace_every_generation and t0_diff["different"]:
        t0_class = classify_difference(t0_diff, t0_changed_slots=t0_changed_slots)
        if t0_class["class"] == "COUPLED_NON_HP":
            trace["first_non_hp_generation"] = 0
        if t0_class["new_changed_slots"]:
            trace["first_spread_generation"] = 0
        if t0_class["class"] == "PASSIVE_LIFETIME":
            trace["first_passive_lifetime_generation"] = 0
    elif trace_every_generation and not t0_diff["different"]:
        trace["first_reconvergence_generation"] = 0

    checkpoint_set = set(checkpoint_generations[1:])
    trace_reconverged = not bool(t0_diff["different"])

    for relative_generation in range(1, max_generation + 1):
        for name in BRANCHES:
            metrics = branches[name]["experiment"]._advance(())
            if instrumented:
                add_activity(branches[name]["activity"], metrics)

        if trace_every_generation and not trace_reconverged:
            diff = live_state_diff(branches["b"]["state"], branches["h"]["state"])
            classified = classify_difference(
                diff,
                t0_changed_slots=t0_changed_slots,
            )
            if diff["different"]:
                trace["last_different_generation"] = relative_generation
                if (
                    trace["first_non_hp_generation"] is None
                    and classified["class"] == "COUPLED_NON_HP"
                ):
                    trace["first_non_hp_generation"] = relative_generation
                if (
                    trace["first_spread_generation"] is None
                    and classified["new_changed_slots"]
                ):
                    trace["first_spread_generation"] = relative_generation
                if (
                    trace["first_passive_lifetime_generation"] is None
                    and classified["class"] == "PASSIVE_LIFETIME"
                ):
                    trace["first_passive_lifetime_generation"] = relative_generation
            else:
                trace["first_reconvergence_generation"] = relative_generation
                trace_reconverged = True

        if relative_generation in checkpoint_set:
            key = f"plus_{relative_generation}"
            if instrumented:
                checkpoints[key] = _checkpoint_record(
                    branches,
                    t0_changed_slots=t0_changed_slots,
                )
            else:
                checkpoints[key] = {
                    "generation": int(branches["b"]["state"].generation),
                    "branch_digests": {
                        name: canonical_digest(branch["state"].to_snapshot())
                        for name, branch in branches.items()
                    },
                }

    result: dict[str, Any] = {
        "status": "complete",
        "seed": int(seed),
        "initial_density": int(density),
        "initial_snapshot_digest": canonical_digest(initial_snapshot),
        "pre_teacher_snapshot_digest": canonical_digest(pre_teacher),
        "cohort": {
            "expected_primary_density32": expected_primary,
            "expected_no_write_density32": expected_no_write,
            "density4_control": density == 4,
        },
        "teacher_hits": {
            "b": branches["b"]["hits"] if instrumented else [],
            "h": branches["h"]["hits"] if instrumented else [],
        },
        "checkpoints": checkpoints,
    }
    if instrumented:
        result["trace"] = trace
    return result


def deterministic_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": case["seed"],
        "initial_density": case["initial_density"],
        "initial_snapshot_digest": case["initial_snapshot_digest"],
        "pre_teacher_snapshot_digest": case["pre_teacher_snapshot_digest"],
        "cohort": case["cohort"],
        "teacher_hits": case["teacher_hits"],
        "checkpoints": case["checkpoints"],
        "trace": case["trace"],
    }


def raw_digest_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": case["seed"],
        "initial_density": case["initial_density"],
        "initial_snapshot_digest": case["initial_snapshot_digest"],
        "pre_teacher_snapshot_digest": case["pre_teacher_snapshot_digest"],
        "branch_digests": {
            checkpoint: record["branch_digests"]
            for checkpoint, record in case["checkpoints"].items()
        },
    }


def run_case(
    *,
    seed: int,
    density: int,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
    checkpoint_generations: tuple[int, ...] = CHECKPOINT_GENERATIONS,
) -> dict[str, Any]:
    first = case_once(
        seed=seed,
        density=density,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
        checkpoint_generations=checkpoint_generations,
    )
    second = case_once(
        seed=seed,
        density=density,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
        checkpoint_generations=checkpoint_generations,
    )
    raw = case_once(
        seed=seed,
        density=density,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=False,
        checkpoint_generations=checkpoint_generations,
    )

    first_digest = canonical_digest(deterministic_projection(first))
    second_digest = canonical_digest(deterministic_projection(second))
    replay_match = first_digest == second_digest
    raw_match = raw_digest_projection(first) == raw_digest_projection(raw)
    if not replay_match:
        raise RuntimeError(
            f"non-deterministic #122 case density={density} seed={seed}"
        )
    if not raw_match:
        raise RuntimeError(
            f"instrumentation perturbs #122 state density={density} seed={seed}"
        )
    first["replay_digest"] = first_digest
    first["replay_match"] = True
    first["raw_instrumented_match"] = True
    return first


def _checkpoint_key(relative_generation: int) -> str:
    return "t0" if relative_generation == 0 else f"plus_{relative_generation}"


def build_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_density: dict[str, Any] = {}
    for density in DEFAULT_DENSITIES:
        density_cases = [
            case for case in cases if int(case["initial_density"]) == int(density)
        ]
        horizon_counts: dict[str, Any] = {}
        for generation in CHECKPOINT_GENERATIONS:
            key = _checkpoint_key(generation)
            diffs = [case["checkpoints"][key]["b_vs_h"] for case in density_cases]
            classes = Counter(
                case["checkpoints"][key]["classification"]["class"]
                for case in density_cases
            )
            horizon_counts[key] = {
                "b_h_different_case_count": sum(bool(diff["different"]) for diff in diffs),
                "classification_counts": dict(sorted(classes.items())),
            }
        by_density[str(density)] = {
            "case_count": len(density_cases),
            "horizons": horizon_counts,
            "duplicate_control_clean_case_count": sum(
                all(
                    not case["checkpoints"][_checkpoint_key(g)][
                        "control_vs_control_repeat"
                    ]["different"]
                    for g in CHECKPOINT_GENERATIONS
                )
                for case in density_cases
            ),
            "replay_match_count": sum(case["replay_match"] is True for case in density_cases),
            "raw_instrumented_match_count": sum(
                case["raw_instrumented_match"] is True for case in density_cases
            ),
        }

    primary = [
        case for case in cases if case["cohort"]["expected_primary_density32"]
    ]
    no_write = [
        case for case in cases if case["cohort"]["expected_no_write_density32"]
    ]
    t0_reconfirmed = [
        case for case in primary if case["checkpoints"]["t0"]["b_vs_h"]["different"]
    ]
    persistent_1000 = [
        case
        for case in primary
        if case["checkpoints"]["plus_1000"]["b_vs_h"]["different"]
    ]
    qualifying_recall = [
        case
        for case in persistent_1000
        if case["replay_match"] is True
        and case["raw_instrumented_match"] is True
        and all(
            not case["checkpoints"][_checkpoint_key(g)][
                "control_vs_control_repeat"
            ]["different"]
            for g in CHECKPOINT_GENERATIONS
        )
    ]
    no_write_clean = [
        case
        for case in no_write
        if all(
            not case["checkpoints"][_checkpoint_key(g)]["b_vs_h"]["different"]
            for g in CHECKPOINT_GENERATIONS
        )
    ]
    all_controls_clean = all(
        all(
            not case["checkpoints"][_checkpoint_key(g)][
                "control_vs_control_repeat"
            ]["different"]
            for g in CHECKPOINT_GENERATIONS
        )
        for case in cases
    )
    all_equivalent = all(
        case["replay_match"] is True and case["raw_instrumented_match"] is True
        for case in cases
    )
    cohort_reconfirmed = (
        len(t0_reconfirmed) == len(PRIMARY_DENSITY32_SEEDS)
        and len(primary) == len(PRIMARY_DENSITY32_SEEDS)
    )
    no_write_cohort_clean = len(no_write_clean) == len(NO_WRITE_DENSITY32_SEEDS)

    route_recall = (
        cohort_reconfirmed
        and no_write_cohort_clean
        and all_controls_clean
        and all_equivalent
        and bool(qualifying_recall)
    )

    primary_horizons: dict[str, Any] = {}
    for generation in CHECKPOINT_GENERATIONS:
        key = _checkpoint_key(generation)
        classification = Counter(
            case["checkpoints"][key]["classification"]["class"]
            for case in primary
        )
        primary_horizons[key] = {
            "different_count": sum(
                bool(case["checkpoints"][key]["b_vs_h"]["different"])
                for case in primary
            ),
            "classification_counts": dict(sorted(classification.items())),
            "different_seeds": [
                int(case["seed"])
                for case in primary
                if case["checkpoints"][key]["b_vs_h"]["different"]
            ],
        }

    return {
        "issue": 122,
        "base_main": BASE_MAIN,
        "learning_claim": False,
        "p6_10_plus": "frozen",
        "protocol": {
            "teacher_pair": [TEACHER_B, TEACHER_H],
            "post_t0_external_stimulus": False,
            "checkpoint_generations": list(CHECKPOINT_GENERATIONS),
            "primary_density32_seeds": list(PRIMARY_DENSITY32_SEEDS),
            "no_write_density32_seeds": list(NO_WRITE_DENSITY32_SEEDS),
            "densities": list(DEFAULT_DENSITIES),
            "seeds": list(DEFAULT_SEEDS),
        },
        "matrix": {
            "case_count": len(cases),
            "by_density": by_density,
        },
        "primary_density32": {
            "case_count": len(primary),
            "t0_reconfirmed_count": len(t0_reconfirmed),
            "t0_reconfirmed_seeds": [int(case["seed"]) for case in t0_reconfirmed],
            "horizons": primary_horizons,
            "plus_1000_persistent_count": len(persistent_1000),
            "plus_1000_persistent_seeds": [
                int(case["seed"]) for case in persistent_1000
            ],
            "first_non_hp_generation_by_seed": {
                str(case["seed"]): case["trace"]["first_non_hp_generation"]
                for case in primary
            },
            "first_spread_generation_by_seed": {
                str(case["seed"]): case["trace"]["first_spread_generation"]
                for case in primary
            },
            "first_passive_lifetime_generation_by_seed": {
                str(case["seed"]): case["trace"][
                    "first_passive_lifetime_generation"
                ]
                for case in primary
            },
            "first_reconvergence_generation_by_seed": {
                str(case["seed"]): case["trace"]["first_reconvergence_generation"]
                for case in primary
            },
            "last_different_generation_by_seed": {
                str(case["seed"]): case["trace"]["last_different_generation"]
                for case in primary
            },
        },
        "controls": {
            "primary_cohort_reconfirmed": cohort_reconfirmed,
            "no_write_density32_clean_count": len(no_write_clean),
            "no_write_density32_clean": no_write_cohort_clean,
            "duplicate_no_teacher_clean": all_controls_clean,
            "deterministic_and_raw_equivalent": all_equivalent,
        },
        "route_gate": {
            "required_plus_1000_persistent_primary_cases": 1,
            "observed_plus_1000_persistent_primary_cases": len(qualifying_recall),
            "qualifying_plus_1000_seeds": [
                int(case["seed"]) for case in qualifying_recall
            ],
            "route": "ROUTE-RECALL" if route_recall else "ROUTE-MEMORY-ARENA",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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
                f"#122 density={density} seed={seed} "
                f"t0={case['checkpoints']['t0']['b_vs_h']['different']} "
                f"+100={case['checkpoints']['plus_100']['b_vs_h']['different']} "
                f"+1000={case['checkpoints']['plus_1000']['b_vs_h']['different']}",
                file=sys.stderr,
                flush=True,
            )

    summary = build_summary(cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(case, sort_keys=True) + "\n" for case in cases),
        encoding="utf-8",
    )
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
