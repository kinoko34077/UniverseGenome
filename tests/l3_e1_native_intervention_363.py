"""E1 #363: source-locked candidate for ONE separately reviewed original native contact test.

Importing or unit-testing is inert. Original exposed seed 544 is never advanced
except after its OWN reviewed marker, unique main push and exact source lock.
Old E0/#336/#358 Actions/markers are not touched or rerun.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

from core.experiment import IOExperiment
from research.a1_exposed_reader_pilot_317 import R2_FROZEN_DIGEST, source_event_digest
from research.phase_g_memory_search_159 import _load_protocol
from research.r2_write_rules_175 import LocalWriteRule, HORIZONS, h0_branches, load_frozen
from research.transduction_audit_120 import canonical_digest, clone_state
from research.a2_matched_recipient_contract_336 import CONTACT_KEY, NONTRACE_CONTEXT
from tests.l3_xor_exposed_pilot_358 import candidate_config
from tests.support_r2_masked_xor_native_observer_358 import MaskedXorNativeObserver
from tests.support_l3_e1_precontact_363 import first_h0_carrier_trace_contrast

PROTOCOL = Path("tests/l3_e1_precontact_protocol_363.json")
MARKER = Path("research/approvals/l3_e1_original_native_363.run")
PREFIX = "L3-E1-363-ORIGINAL-NATIVE-ONE-SHOT "
ARCHIVE = Path("research/artifacts/l3_route_e0_363_original_544_545_run38788978495.json.base64")
ARCHIVE_RAW_SHA = "08b1368a74729dfa5bee6da29069a7d757cc053fd5de493777e701196aa1368d"
SCHEMA = "UG_L3_363_E1_AUTHENTIC_PRECONTACT_INTERVENTION_V1"
_AUTHORIZED = object()


def exact_gate(source_sha: str) -> None:
    if (os.environ.get("GITHUB_EVENT_NAME") != "push"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise PermissionError("E1 main one-use marker push only")
    if (len(source_sha) != 40
            or any(c not in "0123456789abcdef" for c in source_sha)
            or not MARKER.is_file() or not PROTOCOL.is_file()):
        raise PermissionError("E1 exact approved marker/source unavailable")
    p = json.loads(PROTOCOL.read_text())
    if (p["schema"] != "UG_L3_363_E1_ORIGINAL_SELECTED_PRECONTACT_SOURCE_ONLY_V1"
            or p["owner_issue"] != 363
            or p["status"] != "SOURCE_ONLY_PREDECLARATION_NO_NEW_PHYSICS_AUTHORIZATION"
            or p["frozen_provenance"]["exposed_seed"] != 544
            or p["frozen_provenance"]["archived_raw_sha256"] != ARCHIVE_RAW_SHA
            or p["actual_e1_original_physics_started"] is not False
            or p["bounds"]["no_retry"] is not True):
        raise PermissionError("frozen E1 protocol changed")
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              timeout=12, check=True).stdout.strip()
    head, parent = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^")
    if head != source_sha or MARKER.read_text() != PREFIX + parent + "\n":
        raise PermissionError("E1 source-locked marker does not match reviewed parent")
    if git("diff", "--name-only", "HEAD^", "HEAD") != str(MARKER):
        raise PermissionError("E1 activation must be one newly added marker only")
    adds = git("log", "--full-history", "--format=%H", "--diff-filter=A", "--", str(MARKER)).splitlines()
    mods = git("log", "--full-history", "--format=%H", "--diff-filter=M", "--", str(MARKER)).splitlines()
    deletions = git("log", "--full-history", "--format=%H", "--diff-filter=D", "--", str(MARKER)).splitlines()
    if len(adds) != 1 or mods or deletions:
        raise PermissionError("E1 marker used or changed")
    if subprocess.run(["git", "diff", "--quiet", "HEAD"], check=False).returncode:
        raise PermissionError("dirty E1 source checkout")


def budget(start: float) -> None:
    if time.perf_counter() - start > 900:
        raise TimeoutError("E1 host time budget exceeded")
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 > 1536:
        raise MemoryError("E1 host RSS >1536 MiB")


def archived_e0() -> dict:
    raw = base64.b64decode(ARCHIVE.read_text().strip(), validate=True)
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_RAW_SHA:
        raise ValueError("authentic E0 raw archive SHA drift")
    e0 = json.loads(raw)
    if (e0["schema"] != "UG_L3_363_GENUINE_NATIVE_ROUTE_E0_V1"
            or e0["source_sha"] != "9c18a878a2f122ee351c5052de3c7f3f0883b74b"
            or not e0["controls_pass"] or not e0["genuine_native_observed_unobserved_parity"]
            or e0["learning_claim"] is not False):
        raise ValueError("original E0 integrity/control mismatch")
    return e0


def setup(seed: int, role: str, branches: dict, config):
    state = clone_state(branches[role], config)
    return state, IOExperiment(state, experiment=_load_protocol()), LocalWriteRule("unit_add", {31})


def original_branch(role: str, branches: dict, config, e0: dict, start: float):
    """Authenticated fresh candidate acquisition, not E0 one-shot Action replay."""
    state, exp, writer = setup(544, role, branches, config)
    obs = MaskedXorNativeObserver(state, event_limit=200000)
    checkpoints = {"0": canonical_digest(state.to_snapshot())}
    with writer.attach(), obs.attach():
        for i in range(1, 1001):
            exp._advance(())
            if i in HORIZONS[1:]:
                checkpoints[str(i)] = canonical_digest(state.to_snapshot())
            if i % 25 == 0:
                budget(start)
    expected = e0["branch_summaries"]["544"][role]
    if (checkpoints != expected["checkpoints"]
            or source_event_digest(obs.events) != expected["selected_events_sha256"]
            or source_event_digest(obs.prior.free_events) != expected["free_events_sha256"]
            or len(obs.events) != expected["selected_directed_contact_count"]):
        raise ValueError("reacquired original B/H deviates from archived E0")
    return obs.events


def replay_original_b_prestep(branches: dict, config, selected: dict,
                              original_b_events: list[dict], start: float):
    """Capture original full authoritative state BEFORE original selected step."""
    state, exp, writer = setup(544, "b", branches, config)
    obs = MaskedXorNativeObserver(state, event_limit=200000)
    generation = selected["native_key"]["native_generation"]
    pre = epochs = None
    with writer.attach(), obs.attach():
        while state.generation <= generation:
            if state.generation == generation:
                pre = state.to_snapshot()
                epochs = list(obs.prior.epochs)
            exp._advance(())
            budget(start)
    if pre is None or epochs is None:
        raise ValueError("selected generation never reached in original B replay")
    # All selected events through captured generation must exactly match
    # the independently archived-E0-authenticated B continuation.
    if obs.events != original_b_events[:len(obs.events)]:
        raise ValueError("original B replay diverged before selected native event")
    key = tuple(selected["native_key"][field] for field in CONTACT_KEY)
    candidates = [e for e in obs.events if tuple(e[field] for field in CONTACT_KEY) == key]
    if len(candidates) != 1:
        raise ValueError("selected true native event not present in original B replay")
    if candidates[0]["source_trace_start"] != selected["baseline_B_source_trace"]:
        raise ValueError("original B pre-step trace disagrees with selected actual contact")
    return pre, epochs, candidates[0]


def arm(pre: dict, epochs: list[int], config, source: int,
        trace: int, start: float, *, zero_source_latent: bool = False):
    state = clone_state(deepcopy(pre), config)
    if not (0 <= source < state.max_cells and 0 <= trace <= 255):
        raise ValueError("invalid native intervention source/trace")
    state.slow_trace[source] = trace
    if zero_source_latent:
        state.latent[source] = 0
    initial = state.to_snapshot()
    bare = clone_state(deepcopy(initial), config)
    exp = IOExperiment(state, experiment=_load_protocol())
    bare_exp = IOExperiment(bare, experiment=_load_protocol())
    observed = MaskedXorNativeObserver(state, event_limit=200000)
    if len(epochs) != state.max_cells:
        raise ValueError("incomplete original native source epoch table")
    observed.prior.epochs[:] = epochs
    with LocalWriteRule("unit_add", {31}).attach(), observed.attach():
        exp._advance(())
    with LocalWriteRule("unit_add", {31}).attach():
        bare_exp._advance(())
    if state.to_snapshot() != bare.to_snapshot():
        raise ValueError("E1 instrumented/uninstrumented native full-state drift")
    budget(start)
    return {"initial": initial, "after_digest": canonical_digest(state.to_snapshot()),
            "events": observed.events, "observer_parity": True}


def evaluate_arms(pre: dict, epochs: list[int], config, selected: dict,
                  reference: dict, start: float) -> dict:
    """Do not reinterpret synthetic controls as original teacher-learning."""
    source = selected["native_key"]["source_slot"]
    btrace = selected["baseline_B_source_trace"]
    htrace = selected["intervention_H_source_trace"]
    treatments = {
        "baseline": (btrace, False),
        "same_value_sham": (btrace, False),
        "trace_only_H": (htrace, False),
        "zero_trace": (0, False),
        "source_zero_baseline": (btrace, True),
        "source_zero_trace_H": (htrace, True),
    }
    arms = {name: arm(pre, epochs, config, source, tr, start, zero_source_latent=bit0)
            for name, (tr, bit0) in treatments.items()}
    key = tuple(selected["native_key"][field] for field in CONTACT_KEY)
    records = {}
    for name, measured in arms.items():
        hits = [e for e in measured["events"]
                if tuple(e[field] for field in CONTACT_KEY) == key]
        if len(hits) != 1:
            raise ValueError("E1 intervention altered actual native selected pair/key")
        records[name] = hits[0]
    if records["baseline"] != reference or records["same_value_sham"] != reference:
        raise ValueError("genuine source B baseline/sham lost original provenance")
    if arms["baseline"]["after_digest"] != arms["same_value_sham"]["after_digest"]:
        raise ValueError("same-trace sham differs in full native output")
    # Every change to full authoritative PRE-step state must be exactly
    # source trace on the treatment; two source-zero controls form a separate
    # paired contrast and are NOT part of the one-variable causal estimate.
    orig = arms["baseline"]["initial"]
    for label, measured in arms.items():
        other = deepcopy(measured["initial"])
        other["arrays"]["slow_trace"][source] = orig["arrays"]["slow_trace"][source]
        if label.startswith("source_zero_"):
            other["arrays"]["latent"][source] = orig["arrays"]["latent"][source]
        if other != orig:
            raise ValueError("E1 pre-step intervention changed unauthorized state")
    for left, right in (("baseline", "trace_only_H"),
                        ("source_zero_baseline", "source_zero_trace_H")):
        a,b=records[left],records[right]
        if any(a[field] != b[field] for field in NONTRACE_CONTEXT):
            raise ValueError("E1 original native pretransmit nontrace confounded")
        if (a["physical_address"],a["source_xy"],a["recipient_xy"]) != (
                b["physical_address"],b["source_xy"],b["recipient_xy"]):
            raise ValueError("E1 original selected geometry diverged")
        predicted = a["source_latent_before"] & (a["native_mask"] ^ b["native_mask"])
        observed_delta = a["recipient_latent_after"] ^ b["recipient_latent_after"]
        if predicted != observed_delta:
            raise ValueError("E1 selected native XOR causal identity failed")
        if left.startswith("source_zero") and (predicted or observed_delta):
            raise ValueError("E1 source-bit-zero negative control failed")
    a,b=records["baseline"],records["trace_only_H"]
    effect=a["recipient_latent_after"] ^ b["recipient_latent_after"]
    maskdiff=a["native_mask"] ^ b["native_mask"]
    if effect:
        outcome="LOCAL_AUTHENTIC_CONTEXT_CONTROLLED_RECEIVER_EFFECT_RETENTION_UNRESOLVED"
    elif not maskdiff:
        outcome="NEGATIVE_TRACE_READER_MASK_NOT_REACHED"
    elif not (a["source_latent_before"] & maskdiff):
        outcome="NEGATIVE_MASK_CHANGE_WITHOUT_SOURCE_BIT"
    else:
        outcome="NEGATIVE_NO_REAL_RECIPIENT_EFFECT"
    return {
        "selected": selected, "baseline_original_event_verified": True,
        "prestep_authoritative_digest": canonical_digest(pre),
        "arm_outcome_digests": {name: a["after_digest"] for name,a in arms.items()},
        "native_records": {name: {
            "source_trace_start": e["source_trace_start"],
            "source_latent_before": e["source_latent_before"],
            "recipient_latent_before": e["recipient_latent_before"],
            "native_mask": e["native_mask"],
            "recipient_latent_after": e["recipient_latent_after"],
        } for name,e in records.items()},
        "trace_only_mask_xor": maskdiff, "trace_only_receiver_xor": effect,
        "classification": outcome, "all_native_observer_parities": True,
        "same_value_sham_full_state_parity": True,
        "zero_source_bit_pair_negative": True,
    }


def study(source_sha: str, *, _token=None):
    if _token is not _AUTHORIZED:
        raise PermissionError("E1 genuine original seed physics not authorized for tests")
    start=time.perf_counter()
    e0=archived_e0()
    frozen=load_frozen()
    if frozen["digest"] != R2_FROZEN_DIGEST:
        raise ValueError("qualified R2 manifest changed")
    branches=h0_branches(544)
    for role in ("b","h","control"):
        if canonical_digest(branches[role]) != frozen["h0_evidence"]["544"][role+"_digest"]:
            raise ValueError("E1 frozen native teacher h0 diverged")
    source_carriers = [i for i,(x,y) in enumerate(zip(
        branches["b"]["arrays"]["slow_trace"], branches["h"]["arrays"]["slow_trace"])) if x != y]
    if source_carriers != [31]:
        raise ValueError("unexpected frozen original teacher carrier")
    base,config=candidate_config()
    diffs = [k for k,v in asdict(base).items() if asdict(config)[k] != v]
    if diffs != ["latent_operator"] or config.latent_operator != "masked_xor":
        raise ValueError("original one-factor source configuration drift")
    b_events=original_branch("b",branches,config,e0,start)
    h_events=original_branch("h",branches,config,e0,start)
    selected=first_h0_carrier_trace_contrast(b_events,h_events)
    result={"schema":SCHEMA, "owner":363, "source_sha":source_sha,
            "original_e0_raw_sha256":ARCHIVE_RAW_SHA,
            "selection_provenance":"GENUINE_REPLAY_MATCHES_AUTHENTIC_E0_EVENT_HASHES_AND_CHECKPOINTS",
            "independent_confirmation":False, "learning_claim":False}
    if selected is None:
        result["classification"]="NOT_EVALUABLE_NO_QUALIFIED_ORIGINAL_H0_CONTACT"
    else:
        pre,epochs,ref=replay_original_b_prestep(branches,config,selected,b_events,start)
        result["local_intervention"]=evaluate_arms(pre,epochs,config,selected,ref,start)
        result["classification"]=result["local_intervention"]["classification"]
    result["resources"]={"wall_seconds":round(time.perf_counter()-start,3),
                         "rss_mib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
    budget(start)
    if len(json.dumps(result,sort_keys=True,separators=(",",":")).encode())>131072:
        raise ValueError("E1 raw result above 128KiB")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if not args.execute:
        raise PermissionError("E1 original contact intervention requires one reviewed main marker")
    exact_gate(args.source_sha)
    result=study(args.source_sha,_token=_AUTHORIZED)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n")


if __name__=="__main__":
    main()
