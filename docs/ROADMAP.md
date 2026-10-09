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
Next legitimate work is a **new separately frozen, prospective
final-FREE / physical handoff causal question** with independent data,
not reopening R2 thresholds or touching R3/old Phase-H held-out.
No R3, new accepted profile, learning or autonomous behavior justified.
`learning_claim=false`, inert production defaults, P6.10+ freeze,
L4 separation and #93 separation remain authoritative.
