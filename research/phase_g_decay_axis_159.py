"""Phase G / #159 G1: frozen trace-decay-axis long-horizon research.

This module is deliberately research-only. It resolves exactly the frozen
SearchPlan candidates and evaluates ONLY G0's adaptive search/sentinel seeds.
The held-out seeds have no post-h0 execution route in this module.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.experiment import IOExperiment
from core.physics import create_universe
from core.state import Lifecycle
from research.phase_g_memory_search_159 import (
    DECAY_DOMAIN,
    HELDOUT_POOL,
    OLD_140_PRIMARY_SEEDS,
    _digest,
    _load_base_config,
    _load_protocol,
    build_phase_g_registry,
    phase_g_objective_profile,
    phase_g_search_plan,
    resolve_decay_candidate,
)
from research.slow_trace_persistence_140 import (
    _checkpoint_from_snapshots,
    _deterministic_projection,
    _original_trace_carriers,
    _raw_projection,
    snapshot_diff,
)
from research.transduction_audit_120 import (
    TEACHER_B,
    TEACHER_H,
    advance_to_pre_teacher,
    canonical_digest,
    clone_state,
    teacher_step,
)

ISSUE = 159
FROZEN_G0_PATH = Path("research/artifacts/phase_g_g0_qualification_159.json")
FROZEN_G0_DIGEST = "ac8f9ab96c19d38e0553e13532a145207c8e00cba8014504aee2f08fbe598ca3"
FROZEN_PROTOCOL_DIGEST = "5a7d813b2ae55028a2a27ffd26bd0b42ffd06007f01b35abd7e16b367fe92a33"
HORIZONS = (0, 1, 10, 100, 1000)
REFERENCE_RATE = 256


def load_frozen_contract(path: Path = FROZEN_G0_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    without_digest = {key: val for key, val in payload.items() if key != "artifact_digest"}
    if payload.get("artifact_digest") != FROZEN_G0_DIGEST:
        raise ValueError("G0 qualification artifact digest differs from accepted freeze")
    if _digest(without_digest) != FROZEN_G0_DIGEST:
        raise ValueError("G0 qualification payload failed digest verification")
    if payload["protocol_digest"] != FROZEN_PROTOCOL_DIGEST:
        raise ValueError("G0 protocol provenance differs from accepted freeze")
    if payload.get("held_out_max_horizon") != 0:
        raise ValueError("G0 held-out boundary was violated")
    if payload["protocol"]["teacher_pair"] != [TEACHER_B, TEACHER_H]:
        raise ValueError("teacher pair differs from G0")
    if payload["protocol"]["adaptive_horizons"] != [100, 1000]:
        raise ValueError("long-horizon boundaries differ from G0")
    if not payload["protocol"]["no_further_external_stimulation_after_h0"]:
        raise ValueError("post-h0 stimulation is forbidden")
    if payload["search_plan_digest"] != phase_g_search_plan().digest:
        raise ValueError("SearchPlan differs from accepted G0")
    if payload["registry_digest"] != build_phase_g_registry().digest:
        raise ValueError("SearchRegistry differs from accepted G0")
    if payload["objective_profile_digest"] != _digest(phase_g_objective_profile().to_dict()):
        raise ValueError("ObjectiveProfile differs from accepted G0")
    positives = payload["search_cohort"]
    sentinels = payload["search_negative_sentinels"]
    if len(positives) != 16 or len(sentinels) != 4:
        raise ValueError("G1 expected 16 search seeds and 4 search sentinels")
    if (set(positives) & set(sentinels) or
        (set(positives) | set(sentinels)) & set(HELDOUT_POOL) or
        (set(positives) | set(sentinels)) & set(OLD_140_PRIMARY_SEEDS)):
        raise ValueError("search/sentinel sets overlap held-out or historical seeds")
    return payload


def _authorized_role(seed: int, role: str, frozen: dict[str, Any]) -> None:
    if role == "search" and seed in frozen["search_cohort"]:
        return
    if role == "sentinel" and seed in frozen["search_negative_sentinels"]:
        return
    raise ValueError(f"seed={seed} role={role} not in frozen adaptive-search evidence")


def case_once(
    *, seed: int, role: str, decay_rate: int, frozen: dict[str, Any],
    instrumented: bool, max_horizon: int = 1000,
) -> dict[str, Any]:
    _authorized_role(seed, role, frozen)
    if decay_rate not in DECAY_DOMAIN:
        raise ValueError("decay candidate outside frozen domain")
    if max_horizon not in HORIZONS[1:]:
        raise ValueError("only frozen observation horizons are allowed")

    base = _load_base_config()
    resolved = resolve_decay_candidate(decay_rate, base_config=base)
    config = resolved.universe_spec.to_physics_config(base)
    protocol = _load_protocol()
    initial = create_universe(seed=seed, config=config).to_snapshot()
    pre_teacher = advance_to_pre_teacher(
        initial, config=config, protocol=protocol, instrumented=False,
    )["a_pre_teacher"]

    teacher_branches = {
        name: teacher_step(
            pre_teacher, config=config, protocol=protocol,
            teacher_value=teacher_value, instrumented=instrumented,
        )
        for name, teacher_value in (
            ("control", None), ("control_repeat", None),
            ("b", TEACHER_B), ("h", TEACHER_H),
        )
    }
    h0 = {name: branch["after_snapshot"] for name, branch in teacher_branches.items()}
    checkpoints = {"0": _checkpoint_from_snapshots(h0)}
    carriers = _original_trace_carriers(h0["b"], h0["h"])
    states = {name: clone_state(snapshot, config) for name, snapshot in h0.items()}
    experiments = {name: IOExperiment(state, experiment=protocol) for name, state in states.items()}
    first_free = {
        name: {str(slot): None for slot in slots}
        for name, slots in carriers.items()
    }

    for generation in range(1, max_horizon + 1):
        for experiment in experiments.values():
            experiment._advance(())
        if instrumented:
            for name in ("b", "h"):
                for slot in carriers[name]:
                    key = str(slot)
                    if first_free[name][key] is None and states[name].lifecycle[slot] == Lifecycle.FREE:
                        first_free[name][key] = generation
        if generation in HORIZONS[1:]:
            checkpoints[str(generation)] = _checkpoint_from_snapshots({
                name: state.to_snapshot() for name, state in states.items()
            })

    terminal = checkpoints[str(max_horizon)]["comparisons"]["b_vs_h"]
    original_slots = set(carriers["b"]) | set(carriers["h"])
    turnover_witness = bool(
        instrumented
        and any(g is not None for items in first_free.values() for g in items.values())
        and terminal["different"]
        and any(slot not in original_slots for slot in terminal["changed_slots"])
    )
    return {
        "seed": seed,
        "role": role,
        "profile": {
            "trace_write_cap": 32,
            "trace_transfer_cap": 8,
            "trace_discharge_cap": 16,
            "trace_decay_rate": decay_rate,
            "trace_bonus_shift": 5,
        },
        "candidate_identity": resolved.candidate_identity,
        "initial_snapshot_digest": canonical_digest(initial),
        "pre_teacher_snapshot_digest": canonical_digest(pre_teacher),
        "teacher_hits": {
            "b": teacher_branches["b"]["hits"] if instrumented else [],
            "h": teacher_branches["h"]["hits"] if instrumented else [],
        },
        "original_trace_carriers": carriers,
        "first_free_generation": first_free if instrumented else {"b": {}, "h": {}},
        "checkpoints": checkpoints,
        "turnover_witness": turnover_witness,
    }


def evaluate_case(
    *, seed: int, role: str, decay_rate: int, frozen: dict[str, Any],
    verify: bool = True, max_horizon: int = 1000,
) -> dict[str, Any]:
    first = case_once(
        seed=seed, role=role, decay_rate=decay_rate, frozen=frozen,
        instrumented=True, max_horizon=max_horizon,
    )
    replay_clean: bool | None = None
    raw_clean: bool | None = None
    if verify:
        second = case_once(
            seed=seed, role=role, decay_rate=decay_rate, frozen=frozen,
            instrumented=True, max_horizon=max_horizon,
        )
        raw = case_once(
            seed=seed, role=role, decay_rate=decay_rate, frozen=frozen,
            instrumented=False, max_horizon=max_horizon,
        )
        replay_clean = (
            canonical_digest(_deterministic_projection(first))
            == canonical_digest(_deterministic_projection(second))
        )
        raw_clean = _raw_projection(first) == _raw_projection(raw)

    checkpoint_counts = {
        key: {
            "b_vs_h_distinct": bool(val["comparisons"]["b_vs_h"]["different"]),
            "control_clean": not bool(
                val["comparisons"]["control_vs_control_repeat"]["different"]
            ),
            "branch_digests": val["branch_digests"],
        }
        for key, val in first["checkpoints"].items()
    }
    result = {
        "seed": seed,
        "role": role,
        "decay_rate": decay_rate,
        "candidate_identity": first["candidate_identity"],
        "checkpoints": checkpoint_counts,
        "turnover_witness": first["turnover_witness"],
        "replay_clean": replay_clean,
        "raw_instrumented_clean": raw_clean,
        "case_digest": canonical_digest(_deterministic_projection(first)),
    }
    return result


def run_candidate(
    rate: int, *, max_horizon: int = 1000,
    frozen: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frozen = frozen or load_frozen_contract()
    if rate not in DECAY_DOMAIN:
        raise ValueError("candidate outside frozen domain")
    search = [
        evaluate_case(seed=seed, role="search", decay_rate=rate, frozen=frozen,
                      verify=True, max_horizon=max_horizon)
        for seed in frozen["search_cohort"]
    ]
    sentinels = [
        evaluate_case(seed=seed, role="sentinel", decay_rate=rate, frozen=frozen,
                      verify=False, max_horizon=max_horizon)
        for seed in frozen["search_negative_sentinels"]
    ]
    observed_horizons = tuple(h for h in HORIZONS if h <= max_horizon)
    ctrl_clean = all(
        case["checkpoints"][str(h)]["control_clean"]
        for case in search + sentinels for h in observed_horizons
    )
    negative_clean = all(
        not case["checkpoints"][str(h)]["b_vs_h_distinct"]
        for case in sentinels for h in observed_horizons
    )
    replay_clean = all(case["replay_clean"] is True for case in search)
    raw_clean = all(case["raw_instrumented_clean"] is True for case in search)
    valid = ctrl_clean and negative_clean and replay_clean and raw_clean
    scores = {
        "h1000_distinct_count": sum(case["checkpoints"].get("1000", {}).get("b_vs_h_distinct", False) for case in search),
        "h100_distinct_count": sum(case["checkpoints"].get("100", {}).get("b_vs_h_distinct", False) for case in search),
        "turnover_witness_count": sum(case["turnover_witness"] for case in search),
    }
    result = {
        "schema_version": 1,
        "issue": ISSUE,
        "phase": "G1",
        "horizon": max_horizon,
        "decay_rate": rate,
        "candidate_identity": search[0]["candidate_identity"],
        "g0_artifact_digest": FROZEN_G0_DIGEST,
        "protocol_digest": FROZEN_PROTOCOL_DIGEST,
        "search_plan_digest": frozen["search_plan_digest"],
        "search_seeds": list(frozen["search_cohort"]),
        "sentinel_seeds": list(frozen["search_negative_sentinels"]),
        "heldout_max_horizon": 0,
        "validity": {
            "duplicate_control_clean": ctrl_clean,
            "negative_sentinels_clean": negative_clean,
            "replay_clean": replay_clean,
            "raw_instrumented_clean": raw_clean,
        },
        "valid": valid,
        "scores": scores,
        "cases": search + sentinels,
    }
    result["artifact_digest"] = _digest(result)
    return result


def aggregate_candidates(files: list[Path]) -> dict[str, Any]:
    frozen = load_frozen_contract()
    results = [json.loads(file.read_text(encoding="utf-8")) for file in files]
    if sorted(r["decay_rate"] for r in results) != sorted(DECAY_DOMAIN):
        raise ValueError("G1 requires exactly the frozen 12 candidate rates")
    for result in results:
        d = result.pop("artifact_digest", None)
        if d != _digest(result):
            raise ValueError("tampered G1 candidate artifact")
        result["artifact_digest"] = d
        if result["horizon"] != 1000 or result["heldout_max_horizon"] != 0:
            raise ValueError("incomplete or held-out-contaminated G1 result")
        if result["g0_artifact_digest"] != FROZEN_G0_DIGEST:
            raise ValueError("G1 result used a different cohort freeze")
        if result["protocol_digest"] != FROZEN_PROTOCOL_DIGEST:
            raise ValueError("G1 result used a different protocol")
        if result["search_plan_digest"] != frozen["search_plan_digest"]:
            raise ValueError("G1 result used a different SearchPlan")
        if result["search_seeds"] != frozen["search_cohort"] or result["sentinel_seeds"] != frozen["search_negative_sentinels"]:
            raise ValueError("G1 result used mismatched evidence")
        if len(result["cases"]) != 20 or sorted(c["seed"] for c in result["cases"]) != sorted(result["search_seeds"] + result["sentinel_seeds"]):
            raise ValueError("G1 case coverage incomplete")
        if result["candidate_identity"] != resolve_decay_candidate(result["decay_rate"]).candidate_identity:
            raise ValueError("G1 candidate identity mismatch")

    valid = [r for r in results if r["valid"]]
    reference = next(r for r in results if r["decay_rate"] == REFERENCE_RATE)
    ranking = sorted(
        valid,
        key=lambda r: (
            -r["scores"]["h1000_distinct_count"],
            -r["scores"]["h100_distinct_count"],
            -r["scores"]["turnover_witness_count"],
            r["candidate_identity"],
        ),
    )
    if not reference["valid"] or not ranking:
        route = "ROUTE-G1-FIX"
        selected = None
    else:
        selected = ranking[0]
        route = (
            "ROUTE-PHASE-H"
            if selected["scores"]["h1000_distinct_count"] > reference["scores"]["h1000_distinct_count"]
            else "CHANGE_PATH"
        )
    summary = {
        "schema_version": 1,
        "issue": ISSUE,
        "phase": "G1",
        "g0_artifact_digest": FROZEN_G0_DIGEST,
        "protocol_digest": FROZEN_PROTOCOL_DIGEST,
        "search_plan_digest": frozen["search_plan_digest"],
        "reference_rate": REFERENCE_RATE,
        "reference_h1000_distinct_count": reference["scores"]["h1000_distinct_count"],
        "candidate_results": [
            {
                "rate": r["decay_rate"],
                "identity": r["candidate_identity"],
                "valid": r["valid"],
                "validity": r["validity"],
                "scores": r["scores"],
                "artifact_digest": r["artifact_digest"],
            }
            for r in sorted(results, key=lambda x: x["decay_rate"])
        ],
        "ranking": [r["decay_rate"] for r in ranking],
        "selected_rate": selected["decay_rate"] if selected else None,
        "selected_identity": selected["candidate_identity"] if selected else None,
        "terminal_route": route,
        "heldout_max_horizon": 0,
        "learning_claim": False,
    }
    summary["artifact_digest"] = _digest(summary)
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--rate", type=int)
    group.add_argument("--aggregate-dir", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.rate is not None:
        result = run_candidate(args.rate)
    else:
        files = sorted(args.aggregate_dir.glob("candidate-*.json"))
        result = aggregate_candidates(files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.rate is None:
        print(json.dumps({
            "selected_rate": result["selected_rate"],
            "terminal_route": result["terminal_route"],
            "candidate_results": result["candidate_results"],
            "artifact_digest": result["artifact_digest"],
        }, indent=2, sort_keys=True))
    else:
        print(json.dumps({
            "rate": result["decay_rate"],
            "valid": result["valid"],
            "scores": result["scores"],
            "artifact_digest": result["artifact_digest"],
        }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
