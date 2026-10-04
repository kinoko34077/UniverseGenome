# Phase 6+ capability handoff

Status: **P6.1 through P6.5 accepted; P6.6 generalization is the next bounded child frontier**.
No P6.6+ capability has been implemented.

## Current v0.1 boundary

Phase 0 through Phase 5 are readiness-accepted on `main` after the fresh
#60 rerun. Status-truth remediation #66 is
complete via PR #69 and Phase 5 search-semantics remediation #65 is complete
via PR #70, merged to main as `3e8c8f31a1d87d3f2a7e88de731392b4f3202bd2`.
GUI/authoritative-search integration #63 is complete via PR #73, and
post-v0.1 residual reconciliation #61 is complete via PR #74, merged to main
as `87de79012650b44b934651c8e1ba5a7b8d91e173`. No unresolved remediation
owner remains. Readiness rerun #60 passed. P6.1 #79 / PR #80, P6.2 #82 /
PR #83, P6.3 #85 / PR #86, P6.4 #88 / PR #89, and P6.5 #91 / PR #92
subsequently added the first five accepted bounded Phase 6 experimental
capabilities.

The original sequential Work Order #7 established the v0.1 phase sequence.
Earlier remediation established the current Phase 0–5 implementation boundary;
the later #64 audit found cross-phase acceptance gaps that were subsequently
repaired through #66/#65/#63/#61. The fresh #60 readiness rerun has now passed. The historical implementation boundary is documented by:

- original Phase 1–5 implementation PRs;
- completeness audit #27;
- post-remediation audit #42;
- review #54;
- Phase 5 semantic remediation #56 / PR #57;
- Phase 5 architecture restoration #58 / PR #59;
- Phase 5 search-semantics remediation #65 / PR #70;
- GUI/authoritative-search integration #63 / PR #73;
- post-v0.1 residual reconciliation #61 / PR #74;
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

The historical post-merge main CI `37137438184` succeeded with:

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

PR #70 completed #65 search-semantics remediation. Its exact reviewed head
`c6c32af9151f7c591b54df1787b9be39026fdd79` passed CI #93
(`37177555446`) with 142 tests / OK and browser E2E SUCCESS before squash
merge to current main `3e8c8f31...`.

PR #74 completed #61 residual reconciliation. Its exact reviewed head
`1441d0bf2b7faa58e265efdc263a8bbf4b3a5414` passed CI #138
(`37183145594`) with 149 tests / OK and browser E2E SUCCESS before squash
merge to current main `87de7901...`.

PR #80 completed P6.1 multiple independent byte mappings. Its exact reviewed
head `6182fa3b615da446260b7e0ef698d7761d946e49` passed CI #165
(`37190230270`) with 158 tests / OK, the real Phase 6.1 experiment smoke and
browser E2E SUCCESS before squash merge to main
`237845bb8b4512048508d8174ef328b3f36fbf52`. The bounded smoke observed
A→B baseline 0 / trained 0 and C→D baseline 0 / trained 0; no-input and
unmapped-input counterfactuals were clean and `learning_claim=false`.

PR #83 completed P6.2 temporal sequence discrimination. Its exact reviewed
head `349e4761eb0524904257415b1a93c475f7788332` passed CI #186
(`37192574567`) with 166 tests / OK, the real P6.2 experiment smoke, bounded
P6.2 optimizer integration smoke, and browser E2E SUCCESS before squash merge
to main `c6920bb9c8227c57ce0358d10353ebf7e489a7c4`. The bounded experiment
smoke observed AA→B baseline 0 / trained 0 and AC→D baseline 0 / trained 0
across three seeds; no-input, prefix-A and unmapped-CA counterfactuals were
clean and `learning_claim=false`. Capability acceptance therefore does not
claim that temporal learning has succeeded.

PR #86 completed P6.3 multi-event output timing. Its exact reviewed
head `08a6df9741f864a3482732818040667bbf865a74` passed CI #214
(`37195498334`) with 173 tests / OK, the real P6.3 experiment smoke, bounded
P6.3 optimizer integration smoke, and browser E2E SUCCESS before squash merge
to main `1df6e29687ab383fb01812ddb5c1e25cc86d6652`. The bounded experiment
smoke observed AA→B,B baseline 0 / trained 0 and AC→D,D baseline 0 / trained 0
across three seeds; no-input, prefix-A and unmapped-CA counterfactuals were
clean and `learning_claim=false`. Capability acceptance therefore does not
claim that timed multi-event learning has succeeded.

PR #89 completed P6.4 forgetting/relearning retention. Its exact reviewed head
`e7104fb249b7ccdf06411b6522e55d0cc7452861` passed CI #238
(`37204968652`) with 183 tests / OK, real P6.4 experiment/optimizer smokes,
and browser E2E SUCCESS before squash merge to main
`ce9e54ad9290756ca5ed57863544874989a12527`. Exact-main push CI #239
(`37205180423`) also passed. The bounded experiment produced no T0-success
cases, so retention/relearning were non-evaluable (`null`) and
`learning_claim=false`. Capability acceptance therefore does not claim
learned retention or relearning.

PR #92 completed P6.5 controlled physical-noise robustness. Its exact reviewed
head `88529c1b1fc93f0f8a6a0214647600ff03558c0c` passed CI #258
(`37208735557`) with 193 tests / OK, real P6.1–P6.5 experiment/optimizer
smokes, and browser E2E SUCCESS before squash merge to main
`cb19ba9467e9a1ccb9586e00445d049d4b700cd7`. All 14 changed files were
verified blob-identical between reviewed head and merged main. The bounded P6.5
smoke produced zero clean-success eligible cases, so noise robustness was
non-evaluable (`null`) and `learning_claim=false`. Capability acceptance
therefore does not claim learned noise robustness.

The previous #60 PASS remains historical and invalidated by the later full
traceability audit #64 and handoff #67/#68. Remediation and residual
reconciliation are complete, and the fresh #60 rerun has established the
current readiness result.

## Phase 4 outcome

The declared multi-seed `A → B → NULL` criterion was not met:

- baseline successes: 0;
- trained successes: 0;
- learning claim: false.

This is a recorded experimental outcome. It must not be reinterpreted as
success, loosened after the fact, or bypassed with semantic shortcuts.

## Phase 6 boundary

P6.1 through P6.5 are accepted capability layers. Later Phase 6 work
must remain bounded rather than becoming a silent change
to the historical v0.1 physics/search contract.

Before any Phase 6 mutation:

1. reread live devflow Control #314;
2. create one new explicit repository-local child Issue with measurable
   acceptance criteria;
3. keep the new capability behind the Phase 6 boundary;
4. preserve deterministic replay, authoritative-state separation and the
   no-semantic-shortcut rule.

## Candidate capability order

Candidate order remains:

1. `A→B` and `C→D` mappings — **P6.1 complete (#79 / PR #80)**;
2. temporal sequences such as `AA→B` and `AC→D` — **P6.2 complete (#82 / PR #83)**;
3. multi-event output timing — **P6.3 complete (#85 / PR #86)**;
4. forgetting and relearning — **P6.4 complete (#88 / PR #89)**;
5. noise robustness — **P6.5 complete (#91 / PR #92)**;
6. generalization — **next bounded frontier**;
7. multi-byte sequences;
8. raw UTF-8 experiments.

This ordering is a handoff sequence, not permission to implement all items in
one work unit. Start with one bounded child Issue.

## Completed post-v0.1 residual boundary

Issue #61 / PR #74 resolved or explicitly reclassified the remaining Phase 0–5
P2/P3 residuals, including post-initial matched seeds, rewind memory semantics,
browser E2E depth, fragmentation RNG addressing, optimizer CLI protocol,
snapshot lineage/prune history, and implementation-default performance debt.

These items no longer form an active remediation queue. Readiness #60 has
passed; the next gate is the acceptance contract of the new bounded Phase 6
child Issue itself.
