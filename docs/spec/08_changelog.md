# Specification Changelog

## 2026-10-04 — Issue #61 residual reconciliation candidate

- preserves the canonical Phase 4 evaluation timeout on the public optimizer
  CLI by default and labels any explicit timeout override in JSON output;
- adds a bounded real-entry optimizer CLI smoke to CI using an explicit
  timeout-8 override rather than silently changing the research protocol;
- replaces reusable storage-slot fragmentation probability addressing with
  physical event addressing under SPEC-RNG-002 while keeping deterministic
  split-mask addressing separate;
- clarifies the 256 MiB rewind figure as measured guidance while 128/256/512
  history cardinality remains the normative bound;
- expands browser E2E across observation-clone rewind, optimizer Save/Load,
  locked detail mode, and staged Reset parameters;
- preserves post-initial matched genome/seed comparison where practical by
  preferring a same-genome seed already represented in another category when
  that seed is free locally, without cross-category selection coupling;
- upgrades Phase 5 optimizer snapshots to format v5 with a durable
  `parent_genome_key` separate from reusable `parent_index`, plus explicit
  event-level history for targets actually retired/replaced; legacy v4
  snapshots remain readable and upgrade on the next save;
- records the existing fixed-length Python-list authoritative state as an
  explicit SPEC-IMPL-001 implementation-default deviation; NumPy/Numba
  migration is deferred until profiling or a concrete performance target shows
  benefit, without changing upper-level state/physics contracts.

## 2026-10-04 — Issue #63 authoritative Phase 5 browser integration

- replaces the browser server's parallel Phase 3 population authority with the
  existing 128-slot `SteadyStateOptimizer`;
- overview/detail payloads now project the real category/genome/seed,
  fitness/growth, evidence, lineage/allocation and replacement state;
- separates outer Search Run/Pause/Search Step from clone-only physical
  observation stepping and rewind;
- Save/Load now round-trips the authoritative Phase 5 optimizer snapshot;
- the server loads the canonical default physical config instead of inventing a
  GUI-only `initial_density=4` runtime;
- manual base-config edits are staged for Reset and do not mutate running slots;
- the activity display is explicitly retained as a visualization-only proxy,
  not optimizer `activity_cost`;
- Playwright E2E verifies that a real optimizer replacement is visible through
  the browser without rebuilding a parallel population;
- P1 remediation is complete after this changeset; #61 residual reconciliation
  and #60 readiness rerun remain before Phase 6.

## 2026-10-04 — Issue #65 Phase 5 search-semantics remediation accepted (#65 / PR #70)

- executes the accepted 16-generation short-health cadence on authoritative
  physical time and retires explicit all-active-cell loss as an absolute
  failure;
- defines persistent non-response through task-level autonomous output evidence:
  four consecutive no-output observations at real 128-generation boundaries
  while active cells remain, covering the 512-generation stagnation horizon;
- preserves canonical growth bit 5/6 semantics as retention/noise robustness,
  keeps Phase 4 no-input/alternate-input cleanliness as separate observables,
  and leaves integrated v0.1 retention/noise fields inactive until an explicit
  later measurement protocol is accepted;
- accepts and implements the Human-approved `tiered_category_rank` policy for
  real-slot evidence escalation: category-local aggregate canonical fitness,
  4→8 top 1/2, 8→16 top 1/4, 16→32 top 1/8, with deterministic per-category
  1:1 evidence/mutation scheduling after provisional groups reach four seeds;
- repairs integrated mutation to explore valid adjacent binary-grid directions
  without no-op children and constrains effective `initial_density` mutation
  to `PhysicsConfig.max_cells`;
- preserves the 128 authoritative-slot, category-isolation, real-seed evidence,
  free/prune-target-only replacement, and deterministic snapshot boundaries;
- exact reviewed head `c6c32af9151f7c591b54df1787b9be39026fdd79`
  passed CI #93 (`37177555446`) with 142 tests / OK and browser E2E SUCCESS,
  then squash-merged to main as
  `3e8c8f31a1d87d3f2a7e88de731392b4f3202bd2`.

## 2026-10-04 — Issue #65 Phase 5 search-liveness remediation (historical checkpoint)

This checkpoint is superseded by the later Issue #65 remediation candidate
above; its unresolved-gate wording records the state before the Human policy
decision and persistent-response protocol were completed.

- connected the accepted 16-generation short-health cadence to authoritative
  physical-step metrics and recorded the explicit all-active-cell-loss failure
  reason;
- made that accepted absolute failure retirement-eligible independently of
  growth history, leader protection, or provisional minimum-evidence maturity;
- constrained integrated mutation to valid adjacent binary-grid values,
  including the effective `initial_density <= max_cells` bound and deterministic
  opposite-direction fallback;
- kept the canonical growth bit 5/6 meanings (`retention` and `noise
  robustness`) separate from Phase 4 counterfactual observables; the
  persistent-non-response predicate and promising-allocation policy remain
  unresolved specification gates.

## 2026-10-04 — Audit #64 / Issues #66/#67/#68 current-state correction

- distinguished Phase 0–5 implementation presence from current acceptance and
  readiness; unresolved P1 owners #66, #65, and #63 keep Phase 6+ blocked;
- recorded #60 as the later readiness rerun owner and retained its earlier PASS
  only as historical evidence;
- marked the Phase 5 implementation plans as historical execution records whose
  checkboxes do not define Current State;
- added the missing Phase 2D acceptance trace `#16 / PR #17` and corrected the
  historical Issue #8 `REQ-083` reference without introducing a new requirement.

## 2026-10-03 — Issue #58 Phase 5 authoritative Universe-slot corrections

- restored the original 128-authoritative-Universe architecture: one persistent
  `UniverseState` per category/genome/seed slot, with seed evidence represented
  by actual slot allocation rather than hidden CandidateSlot state;
- separated persistent training generations from disposable evaluation-clone
  generations and made growth observations real 128-generation boundaries;
- established observed generation-0 references, removed synthetic growth
  windows, persisted authoritative slot arrays, and retained the promising
  allocation policy as an explicitly unapproved hook pending a specification
  decision.

## 2026-10-03 — Issue #56 Phase 5 semantic corrections

- recorded the earlier Phase 5 seed-evidence model as superseded by the
  authoritative-slot allocation model in the #58 entry above;
- added eight distinct deterministic initial parameter genomes per category;
- normalized absolute fitness across evidence counts and mapped wrong outputs,
  timeout, first-response latency, and physics activity to explicit observables;
- gated growth history on 128 physical evaluation generations and corrected the
  zero-median pruning threshold;
- removed unused reconstructed universe snapshots from authoritative optimizer
  persistence and updated the bounded headless evidence path.

## 2026-10-03 — Audit #27 remediation completed
- Phase 4 remediation #28 / PR #32 (`4eccfddf4a2f14dfa423613499f22f67559aec24`)
  connects autonomous scoring to real output-edge collection while retaining
  the baseline 0 / trained 0 / no-learning-claim result.
- Phase 3 remediation #29 / PR #33 (`2ff7f429f332b4cbbe1fca4c886b0b5ec9e63b93`)
  connects the browser observer/control surface to the bounded,
  server-owned runtime API.
- Phase 5 remediation #30 / PR #34 (`02b07bb8dae7f649d543f8386d421064c6977a55`)
  maps all genome fields to effective physics, evaluates candidates through
  the real Phase 4 collector, and exposes bounded replacement escalation.
- Configuration, CI labels, specification status, README routing, roadmap,
  and Phase 6+ handoff wording were reconciled under remediation #31.
- Residual P2 remediation #36 / PR #39 (`4da092151d7e89687515b9281209c5d1f79c7cd6`)
  reconciles physical ordering, structure degradation, local BLACK_HOLE revival,
  and one-event noise/randomness behavior.
- Residual P2 remediation #37 / PR #40 (`4fe87b2f32662d7445bc8084dc91d07e2a029d42`)
  adds bounded optimizer snapshot/restore, growth-only fitness/pruning fields,
  and measured headless population performance.
- Residual P3 remediation #38 / PR #41 reconciles package phase metadata,
  canonical rotate-operator naming, fixed I/O coordinates, and documented
  black-hole/noise defaults without rewriting historical records.

## 2026-10-03 — v0.1 specification basis established
- Issue #2 preserves historical rationale.
- Issue #3 requirements are canonicalized to `docs/spec/01_requirements.md`.
- Issue #4 detailed specification is split across `docs/spec/`.
- ADR-001..ADR-008 preserve architecture rationale.
- Phase 0/1 boundary remains explicit.
- No runtime physics capability is claimed by this specification-only checkpoint.

Future physical-rule changes must record affected REQ/SPEC IDs, old/new behavior, rationale, test impact, snapshot/compatibility impact and status changes.

## 2026-10-03 — Phase 1 accepted (#8 / PR #9)
- `core/physics.py` now implements the bounded deterministic single-universe
  step: fixed-point torus movement, destination-only footprints, tunneling,
  spatial buckets, bounded collision pairing, HP/lifecycle handling, noise and
  performance counters.
- `core/state.py` and `persistence/snapshot.py` provide reusable fixed slots,
  no permanent Cell ID, and versioned continuation-equivalent snapshots.
- `core/runner.py` provides a headless Phase 1 JSON run surface.
- Exact-head CI, formal review, PR merge, and post-main verification completed
  on merge commit `243ec24100cd96c051267ef53a74ca58652cb4b2`.

## 2026-10-03 — Phase 2A bond/contact implementation candidate (#10)
- `core/physics.py` now updates local `bond_strength:uint8` with explicit,
  saturating gain/decay parameters for compatible destination contact.
- Headless metrics expose compatible bond contacts, while bounded destination
  pair resolution remains unchanged.
- Phase 2B latent operators and all later phases were deferred pending a later
  child Issue.

## 2026-10-03 — Phase 2A accepted (#10 / PR #11)
- Local `bond_strength:uint8` gain/decay, deterministic contact accounting,
  snapshot continuation, and headless bond metrics passed exact-head review,
  merge, and post-main CI on `1e0a1fa0bae9a599d4f4f17564a4683d9f292992`.

## 2026-10-03 — Phase 2B latent operator implementation candidate (#12)
- `core/physics.py` implements deterministic 1..16-bit local masks and the four
  accepted 16-bit latent operator families with synchronous updates.
- Successful local transmission contributes activity for HP recovery and is
  exposed in headless metrics.
- Phase 2C fusion and later phases were deferred pending #12 acceptance.

## 2026-10-03 — Phase 2B accepted (#12 / PR #13)
- Deterministic local masks, four latent operators, synchronous propagation,
  activity recovery, snapshot continuation and headless transmission metrics
  passed exact-head review, merge, and post-main CI on
  `ee9a36d573707aeb9835c82f941beb526485c46f`.

## 2026-10-03 — Phase 2C fusion implementation candidate (#14)
- `core/physics.py` discovers bounded local exact 2×2 footprint covers and
  commits deterministic upper-level cores with the specified HP, direction,
  speed, age, bond, latent mixer and slot reuse behavior.
- Phase 2D fragmentation and later phases remain deferred pending #14
  acceptance.

## 2026-10-03 — Phase 2C accepted (#14 / PR #15)
- Bounded local exact 2×2 fusion, deterministic upper-level result state,
  latent mixer, HP/slot lifecycle and snapshot continuation passed exact-head
  review, merge, and post-main CI on
  `9d860c5e7cc61df647bc7c36c7f465854af565fa`.

## 2026-10-03 — Phase 2D fragmentation implementation candidate (#16)
- `core/physics.py` implements deterministic fixed-capacity fragmentation,
  level-0 collapse/deletion, latent/HP/age split and headless counters.
- Phase 2E aging and later phases remain deferred pending #16 acceptance.

## 2026-10-03 — Phase 2D accepted (#16 / PR #17)
- Deterministic fragmentation, bounded slot reuse, split-state semantics, and
  continuation evidence passed the Phase 2D acceptance boundary.
- Phase 2E aging remained deferred to #18 / PR #19 at this checkpoint.

## 2026-10-03 — Phase 2E aging implementation candidate (#18)
- `core/physics.py` implements safe highest-set-bit age classes and
  deterministic power-of-two fragmentation pressure with uint16 saturation.
- Phase 3 and later runtime/learning work remains deferred pending #18
  acceptance.

## 2026-10-03 — Phase 3 runtime/observation implementation candidate (#20)
- `core/population.py` implements four isolated categories × 32 slots,
  matched genome/seed metadata, compact bounded history, rewind, clone, and
  population snapshot/headless summary surfaces.
- The static UI exposes the 16×8 overview, detail modes, and required controls;
  the authoritative simulation clock remains in the core.
- Phase 4 I/O learning and later work remain deferred pending #20 acceptance.

## 2026-10-03 — Phase 4 I/O implementation candidate (#22)
- `core/io_bus.py` defines fixed 8-bit input/output buses, organ coordinates,
  and rising-edge byte/NULL events.
- `core/experiment.py` defines teacher episodes, autonomous clone evaluation,
  and a multi-seed baseline-vs-trained measurement.
- Current measurement is baseline 0 / trained 0; no learning claim is made.
- Phase 5 optimization and later work remain deferred pending #22 acceptance.

## 2026-10-03 — Phase 5 optimizer implementation candidate (#24)
- `search/genome.py`, `search/fitness.py`, `search/pruning.py`, and
  `search/evolution.py` implement separated genome fields, lexicographic
  fitness, bounded growth/pruning, binary mutation, and seed escalation.
- The Phase 4 baseline 0 / trained 0 outcome remains a failed learning claim;
  Phase 5 is diagnostic outer-search machinery only.
- Phase 6+ remains handoff-only pending #24 acceptance.

## 2026-10-03 — Phase 2E accepted (#18 / PR #19)
- Deterministic age-class pressure passed exact-head review, merge, and
  post-main CI on `ff4135ae806994ee5f1f18077d241bdfc5f72212`.

## 2026-10-03 — Phase 3 accepted (#20 / PR #21)
- The 128-slot runtime, bounded observation history, clone isolation, and UI
  surface passed exact-head review, merge, and post-main CI on
  `248fa86b6529044f336d24c6d46315959eea2d2a`.

## 2026-10-03 — Phase 4 accepted (#22 / PR #23)
- Fixed I/O, edge events, teacher exclusion, clone evaluation, and the
  multi-seed measurement passed exact-head review, merge, and post-main CI on
  `83ce864d71b81d39cf339c1c701ebecaefcc425a`.
- Baseline 0 / trained 0 produced no learning claim.

## 2026-10-03 — Phase 5 accepted (#24 / PR #25)
- Genome separation, lexicographic fitness, bounded growth/pruning, mutation,
  seed escalation and optimizer diagnostics passed exact-head review, merge,
  and post-main CI on `7304782ca66f883605a9466643172b864dfd5e0d`.
- Phase 6+ remains a durable handoff, not an automatic continuation.
