"""#334 — read-only validator for a NON-EXECUTABLE A2 rotate_copy pilot draft.

Never calls create_universe, teacher_step, native step, Actions, or any seed
qualification. This file cannot authorize or execute an experiment.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
import json

from core.physics import LATENT_OPERATORS
from research.a1_exposed_reader_pilot_317 import (
    R2_ORIGINAL_SOURCE, R2_FROZEN_DIGEST,
)
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import RATE, load_frozen

MANIFEST = Path("research/protocols/a2_rotate_copy_preflight_334.json")
SCHEMA = "UG_A2_ROTATE_COPY_RESEARCH_ONLY_PREFLIGHT_DRAFT_V1"


def validate_nonexecuting_draft(plan: dict) -> dict:
    """Fail closed on changes to candidate, native science or HOLD boundary."""
    if (plan.get("schema") != SCHEMA
            or plan.get("issue") != 334
            or plan.get("state") != "DESIGN_ONLY_NOT_APPROVED_TO_RUN"):
        raise ValueError("A2 design status or schema drift")
    if plan["original_r2_physics_source"] != R2_ORIGINAL_SOURCE:
        raise ValueError("A2 original R2 source SHA changed")
    frozen = load_frozen()  # Reads accepted immutable manifest only.
    if (plan["original_r2_frozen_manifest_digest"] != R2_FROZEN_DIGEST
            or frozen["digest"] != R2_FROZEN_DIGEST
            or plan["original_exposed_case_action_run"] != 37950076024):
        raise ValueError("A2 original R2 frozen manifest/source evidence drift")

    c=plan["candidate"]
    if (c["original_operator"]!="masked_copy"
            or c["hypothetical_operator"]!="rotate_copy"
            or c["rotate_amount"]!=4
            or c["only_permitted_post_h0_config_change"]!="latent_operator"
            or c["h0_setup"]!="original_masked_copy_only_prior_to_h0_same_original_teacher_scheduling"
            or c["operator_activation"]!="clone_after_original_h0_only"
            or c["source_code_change"] or c["production_default_change"]):
        raise ValueError("A2 single post-h0 physics factor or source isolation changed")
    if c["hypothetical_operator"] not in LATENT_OPERATORS:
        raise ValueError("candidate operator is not a native approved source mode")
    reference=profile(RATE)
    if reference.latent_operator!="masked_copy" or reference.rotate_amount!=4:
        raise ValueError("original research reference physics changed")
    treatment=replace(reference,latent_operator="rotate_copy")
    original_dict=asdict(reference)
    treatment_dict=asdict(treatment)
    changed=[k for k in original_dict if original_dict[k]!=treatment_dict[k]]
    if changed!=["latent_operator"]:
        raise ValueError("candidate must change only one original physics parameter")

    case=plan["exposed_exploratory_only"]
    if (case["positive_seed"]!=544 or case["negative_seed"]!=545
            or case["teacher_values"]!={"b":66,"h":8}
            or case["writer"]!="research_only_unit_add"
            or case["trace_decay_rate"]!=RATE
            or case["h0_native_generation"]!=13
            or case["physical_steps"]!=1000
            or case["checkpoints"]!=[0,1,10,100,250,500,1000]
            or case["teacher_after_h0"]
            or case["candidate_post_h0_old_baseline_checkpoint_parity_expected"]
            or not case["baseline_original_masked_copy_golden_required"]
            or not case["negative_BH_identical_required"]):
        raise ValueError("historical h0/teacher/negative/snapshot controls drift")
    if 544 not in frozen["positive_seeds"] or 545 not in frozen["negative_seeds"]:
        raise ValueError("original h0-only R2 role qualification changed")
    h544=frozen["h0_evidence"]["544"]
    h545=frozen["h0_evidence"]["545"]
    if (not h544["h0_trace_distinct"]
            or h544["b_digest"]==h544["h_digest"]
            or h545["h0_trace_distinct"]
            or not h545["h0_global_equal"]
            or h545["b_digest"]!=h545["h_digest"]):
        raise ValueError("original B/H positive and sentinel h0 SHA control mismatch")
    if case["control_no_teacher"]!="separate canonical original control h0; never require it to equal B/H h0":
        raise ValueError("original no-teacher h0 must be independent reference")

    seeds=plan["seed_partition"]
    if (seeds["historic_old_phaseH_reserved"]!=[96,159]
            or seeds["historic_R1_pool"]!=[160,543]
            or seeds["historic_R2_pool"]!=[544,1023]
            or seeds["exploratory_this_draft"]!=[544,545]
            or seeds["independent_R3_floor"]!=1024
            or seeds["independent_R3_seeds_to_be_selected_by_this_draft"]!=[]
            or seeds["heldout_consumed"]):
        raise ValueError("A2 historical and protected seed partition mismatch")
    if set(seeds["exploratory_this_draft"]) & set(range(96,160)):
        raise ValueError("A2 protected Phase H seed exposure")
    if any(s>=1024 for s in seeds["exploratory_this_draft"]):
        raise ValueError("A2 independent R3 pool cannot be consumed")

    limits=plan["bounds"]
    if (limits["max_rss_mib"]>1536
            or limits["max_host_wall_seconds"]>900
            or limits["max_json_result_bytes"]>131072
            or limits["max_physical_steps_after_h0"]!=1000
            or limits["seed_fallback"]
            or limits["posthoc_tuning"]):
        raise ValueError("A2 original planned science budget or fixed-horizon drift")

    gate=plan["execution_permission"]
    allowed={
        "approval_state":"HOLD",
        "can_run_actions":False,"can_change_physics":False,
        "can_change_defaults":False,"can_consume_new_seed":False,
        "can_consume_heldout":False,"can_promote_R3":False,
        "learning_claim":False,
    }
    if gate!=allowed:
        raise ValueError("A2 unapproved executable/study promotion attempted")
    if (plan["record_policy"]["destination"]!=
            "kinoko34077/UniverseGenome Git repository research/artifacts; never Google Drive"):
        raise ValueError("A2 evidence destination must remain repository native")
    if not plan["gates"]["validity"] or not plan["gates"]["primary_observation"]:
        raise ValueError("A2 scientific decision gates cannot be blank")
    return {
        "status":"VALID_DRAFT_ONLY_NO_EXECUTION",
        "schema":SCHEMA,
        "original_r2_digest":R2_FROZEN_DIGEST,
        "baseline_operator":"masked_copy",
        "candidate_operator":"rotate_copy",
        "changed_fields":changed,
        "previously_outcome_exposed_only":[544,545],
        "learning_claim":False,
        "can_run_actions":False,
    }


def validate_saved_draft(path: Path = MANIFEST) -> dict:
    return validate_nonexecuting_draft(json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    print(json.dumps(validate_saved_draft(),sort_keys=True))
