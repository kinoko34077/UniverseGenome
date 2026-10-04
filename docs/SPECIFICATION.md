# UniverseGenome v0.1 Canonical Specification Index

Status: accepted v0.1 specification basis; Phase 0–5 readiness accepted, P6.1 accepted through #79 / PR #80, P6.2 accepted through #82 / PR #83, and P6.3 capability accepted through #85 / PR #86
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
rerun #60 passed after remediation/reconciliation. P6.1 multiple independent
byte mappings are implemented/accepted through #79 / PR #80, P6.2 temporal
sequence discrimination through #82 / PR #83, and P6.3 multi-event output timing
through #85 / PR #86. The accepted P6.3 bounded smoke remains AA→B,B 0→0 and
AC→D,D 0→0 with `learning_claim=false` and clean
no-input/prefix-A/unmapped-CA controls. The next permitted capability is one
bounded P6.4 forgetting/relearning child Issue with explicit acceptance criteria. This state statement is separate from
historical acceptance records preserved in the changelog and Issues.

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

Phase 0 through Phase 5 are readiness-accepted on `main`; #60 has passed and
P6.1 is implemented/accepted through #79 / PR #80, P6.2 through #82 / PR #83,
and P6.3 through #85 / PR #86. Phase 6 remains a bounded capability ladder:
P6.4+ requires separate child Issues. The current timed multi-event measurement
still records no learning claim, and Phase 5 consumes that explicit evidence
rather than asserting success. See
`docs/PHASE6_HANDOFF.md`.

See `docs/ROADMAP.md`.
