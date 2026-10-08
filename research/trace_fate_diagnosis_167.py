"""#167 D1: read-only observations of accepted D1 memory physics.

No changes to core, configuration, optimizer, or the frozen #159 evaluator.
The observer wraps existing helper calls and delegates to each exactly once.
Instrumented runs are single-threaded: temporary patches are process-global.
The selected cohort is historically outcome-exposed and is NOT held-out evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack, contextmanager
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import core.physics as physics
from core.experiment import IOExperiment
from core.state import Lifecycle, UniverseState
from research.phase_g_decay_axis_159 import (
    _authorized_role, load_frozen_contract, resolve_decay_candidate,
)
from research.phase_g_memory_search_159 import _digest, _load_base_config, _load_protocol
from research.slow_trace_persistence_140 import (
    AUTHORITATIVE_FIELDS, _checkpoint_from_snapshots,
)
from research.transduction_audit_120 import (
    TEACHER_B, TEACHER_H, advance_to_pre_teacher, canonical_digest,
    clone_state, teacher_step,
)

ISSUE = 167
RATES = (0, 256)
CHECKPOINTS = (0, 1, 2, 4, 8, 16, 32, 64, 100, 128, 256, 512, 1000)
HORIZONS = (1, 10, 100, 1000)
BRANCHES = ("control", "control_repeat", "b", "h")
OBSERVATION_SCHEMA = 1
# Frozen contract: changes require a newly recorded pre-outcome contract.
MEASUREMENTS = (
    "write_units", "write_clamp_loss", "transfer_units", "transfer_pairs",
    "transfer_equalized_pairs", "discharge_budget", "discharge_units",
    "discharge_no_recipient", "discharge_no_headroom", "free_with_trace",
    "gross_free_trace", "fusion_trace_loss", "fragmentation_trace_loss",
    "read_events", "read_bonus_positive", "read_width_saturated",
)


def contract_digest(frozen: dict[str, Any]) -> str:
    return _digest({
        "issue": ISSUE, "schema": OBSERVATION_SCHEMA,
        "g0_artifact_digest": frozen["artifact_digest"],
        "protocol_digest": frozen["protocol_digest"],
        "rates": list(RATES), "checkpoints": list(CHECKPOINTS),
        "search_cohort": frozen["search_cohort"],
        "search_negative_sentinels": frozen["search_negative_sentinels"],
        "measurements": list(MEASUREMENTS),
        "max_heldout_horizon": 0,
    })


class EventObserver:
    """Research-only non-mutating wrapper of production helper boundaries."""

    def __init__(self) -> None:
        self.events: Counter[str] = Counter()
        self.read_sites: dict[tuple[int, int, int, int], list[tuple[int, int]]] = {}
        self._state: UniverseState | None = None

    def begin(self, state: UniverseState | None = None) -> None:
        self._state = state
        self.events = Counter()
        self.read_sites = defaultdict(list)

    @contextmanager
    def attach(self):
        # Store originals before installing wrappers, including instance binding.
        write = physics._apply_slow_trace_writes
        transfer = physics._transfer_slow_trace
        discharge = physics._discharge_slow_trace
        fusion = physics._fuse_groups
        fragmentation = physics._fragment_active_cells
        read = physics.transmission_mask
        free = UniverseState.free

        def observed_write(state, config, amounts):
            before = state.slow_trace[:]
            value = write(state, config, amounts)
            for slot, amount in amounts.items():
                if amount <= 0 or config.trace_write_cap <= 0:
                    continue
                if state.lifecycle[slot] == Lifecycle.FREE:
                    continue
                intended = min(int(amount), config.trace_write_cap)
                actual = state.slow_trace[slot] - before[slot]
                self.events["write_units"] += actual
                self.events["write_clamp_loss"] += intended - actual
            return value

        def observed_transfer(state, config, pairs):
            pairset = tuple(pairs)
            before = state.slow_trace[:]
            result = transfer(state, config, pairset)
            self.events["transfer_pairs"] += len(pairset) if config.trace_transfer_cap else 0
            self.events["transfer_units"] += sum(
                max(0, before[i] - state.slow_trace[i]) for i in range(state.max_cells)
            )
            self.events["transfer_equalized_pairs"] += sum(
                before[a] != before[b] and state.slow_trace[a] == state.slow_trace[b]
                for a, b in pairset
            )
            return result

        def observed_discharge(state, config, occupancy):
            carriers = [
                slot for slot in range(state.max_cells)
                if state.lifecycle[slot] == Lifecycle.BLACK_HOLE and state.slow_trace[slot]
            ]
            before = {slot: state.slow_trace[slot] for slot in carriers}
            for slot in carriers:
                self.events["discharge_budget"] += min(config.trace_discharge_cap, before[slot])
                footprint = physics.destination_footprint(
                    state.structure[slot], state.x[slot], state.y[slot]
                )
                recipients = {
                    recipient
                    for tile in footprint for recipient in occupancy.get(tile, ())
                    if state.lifecycle[recipient] == Lifecycle.ACTIVE
                }
                if not recipients:
                    self.events["discharge_no_recipient"] += 1
                elif all(state.slow_trace[recipient] == 255 for recipient in recipients):
                    self.events["discharge_no_headroom"] += 1
            result = discharge(state, config, occupancy)
            self.events["discharge_units"] += sum(
                max(0, trace - state.slow_trace[slot])
                for slot, trace in before.items()
            )
            return result

        def observed_free(state, slot):
            previous = int(state.slow_trace[slot])
            if previous:
                self.events["free_with_trace"] += 1
                # Gross erasure is NOT net physical information loss in fusion.
                self.events["gross_free_trace"] += previous
            return free(state, slot)

        def observed_fusion(state, config, occupancy):
            before = sum(state.slow_trace)
            result = fusion(state, config, occupancy)
            self.events["fusion_trace_loss"] += max(0, before - sum(state.slow_trace))
            return result

        def observed_fragmentation(state, config, active, generation, fused):
            before = sum(state.slow_trace)
            result = fragmentation(state, config, active, generation, fused)
            self.events["fragmentation_trace_loss"] += max(
                0, before - sum(state.slow_trace)
            )
            return result

        def observed_read(seed, generation, address, pair, bond_strength,
                          participant=None, *, source_trace=None):
            result = read(
                seed, generation, address, pair, bond_strength,
                participant=participant, source_trace=source_trace,
            )
            self.events["read_events"] += 1
            if participant is not None:
                slot = pair[0]
                trace = int(
                    participant.slow_trace[slot] if source_trace is None else source_trace
                )
                shift = int(participant.config.trace_bonus_shift)
                bonus = trace >> shift
                base = 1 + (bond_strength >> 4)
                width = min(16, base + bonus)
                self.events["read_bonus_positive"] += bool(bonus)
                self.events["read_width_saturated"] += width == 16
                # Physical-local key. No persistent slot ID / teacher label.
                site = (int(address), int(participant.x[slot]),
                        int(participant.y[slot]), int(base))
                self.read_sites[site].append((bonus, width))
            return result

        with ExitStack() as stack:
            for name, func in (
                ("_apply_slow_trace_writes", observed_write),
                ("_transfer_slow_trace", observed_transfer),
                ("_discharge_slow_trace", observed_discharge),
                ("_fuse_groups", observed_fusion),
                ("_fragment_active_cells", observed_fragmentation),
                ("transmission_mask", observed_read),
            ):
                stack.enter_context(patch.object(physics, name, new=func))
            stack.enter_context(patch.object(UniverseState, "free", new=observed_free))
            yield self


def _branch_metrics(state: UniverseState) -> dict[str, int]:
    trace = state.slow_trace
    return {
        "trace_mass": sum(trace),
        "trace_nonzero_slots": sum(bool(x) for x in trace),
        "trace_saturated_slots": trace.count(255),
        "active": state.lifecycle.count(Lifecycle.ACTIVE),
        "black_hole": state.lifecycle.count(Lifecycle.BLACK_HOLE),
        "free": state.lifecycle.count(Lifecycle.FREE),
    }


def _distinctions(b: UniverseState, h: UniverseState) -> dict[str, bool]:
    trace = b.slow_trace != h.slow_trace
    other = any(
        getattr(b, field) != getattr(h, field)
        for field in AUTHORITATIVE_FIELDS if field != "slow_trace"
    )
    return {"trace": bool(trace), "nontrace": bool(other), "global": bool(trace or other)}


def _matched_reads(first: dict, second: dict) -> dict[str, int]:
    common = set(first).intersection(second)
    matched = [
        (first[k][0], second[k][0]) for k in common
        if len(first[k]) == len(second[k]) == 1
    ]
    return {
        "matched_sites": len(matched),
        "bonus_differing_sites": sum(a[0] != b[0] for a, b in matched),
        "width_differing_sites": sum(a[1] != b[1] for a, b in matched),
    }


def observe_case(*, seed: int, role: str, decay_rate: int,
                 max_horizon: int = 1000) -> dict[str, Any]:
    frozen = load_frozen_contract()
    _authorized_role(seed, role, frozen)
    if decay_rate not in RATES:
        raise ValueError("rate outside diagnostic control pair")
    if max_horizon not in HORIZONS:
        raise ValueError("horizon outside diagnostic contract")

    base = _load_base_config()
    config = resolve_decay_candidate(
        decay_rate, base_config=base
    ).universe_spec.to_physics_config(base)
    protocol = _load_protocol()
    initial = physics.create_universe(seed=seed, config=config).to_snapshot()
    pre_teacher = advance_to_pre_teacher(
        initial, config=config, protocol=protocol, instrumented=False
    )["a_pre_teacher"]
    # Observe the teacher write window too: h0 state alone cannot reveal
    # write saturation or first read opportunities during teacher output.
    observer = EventObserver()
    h0: dict[str, dict] = {}
    h0_events: dict[str, dict[str, int]] = {}
    with observer.attach():
        for name, value in (
            ("control", None), ("control_repeat", None),
            ("b", TEACHER_B), ("h", TEACHER_H),
        ):
            observer.begin()
            h0[name] = teacher_step(
                pre_teacher, config=config, protocol=protocol,
                teacher_value=value, instrumented=False
            )["after_snapshot"]
            h0_events[name] = {
                key: int(observer.events[key]) for key in MEASUREMENTS
            }
    states = {name: clone_state(h0[name], config) for name in BRANCHES}
    experiments = {
        name: IOExperiment(states[name], experiment=protocol) for name in BRANCHES
    }
    checkpoints = {"0": _checkpoint_from_snapshots(h0)}
    branch_stats = {
        name: {"0": _branch_metrics(states[name])} for name in BRANCHES
    }
    totals = {name: Counter() for name in BRANCHES}
    read_comparison = Counter()
    event_timeline: dict[str, list[dict[str, Any]]] = {"b": [], "h": []}
    trace_timeline: list[dict[str, int]] = []
    matched_read_timeline: list[dict[str, int]] = []
    transitions: dict[str, dict[str, int | None]] = {
        key: {"first_distinct": None, "last_distinct": None,
              "first_reconvergence": None}
        for key in ("trace", "nontrace", "global")
    }
    previous = {key: False for key in transitions}
    with observer.attach():
        for generation in range(0, max_horizon + 1):
            if generation:
                reads = {}
                for name in BRANCHES:
                    observer.begin(states[name])
                    experiments[name]._advance(())
                    totals[name].update(observer.events)
                    if name in ("b", "h"):
                        reads[name] = dict(observer.read_sites)
                        event_timeline[name].append({
                            "generation": generation,
                            "counters": {
                                key: int(value) for key, value in observer.events.items()
                                if value
                            },
                        })
                matched = _matched_reads(reads["b"], reads["h"])
                read_comparison.update(matched)
                matched_read_timeline.append({"generation": generation, **matched})
            b_trace = states["b"].slow_trace
            h_trace = states["h"].slow_trace
            trace_timeline.append({
                "generation": generation,
                "b_mass": sum(b_trace),
                "h_mass": sum(h_trace),
                "differing_slots": sum(a != b for a, b in zip(b_trace, h_trace)),
                "absolute_delta_sum": sum(abs(a - b) for a, b in zip(b_trace, h_trace)),
            })
            diff = _distinctions(states["b"], states["h"])
            for key, differs in diff.items():
                entry = transitions[key]
                if differs:
                    if entry["first_distinct"] is None:
                        entry["first_distinct"] = generation
                    entry["last_distinct"] = generation
                elif previous[key] and entry["first_reconvergence"] is None:
                    entry["first_reconvergence"] = generation
                previous[key] = differs
            if generation in CHECKPOINTS:
                snapshots = {name: state.to_snapshot() for name, state in states.items()}
                checkpoints[str(generation)] = _checkpoint_from_snapshots(snapshots)
                for name in BRANCHES:
                    branch_stats[name][str(generation)] = _branch_metrics(states[name])

    result = {
        "schema_version": OBSERVATION_SCHEMA, "issue": ISSUE,
        "kind": "post_g1_diagnostic_not_heldout",
        "seed": seed, "role": role, "decay_rate": decay_rate,
        "max_horizon": max_horizon, "g0_digest": frozen["artifact_digest"],
        "protocol_digest": frozen["protocol_digest"],
        "contract_digest": contract_digest(frozen),
        "initial_digest": canonical_digest(initial),
        "pre_teacher_digest": canonical_digest(pre_teacher),
        "checkpoint_branch_digests": {
            generation: checkpoint["branch_digests"]
            for generation, checkpoint in checkpoints.items()
        },
        "checkpoints": {
            generation: checkpoint["comparisons"]
            for generation, checkpoint in checkpoints.items()
        },
        "branch_stats": branch_stats,
        "h0_teacher_window_events": h0_events,
        "event_totals": {
            name: {key: int(totals[name][key]) for key in MEASUREMENTS}
            for name in BRANCHES
        },
        "physically_matched_reads": dict(read_comparison),
        "trace_timeline": trace_timeline,
        "event_timeline": event_timeline,
        "matched_read_timeline": matched_read_timeline,
        "transitions": transitions,
        "heldout_max_horizon": 0, "learning_claim": False,
    }
    result["artifact_digest"] = _digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--role", choices=("search", "sentinel"), required=True)
    parser.add_argument("--rate", type=int, required=True)
    parser.add_argument("--horizon", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = observe_case(
        seed=args.seed, role=args.role, decay_rate=args.rate,
        max_horizon=args.horizon,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "seed": result["seed"], "rate": result["decay_rate"],
        "horizon": result["max_horizon"],
        "transitions": result["transitions"],
        "artifact_digest": result["artifact_digest"],
        "learning_claim": result["learning_claim"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
