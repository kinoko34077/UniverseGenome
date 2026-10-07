"""TEST-ST-012 L3 slow-trace persistence / turnover research for #140.

The active D1 profile and protocol were frozen on UniverseGenome#140 RP0 before
this harness was created or any #140 outcome was inspected. This module applies
the profile only through an in-memory PhysicsConfig override; production
defaults and the Phase 5 genome remain unchanged.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.experiment import ExperimentConfig, IOExperiment
from core.physics import PhysicsConfig, create_universe
from core.runner import load_config
from core.state import Lifecycle, UniverseState
from research.transduction_audit_120 import (
    TEACHER_B,
    TEACHER_H,
    advance_to_pre_teacher,
    build_physics_config,
    canonical_digest,
    clone_state,
    teacher_step,
)

BASE_MAIN = "cdbb04eaaedb3068d216e82bf257b475a20a31cb"
PROFILE_NAME = "D1_ACTIVE_32_8_16_256_5"
PROFILE = {
    "trace_write_cap": 32,
    "trace_transfer_cap": 8,
    "trace_discharge_cap": 16,
    "trace_decay_rate": 256,
    "trace_bonus_shift": 5,
}

PRIMARY_DENSITY32_SEEDS = (0, 5, 8, 9, 12, 14, 18, 19, 20, 22, 24, 29)
NEGATIVE_DENSITY32_SENTINELS = (1, 2, 3, 4)
HORIZONS = (0, 1, 10, 100, 1000)
REQUIRED_PRIMARY_PERSISTENT = 8
REQUIRED_TURNOVER_WITNESSES = 1

AUTHORITATIVE_FIELDS = (
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
    "slow_trace",
)


def build_active_config(base_config: dict[str, Any], density: int = 32) -> PhysicsConfig:
    """Return the frozen #140 active profile without mutating the input mapping."""
    base = build_physics_config(base_config, density)
    values = base.to_dict()
    values.update(PROFILE)
    return PhysicsConfig(**values)


def snapshot_diff(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    """Compare every authoritative cell array relevant to TEST-ST-012."""
    first_arrays = first["arrays"]
    second_arrays = second["arrays"]
    fields: dict[str, Any] = {}
    changed_union: set[int] = set()
    for name in AUTHORITATIVE_FIELDS:
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


def _branch_checkpoint(states: dict[str, UniverseState]) -> dict[str, Any]:
    snapshots = {name: state.to_snapshot() for name, state in states.items()}
    return _checkpoint_from_snapshots(snapshots)


def _checkpoint_from_snapshots(
    snapshots: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "branch_digests": {
            name: canonical_digest(snapshot)
            for name, snapshot in snapshots.items()
        },
        "comparisons": {
            "b_vs_h": snapshot_diff(snapshots["b"], snapshots["h"]),
            "b_vs_control": snapshot_diff(snapshots["b"], snapshots["control"]),
            "h_vs_control": snapshot_diff(snapshots["h"], snapshots["control"]),
            "control_vs_control_repeat": snapshot_diff(
                snapshots["control"], snapshots["control_repeat"]
            ),
        },
    }


def _original_trace_carriers(
    b_snapshot: dict[str, Any],
    h_snapshot: dict[str, Any],
) -> dict[str, list[int]]:
    b_trace = b_snapshot["arrays"]["slow_trace"]
    h_trace = h_snapshot["arrays"]["slow_trace"]
    changed = [
        slot
        for slot, (b_value, h_value) in enumerate(zip(b_trace, h_trace))
        if int(b_value) != int(h_value)
    ]
    return {
        "b": [slot for slot in changed if int(b_trace[slot]) > 0],
        "h": [slot for slot in changed if int(h_trace[slot]) > 0],
    }


def _raw_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": case["seed"],
        "role": case["role"],
        "profile": case["profile"],
        "initial_snapshot_digest": case["initial_snapshot_digest"],
        "pre_teacher_snapshot_digest": case["pre_teacher_snapshot_digest"],
        "checkpoint_branch_digests": {
            horizon: checkpoint["branch_digests"]
            for horizon, checkpoint in case["checkpoints"].items()
        },
    }


def _deterministic_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        **_raw_projection(case),
        "teacher_hits": case["teacher_hits"],
        "original_trace_carriers": case["original_trace_carriers"],
        "first_free_generation": case["first_free_generation"],
        "turnover_witness": case["turnover_witness"],
        "checkpoint_comparisons": {
            horizon: checkpoint["comparisons"]
            for horizon, checkpoint in case["checkpoints"].items()
        },
    }


def case_once(
    *,
    seed: int,
    role: str,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
    instrumented: bool,
    max_horizon: int = 1000,
) -> dict[str, Any]:
    if max_horizon not in HORIZONS[1:]:
        raise ValueError("max_horizon must be one of 1, 10, 100, 1000")

    config = build_active_config(config_payload, density=32)
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
        name: branch["after_snapshot"]
        for name, branch in teacher_branches.items()
    }
    checkpoints: dict[str, Any] = {
        "0": _checkpoint_from_snapshots(h0_snapshots)
    }
    original_carriers = _original_trace_carriers(
        h0_snapshots["b"], h0_snapshots["h"]
    )

    states = {
        name: clone_state(snapshot, config)
        for name, snapshot in h0_snapshots.items()
    }
    experiments = {
        name: IOExperiment(state, experiment=protocol)
        for name, state in states.items()
    }

    first_free_generation: dict[str, dict[str, int | None]] = {
        branch: {str(slot): None for slot in slots}
        for branch, slots in original_carriers.items()
    }

    declared_horizons = tuple(
        horizon for horizon in HORIZONS[1:] if horizon <= max_horizon
    )
    for generation in range(1, max_horizon + 1):
        for experiment in experiments.values():
            experiment._advance(())

        if instrumented:
            for branch in ("b", "h"):
                for slot in original_carriers[branch]:
                    key = str(slot)
                    if (
                        first_free_generation[branch][key] is None
                        and states[branch].lifecycle[slot] == Lifecycle.FREE
                    ):
                        first_free_generation[branch][key] = generation

        if generation in declared_horizons:
            checkpoints[str(generation)] = _branch_checkpoint(states)

    terminal = checkpoints[str(max_horizon)]["comparisons"]["b_vs_h"]
    original_union = set(original_carriers["b"]) | set(original_carriers["h"])
    carrier_freed = any(
        generation is not None
        for branch in first_free_generation.values()
        for generation in branch.values()
    )
    changed_elsewhere = any(
        int(slot) not in original_union for slot in terminal["changed_slots"]
    )
    turnover_witness = bool(
        instrumented
        and carrier_freed
        and terminal["different"]
        and changed_elsewhere
    )

    return {
        "status": "complete",
        "issue": 140,
        "base_main": BASE_MAIN,
        "profile_name": PROFILE_NAME,
        "profile": dict(PROFILE),
        "learning_claim": False,
        "density": 32,
        "seed": int(seed),
        "role": role,
        "max_horizon": int(max_horizon),
        "initial_snapshot_digest": canonical_digest(initial_snapshot),
        "pre_teacher_snapshot_digest": canonical_digest(pre_teacher),
        "teacher_hits": {
            "b": teacher_branches["b"]["hits"] if instrumented else [],
            "h": teacher_branches["h"]["hits"] if instrumented else [],
        },
        "original_trace_carriers": original_carriers,
        "first_free_generation": (
            first_free_generation if instrumented else {"b": {}, "h": {}}
        ),
        "checkpoints": checkpoints,
        "turnover_witness": turnover_witness,
    }


def run_case(
    *,
    seed: int,
    role: str,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
    verify: bool,
    max_horizon: int = 1000,
) -> dict[str, Any]:
    first = case_once(
        seed=seed,
        role=role,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
        max_horizon=max_horizon,
    )
    first["replay_match"] = None
    first["raw_instrumented_match"] = None
    if not verify:
        return first

    second = case_once(
        seed=seed,
        role=role,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
        max_horizon=max_horizon,
    )
    raw = case_once(
        seed=seed,
        role=role,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=False,
        max_horizon=max_horizon,
    )

    replay_match = canonical_digest(_deterministic_projection(first)) == canonical_digest(
        _deterministic_projection(second)
    )
    raw_match = _raw_projection(first) == _raw_projection(raw)
    first["replay_match"] = replay_match
    first["raw_instrumented_match"] = raw_match
    if not replay_match:
        raise RuntimeError(f"non-deterministic #140 case seed={seed}")
    if not raw_match:
        raise RuntimeError(f"instrumentation perturbs #140 case seed={seed}")
    return first


def case_plan() -> tuple[dict[str, Any], ...]:
    return tuple(
        [
            {
                "seed": seed,
                "role": "density32_primary",
                "verify": True,
            }
            for seed in PRIMARY_DENSITY32_SEEDS
        ]
        + [
            {
                "seed": seed,
                "role": "density32_negative_sentinel",
                "verify": False,
            }
            for seed in NEGATIVE_DENSITY32_SENTINELS
        ]
    )


def _checkpoint_diff(case: dict[str, Any], horizon: int) -> dict[str, Any]:
    return case["checkpoints"][str(horizon)]["comparisons"]["b_vs_h"]


def summarize(cases: Iterable[dict[str, Any]]) -> dict[str, Any]:
    material = list(cases)
    primary = [case for case in material if case["role"] == "density32_primary"]
    negatives = [
        case
        for case in material
        if case["role"] == "density32_negative_sentinel"
    ]
    if len(primary) != len(PRIMARY_DENSITY32_SEEDS):
        raise ValueError("full summary requires all 12 primary cases")
    if len(negatives) != len(NEGATIVE_DENSITY32_SENTINELS):
        raise ValueError("full summary requires all four negative sentinels")
    if any(case["max_horizon"] != 1000 for case in material):
        raise ValueError("full summary requires +1000 cases")

    h0 = [case for case in primary if _checkpoint_diff(case, 0)["different"]]
    h1000 = [case for case in primary if _checkpoint_diff(case, 1000)["different"]]
    negative_clean = all(
        not _checkpoint_diff(case, horizon)["different"]
        for case in negatives
        for horizon in HORIZONS
    )
    duplicate_control_clean = all(
        not case["checkpoints"][str(horizon)]["comparisons"][
            "control_vs_control_repeat"
        ]["different"]
        for case in material
        for horizon in HORIZONS
    )
    replay_clean = all(case["replay_match"] is True for case in primary)
    raw_clean = all(
        case["raw_instrumented_match"] is True for case in primary
    )
    turnover = [case for case in primary if case["turnover_witness"]]

    passed = (
        len(h0) == len(PRIMARY_DENSITY32_SEEDS)
        and len(h1000) >= REQUIRED_PRIMARY_PERSISTENT
        and negative_clean
        and duplicate_control_clean
        and replay_clean
        and raw_clean
        and len(turnover) >= REQUIRED_TURNOVER_WITNESSES
    )

    return {
        "status": "complete",
        "issue": 140,
        "base_main": BASE_MAIN,
        "learning_claim": False,
        "p6_10_plus": "frozen",
        "profile_name": PROFILE_NAME,
        "profile": dict(PROFILE),
        "protocol": {
            "density": 32,
            "teacher_pair": [TEACHER_B, TEACHER_H],
            "primary_seeds": list(PRIMARY_DENSITY32_SEEDS),
            "negative_sentinels": list(NEGATIVE_DENSITY32_SENTINELS),
            "horizons": list(HORIZONS),
            "required_primary_h1000": REQUIRED_PRIMARY_PERSISTENT,
            "required_turnover_witnesses": REQUIRED_TURNOVER_WITNESSES,
            "no_further_external_stimulation_after_h0": True,
        },
        "primary": {
            "h0_distinct_count": len(h0),
            "h0_distinct_seeds": [int(case["seed"]) for case in h0],
            "h1000_distinct_count": len(h1000),
            "h1000_distinct_seeds": [int(case["seed"]) for case in h1000],
            "turnover_witness_count": len(turnover),
            "turnover_witness_seeds": [int(case["seed"]) for case in turnover],
            "replay_clean": replay_clean,
            "raw_instrumented_clean": raw_clean,
        },
        "controls": {
            "negative_sentinels_clean": negative_clean,
            "duplicate_control_clean": duplicate_control_clean,
        },
        "semantic_shortcut_boundary": {
            "production_test_st_011_basis": "#135 PASS",
            "harness_direct_trace_mutation": False,
            "teacher_semantics_enter_production_trace_rule": False,
        },
        "terminal_gate": {
            "passed": passed,
            "route": (
                "PASS-L3-PERSISTENCE-CAPABLE"
                if passed
                else "FAIL-L3-PERSISTENCE"
            ),
        },
    }


def append_case(path: Path, case: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(case, sort_keys=True) + "\n")


def read_completed(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    if not path.exists():
        return {}
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        key = (str(case["role"]), int(case["seed"]))
        result[key] = case
    return result


def parse_args() -> argparse.Namespace:
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
        default=Path("research/artifacts/slow_trace_persistence_140.jsonl"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("research/artifacts/slow_trace_persistence_140_summary.json"),
    )
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_payload = load_config(args.config)
    experiment_payload = json.loads(args.experiment.read_text(encoding="utf-8"))

    if args.smoke:
        case = run_case(
            seed=PRIMARY_DENSITY32_SEEDS[0],
            role="density32_primary",
            config_payload=config_payload,
            experiment_payload=experiment_payload,
            verify=True,
            max_horizon=10,
        )
        print(json.dumps(case, indent=2, sort_keys=True))
        return 0

    completed = read_completed(args.output)
    for spec in case_plan():
        key = (str(spec["role"]), int(spec["seed"]))
        if key in completed:
            print(f"#140 skip completed {key}", file=sys.stderr, flush=True)
            continue
        case = run_case(
            seed=int(spec["seed"]),
            role=str(spec["role"]),
            config_payload=config_payload,
            experiment_payload=experiment_payload,
            verify=bool(spec["verify"]),
            max_horizon=1000,
        )
        append_case(args.output, case)
        completed[key] = case
        print(
            f"#140 complete role={case['role']} seed={case['seed']} "
            f"h0={_checkpoint_diff(case, 0)['different']} "
            f"h1000={_checkpoint_diff(case, 1000)['different']} "
            f"turnover={case['turnover_witness']}",
            file=sys.stderr,
            flush=True,
        )

    required = {
        (str(spec["role"]), int(spec["seed"]))
        for spec in case_plan()
    }
    missing = sorted(required.difference(completed))
    if missing:
        print(json.dumps({"status": "partial", "missing": missing}, indent=2))
        return 2

    ordered = [
        completed[(str(spec["role"]), int(spec["seed"]))]
        for spec in case_plan()
    ]
    summary = summarize(ordered)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
