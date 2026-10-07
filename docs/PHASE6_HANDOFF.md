# Phase 6+ capability handoff

Status: **P6.1 through P6.9 accepted; no later capability is currently selected**.

Post-P6.9 learning-path work is accepted through the generalized Outer Search
implementation gate owned by #144/#145. #140 remains the latest canonical L3
result: the frozen D1 research profile retained B/H distinction 12/12 through
+100 but only **1/12 at +1000**, so robust L3 persistence is not established.
#144/#145 subsequently generalized the existing Inner/Outer architecture
without changing that result. Phase F / PR #157 ended in
`ACCEPT-OUTER-SEARCH-GENERALIZATION-IMPLEMENTATION` on main
`69cd7e99092bda565eec89daed2bb0873fd3c184`: the canonical Legacy
SearchPlan reproduces the pre-generalization Phase 5 oracle exactly, optimizer
persistence is v7 with deterministic legacy migration, and matched density4 /
density32 performance remains within the accepted 5% gate.

No new search dimension is active merely because it is registered. Production
slow-trace defaults remain `(0,0,0,0,8)`, all non-inert values remain
research-only, and `learning_claim=false` remains authoritative. Phase G
research child #159 is now active: G0 / PR #160 is accepted on main
`311d391c8264f19aae59ec699151a902bbbca2ce`, with a decay-only
research SearchPlan and disjoint h0-qualified adaptive-search / held-out
cohorts frozen before long-horizon search. G1 adaptive decay-axis search is the
first unfinished checkpoint; held-out post-h0 validation remains separately
gated as Phase H. **No automatic P6.10 is authorized.** P6.10 and L4+ remain
separately gated.

## Current v0.1 boundary

Phase 0 through Phase 5 are readiness-accepted on `main` after the fresh
#60 rerun. Status-truth remediation #66 is
complete via PR #69 and Phase 5 search-semantics remediation #65 is complete
via PR #70, merged to main as `3e8c8f31a1d87d3f2a7e88de731392b4f3202bd2`.
GUI/authoritative-search integration #63 is complete via PR #73, and
post-v0.1 residual reconciliation #61 is complete via PR #74, merged to main
as `87de79012650b44b934651c8e1ba5a7b8d91e173`. No unresolved remediation
owner remains. Readiness rerun #60 passed. P6.1 #79 / PR #80, P6.2 #82 /
PR #83, P6.3 #85 / PR #86, P6.4 #88 / PR #89, P6.5 #91 / PR #92,
P6.6 #95 / PR #96, P6.7 #98 / PR #99, P6.8 #101 / PR #102, and
P6.9 #104 / PR #105 subsequently added nine accepted bounded Phase 6
experimental capabilities.

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

PR #96 completed P6.6 predeclared held-out relation generalization. Its exact
reviewed head `2904446564f535fe650e94bd896581a70b0ebb6b` passed CI #286
(`37212729551`) with Phase 5 plus P6.1–P6.6 real experiment/optimizer smokes
and browser E2E SUCCESS before squash merge to main
`f5ac79062e35eb8206e8449ceb0a9ea015cbc961`. All 12 changed files were
verified blob-identical between reviewed head and merged main. The bounded P6.6
smoke produced teacher baseline/trained success 0→0, zero training-qualified
and generalization-eligible seeds, `generalization_rate=null`, and
`learning_claim=false`. Capability acceptance therefore does not claim
successful generalization.

PR #99 completed P6.7 bounded distinct multi-byte output sequences. Its exact
reviewed head `667095db0ee6832dcc2591ee96617b0d336e7649` passed CI #308
(`37215132723`) with 213 tests / OK, real P6.1–P6.7 experiment/optimizer
smokes and browser E2E SUCCESS before squash merge to main
`7ce83696bcea4e2410d0f95a00fe5d6487417013`. All 11 changed files were
verified blob-identical between reviewed head and merged main. The bounded P6.7
smoke produced zero trained mapped successes and `learning_claim=false`;
capability acceptance therefore does not claim successful distinct-sequence
learning.

PR #102 completed P6.8 bounded raw UTF-8 byte experiments. Its exact reviewed
head `d8d84fd64ad5af3804207dae5bf42e7409a7a223` passed CI #317
(`37218913896`) with 217 tests / OK, real P6.1–P6.8 experiment/optimizer
smokes and browser E2E SUCCESS before squash merge to main
`f203eb3c15d57c9b387a29b1ba8b493b82b7ad93`. The reviewed head and merged
main have identical Git trees. P6.8 added no Unicode/tokenizer runtime; the
accepted experiment uses numeric bytes only. The bounded smoke produced zero
trained mapped successes and `learning_claim=false`; capability acceptance
therefore does not claim successful UTF-8 learning.

PR #105 completed P6.9 bounded mixed-length raw byte sequence mappings. Its
exact reviewed head `4f8adc07439764ee5de436053f8ff4dd12b32974` passed CI #333
(`37239378797`) with 222 tests / OK, real P6.1–P6.9 experiment/optimizer
smokes and browser E2E SUCCESS before squash merge to main
`0cc2866f29c0c4ad01950bff9f8209bee85265c1`. All 11 implementation-changed
files are blob-identical between reviewed head and merged main. P6.9 keeps
mixed valid mapped inputs prefix-free, adds no tokenizer/text semantic runtime,
and leaves Phase 5 search semantics unchanged. The bounded smoke produced zero
trained mapped successes and `learning_claim=false`; capability acceptance
therefore does not claim successful mixed-length learning.

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

P6.1 through P6.9 are accepted capability layers. No later semantic capability
is currently selected. Post-P6.9 learning-emergence / learning-path research is
accepted through #127 / PR #129 without changing production physics/defaults.

#111 / PR #114 showed that density 32 improves substrate persistence/activity
but does not produce canonical A→B→NULL learning. #113 / PR #115 localized the
strongest reachable causal path at **L3 memory persistence**; L4–L7 are
NOT_EVALUABLE.

#119 separated this formal L3 result from the physical-I/O distinguishability
problem. #120 / PR #121 then established the frozen B=66/H=8 diagnostic
condition: **12/32** density-32 immediate teacher-specific writes, traceable
12/12 and HP-only, terminal route **ROUTE-MEMORY**.

#122 / PR #126 tested persistence of the exact accepted write-positive cohort
under ordinary unchanged physics. The 12 density-32 primary cases remain
B/H-distinct through +10, fall to 9/12 at +100, and only **1/12** is distinct
at +1000. Six cases reach non-HP state, but every case first splits in
lifecycle/survival and only afterward reaches latent/structure/bond differences.
The predeclared terminal classification is therefore
**ROUTE-MEMORY-ARENA**, not ROUTE-RECALL.

#127 / PR #129 tested the next bounded research-only persistence arena. Both
ENERGY_TO_LATENT_XOR and ENERGY_TO_STRUCTURE_PROMOTE create pre-lifecycle non-HP
B/H distinctions in 12/12 primary cases, but each retains only **5/12** at
+1000, below the frozen 8/12 gate. The contact-bond candidate was statically
unreachable for content-specific writes and the HP-no-decay reference retained
0/12. No candidate passes; terminal route is
**ROUTE-ARCHITECTURE-RETHINK**.

#130 completed the design-only architecture rethink and selected
**D1 Anonymous Slow Trace with Conservative Local Transfer**, routing it to
formal specification review. B1 latent echo and C1 morphology cluster remain
rejected primary candidates.

#132 / PR #134 completed specification review with **ACCEPT-SPEC-PROPOSAL**.
#135 / PR #139 has now implemented that accepted D1 contract through
TEST-ST-010 on main `9091bbbc0fdbf261859d7f1b68772601b963548e`.
Production includes `slow_trace:uint8[MAX_CELLS]`, local generic
write/transfer/discharge/decay/read semantics, UniverseState v2 / optimizer v6
migration, and the inert compatibility/default tuple `(0,0,0,0,8)`.
The frozen density-4/density-32 inert compatibility matrix passed and measured
TEST-ST-010 evidence is recorded in #135. All non-inert values remain
research-only.

#140 / PR #142 completed TEST-ST-012 with **FAIL-L3-PERSISTENCE**. The frozen
research-only profile retained B/H distinction 12/12 through +100 but only
1/12 at +1000 against the >=8/12 gate. Seed 22 demonstrated
turnover-surviving redistribution, so the turnover path is physically possible,
but robust L3 persistence remains unproven. No second profile or successor
learning mechanism has been accepted. Active-default promotion, L4 recall and
P6.10+ remain outside the current boundary. `learning_claim=false` remains
unchanged. #93 remains a separate performance/architecture workstream.

Any further work must remain bounded rather than becoming a silent change to the
historical v0.1 physics/search contract.

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
6. generalization — **P6.6 complete (#95 / PR #96)**;
7. multi-byte sequences — **P6.7 complete (#98 / PR #99)**;
8. raw UTF-8 experiments — **P6.8 complete (#101 / PR #102)**;
9. mixed-length raw byte sequences — **P6.9 complete (#104 / PR #105)**.

The original eight-item capability ladder was completed through P6.8 and the
explicitly selected P6.9 extension is also complete. This list is not permission
to invent P6.10. A further experiment requires an explicit roadmap/research
decision in #78 and one new bounded child Issue.

## Completed post-v0.1 residual boundary

Issue #61 / PR #74 resolved or explicitly reclassified the remaining Phase 0–5
P2/P3 residuals, including post-initial matched seeds, rewind memory semantics,
browser E2E depth, fragmentation RNG addressing, optimizer CLI protocol,
snapshot lineage/prune history, and implementation-default performance debt.

These items no longer form an active remediation queue. Readiness #60 has
passed. P6.1–P6.9 remain terminal capability layers. Learning-path research is
accepted through #127 / PR #129; #130 selected D1, #132 / PR #134 accepted its
specification, #135 / PR #139 implemented D1 through TEST-ST-010 under inert
defaults, and #140 / PR #142 completed TEST-ST-012 with
`FAIL-L3-PERSISTENCE`. The failed gate preserves a valid turnover witness but
does not establish robust +1000 persistence. No successor learning-path gate is
currently accepted. L4 recall, active-default promotion and P6.10+ remain
frozen.
