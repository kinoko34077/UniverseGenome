# World and Physics Behavior Specification

Owns geometric/local-physics behavior. The accepted Phase 1 subset, Phase 2A
contact/bond update, Phase 2B latent propagation, Phase 2C fusion, and Phase
2D fragmentation are implemented; aging remains deferred.

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

# 15. Fusion

Implemented in Phase 2C; aging remains deferred.

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

Implemented in Phase 2D; aging remains deferred.

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

Exact hash/generator choice is implementation-specific but must be documented.

---
