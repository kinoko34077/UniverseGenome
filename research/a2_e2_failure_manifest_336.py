"""E2 #336 — bounded honest failure-provenance record, no physics execution.

This module is deliberately independent of the E2 runner. It creates a
compact record only from GitHub execution metadata and fixed original study
protocol references. It does NOT interpret native results as a science
outcome or claim observed/unobserved seed parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
import re
import sys
from typing import Any

ORIGINAL_SOURCE = "af568ac1558f2f3f86e51341208f5b51557b7a39"
ORIGINAL_MANIFEST = "3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543"
SCHEMA = "UG_A2_E2_NON_OUTCOME_FAILURE_RECORD_V1"
STAGES = frozenset(("source-preflight", "native-physics", "report-validation"))
REASONS = frozenset(("STEP_FAILED", "RESOURCE_LIMIT", "PROCESS_TIMEOUT", "VALIDATION_FAILED", "UNKNOWN"))
MAX_BYTES = 8192


def build_failure_record(*, stage: str, reason: str, source_sha: str,
                         run_id: str, attempt: int, original_output_exists: bool) -> dict[str, Any]:
    if stage not in STAGES or reason not in REASONS:
        raise ValueError("E2 failure stage/reason is not a fixed safe code")
    if not re.fullmatch("[0-9a-f]{40}", source_sha):
        raise ValueError("E2 exact Git source SHA required")
    if not re.fullmatch("[1-9][0-9]{0,19}", run_id):
        raise ValueError("E2 run id must be positive and bounded")
    if type(attempt) is not int or attempt != 1:
        raise ValueError("E2 only first accepted run attempt may be recorded")
    if type(original_output_exists) is not bool:
        raise ValueError("E2 output-existence evidence must be Boolean")
    return {
        "schema": SCHEMA,
        "issue": 336,
        "classification": "NOT_EVALUABLE_PENDING_INVESTIGATION",
        "result_kind": "FAILURE_METADATA_ONLY_NOT_SCIENCE_OUTCOME",
        "stage": stage,
        "reason_code": reason,
        "execution": {
            "run_id": run_id,
            "attempt": attempt,
            "source_sha": source_sha,
            "python": platform.python_version(),
            "implementation": sys.implementation.name,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "fixed_protocol": {
            "original_source_sha": ORIGINAL_SOURCE,
            "original_r2_manifest_sha256": ORIGINAL_MANIFEST,
            "positive_exposed_seed": 544,
            "negative_exposed_seed": 545,
            "candidate": "rotate_copy",
            "rotate_amount": 4,
            "post_h0_steps_planned": 1000,
            "rss_limit_mib": 1536,
            "wall_limit_sec": 900,
        },
        "original_success_report_exists": original_output_exists,
        "original_success_report_validated": False,
        "source_native_conditions_verified": False,
        "independent_confirmation": False,
        "learning_claim": False,
        "note": "This file records a failed execution path only; never infer whether any seed was processed or science effect observed.",
    }


def write_failure_record(path: Path, **kwargs: Any) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError("E2 failure record must never overwrite an existing report")
    result = build_failure_record(**kwargs)
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(raw) > MAX_BYTES:
        raise ValueError("E2 failure manifest exceeded compact bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(raw)
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "path": str(path)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=sorted(STAGES), required=True)
    p.add_argument("--reason", choices=sorted(REASONS), required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--attempt", required=True, type=int)
    p.add_argument("--report-path", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    status = write_failure_record(
        args.output,
        stage=args.stage,
        reason=args.reason,
        source_sha=args.source_sha,
        run_id=args.run_id,
        attempt=args.attempt,
        original_output_exists=args.report_path.is_file(),
    )
    print(json.dumps(status, sort_keys=True))


if __name__ == "__main__":
    main()
