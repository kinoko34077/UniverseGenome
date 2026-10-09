"""#172 R1: research-only local causal trace interventions.

IMPORTANT: --qualify reads ONLY h0. Intervention execution requires the
separately committed, content-addressed frozen R1 manifest; no runtime seed
selection or historical Phase H held-out access is permitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack, contextmanager
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import core.physics as physics
from core.experiment import IOExperiment
from core.state import Lifecycle, UniverseState
from research.phase_g_decay_axis_159 import load_frozen_contract, resolve_decay_candidate
from research.phase_g_memory_search_159 import _digest, _load_base_config, _load_protocol
from research.slow_trace_persistence_140 import AUTHORITATIVE_FIELDS
from research.transduction_audit_120 import (
    TEACHER_B, TEACHER_H, advance_to_pre_teacher, canonical_digest,
    clone_state, teacher_step,
)

ISSUE = 172
POOL = tuple(range(160, 544))
OLD_POOLS = frozenset(range(0, 160))
POSITIVE_COUNT = 24
NEGATIVE_COUNT = 8
RATES = (0, 256)
FACTORS = ("free_local_relay", "post_h0_write_off", "transfer_off", "read_bonus_off")
CHECKPOINTS = (0, 1, 10, 100, 250, 500, 1000)
FROZEN_PATH = Path("research/artifacts/r1_frozen_172.json")
SOURCE_BASE = "f7681f7a9879624a5889b96c52a412405d2ac16f"


def profile(rate: int):
    if rate not in RATES:
        raise ValueError("rate outside R1 reference controls")
    base = _load_base_config()
    return resolve_decay_candidate(rate, base_config=base).universe_spec.to_physics_config(base)


def h0_snapshots(seed: int, *, rate: int = 256) -> dict[str, dict]:
    if seed not in POOL and seed not in load_frozen_contract()["search_cohort"]:
        raise ValueError("seed outside R1 qualification/exploratory data")
    config = profile(rate)
    experiment = _load_protocol()
    initial = physics.create_universe(seed=seed, config=config).to_snapshot()
    prepared = advance_to_pre_teacher(
        initial, config=config, protocol=experiment, instrumented=False
    )["a_pre_teacher"]
    return {
        name: teacher_step(
            prepared, config=config, protocol=experiment,
            teacher_value=value, instrumented=False,
        )["after_snapshot"]
        for name, value in (("b", TEACHER_B), ("h", TEACHER_H), ("control", None))
    }


def _different(a: dict, b: dict, *, trace: bool) -> bool:
    if trace:
        return a["arrays"]["slow_trace"] != b["arrays"]["slow_trace"]
    return any(a["arrays"][k] != b["arrays"][k] for k in AUTHORITATIVE_FIELDS)


def qualification() -> dict[str, Any]:
    """No post-h0 outcome may be consulted by this scan."""
    positives: list[int] = []
    negatives: list[int] = []
    h0_evidence: dict[str, dict] = {}
    for seed in POOL:
        snapshots = h0_snapshots(seed)
        positive = _different(snapshots["b"], snapshots["h"], trace=True)
        globally_different = _different(snapshots["b"], snapshots["h"], trace=False)
        if positive and len(positives) < POSITIVE_COUNT:
            positives.append(seed)
            role = "positive"
        elif not globally_different and len(negatives) < NEGATIVE_COUNT:
            negatives.append(seed)
            role = "negative"
        else:
            continue
        h0_evidence[str(seed)] = {
            "role": role,
            "b_digest": canonical_digest(snapshots["b"]),
            "h_digest": canonical_digest(snapshots["h"]),
            "control_digest": canonical_digest(snapshots["control"]),
            "h0_trace_distinct": positive,
            "h0_global_distinct": globally_different,
        }
        if len(positives) == POSITIVE_COUNT and len(negatives) == NEGATIVE_COUNT:
            break
    if len(positives) != POSITIVE_COUNT or len(negatives) != NEGATIVE_COUNT:
        raise ValueError("R1 h0-only qualification could not fill frozen counts")
    if (set(positives) | set(negatives)) & OLD_POOLS:
        raise ValueError("historical or Phase H protected seed collision")
    record = {
        "schema_version": 1,
        "issue": ISSUE,
        "kind": "h0_only_unexposed_qualification",
        "base_main": SOURCE_BASE,
        "scan_pool": [POOL[0], POOL[-1]],
        "reference_rate": 256,
        "positive_seeds": positives,
        "negative_seeds": negatives,
        "h0_evidence": h0_evidence,
        "horizon_max": 0,
        "learning_claim": False,
    }
    record["digest"] = _digest(record)
    return record


def load_frozen(path: Path = FROZEN_PATH) -> dict[str, Any]:
    frozen = json.loads(path.read_text(encoding="utf-8"))
    digest = frozen.pop("digest", None)
    if _digest(frozen) != digest:
        raise ValueError("R1 frozen protocol digest mismatch")
    frozen["digest"] = digest
    if frozen.get("issue") != ISSUE or frozen.get("base_main") != SOURCE_BASE:
        raise ValueError("R1 protocol/authority mismatch")
    a = frozen.get("positive_seeds", [])
    b = frozen.get("negative_seeds", [])
    if len(a) != POSITIVE_COUNT or len(b) != NEGATIVE_COUNT:
        raise ValueError("R1 count drift")
    if not (set(a) | set(b)).issubset(POOL) or set(a) & set(b):
        raise ValueError("R1 seed disjointness failure")
    if frozen.get("rates") != list(RATES) or frozen.get("factors") != list(FACTORS):
        raise ValueError("R1 factors/rates changed")
    if frozen.get("checkpoints") != list(CHECKPOINTS):
        raise ValueError("R1 horizons changed")
    if frozen.get("heldout_max_horizon") != 0:
        raise ValueError("R1 reserved heldout boundary changed")
    return frozen


class ResearchIntervention:
    """Pass-through sham or exactly ONE research-only local operator change.

    Patch exists only within the requested trajectory, after teacher h0.
    Counters describe exposure; no semantic value/teacher label enters physics.
    """

    def __init__(self, factor: str):
        if factor not in ("sham",) + FACTORS:
            raise ValueError("unregistered intervention")
        self.factor = factor
        self.events: Counter[str] = Counter()

    @contextmanager
    def attach(self):
        write = physics._apply_slow_trace_writes
        transfer = physics._transfer_slow_trace
        read = physics.transmission_mask
        free = UniverseState.free

        def observed_write(state, config, amounts):
            self.events["write_sites"] += sum(
                int(amount > 0 and state.lifecycle[slot] != Lifecycle.FREE)
                for slot, amount in amounts.items()
            )
            self.events["write_saturation_opportunities"] += sum(
                max(0, min(int(amount), config.trace_write_cap)
                    - (255 - int(state.slow_trace[slot])))
                for slot, amount in amounts.items()
                if amount > 0 and state.lifecycle[slot] != Lifecycle.FREE
            )
            if self.factor == "post_h0_write_off":
                return None
            return write(state, config, amounts)

        def observed_transfer(state, config, pairs):
            selected = tuple(pairs)
            self.events["transfer_opportunities"] += sum(
                state.lifecycle[a] != Lifecycle.FREE
                and state.lifecycle[b] != Lifecycle.FREE
                and state.slow_trace[a] != state.slow_trace[b]
                for a, b in selected
            )
            if self.factor == "transfer_off":
                return None
            return transfer(state, config, selected)

        def observed_free(state, slot):
            amount = int(state.slow_trace[slot])
            if amount:
                self.events["free_trace_events"] += 1
                self.events["free_trace_mass"] += amount
            if self.factor == "free_local_relay" and amount:
                footprint = physics.destination_footprint(
                    state.structure[slot], state.x[slot], state.y[slot]
                )
                occupancy = physics._active_occupancy(state)
                local = sorted({
                    recipient for tile in footprint
                    for recipient in occupancy.get(tile, ())
                    if recipient != slot and state.lifecycle[recipient] == Lifecycle.ACTIVE
                    and int(state.slow_trace[recipient]) < 255
                }, key=lambda k: physics._trace_physical_order_key(state, k))
                if local:
                    target = local[0]
                    cap = state.config.trace_discharge_cap
                    quantity = min(amount, cap, 255 - int(state.slow_trace[target]))
                    if quantity:
                        state.slow_trace[target] += quantity
                        state.slow_trace[slot] -= quantity
                        self.events["relay_units"] += quantity
                        self.events["relay_events"] += 1
            return free(state, slot)

        def observed_read(seed, generation, address, pair, bond_strength,
                          participant=None, *, source_trace=None):
            observed = read(
                seed, generation, address, pair, bond_strength,
                participant=participant, source_trace=source_trace,
            )
            if participant is None:
                return observed
            trace = int(
                participant.slow_trace[pair[0]] if source_trace is None else source_trace
            )
            no_bonus = read(
                seed, generation, address, pair, bond_strength,
                participant=participant, source_trace=0,
            )
            self.events["read_sites"] += 1
            self.events["read_mask_difference_opportunities"] += observed != no_bonus
            return no_bonus if self.factor == "read_bonus_off" else observed

        with ExitStack() as stack:
            stack.enter_context(patch.object(physics, "_apply_slow_trace_writes", observed_write))
            stack.enter_context(patch.object(physics, "_transfer_slow_trace", observed_transfer))
            stack.enter_context(patch.object(physics, "transmission_mask", observed_read))
            stack.enter_context(patch.object(UniverseState, "free", observed_free))
            yield self


def trajectory(snapshot: dict, *, rate: int, factor: str,
               horizon: int) -> dict[str, Any]:
    """A physical trajectory cloned from the exact after-teacher snapshot."""
    if horizon not in CHECKPOINTS[1:]:
        raise ValueError("unregistered R1 horizon")
    cfg = profile(rate)
    state = clone_state(snapshot, cfg)
    experiment = IOExperiment(state, experiment=_load_protocol())
    probe = ResearchIntervention(factor)
    observations: dict[str, dict] = {}
    first_latent_delta: int | None = None
    # No teacher/no additional A input after h0.
    with probe.attach():
        for generation in range(1, horizon + 1):
            experiment._advance(())
            if generation in CHECKPOINTS:
                observations[str(generation)] = {
                    "trace": list(state.slow_trace),
                    "latent": list(state.latent),
                    "snapshot_digest": canonical_digest(state.to_snapshot()),
                    "mass": sum(state.slow_trace),
                }
    return {"checkpoints": observations, "events": dict(sorted(probe.events.items()))}


def evaluate_seed(seed: int, *, rate: int, frozen: dict,
                  horizon: int = 1000) -> dict[str, Any]:
    role = ("positive" if seed in frozen["positive_seeds"] else
            "negative" if seed in frozen["negative_seeds"] else None)
    if role is None:
        raise ValueError("seed not authorized by frozen manifest")
    snapshots = h0_snapshots(seed, rate=rate)
    branches: dict[str, dict] = {"sham": {}, **{k: {} for k in FACTORS}}
    for factor in branches:
        for teacher in ("b", "h"):
            branches[factor][teacher] = trajectory(
                snapshots[teacher], rate=rate, factor=factor, horizon=horizon
            )
    by_factor: dict[str, Any] = {}
    for factor, trajectories in branches.items():
        item: dict[str, Any] = {"events": {
            teacher: trajectories[teacher]["events"] for teacher in ("b", "h")
        }}
        item["checkpoints"] = {}
        for k in (str(x) for x in CHECKPOINTS[1:] if x <= horizon):
            b, h = (trajectories[t]["checkpoints"][k] for t in ("b", "h"))
            sham_b = branches["sham"]["b"]["checkpoints"][k]
            sham_h = branches["sham"]["h"]["checkpoints"][k]
            item["checkpoints"][k] = {
                "trace_distinct": b["trace"] != h["trace"],
                "trace_delta": sum(abs(a - c) for a, c in zip(b["trace"], h["trace"])),
                "trace_masses": [b["mass"], h["mass"]],
                "latent_distinct": b["latent"] != h["latent"],
                "b_latent_vs_sham": b["latent"] != sham_b["latent"],
                "h_latent_vs_sham": h["latent"] != sham_h["latent"],
                "teacher_latent_response_interaction_slots": sum(
                    (int(b["latent"][index]) - int(sham_b["latent"][index]))
                    != (int(h["latent"][index]) - int(sham_h["latent"][index]))
                    for index in range(len(b["latent"]))
                ),
                "b_digest": b["snapshot_digest"], "h_digest": h["snapshot_digest"],
            }
        by_factor[factor] = item
    primary = str(horizon)
    result = {
        "issue": ISSUE, "schema_version": 1, "seed": seed,
        "role": role, "rate": rate, "horizon": horizon,
        "frozen_digest": frozen["digest"],
        "h0": {k: canonical_digest(v) for k, v in snapshots.items()},
        "initial_trace_distinct": _different(snapshots["b"], snapshots["h"], trace=True),
        "initial_global_distinct": _different(snapshots["b"], snapshots["h"], trace=False),
        "factors": by_factor,
        "outcomes": {
            factor: {
                "sham_distinct": by_factor["sham"]["checkpoints"][primary]["trace_distinct"],
                "intervention_distinct": by_factor[factor]["checkpoints"][primary]["trace_distinct"],
                "rescue_only": (
                    by_factor[factor]["checkpoints"][primary]["trace_distinct"]
                    and not by_factor["sham"]["checkpoints"][primary]["trace_distinct"]
                ),
                "sham_only": (
                    by_factor["sham"]["checkpoints"][primary]["trace_distinct"]
                    and not by_factor[factor]["checkpoints"][primary]["trace_distinct"]
                ),
                "physical_latent_change": any(
                    p["b_latent_vs_sham"] or p["h_latent_vs_sham"]
                    for p in by_factor[factor]["checkpoints"].values()
                ),
                "teacher_latent_response_interaction": any(
                    p["teacher_latent_response_interaction_slots"] > 0
                    for p in by_factor[factor]["checkpoints"].values()
                ),
                "factor_exposure": (
                    sum(by_factor[factor]["events"][teacher].get(event, 0)
                        for teacher in ("b", "h")) > 0
                ),
            } for factor in FACTORS
            for event in ((
                "relay_events" if factor == "free_local_relay" else
                "write_sites" if factor == "post_h0_write_off" else
                "transfer_opportunities" if factor == "transfer_off" else
                "read_mask_difference_opportunities"
            ),)
        },
        "learning_claim": False, "heldout_max_horizon": 0,
    }
    result["digest"] = _digest(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualify", action="store_true")
    parser.add_argument("--evaluate-seed", type=int)
    parser.add_argument("--rate", type=int, default=256)
    parser.add_argument("--horizon", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.qualify:
        if args.evaluate_seed is not None:
            parser.error("--qualify forbids evaluation")
        output = qualification()
    else:
        if args.evaluate_seed is None:
            parser.error("--evaluate-seed required")
        frozen = load_frozen()
        output = evaluate_seed(args.evaluate_seed, rate=args.rate, frozen=frozen,
                               horizon=args.horizon)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8"
    )
    print(json.dumps({
        "issue": ISSUE, "kind": "h0_qualification" if args.qualify else "intervention",
        "digest": output["digest"], "seed": args.evaluate_seed, "rate": args.rate,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
