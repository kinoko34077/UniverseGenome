# ADR-009 — Anonymous slow-trace persistence architecture
Status: accepted specification decision (#132); implementation pending

## Context

Accepted learning-path evidence through #120, #122 and #127 shows that:
- a bounded content-specific physical write can occur;
- current unchanged physics retains only 1/12 primary B/H distinctions at +1000;
- direct generic writes into existing latent or structure state can create
  pre-lifecycle non-HP state 12/12 but retain only 5/12 at +1000.

#130 therefore selected D1 — Anonymous Slow Trace with Conservative Local
Transfer — as the least-collateral architecture coherent enough for formal
specification review. That selection did not accept production implementation.

## Decision

#132 accepts D1 as the specification architecture for a separate RED-first
implementation/research owner. Production behavior remains unchanged until that
later owner passes the accepted implementation and causal gates. The specified
authoritative per-cell slow state is:

`slow_trace:uint8[MAX_CELLS]`.

The accepted architecture specification is inseparable from these constraints:
- values carry no byte/token/teacher/target semantics;
- qualifying write sources are generic physical activity only;
- ordinary transfer reuses the selected local latent-transmission pair set and
  is conservative;
- BLACK_HOLE carriers have bounded local discharge before final FREE;
- trace has explicit deterministic physical forgetting;
- fusion/fragmentation have explicit material trace semantics;
- read coupling changes only bounded latent-transmission mask width and leaves
  all four latent operator formulas unchanged;
- authoritative snapshot/replay state includes the field and required
  parameters;
- no permanent Cell ID, host-side learned state, global memory search or N²
  persistent graph is introduced.

## Why a new state axis is proposed

Rejected primary alternatives from #130:
- latent echo: long-term memory would share and alter the existing fast latent
  signaling substrate;
- morphology/topology cluster: memory would be strongly confounded with
  structure, bond, movement, collision, fusion and fragmentation dynamics.

D1 adds one finite state axis in exchange for explicit timescale separation,
turnover transfer, forgetting and a bounded causal read effect.

## Compatibility boundary

This specification decision does not by itself change:
- fixed I/O organ geometry or raw-byte protocol;
- teacher/evaluation authority separation;
- Phase 5 fitness/search/category semantics;
- P6.1–P6.9 behavior;
- the canonical A→B→NULL learning criterion;
- `learning_claim=false`;
- the P6.10+ freeze.

Production implementation requires the specified UniverseState v2 / optimizer
v6 boundaries with legacy v1 and optimizer v4/v5 zero-trace migration and a
separate implementation owner.

## Acceptance / falsification boundary

D1 is not classified as L3-persistence-capable unless a separately predeclared
causal audit passes the frozen gate:
- accepted B/H high-contrast condition;
- frozen #122/#127 density32 primary cohort;
- >=8/12 content-specific distinctions at +1000;
- declared carrier-turnover cases where the original carrier is FREE but the
  distinction survives elsewhere in authoritative local state;
- negative sentinels clean;
- deterministic replay and raw/instrumented equivalence;
- no semantic shortcut.

L4 recall remains a later independent gate.

## Status boundary

This ADR is **accepted at the specification level** by #132. That acceptance
does not claim implementation or L3 capability. Production state/physics remain
unchanged until a separate successor owner completes RED-first implementation,
verification and the accepted causal gate.
