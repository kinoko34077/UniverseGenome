# ADR-009 — Candidate anonymous slow-trace persistence architecture
Status: proposed

## Context

Accepted learning-path research through #127 shows:

- current high-contrast teacher transduction can create content-bearing physical
  differences;
- unchanged production dynamics retain only 1/12 frozen primary B/H
  distinctions at +1000;
- direct generic writes into existing `latent` or `structure` can create
  pre-lifecycle non-HP distinctions in 12/12 cases but retain only 5/12 at
  +1000 against the frozen 8/12 gate.

#130 therefore re-evaluated the persistence architecture rather than adding
another one-shot write rule.

## Proposed decision

Advance **D1 — Anonymous Slow Trace with Conservative Local Transfer** to formal
specification review.

The proposal adds one bounded authoritative anonymous per-cell quantity:

`slow_trace:uint8`

Its intended role is a slower physical history timescale separate from:

- `latent:uint16` fast signal state;
- HP survival/activity state;
- bond/contact strength;
- structure/morphology.

The candidate architecture requires:

- generic meaningful-activity write;
- bounded conservative transfer across already-local compatible relations;
- bounded BLACK_HOLE discharge before final FREE;
- explicit deterministic forgetting;
- fusion/fragmentation material handling;
- bounded local read coupling through latent-transmission width only;
- authoritative snapshot/replay/version migration.

No teacher byte, token, target label, organ identity or host-side learned table
is part of the memory rule.

## Alternatives considered

### B1 — latent echo

Rejected as the primary specification candidate because long-timescale
persistence/erosion would operate on the same bits that already implement the
four accepted fast latent operator categories. It provides no clean physical
separation between transient signal and consolidated history.

### C1 — morphology cluster

Rejected as the primary specification candidate because reliable persistence
would couple memory directly to bond/structure/occupancy and therefore has
larger collateral effects on motion, collision, fusion and fragmentation.
#127 also showed limited contact-specific reachability/persistence for the
corresponding existing-state candidates.

### Foundation rethink

Retained as a fallback if the D1 specification or later causal implementation
cannot satisfy bounded locality, forgetting, turnover tolerance and the frozen
L3 persistence gate without semantic shortcuts.

## Consequences if later accepted

Positive:

- explicit slow/fast physical timescale separation;
- bounded state and transfer mass;
- explicit turnover path without permanent Cell ID;
- forgetting is part of the architecture rather than an afterthought;
- causal read effect remains local and semantic-agnostic;
- persistence becomes independently testable.

Costs/risks:

- one additional authoritative uint8 array per Universe;
- snapshot/version migration;
- new physical parameters and runtime work;
- scalar trace may still have insufficient effective memory capacity;
- transfer/equalization may erase spatial distinctions;
- read coupling may alter latent-signal strength and requires regression tests.

## Current authority

This ADR is **proposed**, not accepted.

#132 may refine/reject the proposal. It does not authorize production
implementation, accepted numeric defaults, L4 recall, P6.10+ work or a learning
claim. A production change requires accepted specification review followed by a
separate implementation owner.
