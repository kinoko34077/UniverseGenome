# UniverseGenome

UniverseGenome is a local-physics artificial-universe research project descended from the SCA v2 design lineage.

The inner system is intended to learn through deterministic time evolution of anonymous local cells. A separate outer layer will later search universe-level physical parameters (the universe genome).

## Current accepted state

**Phase 1 through Phase 5 are accepted on `main`; Phase 6+ remains a separate
handoff boundary with no Phase 6 capability implemented yet.** The repository
contains the canonical v0.1 requirements/specification, deterministic local
physics, the server-owned 128-universe runtime/API, browser observer/control
surface, physical I/O measurement, and the persistent authoritative Phase 5
optimizer.

The Phase 6 readiness audit (#60) found no unresolved P0/P1 in the accepted
Phase 0–5 runtime path after PR #59. The current Phase 4 measurement remains
baseline 0 / trained 0 with no learning claim. Non-blocking follow-up work is
tracked separately in #61. See the [Phase 6+ handoff](docs/PHASE6_HANDOFF.md)
before opening a new bounded Phase 6 work unit.

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
- Readiness audit #60 establishes the Phase 6 handoff boundary; non-blocking
  residuals are tracked in #61.

## Headless verification commands

```bash
python -m core.runner --config config/default.json --generations 8 --json
python -m core.runner --config config/default.json --optimizer --json
python -m unittest discover -s tests -v
python -m server.app --help
```

The GUI observes the server-owned runtime API and does not drive the
authoritative simulation clock.

## Reuse lineage

- `Structured-Cell-Automaton`: historical SCA v1; selected optimizer/save/visualization ideas may be adapted outside the inner universe.
- `2bit-cell-automaton`: approved visualization/inspection lineage. Old physics rules are not reused as UniverseGenome physics.

## Key constraints

- no permanent Cell ID
- no v1 Syntax/meaning-tag semantics in the core
- fixed-point/discrete world design
- deterministic replay requirement
- Core/GUI clock separation
