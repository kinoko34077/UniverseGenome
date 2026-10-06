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

# 14.1 Anonymous slow-trace dynamics (#132)

The following rules are the **accepted D1 behavior specification**. They are
implementation-pending and extend the accepted local-physics contract without
changing the four latent operator formulas.

SP3 defines two configuration classes:

- **inert compatibility/default profile**:
  `write=0, transfer=0, discharge=0, decay=0, bonus_shift=8`; this profile
  must not alter any accepted pre-D1 physical trajectory;
- **active research profile**: `trace_write_cap`, `trace_transfer_cap`,
  `trace_discharge_cap` and `trace_decay_rate` are all nonzero and
  `trace_bonus_shift` is in `0..7`. Numeric active values are research-only
  until a later causal/performance/migration gate promotes them.

A partially enabled mix may be used only as an explicitly named diagnostic or
reference condition. It is not an accepted active production default merely
because each value is within its legal type range.

## SPEC-ST-001 — Generation-start trace view
**Status: accepted**

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
**Status: accepted**

For each ordinary cell, derive one **recovery-equivalent activity amount**
`g_i(t)` from the meaningful-activity recovery applications that the accepted
HP path recognizes in that generation. Qualifying sources remain:

- external stimulus received;
- successful local latent signal propagation;
- accepted BLACK_HOLE revival stimulation.

`g_i(t)` is based on the configured physical recovery amount(s), not on the
net HP delta after uint8 saturation. Consequently, a valid physical activity
event may still write trace when HP is already 255.

The aggregation follows accepted recovery applications, not raw semantic
presentation multiplicity:

- multiple organ anchors that resolve to the same stimulated ordinary-cell slot
  do not create multiple trace writes merely because several lines overlap;
- when accepted HP logic treats simultaneous ordinary stimulus and latent
  activity as one recovery application, slow trace treats it as one;
- if the accepted lifecycle/HP path performs two distinct recovery applications
  for a slot in one generation, both contribute to `g_i(t)`.

For `g_i(t) > 0`:

`w_i = min(g_i(t), trace_write_cap)`

After latent propagation is resolved:

`T_written_i = min(255, T_i(t) + w_i)`

The write path receives no byte value, organ identity, target label,
matched-control result or semantic category.

---

## SPEC-ST-003 — Conservative compatible-contact transfer
**Status: accepted**

After slow-trace write proposals are applied, an already-selected compatible
local latent-transmission pair `A,B` may redistribute trace.

Using the pair's post-write/pre-transfer values `ta,tb`:

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
- only the same deterministic non-overlapping pair set selected for accepted
  local latent transmission is eligible;
- slow trace does not run an independent second pair-selection algorithm;
- if a compatible contact is not selected for latent transmission in that
  generation, it performs no slow-trace transfer;
- pair resolution does not create or persist a Cell identity.

All eligible transfer pairs read pre-transfer values and commit synchronously.
Reusing the latent-transmission pair set prevents D1 from silently adding a new
contact topology or extra per-cell pair fanout.

---

## SPEC-ST-004 — Bounded latent-transmission read coupling
**Status: accepted**

For an already-compatible selected latent transmission, let `S` be the
transmitting/source cell and use its generation-start slow trace `T_S(t)`.

Accepted baseline width:

`base_width = 1 + (bond_strength >> 4)`

Trace bonus:

`trace_bonus = T_S(t) >> trace_bonus_shift`

Effective width:

`n = min(16, base_width + trace_bonus)`

Requirements:

- `n` remains in `1..16`;
- selected bit positions continue to use accepted deterministic event
  randomness;
- SPEC-LATENT-C0/C1/C2/C3 formulas are unchanged;
- slow trace changes only transmission width, not the transmitted bit value;
- a trace write caused by the current latent event cannot increase that same
  event's width.

---

## SPEC-ST-005 — Fusion and fragmentation material continuity
**Status: accepted**

If fusion occurs after write/transfer resolution:

`result_trace = min(255, sum(participant_trace))`

Any amount above 255 is explicit bounded saturation loss. Participant slots
made FREE by fusion are reset to zero trace.

If fragmentation occurs:

```
fragment_trace = old_trace // 2
core_trace = old_trace - fragment_trace
```

Thus fragmentation creates no trace mass and both resulting values remain
bounded.

These rules carry anonymous physical history through material reorganization;
they do not carry a semantic label or lineage ID.

---

## SPEC-ST-006 — BLACK_HOLE discharge and FREE erasure
**Status: accepted**

A BLACK_HOLE carrier may discharge trace before final BLACK_HOLE→FREE
expiration.

This requires one explicit specified change to the current lifecycle ordering:
a pre-existing BLACK_HOLE whose timer reaches the expiration boundary is marked
**pending FREE** for the current generation rather than being erased
immediately at generation start. It remains immobile and does not participate
as an ACTIVE collision/transmission/fusion/fragmentation cell. Its final
`free()` occurs only after the discharge opportunity later in the same
generation.

Per BLACK_HOLE carrier per generation:

`budget = min(trace_discharge_cap, carrier_trace)`

Requirements:

- recipients come only from current local ACTIVE
  occupancy/neighborhood information;
- recipients are processed in a deterministic physically addressed order;
- reusable storage-slot identity is not part of the random/event key and is
  never persistent lineage;
- each transfer is capped by remaining budget and recipient uint8 headroom;
- transferred quantity is subtracted from the BLACK_HOLE carrier;
- total trace does not increase;
- if no recipient is available, remaining trace stays with a non-expiring
  carrier until a later grace generation or is lost at final FREE;
- a pending-FREE carrier receives exactly the current generation's bounded
  discharge opportunity and then loses any remainder when freed;
- a newly entered BLACK_HOLE may use the same bounded discharge rule in that
  generation;
- a revived cell retains the trace it still owns and rejoins ACTIVE processing;
- final FREE sets `slow_trace=0`.

No ghost record survives slot release.

---

## SPEC-ST-007 — Deterministic bounded decay
**Status: accepted**

After discharge and before generation commit, each non-FREE carrier that will
survive the commit and has `slow_trace > 0` performs at most one decay event.

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

Decay is local forgetting. SP3 permits `trace_decay_rate=0` only in the
inert compatibility/default profile or an explicitly named diagnostic/reference
condition. Any active D1 research profile used to support persistence acceptance
must use a nonzero decay rate so the architecture retains an exercised,
physically available forgetting path.

A pending-FREE carrier is erased after its discharge opportunity and need not
perform a decay event whose result would be discarded immediately.

---

## SPEC-ST-008 — Insertion into SPEC-STEP-001
**Status: accepted**

When D1 is implemented, the generation ordering becomes the
accepted SPEC-STEP-001 order plus the following constrained substeps:

0. capture generation-start `slow_trace T(t)`;
0a. process pre-existing BLACK_HOLE revival/aging boundary:
    - accepted external/local revival still occurs before ordinary movement;
    - non-revived BLACK_HOLE timers advance;
    - an expiring carrier becomes pending-FREE rather than being erased yet;
    - non-revived BLACK_HOLE/pending-FREE carriers remain immobile and excluded
      from ACTIVE collision/transmission/fusion/fragmentation processing;
1. external input / teacher stimulus records ordinary-cell meaningful activity;
2. noise spawn proposal;
3. movement proposal;
4. destination placement;
5. collision;
6. bond update;
7. latent propagation:
   - mask width reads generation-start `T(t)`;
   - successful propagation records ordinary physical activity;
   - expose the same selected non-overlapping transmission-pair set to trace
     transfer;
7a. apply slow-trace meaningful-activity write proposals;
7b. apply synchronous conservative slow-trace transfer on exactly that selected
    pair set;
8. fusion, including slow-trace fusion;
9. age fragmentation, including slow-trace split;
10. HP gain / decay / damage;
11. lifecycle completion:
    - ACTIVE cells reaching HP zero enter BLACK_HOLE;
    - discharge trace from remaining/new/pending-FREE BLACK_HOLE carriers to
      current local ACTIVE recipients;
    - apply slow-trace decay to ACTIVE and non-expiring BLACK_HOLE carriers that
      will survive commit;
    - finalize pending-FREE carriers with `free()` and zero trace;
12. output edge detection;
13. commit `t+1`.

No substep may consume a value written by a later substep. Transfer reads
post-write/pre-transfer pair values. Fusion/fragmentation read the post-transfer
trace. Read coupling always uses the generation-start trace view.

This ordering intentionally differs from current production only
where required to give an expiring BLACK_HOLE a bounded discharge opportunity
before slot erasure; SP2 acceptance tests must make that difference RED before
implementation.

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
