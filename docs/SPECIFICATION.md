# UniverseGenome v0.1 Canonical Specification Index

Status: accepted Phase 0–5 basis; P6.1 multiple-mapping capability implemented after readiness rerun #60
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
reconciliation #61 completed. P6.1 multiple independent byte mappings is now
implemented and accepted via #79 / PR #80. The next permitted capability work
is P6.2 temporal sequence discrimination in a new bounded child Issue with
explicit acceptance criteria. The P6.1 experiment still reports no learning
claim. This state statement is separate from the historical acceptance records preserved
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
residual reconciliation through #61 are complete and #60 has passed. P6.1 is
the first implemented bounded Phase 6 capability. Its A→B/C→D experiment
remains a measured failure (`learning_claim=false`), not a success claim.
The current implementation frontier is P6.2, which remains unimplemented. See
`docs/PHASE6_HANDOFF.md` and roadmap #78.

See `docs/ROADMAP.md`.
