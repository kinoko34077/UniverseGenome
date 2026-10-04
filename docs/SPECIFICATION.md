# UniverseGenome v0.1 Canonical Specification Index

Status: accepted v0.1 specification basis; Phase 0–5 readiness accepted, P6.1 accepted through #79 / PR #80, P6.2 through #82 / PR #83, P6.3 through #85 / PR #86, P6.4 through #88 / PR #89, and P6.5 capability accepted through #91 / PR #92
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
sequence discrimination through #82 / PR #83, P6.3 multi-event output timing
through #85 / PR #86, P6.4 forgetting/relearning retention through #88 /
PR #89, P6.5 controlled physical-noise robustness through #91 / PR #92, and
P6.6 predeclared held-out relation generalization through #95 / PR #96.
The accepted P6.6 bounded smoke produced no training-qualified seeds, so
generalization eligibility was zero and the generalization rate remained
non-evaluable (`null`) with `learning_claim=false`.
The next permitted capability is one bounded P6.7 multi-byte-sequence child
Issue with explicit acceptance criteria. This state
statement is separate from historical acceptance records preserved in the
changelog and Issues.

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
P6.3 through #85 / PR #86, P6.4 through #88 / PR #89, P6.5 through
#91 / PR #92, and P6.6 through #95 / PR #96. Phase 6 remains a bounded
capability ladder: P6.7+ requires separate child Issues. The current P6.6
generalization measurement has no training-qualified/eligible cases, so
generalization remains non-evaluable rather than asserted as successful. See
`docs/PHASE6_HANDOFF.md`.

See `docs/ROADMAP.md`.
