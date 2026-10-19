"""#393 O3-A: fail-closed h0-only cohort proposal (NO real-world attestation).

Source-only syntax, exclusion and role segregation. The external O3-B native
attestor must later authenticate pre-outcome h0 snapshots and history; hashes
or asserted booleans supplied by a caller are NOT proof of genuine evidence.
This module cannot enroll/execute new worlds or select a winning parameter.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from research.outer_l3_memory_search_386 import _protocol as outer_protocol
from research.outer_l3_eligible_selection_388 import EXPOSED_ORIGINAL_SEEDS

PROTOCOL_PATH = Path("research/outer_l3_h0_cohort_protocol_393.json")
STATUS = "STRUCTURALLY_WELL_FORMED_UNATTESTED_NO_EXECUTION"
_ENTRY_FIELDS = frozenset(("seed_id", "h0_generation", "h0_snapshot_sha256",
                           "h0_case_sha256", "source_sha"))
_MANIFEST_FIELDS = frozenset(("training", "validation", "additional_exposed_seeds",
                              "claimed_control_roles", "claimed_qualification_phase"))


def _is_sha(value: object, length: int) -> bool:
    return type(value) is str and len(value) == length and all(c in "0123456789abcdef" for c in value)


def load_h0_source_contract() -> dict:
    p = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    outer = outer_protocol()
    if (
        p["schema"] != "UG_OUTER_L3_O3_A_H0_COHORT_SOURCE_GATE_V1"
        or p["issue"] != 393
        or p["mode"] != "SOURCE_ONLY_UNPOPULATED_NO_SEED_APPROVAL"
        or p["exclusions"]["reserved_closed_inclusive"] != [[96, 159]]
        or tuple(p["exclusions"]["documented_exposed_seeds"]) != tuple(sorted(EXPOSED_ORIGINAL_SEEDS))
        or p["exclusions"]["exclusion_completeness_certified"] is not False
        or p["exclusions"]["further_outcome_exposure_ledger"] != "REQUIRED_BEFORE_REAL_MATERIALIZATION"
        or p["execution"]["manifest_unpopulated"] is not True
        or p["execution"]["requires_independent_attestation_in_o3b"] is not True
        or p["execution"]["no_Inner_step_in_tests"] is not True
        or p["scientific"]["learning_claim"] is not False
        or p["scientific"]["winning_candidate_selected"] is not False
        or p["control_roles"] != outer["comparison"]["matched_controls"]
        or p["roles"]["training"]["min_cases"] != outer["objective"]["minimum_evidence_cases"]
        or p["roles"]["validation"]["fully_sealed_until_training_candidate_frozen"] is not True
        or p["accepted_o2_source_main"] != outer["source_main"] and p["accepted_o2_source_main"] !=
            "e4cd5072e06236b6eed5a68fad18c0b1ae501f86"
    ):
        raise ValueError("invalid source-only Outer h0 cohort boundary")
    return p


@dataclass(frozen=True)
class ProposedH0Cohort:
    proposal_sha256: str
    training_seed_ids: tuple[int, ...]
    validation_seed_ids: tuple[int, ...]
    status: str = STATUS
    source_provenance_verified: bool = False
    h0_only_eligibility_verified: bool = False
    exposure_ledger_complete: bool = False
    actual_physics_executed: bool = False
    approved_for_outer_evaluation: bool = False
    independent_validation: bool = False
    winning_candidate_selected: bool = False
    learning_claim: bool = False


def validate_h0_cohort_proposal(manifest: dict) -> ProposedH0Cohort:
    """Only syntactic eligibility. Attestation is deliberately impossible here."""
    p = load_h0_source_contract()
    if type(manifest) is not dict or set(manifest) != _MANIFEST_FIELDS:
        raise ValueError("require an exact h0-only manifest proposal with no outcomes")
    if manifest["claimed_qualification_phase"] != "H0_ONLY_BEFORE_CANDIDATE_OUTCOMES":
        raise ValueError("post-outcome candidate selection is forbidden")
    if manifest["claimed_control_roles"] != p["control_roles"]:
        raise ValueError("missing or substituted matched controls")
    extra = manifest["additional_exposed_seeds"]
    if type(extra) is not list or any(type(x) is not int or x < 0 for x in extra):
        raise ValueError("invalid additional outcome-exposure ledger entries")
    if extra != sorted(set(extra)):
        raise ValueError("outcome exposure entries must be sorted unique")
    excluded = set(EXPOSED_ORIGINAL_SEEDS) | set(extra)
    for left, right in p["exclusions"]["reserved_closed_inclusive"]:
        excluded.update(range(left, right + 1))
    included = set()
    results = {}
    for role in ("training", "validation"):
        entries = manifest[role]
        if (type(entries) is not list
                or len(entries) < p["roles"][role]["min_cases"]
                or len(entries) > p["execution"]["max_population_slots"]):
            raise ValueError(f"missing bounded predeclared {role} cohort")
        ids = []
        for row in entries:
            if type(row) is not dict or set(row) != _ENTRY_FIELDS:
                raise ValueError("invalid h0-only row or leaked outcome/fitness metadata")
            seed, gen = row["seed_id"], row["h0_generation"]
            if type(seed) is not int or seed < 0 or type(gen) is not int or gen < 0:
                raise ValueError("invalid h0-only seed or generation")
            if seed in excluded or seed in included:
                raise ValueError("previously exposed, reserved or overlapping seed")
            if not _is_sha(row["source_sha"], 40) or row["source_sha"] != p["accepted_o2_source_main"]:
                raise ValueError("unreviewed original source SHA")
            if (not _is_sha(row["h0_snapshot_sha256"], 64)
                    or not _is_sha(row["h0_case_sha256"], 64)):
                raise ValueError("missing h0-only source/snapshot digest fields")
            included.add(seed)
            ids.append(seed)
        if ids != sorted(ids):
            raise ValueError("h0-only candidate seed IDs must be ordered, not cherry-picked")
        results[role] = tuple(ids)
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return ProposedH0Cohort(
        proposal_sha256=hashlib.sha256(payload).hexdigest(),
        training_seed_ids=results["training"],
        validation_seed_ids=results["validation"],
    )
