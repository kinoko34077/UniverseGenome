"""#388 O2-1: pure Outer-candidate to Inner physical input boundary.

This source-only adapter does not create a UniverseState, advance native physics,
allocate a seed, execute an experiment, or evaluate a fitness score.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from core.physics import PhysicsConfig
from research.outer_l3_memory_search_386 import resolve_outer_l3_candidate

FORBIDDEN_INNER_KEYS = frozenset((
    "candidate_identity", "candidate_id", "teacher", "teacher_role",
    "seed", "evidence_seed", "fitness", "objective", "rank", "search_cohort",
    "learning_claim", "source_sha", "selection_scope", "pruning_score",
))


def _canonical_sha256(data: Mapping[str, object]) -> str:
    b = json.dumps(
        dict(data), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


@dataclass(frozen=True)
class InnerPhysicsInput:
    """Value-only native physics configuration; no Outer search/teacher data."""

    fields: tuple[tuple[str, Any], ...]
    physics_sha256: str

    def __post_init__(self) -> None:
        raw = dict(self.fields)
        if len(raw) != len(self.fields):
            raise ValueError("duplicate Inner native config fields")
        if FORBIDDEN_INNER_KEYS.intersection(raw):
            raise ValueError("Outer/teacher metadata must never reach Inner")
        actual = PhysicsConfig(**raw).to_dict()
        if raw != actual or tuple(sorted(raw.items())) != self.fields:
            raise ValueError("Inner must receive a complete canonical physical config")
        if self.physics_sha256 != _canonical_sha256(actual):
            raise ValueError("Inner physics config digest mismatch")

    def to_dict(self) -> dict[str, object]:
        return dict(self.fields)

    def to_physics_config(self) -> PhysicsConfig:
        return PhysicsConfig(**self.to_dict())


@dataclass(frozen=True)
class OuterCandidateEnvelope:
    """Search identity is retained outside the clean deterministic Inner input."""

    candidate_identity: str
    active_dimensions: tuple[str, ...]
    input: InnerPhysicsInput

    def __post_init__(self) -> None:
        if not self.candidate_identity or len(self.candidate_identity) > 128:
            raise ValueError("invalid Outer candidate identity")
        if len(set(self.active_dimensions)) != len(self.active_dimensions):
            raise ValueError("duplicate Outer active dimensions")


def resolve_inner_execution_input(
    scalars: Mapping[str, int],
    rules: Mapping[str, str],
    *, base_config: PhysicsConfig,
) -> OuterCandidateEnvelope:
    """Resolve a complete registered research candidate, without constructing a world.

    Physical enablement flags and constants are explicitly passed and covered
    by the resulting SHA. Seeds, teachers, fitness, rank and provenance are
    never written to Inner input. The caller has NOT selected a winning value.
    """
    if not isinstance(base_config, PhysicsConfig):
        raise TypeError("source-bound PhysicsConfig required for Inner resolution")
    resolved, physical = resolve_outer_l3_candidate(
        scalars, rules, base_config=base_config,
    )
    data = physical.to_dict()
    if FORBIDDEN_INNER_KEYS.intersection(data):
        raise ValueError("nonphysical Outer metadata in resolved native config")
    if data["noise_rate"] != scalars["noise_rate"]:
        raise ValueError("Outer/Inner noise rate diverged")
    if data["fragmentation_rate"] != scalars["fragmentation_base_probability"]:
        raise ValueError("Outer/Inner fragmentation rate diverged")
    if data["latent_operator"] != rules["latent_operator"]:
        raise ValueError("Outer/Inner latent operator diverged")
    inner = InnerPhysicsInput(
        fields=tuple(sorted(data.items())),
        physics_sha256=_canonical_sha256(data),
    )
    return OuterCandidateEnvelope(
        candidate_identity=resolved.candidate_identity,
        active_dimensions=tuple(resolved.active_dimensions),
        input=inner,
    )
