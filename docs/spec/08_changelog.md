# Specification Changelog

## 2026-10-05 — Phase 6.9 mixed-length raw byte sequence implementation candidate (#104)

- extends the accepted raw-byte protocol so one experiment can coexist with
  one-, two- and three-byte mappings without padding or truncation;
- retains legacy fixed-length P6.1–P6.8 validation while allowing bounded mixed
  mapping-specific output-event counts;
- canonical mappings are 41→42, 43 44→45 46 and 47 48 49→4A 4B 4C, with
  prefix 47 48 and unmapped 4D 4E controls;
- teacher/evaluation timing derives expected output count from each mapping's
  declared bytes;
- adds canonical/smoke configs, snapshot/timeout preservation, truthful public
  length/evidence fields and real P6.9 experiment/optimizer CI entrypoints;
- preserves Phase 5 search/growth semantics, byte-only protocol authority and
  the honest-learning-claim boundary.

## 2026-10-05 — Phase 6.8 bounded raw UTF-8 byte experiments accepted (#101 / PR #102)

- reuses the accepted P6.7 byte-sequence runtime rather than adding a tokenizer,
  Unicode semantic state or decoded-text scoring path;
- adds canonical numeric-byte mappings C3 A9→C3 B1 and C3 B6→C3 B8 with
  prefix C3 and unmapped C3 A7 controls;
- host-side tests verify those arrays are valid UTF-8 encodings while
  training/evaluation remain byte-only;
- adds canonical/smoke configs, snapshot/timeout preservation tests, public raw
  byte evidence assertions and real P6.8 experiment/optimizer CI entrypoints;
- keeps Phase 5 fitness/search policy and growth bit7 unchanged and preserves
  all P6.1–P6.7 protocol behavior;
- exact reviewed implementation head
  `d8d84fd64ad5af3804207dae5bf42e7409a7a223` passed CI #317
  (`37218913896`) with 217 tests / OK, P6.1–P6.8 real smokes and browser E2E;
- exact-head review `5407267240` had no blocking finding;
- squash-merged implementation main
  `f203eb3c15d57c9b387a29b1ba8b493b82b7ad93`; reviewed head and merged main
  have identical full Git trees;
- bounded P6.8 smoke produced zero trained mapped successes and
  `learning_claim=false`; capability implementation is not a UTF-8 learning
  success claim;
- after P6.8 acceptance, any next capability requires an explicit new roadmap
  decision; no automatic P6.9 is authorized.

## 2026-10-05 — Phase 6.7 bounded distinct multi-byte sequences accepted (#98 / PR #99)

- extends two-event temporal mappings from repeated identical output bytes to
  explicit ordered distinct byte tuples;
- bounded mappings are AA→B,C→NULL and AC→D,E→NULL;
- preserves legacy P6.1–P6.6 mapping serialization and repeated-byte behavior
  when no explicit `output_bytes` tuple exists;
- teacher execution and disposable-clone evaluation use one resolved output
  sequence, requiring exact content, order, count, inter-event timing and NULL;
- adds canonical/smoke P6.7 configs, snapshot/timeout preservation, public
  declared/observed sequence evidence and real experiment/optimizer CI lanes;
- keeps baseline-relative/counterfactual-gated learning claims, Phase 5
  absolute fitness/search policy and reserved growth bit7 unchanged;
- exact reviewed implementation head
  `667095db0ee6832dcc2591ee96617b0d336e7649` passed CI #308
  (`37215132723`) with 213 tests / OK, P6.1–P6.7 real smokes and browser E2E;
- exact-head review `5407048901` had no blocking finding;
- squash-merged implementation main
  `7ce83696bcea4e2410d0f95a00fe5d6487417013`; all 11 changed files were
  verified blob-identical to the reviewed head;
- bounded P6.7 smoke produced zero trained mapped successes and
  `learning_claim=false`; capability acceptance does not claim successful
  distinct-sequence learning;
- the next bounded frontier is P6.8 raw UTF-8 experiments.

## 2026-10-05 — Phase 6.6 held-out relation generalization accepted (#95 / PR #96)

- adds one predeclared held-out relation, AE→F,F→NULL, while teacher training
  remains limited to AA→B,B→NULL and AC→D,D→NULL;
- validates one fixed prefix and the explicit second-byte+1 relation across
  teacher and held-out cases before measurement;
- records baseline and trained held-out outcomes on separate disposable clones
  without advancing authoritative training state;
- requires baseline-relative teacher improvement plus clean counterfactuals for
  training qualification, excludes innate held-out success from eligibility,
  and reports null generalization when no eligible seed exists;
- keeps generalization measurement/reporting outside Phase 5 absolute fitness
  and leaves reserved growth bit7 unused;
- preserves the held-out protocol through ExperimentConfig, optimizer snapshots
  and explicit timeout reconstruction;
- adds canonical/smoke P6.6 configs, public per-seed/aggregate evidence and real
  P6.6 experiment/optimizer CI entrypoints;
- bounded public P6.6 smoke produced baseline/trained teacher successes 0→0,
  `training_qualified_count=0`, `generalization_eligible_count=0` and
  `generalization_rate=null`; all three held-out baseline/trained evaluations
  were unsuccessful and `learning_claim=false`;
- this is explicitly non-evaluable generalization because the prerequisite
  teacher learning did not qualify, not a generalized or generalization-failed
  claim; capability acceptance does not imply that the current universe
  generalized.
- exact reviewed implementation head
  `2904446564f535fe650e94bd896581a70b0ebb6b` passed CI #286
  (`37212729551`) with Phase 5 plus P6.1–P6.6 real smokes and browser E2E;
- exact-head review `5406864275` had no blocking finding;
- squash-merged implementation main:
  `f5ac79062e35eb8206e8449ceb0a9ea015cbc961`;
- all 12 implementation files were verified blob-identical between reviewed
  head and merged main;
- the next bounded frontier is P6.7 multi-byte sequences; P6.8 raw UTF-8
  remains deferred.

## 2026-10-04 — Phase 6.5 controlled physical-noise robustness accepted (#91 / PR #92)

- adds explicit experiment-level `noise_robustness_rate_delta`, with canonical
  delta 256 and a separate bounded-smoke delta 65535;
- evaluates clean and noisy conditions from matched trained T0 disposable
  clones, changing only noisy-clone physical `noise_rate`;
- uses the existing deterministic background-noise physics rather than a
  synthetic robustness shortcut;
- requires clean mapped success for eligibility and noisy mapped success plus
  noisy no-input/prefix-A/unmapped-CA cleanliness for robust classification;
- records explicit eligible/robust/failed counts and null robustness when no
  clean-success evidence exists;
- activates canonical growth bit 6 only from comparable explicit P6.5 evidence,
  leaving absolute fitness and P6.4 retention/bit5 unchanged;
- preserves the protocol through ExperimentConfig, optimizer snapshot and
  explicit timeout reconstruction;
- adds canonical/smoke configs, public clean/noisy evidence reporting, and real
  P6.5 experiment/optimizer CI entrypoints;
- exact reviewed implementation head
  `88529c1b1fc93f0f8a6a0214647600ff03558c0c` passed CI #258
  (`37208735557`) with 193 tests / OK, P6.1–P6.5 experiment/optimizer smokes
  and browser E2E SUCCESS;
- squash-merged implementation main
  `cb19ba9467e9a1ccb9586e00445d049d4b700cd7`, with all 14 changed files
  verified blob-identical to the reviewed head;
- bounded public P6.5 smoke produced zero clean-success eligible cases, so
  robustness remained null/non-evaluable and `learning_claim=false`;
- capability acceptance is not a robustness-success claim; the next bounded
  frontier is P6.6 generalization.

## 2026-10-04 — Phase 6.4 forgetting/relearning accepted (#88 / PR #89)

- extends the accepted P6.3 timed mappings with explicit T0 immediate,
  T1 delayed/interfered and T2 post-relearning clone evaluations on one
  continuing training state;
- adds a canonical 128-generation no-teacher retention delay, one deterministic
  unmapped-CA interference episode and one same-curriculum relearning pass,
  while keeping P6.5 stochastic noise robustness separate;
- records explicit retention eligibility, retained/forgotten,
  relearning-eligible/relearned counts and null rates when no denominator
  exists;
- permits canonical growth bit 5 to use genuine evaluable P6.4 retention
  evidence while preserving the absolute-fitness ordering and all Phase 5
  search/category semantics;
- preserves P6.4 protocol fields through ExperimentConfig, optimizer snapshots
  and explicit timeout reconstruction;
- adds canonical and bounded-smoke configs, public T0/T1/T2 reporting, and real
  P6.4 experiment/optimizer CI smokes;
- exact reviewed implementation head
  `e7104fb249b7ccdf06411b6522e55d0cc7452861` passed CI #238
  (`37204968652`) with 183 tests / OK, P6.1–P6.4 experiment/optimizer
  smokes, and browser E2E SUCCESS;
- squash-merged implementation main
  `ce9e54ad9290756ca5ed57863544874989a12527`, whose exact-main push CI #239
  (`37205180423`) also passed;
- bounded public P6.4 smoke produced zero T0-success eligible cases, therefore
  retention and relearning were explicitly non-evaluable (`null`) and
  `learning_claim=false`;
- capability acceptance is not a retention-success claim; the next bounded
  frontier is P6.5 noise robustness.


## 2026-10-04 — Phase 6.3 multi-event output timing accepted (#85 / PR #86)

- extends the accepted P6.2 temporal mappings with a bounded repeated-output
  protocol: AA→B,B→NULL and AC→D,D→NULL;
- adds explicit repeated-byte event count and physical-generation onset interval
  while preserving one-event P6.1/P6.2 compatibility;
- keeps teacher output as one-generation external stimulation on one continuing
  authoritative training Universe and spaces repeated events by the declared
  onset interval before NULL;
- makes isolated-clone success depend on exact byte content/order/count plus the
  declared repeated-event interval; timing mismatches remain visible through the
  existing wrong-output/error surface;
- preserves no-input, prefix-A and unmapped-CA counterfactual gates and keeps
  failed learning as `learning_claim=false`;
- preserves P6.3 count/interval through ExperimentConfig, optimizer snapshot and
  explicit timeout reconstruction without changing Phase 5 search policy;
- adds canonical and bounded-smoke P6.3 configs, per-seed event-generation
  reporting, and real experiment/optimizer CI smokes;
- exact reviewed head `08a6df9741f864a3482732818040667bbf865a74`
  passed CI #214 (`37195498334`) with 173 tests / OK, real P6.3
  experiment/optimizer smokes, and browser E2E SUCCESS;
- squash-merged implementation main:
  `1df6e29687ab383fb01812ddb5c1e25cc86d6652`;
- bounded public smoke: 3 seeds × 2 timed mappings, AA→B,B 0→0 and AC→D,D 0→0;
  no-input, prefix-A and unmapped-CA counterfactuals clean,
  `learning_claim=false`;
- capability acceptance is therefore not a learning-success claim; P6.7
  arbitrary distinct output-byte sequences remain deferred and the next bounded
  frontier is P6.4 forgetting/relearning.


## 2026-10-04 — Phase 6.2 temporal sequence discrimination accepted (#82 / PR #83)

- extends protocol mappings with bounded ordered two-byte inputs, beginning with
  AA→B and AC→D while preserving P6.1 one-byte compatibility;
- adds explicit inter-input timing and guarantees teacher output begins only
  after complete sequence delivery on one continuing authoritative training
  Universe;
- evaluates each sequence on isolated clones and rejects autonomous output that
  occurs before the full sequence is delivered;
- adds predeclared prefix-only A and unmapped CA controls alongside no-input,
  and gates the learning claim on all sequence mappings/all seeds plus controls;
- preserves sequence mappings/timing/controls through optimizer snapshot and
  explicit timeout reconstruction without changing Phase 5 search policy;
- adds canonical and bounded-smoke P6.2 configs plus sequence-aware public
  reporting and CI experiment/optimizer smoke coverage;
- exact reviewed head `349e4761eb0524904257415b1a93c475f7788332`
  passed CI #186 (`37192574567`) with 166 tests / OK, the real P6.2
  experiment smoke, P6.2 optimizer integration smoke, and browser E2E SUCCESS;
- squash-merged implementation main:
  `c6920bb9c8227c57ce0358d10353ebf7e489a7c4`;
- bounded public smoke: 3 seeds × 2 sequences, AA→B 0→0 and AC→D 0→0;
  no-input, prefix-A and unmapped-CA counterfactuals clean,
  `learning_claim=false`;
- capability acceptance is therefore not a learning-success claim; the next
  bounded frontier is P6.3 multi-event output timing.

## 2026-10-04 — Phase 6.1 multiple independent byte mappings accepted (#79 / PR #80)

- establishes roadmap #78 and bounded child #79 as the first post-readiness
  Phase 6 capability unit;
- adds ordered protocol-level byte mappings with A→B and C→D as the explicit
  initial pair while preserving the legacy single A→B default;
- trains all declared mappings on one continuing authoritative Universe per seed
  and evaluates each mapping on a separate disposable clone;
- records mapping-level and aggregate baseline/trained results under an
  all-mappings/all-seeds, baseline-relative, counterfactual-gated criterion;
- adds an explicit unmapped-input counterfactual distinct from valid mapped
  inputs and keeps failed learning as `learning_claim=false`;
- extends Phase 5 fitness/response aggregation across every active mapping
  evaluation case without changing search/pruning/category semantics;
- adds `config/experiment_phase6_multi_mapping.json` and headless reporting of
  mapping count, evaluation cases, counterfactual input and per-mapping results;
- final reviewed head `6182fa3b615da446260b7e0ef698d7761d946e49`
  passed CI #165 (`37190230270`) with 158 tests / OK, real P6.1 experiment
  smoke and browser E2E SUCCESS, then squash-merged to main as
  `237845bb8b4512048508d8174ef328b3f36fbf52`;
- bounded public smoke: 3 seeds × 2 mappings, A→B 0→0 and C→D 0→0,
  no-input/unmapped counterfactuals clean, `learning_claim=false`.

## 2026-10-04 — Phase 6 readiness rerun accepted (#60)

- audited repaired main `78e9d87a11952197f320602031cfb08852bed078`;
- exact-main push CI `37184102158` passed with 149 tests / OK and browser
  E2E SUCCESS, including the real optimizer CLI smoke;
- current canonical inventory remains 62 REQ / 93 SPEC / 42 TEST / 8 ADR;
- all #64 remediation owners #66/#65/#63/#61 are closed or explicitly
  reclassified with no unresolved P0/P1;
- Phase 4 remains baseline 0 / trained 0 / `learning_claim=false`;
- no Phase 6 capability is implemented; readiness only permits creation of one
  new bounded Phase 6 child Issue.

## 2026-10-04 — Issue #61 residual reconciliation accepted (#61 / PR #74)

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
  event-level history for targets actually retired/replaced; malformed v5
  allocated children without durable parent-genome lineage are rejected, while
  legacy v4 snapshots remain readable and upgrade on the next save;
- records the existing fixed-length Python-list authoritative state as an
  explicit SPEC-IMPL-001 implementation-default deviation; NumPy/Numba
  migration is deferred until profiling or a concrete performance target shows
  benefit, without changing upper-level state/physics contracts;
- exact reviewed head `1441d0bf2b7faa58e265efdc263a8bbf4b3a5414`
  passed CI #138 (`37183145594`) with 149 tests / OK and browser E2E SUCCESS,
  then squash-merged to main as
  `87de79012650b44b934651c8e1ba5a7b8d91e173`.

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
