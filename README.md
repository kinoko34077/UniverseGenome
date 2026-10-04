# UniverseGenome

UniverseGenome is a local-physics artificial-universe research project descended from the SCA v2 design lineage.

The inner system is intended to learn through deterministic time evolution of anonymous local cells. A separate outer layer will later search universe-level physical parameters (the universe genome).

## Current state

**Phase 0 through Phase 5 are readiness-accepted on `main`; Phase 6.1
multiple independent byte mappings, Phase 6.2 temporal sequence
discrimination, Phase 6.3 multi-event output timing, Phase 6.4
forgetting/relearning retention, Phase 6.5 controlled physical-noise
robustness, and Phase 6.6 predeclared held-out relation generalization are
implemented/accepted through #79 / PR #80, #82 / PR #83, #85 / PR #86,
#88 / PR #89, #91 / PR #92, and #95 / PR #96.** The repository contains the
canonical v0.1 foundation, server-owned runtime/API, browser observer/control
surface, authoritative Phase 5 optimizer, and the first six bounded Phase 6
experimental capabilities.
The accepted P6.6 bounded smoke still had teacher baseline/trained success 0→0,
so `training_qualified_count=0`, `generalization_eligible_count=0`, and the
generalization rate was explicitly non-evaluable (`null`) with
`learning_claim=false`. Capability acceptance does not relabel that result as
successful generalization.

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
  physical-noise robustness measurement, and P6.6 #95 / PR #96 implements
  predeclared held-out relation generalization measurement.
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
- Phase 6 roadmap #78 is active; P6.1 #79 / PR #80, P6.2 #82 / PR #83, P6.3 #85 / PR #86, P6.4 #88 / PR #89, P6.5 #91 / PR #92, and P6.6 #95 / PR #96 are accepted on main.
- The next permitted capability is one bounded P6.7 multi-byte-sequence child
  Issue. P6.7+ is not implemented yet.

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
