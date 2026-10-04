# UniverseGenome v0.1 Canonical Specification Index

Status: accepted v0.1 specification basis; Phase 0 through Phase 5 implementation is present, with current acceptance remediation active
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

The checked-in Phase 0–5 implementation is present, but full current
acceptance/readiness is not complete. Status reconciliation #66 and Phase 5
search-semantics remediation #65 are complete; #63 remains the active P1
owner, and readiness owner #60 must rerun the audit from repaired current
`main`. Phase 6+ is blocked until that sequence is complete. This
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

Phase 0 through Phase 5 implementation is present on `main`; current
acceptance remediation is active and Phase 6+ is blocked pending #63 and the
#60 readiness rerun.
Phase 4 recorded no learning claim, and Phase 5 consumes that explicit
measurement rather than asserting success. See `docs/PHASE6_HANDOFF.md`.

See `docs/ROADMAP.md`.
