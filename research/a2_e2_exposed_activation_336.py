"""E2 #336 consent-scoped immutable exposed 544/545 activation checks.

Never launches native experiments here. Existence of a single exact reviewed
Git activation marker is required in addition to the frozen single-candidate
protocol, authenticated named consent and exact Actions source commit.
"""
from __future__ import annotations
import json
from pathlib import Path

from research.a2_protocol_preflight_334 import (
    MANIFEST as ORIGINAL_DRAFT, validate_nonexecuting_draft,
)
from research.a1_exposed_reader_pilot_317 import (
    R2_FROZEN_DIGEST, R2_ORIGINAL_SOURCE,
)
from research.r2_write_rules_175 import load_frozen

PROTOCOL=Path("research/protocols/a2_e2_exposed_rotate_336.json")
SCHEMA="UG_A2_E2_EXPOSED_ROTATE_NATIVE_PROTOCOL_V1"


def verify_source_locked_protocol(source:dict) -> dict:
    """Read-only static prefreeze check, no activation or seed qualification."""
    if source.get("schema")!=SCHEMA or source.get("owner_issue")!=336:
        raise ValueError("invalid E2 protocol schema/owner")
    if source.get("status")!="APPROVED_SCOPED_EXPOSED_ONLY_PENDING_CODE_REVIEW_AND_ACTIVATION":
        raise ValueError("unreviewed E2 scientific protocol state")
    if source["accepted_baseline_main_sha"]!="710b906d5fd5bf800912abcb5e282e5d0f13068b":
        raise ValueError("pre-outcome source baseline replaced")
    if (source["original_R2_source_sha"]!=R2_ORIGINAL_SOURCE
        or source["original_R2_manifest_digest"]!=R2_FROZEN_DIGEST
        or source["original_R2_run_id"]!=37950076024):
        raise ValueError("original R2 evidence replaced")
    original=json.loads(ORIGINAL_DRAFT.read_text(encoding="utf-8"))
    validate_nonexecuting_draft(original)  # Still permanently HOLD.
    frozen=load_frozen()
    if frozen["digest"]!=R2_FROZEN_DIGEST:
        raise ValueError("original R2 qualified manifest changed")
    a=source["authorization"]
    if not (a["consent_scope"]==
       "original already-exposed seed544/545 h0 B/H plus fixed B/B and no-teacher control, original native rotate_copy(4) after h0 for exactly 1000 generations"
       and all(a[k] for k in ("forbid_new_seed","forbid_holdout","forbid_production_default_change","forbid_candidate_sweep"))
       and a["learning_claim"] is False):
        raise ValueError("scoped named intervention consent was expanded")
    cohorts=source["cohorts"]
    if (cohorts["positive_exposed_seed"]!=544 or cohorts["negative_exposed_seed"]!=545
        or cohorts["teacher_values"]!={"b":66,"h":8,"control":None}
        or cohorts["original_h0_generation"]!=13
        or cohorts["historical_R2_seed_window"]!=[544,1023]
        or cohorts["independent_R3_min_seed"]!=1024
        or cohorts["old_phaseH_reserved"]!=[96,159]
        or cohorts["new_qualification_seed_count"]!=0
        or cohorts["new_heldout_consumed"] is not False):
        raise ValueError("E2 exposed roster or disjoint seed guard changed")
    if 544 not in frozen["positive_seeds"] or 545 not in frozen["negative_seeds"]:
        raise ValueError("old R2 seed role changed")
    t=source["treatment"]
    if (t["original_h0_operator"]!="masked_copy"
        or t["candidate_operator"]!="rotate_copy"
        or t["candidate_rotate_amount"]!=4
        or t["only_field_changed_after_h0"]!="latent_operator"
        or t["post_h0_teacher_events"]!=0
        or t["original_writer"]!="unit_add"
        or t["trace_decay_rate"]!=256
        or t["steps_per_branch"]!=1000
        or t["snapshot_horizons"]!=[0,1,10,100,250,500,1000]):
        raise ValueError("E2 native candidate single factor or horizon changed")
    c=source["comparison"]
    required=("original_baseline_all_six_golden_required",
        "positive_B_H_matching_requires_same_nontrace_physics",
        "negative_545_B_H_full_equality_required",
        "positive_544_B_B_full_equality_required",
        "distinct_control_h0_not_misreported_as_identical_sham",
        "instrumented_uninstrumented_full_state_required",
        "deterministic_repeat_required",
        "no_future_masks_reused_from_original",
        "empty_contact_denominators_must_be_reported")
    if any(c.get(k) is not True for k in required):
        raise ValueError("E2 predeclared true physical negative/validity gate altered")
    b=source["budget"]
    if (b["max_total_wall_seconds_per_host"]>900 or b["max_rss_mib"]>1536
        or b["max_per_branch_native_events"]>200000
        or b["max_report_bytes"]>131072
        or b["no_seed_fallback"] is not True
        or b["no_parameter_tuning_after_first_outcome"] is not True):
        raise ValueError("E2 immutable resource/scoring bound expanded")
    d=source["decision"]
    if (d["valid_zero"]!="NEGATIVE_NO_MATCHED_RECIPIENT_EFFECT"
        or d["valid_transient"]!="TRANSIENT_PHYSICAL_EFFECT_NOT_L3"
        or d["valid_persistent"]!="OUTCOME_EXPOSED_RETENTION_CANDIDATE_NOT_INDEPENDENT_L3"
        or d["invalid"]!="NOT_EVALUABLE_NO_POSTHOC_SEED_REPLACEMENT"
        or d["independent_learning_claim_allowed"] is not False):
        raise ValueError("E2 scientific outcome taxonomy changed")
    activation=source["activation"]
    if (activation["marker_path"]!="research/approvals/a2_e2_336.run"
        or activation["marker_exact_text"]!="A2-E2-336-EXPOSED-544-545-ROTATE4-ONCE\n"
        or activation["separate_reviewed_marker_pr_required"] is not True
        or activation["user_approval_recorded"] is not True
        or activation["actual_dispatched"] is not False):
        raise ValueError("E2 activation contract changed")
    return {"valid_source_only":True,"marker_path":activation["marker_path"],
            "marker_bytes":activation["marker_exact_text"].encode("ascii"),
            "science_independent":False,"learning_claim":False}


def verify_activated_exposed_only(*, exact_source_sha:str) -> dict:
    """Fail CLOSED before native h0 unless activation is in reviewed Git."""
    if (len(exact_source_sha)!=40 or
        any(c not in "0123456789abcdef" for c in exact_source_sha)):
        raise PermissionError("exact reviewed source SHA required")
    manifest=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    d=verify_source_locked_protocol(manifest)
    activation=Path(d["marker_path"])
    if not activation.is_file() or activation.read_bytes()!=d["marker_bytes"]:
        raise PermissionError("E2 physical study has not passed separate marker PR")
    return {"status":"APPROVED_EXPOSED_ONLY_BY_GIT_ACTIVATION",
            "exact_source_sha":exact_source_sha,
            "original_h0_seed_roster":[544,545],
            "independent_heldout_consumed":False,
            "learning_claim":False}


if __name__=="__main__":
    print(json.dumps(verify_source_locked_protocol(
        json.loads(PROTOCOL.read_text(encoding="utf-8"))
    ),default=lambda x:x.decode("ascii") if isinstance(x,bytes) else x,
      sort_keys=True))
