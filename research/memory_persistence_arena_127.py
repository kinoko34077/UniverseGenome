"""Research-only memory persistence design arena for UniverseGenome #127.

This module MUST NOT mutate production physics/defaults. It generates a research
variant of the current production step() from its exact source and injects one
predeclared external-energy consolidation hook at the active-cell recovery point.

Route-eligible candidates were frozen in #127 before empirical execution:
- ENERGY_TO_LATENT_XOR
- ENERGY_TO_STRUCTURE_PROMOTE

Reference:
- HP_NO_DECAY_REFERENCE

STIMULUS_CONTACT_BOND_REINFORCEMENT was statically eliminated before MA3.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import physics as P
from core.experiment import ExperimentConfig, IOExperiment
from core.physics import PhysicsConfig, create_universe
from core.runner import load_config
from core.state import UniverseState
from research.transduction_audit_120 import (
    TEACHER_B,
    TEACHER_H,
    build_physics_config,
    canonical_digest,
    clone_state,
    snapshot_diff,
    teacher_coordinates,
)

BASE_MAIN = "a9eed5ca34466f665845f9850ad0b179a004e233"

BASELINE = "BASELINE"
ENERGY_TO_LATENT_XOR = "ENERGY_TO_LATENT_XOR"
ENERGY_TO_STRUCTURE_PROMOTE = "ENERGY_TO_STRUCTURE_PROMOTE"
HP_NO_DECAY_REFERENCE = "HP_NO_DECAY_REFERENCE"

ROUTE_ELIGIBLE_CANDIDATES = (
    ENERGY_TO_LATENT_XOR,
    ENERGY_TO_STRUCTURE_PROMOTE,
)
REFERENCE_CANDIDATES = (HP_NO_DECAY_REFERENCE,)
EMPIRICAL_CANDIDATES = (BASELINE,) + ROUTE_ELIGIBLE_CANDIDATES + REFERENCE_CANDIDATES

PRIMARY_DENSITY32_SEEDS = (0, 5, 8, 9, 12, 14, 18, 19, 20, 22, 24, 29)
NEGATIVE_DENSITY32_SENTINELS = (1, 2, 3, 4)
DENSITY4_WRITE_POSITIVE = (9,)
DENSITY4_NEGATIVE_SENTINELS = (0, 1, 2, 3)
HORIZONS = (0, 1, 10, 100, 1000)
REQUIRED_PRIMARY = 8

NETWORK_FIELDS = frozenset(("latent", "structure", "bond_strength"))
LIFECYCLE_FIELDS = frozenset(
    ("lifecycle", "x", "y", "direction", "speed_code", "age", "black_hole_timer")
)


def _candidate_hook(
    state: UniverseState,
    slot: int,
    recovery_amount: int,
    candidate: str,
) -> dict[str, Any] | None:
    """Apply one frozen research-only candidate at the external recovery hook."""
    amount = int(recovery_amount)
    if amount <= 0:
        return None
    if candidate in (BASELINE, HP_NO_DECAY_REFERENCE):
        return None
    if candidate == ENERGY_TO_LATENT_XOR:
        before = int(state.latent[slot])
        after = (before ^ (amount & 0xFFFF)) & 0xFFFF
        state.latent[slot] = after
        return {
            "field": "latent",
            "before": before,
            "after": after,
            "recovery_amount": amount,
        }
    if candidate == ENERGY_TO_STRUCTURE_PROMOTE:
        before = int(state.structure[slot])
        if before == 0 or P.structure_level(before) >= 7:
            return None
        after = (before << 2) & 0xFFFF
        state.structure[slot] = after
        return {
            "field": "structure",
            "before": before,
            "after": after,
            "recovery_amount": amount,
        }
    raise ValueError(f"unsupported #127 candidate: {candidate}")


def _build_variant_step():
    """Derive the research step from the exact production step source."""
    source = inspect.getsource(P.step)
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

    def replace_once(text: str, old: str, new: str) -> str:
        if text.count(old) != 1:
            raise RuntimeError(
                "production step source anchor changed; #127 variant requires re-audit: "
                + repr(old)
            )
        return text.replace(old, new, 1)

    source = replace_once(
        source,
        "def step(\n",
        "def _generated_variant_step(\n",
    )
    source = replace_once(
        source,
        "    stimulus_slots: Iterable[int] = (),\n) -> StepMetrics:",
        "    stimulus_slots: Iterable[int] = (),\n"
        "    candidate: str = BASELINE,\n"
        "    candidate_write_log: list[dict[str, Any]] | None = None,\n"
        ") -> StepMetrics:",
    )
    source = replace_once(
        source,
        "    stimulated = set(int(slot) for slot in stimulus_slots)\n"
        "    stimulated.update(_local_revival_slots(state))",
        "    external_stimulated = set(int(slot) for slot in stimulus_slots)\n"
        "    stimulated = set(external_stimulated)\n"
        "    stimulated.update(_local_revival_slots(state))",
    )
    source = replace_once(
        source,
        "        if slot in stimulated and slot not in recovered_slots:\n"
        "            state.hp[slot] = min(0xFF, state.hp[slot] + resolved.recovery_hp)\n"
        "        elif slot in latent_activity_slots:\n"
        "            state.hp[slot] = min(0xFF, state.hp[slot] + resolved.recovery_hp)\n"
        "        state.hp[slot] = max(0, state.hp[slot] - resolved.hp_decay)",
        "        external_gain = 0\n"
        "        if slot in stimulated and slot not in recovered_slots:\n"
        "            hp_before_gain = state.hp[slot]\n"
        "            state.hp[slot] = min(0xFF, state.hp[slot] + resolved.recovery_hp)\n"
        "            if slot in external_stimulated:\n"
        "                external_gain = state.hp[slot] - hp_before_gain\n"
        "        elif slot in latent_activity_slots:\n"
        "            state.hp[slot] = min(0xFF, state.hp[slot] + resolved.recovery_hp)\n"
        "        if external_gain > 0:\n"
        "            candidate_record = _candidate_hook(state, slot, external_gain, candidate)\n"
        "            if candidate_record is not None and candidate_write_log is not None:\n"
        "                candidate_write_log.append({\n"
        "                    'generation_before': generation,\n"
        "                    'slot': int(slot),\n"
        "                    'candidate': candidate,\n"
        "                    **candidate_record,\n"
        "                })\n"
        "        state.hp[slot] = max(0, state.hp[slot] - resolved.hp_decay)",
    )

    namespace = dict(P.__dict__)
    namespace.update(
        {
            "Any": Any,
            "BASELINE": BASELINE,
            "_candidate_hook": _candidate_hook,
        }
    )
    exec(compile(source, "<ug127-variant-step>", "exec"), namespace)
    return namespace["_generated_variant_step"], source_hash


variant_step, PRODUCTION_STEP_SOURCE_SHA256 = _build_variant_step()


def candidate_config(
    config_payload: dict[str, Any],
    *,
    density: int,
    candidate: str,
) -> PhysicsConfig:
    config = build_physics_config(config_payload, density)
    if candidate != HP_NO_DECAY_REFERENCE:
        return config
    values = config.to_dict()
    values["hp_decay"] = 0
    return PhysicsConfig(**values)


class VariantIOExperiment(IOExperiment):
    """IOExperiment using the source-anchored research variant step."""

    def __init__(
        self,
        state: UniverseState,
        *,
        experiment: ExperimentConfig,
        candidate: str,
        instrumented: bool,
    ) -> None:
        super().__init__(state, experiment=experiment)
        self.candidate = candidate
        self.instrumented = bool(instrumented)
        self.candidate_writes: list[dict[str, Any]] = []
        self.activity = {
            "collision_count": 0,
            "bond_contact_count": 0,
            "latent_transmission_count": 0,
        }

    def _advance(self, anchors: Iterable[tuple[int, int]] = ()) -> Any:
        stimulus = self._nearby_slots(anchors)
        log = self.candidate_writes if self.instrumented else None
        metrics = variant_step(
            self.state,
            stimulus_slots=stimulus,
            candidate=self.candidate,
            candidate_write_log=log,
        )
        self.activity["collision_count"] += int(metrics.collision_count)
        self.activity["bond_contact_count"] += int(metrics.bond_contact_count)
        self.activity["latent_transmission_count"] += int(
            metrics.latent_transmission_count
        )
        return metrics


def changed_fields(diff: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        name
        for name, payload in diff["fields"].items()
        if int(payload["changed_slots"]) > 0
    )


def checkpoint(
    states: dict[str, UniverseState],
    experiments: dict[str, VariantIOExperiment],
) -> dict[str, Any]:
    snapshots = {name: state.to_snapshot() for name, state in states.items()}
    return {
        "branch_digests": {
            name: canonical_digest(snapshot)
            for name, snapshot in snapshots.items()
        },
        "comparisons": {
            "b_vs_h": snapshot_diff(snapshots["b"], snapshots["h"]),
            "b_vs_control": snapshot_diff(
                snapshots["b"], snapshots["control"]
            ),
            "h_vs_control": snapshot_diff(
                snapshots["h"], snapshots["control"]
            ),
            "control_vs_control_repeat": snapshot_diff(
                snapshots["control"], snapshots["control_repeat"]
            ),
        },
        "active_counts": {
            name: len(state.active_slots()) for name, state in states.items()
        },
        "activity": {
            name: {
                **dict(experiments[name].activity),
                "candidate_write_count": len(
                    experiments[name].candidate_writes
                ),
            }
            for name in states
        },
    }


def prepare_pre_teacher(
    initial_snapshot: dict[str, Any],
    *,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
    candidate: str,
    instrumented: bool,
) -> dict[str, Any]:
    state = clone_state(initial_snapshot, config)
    experiment = VariantIOExperiment(
        state,
        experiment=protocol,
        candidate=candidate,
        instrumented=instrumented,
    )
    for _ in range(protocol.byte_hold_generations):
        experiment.drive_input(65)
        experiment._advance(experiment.input_bus.signal_coordinates())
    experiment.release_input()
    for _ in range(
        protocol.byte_gap_generations + protocol.teacher_delay_generations
    ):
        experiment._advance(())
    return {
        "snapshot": state.to_snapshot(),
        "input_candidate_writes": list(experiment.candidate_writes),
    }


def make_teacher_branch(
    pre_teacher_snapshot: dict[str, Any],
    *,
    config: PhysicsConfig,
    protocol: ExperimentConfig,
    candidate: str,
    teacher_value: int | None,
    instrumented: bool,
) -> dict[str, Any]:
    state = clone_state(pre_teacher_snapshot, config)
    experiment = VariantIOExperiment(
        state,
        experiment=protocol,
        candidate=candidate,
        instrumented=instrumented,
    )
    hits: tuple[int, ...] = ()
    if teacher_value is None:
        experiment._advance(())
    else:
        anchors = teacher_coordinates(teacher_value)
        if instrumented:
            hits = tuple(sorted(experiment._nearby_slots(anchors)))
        experiment._advance(anchors)
    return {
        "state": state,
        "experiment": experiment,
        "hits": list(hits),
        "candidate_writes": list(experiment.candidate_writes),
    }


def case_once(
    *,
    candidate: str,
    density: int,
    seed: int,
    role: str,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
    instrumented: bool,
) -> dict[str, Any]:
    config = candidate_config(
        config_payload,
        density=density,
        candidate=candidate,
    )
    protocol = replace(
        ExperimentConfig.from_mapping(experiment_payload),
        teacher_repetitions=1,
    )
    initial = create_universe(seed=seed, config=config).to_snapshot()
    prepared = prepare_pre_teacher(
        initial,
        config=config,
        protocol=protocol,
        candidate=candidate,
        instrumented=instrumented,
    )
    pre_teacher = prepared["snapshot"]

    branch_payloads = {
        "control": make_teacher_branch(
            pre_teacher,
            config=config,
            protocol=protocol,
            candidate=candidate,
            teacher_value=None,
            instrumented=instrumented,
        ),
        "control_repeat": make_teacher_branch(
            pre_teacher,
            config=config,
            protocol=protocol,
            candidate=candidate,
            teacher_value=None,
            instrumented=instrumented,
        ),
        "b": make_teacher_branch(
            pre_teacher,
            config=config,
            protocol=protocol,
            candidate=candidate,
            teacher_value=TEACHER_B,
            instrumented=instrumented,
        ),
        "h": make_teacher_branch(
            pre_teacher,
            config=config,
            protocol=protocol,
            candidate=candidate,
            teacher_value=TEACHER_H,
            instrumented=instrumented,
        ),
    }
    states = {name: payload["state"] for name, payload in branch_payloads.items()}
    experiments = {
        name: payload["experiment"] for name, payload in branch_payloads.items()
    }

    checkpoints: dict[str, Any] = {"0": checkpoint(states, experiments)}
    h0_diff = checkpoints["0"]["comparisons"]["b_vs_h"]

    trace: dict[str, Any] = {
        "first_non_hp_generation": None,
        "first_lifecycle_generation": None,
        "first_latent_generation": None,
        "first_structure_generation": None,
        "first_bond_generation": None,
        "first_reconvergence_generation": (
            0 if not bool(h0_diff["different"]) else None
        ),
        "first_difference_generation": (
            0 if bool(h0_diff["different"]) else None
        ),
    }

    def inspect_diff(generation: int, diff: dict[str, Any]) -> None:
        fields = set(changed_fields(diff))
        if (
            bool(diff["different"])
            and trace["first_difference_generation"] is None
        ):
            trace["first_difference_generation"] = generation
        if any(name != "hp" for name in fields):
            if trace["first_non_hp_generation"] is None:
                trace["first_non_hp_generation"] = generation
        if fields.intersection(LIFECYCLE_FIELDS):
            if trace["first_lifecycle_generation"] is None:
                trace["first_lifecycle_generation"] = generation
        if "latent" in fields and trace["first_latent_generation"] is None:
            trace["first_latent_generation"] = generation
        if "structure" in fields and trace["first_structure_generation"] is None:
            trace["first_structure_generation"] = generation
        if "bond_strength" in fields and trace["first_bond_generation"] is None:
            trace["first_bond_generation"] = generation
        if (
            not bool(diff["different"])
            and trace["first_reconvergence_generation"] is None
        ):
            trace["first_reconvergence_generation"] = generation

    if instrumented:
        inspect_diff(0, h0_diff)

    for generation in range(1, max(HORIZONS) + 1):
        for experiment in experiments.values():
            experiment._advance(())
        if instrumented:
            bh = snapshot_diff(
                states["b"].to_snapshot(),
                states["h"].to_snapshot(),
            )
            inspect_diff(generation, bh)
        if generation in HORIZONS:
            checkpoints[str(generation)] = checkpoint(states)

    return {
        "status": "complete",
        "candidate": candidate,
        "route_eligible": candidate in ROUTE_ELIGIBLE_CANDIDATES,
        "density": int(density),
        "seed": int(seed),
        "role": role,
        "production_step_source_sha256": PRODUCTION_STEP_SOURCE_SHA256,
        "config": config.to_dict(),
        "initial_snapshot_digest": canonical_digest(initial),
        "pre_teacher_snapshot_digest": canonical_digest(pre_teacher),
        "input_candidate_writes": (
            prepared["input_candidate_writes"] if instrumented else []
        ),
        "teacher": {
            "b_hits": branch_payloads["b"]["hits"] if instrumented else [],
            "h_hits": branch_payloads["h"]["hits"] if instrumented else [],
            "b_candidate_writes": (
                branch_payloads["b"]["candidate_writes"]
                if instrumented else []
            ),
            "h_candidate_writes": (
                branch_payloads["h"]["candidate_writes"]
                if instrumented else []
            ),
        },
        "checkpoints": checkpoints,
        "trace": trace if instrumented else {},
    }


def deterministic_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        key: case[key]
        for key in (
            "candidate",
            "route_eligible",
            "density",
            "seed",
            "role",
            "production_step_source_sha256",
            "config",
            "initial_snapshot_digest",
            "pre_teacher_snapshot_digest",
            "input_candidate_writes",
            "teacher",
            "checkpoints",
            "trace",
        )
    }


def raw_projection(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate": case["candidate"],
        "density": case["density"],
        "seed": case["seed"],
        "initial_snapshot_digest": case["initial_snapshot_digest"],
        "pre_teacher_snapshot_digest": case["pre_teacher_snapshot_digest"],
        "branch_digests": {
            horizon: payload["branch_digests"]
            for horizon, payload in case["checkpoints"].items()
        },
    }


def run_case(
    *,
    candidate: str,
    density: int,
    seed: int,
    role: str,
    verify: bool,
    config_payload: dict[str, Any],
    experiment_payload: dict[str, Any],
) -> dict[str, Any]:
    first = case_once(
        candidate=candidate,
        density=density,
        seed=seed,
        role=role,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
    )
    first["replay_match"] = None
    first["raw_instrumented_match"] = None
    if not verify:
        return first

    second = case_once(
        candidate=candidate,
        density=density,
        seed=seed,
        role=role,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=True,
    )
    raw = case_once(
        candidate=candidate,
        density=density,
        seed=seed,
        role=role,
        config_payload=config_payload,
        experiment_payload=experiment_payload,
        instrumented=False,
    )
    replay = (
        canonical_digest(deterministic_projection(first))
        == canonical_digest(deterministic_projection(second))
    )
    raw_match = raw_projection(first) == raw_projection(raw)
    if not replay:
        raise RuntimeError(
            f"non-deterministic #127 case {candidate} density={density} seed={seed}"
        )
    if not raw_match:
        raise RuntimeError(
            f"instrumentation perturbs #127 case {candidate} density={density} seed={seed}"
        )
    first["replay_match"] = True
    first["raw_instrumented_match"] = True
    return first


def case_plan(candidates: Iterable[str] = EMPIRICAL_CANDIDATES) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate not in EMPIRICAL_CANDIDATES:
            raise ValueError(f"unsupported empirical candidate: {candidate}")
        for seed in PRIMARY_DENSITY32_SEEDS:
            plan.append(
                {
                    "candidate": candidate,
                    "density": 32,
                    "seed": seed,
                    "role": "density32_primary",
                    "verify": (
                        candidate in ROUTE_ELIGIBLE_CANDIDATES
                        or candidate in (BASELINE, HP_NO_DECAY_REFERENCE)
                        and seed == PRIMARY_DENSITY32_SEEDS[0]
                    ),
                }
            )
        for seed in NEGATIVE_DENSITY32_SENTINELS:
            plan.append(
                {
                    "candidate": candidate,
                    "density": 32,
                    "seed": seed,
                    "role": "density32_negative_sentinel",
                    "verify": (
                        candidate in (BASELINE, HP_NO_DECAY_REFERENCE)
                        and seed == NEGATIVE_DENSITY32_SENTINELS[0]
                    ),
                }
            )
        for seed in DENSITY4_WRITE_POSITIVE:
            plan.append(
                {
                    "candidate": candidate,
                    "density": 4,
                    "seed": seed,
                    "role": "density4_write_positive_control",
                    "verify": candidate in (BASELINE, HP_NO_DECAY_REFERENCE),
                }
            )
        for seed in DENSITY4_NEGATIVE_SENTINELS:
            plan.append(
                {
                    "candidate": candidate,
                    "density": 4,
                    "seed": seed,
                    "role": "density4_negative_sentinel",
                    "verify": False,
                }
            )
    return plan


def case_key(candidate: str, density: int, seed: int) -> str:
    return f"{candidate}:{density}:{seed}"


def read_completed(path: Path) -> dict[str, dict[str, Any]]:
    completed: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return completed
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError:
            # A final partial line can exist only after abrupt interruption.
            if line_number == len(path.read_text(encoding="utf-8").splitlines()):
                continue
            raise
        if case.get("status") != "complete":
            continue
        completed[case_key(
            str(case["candidate"]),
            int(case["density"]),
            int(case["seed"]),
        )] = case
    return completed


def append_case(path: Path, case: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(case, sort_keys=True, separators=(",", ":")))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def checkpoint_diff(case: dict[str, Any], horizon: int) -> dict[str, Any]:
    return case["checkpoints"][str(horizon)]["comparisons"]["b_vs_h"]


def candidate_summary(
    candidate: str,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    primary = [case for case in cases if case["role"] == "density32_primary"]
    negatives = [
        case for case in cases
        if "negative_sentinel" in case["role"]
    ]
    d32_neg = [
        case for case in cases
        if case["role"] == "density32_negative_sentinel"
    ]

    horizons: dict[str, Any] = {}
    for horizon in HORIZONS:
        distinct = [
            case for case in primary
            if checkpoint_diff(case, horizon)["different"]
        ]
        horizons[str(horizon)] = {
            "distinct_count": len(distinct),
            "distinct_seeds": [int(case["seed"]) for case in distinct],
        }

    non_hp = [
        case for case in primary
        if case["trace"]["first_non_hp_generation"] is not None
        and int(case["trace"]["first_non_hp_generation"]) <= 1000
    ]
    pre_lifecycle = []
    for case in primary:
        non = case["trace"]["first_non_hp_generation"]
        life = case["trace"]["first_lifecycle_generation"]
        if non is not None and (life is None or int(non) < int(life)):
            pre_lifecycle.append(case)

    negative_clean = all(
        case["trace"]["first_difference_generation"] is None
        for case in negatives
    )
    duplicate_control_clean = all(
        all(
            not case["checkpoints"][str(horizon)]["comparisons"][
                "control_vs_control_repeat"
            ]["different"]
            for horizon in HORIZONS
        )
        for case in cases
    )
    verified = [
        case for case in cases if case["replay_match"] is not None
    ]
    replay_clean = all(case["replay_match"] is True for case in verified)
    raw_clean = all(
        case["raw_instrumented_match"] is True for case in verified
    )
    verified_primary = [
        case for case in primary if case["replay_match"] is not None
    ]

    h1000 = horizons["1000"]["distinct_count"]
    route_eligible = candidate in ROUTE_ELIGIBLE_CANDIDATES
    capable = (
        route_eligible
        and h1000 >= REQUIRED_PRIMARY
        and len(non_hp) >= REQUIRED_PRIMARY
        and len(pre_lifecycle) >= REQUIRED_PRIMARY
        and negative_clean
        and duplicate_control_clean
        and len(verified_primary) == len(PRIMARY_DENSITY32_SEEDS)
        and replay_clean
        and raw_clean
    )
    return {
        "candidate": candidate,
        "route_eligible": route_eligible,
        "primary_case_count": len(primary),
        "horizons": horizons,
        "non_hp_by_1000_count": len(non_hp),
        "non_hp_by_1000_seeds": [int(case["seed"]) for case in non_hp],
        "pre_lifecycle_non_hp_count": len(pre_lifecycle),
        "pre_lifecycle_non_hp_seeds": [
            int(case["seed"]) for case in pre_lifecycle
        ],
        "negative_sentinels_clean": negative_clean,
        "density32_negative_sentinel_count": len(d32_neg),
        "duplicate_control_clean": duplicate_control_clean,
        "verified_case_count": len(verified),
        "verified_primary_count": len(verified_primary),
        "replay_clean": replay_clean,
        "raw_instrumented_clean": raw_clean,
        "input_candidate_write_count": sum(
            len(case["input_candidate_writes"]) for case in cases
        ),
        "teacher_candidate_write_count": sum(
            len(case["teacher"]["b_candidate_writes"])
            + len(case["teacher"]["h_candidate_writes"])
            for case in cases
        ),
        "persistence_capable": capable,
    }


def baseline_reference() -> dict[str, Any]:
    path = Path("research/artifacts/memory_coupling_audit_122_summary.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "source_issue": 122,
        "source_main": "1355bb8fbdaed66e58166cdd19a8d74fa7bf1c5b",
        "primary_h0": payload["primary_density32"]["h0_write_count"],
        "primary_h1000": payload["primary_density32"]["h1000_persistent_count"],
        "route": payload["route_gate"]["route"],
    }


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_candidate = {
        candidate: candidate_summary(
            candidate,
            [case for case in cases if case["candidate"] == candidate],
        )
        for candidate in EMPIRICAL_CANDIDATES
    }
    passing = [
        candidate
        for candidate in ROUTE_ELIGIBLE_CANDIDATES
        if by_candidate[candidate]["persistence_capable"]
    ]
    return {
        "issue": 127,
        "base_main": BASE_MAIN,
        "production_step_source_sha256": PRODUCTION_STEP_SOURCE_SHA256,
        "learning_claim": False,
        "p6_10_plus": "frozen",
        "production_physics_change": False,
        "baseline_reference": baseline_reference(),
        "protocol": {
            "teacher_pair": [TEACHER_B, TEACHER_H],
            "horizons": list(HORIZONS),
            "required_primary": REQUIRED_PRIMARY,
            "primary_density32_seeds": list(PRIMARY_DENSITY32_SEEDS),
            "density32_negative_sentinels": list(
                NEGATIVE_DENSITY32_SENTINELS
            ),
            "density4_write_positive": list(DENSITY4_WRITE_POSITIVE),
            "density4_negative_sentinels": list(
                DENSITY4_NEGATIVE_SENTINELS
            ),
        },
        "candidate_results": by_candidate,
        "passing_candidates": passing,
        "terminal_route": (
            "ROUTE-PHYSICS-CANDIDATE"
            if passing
            else "ROUTE-ARCHITECTURE-RETHINK"
        ),
    }


def parse_candidates(raw: str) -> tuple[str, ...]:
    values = tuple(
        item.strip() for item in raw.split(",") if item.strip()
    )
    if not values:
        raise ValueError("at least one candidate is required")
    for value in values:
        if value not in EMPIRICAL_CANDIDATES:
            raise ValueError(f"unsupported empirical candidate: {value}")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("config/default.json")
    )
    parser.add_argument(
        "--experiment",
        type=Path,
        default=Path("config/experiment_v0_1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "research/artifacts/memory_persistence_arena_127.jsonl"
        ),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path(
            "research/artifacts/memory_persistence_arena_127_summary.json"
        ),
    )
    parser.add_argument(
        "--candidates",
        default=",".join(EMPIRICAL_CANDIDATES),
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
    )
    args = parser.parse_args()

    selected = parse_candidates(args.candidates)
    config_payload = load_config(args.config)
    experiment_payload = json.loads(
        args.experiment.read_text(encoding="utf-8")
    )
    plan = case_plan(selected)
    completed = read_completed(args.output)

    if not args.summary_only:
        for spec in plan:
            key = case_key(
                str(spec["candidate"]),
                int(spec["density"]),
                int(spec["seed"]),
            )
            if key in completed:
                print(f"#127 skip completed {key}", file=sys.stderr, flush=True)
                continue
            case = run_case(
                candidate=str(spec["candidate"]),
                density=int(spec["density"]),
                seed=int(spec["seed"]),
                role=str(spec["role"]),
                verify=bool(spec["verify"]),
                config_payload=config_payload,
                experiment_payload=experiment_payload,
            )
            append_case(args.output, case)
            completed[key] = case
            print(
                f"#127 complete {key} "
                f"h1000={checkpoint_diff(case, 1000)['different']} "
                f"nonhp={case['trace']['first_non_hp_generation']} "
                f"life={case['trace']['first_lifecycle_generation']}",
                file=sys.stderr,
                flush=True,
            )

    required_keys = {
        case_key(
            str(spec["candidate"]),
            int(spec["density"]),
            int(spec["seed"]),
        )
        for spec in case_plan(EMPIRICAL_CANDIDATES)
    }
    missing = sorted(required_keys.difference(completed))
    if missing:
        print(
            json.dumps(
                {
                    "status": "partial",
                    "completed": len(completed),
                    "required": len(required_keys),
                    "missing": missing,
                },
                indent=2,
            )
        )
        return 2

    ordered = [
        completed[
            case_key(
                str(spec["candidate"]),
                int(spec["density"]),
                int(spec["seed"]),
            )
        ]
        for spec in case_plan(EMPIRICAL_CANDIDATES)
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
