# Observation and GUI Specification

The GUI is an observer/control surface and does not own the authoritative simulation clock.

# 34. GUI overview

Specified for Phase 3.

## SPEC-UI-001
**Status: accepted**

Layout:

- 16 columns × 8 rows
- 128 universe thumbnails
- four categories grouped as two rows/category
- a few pixels of visual gap between universes/categories

Per-universe thumbnail:

- 8×8 summary
- about 2 fps

Initial visual mapping:

- activity → brightness
- highest hierarchy → hue

Do not reuse hue for category labeling; use border/label/layout for category identity.

---

---

# 35. GUI detail

## SPEC-UI-010
**Status: accepted**

Selected universe:

- 32×32 detail map
- about 8 fps

Modes:

- HP
- hierarchy
- latent bit 0..15
- activity
- bond/contact

---

## SPEC-UI-011 — HP mode
**Status: accepted-default**

Hue:

- high HP → blue
- medium HP → green
- low HP → red

Brightness:

- bond/contact strength

A nonzero minimum brightness must distinguish active unbonded cells from empty space.

---

## SPEC-UI-012 — Hierarchy mode
**Status: accepted-default**

- hue → hierarchy level
- brightness → bond/contact strength

---

## SPEC-UI-013 — Automatic alternation
**Status: accepted**

At 8 fps, initial automatic HP/hierarchy mode switch:

- every 4 rendered frames

If visually distracting, allow every 8 frames.

Manual mode lock is required.

---

---

# 36. GUI controls

## SPEC-UI-020
**Status: accepted**

Required controls:

- Run
- Pause
- 1 Step
- Reset
- Select Universe
- Clone for Observation
- Rewind
- Save Snapshot
- Load Snapshot

After Phase 5 becomes the authoritative automated-search owner, the same
surface has the following cross-phase semantics:

- Run / Pause control the outer `SteadyStateOptimizer` search loop;
- one outer search iteration is exposed separately from one physical
  observation step;
- physical 1 Step is allowed only on an isolated observation clone and never
  advances an authoritative search slot;
- Reset recreates the authoritative optimizer from the current reset
  configuration;
- universe selection may be performed directly by the 128 overview thumbnails;
  a redundant standalone selector that only re-selects the current index is not
  required;
- Clone for Observation copies the selected authoritative optimizer slot;
- Save / Load serialize and restore the authoritative Phase 5 optimizer
  snapshot, not a parallel Phase 3 population.

---

## SPEC-UI-021 — Rewind capacity
**Status: accepted**

Selectable:

- 128
- 256
- 512 generations

Use bounded ring/history storage, not unbounded generation retention.

The population runtime stores each retained checkpoint as compact deterministic
JSON text rather than a live nested Python dictionary. Runtime summaries expose
the retained entry count, serialized object memory estimate, a 256 MiB bound,
and whether the current estimate is within that bound. The 128/256/512 policy
therefore has executable memory evidence while preserving exact rewind and
snapshot round-trips.

---

## SPEC-UI-022 — Parameter edits
**Status: accepted**

Manual parameter changes do not mutate the constants of an already-running authoritative experiment.

Apply on next reset/spawn/new universe unless a future explicit live-edit mode is specified.
For the integrated v0.1 browser surface, exposed manual edits are staged as
pending reset parameters and are applied when Reset creates a new authoritative
optimizer. They are never written into already-running slot configurations.

---

# 37. Current observer implementation contract

The accepted observer surface is implemented through the server-owned runtime
payload. After Phase 5 integration, that runtime owns the single authoritative
`SteadyStateOptimizer`; it must not create a second authoritative
`core.population.Population`.

- every overview summary is projected from one of the 128 authoritative
  optimizer slots and contains a bounded 8×8 spatial projection with visual
  activity, highest hierarchy, and occupancy values;
- overview/detail metadata exposes the actual category, genome, seed,
  absolute fitness, growth history, evidence-group size/maturity, current
  lineage fields, allocation reason, and latest replacement/prune event when
  available;
- detail cells expose HP, hierarchy level, latent, visual activity, and
  bond/contact values;
- the current activity rendering value is explicitly a display-only proxy
  `min(255, bond_strength + 16 * popcount(latent))`; it is not the optimizer
  `activity_cost` fitness observable;
- overview polling is 500 ms and detail polling is 125 ms; those render timers
  only read state and never advance search or physical time;
- HP/hierarchy automatic alternation occurs every four detail frames and can
  be manually locked;
- clone observation is an explicit selected observation target; physical
  stepping/rewind on that clone does not mutate or advance the authoritative
  slot;
- authoritative Save/Load uses
  `UniverseGenomePhase5SteadyStateOptimizer` snapshots;
- observation-clone rewind capacity is bounded to 128, 256, or 512 physical
  generations, with 512 as the default.

---
