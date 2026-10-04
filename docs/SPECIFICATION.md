# UniverseGenome v0.1 Canonical Specification Index

Status: accepted v0.1 specification basis; Phase 0 through Phase 5 are readiness-accepted after rerun #60
Requirements source: #3  
Detailed specification source/review history: #4  
Historical rationale: #2  
Phase 0 owner: #5

## Canonical ownership

The checked-in files under `docs/spec/` own the durable repository specification.

- `docs/spec/01_requirements.md` owns what the system must achieve.
- `docs/spec/02_functional_spec.md` owns higher-level functional behavior.
- `docs/spec/03_behavior_spec.md` owns local world/physics behavior.
- `docs/spec/04_data_spec.md` owns state/data representation.
- `docs/spec/05_ui_spec.md` owns observation/UI behavior.
- `docs/spec/06_implementation_spec.md` owns implementation boundaries and phase scope.
- `docs/spec/07_test_spec.md` owns executable acceptance expectations.
- `docs/adr/` owns durable architecture rationale.

Issue #3 and #4 remain durable review/history surfaces and must link to future accepted specification changes rather than silently diverge.

## Current repository state

The checked-in Phase 0–5 implementation is present and the fresh readiness
rerun #60 passed after P1 remediation #66/#65/#63 and post-v0.1 residual
reconciliation #61 completed. No Phase 6+ capability is implemented yet; the
next permitted work is one new bounded Phase 6 child Issue with explicit
acceptance criteria. This
state statement is separate from the historical acceptance records preserved
in the changelog and Issues.

## Status vocabulary

- accepted
- accepted-default
- parameterized
- candidate
- implemented
- tested
- deprecated
- removed
- rejected

Status is a single base term. Qualifiers such as invariant, parameterization,
or policy-hook-only behavior belong in the explanatory text following a status
line; they are not new compound status values. An implementation default does
not promote `accepted-default` or `parameterized` into an immutable rule.

## Current implementation frontier

Phase 0 through Phase 5 are readiness-accepted on `main`; remediation and
residual reconciliation through #61 are complete and #60 has passed. Phase 6+
remains a new bounded capability layer, not an already-implemented feature.
Phase 4 recorded no learning claim, and Phase 5 consumes that explicit
measurement rather than asserting success. See `docs/PHASE6_HANDOFF.md`.

See `docs/ROADMAP.md`.
