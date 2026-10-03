# UniverseGenome

UniverseGenome is a local-physics artificial-universe research project descended from the SCA v2 design lineage.

The inner system is intended to learn through deterministic time evolution of anonymous local cells. A separate outer layer will later search universe-level physical parameters (the universe genome).

## Current accepted state

**Phase 1 implementation in progress.** The repository contains the canonical
v0.1 requirements/specification, architecture decisions, a deterministic
single-universe core on the dedicated Phase 1 branch, headless snapshot and
performance verification, and the unchanged observer/UI scaffold. Acceptance
and merge are tracked by Issue #8 under the parent Work Order #7.

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

## Headless verification commands

```bash
python -m core.runner --config config/default.json --generations 8 --json
python -m unittest discover -s tests -v
python -m server.app --help
```

The GUI scaffold is static and does not drive the authoritative simulation clock.

## Reuse lineage

- `Structured-Cell-Automaton`: historical SCA v1; selected optimizer/save/visualization ideas may be adapted outside the inner universe.
- `2bit-cell-automaton`: approved visualization/inspection lineage. Old physics rules are not reused as UniverseGenome physics.

## Key constraints

- no permanent Cell ID
- no v1 Syntax/meaning-tag semantics in the core
- fixed-point/discrete world design
- deterministic replay requirement
- Core/GUI clock separation
