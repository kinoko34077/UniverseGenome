"""R2 #175: sealed h0 qualification and research-only local WRITE amendments.

Qualify mode reads teacher h0 ONLY. Evaluate mode requires a separately committed
manifest created *before* any post-h0 result; no seed substitution or tuning.
Native physics and production configuration are never changed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import core.physics as physics
from core.experiment import IOExperiment
from core.state import Lifecycle, UniverseState
from research.phase_g_memory_search_159 import _digest, _load_protocol
from research.r1_causal_isolation_172 import profile
from research.slow_trace_persistence_140 import AUTHORITATIVE_FIELDS
from research.transduction_audit_120 import (
    TEACHER_B, TEACHER_H, advance_to_pre_teacher,
    canonical_digest, clone_state, teacher_step,
)

ISSUE = 175
BASE_MAIN = "374f763103546c123b841c3614526acca68fb9cd"
POOL = tuple(range(544, 1024))
POSITIVE_COUNT = 16
NEGATIVE_COUNT = 8
RATE = 256
HORIZONS = (0, 1, 10, 100, 250, 500, 1000)
PROFILES = ("baseline", "unit_add", "empty_site", "half_ceiling")
MANIFEST = Path("research/artifacts/r2_frozen_175.json")
DECISION = {
    "entry": "new disjoint h0-only first-ascending 16 trace-positive and 8 B/H globally equal; never select on h>0",
    "primary": "B/H slow_trace contrast at +1000 in matched post-h0 physical continuation",
    "success": ">=12/16 positive cases distinct at +1000 AND >=4/16 positive paired net uplift versus baseline AND >=1 independently certified legitimate original carrier turnover/handoff witness AND 8/8 negative clean AND all validity gates",
    "negative": "B/H authoritative snapshots identical at all checkpoints and profiles",
    "missing_lineage": "a freed slot plus surviving trace elsewhere is not a certified content-transfer witness; without physical provenance gate remains HOLD/CHANGE_PATH",
    "control": "exact same B/H h0 snapshots, per-profile trajectory RNG state and schedule, unchanged teacher-free post-h0 continuation",
    "post_selection": "full-lifetime generic rule verification including pre-teacher behavior required prior to separate R3 approval",
    "profiles": {
        "baseline": "native saturating uint8 addition",
        "unit_add": "if eligible local physical write and cap>0, add exactly 1 up to 255",
        "empty_site": "if eligible and trace==0, add min(amount,cap) up to 255; otherwise no write",
        "half_ceiling": "if eligible and trace<127, add min(amount,cap) up to 127; otherwise no write"
    },
    "sampling": "new seeds544..1023 first h0-only eligible, 16 positive 8 negative, no fallback after freeze",
    "invalid": "any digest, h0 snapshot, deterministic replay, baseline native parity, neg or source protocol check failure invalidates entire candidate evaluation; no exclusions",
    "mechanism": "research-only patched local generic write operator; no teacher/post-teacher switch in physics; post-h0 snapshot matching is design limitation",
    "out_of_scope": "no full autonomous memory claim, no R3 held-out usage, no old Phase H reserved seeds 96..159 post-h0, no production write rule/default change, no learning_claim"
}


def _engine_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def h0_branches(seed: int) -> dict[str, dict]:
    if seed not in POOL:
        raise ValueError("R2 seed is outside new independent qualification pool")
    config = profile(RATE)
    protocol = _load_protocol()
    initial = physics.create_universe(seed=seed, config=config).to_snapshot()
    prepared = advance_to_pre_teacher(
        initial, config=config, protocol=protocol, instrumented=False
    )["a_pre_teacher"]
    return {
        label: teacher_step(
            prepared, config=config, protocol=protocol,
            teacher_value=value, instrumented=False,
        )["after_snapshot"]
        for label, value in (("b", TEACHER_B), ("h", TEACHER_H), ("control", None))
    }


def _different(a: dict, b: dict, trace: bool = False) -> bool:
    if trace:
        return a["arrays"]["slow_trace"] != b["arrays"]["slow_trace"]
    return any(a["arrays"][key] != b["arrays"][key] for key in AUTHORITATIVE_FIELDS)


def qualify() -> dict[str, Any]:
    """This path is forbidden from advancing any seeded trial beyond h0."""
    positives: list[int] = []
    negatives: list[int] = []
    evidence: dict[str, Any] = {}
    for seed in POOL:
        snapshots = h0_branches(seed)
        is_positive = _different(snapshots["b"], snapshots["h"], trace=True)
        is_negative = not _different(snapshots["b"], snapshots["h"], trace=False)
        if is_positive and len(positives) < POSITIVE_COUNT:
            positives.append(seed)
            role = "positive"
        elif is_negative and len(negatives) < NEGATIVE_COUNT:
            negatives.append(seed)
            role = "negative"
        else:
            continue
        evidence[str(seed)] = {
            "role": role,
            "b_digest": canonical_digest(snapshots["b"]),
            "h_digest": canonical_digest(snapshots["h"]),
            "control_digest": canonical_digest(snapshots["control"]),
            "h0_trace_distinct": is_positive,
            "h0_global_equal": is_negative,
        }
        if len(positives) == POSITIVE_COUNT and len(negatives) == NEGATIVE_COUNT:
            break
    if len(positives) != POSITIVE_COUNT or len(negatives) != NEGATIVE_COUNT:
        raise ValueError("R2 h0-only eligible seed quotas not reached")
    if set(positives) & set(negatives):
        raise ValueError("R2 role overlap")
    result = {
        "schema_version": 1, "issue": ISSUE, "base_main": BASE_MAIN,
        "engine_sha256": _engine_hash(), "seed_pool": [POOL[0], POOL[-1]],
        "positive_seeds": positives, "negative_seeds": negatives,
        "h0_evidence": evidence, "reference_rate": RATE,
        "profiles": list(PROFILES), "checkpoints": list(HORIZONS),
        "decision": DECISION, "max_qualification_horizon": 0,
        "historical_seed_exclusion": [0, 543],
        "r3_unseen_pool_floor": 1024, "learning_claim": False,
    }
    result["digest"] = _digest(result)
    return result


def load_frozen(path: Path = MANIFEST) -> dict[str, Any]:
    frozen = json.loads(path.read_text(encoding="utf-8"))
    digest = frozen.get("digest")
    if _digest({k: v for k, v in frozen.items() if k != "digest"}) != digest:
        raise ValueError("R2 frozen manifest self-digest mismatch")
    if (frozen.get("issue") != ISSUE or frozen.get("base_main") != BASE_MAIN
            or frozen.get("engine_sha256") != _engine_hash()):
        raise ValueError("R2 research engine has changed since pre-outcome freeze")
    if (frozen.get("profiles") != list(PROFILES)
            or frozen.get("checkpoints") != list(HORIZONS)
            or frozen.get("reference_rate") != RATE
            or frozen.get("decision") != DECISION
            or frozen.get("max_qualification_horizon") != 0):
        raise ValueError("R2 frozen design drift")
    positives, negatives = frozen["positive_seeds"], frozen["negative_seeds"]
    if (len(positives) != POSITIVE_COUNT or len(negatives) != NEGATIVE_COUNT
            or set(positives) & set(negatives)
            or not (set(positives) | set(negatives)).issubset(POOL)):
        raise ValueError("R2 seed roster drift")
    return frozen


class LocalWriteRule:
    """Anonymous operator-only research intervention, never installed globally."""
    def __init__(self, name: str, originals: set[int]):
        if name not in PROFILES:
            raise ValueError("unregistered R2 physical candidate")
        self.name = name
        self.originals = originals
        self.events: Counter[str] = Counter()
        self.first_free: dict[int, int] = {}
        self.free_slots: list[tuple[int, int]] = []

    @contextmanager
    def attach(self):
        original_write = physics._apply_slow_trace_writes
        original_free = UniverseState.free

        def write(state, config, amounts):
            if self.name == "baseline":
                return original_write(state, config, amounts)
            if config.trace_write_cap <= 0:
                return original_write(state, config, amounts)
            for slot, amount in amounts.items():
                if state.lifecycle[slot] == Lifecycle.FREE or amount <= 0:
                    continue
                self.events["eligible_sites"] += 1
                old = int(state.slow_trace[slot])
                proposed = min(int(amount), config.trace_write_cap)
                if self.name == "unit_add":
                    new = min(255, old + 1)
                elif self.name == "empty_site":
                    new = min(255, proposed) if old == 0 else old
                elif self.name == "half_ceiling":
                    new = min(127, old + proposed) if old < 127 else old
                else:
                    raise RuntimeError("unhandled R2 candidate")
                state.slow_trace[slot] = new
                if new != old:
                    self.events["effective_sites"] += 1
                    self.events["units_added"] += new - old
            return None

        def free(state, slot):
            if slot in self.originals and slot not in self.first_free:
                self.first_free[slot] = state.generation
                self.events["original_carrier_freed"] += 1
            self.free_slots.append((state.generation, slot))
            return original_free(state, slot)

        with patch.object(physics, "_apply_slow_trace_writes", write), patch.object(
            UniverseState, "free", free
        ):
            yield self


def trajectory(snapshot: dict, *, candidate: str, originals: set[int]):
    config = profile(RATE)
    state = clone_state(snapshot, config)
    experiment = IOExperiment(state, experiment=_load_protocol())
    observer = LocalWriteRule(candidate, originals)
    records: dict[str, Any] = {}
    with observer.attach():
        for horizon in range(1, HORIZONS[-1] + 1):
            experiment._advance(())
            if horizon in HORIZONS:
                records[str(horizon)] = {
                    "trace": list(state.slow_trace), "latent": list(state.latent),
                    "digest": canonical_digest(state.to_snapshot()),
                    "mass": int(sum(state.slow_trace)),
                    "nonfree": [
                        slot for slot in range(state.max_cells)
                        if state.lifecycle[slot] != Lifecycle.FREE
                    ],
                }
    return {
        "checkpoints": records, "events": dict(observer.events),
        "original_first_free": observer.first_free,
        "free_slots": observer.free_slots,
    }


def evaluate_seed(seed: int, frozen: dict) -> dict[str, Any]:
    if seed not in frozen["positive_seeds"] + frozen["negative_seeds"]:
        raise ValueError("seed not selected by pre-outcome freeze")
    branches = h0_branches(seed)
    for label in ("b", "h", "control"):
        expected = frozen["h0_evidence"][str(seed)][label + "_digest"]
        if canonical_digest(branches[label]) != expected:
            raise ValueError("R2 qualified h0 changed")
    originals = {
        idx for idx, (b, h) in enumerate(zip(
            branches["b"]["arrays"]["slow_trace"], branches["h"]["arrays"]["slow_trace"]
        )) if b != h
    }
    histories = {
        candidate: {
            label: trajectory(branches[label], candidate=candidate, originals=originals)
            for label in ("b", "h")
        } for candidate in PROFILES
    }
    data: dict[str, Any] = {}
    for candidate, results in histories.items():
        comparison: dict[str, Any] = {}
        for horizon in HORIZONS[1:]:
            key = str(horizon)
            b = results["b"]["checkpoints"][key]
            h = results["h"]["checkpoints"][key]
            compare = histories["baseline"]
            comparison[key] = {
                "trace_distinct": b["trace"] != h["trace"],
                "trace_difference_l1": sum(abs(x-y) for x,y in zip(b["trace"],h["trace"])),
                "trace_mass_bh": [b["mass"],h["mass"]],
                "latent_intervention_delta_b": (
                    b["latent"] != compare["b"]["checkpoints"][key]["latent"]
                ),
                "latent_intervention_delta_h": (
                    h["latent"] != compare["h"]["checkpoints"][key]["latent"]
                ),
                "b_digest": b["digest"], "h_digest": h["digest"],
            }
        final_b = results["b"]["checkpoints"]["1000"]
        final_h = results["h"]["checkpoints"]["1000"]
        final_elsewhere = [
            slot for slot,(v,w) in enumerate(zip(final_b["trace"],final_h["trace"]))
            if v != w and slot not in originals
            and slot in final_b["nonfree"] and slot in final_h["nonfree"]
        ]
        freed_b, freed_h = results["b"]["original_first_free"], results["h"]["original_first_free"]
        # This is a diagnostic necessary condition, NOT demonstrated physical provenance.
        possible_turnover = bool(
            set(freed_b) & set(freed_h) & originals and final_elsewhere
        )
        data[candidate] = {
            "checkpoints": comparison,
            "write_events": {label: results[label]["events"] for label in ("b","h")},
            "original_freed_bh": [sorted(freed_b), sorted(freed_h)],
            "turnover_possible_but_unproven": possible_turnover,
            "turnover_certified": False,
            "first_free_generation_bh": [
                {str(k):v for k,v in freed_b.items()},
                {str(k):v for k,v in freed_h.items()}
            ],
        }
    role = "positive" if seed in frozen["positive_seeds"] else "negative"
    result = {
        "issue": ISSUE, "schema_version": 1, "seed": seed,
        "role": role, "frozen_digest": frozen["digest"],
        "h0": {k: canonical_digest(v) for k,v in branches.items()},
        "h0_trace_distinct": bool(originals),
        "candidates": data, "learning_claim": False,
    }
    result["digest"] = _digest(result)
    return result


def raw_baseline_parity(seed: int, candidate_result: dict) -> None:
    branches = h0_branches(seed)
    config = profile(RATE)
    for label in ("b", "h"):
        state = clone_state(branches[label], config)
        experiment = IOExperiment(state, experiment=_load_protocol())
        for generation in range(1, HORIZONS[-1]+1):
            experiment._advance(())
            if generation in HORIZONS:
                expected = candidate_result["candidates"]["baseline"]["checkpoints"][str(generation)][label+"_digest"]
                if canonical_digest(state.to_snapshot()) != expected:
                    raise ValueError("R2 native baseline/sham parity mismatch")


def validated_seed(seed: int, frozen: dict) -> dict[str, Any]:
    result = evaluate_seed(seed, frozen)
    if result != evaluate_seed(seed, frozen):
        raise ValueError("R2 deterministic repeat mismatch")
    raw_baseline_parity(seed, result)
    if result["role"] == "negative":
        if result["h0_trace_distinct"]:
            raise ValueError("R2 negative was positive at h0")
        for candidate in PROFILES:
            if any(
                not x["b_digest"] == x["h_digest"]
                for x in result["candidates"][candidate]["checkpoints"].values()
            ):
                raise ValueError("R2 negative sentinel diverged")
    elif not result["h0_trace_distinct"]:
        raise ValueError("R2 positive seed lacked trace contrast at h0")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--qualify", action="store_true")
    p.add_argument("--seed", type=int)
    p.add_argument("--validate", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.qualify:
        if args.seed is not None or args.validate:
            p.error("--qualify cannot examine post-h0 outcomes")
        result = qualify()
    else:
        if args.seed is None:
            p.error("--seed required")
        frozen = load_frozen()
        result = (validated_seed(args.seed, frozen) if args.validate
                  else evaluate_seed(args.seed, frozen))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({
        "issue": ISSUE, "kind": "h0_only_qualification" if args.qualify else "post_h0_candidate",
        "digest": result["digest"], "seed": args.seed, "engine": _engine_hash()
    }, sort_keys=True))


if __name__ == "__main__":
    main()
