"""A2 E1b #336: exact research-only original R2 pilot runner, execution HARD-HOLD.

This is an inert prepared runner for a FUTURE separately accepted rotate_copy
native treatment. Even with --execute it refuses the current source-authoritative
protocol, which has can_run_actions=false. No CI or import performs physics.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
import platform
from pathlib import Path
import sys
import time
from typing import Any

from core.experiment import IOExperiment
from research.a1_exposed_reader_pilot_317 import (
    GOLDEN, R2_FROZEN_DIGEST, SEEDS, source_event_digest,
    sampled_max_rss_mib, check_budget,
    single_pass as old_masked_copy_reference,
)
from research.a2_matched_recipient_contract_336 import (
    compare_native_contact_witnesses,
)
from research.a2_passive_native_recipient_observer_336 import (
    PassiveNativeRecipientObserver,
)
from research.a2_protocol_preflight_334 import (
    MANIFEST, validate_nonexecuting_draft,
)
from research.phase_g_memory_search_159 import _load_protocol
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import (
    LocalWriteRule, RATE, HORIZONS, h0_branches, load_frozen,
)
from research.transduction_audit_120 import canonical_digest, clone_state


ISSUE = 336
SCHEMA = "UG_A2_RESEARCH_ONLY_ROTATE_COPY_EXPOSED_PILOT_V1"
MAX_REPORT = 128 * 1024


def execution_gate(*, plan:dict, named_approval:bool, source_sha:str) -> None:
    """Fail CLOSED *before any original seed h0 or source-native world step*.

    A later independently accepted code+protocol update is required to change
    the present authorization. Command-line flags cannot override it.
    """
    if not named_approval:
        raise PermissionError("A2 real native treatment requires named approval")
    if len(source_sha)!=40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise PermissionError("exact reviewed runner source commit SHA required")
    # Existing accepted #334 machine validator is intentionally nonexecutable.
    # It rejects attempts to mutate HOLD flags; no execution path can bypass it.
    validate_nonexecuting_draft(plan)
    authorization=plan["execution_permission"]
    if (plan["state"]!="ACCEPTED_EXACT_RUNNABLE"
            or authorization["approval_state"]!="ACCEPTED"
            or not authorization["can_run_actions"]):
        raise PermissionError("A2 original research protocol remains HOLD")


def candidate_config():
    reference=profile(RATE)
    changed=replace(reference,latent_operator="rotate_copy")
    diff=[
        key for key in asdict(reference)
        if asdict(reference)[key]!=asdict(changed)[key]
    ]
    if diff!=["latent_operator"] or changed.rotate_amount!=4:
        raise ValueError("only post-h0 native latent_operator change permitted")
    return reference,changed


def original_h0(seed:int, role:str, frozen:dict) -> dict:
    if seed not in SEEDS or role not in ("b","h","control"):
        raise ValueError("new seed/unknown h0 role prohibited")
    if seed not in frozen["positive_seeds"] and seed not in frozen["negative_seeds"]:
        raise ValueError("unqualified R2 h0 source")
    pair=h0_branches(seed)
    for label in ("b","h","control"):
        actual=canonical_digest(pair[label])
        expected=frozen["h0_evidence"][str(seed)][label+"_digest"]
        if actual!=expected:
            raise ValueError("original source h0 SHA mismatch")
    if seed==545 and pair["b"]!=pair["h"]:
        raise ValueError("negative original source h0 B/H unexpectedly differs")
    return pair[role]


def run_candidate_branch(seed:int,role:str,frozen:dict,started:float) -> dict[str,Any]:
    """Only reachable after external execution_gate acceptance, NEVER in CI."""
    initial=original_h0(seed,role,frozen)
    _,treatment=candidate_config()
    state=clone_state(initial,treatment)  # Switch ONLY AFTER source-native h0.
    assert state.config is not None and state.config.latent_operator=="rotate_copy"
    before=canonical_digest(state.to_snapshot())
    exp=IOExperiment(state,experiment=_load_protocol())
    original_indices= {
        i for i,(b,h) in enumerate(zip(
            h0_branches(seed)["b"]["arrays"]["slow_trace"],
            h0_branches(seed)["h"]["arrays"]["slow_trace"],
        )) if b!=h
    }
    local_write=LocalWriteRule("unit_add",original_indices)
    observer=PassiveNativeRecipientObserver(state,event_limit=200000)
    checkpoints={"0":before}
    distribution={}
    metrics={"native_transmissions":0,"native_fusions":0,"native_fragmentations":0}
    with local_write.attach(),observer.attach():
        for horizon in range(1,1001):
            metric=exp._advance(())
            metrics["native_transmissions"]+=metric.latent_transmission_count
            metrics["native_fusions"]+=metric.fusion_count
            metrics["native_fragmentations"]+=metric.fragmentation_count
            if horizon in HORIZONS[1:]:
                checkpoints[str(horizon)]=canonical_digest(state.to_snapshot())
                active=state.active_slots()
                distribution[str(horizon)]={
                    "active_cells":len(active),
                    "distinct_latent_words":len({int(state.latent[i]) for i in active}),
                }
            if horizon%25==0:
                check_budget(started)
    if len(checkpoints)!=len(HORIZONS):
        raise ValueError("missing full predeclared original post-h0 horizons")
    check_budget(started)
    return {
        "seed":seed,"role":role,
        "original_h0_sha256":frozen["h0_evidence"][str(seed)][role+"_digest"],
        "candidate_start_sha256":before,
        "checkpoints":checkpoints,"distribution":distribution,
        "metrics":metrics,"native_selected_events":len(observer.events),
        "native_selected_event_sha256":source_event_digest(observer.events),
        "native_free_event_sha256":source_event_digest(observer.prior.free_events),
        "native_free_count":len(observer.prior.free_events),
        "_actual_native_events":observer.events,
    }


def run_accepted_research_only(*, plan:dict, named_approval:bool,
                               source_sha:str) -> dict[str,Any]:
    execution_gate(plan=plan,named_approval=named_approval,source_sha=source_sha)
    frozen=load_frozen()
    if frozen["digest"]!=R2_FROZEN_DIGEST:
        raise ValueError("original source R2 predeclared manifest changed")
    candidate_config()
    started=time.perf_counter()
    baseline=old_masked_copy_reference(frozen,started)
    # Old authoritative R2 checkpoint SHA must be identical under original mode.
    for seed in SEEDS:
        for role in ("b","h"):
            if baseline[str(seed)][role]["checkpoint_digests"]!=GOLDEN[seed][role]:
                raise ValueError("R2 original masked_copy reference drift")
    data={}
    for seed,roles in ((544,("b","h","control")),(545,("b","h"))):
        data[str(seed)]={}
        for role in roles:
            data[str(seed)][role]=run_candidate_branch(seed,role,frozen,started)
    b_sham=run_candidate_branch(544,"b",frozen,started)
    if b_sham!=data["544"]["b"]:
        raise ValueError("positive same-teacher B/B native sham non-deterministic")
    negative=data["545"]
    if negative["b"]!=negative["h"]:
        raise ValueError("negative original h0-identical B/H treatment diverged")
    positive=compare_native_contact_witnesses(
        data["544"]["b"]["_actual_native_events"],
        data["544"]["h"]["_actual_native_events"],
    )
    for group in data.values():
        for record in group.values():
            del record["_actual_native_events"]
    result={
        "schema":SCHEMA,"issue":ISSUE,"runner_source_sha":source_sha,
        "old_original_R2_manifest_digest":R2_FROZEN_DIGEST,
        "conditions":{
            "positive_exposed_seed":544,"negative_exposed_seed":545,
            "teacher_B_H":[66,8],"source_native_h0_generation":13,
            "writer":"research_only_unit_add","trace_decay_rate":RATE,
            "post_h0_native_steps":1000,
            "baseline_operator":"masked_copy","treatment_operator":"rotate_copy",
            "rotate_amount":4,"only_physical_config_delta":"latent_operator",
            "checkpoints":list(HORIZONS),
        },
        "data":data,"positive_native_paired_read_contrast":positive,
        "original_masked_copy_golden_parity":True,
        "negative_BH_full_equality":True,"positive_BB_sham_full_equality":True,
        "independent_confirmation":False,"learning_claim":False,
        "environment":{
            "implementation":sys.implementation.name,
            "python":platform.python_version(),
            "system":platform.platform(),"machine":platform.machine(),
            "rss_mib":sampled_max_rss_mib(),
            "wall_seconds":round(time.perf_counter()-started,3),
        },
    }
    if len(json.dumps(result,sort_keys=True,separators=(",",":")).encode())>MAX_REPORT:
        raise ValueError("A2 original compact science report exceeds 128KiB")
    check_budget(started)
    return result


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    plan=json.loads(MANIFEST.read_text(encoding="utf-8"))
    # Always deny when --execute omitted; current accepted manifest still
    # denies even when --execute is supplied. Never auto-launch from CI.
    value=run_accepted_research_only(
        plan=plan,named_approval=args.execute,source_sha=args.source_sha,
    )
    if args.output is None:
        raise ValueError("explicit Git-archivable local output path required")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n")


if __name__=="__main__":
    main()
