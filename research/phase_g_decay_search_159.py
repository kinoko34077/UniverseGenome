"""Phase G / #159 G1 matched decay-axis search.

This research-only runner evaluates the complete frozen trace_decay_rate domain
against the G0-qualified adaptive search cohort and adaptive negative sentinels.
It never advances the held-out cohort beyond h0 and does not unlock the
production SteadyStateOptimizer for non-legacy SearchPlans.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.experiment import ExperimentConfig, IOExperiment
from core.physics import PhysicsConfig, create_universe
from core.runner import load_config
from core.state import Lifecycle, UniverseState
from research.phase_g_memory_search_159 import (
    DECAY_DOMAIN,
    OLD_140_PRIMARY_SEEDS,
    REFERENCE_DECAY_RATE,
    build_phase_g_registry,
    phase_g_objective_profile,
    phase_g_protocol_payload,
    phase_g_search_plan,
    resolve_decay_candidate,
)
from research.slow_trace_persistence_140 import AUTHORITATIVE_FIELDS, snapshot_diff
from research.transduction_audit_120 import (
    TEACHER_B,
    TEACHER_H,
    advance_to_pre_teacher,
    canonical_digest,
    clone_state,
    teacher_step,
)

ISSUE = 159
G0_ARTIFACT = Path("research/artifacts/phase_g_g0_qualification_159.json")
G0_ARTIFACT_DIGEST = "ac8f9ab96c19d38e0553e13532a145207c8e00cba8014504aee2f08fbe598ca3"
G1_ROUTE_MIN_H1000 = 11
HORIZONS = (0, 100, 1000)


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _load_base_config(path: Path = Path("config/default.json")) -> PhysicsConfig:
    return PhysicsConfig.from_mapping(load_config(path))


def _load_protocol(
    path: Path = Path("config/experiment_v0_1.json"),
) -> ExperimentConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ExperimentConfig.from_mapping(payload)


def load_frozen_g0(path: Path = G0_ARTIFACT) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("artifact_digest") != G0_ARTIFACT_DIGEST:
        raise ValueError("unexpected G0 artifact digest")
    if payload.get("held_out_max_horizon") != 0:
        raise ValueError("G0 held-out boundary is not h0-only")
    if payload.get("search_plan_digest") != phase_g_search_plan().digest:
        raise ValueError("G0 SearchPlan digest drift")
    if payload.get("registry_digest") != build_phase_g_registry().digest:
        raise ValueError("G0 registry digest drift")
    objective = phase_g_objective_profile().to_dict()
    if payload.get("objective_profile_digest") != _digest(objective):
        raise ValueError("G0 ObjectiveProfile digest drift")
    protocol = phase_g_protocol_payload()
    if payload.get("protocol") != protocol:
        raise ValueError("G0 protocol payload drift")
    if payload.get("protocol_digest") != _digest(protocol):
        raise ValueError("G0 protocol digest drift")

    search = tuple(int(seed) for seed in payload["search_cohort"])
    sentinels = tuple(int(seed) for seed in payload["search_negative_sentinels"])
    heldout = tuple(int(seed) for seed in payload["heldout_validation_cohort"])
    heldout_sentinels = tuple(int(seed) for seed in payload["heldout_negative_sentinels"])
    if len(search) != 16 or len(sentinels) != 4:
        raise ValueError("unexpected frozen adaptive cohort size")
    if len(heldout) != 12 or len(heldout_sentinels) != 4:
        raise ValueError("unexpected frozen held-out cohort size")
    if set(search) & set(sentinels):
        raise ValueError("adaptive cohort overlaps adaptive sentinels")
    if (set(search) | set(sentinels)) & (set(heldout) | set(heldout_sentinels)):
        raise ValueError("adaptive and held-out cohorts overlap")
    if (set(search) | set(sentinels)) & set(OLD_140_PRIMARY_SEEDS):
        raise ValueError("adaptive evidence reuses frozen #140 primary seeds")
    return payload


def _checkpoint(states: Mapping[str, UniverseState]) -> dict[str, Any]:
    snapshots = {name: state.to_snapshot() for name, state in states.items()}
    b_vs_h = snapshot_diff(snapshots["b"], snapshots["h"])
    control_repeat = snapshot_diff(snapshots["control"], snapshots["control_repeat"])
    return {
        "branch_digests": {
            name: canonical_digest(snapshot) for name, snapshot in snapshots.items()
        },
        "b_vs_h_distinct": bool(b_vs_h["different"]),
        "b_vs_h_changed_slots": len(b_vs_h["changed_slots"]),
        "control_repeat_clean": not bool(control_repeat["different"]),
    }


def _checkpoint_from_snapshots(
    snapshots: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    b_vs_h = snapshot_diff(snapshots["b"], snapshots["h"])
    control_repeat = snapshot_diff(snapshots["control"], snapshots["control_repeat"])
    return {
        "branch_digests": {
            name: canonical_digest(snapshot) for name, snapshot in snapshots.items()
        },
        "b_vs_h_distinct": bool(b_vs_h["different"]),
        "b_vs_h_changed_slots": len(b_vs_h["changed_slots"]),
        "control_repeat_clean": not bool(control_repeat["different"]),
    }


def _original_trace_carriers(
    b_snapshot: Mapping[str, Any],
    h_snapshot: Mapping[str, Any],
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


def _raw_projection(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "seed": int(case["seed"]),
        "role": str(case["role"]),
        "decay_rate": int(case["decay_rate"]),
        "candidate_identity": str(case["candidate_identity"]),
        "initial_snapshot_digest": str(case["initial_snapshot_digest"]),
        "pre_teacher_snapshot_digest": str(case["pre_teacher_snapshot_digest"]),
        "checkpoint_branch_digests": {
            horizon: checkpoint["branch_digests"]
            for horizon, checkpoint in case["checkpoints"].items()
        },
    }


def _deterministic_projection(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **_raw_projection(case),
        "original_trace_carriers": case["original_trace_carriers"],
        "first_free_generation": case["first_free_generation"],
        "turnover_witness": bool(case["turnover_witness"]),
        "checkpoint_flags": {
            horizon: {
                "b_vs_h_distinct": bool(checkpoint["b_vs_h_distinct"]),
                "b_vs_h_changed_slots": int(checkpoint["b_vs_h_changed_slots"]),
                "control_repeat_clean": bool(checkpoint["control_repeat_clean"]),
            }
            for horizon, checkpoint in case["checkpoints"].items()
        },
    }


def case_once(
    *,
    decay_rate: int,
    seed: int,
    role: str,
    instrumented: bool,
    max_horizon: int = 1000,
    config_path: Path = Path("config/default.json"),
    experiment_path: Path = Path("config/experiment_v0_1.json"),
) -> dict[str, Any]:
    if decay_rate not in DECAY_DOMAIN:
        raise ValueError("decay_rate outside frozen G1 domain")
    if max_horizon not in (100, 1000):
        raise ValueError("G1 max_horizon must be 100 or 1000")

    base_config = _load_base_config(config_path)
    resolved = resolve_decay_candidate(decay_rate, base_config=base_config)
    config = resolved.universe_spec.to_physics_config(base_config)
    protocol = _load_protocol(experiment_path)

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
        name: branch["after_snapshot"] for name, branch in teacher_branches.items()
    }
    checkpoints: dict[str, Any] = {
        "0": _checkpoint_from_snapshots(h0_snapshots)
    }
    original_carriers = _original_trace_carriers(
        h0_snapshots["b"], h0_snapshots["h"]
    )

    states = {
        name: clone_state(snapshot, config) for name, snapshot in h0_snapshots.items()
    }
    experiments = {
        name: IOExperiment(state, experiment=protocol) for name, state in states.items()
    }
    first_free_generation: dict[str, dict[str, int | None]] = {
        branch: {str(slot): None for slot in slots}
        for branch, slots in original_carriers.items()
    }

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

        if generation in (100, 1000) and generation <= max_horizon:
            checkpoints[str(generation)] = _checkpoint(states)

    terminal = checkpoints[str(max_horizon)]
    original_union = set(original_carriers["b"]) | set(original_carriers["h"])
    terminal_snapshots = {
        name: state.to_snapshot() for name, state in states.items()
    }
    terminal_diff = snapshot_diff(
        terminal_snapshots["b"],
        terminal_snapshots["h"],
    )
    carrier_freed = any(
        generation is not None
        for values in first_free_generation.values()
        for generation in values.values()
    )
    changed_elsewhere = any(
        int(slot) not in original_union for slot in terminal_diff["changed_slots"]
    )
    turnover_witness = bool(
        instrumented
        and carrier_freed
        and terminal["b_vs_h_distinct"]
        and changed_elsewhere
    )

    return {
        "schema_version": 1,
        "issue": ISSUE,
        "seed": int(seed),
        "role": role,
        "decay_rate": int(decay_rate),
        "candidate_identity": resolved.candidate_identity,
        "max_horizon": int(max_horizon),
        "initial_snapshot_digest": canonical_digest(initial_snapshot),
        "pre_teacher_snapshot_digest": canonical_digest(pre_teacher),
        "checkpoints": checkpoints,
        "original_trace_carriers": original_carriers,
        "first_free_generation": (
            first_free_generation if instrumented else {"b": {}, "h": {}}
        ),
        "turnover_witness": turnover_witness,
    }


def run_case(
    *,
    decay_rate: int,
    seed: int,
    role: str,
    verify: bool,
    max_horizon: int = 1000,
) -> dict[str, Any]:
    first = case_once(
        decay_rate=decay_rate,
        seed=seed,
        role=role,
        instrumented=True,
        max_horizon=max_horizon,
    )
    first["replay_match"] = None
    first["raw_instrumented_match"] = None
    if not verify:
        return first

    second = case_once(
        decay_rate=decay_rate,
        seed=seed,
        role=role,
        instrumented=True,
        max_horizon=max_horizon,
    )
    raw = case_once(
        decay_rate=decay_rate,
        seed=seed,
        role=role,
        instrumented=False,
        max_horizon=max_horizon,
    )
    replay_match = _digest(_deterministic_projection(first)) == _digest(
        _deterministic_projection(second)
    )
    raw_match = _raw_projection(first) == _raw_projection(raw)
    first["replay_match"] = replay_match
    first["raw_instrumented_match"] = raw_match
    return first


def _case_flags(case: Mapping[str, Any]) -> dict[str, Any]:
    checkpoints = case["checkpoints"]
    return {
        "seed": int(case["seed"]),
        "h0_distinct": bool(checkpoints["0"]["b_vs_h_distinct"]),
        "h100_distinct": bool(checkpoints["100"]["b_vs_h_distinct"]),
        "h1000_distinct": bool(checkpoints["1000"]["b_vs_h_distinct"]),
        "turnover_witness": bool(case["turnover_witness"]),
        "replay_match": case.get("replay_match"),
        "raw_instrumented_match": case.get("raw_instrumented_match"),
        "control_repeat_clean": all(
            bool(checkpoint["control_repeat_clean"])
            for checkpoint in checkpoints.values()
        ),
        "branch_digest": _digest(
            {
                horizon: checkpoint["branch_digests"]
                for horizon, checkpoint in checkpoints.items()
            }
        ),
    }


def evaluate_candidate(decay_rate: int) -> dict[str, Any]:
    frozen = load_frozen_g0()
    search_seeds = tuple(int(seed) for seed in frozen["search_cohort"])
    negative_seeds = tuple(int(seed) for seed in frozen["search_negative_sentinels"])

    primary = [
        run_case(
            decay_rate=decay_rate,
            seed=seed,
            role="adaptive_search",
            verify=True,
            max_horizon=1000,
        )
        for seed in search_seeds
    ]
    negatives = [
        run_case(
            decay_rate=decay_rate,
            seed=seed,
            role="adaptive_negative_sentinel",
            verify=False,
            max_horizon=1000,
        )
        for seed in negative_seeds
    ]

    primary_flags = [_case_flags(case) for case in primary]
    negative_flags = [_case_flags(case) for case in negatives]
    replay_clean = all(flag["replay_match"] is True for flag in primary_flags)
    raw_clean = all(
        flag["raw_instrumented_match"] is True for flag in primary_flags
    )
    duplicate_controls_clean = all(
        flag["control_repeat_clean"]
        for flag in (*primary_flags, *negative_flags)
    )
    negative_sentinels_clean = all(
        not flag["h0_distinct"]
        and not flag["h100_distinct"]
        and not flag["h1000_distinct"]
        for flag in negative_flags
    )
    validity_clean = replay_clean and raw_clean and duplicate_controls_clean
    eligible = validity_clean and negative_sentinels_clean

    resolved = resolve_decay_candidate(decay_rate, base_config=_load_base_config())
    evidence = {
        "h1000_distinct_count": sum(
            flag["h1000_distinct"] for flag in primary_flags
        ),
        "h100_distinct_count": sum(
            flag["h100_distinct"] for flag in primary_flags
        ),
        "turnover_witness_count": sum(
            flag["turnover_witness"] for flag in primary_flags
        ),
    }
    record: dict[str, Any] = {
        "schema_version": 1,
        "issue": ISSUE,
        "phase": "G1",
        "learning_claim": False,
        "decay_rate": int(decay_rate),
        "candidate_identity": resolved.candidate_identity,
        "search_plan_digest": frozen["search_plan_digest"],
        "registry_digest": frozen["registry_digest"],
        "objective_profile_digest": frozen["objective_profile_digest"],
        "protocol_digest": frozen["protocol_digest"],
        "g0_artifact_digest": frozen["artifact_digest"],
        "search_cohort": list(search_seeds),
        "search_negative_sentinels": list(negative_seeds),
        "heldout_post_h0_executed": False,
        "evidence": evidence,
        "validity": {
            "replay_clean": replay_clean,
            "raw_instrumented_clean": raw_clean,
            "duplicate_controls_clean": duplicate_controls_clean,
            "negative_sentinels_clean": negative_sentinels_clean,
            "validity_clean": validity_clean,
            "eligible": eligible,
        },
        "search_cases": primary_flags,
        "negative_cases": negative_flags,
    }
    record["record_digest"] = _digest(record)
    return record


def _ranking_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    evidence = record["evidence"]
    return (
        -int(evidence["h1000_distinct_count"]),
        -int(evidence["h100_distinct_count"]),
        -int(evidence["turnover_witness_count"]),
        str(record["candidate_identity"]),
    )


def aggregate_candidates(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    material = sorted(
        (dict(record) for record in records),
        key=lambda record: int(record["decay_rate"]),
    )
    if tuple(int(record["decay_rate"]) for record in material) != DECAY_DOMAIN:
        raise ValueError("G1 aggregation requires every frozen decay candidate exactly once")

    frozen = load_frozen_g0()
    for record in material:
        if record.get("g0_artifact_digest") != frozen["artifact_digest"]:
            raise ValueError("candidate G0 artifact provenance mismatch")
        if record.get("search_plan_digest") != frozen["search_plan_digest"]:
            raise ValueError("candidate SearchPlan provenance mismatch")
        if record.get("registry_digest") != frozen["registry_digest"]:
            raise ValueError("candidate registry provenance mismatch")
        if record.get("objective_profile_digest") != frozen["objective_profile_digest"]:
            raise ValueError("candidate objective provenance mismatch")
        if record.get("protocol_digest") != frozen["protocol_digest"]:
            raise ValueError("candidate protocol provenance mismatch")
        if record.get("heldout_post_h0_executed") is not False:
            raise ValueError("G1 candidate accessed held-out post-h0 evidence")

    validity_clean = all(
        bool(record["validity"]["validity_clean"]) for record in material
    )
    reference = next(
        record for record in material if int(record["decay_rate"]) == REFERENCE_DECAY_RATE
    )
    eligible = [
        record for record in material if bool(record["validity"]["eligible"])
    ]

    if not validity_clean or not bool(reference["validity"]["eligible"]):
        route = "ROUTE-G1-FIX"
        best = None
    elif not eligible:
        route = "CHANGE_PATH"
        best = None
    else:
        best = min(eligible, key=_ranking_key)
        best_h1000 = int(best["evidence"]["h1000_distinct_count"])
        reference_h1000 = int(reference["evidence"]["h1000_distinct_count"])
        route = (
            "ROUTE-PHASE-H"
            if (
                best_h1000 >= G1_ROUTE_MIN_H1000
                and best_h1000 > reference_h1000
            )
            else "CHANGE_PATH"
        )

    result: dict[str, Any] = {
        "schema_version": 1,
        "issue": ISSUE,
        "phase": "G1",
        "learning_claim": False,
        "heldout_post_h0_executed": False,
        "g0_artifact_digest": frozen["artifact_digest"],
        "search_plan_digest": frozen["search_plan_digest"],
        "registry_digest": frozen["registry_digest"],
        "objective_profile_digest": frozen["objective_profile_digest"],
        "protocol_digest": frozen["protocol_digest"],
        "route_gate": {
            "minimum_h1000_distinct_count": G1_ROUTE_MIN_H1000,
            "must_strictly_beat_reference_decay_rate": REFERENCE_DECAY_RATE,
        },
        "reference": {
            "decay_rate": REFERENCE_DECAY_RATE,
            "candidate_identity": reference["candidate_identity"],
            "h1000_distinct_count": reference["evidence"]["h1000_distinct_count"],
            "eligible": reference["validity"]["eligible"],
        },
        "selected": (
            None
            if best is None
            else {
                "decay_rate": best["decay_rate"],
                "candidate_identity": best["candidate_identity"],
                "evidence": best["evidence"],
            }
        ),
        "terminal_route": route,
        "candidates": material,
    }
    result["artifact_digest"] = _digest(result)
    return result


def read_candidate_records(directory: Path) -> list[dict[str, Any]]:
    paths = sorted(directory.rglob("candidate-*.json"))
    records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=int)
    parser.add_argument("--aggregate-dir", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if (args.candidate is None) == (args.aggregate_dir is None):
        raise SystemExit("choose exactly one of --candidate or --aggregate-dir")

    if args.candidate is not None:
        if args.smoke:
            frozen = load_frozen_g0()
            seed = int(frozen["search_cohort"][0])
            payload = run_case(
                decay_rate=int(args.candidate),
                seed=seed,
                role="adaptive_search_smoke",
                verify=True,
                max_horizon=100,
            )
        else:
            payload = evaluate_candidate(int(args.candidate))
    else:
        payload = aggregate_candidates(read_candidate_records(args.aggregate_dir))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.aggregate_dir is not None:
        print(
            json.dumps(
                {
                    "artifact_digest": payload["artifact_digest"],
                    "selected": payload["selected"],
                    "terminal_route": payload["terminal_route"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
