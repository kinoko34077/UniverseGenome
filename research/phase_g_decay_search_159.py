"""Phase G #159 G1: frozen decay-axis research-only long-horizon evaluator.

Uses the accepted #140 observation semantics over resolved G0 SearchPlan physics.
No production optimizer change and no held-out post-h0 code path.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.experiment import IOExperiment
from core.physics import create_universe
from core.state import Lifecycle
from research import slow_trace_persistence_140 as oracle
from research import phase_g_memory_search_159 as g0
from research.transduction_audit_120 import (
    TEACHER_B, TEACHER_H, advance_to_pre_teacher, canonical_digest,
    clone_state, teacher_step,
)

FROZEN_PATH = Path("research/artifacts/phase_g_g0_qualification_159.json")
HORIZONS = (0, 1, 10, 100, 1000)
PHASE_G_ROUTE_THRESHOLD = 11
EXPECTED_CASE_COUNT = 20


def frozen_contract() -> dict[str, Any]:
    frozen = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
    advertised = frozen["artifact_digest"]
    actual = g0._digest({k: v for k, v in frozen.items() if k != "artifact_digest"})
    if actual != advertised:
        raise RuntimeError("G0 frozen artifact digest mismatch")
    if advertised != "ac8f9ab96c19d38e0553e13532a145207c8e00cba8014504aee2f08fbe598ca3":
        raise RuntimeError("G0 frozen artifact identity changed")
    if frozen["search_plan_digest"] != g0.phase_g_search_plan().digest:
        raise RuntimeError("G0 SearchPlan drift")
    if frozen["registry_digest"] != g0.build_phase_g_registry().digest:
        raise RuntimeError("G0 registry drift")
    if frozen["objective_profile_digest"] != g0._digest(g0.phase_g_objective_profile().to_dict()):
        raise RuntimeError("G0 objective drift")
    if frozen["protocol"] != g0._protocol_payload():
        raise RuntimeError("G0 protocol drift")
    if frozen["protocol_digest"] != g0._digest(frozen["protocol"]):
        raise RuntimeError("G0 protocol digest mismatch")
    if frozen["protocol"]["teacher_pair"] != [TEACHER_B, TEACHER_H]:
        raise RuntimeError("unexpected teacher pair")
    if frozen["protocol"]["adaptive_horizons"] != [100, 1000]:
        raise RuntimeError("unexpected adaptive horizons")
    if frozen["held_out_max_horizon"] != 0:
        raise RuntimeError("held-out horizon must stay h0-only")
    if len(frozen["search_cohort"]) != 16 or len(frozen["search_negative_sentinels"]) != 4:
        raise RuntimeError("unexpected adaptive evidence allocation")
    if not set(frozen["search_cohort"]).isdisjoint(frozen["heldout_validation_cohort"]):
        raise RuntimeError("search and held-out cohorts overlap")
    if set(frozen["search_cohort"]) | set(frozen["search_negative_sentinels"]) != set(
        [32, 36, 37, 40, 42, 45, 46, 47, 49, 50, 53, 54, 55, 62, 65, 67, 33, 34, 35, 38]
    ):
        raise RuntimeError("adaptive cohort changed")
    return frozen


def allowed_case(seed: int, role: str, frozen: dict[str, Any]) -> None:
    expected = (
        frozen["search_cohort"] if role == "adaptive_search"
        else frozen["search_negative_sentinels"] if role == "negative_sentinel"
        else ()
    )
    if int(seed) not in expected:
        raise ValueError("G1 rejects non-adaptive or held-out seed/role")


def case_once(
    *, seed: int, role: str, decay_rate: int, instrumented: bool,
    max_horizon: int = 1000,
    frozen: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Match #140 B/H/duplicate-control horizon and turnover observations."""
    f = frozen if frozen is not None else frozen_contract()
    allowed_case(seed, role, f)
    if decay_rate not in g0.DECAY_DOMAIN:
        raise ValueError("decay rate outside predeclared domain")
    if max_horizon not in HORIZONS[1:]:
        raise ValueError("undeclared test horizon")
    base = g0._load_base_config()
    resolved = g0.resolve_decay_candidate(decay_rate, base_config=base)
    config = resolved.universe_spec.to_physics_config(base)
    protocol = g0._load_protocol()
    if protocol.to_dict() != f["protocol"]["experiment"]:
        raise RuntimeError("protocol configuration drift")

    initial_snapshot = create_universe(seed=seed, config=config).to_snapshot()
    prepared = advance_to_pre_teacher(
        initial_snapshot, config=config, protocol=protocol, instrumented=False
    )
    pre_teacher = prepared["a_pre_teacher"]
    teacher_branches = {
        branch: teacher_step(
            pre_teacher, config=config, protocol=protocol,
            teacher_value=value, instrumented=instrumented
        )
        for branch, value in (
            ("control", None), ("control_repeat", None),
            ("b", TEACHER_B), ("h", TEACHER_H)
        )
    }
    snapshots = {branch: result["after_snapshot"] for branch, result in teacher_branches.items()}
    checkpoints = {"0": oracle._checkpoint_from_snapshots(snapshots)}
    original_carriers = oracle._original_trace_carriers(snapshots["b"], snapshots["h"])
    states = {branch: clone_state(snapshot, config) for branch, snapshot in snapshots.items()}
    experiments = {branch: IOExperiment(state, experiment=protocol) for branch, state in states.items()}
    freed = {
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
                    if freed[branch][key] is None and states[branch].lifecycle[slot] == Lifecycle.FREE:
                        freed[branch][key] = generation
        if generation in HORIZONS:
            checkpoints[str(generation)] = oracle._branch_checkpoint(states)

    terminal = checkpoints[str(max_horizon)]["comparisons"]["b_vs_h"]
    original_union = set(original_carriers["b"]) | set(original_carriers["h"])
    turnover = bool(
        instrumented
        and any(t is not None for branch in freed.values() for t in branch.values())
        and terminal["different"]
        and any(int(slot) not in original_union for slot in terminal["changed_slots"])
    )
    return {
        "status": "complete",
        "issue": 159,
        "base_main": g0.BASELINE_SHA,
        "profile": {"trace_write_cap": 32, "trace_transfer_cap": 8,
                    "trace_discharge_cap": 16, "trace_decay_rate": decay_rate,
                    "trace_bonus_shift": 5},
        "profile_name": "phase_g_decay_axis_v1",
        "learning_claim": False,
        "density": 32,
        "seed": int(seed),
        "role": role,
        "max_horizon": int(max_horizon),
        "candidate_identity": resolved.candidate_identity,
        "initial_snapshot_digest": canonical_digest(initial_snapshot),
        "pre_teacher_snapshot_digest": canonical_digest(pre_teacher),
        "teacher_hits": {
            "b": teacher_branches["b"]["hits"] if instrumented else [],
            "h": teacher_branches["h"]["hits"] if instrumented else [],
        },
        "original_trace_carriers": original_carriers,
        "first_free_generation": freed if instrumented else {"b": {}, "h": {}},
        "checkpoints": checkpoints,
        "turnover_witness": turnover,
    }


def verify_case(*, seed: int, role: str, decay_rate: int, frozen: dict[str, Any]) -> dict[str, Any]:
    first = case_once(seed=seed, role=role, decay_rate=decay_rate,
                      instrumented=True, frozen=frozen)
    replay_match: bool | None = None
    raw_match: bool | None = None
    if role == "adaptive_search":
        replay = case_once(seed=seed, role=role, decay_rate=decay_rate,
                           instrumented=True, frozen=frozen)
        raw = case_once(seed=seed, role=role, decay_rate=decay_rate,
                        instrumented=False, frozen=frozen)
        replay_match = (
            canonical_digest(oracle._deterministic_projection(first))
            == canonical_digest(oracle._deterministic_projection(replay))
        )
        raw_match = oracle._raw_projection(first) == oracle._raw_projection(raw)
    comparisons = first["checkpoints"]
    distinct = {
        horizon: bool(comparisons[str(horizon)]["comparisons"]["b_vs_h"]["different"])
        for horizon in HORIZONS
    }
    controls_clean = all(
        not bool(comparisons[str(horizon)]["comparisons"]["control_vs_control_repeat"]["different"])
        for horizon in HORIZONS
    )
    return {
        "seed": seed, "role": role,
        "candidate_identity": first["candidate_identity"],
        "distinct": {str(horizon): value for horizon, value in distinct.items()},
        "turnover_witness": bool(first["turnover_witness"]),
        "duplicate_control_clean": controls_clean,
        "replay_match": replay_match,
        "raw_instrumented_match": raw_match,
        "branch_digest_by_horizon": {
            str(horizon): comparisons[str(horizon)]["branch_digests"] for horizon in HORIZONS
        },
        "evidence_digest": g0._digest(oracle._deterministic_projection(first)),
    }


def assess_candidate(cases: list[dict[str, Any]], frozen: dict[str, Any]) -> dict[str, Any]:
    searches = [c for c in cases if c["role"] == "adaptive_search"]
    negatives = [c for c in cases if c["role"] == "negative_sentinel"]
    if [c["seed"] for c in searches] != frozen["search_cohort"]:
        raise RuntimeError("adaptive cases do not match frozen order")
    if [c["seed"] for c in negatives] != frozen["search_negative_sentinels"]:
        raise RuntimeError("negative cases do not match frozen order")
    replay_clean = all(c["replay_match"] is True for c in searches)
    raw_clean = all(c["raw_instrumented_match"] is True for c in searches)
    duplicates_clean = all(c["duplicate_control_clean"] for c in cases)
    negative_clean = all(
        not c["distinct"][str(h)] for c in negatives for h in HORIZONS
    )
    return {
        "valid": bool(replay_clean and raw_clean and duplicates_clean and negative_clean),
        "replay_clean": replay_clean,
        "raw_instrumented_clean": raw_clean,
        "duplicate_controls_clean": duplicates_clean,
        "negative_sentinels_clean": negative_clean,
        "h0_distinct_count": sum(c["distinct"]["0"] for c in searches),
        "h100_distinct_count": sum(c["distinct"]["100"] for c in searches),
        "h1000_distinct_count": sum(c["distinct"]["1000"] for c in searches),
        "turnover_witness_count": sum(c["turnover_witness"] for c in searches),
    }


def run_candidate(decay_rate: int) -> dict[str, Any]:
    frozen = frozen_contract()
    if decay_rate not in g0.DECAY_DOMAIN:
        raise ValueError("candidate outside frozen decay domain")
    candidate = g0.resolve_decay_candidate(decay_rate)
    cases = [
        verify_case(seed=seed, role="adaptive_search",
                    decay_rate=decay_rate, frozen=frozen)
        for seed in frozen["search_cohort"]
    ] + [
        verify_case(seed=seed, role="negative_sentinel",
                    decay_rate=decay_rate, frozen=frozen)
        for seed in frozen["search_negative_sentinels"]
    ]
    if len(cases) != EXPECTED_CASE_COUNT:
        raise RuntimeError("invalid matched evidence count")
    record = {
        "schema_version": 1, "issue": 159, "phase": "G1",
        "scope": "adaptive_search_only", "learning_claim": False,
        "decay_rate": int(decay_rate),
        "candidate_identity": candidate.candidate_identity,
        "G0_artifact_digest": frozen["artifact_digest"],
        "search_plan_digest": frozen["search_plan_digest"],
        "registry_digest": frozen["registry_digest"],
        "objective_profile_digest": frozen["objective_profile_digest"],
        "protocol_digest": frozen["protocol_digest"],
        "held_out_max_horizon": 0,
        "cases": cases, "summary": assess_candidate(cases, frozen),
    }
    record["result_digest"] = g0._digest(record)
    return record


def aggregate(directory: Path) -> dict[str, Any]:
    """Admit the exact frozen 12-candidate evidence, then route by frozen criteria."""
    frozen = frozen_contract()
    paths = sorted(directory.glob("candidate-*.json"))
    if len(paths) != len(g0.DECAY_DOMAIN):
        raise RuntimeError("incomplete or duplicate G1 candidate evidence")
    records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if sorted(r["decay_rate"] for r in records) != sorted(g0.DECAY_DOMAIN):
        raise RuntimeError("candidate domain mismatch")
    for record in records:
        digest = record["result_digest"]
        if digest != g0._digest({k: v for k, v in record.items() if k != "result_digest"}):
            raise RuntimeError("candidate evidence digest mismatch")
        decay = record["decay_rate"]
        if record["candidate_identity"] != g0.resolve_decay_candidate(decay).candidate_identity:
            raise RuntimeError("candidate identity mismatch")
        for key, source in (
            ("G0_artifact_digest", "artifact_digest"),
            ("search_plan_digest", "search_plan_digest"),
            ("registry_digest", "registry_digest"),
            ("objective_profile_digest", "objective_profile_digest"),
            ("protocol_digest", "protocol_digest"),
        ):
            if record[key] != frozen[source]:
                raise RuntimeError("candidate provenance mismatch")
        if record["scope"] != "adaptive_search_only" or record["held_out_max_horizon"] != 0:
            raise RuntimeError("held-out boundary violation")
        cases = record["cases"]
        if len(cases) != EXPECTED_CASE_COUNT or assess_candidate(cases, frozen) != record["summary"]:
            raise RuntimeError("candidate results incomplete/inconsistent")
        if any(c["candidate_identity"] != record["candidate_identity"] for c in cases):
            raise RuntimeError("case identity mismatch")

    valid = [r for r in records if r["summary"]["valid"]]
    reference = next(r for r in records if r["decay_rate"] == g0.REFERENCE_DECAY_RATE)
    def ordering(r: dict[str, Any]) -> tuple[int, int, int, str]:
        s = r["summary"]
        return (-s["h1000_distinct_count"], -s["h100_distinct_count"],
                -s["turnover_witness_count"], r["candidate_identity"])
    ranking = sorted(valid, key=ordering)
    best = ranking[0] if ranking else None
    if not reference["summary"]["valid"] or not valid:
        route = "ROUTE-G1-FIX"
    elif (best["summary"]["h1000_distinct_count"] >= PHASE_G_ROUTE_THRESHOLD
          and best["summary"]["h1000_distinct_count"] >
          reference["summary"]["h1000_distinct_count"]):
        route = "ROUTE-PHASE-H"
    else:
        route = "CHANGE_PATH"
    result = {
        "schema_version": 1, "issue": 159, "phase": "G1",
        "scope": "adaptive_search_only", "learning_claim": False,
        "held_out_max_horizon": 0, "G0_artifact_digest": frozen["artifact_digest"],
        "objective_profile_digest": frozen["objective_profile_digest"],
        "protocol_digest": frozen["protocol_digest"],
        "reference_decay_rate": 256,
        "reference_h1000_count": reference["summary"]["h1000_distinct_count"],
        "route_threshold": PHASE_G_ROUTE_THRESHOLD,
        "candidate_results": [
            {"decay_rate": r["decay_rate"], "candidate_identity": r["candidate_identity"],
             "summary": r["summary"], "result_digest": r["result_digest"]}
            for r in sorted(records, key=lambda x: x["decay_rate"])
        ],
        "eligible_ranked_decay_rates": [r["decay_rate"] for r in ranking],
        "selected_candidate": None if best is None else {
            "decay_rate": best["decay_rate"],
            "candidate_identity": best["candidate_identity"],
            "summary": best["summary"],
        },
        "terminal_route": route,
    }
    result["result_digest"] = g0._digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--decay", type=int, choices=g0.DECAY_DOMAIN)
    modes.add_argument("--aggregate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_candidate(args.decay) if args.decay is not None else aggregate(args.aggregate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "issue": 159, "mode": "candidate" if args.decay is not None else "aggregate",
        "decay_rate": args.decay, "route": result.get("terminal_route"),
        "result_digest": result["result_digest"], "valid": result.get("summary", {}).get("valid"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
