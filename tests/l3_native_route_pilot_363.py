"""#363 E0: distinct bounded genuine native contact-path attribution experiment.

This is not a replay of the old one-use #358 Action. Its original report is a
frozen golden witness; this E0 must receive its OWN reviewed main marker push.
Never executes original seed physics on import, unit test, or pull request.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
import hashlib
import json
import os
import platform
from pathlib import Path
import resource
import subprocess
import sys
import time

from core.experiment import IOExperiment
from core.state import Lifecycle
from research.a1_exposed_reader_pilot_317 import (
    GOLDEN, R2_FROZEN_DIGEST, source_event_digest,
    single_pass as old_masked_copy_reference,
)
from research.phase_g_memory_search_159 import _load_protocol
from research.r2_write_rules_175 import LocalWriteRule, RATE, HORIZONS, h0_branches, load_frozen
from research.transduction_audit_120 import canonical_digest, clone_state
from tests.l3_xor_exposed_pilot_358 import candidate_config
from tests.support_r2_masked_xor_native_observer_358 import MaskedXorNativeObserver
from tests.support_l3_native_route_363 import classify_route

MARKER = Path("research/approvals/l3_route_e0_363.run")
PROTOCOL = Path("tests/l3_native_route_protocol_363.json")
PREFIX = "L3-ROUTE-E0-363-SOURCE-NATIVE-ONE-SHOT "
OLD_REPORT = Path("research/artifacts/l3_xor358_original_544_545_run38667491457.json.base64")
OLD_RAW_SHA = "f9ff71a0ef14c75fc37f021d29e983efbb1cb4e3b2d7eed6451403462907999f"
ISSUE = 363
SCHEMA = "UG_L3_363_GENUINE_NATIVE_ROUTE_E0_V1"
_AUTHORIZED = object()


def exact_marker_gate(source_sha: str) -> None:
    if (os.environ.get("GITHUB_EVENT_NAME") != "push"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise PermissionError("single reviewed main push only, no retry")
    if (len(source_sha) != 40 or not all(ch in "0123456789abcdef" for ch in source_sha)
            or not MARKER.is_file() or not PROTOCOL.is_file()):
        raise PermissionError("missing exact source/marker/study protocol")
    spec = json.loads(PROTOCOL.read_text())
    if (spec["schema"] != "UG_L3_NATIVE_ROUTE_E0_363_FROZEN_V1"
            or spec["owner_issue"] != 363
            or spec["experimental_controls"]["source_positive_seed"] != 544
            or spec["experimental_controls"]["source_negative_seed"] != 545
            or spec["experimental_controls"]["post_h0_operator"] != "masked_xor"
            or spec["experimental_controls"]["rotate_amount_unchanged"] != 4
            or spec["actual_new_native_run_started"] is not False
            or spec["approval_to_run"] is not False
            or spec["limits"]["no_retry"] is not True):
        raise PermissionError("new E0 exact frozen design mismatch")
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], capture_output=True, check=True, text=True, timeout=12,
        ).stdout.strip()
    head, parent = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^")
    if head != source_sha or MARKER.read_text() != PREFIX + parent + "\n":
        raise PermissionError("marker does not name exact reviewed parent source")
    if git("diff", "--name-only", "HEAD^", "HEAD") != str(MARKER):
        raise PermissionError("new marker activation commit must change only one new file")
    adds = git("log", "--full-history", "--format=%H", "--diff-filter=A", "--", str(MARKER)).splitlines()
    mods = git("log", "--full-history", "--format=%H", "--diff-filter=M", "--", str(MARKER)).splitlines()
    deleted = git("log", "--full-history", "--format=%H", "--diff-filter=D", "--", str(MARKER)).splitlines()
    if len(adds) != 1 or mods or deleted:
        raise PermissionError("source-native marker was already used/modified")
    if subprocess.run(["git","diff","--quiet","HEAD"],check=False).returncode != 0:
        raise PermissionError("dirty source checkout")


def budget(start: float) -> None:
    if time.perf_counter() - start > 900:
        raise TimeoutError("new native route E0 entire host budget")
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 > 1536:
        raise MemoryError("new native E0 RSS >1536 MiB")


def original_report() -> dict:
    raw = base64.b64decode(OLD_REPORT.read_text().strip(), validate=True)
    if hashlib.sha256(raw).hexdigest() != OLD_RAW_SHA:
        raise ValueError("old independently archived genuine one-shot raw SHA changed")
    obj = json.loads(raw)
    if obj["schema"] != "UG_L3_MASKED_XOR358_AUTHENTIC_EXPOSED_PILOT_V1":
        raise ValueError("old native archive schema changed")
    if (obj["original_masked_copy_golden_parity"] is not True
            or obj["negative_BH_full_equality"] is not True
            or obj["positive_BB_sham_full_equality"] is not True
            or obj["native_observer_attached_and_full_state_parity"] is not True):
        raise ValueError("old original source-native controls invalid")
    return obj


def trace_carrier_slots(snapshot_b: dict, snapshot_h: dict) -> set[int]:
    return {
        i for i,(b,h) in enumerate(zip(
            snapshot_b["arrays"]["slow_trace"], snapshot_h["arrays"]["slow_trace"],
        )) if b != h
    }


def run_branch(seed: int, role: str, frozen: dict, old: dict, start: float,
               *, _token: object | None=None):
    if _token is not _AUTHORIZED:
        raise PermissionError("real seed run not authorized outside E0 marker gate")
    if seed not in (544,545) or role not in ("b","h","control"):
        raise ValueError("unknown source R2 h0 seed/teacher role")
    snapshots = h0_branches(seed)
    for r in ("b","h","control"):
        if canonical_digest(snapshots[r]) != frozen["h0_evidence"][str(seed)][r+"_digest"]:
            raise ValueError("source h0 original frozen digest mismatch")
    carrier = trace_carrier_slots(snapshots["b"],snapshots["h"])
    if bool(carrier) != (seed == 544):
        raise ValueError("native original h0 teacher-specific carrier mismatch")
    reference,treatment=candidate_config()
    diffs=[k for k,v in asdict(reference).items() if asdict(treatment)[k]!=v]
    if diffs!=["latent_operator"] or treatment.rotate_amount != 4:
        raise ValueError("wrong one-factor new E0 operator")
    init=snapshots[role]
    state=clone_state(init,treatment)
    exp=IOExperiment(state,experiment=_load_protocol())
    writer=LocalWriteRule("unit_add",carrier)
    obs=MaskedXorNativeObserver(state,event_limit=200000)
    checkpoints={"0":canonical_digest(state.to_snapshot())}
    snapshot_traces={"0":list(map(int,state.slow_trace))}
    snapshot_latents={"0":list(map(int,state.latent))}
    metrics={"transmissions":0,"free_events":0,"native_fusions":0,"fragmentations":0}
    with writer.attach(),obs.attach():
        for i in range(1,1001):
            m=exp._advance(())
            metrics["transmissions"]+=m.latent_transmission_count
            metrics["native_fusions"]+=m.fusion_count
            metrics["fragmentations"]+=m.fragmentation_count
            if i in HORIZONS[1:]:
                key=str(i)
                checkpoints[key]=canonical_digest(state.to_snapshot())
                snapshot_traces[key]=list(map(int,state.slow_trace))
                snapshot_latents[key]=list(map(int,state.latent))
            if i%25==0: budget(start)
    budget(start)
    if len(obs.events)>200000:
        raise ValueError("source native selected contact cap reached")
    metrics["free_events"]=len(obs.prior.free_events)
    observed_events=source_event_digest(obs.events)
    old_branch=old["data"][str(seed)][role]
    if (checkpoints!=old_branch["checkpoints"]
            or observed_events!=old_branch["native_selected_event_sha256"]
            or source_event_digest(obs.prior.free_events)!=old_branch["native_free_event_sha256"]):
        raise ValueError("new E0 observational intervention altered frozen authentic #358 native trajectory")
    # Unobserved new physics from identical frozen h0; full-authoritative parity.
    bare=clone_state(init,treatment)
    unobserved=IOExperiment(bare,experiment=_load_protocol())
    bare_writer=LocalWriteRule("unit_add",carrier)
    bare_digests={"0":canonical_digest(bare.to_snapshot())}
    with bare_writer.attach():
        for i in range(1,1001):
            unobserved._advance(())
            if i in HORIZONS[1:]:
                bare_digests[str(i)]=canonical_digest(bare.to_snapshot())
            if i%25==0: budget(start)
    if bare_digests!=checkpoints:
        raise ValueError("E0 native observer changed physical trajectory")
    return {
        "summary":{
            "seed":seed,"role":role,"h0_digest":frozen["h0_evidence"][str(seed)][role+"_digest"],
            "checkpoints":checkpoints,
            "selected_directed_contact_count":len(obs.events),
            "selected_events_sha256":observed_events,
            "free_events_sha256":source_event_digest(obs.prior.free_events),
            "source_h0_trace_carrier_slots":sorted(carrier),
            "metrics":metrics,
            "genuine_uninstrumented_parity":True,
            "exact_old_358_native_trajectory_parity":True,
        },
        "events":obs.events,"trace":snapshot_traces,"latent":snapshot_latents,
    }


def study(*,source_sha:str) -> dict:
    exact_marker_gate(source_sha)
    t0=time.perf_counter()
    old=original_report()
    frozen=load_frozen()
    if frozen["digest"]!=R2_FROZEN_DIGEST:
        raise ValueError("original qualified R2 manifest changed")
    baseline=old_masked_copy_reference(frozen,t0)
    for seed in (544,545):
        for role in ("b","h"):
            if baseline[str(seed)][role]["checkpoint_digests"]!=GOLDEN[seed][role]:
                raise ValueError("original masked_copy physics golden parity failed")
    groups={}
    for seed,roles in ((544,("b","h","control")),(545,("b","h"))):
        groups[str(seed)]={}
        for role in roles:
            groups[str(seed)][role]=run_branch(seed,role,frozen,old,t0,_token=_AUTHORIZED)
    repeat=run_branch(544,"b",frozen,old,t0,_token=_AUTHORIZED)
    if repeat["summary"]!=groups["544"]["b"]["summary"]:
        raise ValueError("same B native repeat invalid")
    if (groups["545"]["b"]["summary"]["checkpoints"] !=
            groups["545"]["h"]["summary"]["checkpoints"]):
        raise ValueError("negative original B/H full state diverged")
    if (groups["544"]["h"]["summary"]["checkpoints"] !=
            groups["544"]["control"]["summary"]["checkpoints"]):
        raise ValueError("H must equal no-teacher full-state controls at all horizons")
    classified={}
    checkpoint_diffs={}
    for seed in (544,545):
        group=groups[str(seed)]
        carriers=set(group["b"]["summary"]["source_h0_trace_carrier_slots"])
        classified[str(seed)]=classify_route(
            group["b"]["events"],group["h"]["events"],initial_trace_carrier_slots=carriers)
        checkpoint_diffs[str(seed)]={}
        for k in map(str,HORIZONS):
            t1,t2=group["b"]["trace"][k],group["h"]["trace"][k]
            l1,l2=group["b"]["latent"][k],group["h"]["latent"][k]
            checkpoint_diffs[str(seed)][k]={
                "trace_diff_slots":sum(a!=b for a,b in zip(t1,t2)),
                "latent_diff_slots":sum(a!=b for a,b in zip(l1,l2)),
            }
        if seed==545 and (classified["545"]["counts"].get("source_trace_delta_all_matched",0)
                or classified["545"]["counts"].get("recipient_after_delta_all_matched",0)):
            raise ValueError("negative sentinel native stage divergence")
    result={
        "schema":SCHEMA,"issue":ISSUE,"source_sha":source_sha,
        "original_authentic_raw_sha256":OLD_RAW_SHA,
        "classification":classified,
        "checkpoint_BH_differences":checkpoint_diffs,
        "branch_summaries":{
            seed:{role:d["summary"] for role,d in group.items()}
            for seed,group in groups.items()
        },
        "science_scope":"EXPLORATORY_REAL_NATIVE_CONTACT_STAGE_ATTRIBUTION_NOT_CAUSAL_CONFIRMED",
        "old_source_golden_pass":True,"controls_pass":True,
        "genuine_native_observed_unobserved_parity":True,
        "independent_confirmation":False,"learning_claim":False,
        "environment":{
            "wall_seconds":round(time.perf_counter()-t0,3),
            "rss_mib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            "python":platform.python_version(),"machine":platform.machine(),
        }
    }
    if len(json.dumps(result,sort_keys=True,separators=(",",":")).encode()) > 131072:
        raise ValueError("exceeded genuine native compact raw evidence size")
    budget(t0)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--execute",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if not a.execute:
        raise PermissionError("new source-native E0 physics needs reviewed one-use marker")
    result=study(source_sha=a.source_sha)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n")


if __name__=="__main__":
    main()
