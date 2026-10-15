"""#358: new bounded single-factor masked_xor exploratory native runner.

Never executes at import or ordinary pull-request CI. A separate reviewed
single-use Git activation marker on main and exact source/host identity are required.
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
from tests.support_r2_masked_xor_contact_354 import classify_purported_native_contacts
from tests.support_r2_masked_xor_native_observer_358 import MaskedXorNativeObserver
from research.phase_g_memory_search_159 import _load_protocol
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import (
    LocalWriteRule, RATE, HORIZONS, h0_branches, load_frozen,
)
from research.transduction_audit_120 import canonical_digest, clone_state


ISSUE = 358
SCHEMA = "UG_L3_MASKED_XOR358_AUTHENTIC_EXPOSED_PILOT_V1"
MAX_REPORT = 128 * 1024
# Internal sentinel: callers must first pass execution_gate; public branch
# entry cannot accidentally start original seed physics from a plain import.
_AUTHORIZED_ENTRY = object()


MARKER = Path("research/approvals/l3_xor_exposed_358.run")
PREFIX = "L3-XOR-358-EXPOSED-544-545-SINGLEFACTOR4-ONCE "
PROTOCOL = Path("tests/l3_xor_exposed_protocol_358.json")


def verify_study_gate(source_sha: str) -> None:
    """Fail closed before real physics; HEAD must be unique reviewed marker push."""
    import os
    import subprocess
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise PermissionError("real one-shot marker cannot be retried")
    if os.environ.get("GITHUB_EVENT_NAME") != "push" or os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise PermissionError("genuine #358 physics only on accepted main marker push")
    if len(source_sha) != 40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise PermissionError("exact source SHA required")
    if not MARKER.is_file() or not PROTOCOL.is_file():
        raise PermissionError("reviewed #358 marker/protocol missing")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (protocol["schema"] != "UG_L3_XOR358_EXPOSED_EXPLORATORY_V1"
            or protocol["owner_issue"] != 358
            or protocol["fixed_roster"] != {"positive":544, "negative":545, "teacher_b":66, "teacher_h":8}
            or protocol["treatment"]["latent_operator"] != "masked_xor"
            or protocol["treatment"]["unchanged_rotate_amount"] != 4
            or protocol["treatment"]["only_changed_config_field"] != "latent_operator"
            or protocol["actual_science_run_performed"] is not False
            or protocol["limits"]["no_retry"] is not True):
        raise PermissionError("frozen science protocol mismatch")
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], check=True, capture_output=True,
                              text=True, timeout=12).stdout.strip()
    head = git("rev-parse", "HEAD")
    parent = git("rev-parse", "HEAD^")
    if head != source_sha or MARKER.read_text(encoding="utf-8") != PREFIX + parent + "\n":
        raise PermissionError("source/marker exact reviewed commit mismatch")
    if git("diff", "--name-only", "HEAD^", "HEAD") != str(MARKER):
        raise PermissionError("marker commit unexpectedly changed science source")
    adds = git("log", "--full-history", "--format=%H", "--diff-filter=A", "--", str(MARKER)).splitlines()
    mods = git("log", "--full-history", "--format=%H", "--diff-filter=M", "--", str(MARKER)).splitlines()
    deletes = git("log", "--full-history", "--format=%H", "--diff-filter=D", "--", str(MARKER)).splitlines()
    if len(adds) != 1 or mods or deletes:
        raise PermissionError("original new #358 marker was reused/modified")
    if subprocess.run(["git","diff","--quiet","HEAD","--","tests",
                       "research/r2_write_rules_175.py","core/physics.py"],
                      check=False).returncode != 0:
        raise PermissionError("native #358 source dirty")


def candidate_config():
    reference=profile(RATE)
    changed=replace(reference,latent_operator="masked_xor")
    diff=[
        key for key in asdict(reference)
        if asdict(reference)[key]!=asdict(changed)[key]
    ]
    if diff!=["latent_operator"] or changed.rotate_amount!=reference.rotate_amount or changed.rotate_amount!=4:
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


def run_candidate_branch(seed:int,role:str,frozen:dict,started:float,
                         *, _approval_token:object|None=None) -> dict[str,Any]:
    """Only the validated guarded run may initiate original seed physics."""
    if _approval_token is not _AUTHORIZED_ENTRY:
        raise PermissionError("A2 no direct original seed execution outside accepted entry")
    initial=original_h0(seed,role,frozen)
    _,treatment=candidate_config()
    state=clone_state(initial,treatment)  # Switch ONLY AFTER source-native h0.
    assert state.config is not None and state.config.latent_operator=="masked_xor"
    before=canonical_digest(state.to_snapshot())
    exp=IOExperiment(state,experiment=_load_protocol())
    original_indices= {
        i for i,(b,h) in enumerate(zip(
            h0_branches(seed)["b"]["arrays"]["slow_trace"],
            h0_branches(seed)["h"]["arrays"]["slow_trace"],
        )) if b!=h
    }
    local_write=LocalWriteRule("unit_add",original_indices)
    observer=MaskedXorNativeObserver(state,event_limit=200000)
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
    # Independently run original native source from the SAME canonical h0,
    # never attaching the passive recorder. Compare all complete snapshots.
    unobserved=clone_state(initial,treatment)
    reference_exp=IOExperiment(unobserved,experiment=_load_protocol())
    reference_rule=LocalWriteRule("unit_add",original_indices)
    control_hashes={"0":canonical_digest(unobserved.to_snapshot())}
    with reference_rule.attach():
        for horizon in range(1,1001):
            reference_exp._advance(())
            if horizon in HORIZONS[1:]:
                control_hashes[str(horizon)]=canonical_digest(unobserved.to_snapshot())
            if horizon%25==0:
                check_budget(started)
    if control_hashes!=checkpoints:
        raise ValueError("INVALID_INSTRUMENTATION: authentic unobserved physical source diverged")
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
        "uninstrumented_full_state_parity":True,
        "native_selected_examples_first_last":(
            observer.events[:2]+observer.events[-2:] if observer.events else []
        ),
        "_actual_native_events":observer.events,
    }


def run_exposed_study(*, source_sha: str) -> dict[str, Any]:
    verify_study_gate(source_sha)
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
            data[str(seed)][role]=run_candidate_branch(seed,role,frozen,started,
                                                       _approval_token=_AUTHORIZED_ENTRY)
    b_sham=run_candidate_branch(544,"b",frozen,started,
                                _approval_token=_AUTHORIZED_ENTRY)
    if b_sham!=data["544"]["b"]:
        raise ValueError("positive same-teacher B/B native sham non-deterministic")
    negative=data["545"]
    if ({k:v for k,v in negative["b"].items() if k!="role"}
            !={k:v for k,v in negative["h"].items() if k!="role"}):
        raise ValueError("negative original h0-identical B/H treatment diverged")
    positive=classify_purported_native_contacts(
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
            "baseline_operator":"masked_copy","treatment_operator":"masked_xor",
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
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if not args.execute:
        raise PermissionError("native #358 execution requires explicit reviewed one-shot marker")
    value=run_exposed_study(source_sha=args.source_sha)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\\n")


if __name__=="__main__":
    main()
