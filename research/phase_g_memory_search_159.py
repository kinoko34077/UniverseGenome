"""Phase G / #159 bounded memory-physics research consumer.

G0 intentionally does not unlock the production SteadyStateOptimizer for arbitrary
SearchPlans.  It consumes the accepted generalized SearchPlan/registry/resolver
surface directly, and is limited to h0 cohort qualification plus provenance freeze.
No +100/+1000 adaptive ranking or held-out post-h0 execution exists in this module.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig, create_universe
from core.runner import load_config
from search.genome import UniverseGenome, UNIVERSE_GENOME_FIELDS
from search.outer_search import (
    CandidateValues,
    ObjectiveMetric,
    ObjectiveProfile,
    RuleSearch,
    ScalarSearch,
    SearchPlan,
    SearchRegistry,
    build_default_search_registry,
    resolve_candidate,
)
from research.slow_trace_persistence_140 import snapshot_diff
from research.transduction_audit_120 import (
    TEACHER_B,
    TEACHER_H,
    advance_to_pre_teacher,
    canonical_digest,
    teacher_step,
)

ISSUE = 159
BASELINE_SHA = "b5803adf87f24375d9aa33abc99d85fa91d4eed5"
BASELINE_TAG = "v0.2.0-alpha.1"

OLD_140_PRIMARY_SEEDS = (0, 5, 8, 9, 12, 14, 18, 19, 20, 22, 24, 29)
SEARCH_POOL = tuple(range(32, 96))
HELDOUT_POOL = tuple(range(96, 160))

SEARCH_POSITIVE_COUNT = 16
SEARCH_NEGATIVE_COUNT = 4
HELDOUT_POSITIVE_COUNT = 12
HELDOUT_NEGATIVE_COUNT = 4

DECAY_DOMAIN = (0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024)
REFERENCE_DECAY_RATE = 256
SEARCH_HORIZONS = (100, 1000)
REFERENCE_TRACE_FIXED = {
    "trace_write_cap": 32,
    "trace_transfer_cap": 8,
    "trace_discharge_cap": 16,
    "trace_bonus_shift": 5,
}

OBJECTIVE_PROFILE_ID = "phase_g_l3_persistence"
OBJECTIVE_PROFILE_VERSION = 1
SEARCH_COHORT_POLICY = "phase_g_search_qualified_h0_v1"
VALIDATION_COHORT_POLICY = "phase_g_heldout_qualified_h0_v1"


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def phase_g_objective_profile() -> ObjectiveProfile:
    """Predeclared Phase G ranking contract; G0 records it but does not rank."""
    return ObjectiveProfile(
        profile_id=OBJECTIVE_PROFILE_ID,
        version=OBJECTIVE_PROFILE_VERSION,
        metrics=(
            ObjectiveMetric("h1000_distinct_count", "maximize", comparison=True),
            ObjectiveMetric("h100_distinct_count", "maximize", comparison=True),
            ObjectiveMetric("turnover_witness_count", "maximize", comparison=True),
        ),
        minimum_evidence=4,
        tie_breakers=("candidate_identity",),
        invalid_evidence_policy="reject",
        negative_control_fields=(
            "negative_sentinels_clean",
            "replay_clean",
            "raw_instrumented_clean",
        ),
        negative_control_policy="gate",
        short_health_policy="phase5_short_health_v1",
        failure_policy="phase5_failure_v1",
        response_window_limit=4,
    )


def build_phase_g_registry() -> SearchRegistry:
    """Return the accepted production registry plus the predeclared research objective."""
    base = build_default_search_registry()
    objectives = dict(base.objective_profiles)
    profile = phase_g_objective_profile()
    objectives[(profile.profile_id, profile.version)] = profile
    return SearchRegistry(
        scalar_dimensions=dict(base.scalar_dimensions),
        rule_dimensions=dict(base.rule_dimensions),
        objective_profiles=objectives,
        schema_version=base.schema_version,
    )


def phase_g_search_plan() -> SearchPlan:
    """Decay-only research plan frozen by #159 before any long-horizon outcome."""
    fixed: dict[str, int] = UniverseGenome.default().to_dict()
    fixed["initial_density"] = 32
    fixed.update(REFERENCE_TRACE_FIXED)
    return SearchPlan(
        schema_version=1,
        plan_id="phase_g_decay_axis",
        plan_version=1,
        population_size=128,
        fixed=fixed,
        search={
            "trace_decay_rate": ScalarSearch(
                strategy="adjacent_binary",
                domain=DECAY_DOMAIN,
            )
        },
        rules={
            "latent_operator": RuleSearch(
                variants=("masked_copy",),
                strategy="finite_variant",
            )
        },
        objective_profile_id=OBJECTIVE_PROFILE_ID,
        objective_profile_version=OBJECTIVE_PROFILE_VERSION,
        search_cohort_policy=SEARCH_COHORT_POLICY,
        validation_cohort_policy=VALIDATION_COHORT_POLICY,
        scheduler_base_seed=0,
        scheduler_policy="phase_g_matched_evidence_v1",
        initialization_policy="phase_g_decay_domain_v1",
    )


def decay_candidate(decay_rate: int) -> CandidateValues:
    if decay_rate not in DECAY_DOMAIN:
        raise ValueError("decay_rate is outside the frozen Phase G domain")
    return CandidateValues(
        scalars={"trace_decay_rate": int(decay_rate)},
        rules={"latent_operator": "masked_copy"},
    )


def resolve_decay_candidate(
    decay_rate: int,
    *,
    base_config: PhysicsConfig | None = None,
):
    plan = phase_g_search_plan()
    registry = build_phase_g_registry()
    result = resolve_candidate(plan, registry, decay_candidate(decay_rate))
    result.universe_spec.to_physics_config(base_config or PhysicsConfig())
    return result


def _load_protocol(
    experiment_path: Path = Path("config/experiment_v0_1.json"),
) -> ExperimentConfig:
    payload = json.loads(experiment_path.read_text(encoding="utf-8"))
    return replace(ExperimentConfig.from_mapping(payload), teacher_repetitions=1)


def _load_base_config(
    config_path: Path = Path("config/default.json"),
) -> PhysicsConfig:
    return PhysicsConfig.from_mapping(load_config(config_path))


def qualify_case_h0(
    *,
    seed: int,
    config_path: Path = Path("config/default.json"),
    experiment_path: Path = Path("config/experiment_v0_1.json"),
) -> dict[str, Any]:
    """Inspect only the immediate post-teacher state used to qualify cohorts."""
    if seed < 0:
        raise ValueError("seed must be non-negative")

    base_config = _load_base_config(config_path)
    resolved = resolve_decay_candidate(REFERENCE_DECAY_RATE, base_config=base_config)
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

    branches = {
        "control": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=None,
            instrumented=False,
        )["after_snapshot"],
        "control_repeat": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=None,
            instrumented=False,
        )["after_snapshot"],
        "b": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=TEACHER_B,
            instrumented=False,
        )["after_snapshot"],
        "h": teacher_step(
            pre_teacher,
            config=config,
            protocol=protocol,
            teacher_value=TEACHER_H,
            instrumented=False,
        )["after_snapshot"],
    }

    b_vs_h = snapshot_diff(branches["b"], branches["h"])
    control_repeat = snapshot_diff(branches["control"], branches["control_repeat"])
    return {
        "seed": int(seed),
        "max_horizon": 0,
        "reference_decay_rate": REFERENCE_DECAY_RATE,
        "candidate_identity": resolved.candidate_identity,
        "pre_teacher_snapshot_digest": canonical_digest(pre_teacher),
        "branch_digests": {
            name: canonical_digest(snapshot)
            for name, snapshot in branches.items()
        },
        "b_vs_h_distinct": bool(b_vs_h["different"]),
        "b_vs_h_changed_slots": list(b_vs_h["changed_slots"]),
        "control_clean": not bool(control_repeat["different"]),
    }


def select_qualification_cohort(
    cases: Iterable[Mapping[str, Any]],
    *,
    positive_count: int,
    negative_count: int,
) -> dict[str, list[int]]:
    ordered = sorted(cases, key=lambda item: int(item["seed"]))
    positives = [
        int(item["seed"]) for item in ordered if bool(item["b_vs_h_distinct"])
    ]
    negatives = [
        int(item["seed"]) for item in ordered if not bool(item["b_vs_h_distinct"])
    ]
    if len(positives) < positive_count or len(negatives) < negative_count:
        raise ValueError(
            "qualification pool does not contain the predeclared positive/negative counts"
        )
    return {
        "positive": positives[:positive_count],
        "negative": negatives[:negative_count],
    }


def _protocol_payload(
    experiment_path: Path = Path("config/experiment_v0_1.json"),
) -> dict[str, Any]:
    """Freeze the complete Phase G protocol, not only ExperimentConfig."""
    return {
        "experiment": _load_protocol(experiment_path).to_dict(),
        "teacher_pair": [TEACHER_B, TEACHER_H],
        "qualification_horizon": 0,
        "adaptive_horizons": list(SEARCH_HORIZONS),
        "no_further_external_stimulation_after_h0": True,
    }


def _protocol_digest(
    experiment_path: Path = Path("config/experiment_v0_1.json"),
) -> str:
    return _digest(_protocol_payload(experiment_path))


def qualify_pools_h0(
    *,
    config_path: Path = Path("config/default.json"),
    experiment_path: Path = Path("config/experiment_v0_1.json"),
) -> dict[str, Any]:
    """Qualify disjoint search/held-out pools without advancing beyond h0."""
    search_cases = [
        qualify_case_h0(
            seed=seed,
            config_path=config_path,
            experiment_path=experiment_path,
        )
        for seed in SEARCH_POOL
    ]
    heldout_cases = [
        qualify_case_h0(
            seed=seed,
            config_path=config_path,
            experiment_path=experiment_path,
        )
        for seed in HELDOUT_POOL
    ]

    search_selection = select_qualification_cohort(
        search_cases,
        positive_count=SEARCH_POSITIVE_COUNT,
        negative_count=SEARCH_NEGATIVE_COUNT,
    )
    heldout_selection = select_qualification_cohort(
        heldout_cases,
        positive_count=HELDOUT_POSITIVE_COUNT,
        negative_count=HELDOUT_NEGATIVE_COUNT,
    )

    all_selected = (
        set(search_selection["positive"])
        | set(search_selection["negative"])
        | set(heldout_selection["positive"])
        | set(heldout_selection["negative"])
    )
    if all_selected & set(OLD_140_PRIMARY_SEEDS):
        raise RuntimeError("qualified Phase G cohort overlaps frozen #140 primary seeds")
    if set(SEARCH_POOL) & set(HELDOUT_POOL):
        raise RuntimeError("search and held-out qualification pools overlap")
    if any(case["max_horizon"] != 0 for case in (*search_cases, *heldout_cases)):
        raise RuntimeError("G0 qualification observed a post-h0 horizon")
    if not all(case["control_clean"] for case in (*search_cases, *heldout_cases)):
        raise RuntimeError("duplicate h0 controls diverged during qualification")

    plan = phase_g_search_plan()
    registry = build_phase_g_registry()
    objective = phase_g_objective_profile()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "issue": ISSUE,
        "baseline_sha": BASELINE_SHA,
        "baseline_tag": BASELINE_TAG,
        "learning_claim": False,
        "phase": "G0",
        "scope": "h0_qualification_only",
        "held_out_max_horizon": 0,
        "old_140_primary_seeds_excluded": list(OLD_140_PRIMARY_SEEDS),
        "search_pool": list(SEARCH_POOL),
        "heldout_pool": list(HELDOUT_POOL),
        "search_cohort": search_selection["positive"],
        "search_negative_sentinels": search_selection["negative"],
        "heldout_validation_cohort": heldout_selection["positive"],
        "heldout_negative_sentinels": heldout_selection["negative"],
        "search_plan": plan.to_dict(),
        "search_plan_digest": plan.digest,
        "registry_digest": registry.digest,
        "objective_profile": objective.to_dict(),
        "objective_profile_digest": _digest(objective.to_dict()),
        "protocol": _protocol_payload(experiment_path),
        "protocol_digest": _protocol_digest(experiment_path),
        "reference_candidate": resolve_decay_candidate(
            REFERENCE_DECAY_RATE,
            base_config=_load_base_config(config_path),
        ).candidate_identity,
        "qualification_case_digests": {
            "search": _digest(search_cases),
            "heldout": _digest(heldout_cases),
        },
    }
    payload["artifact_digest"] = _digest(payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualify", action="store_true")
    parser.add_argument("--config", type=Path, default=Path("config/default.json"))
    parser.add_argument(
        "--experiment",
        type=Path,
        default=Path("config/experiment_v0_1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/artifacts/phase_g_g0_qualification_159.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.qualify:
        print(
            json.dumps(
                {
                    "issue": ISSUE,
                    "phase": "G0",
                    "search_plan_digest": phase_g_search_plan().digest,
                    "registry_digest": build_phase_g_registry().digest,
                    "objective_profile_digest": _digest(
                        phase_g_objective_profile().to_dict()
                    ),
                    "long_horizon_search_enabled": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    artifact = qualify_pools_h0(
        config_path=args.config,
        experiment_path=args.experiment,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
