# Test Specification

These are Phase 1 acceptance tests. Phase 0 adds scaffold/smoke checks without claiming Phase 1 acceptance.

# 43. Phase 1 acceptance tests

## TEST-P1-001 Deterministic replay
Same config/seed/initial state/generation count → identical authoritative final state.

## TEST-P1-002 Torus
All boundaries wrap correctly.

## TEST-P1-003 Speed
Each supported speed produces expected displacement over known generation counts.

## TEST-P1-004 Tunneling
Intermediate occupied tiles do not collide; destination overlap does.

## TEST-P1-005 Noise determinism
Same accepted conditions → same noise events.

## TEST-P1-006 Collision
Destination collision works; 3+ arrivals do not trigger unbounded pair work.

## TEST-P1-007 HP / black-hole
HP reaches zero → BLACK_HOLE → revival or timeout deletion exactly as configured.

## TEST-P1-008 Snapshot roundtrip
Save → load → continue equals uninterrupted continuation.

## TEST-P1-009 Headless
Phase 1 tests/run can execute without GUI.

## TEST-P1-010 Performance metrics
At least report:

- generations/sec
- active cells
- collision count
- noise spawn count

## Phase 2A acceptance tests

### TEST-P2A-001 Local bond gain/decay

Compatible low-relative-speed destination contact saturating-adds bond
strength; non-contact and incompatible contact saturating-subtract it.

### TEST-P2A-002 Bounded contact accounting

Three or more arrivals continue to resolve only one deterministic pair, and
bond contact accounting does not introduce an N² persistent graph.

### TEST-P2A-003 Bond snapshot continuation

Save/load restores bond parameters and arrays; resumed execution equals
uninterrupted execution.

## Phase 2B acceptance tests

### TEST-P2B-001 Operator formulas

Masked Copy, Masked XOR, Rotate + Masked Copy, and Masked AND preserve the
canonical 16-bit formulas and rotate wraparound.

### TEST-P2B-002 Mask determinism and width

The same accepted event produces the same mask; bond strength selects a width
from 1 through 16 without duplicate bit positions.

### TEST-P2B-003 Synchronous local transmission

Compatible contact applies bounded latent updates from the pre-transmission
state and counts successful transmission as meaningful activity for HP gain.

---
