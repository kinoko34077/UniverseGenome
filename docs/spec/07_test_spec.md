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

## Phase 2C acceptance tests

### TEST-P2C-001 Fusion eligibility and result

An exact local 2×2 cover with compatible level, velocity and bond state fuses
once into a level+1 1×1 core with the specified HP, direction, speed, age,
bond, latent and slot lifecycle results.

### TEST-P2C-002 Fusion rejection and bounded discovery

Wrong-level, under-bonded, over-threshold-velocity and non-composing local
groups remain unchanged; candidate discovery is local and bounded.

### TEST-P2C-003 Fusion snapshot continuation

Save/load restores fusion parameters and fused state; resumed execution equals
uninterrupted execution.

## Phase 2D acceptance tests

### TEST-P2D-001 Fragment state split

A level>0 core retains its level and emits one lower 1×1 fragment with the
canonical direction, speed, latent, HP and age split.

### TEST-P2D-002 Level-0 and capacity behavior

Compound level-0 shapes collapse, level-0 singles follow deletion, and full
capacity/probability-zero cases are deterministic no-ops.

### TEST-P2D-003 Fragmentation snapshot continuation

Save/load restores fragmentation parameters and state; resumed execution
equals uninterrupted execution.

## Phase 2E acceptance tests

### TEST-P2E-001 Age-class boundaries

Age zero is safe, age 1 maps to class 0, and the 2/4/8/16 boundaries map to
the highest-set-bit classes specified by `SPEC-AGE-001`.

### TEST-P2E-002 Age-scaled fragmentation pressure

The configured base fragmentation rate is multiplied by the class power of
two with uint16 saturation; disabled aging preserves the base rate.

### TEST-P2E-003 Deterministic age pressure

Fixed seed/config/state produces the same age-dependent fragmentation outcome,
and an older structure receives a higher pressure window than a younger one.

### TEST-P2E-004 Aging snapshot continuation

Save/load restores aging configuration and state; resumed execution equals
uninterrupted execution.

## Phase 3 acceptance tests

### TEST-P3-001 Population layout and matched metadata

The runtime creates exactly 128 independent slots as four categories × 32,
with corresponding genome/seed pairs aligned across categories.

### TEST-P3-002 Independent deterministic stepping

Fixed population seed/configuration produces the same per-slot trajectory on
replay, and stepping one slot cannot mutate another slot.

### TEST-P3-003 Bounded rewind and clone isolation

Only 128/256/512 generation histories are accepted; rewind stays bounded and
observation clones cannot mutate authoritative slots.

### TEST-P3-004 Headless and observer/control surface

Population status/summary runs without the GUI, while the 16×8 overview,
detail modes, required controls, and external-clock declaration are exposed.

### TEST-P3-005 Bounded rewind memory evidence

The 128, 256, and 512 history policies retain at most the selected bounded
entry count, report a reproducible compact-history memory estimate, and remain
within the explicit runtime budget.

## Phase 4 acceptance tests

### TEST-P4-001 Raw bus and fixed organs

Bytes 0..255, independent VALID, fixed input/output organs, and recorded
non-cell coordinates are representable and deterministic.

### TEST-P4-002 Edge-based output events

Only VALID rising edges emit bytes or NULL; continuous HIGH does not repeat an
event, LOW→HIGH emits a new event, and an already-HIGH line at evaluation start
is primed without producing a spurious event.

### TEST-P4-003 Teacher exclusion and clone evaluation

Teacher B/NULL stimulation is kept out of autonomous output scoring, and
evaluation on a clone leaves the authoritative training state unchanged.

### TEST-P4-004 Multi-seed learning measurement

Baseline and trained A→B→NULL measurements run across multiple seeds with a
predeclared criterion, plus no-input and alternate-input output-clean
counterfactuals; a failed criterion is recorded as failure, not success.

### TEST-P4-005 Footprint-safe I/O boundary

Initial and noise spawns avoid every fixed-organ tile across their complete
destination footprint. Output occupancy and input proximity detect compound
cells through the complete footprint rather than only the anchor tile.

## Phase 5 acceptance tests

### TEST-P5-001 Genome separation and mutation

Genome fields exclude seed and protocol fields; mutation changes one adjacent
binary-grid parameter without changing category or seed.

### TEST-P5-002 Fitness and growth

Absolute fitness follows the lexicographic specification, while growth flags
and four 8-bit windows remain separate and bounded. Growth bit 5 retains the
canonical `retention` meaning and bit 6 retains the canonical `noise
robustness` meaning. Phase 4 no-input-clean and alternate-input-clean
counterfactual measurements must not be silently substituted for those fields.

### TEST-P5-003 Pruning and protection

Category-relative low-growth eligibility uses four windows and protects the
absolute-fitness top 1/8 from growth-only pruning. Authoritative 16-generation
health boundaries detect all-active-cell loss as an absolute-failure reason,
including for a provisional slot. Activity telemetry is persisted, but no
automatic persistent-non-response rule is accepted without a protocol
decision.

### TEST-P5-004 Steady-state escalation

Category-local replacement is deterministic. Same-genome evidence expands by
allocating additional real Universe slots for the same genome/category, while
mutation children are separate real slots with fresh state. The integrated loop
maintains all 128 authoritative Universe states, measures normalized fitness
from evaluation clones of those states, aggregates evidence across each real
same-genome seed group, advances growth only at real 128-generation boundaries,
applies the accepted category-local `tiered_category_rank` policy: aggregate
canonical fitness ranks evidence groups, 4→8 uses the top 1/2, 8→16 the top
1/4, and 16→32 the top 1/8; fractional cutoffs use floor division with a
minimum of one group. Never-matured mutation groups still complete to four
real seeds first; otherwise each category persistently alternates promising
evidence and mutation 1:1 when both are available, preferring lower evidence
count then better aggregate fitness then stable genome key. It
does not replace a live slot without a real free/prune-eligible target, keeps
groups below four real seed slots out of parent/protection selection, completes
never-matured mutation evidence through later freed slots, keeps provisional
sub-four mutation groups temporarily pruning-protected, preserves an
ever-mature marker once a group first reaches four real seeds, and keeps a
later-depleted mature group pruning-eligible without restoring parent/protection
eligibility. It also exercises multiple genome mutation fields and directly
covers the real growth sequence `0 → 128 → 256 → 384 → 512`. Integrated
mutation uses both directions of the adjacent binary grid, falls back from an
invalid bound direction, and never creates a no-op or an `initial_density`
value above effective `PhysicsConfig.max_cells`. Short-health tests retire
all-active-cell loss at the 16-generation cadence. Task-response tests record
one response/no-response observation at each 128-generation growth boundary
and retire `persistent_non_response` only after four consecutive no-output
observations (512 physical generations) while active cells remain; a wrong
autonomous output still counts as a response for this failure rule. Integrated
v0.1 measurement keeps retention/noise-robustness fields zero, so growth bits
5/6 cannot be driven by the separate counterfactual-clean observables.

### TEST-P5-005 Integrated persistence

Optimizer persistence includes the effective base/protocol configuration,
all 128 authoritative Universe states and their parameters, normalized
fitness/growth references, short-health/failure state, physical cadence state,
lineage, and scheduler policy state. It does not retain disposable evaluation
clones. Restore/resume produces the same bounded slot population as
uninterrupted continuation.

The headless performance path reports bounded optimizer iterations, evaluated
slots, replacements, mutation fields, actual same-genome slot-group counts,
and throughput. Promising-allocation state reports the accepted persisted
policy name and only reports evidence growth represented by corresponding real
authoritative slots.

### TEST-P5-006 Phase 6+ handoff boundary

The Phase 5 boundary records the Phase 4 outcome and a durable Phase 6+
handoff; no Phase 6+ capability is activated by the v0.1 Work Order.

---
