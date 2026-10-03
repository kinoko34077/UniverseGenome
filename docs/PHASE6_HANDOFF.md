# Phase 6+ capability handoff

Status: **ready for a new bounded Phase 6 child Issue after readiness audit #60**.
No Phase 6+ capability has been implemented.

## Accepted v0.1 boundary

Phase 0 through Phase 5 are accepted on `main`.

The original sequential Work Order #7 established the v0.1 phase sequence.
Subsequent audits found acceptance gaps that were repaired before this handoff.
The current Phase 0–5 implementation boundary is established by:

- original Phase 1–5 implementation PRs;
- completeness audit #27;
- post-remediation audit #42;
- review #54;
- Phase 5 semantic remediation #56 / PR #57;
- Phase 5 architecture restoration #58 / PR #59;
- readiness audit #60.

PR #59 restored the original Phase 5 architecture and merged as
`5844e989706afce7988c4b8d50f94fc33afb1228`:

- exactly 128 persistent authoritative Universe slots;
- four category-local groups of 32;
- one category + one genome + one seed + one persistent UniverseState per slot;
- matched initial genome/seed positions across categories;
- same-genome fitness aggregated across real seed slots;
- evaluation clones discarded without advancing authoritative learning time;
- observed generation 0 / 128 / 256 / 384 / 512 growth boundaries;
- free/prune-target-only steady-state replacement;
- four-real-seed minimum for parent/protection eligibility;
- provisional versus depleted-mature evidence lifecycle;
- deterministic optimizer snapshot/restore.

Post-merge main CI `37137438184` succeeded with:

- Python test suite: **130 tests / OK**;
- Playwright Chromium browser E2E: **1 passed**.

### Historical acceptance markers

For continuity with earlier audit evidence, the pre-readiness Phase 5 history is
retained as historical evidence rather than current state:

- remediation PR #34 merged at
  `02b07bb8dae7f649d543f8386d421064c6977a55`;
- the later pre-#42 baseline reached
  `4fe87b2f32662d7445bc8084dc91d07e2a029d42`;
- that checkpoint reported **84/84** tests and main CI `37116004528`.

These markers are superseded as current evidence by PR #59,
`5844e989706afce7988c4b8d50f94fc33afb1228`, and CI `37137438184`.

Readiness audit #60 found no unresolved P0/P1 in the accepted Phase 0–5 runtime
path. Non-blocking P2/P3 residuals are tracked separately in #61 and do not
change the accepted v0.1 boundary.

## Phase 4 outcome

The declared multi-seed `A → B → NULL` criterion was not met:

- baseline successes: 0;
- trained successes: 0;
- learning claim: false.

This is a recorded experimental outcome. It must not be reinterpreted as
success, loosened after the fact, or bypassed with semantic shortcuts.

## Phase 6 boundary

Phase 6 must remain a new bounded capability layer rather than a silent change
to the accepted Phase 0–5 physics/search contract.

Before mutation:

1. reread live devflow Control #314;
2. reread this handoff and the task-relevant canonical specs;
3. create a new explicit repository-local child Issue with measurable
   acceptance criteria;
4. keep any new capability behind the Phase 6 boundary;
5. preserve deterministic replay, authoritative-state separation and the
   no-semantic-shortcut rule.

## Candidate capability order

Candidate order remains:

1. `A→B` and `C→D` mappings;
2. temporal sequences such as `AA→B` and `AC→D`;
3. multi-event output timing;
4. forgetting and relearning;
5. noise robustness;
6. generalization;
7. multi-byte sequences;
8. raw UTF-8 experiments.

This ordering is a handoff sequence, not permission to implement all items in
one work unit. Start with one bounded child Issue.

## Non-blocking follow-up boundary

Issue #61 tracks Phase 0–5 residuals that did not rise to P0/P1 during readiness
audit #60, including:

- explicit SPEC-PRUNE-004 absolute-failure handling;
- post-initial matched-seed preservation where practical;
- rewind memory-budget semantics;
- deeper browser E2E coverage.

Those follow-ups remain separate from the first bounded Phase 6 capability
unless a concrete dependency is identified.
