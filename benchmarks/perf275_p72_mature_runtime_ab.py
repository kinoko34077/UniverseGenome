"""P7.2 exposed seed0 original full native128 maturity10/20 interpreter AB only.

Uses one source-locked host, original source-native prefix state and exact previous
selected optimizer-v7 under CPython and PyPy. Never evolves reserved seed16384.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

SOURCE = "65e1d78576026b0214a0184bd6028e01dc3cc7e1"
# Bound an eventually admitted performance run to the prior 18-minute hosted envelope.
MAX_TOTAL_WALL_S = 18 * 60
EXPECTED_RUNTIME = {
    "cpython": ("cpython", 3, 12),
    "pypy": ("pypy", 3, 11),
    "prefix": ("pypy", 3, 11),
}
RUNTIME_PROBE = (
    "import json,sys;"
    "print(json.dumps({"
    "'implementation':sys.implementation.name,"
    "'python_version':list(sys.version_info[:2]),"
    "'executable':sys.executable,"
    "'version':sys.version"
    "},sort_keys=True))"
)
GOLDEN_FIRST4 = (
    "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63",
    "abe281245d5a45e78dcce3eab9e9f787b6260f365fa868da5ef13c2db3262112",
    "0ac1086caa69775a630165c2dab161513b240a63993e4f53a1be9b33688251f2",
    "b06e987f5dffbb114362be88bac56da7a1a00d1e1e60f18368c0fc78a3a7cc10",
)
GOLDEN_MATURE = {
    10: "c1b3dcbfacd46f20914a63746eee2a7e9ccdb59aab266692d5a20788ec9b623e",
    20: "f66dda9554a8b8c9b4da164f60c67aa7455d62f65f32e1d3871775cbc1ed0fc5",
}

NATIVE_CHILD = r"""
import hashlib,json,subprocess,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d16_native_journal_observer_217 import observe_committed_round
from research.d16_twojob_run_control_217 import hash_of
from research.d8_genome_diversity_190 import digest
ordinal=int(sys.argv[1]); prior_file=sys.argv[2]; out=Path(sys.argv[3]); with_observer=int(sys.argv[4])
source=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
prior=None if prior_file=="NONE" else json.loads(Path(prior_file).read_bytes())["selected_snapshot"]
start=time.perf_counter()
with TemporaryDirectory(prefix="perf275-p72-true-d15-") as tmp:
    root=Path(tmp)/"journal"
    r=execute_selected_round(root,source_commit=source,base_seed=0,
                             experiment=ExperimentConfig(),base_config=PhysicsConfig(),
                             base_snapshot=prior,memory_mib=1536,workers=4,evaluation_batch_size=16)
    native_wall=time.perf_counter()-start
    observer=observe_committed_round(root,source_commit=source) if with_observer else None
    if (r["new_evaluations"]!=128 or r["resumed_from"]!=0 or r["checkpoint_writes"]!=8
        or not r["final_committed"] or not r["finalization_performed"]
        or r["final_digest"]!=digest(r["final_snapshot"])
        or r["journal_bytes"]>128*1024*1024
        or r.get("peak_aggregate_rss_bytes",2**64)>1536*1024*1024):
        raise AssertionError("D15 original native128 or cap drift")
    if observer is not None and (
        observer["selected_post_v7_sha256"]!=r["final_digest"]
        or not observer["d15_journal_chain_verified"]
        or observer["original_selected_once_proven_by_D15_final"] is not True
        or observer["read_only"] is not True or observer["learning_claim"] is not False):
        raise AssertionError("D16 original observer drift")
    original_files = {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(root.glob("*.json"))
        if item.name != "manifest.json"
    }
    expected_files = {"base.json", "final.json"} | {
        f"batch-{i:05d}.json" for i in range(8)
    }
    if set(original_files) != expected_files:
        raise AssertionError("D15 original base/8 ordered batch/final payload mismatch")
    result={
        "runtime_identity": {
            "implementation": sys.implementation.name,
            "python_version": list(sys.version_info[:2]),
            "executable": sys.executable,
            "version": sys.version,
        },
        "source_sha":source,"seed":0,"ordinal":ordinal,
        "native_wall_s":native_wall,"selected_v7":r["final_digest"],
        "journal_bytes":r["journal_bytes"],"patches":r["checkpoint_writes"],
        "journal_payload_sha256":original_files,
        "native128_evaluations":128,"default1024":True,
        "sampled_rss_bytes":r.get("peak_aggregate_rss_bytes"),
        "observer_hash":None if observer is None else hash_of(observer),
        "selected_snapshot":r["final_snapshot"],"real_seed16384_executed":False,
    }
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="selected_snapshot"},sort_keys=True),flush=True)
"""


def git_source() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=10).strip()


def remaining_timeout(deadline: float) -> float:
    """Bound each child to the smaller of its 180s step cap and total 18m cap."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("P7.2 aggregate 18-minute wall budget exhausted")
    return min(180.0, remaining)


def validate_runtime_identity(label: str, identity: dict) -> None:
    """Reject mistagged CPython/PyPy paths before accepting performance evidence."""
    expected = EXPECTED_RUNTIME.get(label)
    if expected is None or not isinstance(identity, dict):
        raise AssertionError("P7.2 unknown interpreter label or missing identity")
    implementation, major, minor = expected
    if (identity.get("implementation") != implementation
            or identity.get("python_version") != [major, minor]
            or not isinstance(identity.get("executable"), str)
            or not identity["executable"]):
        raise AssertionError(
            f"P7.2 {label} is not the declared {implementation} {major}.{minor} interpreter"
        )


def preflight_runtime(exe: str, label: str) -> dict:
    """Verify both interpreter binaries before any physical selected128 work."""
    identity = json.loads(
        subprocess.check_output([exe, "-c", RUNTIME_PROBE], text=True, timeout=10)
    )
    validate_runtime_identity(label, identity)
    return identity


def native_step(exe: str, scratch: Path, label: str, ordinal: int,
                prior: Path | None, *, observe: bool, deadline: float) -> tuple[Path, dict]:
    dest = scratch / f"{label}-{ordinal:02d}.json"
    args = [exe, "-c", NATIVE_CHILD, str(ordinal), "NONE" if prior is None else str(prior),
            str(dest), "1" if observe else "0"]
    # Refuse when no budget remains; re-check after process startup as well.
    remaining_timeout(deadline)
    proc = subprocess.Popen(
        args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,  # Linux: child and D15 workers share one process group.
    )
    try:
        _, stderr = proc.communicate(timeout=remaining_timeout(deadline))
    except (subprocess.TimeoutExpired, TimeoutError) as exc:
        # subprocess.run(timeout=...) kills only the parent, not spawn workers.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        raise TimeoutError(
            f"P7.2 {label} ordinal{ordinal} exceeded step/aggregate wall budget"
        ) from exc
    if proc.returncode:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        raise RuntimeError(f"{label} original native ordinal{ordinal} failed: {stderr[-3500:]}")
    result = json.loads(dest.read_bytes())
    validate_runtime_identity(label, result.get("runtime_identity"))
    retained_bytes = sum(p.stat().st_size for p in scratch.glob("*.json"))
    if retained_bytes > 512*1024*1024:
        raise AssertionError("P7.2 per-host retained report/snapshot cap exceeded")
    result["retained_scratch_bytes"] = retained_bytes
    if (result["ordinal"] != ordinal or result["source_sha"] != SOURCE
            or result["seed"] != 0 or result["native128_evaluations"] != 128
            or result["patches"] != 8 or result["sampled_rss_bytes"] > 1536*1024*1024):
        raise AssertionError("frozen source/native/memory envelope drift")
    if ordinal <= 4 and result["selected_v7"] != GOLDEN_FIRST4[ordinal-1]:
        raise AssertionError("original historical selected first4 v7 drift")
    if ordinal in GOLDEN_MATURE and result["selected_v7"] != GOLDEN_MATURE[ordinal]:
        raise AssertionError("original mature selected10/20 v7 drift")
    print(json.dumps({"label":label,"ordinal":ordinal,
                      "native_wall":result["native_wall_s"],
                      "selected_v7":result["selected_v7"],
                      "rss":result["sampled_rss_bytes"]}, sort_keys=True), flush=True)
    return dest, result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cpython", required=True)
    p.add_argument("--pypy", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if git_source() != SOURCE:
        raise AssertionError("original source checkout changed")
    deadline = time.monotonic() + MAX_TOTAL_WALL_S
    report = {
        "kind":"PERF275_P72_TRUE_DEFAULT1024_NATIVE128_MATURE_RUNTIME_AB",
        "source_sha":SOURCE,"seed":0,"status":"INCOMPLETE",
        "prefix_count":0,"mature":{},
        "original_seed16384_executed":False,"learning_claim":False,
    }
    def save():
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")

    save()
    report["interpreter_preflight"] = {
        "cpython": preflight_runtime(args.cpython, "cpython"),
        "pypy": preflight_runtime(args.pypy, "pypy"),
    }
    save()
    with TemporaryDirectory(prefix="perf275-p72-same-host-") as t:
        scratch=Path(t)
        previous=None
        for ordinal in range(1,10):
            previous,_=native_step(args.pypy,scratch,"prefix",ordinal,previous,observe=False,deadline=deadline)
            report["prefix_count"]=ordinal
            save()
        for mature in (10,20):
            c_path,c= native_step(args.cpython,scratch,"cpython",mature,previous,observe=True,deadline=deadline)
            p_path,py= native_step(args.pypy,scratch,"pypy",mature,previous,observe=True,deadline=deadline)
            if (c["selected_v7"]!=py["selected_v7"]
                or c["journal_bytes"]!=py["journal_bytes"]
                or c["journal_payload_sha256"]!=py["journal_payload_sha256"]
                or c["observer_hash"]!=py["observer_hash"]):
                raise AssertionError("actual original D15/D16 observer/v7 cross-runtime mismatch")
            ratio=c["native_wall_s"]/py["native_wall_s"]
            report["mature"][str(mature)]={
                "selected_v7":c["selected_v7"],"observer_hash":c["observer_hash"],
                "journal_bytes":c["journal_bytes"],
                "journal_payload_sha256":c["journal_payload_sha256"],
                "max_retained_scratch_bytes":max(c["retained_scratch_bytes"], py["retained_scratch_bytes"]),
                "cpython_s":c["native_wall_s"],
                "pypy_s":py["native_wall_s"],"speed_ratio":ratio,
                "cpython_rss_bytes":c["sampled_rss_bytes"],
                "pypy_rss_bytes":py["sampled_rss_bytes"],
            }
            save()
            previous=p_path
            if mature==10:
                for ordinal in range(11,20):
                    previous,_=native_step(args.pypy,scratch,"prefix",ordinal,previous,observe=False,deadline=deadline)
                    report["prefix_count"]=ordinal
                    save()
        old=sum(v["cpython_s"] for v in report["mature"].values())
        new=sum(v["pypy_s"] for v in report["mature"].values())
        ratio=old/new
        report["combined_speed_ratio"]=ratio
        report["status"]=(
            "PASS_MATURE_20_PYPY_RUNTIME_CANDIDATE_ONLY"
            if ratio>=1.2 and all(v["speed_ratio"]>=0.97 for v in report["mature"].values())
            else "REJECT_OR_HOLD_MATURE_RUNTIME_GATE"
        )
        save()
        print(json.dumps({"status":report["status"],"combined_ratio":ratio,
                          "original_science_seed16384_executed":False},sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
