# UniverseGenome v0.1 Canonical Specification Index

Status: accepted v0.1 specification basis; Phase 0–5 readiness accepted; P6.1 through P6.9 accepted through #79/#80, #82/#83, #85/#86, #88/#89, #91/#92, #95/#96, #98/#99, #101/#102, and #104/#105
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
PR #89, P6.5 controlled physical-noise robustness through #91 / PR #92,
P6.6 predeclared held-out relation generalization through #95 / PR #96,
P6.7 bounded distinct multi-byte output sequences through #98 / PR #99,
P6.8 bounded raw UTF-8 byte experiments through #101 / PR #102, and P6.9
bounded mixed-length raw byte sequences through #104 / PR #105.
The accepted P6.9 bounded smoke produced zero trained mapped successes and
`learning_claim=false`.

Accepted post-P6.9 learning-emergence / learning-path research now extends
through #127 / PR #129. #113 / PR #115 localized the formal deepest reachable
failed causal level at **L3 memory persistence**. #119 identified the
research/specification-completeness gap between logical byte representation and
substrate-level physical distinguishability. #120 / PR #121 established a
usable high-contrast B=66/H=8 diagnostic condition under unchanged accepted
physics: 12/32 density-32 seeds receive teacher-specific immediate HP-only
writes, terminal route `ROUTE-MEMORY`.

#122 / PR #126 tested the exact accepted write-positive cohort through
h0/+1/+10/+100/+1000 with no further external stimulation. Primary B/H
distinction is 12/12 through +10, 9/12 at +100 and **1/12 at +1000**,
routing to `ROUTE-MEMORY-ARENA`.

#127 / PR #129 then tested frozen research-only local consolidation candidates.
ENERGY_TO_LATENT_XOR and ENERGY_TO_STRUCTURE_PROMOTE each create
teacher-specific pre-lifecycle non-HP distinctions in 12/12 primary cases, but
each retains only **5/12** B/H distinctions at +1000, below the frozen 8/12
gate. Contact-bond reinforcement was statically unreachable for content-specific
writes and HP_NO_DECAY_REFERENCE retained 0/12. No candidate passes; terminal
route is `ROUTE-ARCHITECTURE-RETHINK`.

This remains current-state research evidence, not a new I/O requirement,
physics default, or specification change. It does not establish L4 recall,
learning, or full 8-bit physical channel adequacy. No production
physics/default/P6.10+ semantic change was accepted and
`learning_claim=false` remains authoritative. Successor #130 owns a
design-only learning-state persistence architecture rethink; any accepted
production law/state-model change requires a later explicit
specification-change owner.

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
#91 / PR #92, P6.6 through #95 / PR #96, P6.7 through #98 / PR #99,
P6.8 through #101 / PR #102, and P6.9 through #104 / PR #105. Phase 6 remains
a bounded capability ladder, but no P6.10 or later capability is currently
selected. Accepted learning-path research extends through #127 / PR #129 and
has not demonstrated canonical learning. #113 localizes the formal deepest
reachable failed causal level at L3 memory persistence; #120 establishes a
predeclared high-contrast immediate write condition; #122 shows that the
baseline trace is not robust at +1000; #127 shows that direct generic latent or
structure consolidation creates pre-lifecycle non-HP state but still reaches
only 5/12 +1000 persistence, routing the next bounded question to #130's
design-only learning-state persistence architecture rethink.
`learning_claim=false` remains authoritative. See
`docs/PHASE6_HANDOFF.md`.

See `docs/ROADMAP.md`.
