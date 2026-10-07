# UniverseGenome

UniverseGenome is a local-physics artificial-universe research project descended from the SCA v2 design lineage.

The inner system is intended to learn through deterministic time evolution of anonymous local cells. A separate generalized outer layer searches declared universe-level physical parameters and registered finite rule families while preserving deterministic Inner execution.

## Current state

**Phase 0 through Phase 5 are readiness-accepted on `main`; Phase 6.1
through Phase 6.9 are implemented/accepted through #79 / PR #80, #82 / PR #83,
#85 / PR #86, #88 / PR #89, #91 / PR #92, #95 / PR #96, #98 / PR #99,
#101 / PR #102, and #104 / PR #105.**
The repository contains the canonical v0.1 foundation, server-owned runtime/API,
browser observer/control surface, authoritative Phase 5 optimizer, and nine
bounded Phase 6 experimental capabilities.

P6.9 extends the raw-byte sequence protocol so 1/2/3-byte mappings can coexist
without padding or truncation while keeping valid mapped inputs prefix-free in
this bounded step. The bounded P6.9 smoke produced zero trained mapped successes.

Post-P6.9 learning-emergence / learning-path research is accepted through
#127 / PR #129. #113's matched-snapshot audit localized the deepest reachable
failure at **L3 memory persistence**. #119 identified the physical-transduction
gap; #120 / PR #121 then established a bounded high-contrast B=66/H=8
diagnostic condition with 12/32 density-32 immediate teacher-specific writes,
all HP-only. #122 / PR #126 followed those accepted writes under ordinary
unchanged physics: the frozen 12-seed cohort remains B/H-distinct 12/12 through
+10, 9/12 at +100, but only **1/12 at +1000**, routing to
`ROUTE-MEMORY-ARENA`.

#127 / PR #129 then tested frozen research-only persistence candidates. Both
ENERGY_TO_LATENT_XOR and ENERGY_TO_STRUCTURE_PROMOTE create pre-lifecycle
non-HP teacher-specific state in 12/12 primary cases, but each retains only
**5/12** B/H distinctions at +1000 against the required 8/12. The contact-bond
candidate was statically unreachable for content-specific writes, and the
HP-no-decay reference retained 0/12. The terminal route is therefore **ROUTE-ARCHITECTURE-RETHINK**. #130 completed
the design-only learning-state architecture rethink and selected
**D1 — ANONYMOUS SLOW TRACE WITH CONSERVATIVE LOCAL TRANSFER**. #132 / PR #134
accepted the D1 specification, and #135 / PR #139 then implemented that contract
through TEST-ST-010 on main
`9091bbbc0fdbf261859d7f1b68772601b963548e`. Production now includes the
anonymous `slow_trace:uint8[MAX_CELLS]` state, deterministic local
write/transfer/discharge/forgetting/read semantics, UniverseState v2, and the
inert compatibility/default tuple `(0,0,0,0,8)`. Optimizer persistence is now
v7 with deterministic legacy v4/v5/v6 migration.
The density-4/density-32 inert compatibility matrix is pre-D1-identical and
TEST-ST-010 overhead evidence is recorded in #135. #140 / PR #142 then ran the
frozen TEST-ST-012 research-only profile `D1_ACTIVE_32_8_16_256_5`.
Teacher-specific distinction remained 12/12 through +100 but only **1/12** at
+1000, below the accepted >=8/12 gate. Seed 22 demonstrated that trace can
survive original-carrier turnover and remain elsewhere, but robust L3
persistence was not established. All non-inert values remain research-only.

#144/#145 then generalized the existing Outer Search without changing the
accepted learning result. Phase F / PR #157 ended in
`ACCEPT-OUTER-SEARCH-GENERALIZATION-IMPLEMENTATION` on main
`69cd7e99092bda565eec89daed2bb0873fd3c184`: the Legacy SearchPlan is
exactly equivalent to the frozen pre-generalization oracle and the matched
density4/density32 performance gate passes. No successor memory-physics profile
is accepted and no Phase G search is currently active. Canonical
`learning_claim=false` remains authoritative and P6.10+ semantic expansion
remains frozen.

The full traceability audit (#64) and its handoff (#67/#68) identified three
P1 remediation tracks; #66, #65, and #63 are complete. Post-v0.1 residual
reconciliation #61 is complete via PR #74. No unresolved remediation owner remains. The fresh #60 rerun passed on repaired
current `main`; the earlier invalidated PASS remains historical evidence only. The current Phase 4
measurement remains baseline 0 / trained 0 with no learning claim. See the
[Phase 6+ handoff](docs/PHASE6_HANDOFF.md) for the bounded next-phase contract.

## Canonical entry points

- [Specification index](docs/SPECIFICATION.md)
- [Implementation roadmap](docs/ROADMAP.md)
- [Requirements](docs/spec/01_requirements.md)
- [Physics behavior](docs/spec/03_behavior_spec.md)
- [Implementation/phase specification](docs/spec/06_implementation_spec.md)
- [Tests](docs/spec/07_test_spec.md)
- [Architecture decisions](docs/adr/README.md)
- Repository Issues #2, #3, #4 preserve design/review history.
- Issue #5 owns Phase 0 implementation history.
- Issue #8 / PR #9 record Phase 1 acceptance.
- Issue #10 owns the bounded Phase 2A contact/bond implementation.
- Issue #12 owns the bounded Phase 2B latent-operator implementation.
- Issue #14 owns the bounded Phase 2C fusion implementation.
- Issue #16 owns the bounded Phase 2D fragmentation implementation.
- Issue #18 owns the bounded Phase 2E aging implementation.
- Issue #20 owns the bounded Phase 3 runtime/observation implementation.
- Issue #22 owns the original Phase 4 I/O and A→B→NULL experiment; audit
  remediation #28 / PR #32 wires real autonomous output collection.
- Phase 6 roadmap #78 owns the bounded capability ladder; P6.1 #79 / PR #80
  implements multiple independent byte mappings, P6.2 #82 / PR #83 implements
  temporal sequence discrimination, P6.3 #85 / PR #86 implements multi-event
  output timing, P6.4 #88 / PR #89 implements forgetting/relearning
  retention measurement, P6.5 #91 / PR #92 implements controlled
  physical-noise robustness measurement, P6.6 #95 / PR #96 implements
  predeclared held-out relation generalization measurement, P6.7 #98 /
  PR #99 implements bounded distinct multi-byte output sequences, P6.8
  #101 / PR #102 implements bounded raw UTF-8 byte experiments, and P6.9
  #104 / PR #105 implements bounded mixed-length raw byte sequences.
- Issue #24 owns the original Phase 5 optimizer mechanics; audit remediation
  #30 / PR #34 integrates genome mapping and real Phase 4 candidate evaluation.
- Audit remediation #29 / PR #33 connects the Phase 3 GUI to the runtime API.
- Audit remediation #36 / PR #39 reconciles physical identity, noise, structure,
  and black-hole event semantics.
- Audit remediation #37 / PR #40 adds optimizer snapshot/restore, growth-only
  fitness/pruning fields, and bounded population performance reporting.
- Audit remediation #38 / PR #41 reconciles package metadata, fixed I/O
  coordinates, and documented implemented defaults.
- Post-remediation audit #42 drives the later Phase 3–5 repair series.
- Review #54 and remediation #56 / PR #57 correct Phase 5 evaluation/search
  semantics.
- Remediation #58 / PR #59 restores the original Phase 5 architecture:
  128 persistent authoritative Universe slots, real seed evidence groups,
  real 128/512-generation growth windows, free-slot-only replacement, and
  deterministic optimizer persistence.
- Current status remediation #66 is complete via PR #69; its blocked-state
  projection is accepted on current main.
- Phase 5 search-semantic remediation #65 is complete via PR #70.
- GUI/search integration #63 is complete via PR #73: the browser/server surface
  now observes and controls the authoritative Phase 5 optimizer rather than a
  parallel Phase 3 population.
- Post-v0.1 residual reconciliation #61 is complete via PR #74.
- Readiness audit #60 passed on the repaired Phase 0–5 boundary.
- Phase 6 roadmap #78 is active; P6.1 through P6.9 are accepted on main through
  #79/#80, #82/#83, #85/#86, #88/#89, #91/#92, #95/#96, #98/#99, #101/#102,
  and #104/#105.
- Learning-emergence research #109–#113 is complete through PR #115. The
  accepted causal localization remains L3 memory persistence.
- Analysis report #119 records the post-#113 physical-transduction/specification
  gap; it is evidence, not a specification change.
- Transduction audit #120 / PR #121 is accepted on main. Under unchanged physics,
  the predeclared B/H high-contrast comparison yielded 12/32 density-32
  teacher-specific immediate writes, all HP-only, and satisfied its
  `ROUTE-MEMORY` diagnostic gate.
- Memory persistence audit #122 / PR #126 is accepted on main. Its frozen
  density-32 primary cohort falls from 12/12 B/H-distinct at h0/+10 to 9/12 at
  +100 and **1/12 at +1000**. The non-HP cases are lifecycle-first indirect
  coupling, so the terminal route is `ROUTE-MEMORY-ARENA`.
- Memory persistence design arena #127 / PR #129 is accepted on main. C1
  latent-XOR and C2 structure-promotion both create pre-lifecycle non-HP
  distinctions in 12/12 primary cases but retain only 5/12 at +1000, below the
  frozen 8/12 gate. Terminal route: `ROUTE-ARCHITECTURE-RETHINK`.
- #130 completed the design-only learning-state persistence architecture
  rethink and selected D1 Anonymous Slow Trace with terminal route
  `ROUTE-SPEC-PROPOSAL`.
- #132 / PR #134 is complete with terminal route `ACCEPT-SPEC-PROPOSAL`.
  It remains the accepted specification basis for D1.
- #135 / PR #139 is complete with terminal route `ROUTE-L3-RESEARCH`.
  D1 production state/physics and v2/v6 migration are implemented under the
  inert compatibility/default tuple `(0,0,0,0,8)`; TEST-ST-010 and the
  density-4/density-32 inert compatibility matrix passed.
- #140 / PR #142 is complete with terminal route `FAIL-L3-PERSISTENCE`.
  The frozen profile retained B/H distinction 12/12 through +100 but only 1/12
  at +1000; seed 22 supplied one turnover-surviving redistribution witness.
  The result is a valid research failure, not a harness-validity failure.
- No second profile, active default, L4 recall, or later semantic capability is
  automatically authorized. The next learning-path action requires a separate
  causal/mechanism decision. `learning_claim=false` and the P6.10+ freeze
  remain unchanged. #93 remains a separate performance/architecture workstream.

## Headless verification commands

```bash
python -m core.runner --config config/default.json --generations 8 --json
python -m core.runner --config config/default.json --optimizer --json
# Optional bounded smoke only; explicit override is reported in JSON:
python -m core.runner --config config/default.json --optimizer --optimizer-iterations 0 --optimizer-timeout-generations 8 --json
python -m unittest discover -s tests -v
python -m server.app --help
```

The browser observer now reads the server-owned authoritative Phase 5
`SteadyStateOptimizer`. The 16×8 overview projects its 128 real search slots;
selected physical inspection uses an isolated clone, and render polling does
not drive search or physical time.

## Reuse lineage

- `Structured-Cell-Automaton`: historical SCA v1; selected optimizer/save/visualization ideas may be adapted outside the inner universe.
- `2bit-cell-automaton`: approved visualization/inspection lineage. Old physics rules are not reused as UniverseGenome physics.

## Key constraints

- no permanent Cell ID
- no v1 Syntax/meaning-tag semantics in the core
- fixed-point/discrete world design
- deterministic replay requirement
- Core/GUI clock separation
