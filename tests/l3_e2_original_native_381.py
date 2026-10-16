"""#381: bounded genuine E2 native downstream experiment, dormant until reviewed marker.

An import, unit test or PR cannot advance original seed544 physics. Source
registration, workflow registration and original one-use marker are separately
reviewed acceptance boundaries. Never rerun consumed E0/E1 Actions.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
import resource
from pathlib import Path
import subprocess
import time
from unittest.mock import patch

from core.experiment import IOExperiment
from core.state import Lifecycle, UniverseState
from research.a1_exposed_reader_pilot_317 import R2_FROZEN_DIGEST, source_event_digest
from research.a2_matched_recipient_contract_336 import CONTACT_KEY
from research.phase_g_memory_search_159 import _load_protocol
from research.r2_write_rules_175 import LocalWriteRule, HORIZONS, h0_branches, load_frozen
from research.transduction_audit_120 import canonical_digest, clone_state
from tests.l3_e1_native_intervention_363 import (
    archived_e0, budget, original_branch, replay_original_b_prestep,
)
from tests.l3_xor_exposed_pilot_358 import candidate_config
from tests.support_l3_e1_precontact_363 import first_h0_carrier_trace_contrast
from tests.support_l3_e2_retention_379 import (
    horizon_plan, classify_paired_native_edge,
)
from tests.support_r2_masked_xor_native_observer_358 import MaskedXorNativeObserver

MARKER = Path("research/approvals/l3_e2_original_native_381.run")
PROTOCOL = Path("tests/l3_e2_retention_protocol_379.json")
E1_ARCHIVE = Path("research/artifacts/l3_e1_363_original_native_run38812162541.json.base64")
E1_SHA = "3d7075a727c6bb1e2c08887cf7b1dc8313594d1f5f788ddc1b7915ddcd182164"
PREFIX = "L3-E2-381-ORIGINAL-NATIVE-ONE-SHOT "
SCHEMA = "UG_L3_381_E2_ORIGINAL_RETENTION_CAUSAL_V1"
_AUTHORIZED = object()


def exact_gate(source_sha: str) -> None:
    if (os.environ.get("GITHUB_EVENT_NAME") != "push"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise PermissionError("reviewed E2 main push attempt1 only")
    if (len(source_sha) != 40
            or any(c not in "0123456789abcdef" for c in source_sha)
            or not MARKER.is_file() or not PROTOCOL.is_file()):
        raise PermissionError("missing E2 marker/source/protocol")
    p = json.loads(PROTOCOL.read_text())
    if (p["schema"] != "UG_L3_E2_379_ORIGINAL_CONTEXT_DOWNSTREAM_SOURCE_ONLY_V1"
            or p["owner_issue"] != 379
            or p["parent_owner_issue"] != 363
            or p["status"] != "SOURCE_ONLY_DESIGN_NOT_AUTHORIZED_TO_EXECUTE_NATIVE_E2"
            or p["resources"]["no_retry"] is not True
            or p["resources"]["no_effectful_workflow_or_marker_in_this_design"] is not True
            or p["actual_e2_original_native_physics_started"] is not False
            or p["evidence"]["e1_raw_sha256"] != E1_SHA
            or p["scientific_claims"]["learning_claim"] is not False):
        raise PermissionError("frozen reviewed E2 source contract mismatch")
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, check=True,
                              timeout=12, text=True).stdout.strip()
    head, parent = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^")
    if head != source_sha or MARKER.read_text() != PREFIX + parent + "\n":
        raise PermissionError("E2 exact source-locked marker differs")
    if git("diff", "--name-only", "HEAD^", "HEAD") != str(MARKER):
        raise PermissionError("E2 activation must change only its one marker")
    adds = git("log", "--full-history", "--format=%H", "--diff-filter=A", "--", str(MARKER)).splitlines()
    mods = git("log", "--full-history", "--format=%H", "--diff-filter=M", "--", str(MARKER)).splitlines()
    deletes = git("log", "--full-history", "--format=%H", "--diff-filter=D", "--", str(MARKER)).splitlines()
    if len(adds) != 1 or mods or deletes:
        raise PermissionError("E2 one-shot marker has been used/changed")
    if subprocess.run(["git", "diff", "--quiet", "HEAD"], check=False,
                      timeout=12).returncode:
        raise PermissionError("dirty E2 source checkout")


def actual_e1_archive() -> dict:
    raw = base64.b64decode(E1_ARCHIVE.read_text().strip(), validate=True)
    if hashlib.sha256(raw).hexdigest() != E1_SHA:
        raise ValueError("source-authentic E1 original raw SHA mismatch")
    d = json.loads(raw)
    if (d["schema"] != "UG_L3_363_E1_AUTHENTIC_PRECONTACT_INTERVENTION_V1"
            or d["source_sha"] != "4e5b43bfab3515bc8945f6ffdc38fe9ca8027fcf"
            or d["original_e0_raw_sha256"] !=
                "08b1368a74729dfa5bee6da29069a7d757cc053fd5de493777e701196aa1368d"
            or d["classification"] !=
                "LOCAL_AUTHENTIC_CONTEXT_CONTROLLED_RECEIVER_EFFECT_RETENTION_UNRESOLVED"
            or d["independent_confirmation"] is not False
            or d["learning_claim"] is not False):
        raise ValueError("E1 origin or non-learning boundary mismatch")
    return d


def _key(e: dict) -> tuple:
    return tuple(e[f] for f in CONTACT_KEY)


def trajectory_arm(
    pre: dict, epochs: list[int], config,
    *, source_slot: int, source_trace: int, zero_source_latent: bool,
    absolute_targets: set[int], start: float, _token=None,
) -> dict:
    """One guarded original B pre-step native continuation, never called by PR tests."""
    if _token is not _AUTHORIZED:
        raise PermissionError("native original E2 physical advancement requires one-use gate")
    if (type(source_slot) is not int or source_slot < 0
            or type(source_trace) is not int or not 0 <= source_trace <= 255
            or not absolute_targets or min(absolute_targets) <= pre["generation"]):
        raise ValueError("invalid frozen E2 source intervention and targets")
    state = clone_state(deepcopy(pre), config)
    if source_slot >= state.max_cells or len(epochs) != state.max_cells:
        raise ValueError("missing original full state/epoch table")
    state.slow_trace[source_slot] = source_trace
    if zero_source_latent:
        state.latent[source_slot] = 0
    initial = state.to_snapshot()
    bare = clone_state(deepcopy(initial), config)
    obs = MaskedXorNativeObserver(state, event_limit=200000)
    obs.prior.epochs[:] = list(epochs)
    birth_events: list[dict] = []
    native_spawn = UniverseState.spawn

    def record_native_spawn(participant, *args, **kwargs):
        slot = native_spawn(participant, *args, **kwargs)
        if participant is state:
            birth_events.append({
                "generation": int(state.generation), "slot": int(slot),
                "life_epoch": int(obs.prior.epochs[slot]) + 1,
            })
        return slot

    cp: dict[str, dict] = {}
    exp = IOExperiment(state, experiment=_load_protocol())
    with ExitStack() as stack:
        stack.enter_context(patch.object(UniverseState, "spawn", record_native_spawn))
        stack.enter_context(LocalWriteRule("unit_add", {31}).attach())
        stack.enter_context(obs.attach())
        while state.generation < max(absolute_targets):
            exp._advance(())
            if state.generation in absolute_targets:
                key = str(state.generation)
                cp[key] = {
                    "digest": canonical_digest(state.to_snapshot()),
                    "source_latent": int(state.latent[31]),
                    "recipient_latent": int(state.latent[22]),
                    "source_trace": int(state.slow_trace[31]),
                    "recipient_trace": int(state.slow_trace[22]),
                }
            if state.generation % 25 == 0:
                budget(start)
    if len(obs.events) > 200000:
        raise ValueError("E2 source-native event bound exceeded")
    # Independent ORIGINAL physics continuation without any observer wrapper.
    bare_exp = IOExperiment(bare, experiment=_load_protocol())
    with LocalWriteRule("unit_add", {31}).attach():
        while bare.generation < max(absolute_targets):
            bare_exp._advance(())
            if bare.generation in absolute_targets:
                if canonical_digest(bare.to_snapshot()) != cp[str(bare.generation)]["digest"]:
                    raise ValueError("E2 actual instrumented-vs-bare checkpoint drift")
            if bare.generation % 25 == 0:
                budget(start)
    if bare.to_snapshot() != state.to_snapshot():
        raise ValueError("E2 authoritative terminal observer/bare drift")
    # A BLACK_HOLE is a retained physical identity, but is not an ACTIVE
    # living recipient. Count presence and active-living separately.
    living = {
        (slot, int(obs.prior.epochs[slot]))
        for slot in range(state.max_cells)
        if state.lifecycle[slot] == Lifecycle.ACTIVE
    }
    present = {
        (slot, int(obs.prior.epochs[slot]))
        for slot in range(state.max_cells)
        if state.lifecycle[slot] != Lifecycle.FREE
    }
    budget(start)
    return {
        "initial": initial, "checkpoints": cp,
        "events": obs.events,
        "selected_event_digest": source_event_digest(obs.events),
        "free_events": obs.prior.free_events, "birth_events": birth_events,
        "terminal_living_epochs": living, "terminal_present_epochs": present,
        "final_snapshot": state.to_snapshot(),
        "terminal_digest": canonical_digest(state.to_snapshot()),
        "full_native_parity": True,
    }


def downstream_candidate_graph(baseline: dict, treatment: dict,
                               *, selected_contact_post: int) -> dict:
    """Descriptive graph candidates; no transfer/retention proof from aggregate alone."""
    def idx(events):
        m = {}
        for e in events:
            k = _key(e)
            if k in m:
                raise ValueError("duplicate original native selected contact")
            m[k] = e
        return m

    a, b = idx(baseline["events"]), idx(treatment["events"])
    eligible = sorted(k for k in a.keys() & b.keys() if k[0] >= selected_contact_post)
    affected = {(31, 0), (22, 0)}
    counts = Counter()
    examples = []
    current_gen = None
    pending = set()
    recipient_inputs_a = Counter((k[0], k[3], k[5]) for k in a)
    recipient_inputs_b = Counter((k[0], k[3], k[5]) for k in b)
    for k in eligible:
        if current_gen != k[0]:
            if current_gen is not None:
                affected.update(pending)
            pending = set()
            current_gen = k[0]
        # The native observer records recipient-after after all transmissions.
        # Multiple same-step inputs forbid assigning one contact's contribution
        # to a unique receiver final value.
        target = (k[0], k[3], k[5])
        if recipient_inputs_a[target] != 1 or recipient_inputs_b[target] != 1:
            counts["MULTI_INPUT_RECIPIENT_NOT_ISOLATED"] += 1
            continue
        verdict = classify_paired_native_edge(
            a[k], b[k],
            affected_source_epochs=frozenset(affected),
            living_recipient_epochs=frozenset({(k[3], k[5])}),
        )
        label = verdict["classification"]
        counts[label] += 1
        if label == "CANDIDATE_NATIVE_EDGE_REQUIRES_CHAIN_AND_TURNOVER_PROOF":
            pending.add((k[3],k[5]))
            if len(examples) < 12:
                examples.append(verdict)
    affected.update(pending)
    living_pair = baseline["terminal_living_epochs"] & treatment["terminal_living_epochs"]
    terminal_different_living = sorted(
        identity for identity in living_pair if
        baseline["final_snapshot"]["arrays"]["latent"][identity[0]]
        != treatment["final_snapshot"]["arrays"]["latent"][identity[0]]
    )
    original_free_baseline = {
        (int(e["slot"]),int(e["life_epoch"]))
        for e in baseline["free_events"]
    }
    original_free_treatment = {
        (int(e["slot"]),int(e["life_epoch"]))
        for e in treatment["free_events"]
    }
    original_turnover = ((31,0) in original_free_baseline & original_free_treatment
                         or (22,0) in original_free_baseline & original_free_treatment)
    candidates = [
        identity for identity in terminal_different_living
        if identity in affected and identity not in ((31,0),(22,0))
    ]
    # A candidate path may still lack complete provenance at mechanics-diverged
    # epochs. Never promote it to an independently certified memory claim.
    return {
        "matched_native_key_count": len(eligible),
        "native_epoch_candidate_counts": dict(counts),
        "candidate_first_events": examples,
        "terminal_living_latent_delta_epoch_count": len(terminal_different_living),
        "candidate_living_distinct_epoch_count": len(candidates),
        "original_donor_or_receiver_freed_both_arms": original_turnover,
        "causal_cross_life_epoch_turnover_proven": False,
        "candidate_turnover_path_not_independently_confirmed": bool(original_turnover and candidates),
        "post_treatment_mechanical_divergence_observed": bool(
            counts["POST_TREATMENT_MECHANICAL_CONTEXT_DIVERGENCE"]
        ),
    }


def study(source_sha: str, *, _token=None) -> dict:
    if _token is not _AUTHORIZED:
        raise PermissionError("E2 authentic native original physics not authorized from unit test")
    start=time.perf_counter()
    p=json.loads(PROTOCOL.read_text())
    e1=actual_e1_archive()
    e0=archived_e0()
    frozen=load_frozen()
    if frozen["digest"] != R2_FROZEN_DIGEST:
        raise ValueError("original R2 qualified frozen manifest drift")
    branches=h0_branches(544)
    for role in ("b","h","control"):
        if canonical_digest(branches[role]) != frozen["h0_evidence"]["544"][role+"_digest"]:
            raise ValueError("E2 original teacher h0 witness drift")
    base, config = candidate_config()
    if ([k for k,v in asdict(base).items() if asdict(config)[k] != v]
            != ["latent_operator"] or config.latent_operator != "masked_xor"):
        raise ValueError("E2 original native operator one-factor drift")
    e1sel=e1["local_intervention"]["selected"]
    if e1sel["native_key"] != {
        k:p["evidence"]["selected"][k] for k in CONTACT_KEY
    } or (e1sel["baseline_B_source_trace"], e1sel["intervention_H_source_trace"]) != (32,0):
        raise ValueError("original selected E1 physical contact differs from frozen E2")
    b_events=original_branch("b",branches,config,e0,start)
    h_events=original_branch("h",branches,config,e0,start)
    if first_h0_carrier_trace_contrast(b_events,h_events) != e1sel:
        raise ValueError("E2 selection differs from original E1 prereg and authentic E0")
    pre,epochs,orig_b=replay_original_b_prestep(
        branches,config,e1sel,b_events,start
    )
    if (canonical_digest(pre) != e1["local_intervention"]["prestep_authoritative_digest"]
            or orig_b["native_mask"] != e1["local_intervention"]["native_records"]["baseline"]["native_mask"]):
        raise ValueError("E2 prestep or selected original B mask SHA provenance mismatch")
    actual_h0_generation=int(branches["b"]["generation"])
    schedule=horizon_plan(actual_h0_generation)
    absolute_targets={
        row["absolute_snapshot_generation"] for group in ("post_h0","post_selected")
        for row in schedule[group]
        if row["absolute_snapshot_generation"] > pre["generation"]
    }
    if schedule["required_last_generation"] not in absolute_targets:
        raise ValueError("missing required original absolute long horizon")
    source=e1sel["native_key"]["source_slot"]
    if source!=31 or pre["generation"]!=49:
        raise ValueError("unexpected original selected E2 source or pre-step")
    variants={
        "baseline":(32,False),"same_value_sham":(32,False),
        "trace_only_H":(0,False),
        "source_zero_baseline":(32,True),"source_zero_trace_H":(0,True),
    }
    arms={
        name:trajectory_arm(
            pre,epochs,config,source_slot=source,source_trace=trace,
            zero_source_latent=zero,absolute_targets=absolute_targets,
            start=start,_token=_AUTHORIZED,
        )
        for name,(trace,zero) in variants.items()
    }
    b0,sham=arms["baseline"],arms["same_value_sham"]
    if (b0["checkpoints"]!=sham["checkpoints"]
            or b0["selected_event_digest"]!=sham["selected_event_digest"]
            or b0["terminal_digest"]!=sham["terminal_digest"]
            or b0["free_events"]!=sham["free_events"]
            or b0["birth_events"]!=sham["birth_events"]):
        raise ValueError("E2 full downstream B/B sham mismatch")
    # Original E0 B golden end checkpoint is post-h0 +1000, not post-E1 +1000.
    e0_h1000=e0["branch_summaries"]["544"]["b"]["checkpoints"]["1000"]
    if b0["checkpoints"][str(actual_h0_generation+1000)]["digest"]!=e0_h1000:
        raise ValueError("original E2 baseline differs from real E0 +1000")
    key=tuple(e1sel["native_key"][f] for f in CONTACT_KEY)
    for name,a in arms.items():
        events=[e for e in a["events"] if _key(e)==key]
        if len(events)!=1:
            raise ValueError("E2 original selected contact absent or duplicated")
        expect=e1["local_intervention"]["native_records"][name]
        if any(events[0][f]!=expect[f] for f in expect):
            raise ValueError("E2 original one-step recipient did not reproduce E1")
    graph=downstream_candidate_graph(
        b0, arms["trace_only_H"],
        selected_contact_post=50,
    )
    last=str(schedule["required_last_generation"])
    terminal_equal=(b0["checkpoints"][last]["digest"]
                    ==arms["trace_only_H"]["checkpoints"][last]["digest"])
    any_downstream_delta=any(
        b0["checkpoints"][k]["digest"]!=arms["trace_only_H"]["checkpoints"][k]["digest"]
        for k in b0["checkpoints"]
    )
    if not any_downstream_delta:
        result="NO_NEW_DOWNSTREAM_DIFFERENCE"
    elif terminal_equal:
        result="SHORT_LIVED_EXPIRED_BY_FROZEN_HORIZON"
    elif graph["candidate_turnover_path_not_independently_confirmed"]:
        result="CANDIDATE_LINEAGE_WITNESS_NOT_INDEPENDENT"
    else:
        result="PERSISTENT_SNAPSHOT_ONLY_NO_LINEAGE"
    out={
        "schema":SCHEMA,"owner":381,"source_sha":source_sha,
        "original_e0_raw_sha256":p["evidence"]["e0_original_raw_sha256"],
        "original_e1_raw_sha256":E1_SHA,
        "original_selected":e1sel,"horizons":schedule,
        "arms":{name:{
            "checkpoints":a["checkpoints"],
            "terminal_digest":a["terminal_digest"],
            "native_directed_selected_contacts":len(a["events"]),
            "birth_event_count":len(a["birth_events"]),
            "free_event_count":len(a["free_events"]),
            "terminal_active_epoch_count":len(a["terminal_living_epochs"]),
            "terminal_present_epoch_count":len(a["terminal_present_epochs"]),
            "source_native_parity":a["full_native_parity"],
        } for name,a in arms.items()},
        "preintervention_h0_checkpoints": {
            k:v for k,v in e0["branch_summaries"]["544"]["b"]["checkpoints"].items()
            if actual_h0_generation+int(k) <= pre["generation"]
        },
        "candidate_graph":graph,
        "classification":result,
        "independent_confirmation":False,"natural_spontaneous_teacher_causality_proven":False,
        "turnover_causal_proof":False,"learning_claim":False,
        "resources":{"seconds":round(time.perf_counter()-start,3),
                     "rss_mib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024},
    }
    budget(start)
    if len(json.dumps(out,sort_keys=True,separators=(",",":")).encode())>131072:
        raise ValueError("E2 original compact report exceeded 128KiB")
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--execute",action="store_true")
    args=p.parse_args()
    if not args.execute:
        raise PermissionError("E2 only one reviewed marker may launch original native physics")
    exact_gate(args.source_sha)
    data=study(args.source_sha,_token=_AUTHORIZED)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n")


if __name__=="__main__":
    main()
