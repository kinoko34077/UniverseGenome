# UniverseGenome Implementation Roadmap

## Current repository state

Phase 0 through Phase 5 are readiness-accepted on `main`. Current State
reconciliation #66, Phase 5 remediation #65, GUI/search integration #63, and
post-v0.1 residual reconciliation #61 are complete; readiness rerun #60 passed.
Phase 6 roadmap #78 is active. P6.1 multiple independent byte mappings are
accepted through #79 / PR #80, P6.2 temporal sequence discrimination through
#82 / PR #83, P6.3 multi-event output timing through #85 / PR #86, P6.4
forgetting/relearning retention through #88 / PR #89, P6.5 controlled
physical-noise robustness through #91 / PR #92, P6.6 predeclared held-out
relation generalization through #95 / PR #96, P6.7 bounded distinct
multi-byte output sequences through #98 / PR #99, P6.8 bounded raw UTF-8
byte experiments through #101 / PR #102, and P6.9 bounded mixed-length raw
byte sequences through #104 / PR #105 on main.

Post-P6.9 learning-emergence / learning-path research is accepted through
#122 / PR #126. #111 / PR #114 showed that density 32 improves substrate
persistence/activity but still yields zero canonical trained successes. #113 /
PR #115 localized the deepest reachable failure at **L3 memory persistence**;
L4–L7 remained NOT_EVALUABLE. #119 recorded the physical-I/O distinguishability
gap. #120 / PR #121 then established a bounded high-contrast B=66/H=8
immediate-write diagnostic condition: 12/32 density-32 seeds, traceable and
HP-only, terminal route `ROUTE-MEMORY`.

#122 / PR #126 followed the frozen 12 write-positive density-32 seeds through
h0/+1/+10/+100/+1000 under unchanged physics. B/H distinction is 12/12 through
+10, 9/12 at +100 and **1/12 at +1000**. Six seeds develop non-HP differences,
but lifecycle divergence always occurs first and latent/structure/bond
differences follow later; 11/12 primary cases reconverge by +1000. The
predeclared route is **ROUTE-MEMORY-ARENA**.

#127 / PR #129 completed the research-only persistence arena and routed to
`ROUTE-ARCHITECTURE-RETHINK`. #130 then completed the design-only architecture
rethink, selected **D1 Anonymous Slow Trace with Conservative Local Transfer**,
and terminated at **ROUTE-SPEC-PROPOSAL**. #132 / PR #134 subsequently
completed formal specification review and terminated at
**ACCEPT-SPEC-PROPOSAL**.

#135 / PR #139 has completed the RED-first implementation contract with terminal
route **ROUTE-L3-RESEARCH**. D1 is now production-implemented through
TEST-ST-010: authoritative `slow_trace:uint8[MAX_CELLS]`, local physical
write/transfer/discharge/decay/read semantics, UniverseState v2 / optimizer v6
migration, and the inert compatibility/default tuple `(0,0,0,0,8)`.
Density-4/density-32 inert compatibility against pre-D1 behavior passed and
TEST-ST-010 overhead is measured. All non-inert values remain research-only and
are not Phase 5 search-genome defaults.

#140 / PR #142 has completed the frozen TEST-ST-012 L3 persistence / turnover
gate with terminal route **FAIL-L3-PERSISTENCE**. Under research-only profile
`D1_ACTIVE_32_8_16_256_5`, B/H distinction remained 12/12 through +100 but
fell to **1/12 at +1000** against the accepted >=8/12 threshold. Seed 22 proved
turnover-surviving redistribution is possible, but robust cohort-level L3
persistence is not established.

#144/#145 have now completed the selected bounded architecture response to that
failure: the existing Inner/Outer split is generalized so registered
Universe-level scalar variables and finite rule families can be searched by a
declarative SearchPlan without changing legacy Phase 5 behavior. Phase F /
PR #157 ended in
**ACCEPT-OUTER-SEARCH-GENERALIZATION-IMPLEMENTATION** on main
`69cd7e99092bda565eec89daed2bb0873fd3c184`. The generalized Legacy
SearchPlan matches the immutable pre-generalization oracle across static state,
generations 16/128/512/1024, optimizer decisions and continuation; matched
density4/density32 throughput regression is within the accepted 5% gate.

Phase G research child **#159 completed its first bounded decay-axis
question**. G0 / PRs #160+#161 froze the decay-only research SearchPlan,
qualified disjoint adaptive-search/held-out cohorts and the full protocol.
G1 / PR #164 was accepted on main
`abfb478367a209ecaf4165cda22531506275bde3` with exact-head ordinary
CI and 12-candidate workflow SUCCESS. Every decay rate in
`[0,1,2,4,8,16,32,64,128,256,512,1024]` passed replay,
raw/instrumented, duplicate-control and negative-sentinel gates. All produced
+100 B/H distinction `13/16`, but +1000 distinction `0/16` and zero
turnover witnesses, including reference rate 256. The frozen >=11/16 and
strict-reference-improvement Phase-H routing criteria therefore failed;
terminal decision: **CHANGE_PATH**. Deterministic identity tie-breaking
named rate 1 but does not establish a better physical-memory candidate.
No Phase H held-out post-h0 evidence was executed and no successor profile
was accepted. A new parameter axis or architecture requires its **own
predeclared research contract**, not post-outcome tuning within #159.
Production D1 defaults remain `(0,0,0,0,8)`; L4, active-default promotion,
P6.10+ and a canonical learning claim remain unauthorized.
`learning_claim=false`. #93 remains a separate
performance/architecture workstream.

Research-only successor **#167** completed D1 observation instrumentation
(PR #168) and the frozen D2 cohort (PR #169; accepted main
`0c13a3672c1f1822f54f2831bebf57ba01074cdc`, post-main CI
`37724247269` SUCCESS). The exact-head diagnostic workflow
`37723855643` produced a valid 40/40 cases: both decay 0 and 256
have B/H trace differences 16/16 at h0, 13/16 at +100 and 0/16 at +1000.
Every positive case still has nonzero **total trace mass** at +1000,
so persistence of anonymous trace mass is not teacher-content persistence.
Permanent loss of trace distinction occurs at generations 55–701
(median 278), with only 7/16 (decay 0) or 8/16 (decay 256) showing
a same-generation trace-bearing FREE event. Passive observations did not
isolate write saturation, local transfer, FREE, or sparse read-width
contrast as the sole cause. **D3 terminal: HOLD-UNRESOLVED.**
No active physics profile, new search axis, Phase H/held-out post-h0,
L4/P6.10+ or learning claim follows from this child.

Explicitly selected R1 causal research **#172** / PR **#173** is separately
completed with **CAUSE-SUPPORTED (generic post-h0 write path only)**.
A pre-outcome frozen 24-positive/8-negative cohort, each run at rates 256
(primary) and 0 (sensitivity), yielded **64/64 valid exact-head cases**
(Action `37925171476`, aggregate artifact `11614007295`). Suppressing
generic continued writes after teacher h0 preserved +1000 B/H trace contrast
in **12/24** positives, with 0 sham-only harms, 8/8 clean negatives and
Holm-adjusted exact paired p=0.000732421875; decay0 sensitivity 11/24.
The local-FREE-relay, transfer-off and read-off interventions yielded 0/24
long-horizon recoveries; actual downstream latent effects were 0/24.
This isolates an intervention-responsive *write pathway*, not saturation
alone, not readout, robust TEST-ST-012 L3 acceptance or autonomous learning.
R1 alone did not authorize Phase H, R2, P6.10, L4+ or production promotion.

A new explicitly authorized and separately frozen R2 write-rule child
**#175** / research **PR #176** followed on an independent seed pool
544..1023. With 16 h0-qualified teacher-trace positives and 8 clean
negative sentinels, deterministic replay, raw-reference parity and
24/24 validated case evidence (Action `37950076024`; aggregate digest
`ff3d8292049e508d56ae117d4027ea371583226efc53ecb7d57aaad88582bc7f`),
the h+1000 B/H trace contrast was **0/16 native, 10/16 unit_add,
1/16 empty_site, 1/16 half_ceiling**. unit_add was 10 net rescues
against unchanged reference but failed the frozen >=12/16 gate; no
independently certified original-carrier transfer/turnover or latent
downstream effect was established. R2 therefore completed
**CHANGE_PATH_NO_R2_FULL_ACCEPTANCE**, without any R3/Phase H permission,
production switch or learning claim. Accepted research PR #176 merged
as `90e41860933c59abee8d3f1ea8d68ba5c0e0d92e`.


## Gate 0 — Specification basis
Status: accepted by Phase 0 specification reconciliation.

## Phase 0 — Repository/spec scaffold
Goal: a fresh worker can begin Phase 1 from GitHub alone.

Deliverables:
- canonical specification index/files
- ADRs
- bounded package/module scaffolds
- config/persistence/server/UI/test scaffolds
- minimal headless entrypoint
- automated smoke verification
- README routing

## Phase 1 — Minimal deterministic universe (implementation present; historical acceptance #8 / PR #9)
- 32×32 torus
- 256×256 fixed-point position
- fixed slot pool
- structure/latent/HP state
- direction/speed
- synchronous movement
- destination footprint
- tunneling
- noise spawn
- collision
- HP/BLACK_HOLE
- deterministic replay
- snapshot roundtrip
- headless performance counters

## Phase 2 — Local learning physics
2A contact/bond (implementation present; historical acceptance #10 / PR #11)
2B four latent operators (implementation present; historical acceptance #12 / PR #13)
2C fusion (implementation present; historical acceptance #14 / PR #15)
2D fragmentation (implementation present; historical acceptance #16 / PR #17)
2E aging (implementation present; historical acceptance #18 / PR #19)

## Phase 3 — 128-universe runtime and observation GUI (implementation present; historical acceptance #20 / PR #21, remediation #29 / PR #33)
4 categories × 32 slots, matched genome/seed comparisons, server-owned runtime
API, overview/detail/rewind/clone observation, and bounded controls.

## Phase 4 — I/O learning (implementation present; historical acceptance #22 / PR #23, remediation #28 / PR #32)
8-bit bus, teacher stimulation, A → B → NULL, evaluation clone, real
baseline-vs-trained autonomous measurement. Current result remains 0 / 0 with
no learning claim.

## Phase 5 — Universe-genome optimization (implementation present; historical architecture restoration #58 / PR #59)
The historical Phase 5 contract restored by #58 / PR #59 uses exactly 128 persistent authoritative
Universe slots as four category-local groups of 32. One slot owns one category,
one genome, one seed and one continuing UniverseState. Fitness aggregates real
same-genome seed slots; growth is observed on real 128-generation boundaries;
steady-state replacement occurs only after a real prune/free target exists;
minimum evidence and depleted-mature-group lifecycle are explicit; optimizer
snapshot/restore preserves deterministic continuation.

Phase 5 search-semantics remediation #65 is complete via PR #70 and
cross-phase GUI/authoritative-search remediation #63 is complete via PR #73.
Earlier implementation/remediation history: #24 / PR #25, #30 / PR #34,
#36 / PR #39, #37 / PR #40, #38 / PR #41, #44 / PR #50, #56 / PR #57.

## Phase 6+ — Capability ladder (#78)

P6.1 multiple independent byte mappings is implemented/accepted through #79 /
PR #80. P6.2 temporal sequence discrimination is implemented/accepted through
#82 / PR #83. P6.3 multi-event output timing is implemented/accepted through
#85 / PR #86. P6.4 forgetting/relearning is implemented/accepted through #88 /
PR #89: the protocol measures T0 immediate retention eligibility, advances the
same trained state through a declared no-teacher delay plus deterministic
unmapped-CA interference, evaluates T1, applies one relearning curriculum pass
without reset, then evaluates T2. Evaluable retention is growth-only Phase 5
evidence and does not alter absolute fitness ordering.

The accepted bounded P6.4 smoke produced no T0-success cases across its three
seeds × two mappings. Therefore retention/relearning were explicitly
non-evaluable (`null`) and `learning_claim=false`; capability acceptance is
not a learning or retention-success claim.

P6.5 controlled physical-noise robustness is implemented/accepted through #91 /
PR #92. It compares matched clean/noisy disposable evaluations from the same
trained T0 state, uses the existing physical background-noise path, requires
clean mapped success for evaluability, and exposes null-aware robust/failure
evidence. Evaluable noise robustness may drive growth-only Phase 5 bit 6 without
changing absolute fitness.

The accepted bounded P6.5 smoke produced zero clean-success eligible cases.
Noise robustness was therefore explicitly non-evaluable (`null`) and
`learning_claim=false`; capability acceptance is not a robustness-success
claim.

P6.6 predeclared held-out relation generalization is implemented/accepted
through #95 / PR #96. The bounded smoke produced teacher success 0→0,
`training_qualified_count=0`, `generalization_eligible_count=0`, and
`generalization_rate=null`; `learning_claim=false`. Capability acceptance is
therefore not a successful-generalization claim.

P6.7 bounded distinct multi-byte output sequences are implemented/accepted
through #98 / PR #99. The capability changes the timed output target from
repeated identical bytes to exact ordered tuples `B,C` and `D,E`, while
preserving legacy protocol behavior and Phase 5 search semantics. The bounded
smoke produced zero trained mapped successes and `learning_claim=false`;
capability acceptance is not a sequence-learning-success claim.

P6.8 bounded raw UTF-8 byte experiments are implemented/accepted through #101 /
PR #102. They reuse the P6.7 byte-sequence runtime with externally documented
valid UTF-8 byte arrays only; no tokenizer, Unicode semantic state or Phase 5
search change is introduced. The bounded smoke produced zero trained mapped
successes and `learning_claim=false`; capability acceptance is not a
UTF-8-learning-success claim.

P6.9 bounded mixed-length raw byte sequence mappings are implemented/accepted
through #104 / PR #105. One protocol can coexist with 1/2/3-byte mappings and
mapping-specific 1/2/3-byte outputs while retaining prefix-free mapped inputs in
this bounded step. The bounded smoke produced zero trained mapped successes and
`learning_claim=false`; capability acceptance is not a mixed-length-learning
success claim.

## Post-P6.9 learning-emergence research

- #109: long-run A→B→NULL baseline through ~100k generations; no target learning.
- #110: easier-curriculum / minimal-output / I/O-distance diagnostics; no
  baseline-relative input-specific learned precursor.
- #111 / PR #114: initial-density arena; density 32 materially improves
  persistence/activity, but canonical trained success remains 0.
- #113 / PR #115: 64-case matched-snapshot causal audit, accepted on main
  `155f73b0cbcad276093c26fa55fe69eb562f0347`. Density 4 first fails L0 in
  32/32 cases; density 32 first fails L0 in 23/32, L2 in 8/32 and L3 in 1/32.
  No case passes full L3 persistence, so L4–L7 are NOT_EVALUABLE.
  Deterministic replay and raw-vs-instrumented equivalence both passed 64/64.
- #119: completed report separating logical byte representability from physical
  transduction distinguishability; report-only, with no specification change.
- #120 / PR #121: predeclared transduction-capacity/state-write audit. The
  current 256-byte geometry has 55 idealized receptive regions; density-32
  realized pattern entropy averages ~0.370 bit. B/C yields 2/32 teacher-specific
  writes, while the frozen high-contrast B/H comparison yields **12/32**,
  traceable 12/12. Every B/H immediate teacher-specific difference is HP-only.
  Input probes also directly reproduce contact-without-write through HP
  saturation. Deterministic replay, raw-vs-instrumented equivalence, and
  no-teacher repeat controls all pass 64/64. The predeclared terminal route is
  **ROUTE-MEMORY**.
- #122 / PR #126: memory-coupling/persistence audit using the accepted B/H
  write-positive cohort. Primary B/H distinction is 12/12 at h0/+1/+10,
  9/12 at +100 and **1/12 at +1000**. Six seeds ever develop non-HP
  differences, but all six split in lifecycle/survival before network-state
  divergence; 11/12 reconverge by +1000. Replay/raw-equivalence and controls
  are clean. The predeclared terminal route is **ROUTE-MEMORY-ARENA**.
- #127 / PR #129: research-only memory persistence design arena under a frozen
  8/12 +1000 gate. ENERGY_TO_LATENT_XOR and ENERGY_TO_STRUCTURE_PROMOTE each
  create pre-lifecycle non-HP B/H distinctions in 12/12 primary cases but
  retain only **5/12** at +1000. Contact-bond reinforcement was statically
  unreachable for content-specific writes; HP_NO_DECAY_REFERENCE retains
  0/12 and is reference-only. No candidate passes. Terminal route:
  **ROUTE-ARCHITECTURE-RETHINK**.
- #130: design-only architecture rethink. B1 latent echo and C1 morphology
  cluster were rejected as primary specification candidates because they
  respectively confound long-term memory with existing fast latent semantics
  or with morphology/contact dynamics. D1 **Anonymous Slow Trace with
  Conservative Local Transfer** was selected and routed to formal specification
  review.
- #132 / PR #134: accepted the D1 specification, including REQ-ST-001..008,
  SPEC-ST behavior/data/migration contracts, ADR-009, TEST-ST-001..012 and the
  inert compatibility/default tuple `(0,0,0,0,8)`.
- #135 / PR #139: implemented D1 through TEST-ST-010, preserved pre-D1 behavior
  under the inert profile, measured storage/throughput/snapshot overhead, and
  terminated at **ROUTE-L3-RESEARCH**. No non-inert active default was promoted.

- #140 / PR #142: completed the frozen TEST-ST-012 L3 persistence / turnover
  gate with **FAIL-L3-PERSISTENCE**. The profile passed validity controls and
  demonstrated one turnover witness, but only 1/12 primary cases remained
  teacher-specific at +1000 versus the required >=8/12.

Next frontier: R1 #172 established that continuing generic trace writes
are intervention-responsive; independent bounded R2 #175 tested the
physical WRITE rule and ended `CHANGE_PATH` (best unit_add10/16 vs
required>=12/16, zero certified physical carrier handoffs).
Subsequent **D4 #178** examined the *same, outcome-exposed* R2 cohort
using a nonmutating stage observer (24/24 valid, Action 37952291383).
The six last content-contrast losses were all localized to the
**post-decay / end-of-step pending-FREE stage**, not to the write or
transfer stage in that final-loss generation; this is only an
exploratory association, not an independently confirmed causal root.
D5 **#181** then checked *physical recipient feasibility* before attempting
that counterfactual. With the same already outcome-exposed 16+8 cohort
(24/24 deterministic/observer-parity valid; Action 37958510937), all
ten B/H content-differential pending-FREE events at the six last-loss
epochs had **zero overlapping ACTIVE receiver cells** (`0/10` eligible),
despite rare eligible contact at other epochs in two retained cases.
Native discharge before final FREE already uses this same-footprint
topology; hence an extra local end-stage relay in the observed six
failures is `INFEASIBLE / CHANGE_PATH`, not an independently causal
repair. Research PR #182 accepted on main
`e4dd70f8e39f4f32c0b505180a60a4a166586aaf`.
D6 **#184** then resolved the narrower *earlier contact* question
on the same outcome-exposed R2 cohort. Its native transfer observer
(Action `37960189337`) validated 24/24 cases with exact event
replay, uninstrumented parity and clean sentinels. **9/10** last-loss
donor branch episodes had physically selected earlier contact **and
actual positive conservative trace transfer**; **2/10** had surviving
recipient life epochs, both from the *same seed575 B/H pair* each
receiving an identical 3 units at +61, while teacher content
difference still disappeared at +724. Therefore prior physical
transport exists, but no demonstrated teacher-specific persistent
information path or latent readout. No R3, Phase H, new memory
candidate or `learning_claim=true` follows. A further causal question
would require strict B/H-specific content lineage into recipient
post-transfer physics, then a separately preregistered intervention
with a truly independent cohort, not another scalar parameter sweep.
Research PR #185 accepted main
`d59d712ba04f00849c0b92acb384d1f2685a2390`.
D7 **#187** then followed precisely the *surviving native recipient*
from seed575 B/H, with no-teacher control and frozen B/H-global-equal
negative seed545, through all 1000 generations and write/transfer/decay
stage boundaries. Scientific Action `37961606736` validated exact
replay, native uninstrumented parity and sentinel control; artifact
digest `0650e05be640a34cc026d3993ba9644f60e2d93f411344c2a0495cc091d62d4b`.
Both B/H histories physically delivered **3 units** to receiver slot6
at +61, retained that receiver life epoch after donor FREE +724 and
h+1000, but its **B/H slow-trace value never differed at any observed
stage** (`0/1000` end-of-generation contrasts). The receiver was
B/H=29 versus no-teacher18 at +61, B/H=67/control65 at +724,
and B/H=80/control79 at +1000. Thus scalar effects of teacher
*presence* occurred, but no teacher **B versus H content contrast**
passed through this survivor, and latent at tested checkpoints was
identical. This is **one outcome-exposed microcase**, not statistical
replication, semantic recall, independent causal readout or successful
L3. Research PR #188 accepted main
`7aa9882b19e10b4d43fb923a7b6b00838a378fa8`.
No further unspecified physical search follows automatically.

D8 **#190 / research PR #191** added a **read-only, category-local
genetic diversity and cohort-leakage monitor** rather than changing
legacy 128-slot Outer selection. The real *fresh initial* generation0
population is 4 categories ×32 slots, each with **8 distinct complete
11-field UniverseGenomes ×4 physical seed-evidence slots**, dominant
genotype share **12.5%**, Shannon effective genome count **8.0**,
inverse Simpson effective **8.0** (Action `37964958227`, baseline
report digest `443c7a2616f5eb90deb832d5cac52fd500e4de6a3b126d87d5906b56e2932c54`).
Six unit tests passed: real 128-slot snapshot unchanged, synthetic
single-genotype fixation (U1/top100%/effective1), unequal 16:8:8
concentration (top50%, Simpson2.6666666667), category isolation and
training/validation/heldout seed-leakage rejection. Cross-category
replication of eight matched genomes is intentionally **not**
32 independent genotypes. It remains **UNKNOWN** whether selection
over many optimizer generations collapses genotype diversity or
overfits a narrow teacher/input cohort: the D8 measurement is
generation0 and neither evolved time-series nor genuine untouched
held-out performance was evaluated. Before any new candidate
promotion, require separately frozen temporal diversity metrics
and disjoint evidence roles across input/teacher/seed/noise/horizon,
and inspect generalization gaps and capability regressions.
**Do not automatically award selection diversity bonuses or change
fitness ranking, active D1 configuration or `learning_claim=false`
based solely on this descriptive baseline.

D10 **#195 / research PR #196** verified a native D1 **trace-read opportunity
gate** without changing physics or promoting learning. With a frozen
synthetic ACTIVE-cell native reader fixture (seed7, generation11,
address19, pair(0,1), shift5), trace10 vs18 produced the same mask8192,
whereas 31 vs32 crossed the right-shift threshold and yielded width1→2
and distinct masks8192→8448. Bond255 saturated to width16 and mask65535
for trace0 vs255; production-inert shift8 gave identical width1 for
trace0 vs255. A native generic write with initial trace4, activity5,
cap8 produced trace9 under both externally named preparations: physics
received no teacher label. Exact-head Action `37968783233` passed 4/4,
report digest
`751a1fdbf583bcc9bfacd7a7f32f4de5acee0ac2e90a67e7ed0378d93d8e7e7c`.
An initial failed fixture Action `37968619345` used an EMPTY default
world (initial_density0), correctly preventing writes to FREE slot0;
#195 documented the eligibility-only correction (ACTIVE slots via
initial_density2) before rerunning. This proves **only a conditional
synthetic read-width gate**, NOT any naturally selected B/H differential
contact, altered latent/output, independent generalization or learning.
Actual teacher-content trace survival, an unsaturated selected reader
contact, a downstream difference and independent causal verification
remain separate necessary evidence. D9 Outer diversity #193 is
unrelated; R2 acceptance failed and all R3/Phase H and D1 production
restrictions remain unchanged.

D9 **#193 / research PR #194** executed a **real** legacy Outer
optimizer but did **not** reach evolutionary replacement in its
predeclared bounded horizon. Frozen search seed bases16384 and32768
each ran four actual native optimizer steps (checkpoints0..4) on
fresh disposable 128-slot populations, with an exact duplicate full
replay of seed16384. Scientific Action `37966342059` passed all
three seeded runs and its checksum/replay aggregate (artifact
`11635405921`, digest
`72249d9592a40d32b991caf340156a17f7c6a2363daa81176807c855d9624722`).
Both distinct exploratory seeds, all four category-local 32-slot
strata, remained at initial `unique_genomes=8`,
dominant-genotype share `0.125`, Shannon effective count `8.0`
at all five checkpoints, with **0 actual replacements and
0 mutation-child allocations**. Formal scientific result
`SELECTION_NOT_EXPOSED / CHANGE_PATH`, *not* a demonstration
that genetic diversity survives meaningful selection, not
long-term convergence, and not evidence for or against
overfitting/held-out generalization. The frozen seed16384
replay outputs matched exactly. Do not extend this same
already-exposed 4-step run after inspecting its outcome.
The specific next research question is whether native category-local
pruning eligibility (four growth windows, category median thresholds,
absolute-failure route, parent availability) can ever open the
replacement gate under the observed flat objective; any new
diagnostic uses a separately frozen cohort/fixture and cannot
silently revise accepted selection policy or learner criteria.

D11 **#199 / research PR #200** isolated **conditional native
Outer pruning eligibility**, not a new evolutionary success.
Frozen read-only native `SelectionRecord` fixtures each use four
categories ×32 slots, 8 genotype groups ×4 evidence slots.
Under the accepted native category-local pruning functions:
F0 four complete all-zero growth windows produce a zero category
median and threshold0, and therefore no record satisfies strict
`growth < threshold`; F1 incomplete three-window history also
cannot be growth-pruned. F2, in one category only, 31 slots with
four windows `(3,3,3,3)` and one unprotected worst slot31 with
four zero windows yield median growth bitcount2/threshold1,
natively pruned target31 and a same-category parent0.
F3 makes the same worst slot an absolute failure and prunes it
even with all-zero category medians. The other three
categories remain unpruned. Exact-head native Action
`37970419273` passed 3/3 tests; research artifact
`11634833377`, digest
`8dcd4c41ca42e9e520daf192bd6da19d271eeb2f9c68ac81eceb57d303e33d1f`.
This establishes a **conditional no-growth/no-failure pruning
gate**, *not* proof that the D9 real optimizer's unrecorded
individual growth histories had those exact values. Therefore
D9's no-replacement cause remains unconfirmed and genetic
diversity under genuine selection remains unmeasured.
No accepted selection, fitness, mutation or production D1
settings were changed. A later direct D9-like diagnostic
would have to measure actual pruning eligibility and growth
histories before asserting the bottleneck caused the observed
zero replacements; do not force adaptation or diversity bonuses
based on synthetic cases.

D12 **#202 / research PR #203** verified that the original
D9 no-selection observation was a **pre-eligibility time window**,
not measured diversity maintenance during selection. Under the
identical frozen native default 128-world, search-only seed16384,
four real Outer steps, a read-only per-slot observer reproduced
the **full original D9 case digest**
`3e6162f8af56d0c802b02fa7e73df567dd7365bafc09fb42917ceb1815caf721`
and 0..4 real checkpoints. All four category-local strata were
`GROWTH_HISTORY_INCOMPLETE` throughout: no native prune
candidate/replacement or absolute-failure route was observed.
Default training advances 14 physical generations per Outer step,
so after step4 physical generation56 is short of the first
growth comparison checkpoint128, and four complete growth
windows cannot be present. Source-bound scientific Action
`37971539627` passed all guards; artifact `11638049119`,
D12 report digest
`024b4938da6e606434829382b80ad002931313ff201a52cc6ff01389eafb0d61`.
This is **not** evidence that the optimizer never selects;
it neither demonstrates selection-pressure genetic diversity nor
independent held-out task generalization. Actual active
selection/evolution requires a separately bounded plan with
real replacement exposure. D13 #204 separately owns
user-authorized flexible, budgeted Outer research execution;
it does not retroactively change this frozen D12 result or
the current fixed legacy population contract.

Do not reopen R2 thresholds or touch R3/old Phase-H held-out.
No R3, new accepted profile, learning or autonomous behavior justified.
`learning_claim=false`, inert production defaults, P6.10+ freeze,
L4 separation and #93 separation remain authoritative.
