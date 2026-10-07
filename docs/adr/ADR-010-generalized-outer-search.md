# ADR-010 — Generalized registered Outer Search with legacy-equivalence oracle

**Status:** accepted specification  
**Authority:** #144 / #145

## Context

UniverseGenome already separates two recursive responsibilities:

- the Inner Universe evolves one authoritative state through deterministic local physics;
- the Outer optimizer runs many Universes and searches/selects Universe-level physics.

The accepted Phase 5 implementation proves that the Outer layer is real, but
its searchable scalar fields, four latent-operator categories, mutation-field
knowledge and category allocation are structurally hard-coded. Later research,
including slow-trace persistence work, therefore had to compare additional
physical profiles in one-off research harnesses even though choosing among
bounded physical alternatives is an Outer-search responsibility.

Continuing that pattern would duplicate allocation/evidence/selection logic and
make each new physical research question require a bespoke arena.

## Decision

Generalize the existing Outer Search around a versioned declarative
`SearchPlan`, registered Scalar/Rule/Conditional Dimensions,
`ResolvedUniverseSpec`, versioned ObjectiveProfiles and declared comparison
strata/cohorts.

The generic Outer engine may search only explicitly enabled registered
Universe-level dimensions. The Inner runtime remains a deterministic executor
of one fully resolved physical specification and receives no candidate rank,
fitness, mutation reason, stratum, cohort or acceptance metadata.

Rule families are finite registered repository implementations referenced by
stable IDs. SearchPlan cannot supply arbitrary executable source, runtime
`eval`, callable/import payloads or dynamic code.

The accepted pre-generalization Phase 5 behavior from
`211d84b18fe68e70f89c8921d156e1b7c0592895` is a blocking compatibility
oracle, frozen under
`research/artifacts/legacy_outer_search_oracle_v1/manifest.json`.
The canonical Legacy SearchPlan must reproduce that behavior exactly before any
new search dimension is activated.

## Why this decision

### Generalize the existing Outer layer instead of adding one-off arenas

The existing Outer layer already owns candidate population, matched seed
evidence, mutation, pruning, lineage and replacement. New bounded
Universe-level research axes belong behind that same responsibility boundary.
This keeps search-policy semantics in one place and allows staged/fixed search
without duplicating research harness logic.

### Registered finite rule families instead of arbitrary code evolution

A physical rule is executable behavior, not ordinary scalar data. Allowing a
plan to inject arbitrary code would weaken deterministic replay, locality,
boundedness, reviewability and security. A finite registered family preserves
searchability while keeping implementations reviewed and repository-owned.

### Exact legacy behavior is a blocking oracle

The goal is architectural generalization, not an optimizer-policy change.
Approximate "legacy mode" would make later research ambiguous because observed
differences could come from the refactor itself. Therefore the accepted
pre-generalization initialization, dynamic checkpoints, optimizer decisions,
persistence and continuation are frozen before refactoring and must match
exactly under Legacy SearchPlan.

Performance timing is compared separately under matched conditions because
wall-clock throughput is observational rather than a deterministic state
oracle.

## Consequences

- SearchPlan/registry/candidate/provenance become explicit Outer concepts.
- Current UniverseGenome and latent-category behavior require one authoritative
  compatibility mapping into the generalized model.
- Persisted generalized Outer state advances the optimizer envelope from v6 to
  v7; nested UniverseState does not change solely for this refactor.
- Slow-trace parameters can be represented but remain fixed at production
  defaults `(0,0,0,0,8)` in Legacy SearchPlan.
- A new registered dimension is not searchable until a SearchPlan explicitly
  enables it.
- Seed remains evidence and experiment/protocol parameters remain outside
  candidate physics.
- Search and final held-out validation cohorts remain distinct.
- The known #140 cohort cannot be adaptively tuned against and then reused as
  unbiased final acceptance evidence.
- `learning_claim=false`, L4 unevaluated state, P6.10+ freeze and #93
  separation remain unchanged.

## Reconsider

Reconsider this ADR only if evidence shows that:

- exact legacy behavior cannot be represented without preserving hard-coded
  generic scheduler knowledge;
- the registered finite-rule model cannot express an accepted bounded physical
  rule family;
- the generalized boundary introduces unacceptable measured overhead and no
  reviewed bounded implementation can satisfy the performance gate; or
- a separately accepted architecture supersedes the Inner/Outer contract.

A failed memory-physics search result alone is not a reason to weaken the
legacy-equivalence or no-arbitrary-code boundaries.
