# E2 #336 — compact failure evidence in the execution workflow (source-only prerequisite)

Owner: [UniverseGenome #336](https://github.com/kinoko34077/UniverseGenome/issues/336). The dormant existing original-seed study lane under review is [PR341](https://github.com/kinoko34077/UniverseGenome/pull/341); its merge was refused at the GPT/OpenAI tool preflight and remains OPEN at last check. Claude is asked for a READ_ONLY independent audit via [KAEP](https://github.com/kinoko34077/UniverseGenome/issues/336#issuecomment-6161653425). This separate PR does not edit/merge PR341, introduce the one-time marker, or execute native R2 seed544/545.

## Exact observable gap

The existing one-shot workflow uploads its actual source-native E2 report only under `if: success()`. A fail-closed original-R2 control mismatch, RSS/wall-time cap, Python exception or validation failure may stop before any completed raw JSON report exists. Actions logs retain some diagnostics, but there is no bounded original-environment failure manifest to archive into Git as requested by the research evidence policy. An absent or corrupt result must never be represented as a valid negative scientific observation.

## New narrowly scoped source-only capability

`research/a2_e2_failure_manifest_336.py` builds a **pure, deterministic, bounded metadata-only failure record**. It records exact source SHA, Actions run ID/attempt, host interpreter/platform, original accepted immutable R2 physics SHA and manifest digest, exact already-outcome-exposed positive544/negative545 candidate/conditions, fixed 900 s/1536 MiB bounds, strict stage and non-secret reason enums. It always sets `result_kind=FAILURE_METADATA_ONLY_NOT_SCIENCE_OUTCOME`, `classification=NOT_EVALUABLE_PENDING_INVESTIGATION`, `source_native_conditions_verified=false`, `original_success_report_validated=false`, `independent_confirmation=false`, `learning_claim=false`. It cannot assert which seeds actually ran or whether any physical memory was observed. JSON output <=8 KiB; file is created exclusively with no overwrite and returns its byte SHA256 for later Git archival. Reject arbitrary exception text and unbounded fields to limit accidental secret disclosure.

Independent synthetic/metadata-only tests check exact original roles/horizon, byte SHA and write-once, no fabricated success, enum/format bounds, true first-attempt restriction and missing original report distinction. Hosted CPython3.12/PyPy3.11 CI validates helper and tests; no original native physics or outcome is initiated.

## Scope, next gate and limitation

This PR creates the helper and tests only; **it does not yet connect the helper to the dormant PR341 workflow or its failure step**. First accept it with ordinary repo CI, exact-head formal review and guarded merge if permitted. Before any reviewed activation marker, a separate source review must integrate the helper into a fail-closed `if: failure()` cleanup step and artifact upload, ensuring failed native jobs retain their original failure status and log with no retries or changed seeds/conditions. It must not change the original R2 h0, teacher input, candidate, observer, use of protected R3/PhaseH or production physics. Do not infer that failure metadata alone constitutes a valid experiment or full exact archive of a failed trajectory.
