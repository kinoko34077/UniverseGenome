"""P7.3 source-frozen two-host complete37 runtime comparison.

This is a performance-only gate. It runs one runtime per independent hosted
job from the original source checkout and seed zero, then compares the two
complete 37-round reports. It never dispatches itself and never changes the
historical D16/D18 runtime or protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from typing import Any

# The driver is checked out separately from the original source tree. Make
# its sibling package importable while the child process still runs from the
# source-frozen checkout.
DRIVER_ROOT = Path(__file__).resolve().parents[1]
if str(DRIVER_ROOT) not in sys.path:
    sys.path.insert(0, str(DRIVER_ROOT))

from benchmarks.perf275_p72_mature_runtime_ab import (  # noqa: E402
    NATIVE_CHILD,
    RUNTIME_PROBE,
    validate_runtime_identity,
)

SOURCE = "65e1d78576026b0214a0184bd6028e01dc3cc7e1"
SEED = 0
ROUNDS = 37
MAX_TOTAL_WALL_S = 18 * 60
MAX_ROUND_WALL_S = 180
MAX_RSS_BYTES = 1536 * 1024 * 1024
MAX_JOURNAL_BYTES = 128 * 1024 * 1024
MAX_RETAINED_BYTES = 512 * 1024 * 1024
MIN_SPEED_RATIO = 1.20
REPORT_KIND = "PERF275_P73_TWO_HOST_COMPLETE37_RUNTIME"
EXPECTED_RUNTIME = {
    "cpython": ("cpython", 3, 12),
    "pypy": ("pypy", 3, 11),
}


def git_source() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()


def _runtime_probe(exe: str) -> dict[str, Any]:
    return json.loads(
        subprocess.check_output([exe, "-c", RUNTIME_PROBE], text=True, timeout=10)
    )


def preflight_runtime(exe: str, runtime: str) -> dict[str, Any]:
    expected = EXPECTED_RUNTIME.get(runtime)
    if expected is None:
        raise AssertionError("unknown P7.3 runtime")
    identity = _runtime_probe(exe)
    implementation, major, minor = expected
    if (identity.get("implementation") != implementation
            or identity.get("python_version") != [major, minor]
            or not isinstance(identity.get("executable"), str)
            or not identity["executable"]):
        raise AssertionError(
            f"P7.3 {runtime} is not the declared {implementation} {major}.{minor}"
        )
    return identity


def remaining_timeout(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("P7.3 aggregate 18-minute wall budget exhausted")
    return min(float(MAX_ROUND_WALL_S), remaining)


def native_step(
    runtime: str,
    scratch: Path,
    ordinal: int,
    prior: Path | None,
    *,
    exe: str,
    deadline: float,
) -> tuple[Path, dict[str, Any]]:
    dest = scratch / f"{runtime}-{ordinal:02d}.json"
    args = [
        exe, "-c", NATIVE_CHILD, str(ordinal),
        "NONE" if prior is None else str(prior), str(dest), "1",
    ]
    remaining_timeout(deadline)
    proc = subprocess.Popen(
        args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        _, stderr = proc.communicate(timeout=remaining_timeout(deadline))
    except (subprocess.TimeoutExpired, TimeoutError) as exc:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        raise TimeoutError(
            f"P7.3 {runtime} ordinal{ordinal} exceeded step/aggregate wall budget"
        ) from exc
    if proc.returncode:
        raise RuntimeError(
            f"P7.3 {runtime} ordinal{ordinal} failed: {stderr[-3500:]}"
        )
    result = json.loads(dest.read_bytes())
    validate_runtime_identity(runtime, result.get("runtime_identity"))
    retained = sum(path.stat().st_size for path in scratch.glob("*.json"))
    result["retained_scratch_bytes"] = retained
    if result.get("source_sha") != SOURCE or result.get("seed") != SEED:
        raise AssertionError("P7.3 source/seed drift")
    if result.get("ordinal") != ordinal or result.get("native128_evaluations") != 128:
        raise AssertionError("P7.3 selected128 ordinal drift")
    if (result.get("patches") != 8
            or result.get("default1024") is not True
            or result.get("observer_hash") is None
            or result.get("journal_bytes", MAX_JOURNAL_BYTES + 1) > MAX_JOURNAL_BYTES):
        raise AssertionError("P7.3 D15 journal contract drift")
    if result.get("sampled_rss_bytes", MAX_RSS_BYTES + 1) > MAX_RSS_BYTES:
        raise AssertionError("P7.3 RSS cap exceeded")
    if retained > MAX_RETAINED_BYTES:
        raise AssertionError("P7.3 retained scratch cap exceeded")
    return dest, result


def _new_report(runtime: str) -> dict[str, Any]:
    return {
        "kind": REPORT_KIND,
        "source_sha": SOURCE,
        "seed": SEED,
        "runtime": runtime,
        "status": "INCOMPLETE",
        "rounds_completed": 0,
        "rounds": [],
        "original_seed16384_executed": False,
        "original_seed49152_executed": False,
        "learning_claim": False,
        "host_identity": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
        },
        "interpreter_artifact": {
            "url": os.environ.get("PYPY_ARCHIVE_URL") if runtime == "pypy" else None,
            "sha256": os.environ.get("PYPY_ARCHIVE_SHA256") if runtime == "pypy" else None,
        },
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute_host(runtime: str, exe: str, out: Path) -> dict[str, Any]:
    if runtime not in EXPECTED_RUNTIME:
        raise AssertionError("P7.3 host runtime must be cpython or pypy")
    report = _new_report(runtime)
    _write(out, report)
    if git_source() != SOURCE:
        raise AssertionError("P7.3 original source checkout changed")
    report["interpreter_identity"] = preflight_runtime(exe, runtime)
    _write(out, report)
    deadline = time.monotonic() + MAX_TOTAL_WALL_S
    with TemporaryDirectory(prefix=f"perf275-p73-{runtime}-") as temp:
        scratch = Path(temp)
        prior: Path | None = None
        for ordinal in range(1, ROUNDS + 1):
            prior, result = native_step(
                runtime, scratch, ordinal, prior, exe=exe, deadline=deadline,
            )
            row = {
                key: value for key, value in result.items()
                if key != "selected_snapshot"
            }
            report["rounds"].append(row)
            report["rounds_completed"] = ordinal
            report["max_sampled_rss_bytes"] = max(
                row["sampled_rss_bytes"] for row in report["rounds"]
            )
            report["max_journal_bytes"] = max(
                row["journal_bytes"] for row in report["rounds"]
            )
            report["max_retained_scratch_bytes"] = max(
                row["retained_scratch_bytes"] for row in report["rounds"]
            )
            report["total_native_wall_s"] = sum(
                row["native_wall_s"] for row in report["rounds"]
            )
            _write(out, report)
    if report["rounds_completed"] != ROUNDS:
        raise AssertionError("P7.3 host did not complete exactly 37 rounds")
    report["status"] = "HOST_COMPLETE37"
    _write(out, report)
    return report


def _load_host(path: Path, runtime: str) -> dict[str, Any]:
    report = json.loads(Path(path).read_bytes())
    if (
        report.get("kind") != REPORT_KIND
        or report.get("source_sha") != SOURCE
        or report.get("seed") != SEED
        or report.get("runtime") != runtime
        or report.get("status") != "HOST_COMPLETE37"
        or report.get("rounds_completed") != ROUNDS
        or len(report.get("rounds", [])) != ROUNDS
        or report.get("original_seed16384_executed") is not False
        or report.get("original_seed49152_executed") is not False
        or report.get("learning_claim") is not False
        or not isinstance(report.get("interpreter_identity"), dict)
        or not isinstance(report.get("host_identity"), dict)
        or not isinstance(report.get("interpreter_artifact"), dict)
    ):
        raise AssertionError("P7.3 host report contract invalid")
    validate_runtime_identity(runtime, report["interpreter_identity"])
    for ordinal, row in enumerate(report["rounds"], 1):
        if (
            row.get("ordinal") != ordinal
            or row.get("source_sha") != SOURCE
            or row.get("seed") != SEED
            or row.get("journal_bytes", MAX_JOURNAL_BYTES + 1) > MAX_JOURNAL_BYTES
            or row.get("sampled_rss_bytes", MAX_RSS_BYTES + 1) > MAX_RSS_BYTES
            or row.get("retained_scratch_bytes", MAX_RETAINED_BYTES + 1) > MAX_RETAINED_BYTES
            or not isinstance(row.get("runtime_identity"), dict)
            or row.get("observer_hash") is None
        ):
            raise AssertionError("P7.3 host resource/ordinal contract invalid")
        validate_runtime_identity(runtime, row["runtime_identity"])
    return report


def compare_reports(cpython_path: Path, pypy_path: Path, out: Path) -> dict[str, Any]:
    try:
        cpython = _load_host(cpython_path, "cpython")
        pypy = _load_host(pypy_path, "pypy")
        parity_fields = ("selected_v7", "observer_hash", "journal_payload_sha256")
        for ordinal, (left, right) in enumerate(zip(cpython["rounds"], pypy["rounds"]), 1):
            if any(left.get(field) != right.get(field) for field in parity_fields):
                raise AssertionError(f"P7.3 parity mismatch at round {ordinal}")
        cpython_total = sum(row["native_wall_s"] for row in cpython["rounds"])
        pypy_total = sum(row["native_wall_s"] for row in pypy["rounds"])
        if pypy_total <= 0:
            raise AssertionError("P7.3 PyPy wall total is not positive")
        verdict = {
            "kind": "PERF275_P73_TWO_HOST_COMPLETE37_VERDICT",
            "source_sha": SOURCE,
            "seed": SEED,
            "rounds": ROUNDS,
            "speed_ratio": cpython_total / pypy_total,
            "cpython_total_native_wall_s": cpython_total,
            "pypy_total_native_wall_s": pypy_total,
            "max_cpython_rss_bytes": max(row["sampled_rss_bytes"] for row in cpython["rounds"]),
            "max_pypy_rss_bytes": max(row["sampled_rss_bytes"] for row in pypy["rounds"]),
            "max_cpython_journal_bytes": max(row["journal_bytes"] for row in cpython["rounds"]),
            "max_pypy_journal_bytes": max(row["journal_bytes"] for row in pypy["rounds"]),
            "report_sha256": {
                "cpython": hashlib.sha256(Path(cpython_path).read_bytes()).hexdigest(),
                "pypy": hashlib.sha256(Path(pypy_path).read_bytes()).hexdigest(),
            },
            "original_seed16384_executed": False,
            "original_seed49152_executed": False,
            "learning_claim": False,
            "status": (
                "PASS_COMPLETE37_PYPY_RUNTIME_CANDIDATE_ONLY"
                if cpython_total / pypy_total >= MIN_SPEED_RATIO
                else "REJECT_OR_HOLD_COMPLETE37_RUNTIME_GATE"
            ),
        }
    except Exception as exc:
        verdict = {
            "kind": "PERF275_P73_TWO_HOST_COMPLETE37_VERDICT",
            "source_sha": SOURCE,
            "seed": SEED,
            "rounds": 0,
            "status": "INCOMPLETE",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "original_seed16384_executed": False,
            "original_seed49152_executed": False,
            "learning_claim": False,
        }
        _write(out, verdict)
        raise
    _write(out, verdict)
    return verdict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", choices=tuple(EXPECTED_RUNTIME))
    parser.add_argument("--exe")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compare-cpython", type=Path)
    parser.add_argument("--compare-pypy", type=Path)
    args = parser.parse_args()
    if args.compare_cpython and args.compare_pypy:
        compare_reports(args.compare_cpython, args.compare_pypy, args.out)
        return
    if not args.runtime or not args.exe:
        parser.error("host mode requires --runtime and --exe")
    try:
        execute_host(args.runtime, args.exe, args.out)
    except Exception:
        raise


if __name__ == "__main__":
    main()
