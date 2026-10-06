# World and Physics Behavior Specification

Owns geometric/local-physics behavior. The accepted Phase 1 subset, Phase 2A
contact/bond update, Phase 2B latent propagation, Phase 2C fusion, Phase 2D
fragmentation, and Phase 2E aging are implemented.

# 2. World geometry

## SPEC-WORLD-001 — Logical board
**Status: accepted**

Logical board:

`32 × 32`

Topology:

toroidal in x and y.

Logical coordinate ranges:

- x: 0..31
- y: 0..31

---

## SPEC-WORLD-002 — Internal fixed-point coordinates
**Status: accepted**

Each logical tile is subdivided into 8 units.

Internal coordinate range:

- `x_fp: 0..255`
- `y_fp: 0..255`

Recommended storage:

- `uint8` for x/y if implementation preserves modulo-256 wrap deterministically

Logical tile:

`tile_x = x_fp >> 3`

`tile_y = y_fp >> 3`

Spatial address:

`address = (tile_y << 5) | tile_x`

Range:

`0..1023`

---

---

# 5. Footprint

## SPEC-GEO-001 — Shape footprint
**Status: accepted-default**

At active hierarchy level:

- 1×1 occupies one logical tile
- 1×2 occupies two horizontal logical tiles
- 2×1 occupies two vertical logical tiles

Orientation is currently implied by shape code, not independently rotatable shape orientation.

If later shape rotation is introduced, update this specification before implementation.

---

## SPEC-GEO-002 — Destination-only occupancy
**Status: accepted**

For movement:

- do not sweep/check all intermediate tiles
- calculate destination
- calculate full destination footprint
- detect overlaps there

A 1×2 or 2×1 cell must check all destination tiles in its footprint.

---

---

# 6. Direction and speed

## SPEC-MOVE-001 — Directions
**Status: accepted**

Use eight directions:

0. N
1. NE
2. E
3. SE
4. S
5. SW
6. W
7. NW

The implementation may reserve 4 bits but only values 0..7 are valid in v0.1.

Opposite direction:

`opposite = (dir + 4) & 0b111`

---

## SPEC-MOVE-002 — Speed set
**Status: accepted**

Supported logical speeds:

- 0
- 1/8
- 1/4
- 1/2
- 1
- 2
- 4
- 8

Recommended internal step magnitudes:

- 0
- 1
- 2
- 4
- 8
- 16
- 32
- 64

No float position updates.

---

## SPEC-MOVE-003 — Direction vectors
**Status: accepted-default**

Use integer vectors.

Example:

- N = (0,-v)
- NE = (+v,-v)
- E = (+v,0)
- SE = (+v,+v)
- S = (0,+v)
- SW = (-v,+v)
- W = (-v,0)
- NW = (-v,-v)

Diagonal movement intentionally need not normalize by `sqrt(2)`.

---

## SPEC-MOVE-004 — Toroidal fixed-point wrap
**Status: accepted**

Updated internal x/y wrap modulo 256.

---

---

# 7. Generation semantics

## SPEC-STEP-001 — Synchronous model
**Status: accepted**

A generation must be processed from an authoritative state `t` to a committed state `t+1`.

Later-phase standard order:

1. external input / teacher stimulus
2. noise spawn proposal
3. movement proposal
4. destination placement
5. collision
6. bond update
7. latent propagation
8. fusion
9. age fragmentation
10. HP gain / decay / damage
11. black-hole transition / deletion
12. output edge detection
13. commit `t+1`

Phase 1 may omit unimplemented steps, but it must preserve the relative order of implemented steps and not mutate authoritative state in an order-dependent manner.

---

## SPEC-STEP-002 — Proposal / resolution principle
**Status: accepted**

Movement and multi-cell destination conflicts should use:

> read state → proposal → aggregate → resolve → commit

Avoid iteration-order behavior where a later cell overwrites an earlier cell's already-resolved update.

---

---

# 8. Destination buckets

## SPEC-COLL-001 — Spatial bucket
**Status: accepted-default**

Collision candidate discovery must be spatial.

For each destination logical address / footprint occupancy:

- collect relevant slot references for the generation
- use the collection only as temporary generation-local data

Do not persist destination buckets as cell identity.

---

## SPEC-COLL-002 — 3+ cells
**Status: accepted**

If more than two collision candidates require resolution at one destination in one generation:

- select one pair using deterministic event randomness
- resolve only that pair for the expensive collision interaction
- remaining cells may remain co-located / be processed by ordinary placement rules
- next generation may resolve further contact

Avoid all pair combinations.

---

---

# 9. Relative velocity

## SPEC-COLL-010 — Direction-aware velocity
**Status: accepted**

Collision/contact intensity must derive from velocity vectors.

A valid simple metric for v0.1 is:

`v_rel = max(abs(vx_a - vx_b), abs(vy_a - vy_b))`

This avoids square-root calculation and is compatible with 8-direction grid motion.

Threshold values remain parameterized.

---

---

# 10. Collision damage

## SPEC-COLL-020 — High-speed outcome
**Status: accepted-default**

High-relative-speed contact may cause:

- HP damage
- latent bit damage
- structure degradation / hierarchy lowering

The initial implementation need not perform fusion in Phase 1.

Exact formulas/thresholds must be config data, not hidden literals.

---

## SPEC-COLL-021 — Structure degradation
**Status: accepted-default**

At the lowest hierarchy:

- 1×2 → 1×1
- 2×1 → 1×1
- 1×1 → empty/free transition as lifecycle rules require

For higher hierarchy collision degradation, one-level downward structure movement is the preferred initial rule once that feature is implemented.

---

---

# 11. Bond/contact strength

## SPEC-BOND-001 — Storage
**Status: accepted-default**

No persistent pair graph.

Each active cell stores:

`bond_strength:uint8`

---

## SPEC-BOND-002 — Update
**Status: accepted-default**

Compatible low-relative-speed contact:

`bond_strength = sat_add(bond_strength, BOND_GAIN)`

Non-contact / incompatible state:

`bond_strength = sat_sub(bond_strength, BOND_DECAY)`

Both `BOND_GAIN` and `BOND_DECAY` are universe parameters.

---

---

# 13. Transmission mask

## SPEC-MASK-001 — Width
**Status: accepted-default**

For a transmitting cell/contact, effective mask width:

`n = 1 + (bond_strength >> 4)`

Therefore n ∈ 1..16.

The exact selected bit positions are determined by deterministic event randomness.

---

---

# 14. Four latent rule categories

These are the Phase 2B local transmission rules; fusion and later processing
remain deferred.

Let:

- `S` = source latent
- `D` = destination latent
- `M` = 16-bit transmission mask

## SPEC-LATENT-C0 — Masked Copy
**Status: accepted-default**

`D' = (D & ~M) | (S & M)`

## SPEC-LATENT-C1 — Masked XOR
**Status: accepted-default**

`D' = D ^ (S & M)`

## SPEC-LATENT-C2 — Rotate Copy
**Status: accepted-default**

`R = ROL16(S, rotate_amount)`

`D' = (D & ~M) | (R & M)`

`rotate_amount` is parameterized.

## SPEC-LATENT-C3 — Masked AND
**Status: accepted-default**

`D' = D & (S | ~M)`

If this category collapses toward zero, record the result rather than silently replacing the rule.

---

---

# 14.1 Candidate anonymous slow-trace dynamics (#132)

The following rules are **candidate** D1 behavior. They extend the accepted
local-physics step without changing the four latent operator formulas.

## SPEC-ST-001 — Generation-start trace view
**Status: candidate**

Let `T_i(t)` be the authoritative `slow_trace` of slot `i` at the start of
a generation.

Any slow-trace contribution to the current generation's latent-transmission
mask width reads `T(t)`, not a slow-trace value written later in the same
generation.

Purpose:

- prevent same-generation write→read positive feedback;
- preserve synchronous `t → t+1` semantics;
- make the causal ordering directly testable.

---

## SPEC-ST-002 — Generic meaningful-activity write
**Status: candidate**

For each ordinary-cell slot, define one generation-local meaningful-activity
eligibility bit from the same accepted physical source classes used by HP
recovery:

- **direct external stimulus**: the slot is in the external `stimulus_slots`
  supplied to the physical step for this generation;
- **successful local latent propagation**: the slot participates in the
  deterministic selected latent-transmission pair set for this generation.

Eligibility created only by the local-revival helper is not a second write
source unless the slot also satisfies one of the two source classes above.

The activity amount is exact:

```
g = recovery_hp if (external_stimulus or latent_activity) else 0
w = min(g, trace_write_cap)
```

There is at most **one** slow-trace write increment per cell per generation.
If both qualifying source classes occur for the same cell, they do not double
the write.

A BLACK_HOLE cell revived by direct external stimulus is eligible for this
single write. Eligibility is determined by the qualifying physical event, not
by whether a later fusion/fragmentation path causes the ordinary HP-gain loop
to skip that storage slot.

After latent propagation has resolved and before transfer/fusion:

`T_written = min(255, T(t) + w)`

The write path receives no byte value, organ identity, target label,
matched-control result or semantic category.

---

## SPEC-ST-003 — Conservative compatible-contact transfer
**Status: candidate**

D1 reuses the **exact deterministic non-overlapping pair set already selected
for ordinary latent transmission in step 7**. It does not perform a second
independent contact/pair-selection pass.

For each selected pair `A,B`, use the pair's post-write/pre-transfer values
`ta,tb`:

```
if ta > tb:
    q = min(trace_transfer_cap, (ta - tb) // 2)
    ta' = ta - q
    tb' = tb + q
elif tb > ta:
    q = min(trace_transfer_cap, (tb - ta) // 2)
    tb' = tb - q
    ta' = ta + q
else:
    ta' = ta
    tb' = tb
```

Properties:

- `ta'+tb' == ta+tb`;
- no value leaves `0..255`;
- no mass-copy amplification occurs;
- each slot participates in at most one ordinary transfer because the reused
  latent-transmission pair set is already non-overlapping;
- no extra persistent pair graph or global search is introduced.

All pair transfers read the complete post-write/pre-transfer trace view and are
committed synchronously.

---

## SPEC-ST-004 — Bounded latent-transmission read coupling
**Status: candidate**

For each directed half of an already-selected compatible latent-transmission
pair, let `S` be the transmitting/source cell and use its generation-start
slow trace `T_S(t)`.

Accepted baseline width:

`base_width = 1 + (bond_strength >> 4)`

Candidate trace bonus:

`trace_bonus = T_S(t) >> trace_bonus_shift`

Candidate effective width:

`n = min(16, base_width + trace_bonus)`

Requirements:

- `n` remains in `1..16`;
- the two directions of a selected pair independently use the corresponding
  source cell's generation-start trace;
- selected bit positions continue to use accepted deterministic event
  randomness;
- SPEC-LATENT-C0/C1/C2/C3 formulas are unchanged;
- slow trace changes only transmission width, not the transmitted bit value;
- a trace write caused by the current latent event cannot increase that same
  event's width.

---

## SPEC-ST-005 — Fusion and fragmentation material continuity
**Status: candidate**

If fusion occurs after write/transfer resolution:

`result_trace = min(255, sum(participant_trace))`

Any amount above 255 is explicit bounded saturation loss. Participant slots
made FREE by fusion are reset to zero trace.

Fragmentation follows the actual accepted fragmentation outcome:

- when a fragmentation event successfully creates a new fragment plus retained
  core:

```
fragment_trace = old_trace // 2
core_trace = old_trace - fragment_trace
```

  so the two resulting carriers conserve the pre-fragment trace exactly;

- when a level-0 horizontal/vertical shape degrades in-place to a single cell
  without allocating a second carrier, the surviving slot retains its current
  trace unchanged;

- when a level-0 single-cell fragmentation directly frees the slot, the trace
  is erased with that FREE transition; no synthetic recipient/ghost carrier is
  created;

- when a fragment allocation attempt fails and the accepted fragmentation
  operation therefore does not occur, trace remains unchanged.

These rules carry anonymous physical history through material reorganization
without creating semantic labels or lineage IDs.

---

## SPEC-ST-006 — BLACK_HOLE discharge and FREE erasure
**Status: candidate**

D1 preserves the accepted BLACK_HOLE revival/grace semantics. It adds discharge
only for a slot that **was BLACK_HOLE at generation start and remains
BLACK_HOLE after the generation-start revival decision**.

For such a carrier, discharge occurs after revival eligibility is resolved and
before the accepted black-hole timer decrement/final FREE erasure.

Eligible recipients are currently local ACTIVE cells whose physical footprints
overlap the BLACK_HOLE carrier footprint at that lifecycle-resolution point.

Per BLACK_HOLE carrier:

`budget = min(trace_discharge_cap, carrier_trace)`

Deterministic conflict resolution is exact:

1. process BLACK_HOLE carriers in ascending physical-state order
   `(tile_y, tile_x, y, x, structure, latent, bond_strength, direction,
   speed_code, age, black_hole_timer, slow_trace)`;
2. use reusable storage-slot index only as the final total-order tie-break for
   otherwise identical physical tuples; it is not an RNG/probability key,
   lineage identity or persisted semantic identity;
3. for each carrier, process eligible ACTIVE recipients in the same ordering
   discipline;
4. for each recipient, transfer
   `q = min(remaining_budget, carrier_trace, 255 - recipient_trace)`;
5. subtract every accepted `q` from the carrier immediately and add it to the
   recipient; later carriers observe the resulting recipient headroom;
6. stop when budget is exhausted or no ordered recipient has headroom.

Consequences:

- total trace never increases during discharge;
- a carrier with no eligible recipient keeps its trace until a later grace
  generation or loses it at final FREE;
- a revived BLACK_HOLE cell retains its remaining trace and performs no
  discharge in that generation-start BLACK_HOLE resolution;
- a cell that enters BLACK_HOLE later in the current generation is not a
  discharge carrier until the next generation;
- after discharge, the accepted black-hole timer decrement/free rule runs
  unchanged;
- final FREE sets `slow_trace=0`.

The transient storage-slot tie-break exists only to make an otherwise
physically equal ordering total; FREE→reuse never transfers trace identity.

---

## SPEC-ST-007 — Deterministic bounded decay
**Status: candidate**

After discharge and before generation commit, each remaining non-FREE carrier
with `slow_trace > 0` performs at most one decay event.

```
if event_u16(trace_decay_event_key) < trace_decay_rate:
    slow_trace -= 1
```

The decay key follows SPEC-RNG-001/002:

- universe seed;
- generation;
- physical spatial address;
- dedicated slow-trace decay event type;
- a physical fixed-point/local subaddress where needed to disambiguate events.

Reusable storage-slot index is not part of the probability key.

Decay is local forgetting. A zero decay-rate reference may be permitted only if
SP3 explicitly classifies it as a non-default research/reference value; the
architecture's accepted operating contract must retain a physically available
forgetting path.

---

## SPEC-ST-008 — Candidate insertion into SPEC-STEP-001
**Status: candidate**

If D1 is later accepted/implemented, the accepted generation order is preserved
with these explicit slow-trace insertions:

1. external input / teacher stimulus records direct external-stimulus
   eligibility;
1a. generation-start BLACK_HOLE resolution:
   - determine accepted revival eligibility;
   - revived cells retain trace and do not discharge;
   - non-revived BLACK_HOLE carriers perform SPEC-ST-006 discharge;
   - then run the accepted timer decrement/final FREE rule unchanged;
2. noise spawn proposal;
3. movement proposal;
4. destination placement;
5. collision;
6. bond update;
7. latent propagation:
   - each directed mask width reads generation-start `slow_trace`;
   - the accepted deterministic non-overlapping selected pair set is retained
     for slow-trace transfer;
   - successful propagation records latent-activity eligibility;
7a. apply the single per-cell meaningful-activity write from SPEC-ST-002;
7b. apply synchronous conservative transfer on the exact reused selected pair
    set from SPEC-ST-003;
8. fusion, including candidate trace fusion;
9. age fragmentation, including the SPEC-ST-005 outcome-specific trace rule;
10. HP gain / decay / damage;
11. ACTIVE→BLACK_HOLE transition for newly depleted active cells;
11a. apply slow-trace decay to all remaining non-FREE carriers;
12. output edge detection;
13. commit `t+1`.

A cell newly entering BLACK_HOLE at step 11 cannot discharge until the next
generation's step 1a. This preserves the accepted grace/countdown boundary.

No substep may consume a value written by a later substep. Ordinary transfer
reads post-write/pre-transfer values. Fusion/fragmentation read post-transfer
trace. Read coupling always uses the generation-start trace view.

---

# 15. Fusion

Implemented in Phase 2C; age-dependent pressure is implemented in Phase 2E.

## SPEC-FUSION-001 — Eligibility
**Status: accepted-default**

Fusion candidate requires:

- same active hierarchy level
- participant footprints exactly compose a 2×2 region
- compatible occupancy
- relative velocity <= fusion threshold
- participant bond/contact state >= threshold

Exact thresholds are universe parameters.

---

## SPEC-FUSION-002 — Result
**Status: accepted-default**

Participants become one upper-level core.

Result:

- hierarchy: `k+1`
- shape: 1×1
- age: 0
- bond_strength: 0
- HP: saturating sum of participant HP
- direction: direction of participant with greatest HP
- speed: minimum participant speed

Tie resolution must be deterministic.

Unused participant slots become FREE.

---

## SPEC-FUSION-003 — Latent mixer
**Status: accepted-default**

Fusion latent mixing is common across the four transmission categories.

For spatially ordered participants:

`acc ^= ROL16(latent_i, rotation_i)`

Default 4-position rotations:

- 0
- 4
- 8
- 12

Purpose:

avoid confounding transmission-rule category comparison with a different fusion rule.

---

---

# 16. Fragmentation

Implemented in Phase 2D; age-dependent pressure is implemented in Phase 2E.

## SPEC-FRAG-001 — General behavior
**Status: accepted**

For hierarchy level > 0:

> upper core remains + one lower fragment is emitted.

This is intentionally not the mathematical inverse of fusion.

---

## SPEC-FRAG-002 — Fragment state
**Status: accepted**

Fragment:

- hierarchy = core hierarchy - 1
- shape = 1×1
- direction = opposite core direction
- age = 0

Initial speed:

same speed as core unless empirical work later changes this default.

---

## SPEC-FRAG-003 — Latent conservation-style split
**Status: accepted-default**

Given split mask `F`:

`fragment_latent = old_latent & F`

`core_latent = old_latent & ~F`

Do not duplicate all latent bits into both children.

---

## SPEC-FRAG-004 — HP split
**Status: accepted**

`fragment_hp = old_hp >> 1`

`core_hp = old_hp - fragment_hp`

Do not create HP through fragmentation.

---

## SPEC-FRAG-005 — Age reset
**Status: accepted-default**

- fragment age = 0
- core age = `old_age >> 1`

---

## SPEC-FRAG-006 — Level 0 collapse
**Status: accepted**

No new fragment below level 0.

Instead:

- 1×2 → 1×1
- 2×1 → 1×1
- 1×1 → empty/deletion path

---

---

# 17. Aging

## SPEC-AGE-001 — Age class
**Status: accepted-default**

Age pressure uses:

`age_class = floor(log2(age))`

implemented via highest-set-bit logic where practical.

Examples:

- 1 → 0
- 2..3 → 1
- 4..7 → 2
- 8..15 → 3

Fragmentation probability increases by power-of-two steps with age class.

Base probability is universe parameter.

---

---

# 19. Black-hole lifecycle

## SPEC-BH-001 — Entry
**Status: accepted**

When HP reaches 0:

`ACTIVE → BLACK_HOLE`

not immediate FREE.

---

## SPEC-BH-002 — Behavior
**Status: accepted**

BLACK_HOLE cells:

- do not move
- do not fuse
- do not fragment
- may receive allowed stimulation/signal
- may return ACTIVE if HP becomes positive

---

## SPEC-BH-003 — Expiration
**Status: parameterized**

Grace family initially centered on:

- 32
- 64 generations

The implemented default is `black_hole_grace = 2` generations. The value is
still parameterized for bounded experiments; 32 and 64 are candidate values,
not the current default.

After expiration with no revival:

`BLACK_HOLE → FREE`

---

---

# 20. Background noise

## SPEC-NOISE-001 — Event model
**Status: accepted**

Per universe per generation:

- perform one noise-event decision
- if false: no noise spawn
- if true: choose a position deterministically from event RNG
- allocate one free slot
- create ordinary 1×1 cell

If no free slot:

- discard event

If spawn overlaps:

- normal physics resolves it

The implementation makes one deterministic noise-event decision per
generation. `noise_attempts` remains a readable legacy configuration field for
snapshot/config compatibility, but it does not multiply event decisions.

## SPEC-INIT-001 — Generated substrate excitation
**Status: accepted-default**

**Parameterization:** experiments may select other bounded values through
`PhysicsConfig`.

Generated initial and background-noise cells use explicit configuration values
for latent excitation and speed. The current default is `initial_latent = 1`,
`initial_speed_code = 1`, `noise_latent = 1`, and `noise_speed_code = 1`.
These values make the ordinary generated path capable of movement and latent
participation while preserving `UniverseState.spawn()` defaults for tests and
manual fixtures. Experiments may select other bounded values through
`PhysicsConfig`.

---

## SPEC-NOISE-002 — Probability
**Status: parameterized**

Initial search family:

- 1/1024
- 1/512
- 1/256
- 1/128
- 1/64

---

---

# 21. Deterministic RNG

## SPEC-RNG-001 — No Cell ID dependency
**Status: accepted**

Permanent Cell ID is not available as RNG key.

---

## SPEC-RNG-002 — Event-derived preferred key
**Status: accepted-default**

Preferred random key components:

- universe_seed
- generation
- spatial_address
- event_type
- local_index

A hash/counter-style deterministic generator is preferred over one monolithic sequential stream when it improves matched comparisons.

For fragmentation probability, the implemented event key uses the cell's
physical tile as `spatial_address` and a fixed-point-position-derived
`local_index` with a dedicated chance subevent tag. Reusable storage-slot
indices are not part of the probability key. The fragmentation split-mask draw
continues to use physical position addressing with a distinct local-index
domain, so chance and split draws remain deterministic but separate.

Exact hash/generator choice is implementation-specific but must be documented.

---
